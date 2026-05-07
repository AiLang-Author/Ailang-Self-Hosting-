/*
 * decode_aac.c — AAC decoder shim using libfaad2
 * Reads AAC frames from an input PacketRing, decodes with faad2,
 * writes raw PCM (S16LE interleaved) to an output PacketRing.
 *
 * Usage:
 *   ./decode_aac.x <input_ring_name> <output_ring_name> <clock_name>
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

#include <neaacdec.h>

/* Max compressed AAC frame (64KB is generous) */
#define MAX_AAC_PKT   (64 * 1024)
/* Max decoded PCM per frame: 2048 samples * 8 channels * 2 bytes = 32KB */
#define MAX_PCM_FRAME (64 * 1024)

int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Usage: decode_aac.x <in_ring> <out_ring> <clock>\n");
        return 1;
    }

    const char *in_name  = argv[1];
    const char *out_name = argv[2];
    const char *clk_name = argv[3];

    fprintf(stderr, "[decode_aac] in=%s out=%s clock=%s\n",
            in_name, out_name, clk_name);

    /* ------------------------------------------------------------------ */
    /* Create faad2 decoder                                               */
    /* ------------------------------------------------------------------ */
    NeAACDecHandle decoder = NeAACDecOpen();
    if (!decoder) {
        fprintf(stderr, "[decode_aac] NeAACDecOpen failed\n");
        return 1;
    }

    /* Configure for 16-bit output */
    NeAACDecConfigurationPtr conf = NeAACDecGetCurrentConfiguration(decoder);
    conf->outputFormat = FAAD_FMT_16BIT;  /* S16LE interleaved */
    conf->downMatrix = 1;                  /* Downmix to stereo if >2ch */
    NeAACDecSetConfiguration(decoder, conf);

    fprintf(stderr, "[decode_aac] faad2 decoder opened\n");

    /* ------------------------------------------------------------------ */
    /* Open rings and clock                                               */
    /* ------------------------------------------------------------------ */
    PacketRing in_ring, out_ring;
    PlaybackClock clk;

    if (!pr_open(&in_ring, in_name)) {
        fprintf(stderr, "[decode_aac] failed to open input ring\n");
        return 1;
    }
    if (!pr_create(&out_ring, out_name, 4 * 1024 * 1024)) {
        fprintf(stderr, "[decode_aac] failed to create output ring\n");
        return 1;
    }
    if (!pc_open(&clk, clk_name)) {
        fprintf(stderr, "[decode_aac] failed to open clock\n");
        return 1;
    }

    uint8_t *aac_buf = malloc(MAX_AAC_PKT);
    if (!aac_buf) {
        fprintf(stderr, "[decode_aac] malloc failed\n");
        return 1;
    }

    uint32_t pkt_size, pkt_flags;
    int64_t  pkt_pts;
    int running = 1;
    int initialized = 0;
    uint64_t frames_decoded = 0;

    /* ------------------------------------------------------------------ */
    /* Main decode loop                                                   */
    /* ------------------------------------------------------------------ */
    while (running) {
        int state = pc_get_state(&clk);

        if (state == PC_STOPPED) {
            fprintf(stderr, "[decode_aac] clock STOPPED, exiting\n");
            break;
        }
        if (state == PC_SEEKING) {
            /* Flush output ring; re-open decoder */
            pr_reset(&out_ring);
            NeAACDecClose(decoder);
            decoder = NeAACDecOpen();
            conf = NeAACDecGetCurrentConfiguration(decoder);
            conf->outputFormat = FAAD_FMT_16BIT;
            conf->downMatrix = 1;
            NeAACDecSetConfiguration(decoder, conf);
            initialized = 0;
            usleep(1000);
            continue;
        }
        if (state == PC_PAUSED) {
            usleep(1000);
            continue;
        }

        /* Read an AAC frame from demuxer */
        if (!pr_read(&in_ring, aac_buf, &pkt_size, &pkt_pts, &pkt_flags)) {
            if (pr_is_eof(&in_ring)) {
                pr_signal_eof(&out_ring);
                fprintf(stderr, "[decode_aac] EOF, decoded %lu frames\n",
                        (unsigned long)frames_decoded);
                break;
            }
            usleep(1000);
            continue;
        }

        /* ------------------------------------------------------------ */
        /* First packet with CONFIG flag = AudioSpecificConfig (esds)    */
        /* ------------------------------------------------------------ */
        if (!initialized) {
            unsigned long sample_rate = 0;
            unsigned char channels = 0;

            if (pkt_flags & PR_PKTFLAG_CONFIG) {
                /* Explicit ASC from esds box */
                long err = NeAACDecInit2(decoder, aac_buf, pkt_size,
                                         &sample_rate, &channels);
                if (err < 0) {
                    fprintf(stderr, "[decode_aac] NeAACDecInit2 failed: %ld\n",
                            err);
                    /* Try again with next packet */
                    continue;
                }
            } else {
                /* Raw ADTS or first frame — let faad2 sniff it */
                long err = NeAACDecInit(decoder, aac_buf, pkt_size,
                                        &sample_rate, &channels);
                if (err < 0) {
                    fprintf(stderr, "[decode_aac] NeAACDecInit failed: %ld\n",
                            err);
                    continue;
                }
            }

            initialized = 1;
            fprintf(stderr, "[decode_aac] initialized: rate=%lu ch=%u\n",
                    sample_rate, channels);

            /* If CONFIG-only packet, don't try to decode it */
            if (pkt_flags & PR_PKTFLAG_CONFIG) {
                continue;
            }
        }

        /* ------------------------------------------------------------ */
        /* Decode the AAC frame                                         */
        /* ------------------------------------------------------------ */
        NeAACDecFrameInfo frame_info;
        void *pcm = NeAACDecDecode(decoder, &frame_info,
                                   aac_buf, pkt_size);

        if (frame_info.error != 0) {
            fprintf(stderr, "[decode_aac] decode error %u: %s\n",
                    frame_info.error,
                    NeAACDecGetErrorMessage(frame_info.error));
            /* Non-fatal — skip and continue */
            continue;
        }

        if (!pcm || frame_info.samples == 0) {
            /* No output (priming frame, etc.) */
            continue;
        }

        /*
         * frame_info.samples = total samples across all channels
         * For S16LE: bytes = samples * 2
         */
        uint32_t pcm_bytes = (uint32_t)(frame_info.samples * sizeof(int16_t));

        /* Write decoded PCM to output ring */
        while (!pr_write(&out_ring, pcm, pcm_bytes, pkt_pts, 0)) {
            if (pc_get_state(&clk) == PC_STOPPED) {
                running = 0;
                break;
            }
            usleep(500);
        }

        frames_decoded++;
        if ((frames_decoded % 500) == 0) {
            fprintf(stderr, "[decode_aac] %lu frames decoded\n",
                    (unsigned long)frames_decoded);
        }
    }

    /* ------------------------------------------------------------------ */
    /* Cleanup                                                            */
    /* ------------------------------------------------------------------ */
    NeAACDecClose(decoder);
    free(aac_buf);
    pr_close(&in_ring);
    pr_close(&out_ring);
    pc_close(&clk);

    fprintf(stderr, "[decode_aac] done, %lu frames total\n",
            (unsigned long)frames_decoded);
    return 0;
}
