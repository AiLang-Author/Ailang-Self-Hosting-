/*
 * decode_h264.c — H.264/AVC decoder shim using OpenH264
 * Reads NAL unit packets from an input PacketRing, decodes with OpenH264,
 * writes raw YUV420 frames to an output PacketRing.
 *
 * The presenter converts YUV→BGRA for display.
 *
 * Usage:
 *   ./decode_h264.x <input_ring_name> <output_ring_name> <clock_name>
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

#include <wels/codec_api.h>
#include <wels/codec_def.h>

/* Max compressed NAL packet (2MB should cover any reasonable frame) */
#define MAX_NAL_PKT   (2 * 1024 * 1024)
/* Max decoded frame (4K @ YUV420 = 3840*2160*3/2 ≈ 12MB) */
#define MAX_YUV_FRAME (16 * 1024 * 1024)
/* Output ring 32MB — decoded YUV frames are large */
#define OUT_RING_CAP  (32 * 1024 * 1024)

/*
 * Copy decoded YUV420 from OpenH264's planar buffers into a contiguous
 * packed buffer: Y plane, then U plane, then V plane.
 * Returns total bytes written.
 */
static uint32_t pack_yuv420(uint8_t *dst,
                            uint8_t *y, int y_stride,
                            uint8_t *u, int u_stride,
                            uint8_t *v, int v_stride,
                            int width, int height) {
    int half_w = width / 2;
    int half_h = height / 2;
    uint32_t off = 0;

    /* Y plane */
    for (int row = 0; row < height; row++) {
        memcpy(dst + off, y + row * y_stride, width);
        off += width;
    }
    /* U plane */
    for (int row = 0; row < half_h; row++) {
        memcpy(dst + off, u + row * u_stride, half_w);
        off += half_w;
    }
    /* V plane */
    for (int row = 0; row < half_h; row++) {
        memcpy(dst + off, v + row * v_stride, half_w);
        off += half_w;
    }
    return off;
}

