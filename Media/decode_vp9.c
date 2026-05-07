/*
 * decode_vp9.c — VP9 decoder shim using libvpx
 * Reads VP9 compressed frames from an input PacketRing, decodes with libvpx,
 * writes raw YUV420 frames to an output PacketRing.
 *
 * Usage:
 *   ./decode_vp9.x <input_ring_name> <output_ring_name> <clock_name>
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

#include <vpx/vpx_decoder.h>
#include <vpx/vp8dx.h>

/* Max compressed frame (4MB) */
#define MAX_VP9_PKT   (4 * 1024 * 1024)
/* Max decoded frame (4K @ YUV420 ≈ 12MB) */
#define MAX_YUV_FRAME (16 * 1024 * 1024)
/* Output ring 32MB */
#define OUT_RING_CAP  (32 * 1024 * 1024)

/*
 * Copy VPX image (I420) to contiguous packed YUV420 buffer.
 * Returns total bytes.
 */
static uint32_t pack_vpx_yuv420(uint8_t *dst, const vpx_image_t *img) {
    int w = img->d_w;
    int h = img->d_h;
    int half_w = (w + 1) / 2;
    int half_h = (h + 1) / 2;
    uint32_t off = 0;

    /* Y plane */
    for (int row = 0; row < h; row++) {
        memcpy(dst + off, img->planes[VPX_PLANE_Y] + row * img->stride[VPX_PLANE_Y], w);
        off += w;
    }
    /* U plane */
    for (int row = 0; row < half_h; row++) {
        memcpy(dst + off, img->planes[VPX_PLANE_U] + row * img->stride[VPX_PLANE_U], half_w);
        off += half_w;
    }
    /* V plane */
    for (int row = 0; row < half_h; row++) {
        memcpy(dst + off, img->planes[VPX_PLANE_V] + row * img->stride[VPX_PLANE_V], half_w);
        off += half_w;
    }
    return off;
}

int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Usage: decode_vp9.x <in_ring> <out_ring> <clock>\n");
        return 1;
    }

    const char *in_name  = argv[1];
    const char *out_name = argv[2];
    const char *clk_name = argv[3];

    fprintf(stderr, "[decode_vp9] in=%s out=%s clock=%s\n",
            in_name, out_name, clk_name);

    /* ------------------------------------------------------------------ */
    /* Create libvpx VP9 decoder                                          */
    /* ------------------------------------------------------------------ */
    vpx_codec_ctx_t codec;
    vpx_codec_dec_cfg_t cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.threads = 2;  /* Use 2 decode threads */

    vpx_codec_err_t res = vpx_codec_dec_init(&codec,
        vpx_codec_vp9_dx(), &cfg, 0);
    if (res != VPX_CODEC_OK) {
        fprintf(stderr, "[decode_vp9] vpx_codec_dec_init failed: %s\n",
                vpx_codec_err_to_string(res));
        return 1;
    }

    fprintf(stderr, "[decode_vp9] libvpx VP9 decoder initialized\n");

    /* ------------------------------------------------------------------ */
    /* Open rings and clock                                               */
    /* ------------------------------------------------------------------ */
    PacketRing in_ring, out_ring;
    PlaybackClock clk;

    if (!pr_open(&in_ring, in_name)) {
        fprintf(stderr, "[decode_vp9] failed to open input ring\n");
        return 1;
    }
    if (!pr_create(&out_ring, out_name, OUT_RING_CAP)) {
        fprintf(stderr, "[decode_vp9] failed to create output ring\n");
        return 1;
    }
    if (!pc_open(&clk, clk_name)) {
        fprintf(stderr, "[decode_vp9] failed to open clock\n");
        return 1;
    }

    uint8_t *vp9_buf = malloc(MAX_VP9_PKT);
    uint8_t *yuv_buf = malloc(MAX_YUV_FRAME);
    if (!vp9_buf || !yuv_buf) {
        fprintf(stderr, "[decode_vp9] malloc failed\n");
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
            fprintf(stderr, "[decode_vp9] clock STOPPED, exiting\n");
            break;
        }
        if (state == PC_SEEKING) {
            pr_reset(&out_ring);
            /* Destroy and re-init codec to flush internal state */
            vpx_codec_destroy(&codec);
            memset(&cfg, 0, sizeof(cfg));
            cfg.threads = 2;
            vpx_codec_dec_init(&codec, vpx_codec_vp9_dx(), &cfg, 0);
            usleep(1000);
            continue;
        }
        if (state == PC_PAUSED) {
            usleep(1000);
            continue;
        }

        /* Read a VP9 frame from demuxer */
        if (!pr_read(&in_ring, vp9_buf, &pkt_size, &pkt_pts, &pkt_flags)) {
            if (pr_is_eof(&in_ring)) {
                pr_signal_eof(&out_ring);
                fprintf(stderr, "[decode_vp9] EOF, decoded %lu frames\n",
                        (unsigned long)frames_decoded);
                break;
            }
            usleep(1000);
            continue;
        }

        /* ------------------------------------------------------------ */
        /* Decode the VP9 frame                                         */
        /* ------------------------------------------------------------ */
        res = vpx_codec_decode(&codec, vp9_buf, pkt_size, NULL, 0);
        if (res != VPX_CODEC_OK) {
            fprintf(stderr, "[decode_vp9] decode error: %s\n",
                    vpx_codec_err_to_string(res));
            continue;
        }

        /* Iterate decoded frames (usually 1, but could be more) */
        vpx_codec_iter_t iter = NULL;
        vpx_image_t *img;

        while ((img = vpx_codec_get_frame(&codec, &iter)) != NULL) {
            if (img->fmt != VPX_IMG_FMT_I420) {
                fprintf(stderr, "[decode_vp9] unexpected pixel format: %d\n",
                        img->fmt);
                continue;
            }

            uint32_t yuv_size = pack_vpx_yuv420(yuv_buf, img);

            /*
             * Output frame format (same as decode_h264):
             *   [0..3]  uint32_t width
             *   [4..7]  uint32_t height
             *   [8..]   packed YUV420
             */
            uint32_t hdr[2] = { img->d_w, img->d_h };
            memmove(yuv_buf + 8, yuv_buf, yuv_size);
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
            if ((frames_decoded % 100) == 0) {
                fprintf(stderr, "[decode_vp9] %lu frames decoded\n",
                        (unsigned long)frames_decoded);
            }
        }
    }

    /* ------------------------------------------------------------------ */
    /* Cleanup                                                            */
    /* ------------------------------------------------------------------ */
    vpx_codec_destroy(&codec);
    free(vp9_buf);
    free(yuv_buf);
    pr_close(&in_ring);
    pr_close(&out_ring);
    pc_close(&clk);

    fprintf(stderr, "[decode_vp9] done, %lu frames total\n",
            (unsigned long)frames_decoded);
    return 0;
}
