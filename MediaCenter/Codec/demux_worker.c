/*
 * demux_worker.c
 * Generic demuxer worker — wraps libavformat, speaks CodecRing protocol.
 *
 * Usage: demux_worker <session_id> <file_path>
 *
 * Discovers streams in the container, creates one packet ring per stream,
 * and pumps compressed packets into each ring. MediaCenter reads stream
 * descriptors from stdout (JSON, one line per stream) then forks the
 * appropriate codec worker for each.
 *
 * Rings created:
 *   /dev/shm/ailang_codec_<session_id + stream_index>_pkt
 *
 * Stream descriptor format (stdout, one JSON line per stream):
 *   {"stream":0, "codec":"h264", "type":"video", "width":1920, "height":1080}
 *   {"stream":1, "codec":"aac",  "type":"audio", "rate":44100, "channels":2}
 *
 * Signals:
 *   - Sends CR_FLAG_CONFIG as first packet per stream (codec extradata)
 *   - Sends CR_FLAG_KEYFRAME on keyframes
 *   - Sends CR_FLAG_EOF to all streams on container EOF
 *
 * Build:
 *   gcc -O2 -o demux_worker demux_worker.c \
 *       $(pkg-config --cflags --libs libavformat libavcodec libavutil)
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

#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/avutil.h>

#include "ailang_codec_abi.h"

#define MAX_STREAMS 8

/* ============================================================
 * Ring management
 * ============================================================ */
static CRRing *create_ring(const char *path) {
    int fd = open(path, O_RDWR | O_CREAT | O_TRUNC, 0666);
    if (fd < 0) { perror(path); return NULL; }
    size_t total = CR_HEADER_SIZE + CR_DEFAULT_SIZE;
    if (ftruncate(fd, total) < 0) { perror("ftruncate"); close(fd); return NULL; }
    void *ptr = mmap(NULL, total, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);
    if (ptr == MAP_FAILED) { perror("mmap"); return NULL; }

    /* Initialize ring header */
    CRRing *r = (CRRing *)ptr;
    r->magic     = CR_MAGIC;
    r->capacity  = CR_DEFAULT_SIZE;
    r->write_pos = 0;
    r->read_pos  = 0;
    return r;
}

static void close_ring(CRRing *r) {
    if (r) munmap(r, CR_HEADER_SIZE + CR_DEFAULT_SIZE);
}

/* ============================================================
 * Convert AVCodecID to short name string
 * ============================================================ */
static const char *codec_name(enum AVCodecID id) {
    switch (id) {
        case AV_CODEC_ID_H264:      return "h264";
        case AV_CODEC_ID_HEVC:      return "h265";
        case AV_CODEC_ID_VP9:       return "vp9";
        case AV_CODEC_ID_AV1:       return "av1";
        case AV_CODEC_ID_MP3:       return "mp3";
        case AV_CODEC_ID_AAC:       return "aac";
        case AV_CODEC_ID_OPUS:      return "opus";
        case AV_CODEC_ID_FLAC:      return "flac";
        case AV_CODEC_ID_VORBIS:    return "vorbis";
        case AV_CODEC_ID_PCM_S16LE: return "pcm_s16le";
        case AV_CODEC_ID_PCM_S24LE: return "pcm_s24le";
        case AV_CODEC_ID_PCM_S32LE: return "pcm_s32le";
        case AV_CODEC_ID_PCM_F32LE: return "pcm_f32le";
        default:                     return "unknown";
    }
}

/* ============================================================
 * Convert PTS from stream timebase to nanoseconds
 * ============================================================ */
static int64_t pts_to_ns(int64_t pts, AVRational tb) {
    if (pts == AV_NOPTS_VALUE) return 0;
    /* pts * tb.num / tb.den * 1e9 */
    return av_rescale_q(pts, tb, (AVRational){1, 1000000000});
}

/* ============================================================
 * Wait for ring space with backpressure
 * ============================================================ */
static int wait_for_space(CRRing *r, uint64_t needed) {
    int retries = 0;
    while (cr_write_avail(r) < needed) {
        struct timespec ts = { 0, 500000 };  /* 0.5ms */
        nanosleep(&ts, NULL);
        retries++;
        if (retries > 2000) {  /* 1 second timeout */
            fprintf(stderr, "[demux_worker] ring full timeout\n");
            return -1;
        }
    }
    return 0;
}

/* ============================================================
 * Main
 * ============================================================ */
