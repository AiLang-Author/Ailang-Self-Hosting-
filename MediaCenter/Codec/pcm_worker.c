/*
 * pcm_worker.c
 * PCM/WAV codec worker — trivial passthrough, resamples to S16LE 48kHz stereo.
 *
 * Usage: pcm_worker <session_id>
 *
 * Reads raw PCM packets from:         /dev/shm/ailang_codec_<id>_pkt
 * Writes resampled S16LE PCM frames:  /dev/shm/ailang_codec_<id>_frm
 *
 * Expects CONFIG packet first with 8-byte header:
 *   [0-3] sample_rate  (uint32_t LE)
 *   [4-5] channels     (uint16_t LE)
 *   [6-7] bit_depth    (uint16_t LE)
 *
 * For S16LE 48kHz stereo input, this is a near-zero-cost passthrough.
 * For other formats, libswresample handles conversion.
 *
 * Build:
 *   gcc -O2 -o pcm_worker pcm_worker.c \
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

#include <libavutil/mem.h>
#include <libavutil/channel_layout.h>
#include <libavutil/samplefmt.h>
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
 * PCM config — parsed from CONFIG packet
 * ============================================================ */
typedef struct {
    uint32_t sample_rate;
    uint16_t channels;
    uint16_t bit_depth;
} PCMConfig;

/* Map bit_depth + signedness to AVSampleFormat */
static enum AVSampleFormat pcm_to_avfmt(uint16_t bit_depth) {
    switch (bit_depth) {
        case 8:  return AV_SAMPLE_FMT_U8;
        case 16: return AV_SAMPLE_FMT_S16;
        case 24: return AV_SAMPLE_FMT_S32;  /* 24-bit gets packed into 32 */
        case 32: return AV_SAMPLE_FMT_S32;
        default: return AV_SAMPLE_FMT_S16;
    }
}

/* ============================================================
 * Write resampled audio into frame ring
 * ============================================================ */
