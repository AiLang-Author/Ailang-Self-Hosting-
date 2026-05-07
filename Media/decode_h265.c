/*
 * decode_h265.c — H.265/HEVC decoder shim using libde265
 * Reads HEVC NAL packets from an input PacketRing, decodes with libde265,
 * writes raw YUV420 frames to an output PacketRing.
 *
 * Output frame format (same as decode_h264/decode_vp9):
 *   [0..3]  uint32_t width
 *   [4..7]  uint32_t height
 *   [8..]   packed YUV420 (Y plane, then U, then V)
 *
 * Usage:
 *   ./decode_h265.x <input_ring_name> <output_ring_name> <clock_name>
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

#include <libde265/de265.h>

/* Max compressed HEVC packet (4MB) */
#define MAX_H265_PKT   (4 * 1024 * 1024)
/* Max decoded frame (4K @ YUV420 ≈ 12MB) */
#define MAX_YUV_FRAME  (16 * 1024 * 1024)
/* Output ring 32MB */
#define OUT_RING_CAP   (32 * 1024 * 1024)

/*
 * Copy libde265 image (YUV420) to contiguous packed buffer.
 * Returns total bytes written.
 */
static uint32_t pack_de265_yuv420(uint8_t *dst, const struct de265_image *img) {
    int w = de265_get_image_width(img, 0);
    int h = de265_get_image_height(img, 0);
    int half_w = (w + 1) / 2;
    int half_h = (h + 1) / 2;
    uint32_t off = 0;
    int stride;

    /* Y plane */
    const uint8_t *y = de265_get_image_plane(img, 0, &stride);
    for (int row = 0; row < h; row++) {
        memcpy(dst + off, y + row * stride, w);
        off += w;
    }

    /* U plane */
    const uint8_t *u = de265_get_image_plane(img, 1, &stride);
    for (int row = 0; row < half_h; row++) {
        memcpy(dst + off, u + row * stride, half_w);
        off += half_w;
    }

    /* V plane */
    const uint8_t *v = de265_get_image_plane(img, 2, &stride);
    for (int row = 0; row < half_h; row++) {
        memcpy(dst + off, v + row * stride, half_w);
        off += half_w;
    }

    return off;
}