int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Usage: decode_h264.x <in_ring> <out_ring> <clock>\n");
        return 1;
    }

    const char *in_name  = argv[1];
    const char *out_name = argv[2];
    const char *clk_name = argv[3];

    fprintf(stderr, "[decode_h264] in=%s out=%s clock=%s\n",
            in_name, out_name, clk_name);

    /* ------------------------------------------------------------------ */
    /* Create OpenH264 decoder                                            */
    /* ------------------------------------------------------------------ */
    ISVCDecoder *decoder = NULL;
    long rv = WelsCreateDecoder(&decoder);
    if (rv != 0 || !decoder) {
        fprintf(stderr, "[decode_h264] WelsCreateDecoder failed: %ld\n", rv);
        return 1;
    }

    SDecodingParam param;
    memset(&param, 0, sizeof(param));
    param.sVideoProperty.eVideoBsType = VIDEO_BITSTREAM_AVC;
    param.bParseOnly = false;

    rv = (*decoder)->Initialize(decoder, &param);
    if (rv != 0) {
        fprintf(stderr, "[decode_h264] decoder Initialize failed: %ld\n", rv);
        WelsDestroyDecoder(decoder);
        return 1;
    }

    fprintf(stderr, "[decode_h264] OpenH264 decoder initialized\n");

    /* ------------------------------------------------------------------ */
    /* Open rings and clock                                               */
    /* ------------------------------------------------------------------ */
    PacketRing in_ring, out_ring;
    PlaybackClock clk;

    if (!pr_open(&in_ring, in_name)) {
        fprintf(stderr, "[decode_h264] failed to open input ring\n");
        return 1;
    }
    if (!pr_create(&out_ring, out_name, OUT_RING_CAP)) {
        fprintf(stderr, "[decode_h264] failed to create output ring\n");
        return 1;
    }
    if (!pc_open(&clk, clk_name)) {
        fprintf(stderr, "[decode_h264] failed to open clock\n");
        return 1;
    }

    uint8_t *nal_buf = malloc(MAX_NAL_PKT);
    uint8_t *yuv_buf = malloc(MAX_YUV_FRAME);
    if (!nal_buf || !yuv_buf) {
        fprintf(stderr, "[decode_h264] malloc failed\n");
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
            fprintf(stderr, "[decode_h264] clock STOPPED, exiting\n");
            break;
        }
        if (state == PC_SEEKING) {
            /* Flush output ring and decoder state */
            pr_reset(&out_ring);
            /* Re-initialize decoder to flush internal buffers */
            (*decoder)->Uninitialize(decoder);
            (*decoder)->Initialize(decoder, &param);
            usleep(1000);
            continue;
        }
        if (state == PC_PAUSED) {
            usleep(1000);
            continue;
        }

        /* Read a NAL packet from demuxer */
        if (!pr_read(&in_ring, nal_buf, &pkt_size, &pkt_pts, &pkt_flags)) {
            if (pr_is_eof(&in_ring)) {
                /* Drain any buffered frames */
                SBufferInfo buf_info;
                uint8_t *yuv_ptrs[3] = {NULL, NULL, NULL};
                memset(&buf_info, 0, sizeof(buf_info));

                (*decoder)->FlushFrame(decoder, yuv_ptrs, &buf_info);
                if (buf_info.iBufferStatus == 1) {
                    int w = buf_info.UsrData.sSystemBuffer.iWidth;
                    int h = buf_info.UsrData.sSystemBuffer.iHeight;
                    int y_stride = buf_info.UsrData.sSystemBuffer.iStride[0];
                    int uv_stride = buf_info.UsrData.sSystemBuffer.iStride[1];

                    uint32_t yuv_size = pack_yuv420(yuv_buf,
                        yuv_ptrs[0], y_stride,
                        yuv_ptrs[1], uv_stride,
                        yuv_ptrs[2], uv_stride,
                        w, h);

                    /* Embed width/height in first 8 bytes of output */
                    uint32_t hdr[2] = { (uint32_t)w, (uint32_t)h };
                    memmove(yuv_buf + 8, yuv_buf, yuv_size);
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

                pr_signal_eof(&out_ring);
                fprintf(stderr, "[decode_h264] EOF, decoded %lu frames\n",
                        (unsigned long)frames_decoded);
                break;
            }
            usleep(1000);
            continue;
        }

        /* ------------------------------------------------------------ */
        /* Decode the NAL unit                                          */
        /* ------------------------------------------------------------ */
        SBufferInfo buf_info;
        uint8_t *yuv_ptrs[3] = {NULL, NULL, NULL};
        memset(&buf_info, 0, sizeof(buf_info));

        DECODING_STATE ds = (*decoder)->DecodeFrameNoDelay(
            decoder, nal_buf, (int)pkt_size, yuv_ptrs, &buf_info);

        if (ds != dsErrorFree && ds != dsNoParamSets) {
            fprintf(stderr, "[decode_h264] decode error: %d\n", ds);
            /* Non-fatal — skip this NAL and continue */
            continue;
        }

        /* Check if we got a decoded frame */
        if (buf_info.iBufferStatus != 1) {
            /* No output yet (buffering B-frames, etc.) */
            continue;
        }

        int w = buf_info.UsrData.sSystemBuffer.iWidth;
        int h = buf_info.UsrData.sSystemBuffer.iHeight;
        int y_stride  = buf_info.UsrData.sSystemBuffer.iStride[0];
        int uv_stride = buf_info.UsrData.sSystemBuffer.iStride[1];

        uint32_t yuv_size = pack_yuv420(yuv_buf,
            yuv_ptrs[0], y_stride,
            yuv_ptrs[1], uv_stride,
            yuv_ptrs[2], uv_stride,
            w, h);

        /*
         * Output frame format:
         *   [0..3]  uint32_t width
         *   [4..7]  uint32_t height
         *   [8..]   packed YUV420 (Y + U + V planes)
         *
         * PTS is passed through from the input packet.
         */
        uint32_t hdr[2] = { (uint32_t)w, (uint32_t)h };
        memmove(yuv_buf + 8, yuv_buf, yuv_size);
        memcpy(yuv_buf, hdr, 8);

        /* Write decoded frame to output ring */
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
            fprintf(stderr, "[decode_h264] %lu frames decoded\n",
                    (unsigned long)frames_decoded);
        }
    }

    /* ------------------------------------------------------------------ */
    /* Cleanup                                                            */
    /* ------------------------------------------------------------------ */
    (*decoder)->Uninitialize(decoder);
    WelsDestroyDecoder(decoder);

    free(nal_buf);
    free(yuv_buf);
    pr_close(&in_ring);
    pr_close(&out_ring);
    pc_close(&clk);

    fprintf(stderr, "[decode_h264] done, %lu frames total\n",
            (unsigned long)frames_decoded);
    return 0;
}