int main(int argc, char *argv[]) {
    if (argc < 3) {
        fprintf(stderr, "usage: demux_worker <session_id> <file_path>\n");
        return 1;
    }

    int base_session_id = atoi(argv[1]);
    const char *file_path = argv[2];

    printf("[demux_worker:%d] opening %s\n", base_session_id, file_path);

    /* Open container */
    AVFormatContext *fmt_ctx = NULL;
    int ret = avformat_open_input(&fmt_ctx, file_path, NULL, NULL);
    if (ret < 0) {
        char errbuf[128];
        av_strerror(ret, errbuf, sizeof(errbuf));
        fprintf(stderr, "[demux_worker] avformat_open_input failed: %s\n", errbuf);
        return 1;
    }

    ret = avformat_find_stream_info(fmt_ctx, NULL);
    if (ret < 0) {
        fprintf(stderr, "[demux_worker] avformat_find_stream_info failed\n");
        avformat_close_input(&fmt_ctx);
        return 1;
    }

    /* Limit to MAX_STREAMS */
    int num_streams = fmt_ctx->nb_streams;
    if (num_streams > MAX_STREAMS) num_streams = MAX_STREAMS;

    /* Create per-stream packet rings and output descriptors */
    CRRing *rings[MAX_STREAMS] = {0};
    int stream_active[MAX_STREAMS] = {0};

    for (int i = 0; i < num_streams; i++) {
        AVStream *st = fmt_ctx->streams[i];
        AVCodecParameters *par = st->codecpar;

        /* Only handle audio and video */
        if (par->codec_type != AVMEDIA_TYPE_VIDEO &&
            par->codec_type != AVMEDIA_TYPE_AUDIO) {
            stream_active[i] = 0;
            continue;
        }

        /* Create packet ring for this stream */
        char ring_path[64];
        snprintf(ring_path, 64, "/dev/shm/ailang_codec_%d_pkt",
                 base_session_id + i);
        rings[i] = create_ring(ring_path);
        if (!rings[i]) {
            fprintf(stderr, "[demux_worker] failed to create ring for stream %d\n", i);
            stream_active[i] = 0;
            continue;
        }
        stream_active[i] = 1;

        /* Output stream descriptor to stdout (JSON) */
        if (par->codec_type == AVMEDIA_TYPE_VIDEO) {
            printf("{\"stream\":%d, \"codec\":\"%s\", \"type\":\"video\", "
                   "\"width\":%d, \"height\":%d, \"session_id\":%d}\n",
                   i, codec_name(par->codec_id),
                   par->width, par->height,
                   base_session_id + i);
        } else {
            printf("{\"stream\":%d, \"codec\":\"%s\", \"type\":\"audio\", "
                   "\"rate\":%d, \"channels\":%d, \"session_id\":%d}\n",
                   i, codec_name(par->codec_id),
                   par->sample_rate, par->ch_layout.nb_channels,
                   base_session_id + i);
        }
        fflush(stdout);

        /* Send codec extradata as CONFIG packet */
        if (par->extradata && par->extradata_size > 0) {
            uint32_t pad = (par->extradata_size + CR_RECORD_HDR) % 8;
            if (pad) pad = 8 - pad;
            uint64_t needed = (uint64_t)par->extradata_size + CR_RECORD_HDR + pad;
            if (wait_for_space(rings[i], needed) == 0) {
                cr_write_record(rings[i], par->extradata, par->extradata_size,
                                RTYPE_PACKET, CR_FLAG_CONFIG, 0);
            }
            printf("[demux_worker:%d] stream %d: sent %d bytes extradata\n",
                   base_session_id, i, par->extradata_size);
        }
    }

    /* Flush stdout so MediaCenter can read stream descriptors immediately */
    fflush(stdout);

    printf("[demux_worker:%d] %d streams, entering packet loop\n",
           base_session_id, num_streams);

    /* Packet read loop */
    AVPacket *pkt = av_packet_alloc();
    while (1) {
        ret = av_read_frame(fmt_ctx, pkt);
        if (ret < 0) {
            /* EOF or error */
            break;
        }

        int si = pkt->stream_index;
        if (si >= num_streams || !stream_active[si]) {
            av_packet_unref(pkt);
            continue;
        }

        /* Convert PTS to nanoseconds */
        int64_t pts_ns = pts_to_ns(pkt->pts, fmt_ctx->streams[si]->time_base);

        /* Determine flags */
        uint16_t flags = 0;
        if (pkt->flags & AV_PKT_FLAG_KEY)
            flags |= CR_FLAG_KEYFRAME;

        /* Write packet to ring with backpressure */
        uint32_t pad = (pkt->size + CR_RECORD_HDR) % 8;
        if (pad) pad = 8 - pad;
        uint64_t needed = (uint64_t)pkt->size + CR_RECORD_HDR + pad;

        if (wait_for_space(rings[si], needed) < 0) {
            fprintf(stderr, "[demux_worker] dropping packet for stream %d\n", si);
            av_packet_unref(pkt);
            continue;
        }

        cr_write_record(rings[si], pkt->data, pkt->size,
                        RTYPE_PACKET, flags, pts_ns);

        av_packet_unref(pkt);
    }

    /* Send EOF to all active streams */
    for (int i = 0; i < num_streams; i++) {
        if (!stream_active[i]) continue;
        /* Write zero-length EOF record */
        cr_write_record(rings[i], NULL, 0, RTYPE_PACKET, CR_FLAG_EOF, 0);
    }

    printf("[demux_worker:%d] EOF — sent to all streams\n", base_session_id);

    /* Cleanup */
    av_packet_free(&pkt);
    avformat_close_input(&fmt_ctx);
    for (int i = 0; i < num_streams; i++) {
        close_ring(rings[i]);
    }

    printf("[demux_worker:%d] done\n", base_session_id);
    return 0;
}
