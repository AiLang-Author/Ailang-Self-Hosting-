/*
 * decode_flac.c — FLAC decoder shim using libFLAC
 * Reads FLAC stream data from an input PacketRing, decodes with libFLAC,
 * writes raw PCM (S16LE interleaved) to an output PacketRing.
 *
 * Uses stream decoder with custom callbacks. The read callback pulls data
 * from the input PacketRing (blocking if necessary). The write callback
 * pushes decoded PCM to the output PacketRing.
 *
 * The demuxer sends the FLAC stream header (fLaC magic + metadata blocks)
 * as a CONFIG-flagged packet first, then raw FLAC data chunks.
 * On seek, the demuxer re-sends the header as CONFIG, then new data.
 * The decoder saves the header and pre-fills it on re-init.
 *
 * Usage:
 *   ./decode_flac.x <input_ring_name> <output_ring_name> <clock_name>
 *
 * Orthogonal: speaks only PacketRing + PlaybackClock.
 *
 * Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
 */

#include "packetring.h"
#include "playbackclock.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <FLAC/stream_decoder.h>

/* Read buffer for ring data */
#define READ_BUF_SIZE   (256 * 1024)
/* Saved metadata for seek re-init */
#define METADATA_MAX    (64 * 1024)

typedef struct {
    /* Ring buffer for feeding libFLAC */
    uint8_t     *buf;
    size_t       buf_size;
    size_t       buf_pos;

    /* Saved FLAC header (fLaC + metadata blocks) for seek re-init */
    uint8_t     *metadata_buf;
    size_t       metadata_size;

    /* Ring/clock references */
    PacketRing  *in_ring;
    PacketRing  *out_ring;
    PlaybackClock *clk;

    /* Current PTS from most recent packet */
    int64_t      current_pts;

    /* State flags */
    int          seeking;
    int          abort_flag;

    /* Stream info */
    int          channels;
    int          sample_rate;
    int          bps;

    /* Stats */
    uint64_t     frames_decoded;
} FlacContext;

/* ------------------------------------------------------------------ */
/* libFLAC read callback — pulls data from input PacketRing            */
/* ------------------------------------------------------------------ */
static FLAC__StreamDecoderReadStatus flac_read_cb(
    const FLAC__StreamDecoder *dec,
    FLAC__byte buffer[],
    size_t *bytes,
    void *client_data)
{
    (void)dec;
    FlacContext *ctx = (FlacContext *)client_data;

    while (1) {
        /* Serve from internal buffer first */
        size_t avail = ctx->buf_size - ctx->buf_pos;
        if (avail > 0) {
            size_t n = (*bytes < avail) ? *bytes : avail;
            memcpy(buffer, ctx->buf + ctx->buf_pos, n);
            ctx->buf_pos += n;
            *bytes = n;
            return FLAC__STREAM_DECODER_READ_STATUS_CONTINUE;
        }

        /* Buffer empty — check state */
        int state = pc_get_state(ctx->clk);

        if (state == PC_STOPPED || ctx->abort_flag) {
            *bytes = 0;
            return FLAC__STREAM_DECODER_READ_STATUS_ABORT;
        }

        if (state == PC_SEEKING) {
            ctx->seeking = 1;
            *bytes = 0;
            return FLAC__STREAM_DECODER_READ_STATUS_ABORT;
        }

        if (state == PC_PAUSED) {
            usleep(1000);
            continue;
        }

        /* Read from input ring */
        uint32_t pkt_size, pkt_flags;
        int64_t  pkt_pts;

        if (pr_read(ctx->in_ring, ctx->buf, &pkt_size, &pkt_pts, &pkt_flags)) {
            ctx->buf_size = pkt_size;
            ctx->buf_pos = 0;
            ctx->current_pts = pkt_pts;

            /* Save CONFIG data (FLAC header) for seek re-init */
            if ((pkt_flags & PR_PKTFLAG_CONFIG) && pkt_size <= METADATA_MAX) {
                memcpy(ctx->metadata_buf, ctx->buf, pkt_size);
                ctx->metadata_size = pkt_size;
            }

            continue;  /* Now serve from buffer */
        }

        /* Check for EOF */
        if (pr_is_eof(ctx->in_ring)) {
            *bytes = 0;
            return FLAC__STREAM_DECODER_READ_STATUS_END_OF_STREAM;
        }

        /* No data yet — wait briefly */
        usleep(1000);
    }
}

