/*
 * decode_pcm.c — PCM pass-through "decoder"
 * Reads raw PCM packets from an input PacketRing, writes them to an output
 * PacketRing unchanged. This is the simplest possible decoder — used for
 * WAV files where the audio is already raw PCM.
 *
 * Usage:
 *   ./decode_pcm.x <input_ring_name> <output_ring_name> <clock_name>
 *
 * Orthogonal: speaks only PacketRing + PlaybackClock.
 *
 * Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
 */

#include "packetring.h"
#include "playbackclock.h"

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

/* Max packet payload (64KB, plenty for PCM chunks) */
#define MAX_PKT (64 * 1024)

int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Usage: decode_pcm.x <in_ring> <out_ring> <clock>\n");
        return 1;
    }

    const char *in_name  = argv[1];
    const char *out_name = argv[2];
    const char *clk_name = argv[3];

    fprintf(stderr, "[decode_pcm] in=%s out=%s clock=%s\n", in_name, out_name, clk_name);

    /* Open rings and clock */
    PacketRing in_ring, out_ring;
    PlaybackClock clk;

    if (!pr_open(&in_ring, in_name)) {
        fprintf(stderr, "[decode_pcm] failed to open input ring\n");
        return 1;
    }
    if (!pr_create(&out_ring, out_name, 4 * 1024 * 1024)) {
        fprintf(stderr, "[decode_pcm] failed to create output ring\n");
        return 1;
    }
    if (!pc_open(&clk, clk_name)) {
        fprintf(stderr, "[decode_pcm] failed to open clock\n");
        return 1;
    }

    uint8_t *buf = malloc(MAX_PKT);
    if (!buf) {
        fprintf(stderr, "[decode_pcm] malloc failed\n");
        return 1;
    }

    uint32_t pkt_size, pkt_flags;
    int64_t  pkt_pts;
    int running = 1;

    while (running) {
        /* Check clock state */
        int state = pc_get_state(&clk);
        if (state == PC_STOPPED) {
            fprintf(stderr, "[decode_pcm] clock STOPPED, exiting\n");
            break;
        }
        if (state == PC_SEEKING) {
            /* Flush: clear output ring */
            pr_reset(&out_ring);
            usleep(1000);
            continue;
        }
        if (state == PC_PAUSED) {
            usleep(1000);
            continue;
        }

        /* Try to read a packet */
        if (!pr_read(&in_ring, buf, &pkt_size, &pkt_pts, &pkt_flags)) {
            /* Check for EOF */
            if (pr_is_eof(&in_ring)) {
                pr_signal_eof(&out_ring);
                fprintf(stderr, "[decode_pcm] EOF received, exiting\n");
                break;
            }
            /* Ring empty, wait 1ms */
            usleep(1000);
            continue;
        }

        /* Pass through: write to output ring with same PTS/flags */
        while (!pr_write(&out_ring, buf, pkt_size, pkt_pts, pkt_flags)) {
            /* Output full, backpressure */
            if (pc_get_state(&clk) == PC_STOPPED) {
                running = 0;
                break;
            }
            usleep(500);
        }
    }

    free(buf);
    pr_close(&in_ring);
    /* Don't destroy output ring — presenter owns cleanup */
    pr_close(&out_ring);
    pc_close(&clk);

    fprintf(stderr, "[decode_pcm] done\n");
    return 0;
}
