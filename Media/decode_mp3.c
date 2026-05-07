/*
 * decode_mp3.c — MP3 decoder shim using libmpg123
 * Reads MP3 frames from an input PacketRing, decodes with mpg123,
 * writes raw PCM (S16LE interleaved) to an output PacketRing.
 *
 * Usage:
 *   ./decode_mp3.x <input_ring_name> <output_ring_name> <clock_name>
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

#include <mpg123.h>

/* Max compressed MP3 frame (MPEG frames are small, ~1.5KB typical) */
#define MAX_MP3_PKT   (64 * 1024)
/* Max decoded PCM per frame: 1152 samples * 2ch * 2 bytes = 4608 */
#define MAX_PCM_FRAME (32 * 1024)

int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Usage: decode_mp3.x <in_ring> <out_ring> <clock>\n");
        return 1;
    }

    const char *in_name  = argv[1];
    const char *out_name = argv[2];
    const char *clk_name = argv[3];

    fprintf(stderr, "[decode_mp3] in=%s out=%s clock=%s\n",
            in_name, out_name, clk_name);

    /* ------------------------------------------------------------------ */
    /* Initialize mpg123 library and create decoder handle                */
    /* ------------------------------------------------------------------ */
    int err = mpg123_init();
    if (err != MPG123_OK) {
        fprintf(stderr, "[decode_mp3] mpg123_init failed\n");
        return 1;
    }

    mpg123_handle *decoder = mpg123_new(NULL, &err);
    if (!decoder) {
        fprintf(stderr, "[decode_mp3] mpg123_new failed: %s\n",
                mpg123_plain_strerror(err));
        mpg123_exit();
        return 1;
    }

    /* Configure for feeding mode (we push data, not open a file) */
    err = mpg123_open_feed(decoder);
    if (err != MPG123_OK) {
        fprintf(stderr, "[decode_mp3] mpg123_open_feed failed: %s\n",
                mpg123_strerror(decoder));
        mpg123_delete(decoder);
        mpg123_exit();
        return 1;
    }

    /* Force S16LE output */
    mpg123_param(decoder, MPG123_ADD_FLAGS, MPG123_FORCE_STEREO, 0.0);
    mpg123_format_none(decoder);
    /* Accept common sample rates in S16 stereo */
    long rates[] = {8000, 11025, 16000, 22050, 32000, 44100, 48000};
    for (int i = 0; i < 7; i++) {
        mpg123_format(decoder, rates[i], MPG123_STEREO, MPG123_ENC_SIGNED_16);
    }

    fprintf(stderr, "[decode_mp3] mpg123 decoder initialized (feed mode)\n");

    /* ------------------------------------------------------------------ */
    /* Open rings and clock                                               */
    /* ------------------------------------------------------------------ */
    PacketRing in_ring, out_ring;
    PlaybackClock clk;

    if (!pr_open(&in_ring, in_name)) {
        fprintf(stderr, "[decode_mp3] failed to open input ring\n");
        return 1;
    }
    if (!pr_create(&out_ring, out_name, 4 * 1024 * 1024)) {
        fprintf(stderr, "[decode_mp3] failed to create output ring\n");
        return 1;
    }
    if (!pc_open(&clk, clk_name)) {
        fprintf(stderr, "[decode_mp3] failed to open clock\n");
        return 1;
    }

    uint8_t *mp3_buf = malloc(MAX_MP3_PKT);
    uint8_t *pcm_buf = malloc(MAX_PCM_FRAME);
    if (!mp3_buf || !pcm_buf) {
        fprintf(stderr, "[decode_mp3] malloc failed\n");
        return 1;
    }

    uint32_t pkt_size, pkt_flags;
    int64_t  pkt_pts;
    int running = 1;
    int format_logged = 0;
    uint64_t frames_decoded = 0;

    /* ------------------------------------------------------------------ */
    /* Main decode loop                                                   */
    /* ------------------------------------------------------------------ */
    while (running) {
        int state = pc_get_state(&clk);

        if (state == PC_STOPPED) {
            fprintf(stderr, "[decode_mp3] clock STOPPED, exiting\n");
            break;
        }
        if (state == PC_SEEKING) {
            pr_reset(&out_ring);
            /* Reset mpg123 feed state */
            mpg123_close(decoder);
            mpg123_open_feed(decoder);
            format_logged = 0;
            usleep(1000);
            continue;
        }
        if (state == PC_PAUSED) {
            usleep(1000);
            continue;
        }

        /* Read an MP3 frame from demuxer */
        if (!pr_read(&in_ring, mp3_buf, &pkt_size, &pkt_pts, &pkt_flags)) {
            if (pr_is_eof(&in_ring)) {
                /* Drain any remaining buffered PCM */
                size_t done = 0;
                while (mpg123_read(decoder, pcm_buf, MAX_PCM_FRAME, &done)
                       == MPG123_OK && done > 0) {
                    while (!pr_write(&out_ring, pcm_buf, (uint32_t)done,
                                     pkt_pts, 0)) {
                        if (pc_get_state(&clk) == PC_STOPPED) {
                            running = 0;
                            break;
                        }
                        usleep(500);
                    }
                }
                pr_signal_eof(&out_ring);
                fprintf(stderr, "[decode_mp3] EOF, decoded %lu frames\n",
                        (unsigned long)frames_decoded);
                break;
            }
            usleep(1000);
            continue;
        }

        /* ------------------------------------------------------------ */
        /* Feed compressed data to mpg123                               */
        /* ------------------------------------------------------------ */
        err = mpg123_feed(decoder, mp3_buf, pkt_size);
        if (err != MPG123_OK) {
            fprintf(stderr, "[decode_mp3] feed error: %s\n",
                    mpg123_strerror(decoder));
            continue;
        }

        /* ------------------------------------------------------------ */
        /* Read decoded PCM out of mpg123                               */
        /* ------------------------------------------------------------ */
        size_t done = 0;
        int ret;

        while ((ret = mpg123_read(decoder, pcm_buf, MAX_PCM_FRAME, &done))
               == MPG123_OK || ret == MPG123_NEW_FORMAT) {

            if (ret == MPG123_NEW_FORMAT && !format_logged) {
                long rate;
                int ch, enc;
                mpg123_getformat(decoder, &rate, &ch, &enc);
                fprintf(stderr, "[decode_mp3] format: %ld Hz, %d ch, enc=%d\n",
                        rate, ch, enc);
                format_logged = 1;

                /* If mpg123_read returned NEW_FORMAT with no data, read again */
                if (done == 0) {
                    continue;
                }
            }

            if (done == 0) {
                break;
            }

            /* Write decoded PCM to output ring */
            while (!pr_write(&out_ring, pcm_buf, (uint32_t)done,
                             pkt_pts, 0)) {
                if (pc_get_state(&clk) == PC_STOPPED) {
                    running = 0;
                    break;
                }
                usleep(500);
            }

            frames_decoded++;
            done = 0;
        }

        if ((frames_decoded % 500) == 0 && frames_decoded > 0) {
            fprintf(stderr, "[decode_mp3] %lu frames decoded\n",
                    (unsigned long)frames_decoded);
        }
    }

    /* ------------------------------------------------------------------ */
    /* Cleanup                                                            */
    /* ------------------------------------------------------------------ */
    mpg123_close(decoder);
    mpg123_delete(decoder);
    mpg123_exit();

    free(mp3_buf);
    free(pcm_buf);
    pr_close(&in_ring);
    pr_close(&out_ring);
    pc_close(&clk);

    fprintf(stderr, "[decode_mp3] done, %lu frames total\n",
            (unsigned long)frames_decoded);
    return 0;
}