static int write_pcm_frame(CRRing *frm_ring, const uint8_t *pcm_data,
                            int sample_count, SwrContext *swr, int64_t pts_ns)
{
    /* Target: S16LE 48000Hz stereo */
    int out_samples = av_rescale_rnd(
        swr_get_delay(swr, 48000) + sample_count,
        48000, 48000, AV_ROUND_UP);
    if (out_samples < sample_count * 2)
        out_samples = sample_count * 2;

    int frame_bytes = out_samples * 2 * 2;  /* 2ch * 2 bytes */
    size_t desc_size = sizeof(CRFrameDesc) + frame_bytes;
    CRFrameDesc *desc = (CRFrameDesc *)malloc(desc_size);
    if (!desc) return -1;

    uint8_t *out_ptr = desc->data;
    const uint8_t *in_ptr = pcm_data;
    int converted = swr_convert(swr,
        &out_ptr, out_samples,
        &in_ptr, sample_count);
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
        fprintf(stderr, "usage: pcm_worker <session_id>\n");
        return 1;
    }

    int session_id = atoi(argv[1]);
    char pkt_path[64], frm_path[64];
    build_paths(session_id, pkt_path, frm_path);

    CRRing *pkt_ring = open_ring(pkt_path, 0);
    CRRing *frm_ring = open_ring(frm_path, 0);
    if (!pkt_ring || !frm_ring) {
        fprintf(stderr, "[pcm_worker:%d] ring open failed\n", session_id);
        return 1;
    }

    printf("[pcm_worker:%d] rings open\n", session_id);

    uint8_t *pkt_buf = (uint8_t *)malloc(256 * 1024);
    if (!pkt_buf) return 1;

    PCMConfig cfg = { .sample_rate = 44100, .channels = 2, .bit_depth = 16 };
    SwrContext *swr = NULL;


    printf("[pcm_worker:%d] entering loop\n", session_id);

    int running = 1;
    while (running) {
        CRRecord hdr;
        uint64_t total = cr_peek_header(pkt_ring, &hdr);
        if (total == 0) {
            struct timespec ts = { 0, 1000000 };
            nanosleep(&ts, NULL);
            continue;
        }

        if (hdr.flags & CR_FLAG_EOF) {
            running = 0;
            /* Flush any remaining samples in swr */
            if (swr) {
                CRFrameDesc *desc = (CRFrameDesc *)malloc(sizeof(CRFrameDesc) + 4096);
                if (desc) {
                    uint8_t *out_ptr = desc->data;
                    int flushed = swr_convert(swr, &out_ptr, 1024, NULL, 0);
                    if (flushed > 0) {
                        int actual_bytes = flushed * 2 * 2;
                        desc->width = 0; desc->height = 0; desc->pixel_fmt = 0;
                        desc->sample_count = (uint32_t)flushed;
                        desc->sample_rate = 48000;
                        desc->channels = 2;
                        desc->bit_depth = 16;
                        cr_write_record(frm_ring, desc,
                                        (uint32_t)(sizeof(CRFrameDesc) + actual_bytes),
                                        RTYPE_FRAME, 0, hdr.pts_ns);
                    }
                    free(desc);
                }
            }
            continue;
        }

        if (hdr.flags & CR_FLAG_CONFIG) {
            /* Parse PCM config: rate(4) channels(2) bit_depth(2) */
            if (hdr.len >= 8) {
                cr_consume(pkt_ring, pkt_buf, hdr.len, total);
                cfg.sample_rate = pkt_buf[0] | (pkt_buf[1]<<8)
                                | ((uint32_t)pkt_buf[2]<<16) | ((uint32_t)pkt_buf[3]<<24);
                cfg.channels    = pkt_buf[4] | (pkt_buf[5]<<8);
                cfg.bit_depth   = pkt_buf[6] | (pkt_buf[7]<<8);
                /* config received */
                printf("[pcm_worker:%d] config: %uHz %uch %ubit\n",
                       session_id, cfg.sample_rate, cfg.channels, cfg.bit_depth);

                /* Init/reinit resampler */
                if (swr) swr_free(&swr);
                AVChannelLayout stereo = AV_CHANNEL_LAYOUT_STEREO;
                AVChannelLayout src_layout;
                av_channel_layout_default(&src_layout, cfg.channels);
                swr_alloc_set_opts2(&swr,
                    &stereo,       AV_SAMPLE_FMT_S16, 48000,
                    &src_layout,   pcm_to_avfmt(cfg.bit_depth), cfg.sample_rate,
                    0, NULL);
                if (swr_init(swr) < 0) {
                    fprintf(stderr, "[pcm_worker] swr_init failed\n");
                    swr_free(&swr);
                    swr = NULL;
                }
            } else {
                cr_consume(pkt_ring, pkt_buf, hdr.len, total);
            }
            continue;
        }

        /* Normal PCM data packet */
        if (hdr.len > 256 * 1024) {
            fprintf(stderr, "[pcm_worker] oversized packet %u\n", hdr.len);
            cr_consume(pkt_ring, pkt_buf, hdr.len, total);
            continue;
        }
        cr_consume(pkt_ring, pkt_buf, hdr.len, total);

        if (!swr) {
            /* No config yet — init with defaults */
            AVChannelLayout stereo = AV_CHANNEL_LAYOUT_STEREO;
            AVChannelLayout src_layout;
            av_channel_layout_default(&src_layout, cfg.channels);
            swr_alloc_set_opts2(&swr,
                &stereo,       AV_SAMPLE_FMT_S16, 48000,
                &src_layout,   pcm_to_avfmt(cfg.bit_depth), cfg.sample_rate,
                0, NULL);
            if (swr_init(swr) < 0) {
                fprintf(stderr, "[pcm_worker] swr_init failed\n");
                swr_free(&swr);
                swr = NULL;
                continue;
            }
            printf("[pcm_worker:%d] swr init (default): %uHz %uch → 48000Hz stereo\n",
                   session_id, cfg.sample_rate, cfg.channels);
        }

        /* Calculate sample count from packet bytes */
        int bytes_per_sample = cfg.bit_depth / 8;
        if (bytes_per_sample == 0) bytes_per_sample = 2;
        int sample_count = (int)hdr.len / (bytes_per_sample * cfg.channels);

        write_pcm_frame(frm_ring, pkt_buf, sample_count, swr, hdr.pts_ns);
    }

    printf("[pcm_worker:%d] done\n", session_id);

    if (swr) swr_free(&swr);
    free(pkt_buf);
    close_ring(pkt_ring);
    close_ring(frm_ring);
    return 0;
}
