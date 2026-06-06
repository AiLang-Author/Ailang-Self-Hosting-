/*
 * flac_worker.c
 * FLAC codec worker — wraps libavcodec FLAC decoder, speaks CodecRing protocol.
 *
 * Usage: flac_worker <session_id>
 *
 * Reads compressed FLAC packets from:  /dev/shm/ailang_codec_<id>_pkt
 * Writes decoded S16LE PCM frames to: /dev/shm/ailang_codec_<id>_frm
 *
 * Output frames carry:
 *   CRFrameDesc.sample_count  = resampled sample count
 *   CRFrameDesc.sample_rate   = 48000 (resampled to match ALSA)
 *   CRFrameDesc.channels      = 2 (stereo, resampled if needed)
 *   CRFrameDesc.bit_depth     = 16
 *   pts_ns                    = as received from MediaCenter (pass-through)
 *
 * Build:
 *   gcc -O2 -o flac_worker flac_worker.c \
 *       $(pkg-config --cflags --libs libavcodec libavutil libswresample)
 *
 * Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>

#include <libavcodec/avcodec.h>
#include <libavutil/frame.h>
#include <libavutil/mem.h>
#include <libswresample/swresample.h>

#include "ailang_codec_abi.h"

/* ============================================================
 * Ring open helpers
 * ============================================================ */
static CRRing *open_ring(const char *path, int create) {
    int flags = create ? (O_RDWR | O_CREAT) : O_RDWR;
    int fd = open(path, flags, 0666);
    if (fd < 0) { perror(path); return NULL; }
    size_t total = CR_HEADER_SIZE + CR_DEFAULT_SIZE;
    void *ptr = mmap(NULL, total, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);
    if (ptr == MAP_FAILED) { perror("mmap"); return NULL; }
    return (CRRing *)ptr;
}

static void close_ring(CRRing *r) {
    munmap(r, CR_HEADER_SIZE + CR_DEFAULT_SIZE);
}

/* ============================================================
 * Build /dev/shm paths for this session
 * ============================================================ */
static void build_paths(int session_id, char *pkt_path, char *frm_path) {
    snprintf(pkt_path, 64, "/dev/shm/ailang_codec_%d_pkt", session_id);
    snprintf(frm_path, 64, "/dev/shm/ailang_codec_%d_frm", session_id);
}

/* ============================================================
 * Write a decoded audio frame into the frame ring
 * ============================================================ */
static int write_audio_frame(CRRing *frm_ring, AVFrame *frame,
                              SwrContext *swr, int64_t pts_ns)
{
    /* Target: S16LE 48000Hz stereo */
    int out_samples = av_rescale_rnd(
        swr_get_delay(swr, frame->sample_rate) + frame->nb_samples,
        48000, frame->sample_rate, AV_ROUND_UP);

    int frame_bytes = out_samples * 2 * 2;  /* 2 channels * 2 bytes/sample */
    size_t desc_size = sizeof(CRFrameDesc) + frame_bytes;
    CRFrameDesc *desc = (CRFrameDesc *)malloc(desc_size);
    if (!desc) return -1;

    /* Resample into desc->data */
    uint8_t *out_ptr = desc->data;
    int converted = swr_convert(swr,
        &out_ptr, out_samples,
        (const uint8_t **)frame->data, frame->nb_samples);
    if (converted < 0) { free(desc); return -1; }

    int actual_bytes = converted * 2 * 2;
    desc->width        = 0;
    desc->height       = 0;
    desc->pixel_fmt    = 0;
    desc->sample_count = (uint32_t)converted;
    desc->sample_rate  = 48000;
    desc->channels     = 2;
    desc->bit_depth    = 16;

    int r = cr_write_record(frm_ring, desc,
                            (uint32_t)(sizeof(CRFrameDesc) + actual_bytes),
                            RTYPE_FRAME, 0, pts_ns);
    free(desc);
    return r;
}

/* ============================================================
 * Main
 * ============================================================ */