/* ------------------------------------------------------------------ */
/* libFLAC write callback — pushes decoded PCM to output PacketRing    */
/* ------------------------------------------------------------------ */
static FLAC__StreamDecoderWriteStatus flac_write_cb(
    const FLAC__StreamDecoder *dec,
    const FLAC__Frame *frame,
    const FLAC__int32 *const buffer[],
    void *client_data)
{
    (void)dec;
    FlacContext *ctx = (FlacContext *)client_data;

    uint32_t samples = frame->header.blocksize;
    int channels = frame->header.channels;
    int bps = frame->header.bits_per_sample;

    /* Convert to S16LE interleaved */
    uint32_t pcm_bytes = samples * channels * sizeof(int16_t);
    int16_t *pcm = malloc(pcm_bytes);
    if (!pcm) return FLAC__STREAM_DECODER_WRITE_STATUS_ABORT;

    int shift_down = (bps > 16) ? (bps - 16) : 0;
    int shift_up   = (bps < 16) ? (16 - bps) : 0;

    for (uint32_t i = 0; i < samples; i++) {
        for (int ch = 0; ch < channels; ch++) {
            int32_t s = buffer[ch][i];
            if (shift_down > 0) s >>= shift_down;
            if (shift_up > 0)   s <<= shift_up;
            if (s > 32767)  s = 32767;
            if (s < -32768) s = -32768;
            pcm[i * channels + ch] = (int16_t)s;
        }
    }

    /* Write to output ring with backpressure */
    while (!pr_write(ctx->out_ring, pcm, pcm_bytes, ctx->current_pts, 0)) {
        if (pc_get_state(ctx->clk) == PC_STOPPED) {
            free(pcm);
            return FLAC__STREAM_DECODER_WRITE_STATUS_ABORT;
        }
        usleep(500);
    }

    free(pcm);
    ctx->frames_decoded++;

    if ((ctx->frames_decoded % 500) == 0) {
        fprintf(stderr, "[decode_flac] %lu frames decoded\n",
                (unsigned long)ctx->frames_decoded);
    }

    return FLAC__STREAM_DECODER_WRITE_STATUS_CONTINUE;
}

/* ------------------------------------------------------------------ */
/* libFLAC metadata callback — extract stream info                     */
/* ------------------------------------------------------------------ */
static void flac_metadata_cb(
    const FLAC__StreamDecoder *dec,
    const FLAC__StreamMetadata *metadata,
    void *client_data)
{
    (void)dec;
    FlacContext *ctx = (FlacContext *)client_data;

    if (metadata->type == FLAC__METADATA_TYPE_STREAMINFO) {
        ctx->channels    = metadata->data.stream_info.channels;
        ctx->sample_rate = metadata->data.stream_info.sample_rate;
        ctx->bps         = metadata->data.stream_info.bits_per_sample;
        fprintf(stderr, "[decode_flac] STREAMINFO: %d ch, %d Hz, %d bps, "
                "%lu total samples\n",
                ctx->channels, ctx->sample_rate, ctx->bps,
                (unsigned long)metadata->data.stream_info.total_samples);
    }
}

/* ------------------------------------------------------------------ */
/* libFLAC error callback                                              */
/* ------------------------------------------------------------------ */
static void flac_error_cb(
    const FLAC__StreamDecoder *dec,
    FLAC__StreamDecoderErrorStatus status,
    void *client_data)
{
    (void)dec;
    (void)client_data;
    fprintf(stderr, "[decode_flac] decode error: %s\n",
            FLAC__StreamDecoderErrorStatusString[status]);
}

/* ------------------------------------------------------------------ */
/* Create and init a fresh FLAC decoder                                */
/* ------------------------------------------------------------------ */
static FLAC__StreamDecoder *create_decoder(FlacContext *ctx) {
    FLAC__StreamDecoder *decoder = FLAC__stream_decoder_new();
    if (!decoder) {
        fprintf(stderr, "[decode_flac] FLAC__stream_decoder_new failed\n");
        return NULL;
    }

    FLAC__StreamDecoderInitStatus init_status =
        FLAC__stream_decoder_init_stream(
            decoder,
            flac_read_cb,
            NULL,   /* seek */
            NULL,   /* tell */
            NULL,   /* length */
            NULL,   /* eof */
            flac_write_cb,
            flac_metadata_cb,
            flac_error_cb,
            ctx
        );

    if (init_status != FLAC__STREAM_DECODER_INIT_STATUS_OK) {
        fprintf(stderr, "[decode_flac] init failed: %s\n",
                FLAC__StreamDecoderInitStatusString[init_status]);
        FLAC__stream_decoder_delete(decoder);
        return NULL;
    }

    return decoder;
}

