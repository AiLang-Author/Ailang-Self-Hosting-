/*
 * ailang_codec_abi.h
 * Binary interface between MediaCenter and codec worker processes.
 *
 * A codec worker is a standalone process that:
 *   1. Opens its assigned packet ring and frame ring from /dev/shm
 *   2. Reads compressed packets from the packet ring
 *   3. Decodes them using whatever codec library it wraps
 *   4. Writes decoded frames/samples to the frame ring
 *   5. Responds to clock ticks for rate control
 *
 * Worker is launched by MediaCenter:
 *   execve(worker_path, { worker_path, session_id_str, NULL }, envp)
 *
 * Worker opens its rings using session_id:
 *   /dev/shm/ailang_codec_<session_id>_pkt  (read packets from here)
 *   /dev/shm/ailang_codec_<session_id>_frm  (write frames here)
 *
 * Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
 */

#ifndef AILANG_CODEC_ABI_H
#define AILANG_CODEC_ABI_H

#include <stdint.h>
#include <stddef.h>

/* ============================================================
 * Ring buffer layout (matches Library.CodecRing.ailang exactly)
 * ============================================================ */
#define CR_MAGIC          0x474E524C4941ULL   /* 'AILRNG\0\0' */
#define CR_HEADER_SIZE    32
#define CR_RECORD_HDR     16
#define CR_DEFAULT_SIZE   (4 * 1024 * 1024)  /* 4MB per ring */

typedef struct {
    uint64_t magic;
    uint64_t capacity;
    uint64_t write_pos;
    uint64_t read_pos;
    uint8_t  data[];
} CRRing;

/* Record header written into the ring data region */
typedef struct {
    uint32_t len;       /* payload bytes */
    uint16_t type;      /* RTYPE_PACKET or RTYPE_FRAME */
    uint16_t flags;     /* CR_FLAG_* */
    int64_t  pts_ns;    /* absolute nanoseconds from MediaClock */
} CRRecord;

#define RTYPE_PACKET    1
#define RTYPE_FRAME     2

#define CR_FLAG_KEYFRAME  0x0001
#define CR_FLAG_EOF       0x0002
#define CR_FLAG_FLUSH     0x0004

/* ============================================================
 * Frame descriptor — written as payload for RTYPE_FRAME
 * For video: width/height/fmt set, sample_count=0
 * For audio: sample_count/sample_rate/channels set, width=height=0
 * ============================================================ */
typedef struct {
    uint32_t width;         /* video: pixel width */
    uint32_t height;        /* video: pixel height */
    uint32_t pixel_fmt;     /* video: AILFMT_BGRA etc. */
    uint32_t sample_count;  /* audio: samples in this frame */
    uint32_t sample_rate;   /* audio: e.g. 48000 */
    uint16_t channels;      /* audio: 1=mono 2=stereo */
    uint16_t bit_depth;     /* audio: 16 */
    uint8_t  data[];        /* raw pixel or PCM data follows */
} CRFrameDesc;

/* Pixel format IDs */
#define AILFMT_BGRA   1
#define AILFMT_S16LE  2

/* ============================================================
 * Ring access helpers (inline, no dependencies)
 * ============================================================ */
static inline uint64_t cr_write_avail(CRRing *r) {
    uint64_t used = (r->write_pos - r->read_pos + r->capacity) % r->capacity;
    return r->capacity - used - 1;
}

static inline uint64_t cr_read_avail(CRRing *r) {
    return (r->write_pos - r->read_pos + r->capacity) % r->capacity;
}

static inline void cr_write_byte(CRRing *r, uint64_t pos, uint8_t val) {
    r->data[pos % r->capacity] = val;
}

static inline uint8_t cr_read_byte(CRRing *r, uint64_t pos) {
    return r->data[pos % r->capacity];
}

/* Write a complete record into a ring. Returns 0 on success, -1 if full. */
static inline int cr_write_record(CRRing *r, const void *payload, uint32_t len,
                                   uint16_t type, uint16_t flags, int64_t pts_ns)
{
    uint32_t pad   = (len + CR_RECORD_HDR) % 8;
    if (pad) pad   = 8 - pad;
    uint64_t total = (uint64_t)len + CR_RECORD_HDR + pad;

    if (cr_write_avail(r) < total) return -1;

    uint64_t wp = r->write_pos;
    /* header */
    cr_write_byte(r, wp+0, len & 0xff);
    cr_write_byte(r, wp+1, (len>>8) & 0xff);
    cr_write_byte(r, wp+2, (len>>16) & 0xff);
    cr_write_byte(r, wp+3, (len>>24) & 0xff);
    cr_write_byte(r, wp+4, type & 0xff);
    cr_write_byte(r, wp+5, (type>>8) & 0xff);
    cr_write_byte(r, wp+6, flags & 0xff);
    cr_write_byte(r, wp+7, (flags>>8) & 0xff);
    for (int i = 0; i < 8; i++)
        cr_write_byte(r, wp+8+i, ((uint64_t)pts_ns >> (i*8)) & 0xff);
    /* payload */
    const uint8_t *src = (const uint8_t *)payload;
    for (uint32_t i = 0; i < len; i++)
        cr_write_byte(r, wp + CR_RECORD_HDR + i, src[i]);

    r->write_pos = (wp + total) % r->capacity;
    return 0;
}

/* Peek at the next record header. Returns total record size, 0 if empty. */
static inline uint64_t cr_peek_header(CRRing *r, CRRecord *hdr) {
    if (cr_read_avail(r) < CR_RECORD_HDR) return 0;
    uint64_t rp = r->read_pos;
    hdr->len    = cr_read_byte(r,rp+0) | (cr_read_byte(r,rp+1)<<8)
                | ((uint32_t)cr_read_byte(r,rp+2)<<16)
                | ((uint32_t)cr_read_byte(r,rp+3)<<24);
    hdr->type   = cr_read_byte(r,rp+4) | (cr_read_byte(r,rp+5)<<8);
    hdr->flags  = cr_read_byte(r,rp+6) | (cr_read_byte(r,rp+7)<<8);
    hdr->pts_ns = 0;
    for (int i = 7; i >= 0; i--)
        hdr->pts_ns = (hdr->pts_ns << 8) | cr_read_byte(r, rp+8+i);

    uint32_t pad = (hdr->len + CR_RECORD_HDR) % 8;
    if (pad) pad = 8 - pad;
    return (uint64_t)hdr->len + CR_RECORD_HDR + pad;
}

/* Consume record payload into out_buf after cr_peek_header. */
static inline void cr_consume(CRRing *r, void *out_buf, uint32_t len, uint64_t total) {
    uint64_t base = r->read_pos + CR_RECORD_HDR;
    uint8_t *dst  = (uint8_t *)out_buf;
    for (uint32_t i = 0; i < len; i++)
        dst[i] = cr_read_byte(r, base + i);
    r->read_pos = (r->read_pos + total) % r->capacity;
}

/* ============================================================
 * Worker entry point — implement this in every codec worker
 *
 * argv[1] = session_id as decimal string
 *
 * Suggested worker main loop:
 *   1. parse argv[1] → session_id
 *   2. open + mmap /dev/shm/ailang_codec_<id>_pkt  (O_RDWR)
 *   3. open + mmap /dev/shm/ailang_codec_<id>_frm  (O_RDWR)
 *   4. init codec
 *   5. loop:
 *        read packet from pkt ring
 *        if CR_FLAG_EOF: flush decoder, write remaining frames, exit
 *        feed packet to decoder
 *        drain all available frames into frm ring
 * ============================================================ */

#endif /* AILANG_CODEC_ABI_H */