int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "usage: flac_worker <session_id>\n");
        return 1;
    }

    int session_id = atoi(argv[1]);
    char pkt_path[64], frm_path[64];
    build_paths(session_id, pkt_path, frm_path);

    /* Open rings — MediaCenter creates them, we open existing */
    CRRing *pkt_ring = open_ring(pkt_path, 0);
    CRRing *frm_ring = open_ring(frm_path, 0);
    if (!pkt_ring || !frm_ring) {
        fprintf(stderr, "[flac_worker:%d] ring open failed\n", session_id);
        return 1;
    }

    printf("[flac_worker:%d] rings open, pkt=%s frm=%s\n",
           session_id, pkt_path, frm_path);

    /* Init libavcodec FLAC decoder */
    const AVCodec *codec = avcodec_find_decoder(AV_CODEC_ID_FLAC);
    if (!codec) { fprintf(stderr, "[flac_worker] no FLAC decoder\n"); return 1; }

    AVCodecContext *ctx = avcodec_alloc_context3(codec);
    int codec_opened = 0;

    AVPacket *pkt  = av_packet_alloc();
    AVFrame  *frame = av_frame_alloc();
    SwrContext *swr = NULL;  /* init after first decoded frame */

    /* Scratch buffer for reading packets out of the ring */
    uint8_t *pkt_buf = (uint8_t *)malloc(256 * 1024);
    if (!pkt_buf) return 1;

    printf("[flac_worker:%d] waiting for packets\n", session_id);

    int running = 1;
    while (running) {
        CRRecord hdr;
        uint64_t total = cr_peek_header(pkt_ring, &hdr);
        if (total == 0) {
            /* No packet yet — sleep 1ms and retry */
            struct timespec ts = { 0, 1000000 };
            nanosleep(&ts, NULL);
            continue;
        }

        if (hdr.flags & CR_FLAG_EOF) {
            /* Flush decoder */
            if (codec_opened) avcodec_send_packet(ctx, NULL);
            running = 0;
        } else if (hdr.flags & CR_FLAG_CONFIG) {
            /* FLAC codec extradata (STREAMINFO) */
            if (hdr.len <= 256 * 1024) {
                cr_consume(pkt_ring, pkt_buf, hdr.len, total);
                av_free(ctx->extradata);
                ctx->extradata_size = (int)hdr.len;
                ctx->extradata = av_mallocz(hdr.len + AV_INPUT_BUFFER_PADDING_SIZE);
                if (ctx->extradata) {
                    memcpy(ctx->extradata, pkt_buf, hdr.len);
                }
                printf("[flac_worker:%d] received extradata %u bytes\n",
                       session_id, hdr.len);
                if (!codec_opened) {
                    if (avcodec_open2(ctx, codec, NULL) < 0) {
                        fprintf(stderr, "[flac_worker] avcodec_open2 failed\n");
                        return 1;
                    }
                    codec_opened = 1;
                    printf("[flac_worker:%d] decoder opened with extradata\n", session_id);
                }
            } else {
                cr_consume(pkt_ring, pkt_buf, hdr.len, total);
            }
            continue;
        } else {
            if (hdr.len > 256 * 1024) {
                fprintf(stderr, "[flac_worker] oversized packet %u\n", hdr.len);
                cr_consume(pkt_ring, pkt_buf, hdr.len, total);
                continue;
            }
            cr_consume(pkt_ring, pkt_buf, hdr.len, total);

            if (!codec_opened) {
                if (avcodec_open2(ctx, codec, NULL) < 0) {
                    fprintf(stderr, "[flac_worker] avcodec_open2 failed\n");
                    return 1;
                }
                codec_opened = 1;
                printf("[flac_worker:%d] decoder opened (no extradata)\n", session_id);
            }

            pkt->data = pkt_buf;
            pkt->size = (int)hdr.len;
            pkt->pts  = hdr.pts_ns;

            int ret = avcodec_send_packet(ctx, pkt);
            if (ret < 0) {
                fprintf(stderr, "[flac_worker] send_packet err %d\n", ret);
                continue;
            }
        }

        /* Drain all available decoded frames */
        while (1) {
            int ret = avcodec_receive_frame(ctx, frame);
            if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF) break;
            if (ret < 0) {
                fprintf(stderr, "[flac_worker] receive_frame err %d\n", ret);
                break;
            }

            /* Init resampler on first frame */
            if (!swr) {
                AVChannelLayout stereo = AV_CHANNEL_LAYOUT_STEREO;
                swr_alloc_set_opts2(&swr,
                    &stereo,       AV_SAMPLE_FMT_S16, 48000,
                    &frame->ch_layout, frame->format, frame->sample_rate,
                    0, NULL);
                if (swr_init(swr) < 0) {
                    fprintf(stderr, "[flac_worker] swr_init failed\n");
                    swr_free(&swr);
                    swr = NULL;
                    av_frame_unref(frame);
                    continue;
                }
                printf("[flac_worker:%d] swr init: %dHz ch=%d → 48000Hz stereo S16LE\n",
                       session_id, frame->sample_rate, frame->ch_layout.nb_channels);
            }

            write_audio_frame(frm_ring, frame, swr, hdr.pts_ns);
            av_frame_unref(frame);
        }
    }

    printf("[flac_worker:%d] done\n", session_id);

    if (swr)   swr_free(&swr);
    av_frame_free(&frame);
    av_packet_free(&pkt);
    avcodec_free_context(&ctx);
    free(pkt_buf);
    close_ring(pkt_ring);
    close_ring(frm_ring);
    return 0;
}
