/*
 * resample_audio.c — Audio sample rate converter
 * Reads S16LE interleaved PCM from an input PacketRing, resamples to a
 * target sample rate using linear interpolation, writes to output PacketRing.
 *
 * Sits between a decoder and the presenter/mixer in the pipeline:
 *   decoder → [dec_audio ring] → resample_audio → [rsp_audio ring] → presenter
 *
 * Linear interpolation is used for simplicity. For higher quality, this
 * could be replaced with sinc-based resampling (libsamplerate).
 *
 * Usage:
 *   ./resample_audio.x <in_ring> <out_ring> <clock> <in_rate> <out_rate> <channels>
 *
 * Example:
 *   ./resample_audio.x dec_audio_0 rsp_audio_0 clock_0 44100 48000 2
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

/* Max input/output buffer sizes */
#define MAX_IN_SAMPLES   (48000)  /* 1 second at 48kHz */
#define MAX_OUT_SAMPLES  (96000)  /* generous output buffer */
#define OUT_RING_CAP     (4 * 1024 * 1024)

/*
 * Linear interpolation resampler.
 *
 * For each output sample at position out_i:
 *   in_pos = out_i * in_rate / out_rate  (fractional)
 *   sample = lerp(input[floor(in_pos)], input[ceil(in_pos)], frac)
 *
 * Uses fixed-point (24.8) for the fractional position to avoid floats.
 *
 * Parameters:
 *   in:       input S16LE interleaved buffer
 *   in_frames: number of input frames (samples per channel)
 *   out:      output buffer (must be large enough)
 *   in_rate:  input sample rate
 *   out_rate: output sample rate
 *   channels: number of channels
 *
 * Returns number of output frames written.
 */
static int resample_linear(
    const int16_t *in, int in_frames,
    int16_t *out,
    int in_rate, int out_rate,
    int channels)
{
    if (in_rate == out_rate) {
        /* No conversion needed — passthrough */
        memcpy(out, in, in_frames * channels * sizeof(int16_t));
        return in_frames;
    }

    /* Calculate number of output frames:
     * out_frames = in_frames * out_rate / in_rate  (rounded up) */
    int out_frames = (int)(((int64_t)in_frames * out_rate + in_rate - 1) / in_rate);

    /* Fixed-point step: how much to advance in input per output sample
     * step = in_rate * 256 / out_rate  (8 bits fractional) */
    int64_t step_fp = ((int64_t)in_rate << 8) / out_rate;

    int64_t pos_fp = 0;  /* Current position in input (fixed-point 24.8) */

    for (int i = 0; i < out_frames; i++) {
        int idx0 = (int)(pos_fp >> 8);           /* Integer part */
        int frac = (int)(pos_fp & 0xFF);          /* Fractional part (0-255) */
        int idx1 = idx0 + 1;

        /* Clamp to input bounds */
        if (idx0 >= in_frames) idx0 = in_frames - 1;
        if (idx1 >= in_frames) idx1 = in_frames - 1;

        for (int ch = 0; ch < channels; ch++) {
            int32_t s0 = in[idx0 * channels + ch];
            int32_t s1 = in[idx1 * channels + ch];

            /* Linear interpolation: out = s0 + (s1 - s0) * frac / 256 */
            int32_t val = s0 + ((s1 - s0) * frac) / 256;

            /* Clamp to int16 range */
            if (val > 32767)  val = 32767;
            if (val < -32768) val = -32768;

            out[i * channels + ch] = (int16_t)val;
        }

        pos_fp += step_fp;
    }

    return out_frames;
}

