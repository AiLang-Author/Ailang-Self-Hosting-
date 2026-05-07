/*
 * decode_av1.c — AV1 decoder shim using dav1d
 * Reads AV1 OBU packets from an input PacketRing, decodes with dav1d,
 * writes raw YUV420 frames to an output PacketRing.
 *
 * dav1d is the fast AV1 decoder by VideoLAN — much faster than libaom
 * for decode-only workloads.
 *
 * Output frame format (same as decode_h264/decode_vp9/decode_h265):
 *   [0..3]  uint32_t width
 *   [4..7]  uint32_t height
 *   [8..]   packed YUV420 (Y plane, then U, then V)
 *
 * Usage:
 *   ./decode_av1.x <input_ring_name> <output_ring_name> <clock_name>
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

#include <dav1d/dav1d.h>

/* Max compressed AV1 packet (4MB) */
#define MAX_AV1_PKT    (4 * 1024 * 1024)
/* Max decoded frame (4K @ YUV420 ≈ 12MB) */
#define MAX_YUV_FRAME  (16 * 1024 * 1024)
/* Output ring 32MB */
#define OUT_RING_CAP   (32 * 1024 * 1024)

/*
 * dav1d_data_wrap free callback — we manage memory ourselves,
 * so this is a no-op.
 */
static void dav1d_free_noop(const uint8_t *data, void *cookie) {
    (void)data;
    (void)cookie;
}

/*
 * Copy dav1d picture (YUV420 8-bit) to contiguous packed buffer.
 * Returns total YUV bytes.
 */
static uint32_t pack_dav1d_yuv420(uint8_t *dst, const Dav1dPicture *pic) {
    int w = pic->p.w;
    int h = pic->p.h;
    int half_w = (w + 1) / 2;
    int half_h = (h + 1) / 2;
    uint32_t off = 0;

    /* Y plane */
    const uint8_t *y = pic->data[0];
    ptrdiff_t ys = pic->stride[0];
    for (int row = 0; row < h; row++) {
        memcpy(dst + off, y + row * ys, w);
        off += w;
    }

    /* U plane */
    const uint8_t *u = pic->data[1];
    ptrdiff_t cs = pic->stride[1];  /* chroma stride (U and V share) */
    for (int row = 0; row < half_h; row++) {
        memcpy(dst + off, u + row * cs, half_w);
        off += half_w;
    }

    /* V plane */
    const uint8_t *v = pic->data[2];
    for (int row = 0; row < half_h; row++) {
        memcpy(dst + off, v + row * cs, half_w);
        off += half_w;
    }

    return off;
}

