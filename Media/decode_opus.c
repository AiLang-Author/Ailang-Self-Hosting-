/*
 * decode_opus.c — Opus decoder shim using libopus
 * Reads Opus packets from an input PacketRing, decodes with libopus,
 * writes raw PCM (S16LE interleaved, 48kHz) to an output PacketRing.
 *
 * Opus always decodes to 48kHz. Channel count comes from the stream header
 * or is assumed stereo if not provided.
 *
 * Usage:
 *   ./decode_opus.x <input_ring_name> <output_ring_name> <clock_name>
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

#include <opus/opus.h>

/* Max compressed Opus packet (typically <4KB, but be safe) */
#define MAX_OPUS_PKT    (64 * 1024)
/* Max decoded PCM per frame: 120ms @ 48kHz stereo = 5760*2*2 = 23040 bytes */
#define MAX_FRAME_SAMPLES 5760
#define MAX_CHANNELS      2

int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Usage: decode_opus.x <in_ring> <out_ring> <clock>\n");
        return 1;
    }

    const char *in_name  = argv[1];
    const char *out_name = argv[2];
    const char *clk_name = argv[3];

    fprintf(stderr, "[decode_opus] in=%s out=%s clock=%s\n",
            in_name, out_name, clk_name);

    /* ------------------------------------------------------------------ */
    /* Create Opus decoder (48kHz stereo default)                         */
    /* ------------------------------------------------------------------ */
    int channels = MAX_CHANNELS;
    int err;
    OpusDecoder *decoder = opus_decoder_create(48000, channels, &err);
    if (err != OPUS_OK || !decoder) {
        fprintf(stderr, "[decode_opus] opus_decoder_create failed: %s\n",
                opus_strerror(err));
        return 1;
    }

    fprintf(stderr, "[decode_opus] Opus decoder created (48kHz, %d ch)\n",
            channels);

    /* ------------------------------------------------------------------ */
    /* Open rings and clock                                               */
    /* ------------------------------------------------------------------ */
    PacketRing in_ring, out_ring;
    PlaybackClock clk;

    if (!pr_open(&in_ring, in_name)) {
        fprintf(stderr, "[decode_opus] failed to open input ring\n");
        return 1;
    }
    if (!pr_create(&out_ring, out_name, 4 * 1024 * 1024)) {
        fprintf(stderr, "[decode_opus] failed to create output ring\n");
        return 1;
    }
    if (!pc_open(&clk, clk_name)) {
        fprintf(stderr, "[decode_opus] failed to open clock\n");
        return 1;
    }

    uint8_t *opus_buf = malloc(MAX_OPUS_PKT);
    int16_t *pcm_buf  = malloc(MAX_FRAME_SAMPLES * channels * sizeof(int16_t));
    if (!opus_buf || !pcm_buf) {
        fprintf(stderr, "[decode_opus] malloc failed\n");
        return 1;
    }

    uint32_t pkt_size, pkt_flags;
    int64_t  pkt_pts;
    int running = 1;
    uint64_t frames_decoded = 0;

    /* ------------------------------------------------------------------ */
    /* Main decode loop                                                   */
    /* ------------------------------------------------------------------ */
    while (running) {
        int state = pc_get_state(&clk);

        if (state == PC_STOPPED) {
            fprintf(stderr, "[decode_opus] clock STOPPED, exiting\n");
            break;
        }
        if (state == PC_SEEKING) {
            pr_reset(&out_ring);
            /* Reset decoder state (clears internal buffers/PLC) */
            opus_decoder_ctl(decoder, OPUS_RESET_STATE);
            usleep(1000);
            continue;
        }
        if (state == PC_PAUSED) {
            usleep(1000);
            continue;
        }

        /* Read an Opus packet from demuxer */
        if (!pr_read(&in_ring, opus_buf, &pkt_size, &pkt_pts, &pkt_flags)) {
            if (pr_is_eof(&in_ring)) {
                pr_signal_eof(&out_ring);
                fprintf(stderr, "[decode_opus] EOF, decoded %lu frames\n",
                        (unsigned long)frames_decoded);
                break;
            }
            usleep(1000);
            continue;
        }

        /* Skip OpusHead/OpusTags config packets (from MKV/WebM) */
        if (pkt_flags & PR_PKTFLAG_CONFIG) {
            /*
             * OpusHead (19 bytes): version, channels, pre-skip, rate, gain, map
             * We could parse channel count from byte 9 here, but for now
             * we assume stereo was set at init.
             */
            if (pkt_size >= 8 && memcmp(opus_buf, "OpusHead", 8) == 0) {
                if (pkt_size >= 10) {
                    int hdr_channels = opus_buf[9];
                    fprintf(stderr, "[decode_opus] OpusHead: %d channels\n",
                            hdr_channels);
                    /* If channel count differs, recreate decoder */
                    if (hdr_channels != channels && hdr_channels >= 1 &&
                        hdr_channels <= 2) {
                        opus_decoder_destroy(decoder);
                        channels = hdr_channels;
                        decoder = opus_decoder_create(48000, channels, &err);
                        if (err != OPUS_OK) {
                            fprintf(stderr, "[decode_opus] recreate failed\n");
                            return 1;
                        }
                        free(pcm_buf);
                        pcm_buf = malloc(MAX_FRAME_SAMPLES * channels *
                                         sizeof(int16_t));
                    }
                }
            }
            continue;
        }

        /* ------------------------------------------------------------ */
        /* Decode the Opus packet                                       */
        /* ------------------------------------------------------------ */
        int samples = opus_decode(decoder, opus_buf, (opus_int32)pkt_size,
                                  pcm_buf, MAX_FRAME_SAMPLES, 0);
        if (samples < 0) {
            fprintf(stderr, "[decode_opus] decode error: %s\n",
                    opus_strerror(samples));
            continue;
        }

        if (samples == 0) {
            continue;
        }

        /* S16LE interleaved: bytes = samples * channels * 2 */
        uint32_t pcm_bytes = (uint32_t)(samples * channels * sizeof(int16_t));

        /* Write decoded PCM to output ring */
        while (!pr_write(&out_ring, pcm_buf, pcm_bytes, pkt_pts, 0)) {
            if (pc_get_state(&clk) == PC_STOPPED) {
                running = 0;
                break;
            }
            usleep(500);
        }

        frames_decoded++;
        if ((frames_decoded % 500) == 0) {
            fprintf(stderr, "[decode_opus] %lu frames decoded\n",
                    (unsigned long)frames_decoded);
        }
    }

    /* ------------------------------------------------------------------ */
    /* Cleanup                                                            */
    /* ------------------------------------------------------------------ */
    opus_decoder_destroy(decoder);
    free(opus_buf);
    free(pcm_buf);
    pr_close(&in_ring);
    pr_close(&out_ring);
    pc_close(&clk);

    fprintf(stderr, "[decode_opus] done, %lu frames total\n",
            (unsigned long)frames_decoded);
    return 0;
}