int main(int argc, char *argv[]) {
    if (argc < 7) {
        fprintf(stderr, "Usage: resample_audio.x "
                "<in_ring> <out_ring> <clock> <in_rate> <out_rate> <channels>\n");
        return 1;
    }

    const char *in_name  = argv[1];
    const char *out_name = argv[2];
    const char *clk_name = argv[3];
    int in_rate   = atoi(argv[4]);
    int out_rate  = atoi(argv[5]);
    int channels  = atoi(argv[6]);

    fprintf(stderr, "[resample] in=%s out=%s clock=%s %dHz->%dHz %dch\n",
            in_name, out_name, clk_name, in_rate, out_rate, channels);

    if (in_rate <= 0 || out_rate <= 0 || channels <= 0 || channels > 8) {
        fprintf(stderr, "[resample] invalid parameters\n");
        return 1;
    }

    /* Passthrough mode if rates match */
    int passthrough = (in_rate == out_rate);
    if (passthrough) {
        fprintf(stderr, "[resample] rates match, running in passthrough mode\n");
    }

    /* ------------------------------------------------------------------ */
    /* Open rings and clock                                               */
    /* ------------------------------------------------------------------ */
    PacketRing in_ring, out_ring;
    PlaybackClock clk;

    if (!pr_open(&in_ring, in_name)) {
        fprintf(stderr, "[resample] failed to open input ring\n");
        return 1;
    }
    if (!pr_create(&out_ring, out_name, OUT_RING_CAP)) {
        fprintf(stderr, "[resample] failed to create output ring\n");
        return 1;
    }
    if (!pc_open(&clk, clk_name)) {
        fprintf(stderr, "[resample] failed to open clock\n");
        return 1;
    }

    /* Allocate buffers */
    size_t in_buf_bytes  = MAX_IN_SAMPLES  * channels * sizeof(int16_t);
    size_t out_buf_bytes = MAX_OUT_SAMPLES * channels * sizeof(int16_t);
    int16_t *in_buf  = malloc(in_buf_bytes);
    int16_t *out_buf = malloc(out_buf_bytes);
    /* Raw packet buffer for ring reads */
    uint8_t *pkt_buf = malloc(in_buf_bytes);

    if (!in_buf || !out_buf || !pkt_buf) {
        fprintf(stderr, "[resample] malloc failed\n");
        return 1;
    }

    uint32_t pkt_size, pkt_flags;
    int64_t  pkt_pts;
    int running = 1;
    uint64_t packets_processed = 0;

    /* ------------------------------------------------------------------ */
    /* Main processing loop                                               */
    /* ------------------------------------------------------------------ */
    while (running) {
        int state = pc_get_state(&clk);

        if (state == PC_STOPPED) {
            fprintf(stderr, "[resample] clock STOPPED, exiting\n");
            break;
        }
        if (state == PC_SEEKING) {
            pr_reset(&out_ring);
            usleep(1000);
            continue;
        }
        if (state == PC_PAUSED) {
            usleep(1000);
            continue;
        }

        /* Read a PCM packet from the decoder */
        if (!pr_read(&in_ring, pkt_buf, &pkt_size, &pkt_pts, &pkt_flags)) {
            if (pr_is_eof(&in_ring)) {
                pr_signal_eof(&out_ring);
                fprintf(stderr, "[resample] EOF, processed %lu packets\n",
                        (unsigned long)packets_processed);
                break;
            }
            usleep(1000);
            continue;
        }

        /* Forward CONFIG packets as-is (codec headers, etc.) */
        if (pkt_flags & PR_PKTFLAG_CONFIG) {
            while (!pr_write(&out_ring, pkt_buf, pkt_size, pkt_pts, pkt_flags)) {
                if (pc_get_state(&clk) == PC_STOPPED) {
                    running = 0;
                    break;
                }
                usleep(500);
            }
            continue;
        }

        /* Calculate number of input frames */
        int in_frames = pkt_size / (channels * sizeof(int16_t));
        if (in_frames <= 0 || in_frames > MAX_IN_SAMPLES) {
            continue;
        }

        /* Copy to aligned input buffer */
        memcpy(in_buf, pkt_buf, in_frames * channels * sizeof(int16_t));

        /* Resample */
        int out_frames;
        if (passthrough) {
            memcpy(out_buf, in_buf, in_frames * channels * sizeof(int16_t));
            out_frames = in_frames;
        } else {
            out_frames = resample_linear(in_buf, in_frames, out_buf,
                                         in_rate, out_rate, channels);
        }

        /* Write resampled PCM to output ring */
        uint32_t out_bytes = out_frames * channels * sizeof(int16_t);
        while (!pr_write(&out_ring, out_buf, out_bytes, pkt_pts, 0)) {
            if (pc_get_state(&clk) == PC_STOPPED) {
                running = 0;
                break;
            }
            usleep(500);
        }

        packets_processed++;
        if ((packets_processed % 1000) == 0) {
            fprintf(stderr, "[resample] %lu packets (%d->%d Hz)\n",
                    (unsigned long)packets_processed, in_rate, out_rate);
        }
    }

    /* ------------------------------------------------------------------ */
    /* Cleanup                                                            */
    /* ------------------------------------------------------------------ */
    free(in_buf);
    free(out_buf);
    free(pkt_buf);
    pr_close(&in_ring);
    pr_close(&out_ring);
    pc_close(&clk);

    fprintf(stderr, "[resample] done, %lu packets total\n",
            (unsigned long)packets_processed);
    return 0;
}