int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Usage: decode_h265.x <in_ring> <out_ring> <clock>\n");
        return 1;
    }

    const char *in_name  = argv[1];
    const char *out_name = argv[2];
    const char *clk_name = argv[3];

    fprintf(stderr, "[decode_h265] in=%s out=%s clock=%s\n",
            in_name, out_name, clk_name);

    /* ------------------------------------------------------------------ */
    /* Create libde265 HEVC decoder                                       */
    /* ------------------------------------------------------------------ */
    de265_decoder_context *decoder = de265_new_decoder();
    if (!decoder) {
        fprintf(stderr, "[decode_h265] de265_new_decoder failed\n");
        return 1;
    }

    /* Enable multi-threaded decoding */
    de265_set_parameter_bool(decoder, DE265_DECODER_PARAM_BOOL_SEI_CHECK, 0);
    de265_set_parameter_int(decoder, DE265_DECODER_PARAM_DUMP_SPS_HEADERS, 0);
    de265_set_parameter_int(decoder, DE265_DECODER_PARAM_DUMP_VPS_HEADERS, 0);
    de265_set_parameter_int(decoder, DE265_DECODER_PARAM_DUMP_PPS_HEADERS, 0);
    de265_set_number_of_worker_threads(decoder, 2);
    de265_start_worker_threads(decoder, 2);

    fprintf(stderr, "[decode_h265] libde265 HEVC decoder initialized (2 threads)\n");

    /* ------------------------------------------------------------------ */
    /* Open rings and clock                                               */
    /* ------------------------------------------------------------------ */
    PacketRing in_ring, out_ring;
    PlaybackClock clk;

    if (!pr_open(&in_ring, in_name)) {
        fprintf(stderr, "[decode_h265] failed to open input ring\n");
        return 1;
    }
    if (!pr_create(&out_ring, out_name, OUT_RING_CAP)) {
        fprintf(stderr, "[decode_h265] failed to create output ring\n");
        return 1;
    }
    if (!pc_open(&clk, clk_name)) {
        fprintf(stderr, "[decode_h265] failed to open clock\n");
        return 1;
    }

    uint8_t *h265_buf = malloc(MAX_H265_PKT);
    uint8_t *yuv_buf  = malloc(MAX_YUV_FRAME);
    if (!h265_buf || !yuv_buf) {
        fprintf(stderr, "[decode_h265] malloc failed\n");
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
            fprintf(stderr, "[decode_h265] clock STOPPED, exiting\n");
            break;
        }
        if (state == PC_SEEKING) {
            pr_reset(&out_ring);
            /* Re-create decoder for clean state */
            de265_free_decoder(decoder);
            decoder = de265_new_decoder();
            de265_set_parameter_bool(decoder, DE265_DECODER_PARAM_BOOL_SEI_CHECK, 0);
            de265_set_number_of_worker_threads(decoder, 2);
            de265_start_worker_threads(decoder, 2);
            usleep(1000);
            continue;
        }
        if (state == PC_PAUSED) {
            usleep(1000);
            continue;
        }

        /* Read a HEVC packet from demuxer */
        if (!pr_read(&in_ring, h265_buf, &pkt_size, &pkt_pts, &pkt_flags)) {
            if (pr_is_eof(&in_ring)) {
                /* Flush remaining frames */
                de265_flush_data(decoder);
                int more = 1;
                while (more) {
                    de265_error err = de265_decode(decoder, &more);
                    if (err != DE265_OK && err != DE265_ERROR_WAITING_FOR_INPUT_DATA)
                        break;
                    const struct de265_image *img;
                    while ((img = de265_get_next_picture(decoder)) != NULL) {
                        int w = de265_get_image_width(img, 0);
                        int h = de265_get_image_height(img, 0);
                        uint32_t yuv_size = pack_de265_yuv420(yuv_buf + 8, img);
                        uint32_t hdr[2] = { (uint32_t)w, (uint32_t)h };
                        memcpy(yuv_buf, hdr, 8);
                        while (!pr_write(&out_ring, yuv_buf, yuv_size + 8,
                                         pkt_pts, pkt_flags)) {
                            if (pc_get_state(&clk) == PC_STOPPED) {
                                running = 0;
                                break;
                            }
                            usleep(500);
                        }
                        frames_decoded++;
                    }
                }
                pr_signal_eof(&out_ring);
                fprintf(stderr, "[decode_h265] EOF, decoded %lu frames\n",
                        (unsigned long)frames_decoded);
                break;
            }
            usleep(1000);
            continue;
        }

        /* ------------------------------------------------------------ */
        /* Push data to libde265                                        */
        /* ------------------------------------------------------------ */
        de265_error err = de265_push_data(decoder, h265_buf, pkt_size,
                                          pkt_pts, NULL);
        if (err != DE265_OK) {
            fprintf(stderr, "[decode_h265] push error: %s\n",
                    de265_get_error_text(err));
            continue;
        }

        /* Decode and extract frames */
        int more = 1;
        while (more) {
            err = de265_decode(decoder, &more);
            if (err == DE265_ERROR_WAITING_FOR_INPUT_DATA) {
                break;  /* Need more input */
            }
            if (err != DE265_OK) {
                fprintf(stderr, "[decode_h265] decode error: %s\n",
                        de265_get_error_text(err));
                break;
            }

            /* Pull decoded pictures */
            const struct de265_image *img;
            while ((img = de265_get_next_picture(decoder)) != NULL) {
                int w = de265_get_image_width(img, 0);
                int h = de265_get_image_height(img, 0);

                /* Check for YUV420 format */
                de265_chroma chroma = de265_get_chroma_format(img);
                if (chroma != de265_chroma_420) {
                    fprintf(stderr, "[decode_h265] unsupported chroma: %d\n",
                            chroma);
                    continue;
                }

                uint32_t yuv_size = pack_de265_yuv420(yuv_buf + 8, img);

                /* Prepend width/height header */
                uint32_t hdr[2] = { (uint32_t)w, (uint32_t)h };
                memcpy(yuv_buf, hdr, 8);

                /* Write to output ring */
                while (!pr_write(&out_ring, yuv_buf, yuv_size + 8,
                                 pkt_pts, pkt_flags)) {
                    if (pc_get_state(&clk) == PC_STOPPED) {
                        running = 0;
                        break;
                    }
                    usleep(500);
                }

                frames_decoded++;
                if ((frames_decoded % 100) == 0) {
                    fprintf(stderr, "[decode_h265] %lu frames decoded\n",
                            (unsigned long)frames_decoded);
                }
            }
        }
    }

    /* ------------------------------------------------------------------ */
    /* Cleanup                                                            */
    /* ------------------------------------------------------------------ */
    de265_free_decoder(decoder);
    free(h265_buf);
    free(yuv_buf);
    pr_close(&in_ring);
    pr_close(&out_ring);
    pc_close(&clk);

    fprintf(stderr, "[decode_h265] done, %lu frames total\n",
            (unsigned long)frames_decoded);
    return 0;
}
