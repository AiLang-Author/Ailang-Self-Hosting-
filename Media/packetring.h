/*
 * packetring.h — C mirror of Library.PacketRing.ailang
 * Shared memory SPSC ring buffer for cross-process media packet transport.
 *
 * Layout matches the Ailang implementation exactly — both sides can
 * produce/consume on the same shm file.
 *
 * Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
 */

#ifndef PACKETRING_H
#define PACKETRING_H

#include <stdint.h>
#include <stddef.h>

/* Header field offsets (64-byte header at start of shm region) */
#define PR_OFF_WRITE_POS    0
#define PR_OFF_READ_POS     8
#define PR_OFF_CAPACITY    16
#define PR_OFF_FLAGS       24
#define PR_OFF_WRAP_POS    32
#define PR_HEADER_SIZE     64

/* Packet header (16 bytes, at each packet in the data region) */
#define PR_PKT_SIZE         0   /* uint32_t: payload size */
#define PR_PKT_PTS_LO       4   /* uint32_t: PTS low 32 bits */
#define PR_PKT_PTS_HI       8   /* uint32_t: PTS high 32 bits */
#define PR_PKT_FLAGS        12  /* uint32_t: per-packet flags */
#define PR_PKT_HDR_SIZE     16

/* Ring-level flags */
#define PR_FLAG_FLUSH   1
#define PR_FLAG_EOF     2
#define PR_FLAG_ERROR   4

/* Per-packet flags */
#define PR_PKTFLAG_KEYFRAME  1
#define PR_PKTFLAG_CONFIG    2

typedef struct {
    void    *base;      /* mmap'd pointer (header + data) */
    size_t   shm_size;  /* total mmap size */
} PacketRing;

/*
 * Create a new ring (producer side).
 * name:     identifier string (becomes /dev/shm/ailang_media_ring_<name>)
 * capacity: data region size in bytes (should be power of 2)
 * Returns 0 on failure.
 */
int pr_create(PacketRing *ring, const char *name, size_t capacity);

/*
 * Open an existing ring (consumer side).
 * Returns 0 on failure.
 */
int pr_open(PacketRing *ring, const char *name);

/*
 * Unmap and unlink (producer cleanup).
 */
void pr_destroy(PacketRing *ring, const char *name);

/*
 * Unmap only (consumer cleanup, doesn't unlink).
 */
void pr_close(PacketRing *ring);

/*
 * Write a packet into the ring.
 * Returns 1 on success, 0 if insufficient space.
 */
int pr_write(PacketRing *ring, const void *data, uint32_t size,
             int64_t pts_usec, uint32_t flags);

/*
 * Read a packet from the ring.
 * out_buf must be large enough for the payload.
 * Returns 1 on success, 0 if ring empty.
 */
int pr_read(PacketRing *ring, void *out_buf,
            uint32_t *out_size, int64_t *out_pts, uint32_t *out_flags);

/*
 * Peek at next packet metadata without consuming.
 * Returns 1 if packet available, 0 if empty.
 */
int pr_peek(PacketRing *ring,
            uint32_t *out_size, int64_t *out_pts, uint32_t *out_flags);

/* Signal ring-level flags */
void pr_signal_eof(PacketRing *ring);
void pr_signal_flush(PacketRing *ring);
void pr_signal_error(PacketRing *ring);

/* Check ring-level flags */
int pr_is_eof(PacketRing *ring);
int pr_is_flush(PacketRing *ring);
int pr_is_error(PacketRing *ring);

/* Clear all flags */
void pr_clear_flags(PacketRing *ring);

/* Reset ring (clear data + positions, used on seek) */
void pr_reset(PacketRing *ring);

/* Helper: read header fields */
static inline uint64_t pr_read64(PacketRing *ring, int offset) {
    return *(volatile uint64_t *)((uint8_t *)ring->base + offset);
}
static inline void pr_write64(PacketRing *ring, int offset, uint64_t val) {
    *(volatile uint64_t *)((uint8_t *)ring->base + offset) = val;
}
static inline uint32_t pr_read32_at(void *base, int offset) {
    return *(volatile uint32_t *)((uint8_t *)base + offset);
}
static inline void pr_write32_at(void *base, int offset, uint32_t val) {
    *(volatile uint32_t *)((uint8_t *)base + offset) = val;
}

#endif /* PACKETRING_H */