int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Usage: decode_av1.x <in_ring> <out_ring> <clock>\n");
        return 1;
    }

    const char *in_name  = argv[1];
    const char *out_name = argv[2];
    const char *clk_name = argv[3];

    fprintf(stderr, "[decode_av1] in=%s out=%s clock=%s\n",
            in_name, out_name, clk_name);

    /* ------------------------------------------------------------------ */
    /* Create dav1d AV1 decoder                                           */
    /* ------------------------------------------------------------------ */
    Dav1dSettings settings;
    dav1d_default_settings(&settings);
    settings.n_threads = 2;
    settings.max_frame_delay = 1;  /* Low latency */

    Dav1dContext *decoder = NULL;
    int dav_err = dav1d_open(&decoder, &settings);
    if (dav_err < 0 || !decoder) {
        fprintf(stderr, "[decode_av1] dav1d_open failed: %d\n", dav_err);
        return 1;
    }

    fprintf(stderr, "[decode_av1] dav1d AV1 decoder initialized (2 threads)\n");

    /* ------------------------------------------------------------------ */
    /* Open rings and clock                                               */
    /* ------------------------------------------------------------------ */
    PacketRing in_ring, out_ring;
    PlaybackClock clk;

    if (!pr_open(&in_ring, in_name)) {
        fprintf(stderr, "[decode_av1] failed to open input ring\n");
        return 1;
    }
    if (!pr_create(&out_ring, out_name, OUT_RING_CAP)) {
        fprintf(stderr, "[decode_av1] failed to create output ring\n");
        return 1;
    }
    if (!pc_open(&clk, clk_name)) {
        fprintf(stderr, "[decode_av1] failed to open clock\n");
        return 1;
    }

    uint8_t *av1_buf = malloc(MAX_AV1_PKT);
    uint8_t *yuv_buf = malloc(MAX_YUV_FRAME);
    if (!av1_buf || !yuv_buf) {
        fprintf(stderr, "[decode_av1] malloc failed\n");
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
            fprintf(stderr, "[decode_av1] clock STOPPED, exiting\n");
            break;
        }
        if (state == PC_SEEKING) {
            pr_reset(&out_ring);
            /* Flush decoder and re-open */
            dav1d_flush(decoder);
            usleep(1000);
            continue;
        }
        if (state == PC_PAUSED) {
            usleep(1000);
            continue;
        }

        /* Read an AV1 packet from demuxer */
        if (!pr_read(&in_ring, av1_buf, &pkt_size, &pkt_pts, &pkt_flags)) {
            if (pr_is_eof(&in_ring)) {
                /* Drain remaining pictures */
                Dav1dPicture pic;
                memset(&pic, 0, sizeof(pic));
                while (dav1d_get_picture(decoder, &pic) == 0) {
                    if (pic.p.layout == DAV1D_PIXEL_LAYOUT_I420 &&
                        pic.p.bpc == 8) {
                        uint32_t yuv_size = pack_dav1d_yuv420(yuv_buf + 8, &pic);
                        uint32_t hdr[2] = { (uint32_t)pic.p.w, (uint32_t)pic.p.h };
                        memcpy(yuv_buf, hdr, 8);
                        while (!pr_write(&out_ring, yuv_buf, yuv_size + 8,
                                         pkt_pts, 0)) {
                            if (pc_get_state(&clk) == PC_STOPPED) {
                                running = 0;
                                break;
                            }
                            usleep(500);
                        }
                        frames_decoded++;
                    }
                    dav1d_picture_unref(&pic);
                    memset(&pic, 0, sizeof(pic));
                }
                pr_signal_eof(&out_ring);
                fprintf(stderr, "[decode_av1] EOF, decoded %lu frames\n",
                        (unsigned long)frames_decoded);
                break;
            }
            usleep(1000);
            continue;
        }

        /* Skip CONFIG packets (sequence headers handled inline by dav1d) */
        if (pkt_flags & PR_PKTFLAG_CONFIG) {
            /* dav1d handles OBU sequence headers inline, but we can also
             * feed them explicitly — just send as regular data */
        }

        /* ------------------------------------------------------------ */
        /* Feed data to dav1d                                           */
        /* ------------------------------------------------------------ */
        Dav1dData data;
        memset(&data, 0, sizeof(data));
        dav_err = dav1d_data_wrap(&data, av1_buf, pkt_size,
                                  dav1d_free_noop, NULL);
        if (dav_err < 0) {
            fprintf(stderr, "[decode_av1] dav1d_data_wrap failed: %d\n",
                    dav_err);
            continue;
        }
        data.m.timestamp = pkt_pts;

        /* Send data — may need multiple attempts if decoder is full */
        while (data.sz > 0) {
            dav_err = dav1d_send_data(decoder, &data);
            if (dav_err < 0 && dav_err != DAV1D_ERR(EAGAIN)) {
                fprintf(stderr, "[decode_av1] send error: %d\n", dav_err);
                break;
            }

            /* Drain available pictures */
            Dav1dPicture pic;
            memset(&pic, 0, sizeof(pic));
            while (dav1d_get_picture(decoder, &pic) == 0) {
                /* Check for YUV420 8-bit */
                if (pic.p.layout != DAV1D_PIXEL_LAYOUT_I420 ||
                    pic.p.bpc != 8) {
                    fprintf(stderr, "[decode_av1] unsupported format: "
                            "layout=%d bpc=%d\n", pic.p.layout, pic.p.bpc);
                    dav1d_picture_unref(&pic);
                    memset(&pic, 0, sizeof(pic));
                    continue;
                }

                uint32_t yuv_size = pack_dav1d_yuv420(yuv_buf + 8, &pic);

                /* Prepend width/height header */
                uint32_t hdr[2] = {
                    (uint32_t)pic.p.w,
                    (uint32_t)pic.p.h
                };
                memcpy(yuv_buf, hdr, 8);

                int64_t out_pts = pic.m.timestamp;

                /* Write to output ring */
                while (!pr_write(&out_ring, yuv_buf, yuv_size + 8,
                                 out_pts, 0)) {
                    if (pc_get_state(&clk) == PC_STOPPED) {
                        running = 0;
                        break;
                    }
                    usleep(500);
                }

                dav1d_picture_unref(&pic);
                memset(&pic, 0, sizeof(pic));

                frames_decoded++;
                if ((frames_decoded % 100) == 0) {
                    fprintf(stderr, "[decode_av1] %lu frames decoded\n",
                            (unsigned long)frames_decoded);
                }
            }

            if (dav_err == DAV1D_ERR(EAGAIN)) {
                /* Decoder buffer full, drain and retry */
                usleep(100);
            }
        }
    }

    /* ------------------------------------------------------------------ */
    /* Cleanup                                                            */
    /* ------------------------------------------------------------------ */
    dav1d_close(&decoder);
    free(av1_buf);
    free(yuv_buf);
    pr_close(&in_ring);
    pr_close(&out_ring);
    pc_close(&clk);

    fprintf(stderr, "[decode_av1] done, %lu frames total\n",
            (unsigned long)frames_decoded);
    return 0;
}