/* ================================================================== */
/* MAIN                                                                */
/* ================================================================== */
int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Usage: decode_flac.x <in_ring> <out_ring> <clock>\n");
        return 1;
    }

    const char *in_name  = argv[1];
    const char *out_name = argv[2];
    const char *clk_name = argv[3];

    fprintf(stderr, "[decode_flac] in=%s out=%s clock=%s\n",
            in_name, out_name, clk_name);

    /* ------------------------------------------------------------------ */
    /* Open rings and clock                                               */
    /* ------------------------------------------------------------------ */
    PacketRing in_ring, out_ring;
    PlaybackClock clk;

    if (!pr_open(&in_ring, in_name)) {
        fprintf(stderr, "[decode_flac] failed to open input ring\n");
        return 1;
    }
    if (!pr_create(&out_ring, out_name, 4 * 1024 * 1024)) {
        fprintf(stderr, "[decode_flac] failed to create output ring\n");
        return 1;
    }
    if (!pc_open(&clk, clk_name)) {
        fprintf(stderr, "[decode_flac] failed to open clock\n");
        return 1;
    }

    /* ------------------------------------------------------------------ */
    /* Set up FLAC context                                                */
    /* ------------------------------------------------------------------ */
    FlacContext ctx;
    memset(&ctx, 0, sizeof(ctx));

    ctx.buf          = malloc(READ_BUF_SIZE);
    ctx.metadata_buf = malloc(METADATA_MAX);
    ctx.in_ring      = &in_ring;
    ctx.out_ring     = &out_ring;
    ctx.clk          = &clk;

    if (!ctx.buf || !ctx.metadata_buf) {
        fprintf(stderr, "[decode_flac] malloc failed\n");
        return 1;
    }

    /* ------------------------------------------------------------------ */
    /* Create FLAC decoder                                                */
    /* ------------------------------------------------------------------ */
    FLAC__StreamDecoder *decoder = create_decoder(&ctx);
    if (!decoder) return 1;

    fprintf(stderr, "[decode_flac] FLAC decoder initialized\n");

    /* ------------------------------------------------------------------ */
    /* Main loop — process_until_end_of_stream handles everything via     */
    /* callbacks. We only re-enter when seek causes an abort.             */
    /* ------------------------------------------------------------------ */
    int running = 1;

    while (running) {
        /* Process the FLAC stream — blocks until EOF or abort */
        FLAC__stream_decoder_process_until_end_of_stream(decoder);

        /* Check why we exited */
        if (ctx.seeking) {
            /* Seek: re-create decoder, pre-fill with saved metadata */
            ctx.seeking = 0;
            FLAC__stream_decoder_finish(decoder);
            FLAC__stream_decoder_delete(decoder);

            pr_reset(&out_ring);

            /* Pre-fill buffer with saved FLAC header so decoder can re-init */
            if (ctx.metadata_size > 0) {
                memcpy(ctx.buf, ctx.metadata_buf, ctx.metadata_size);
                ctx.buf_size = ctx.metadata_size;
                ctx.buf_pos = 0;
            } else {
                ctx.buf_size = 0;
                ctx.buf_pos = 0;
            }

            decoder = create_decoder(&ctx);
            if (!decoder) {
                fprintf(stderr, "[decode_flac] failed to re-create decoder\n");
                break;
            }
            fprintf(stderr, "[decode_flac] seek: decoder re-initialized\n");
            continue;
        }

        /* EOF or STOPPED — we're done */
        pr_signal_eof(&out_ring);
        fprintf(stderr, "[decode_flac] finished, decoded %lu frames\n",
                (unsigned long)ctx.frames_decoded);
        running = 0;
    }

    /* ------------------------------------------------------------------ */
    /* Cleanup                                                            */
    /* ------------------------------------------------------------------ */
    if (decoder) {
        FLAC__stream_decoder_finish(decoder);
        FLAC__stream_decoder_delete(decoder);
    }
    free(ctx.buf);
    free(ctx.metadata_buf);
    pr_close(&in_ring);
    pr_close(&out_ring);
    pc_close(&clk);

    fprintf(stderr, "[decode_flac] done, %lu frames total\n",
            (unsigned long)ctx.frames_decoded);
    return 0;
}
