/*
 * packetring.c — C mirror of Library.PacketRing.ailang
 * Shared memory SPSC ring buffer for cross-process media packet transport.
 *
 * Layout matches the Ailang implementation exactly.
 *
 * Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
 */

#include "packetring.h"

#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>

/* Build shm path: /dev/shm/ailang_media_ring_<name> */
static void build_path(char *buf, size_t bufsz, const char *name) {
    snprintf(buf, bufsz, "/dev/shm/ailang_media_ring_%s", name);
}

int pr_create(PacketRing *ring, const char *name, size_t capacity) {
    char path[256];
    build_path(path, sizeof(path), name);

    size_t shm_size = PR_HEADER_SIZE + capacity;

    int fd = open(path, O_CREAT | O_RDWR, 0666);
    if (fd < 0) {
        fprintf(stderr, "[PacketRing] open failed: %s\n", path);
        return 0;
    }

    if (ftruncate(fd, shm_size) < 0) {
        close(fd);
        fprintf(stderr, "[PacketRing] ftruncate failed: %s\n", path);
        return 0;
    }

    void *ptr = mmap(NULL, shm_size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);

    if (ptr == MAP_FAILED) {
        fprintf(stderr, "[PacketRing] mmap failed: %s\n", path);
        return 0;
    }

    ring->base = ptr;
    ring->shm_size = shm_size;

    /* Initialize header */
    pr_write64(ring, PR_OFF_WRITE_POS, 0);
    pr_write64(ring, PR_OFF_READ_POS,  0);
    pr_write64(ring, PR_OFF_CAPACITY,  capacity);
    pr_write64(ring, PR_OFF_FLAGS,     0);
    pr_write64(ring, PR_OFF_WRAP_POS,  capacity);

    fprintf(stderr, "[PacketRing] created: %s capacity=%zu\n", path, capacity);
    return 1;
}

int pr_open(PacketRing *ring, const char *name) {
    char path[256];
    build_path(path, sizeof(path), name);

    int fd = open(path, O_RDWR);
    if (fd < 0) {
        fprintf(stderr, "[PacketRing] open failed: %s\n", path);
        return 0;
    }

    /* First mmap just the header to read capacity */
    void *hdr = mmap(NULL, PR_HEADER_SIZE, PROT_READ, MAP_SHARED, fd, 0);
    if (hdr == MAP_FAILED) {
        close(fd);
        fprintf(stderr, "[PacketRing] header mmap failed: %s\n", path);
        return 0;
    }
    uint64_t capacity = *(uint64_t *)((uint8_t *)hdr + PR_OFF_CAPACITY);
    munmap(hdr, PR_HEADER_SIZE);

    /* Full mmap */
    size_t shm_size = PR_HEADER_SIZE + capacity;
    void *ptr = mmap(NULL, shm_size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);

    if (ptr == MAP_FAILED) {
        fprintf(stderr, "[PacketRing] full mmap failed: %s\n", path);
        return 0;
    }

    ring->base = ptr;
    ring->shm_size = shm_size;

    fprintf(stderr, "[PacketRing] opened: %s capacity=%lu\n", path, (unsigned long)capacity);
    return 1;
}

void pr_destroy(PacketRing *ring, const char *name) {
    if (ring->base) {
        munmap(ring->base, ring->shm_size);
        ring->base = NULL;
    }
    char path[256];
    build_path(path, sizeof(path), name);
    unlink(path);
}

void pr_close(PacketRing *ring) {
    if (ring->base) {
        munmap(ring->base, ring->shm_size);
        ring->base = NULL;
    }
}

int pr_write(PacketRing *ring, const void *data, uint32_t size,
             int64_t pts_usec, uint32_t flags) {
    uint32_t total = PR_PKT_HDR_SIZE + size;

    uint64_t wp  = pr_read64(ring, PR_OFF_WRITE_POS);
    uint64_t rp  = pr_read64(ring, PR_OFF_READ_POS);
    uint64_t cap = pr_read64(ring, PR_OFF_CAPACITY);
    uint64_t free_space;

    if (wp >= rp) {
        free_space = cap - wp + rp - 1;
        uint64_t tail_room = cap - wp;
        if (tail_room < total) {
            /* Wrap: set sentinel, move wp to 0 */
            pr_write64(ring, PR_OFF_WRAP_POS, wp);
            wp = 0;
            free_space = rp - 1;
            if (free_space < total)
                return 0;
        } else if (free_space < total) {
            return 0;
        }
    } else {
        free_space = rp - wp - 1;
        if (free_space < total)
            return 0;
    }

    /* Write packet header */
    uint8_t *base = (uint8_t *)ring->base + PR_HEADER_SIZE + wp;
    pr_write32_at(base, PR_PKT_SIZE,   size);
    pr_write32_at(base, PR_PKT_PTS_LO, (uint32_t)(pts_usec & 0xFFFFFFFF));
    pr_write32_at(base, PR_PKT_PTS_HI, (uint32_t)((pts_usec >> 32) & 0xFFFFFFFF));
    pr_write32_at(base, PR_PKT_FLAGS,  flags);

    /* Copy payload */
    if (size > 0)
        memcpy(base + PR_PKT_HDR_SIZE, data, size);

    /* Advance write_pos */
    uint64_t new_wp = wp + total;
    if (new_wp >= cap) {
        new_wp = 0;
        pr_write64(ring, PR_OFF_WRAP_POS, cap);
    }
    pr_write64(ring, PR_OFF_WRITE_POS, new_wp);

    return 1;
}

int pr_read(PacketRing *ring, void *out_buf,
            uint32_t *out_size, int64_t *out_pts, uint32_t *out_flags) {
    uint64_t wp   = pr_read64(ring, PR_OFF_WRITE_POS);
    uint64_t rp   = pr_read64(ring, PR_OFF_READ_POS);
    uint64_t wrap = pr_read64(ring, PR_OFF_WRAP_POS);
    uint64_t cap  = pr_read64(ring, PR_OFF_CAPACITY);

    /* Handle wrap */
    if (rp >= wrap)
        rp = 0;

    /* Empty? */
    if (rp == wp)
        return 0;

    /* Read packet header */
    uint8_t *base = (uint8_t *)ring->base + PR_HEADER_SIZE + rp;
    uint32_t pkt_size  = pr_read32_at(base, PR_PKT_SIZE);
    uint32_t pts_lo    = pr_read32_at(base, PR_PKT_PTS_LO);
    uint32_t pts_hi    = pr_read32_at(base, PR_PKT_PTS_HI);
    uint32_t pkt_flags = pr_read32_at(base, PR_PKT_FLAGS);

    *out_size  = pkt_size;
    *out_pts   = (int64_t)pts_lo | ((int64_t)pts_hi << 32);
    *out_flags = pkt_flags;

    /* Copy payload */
    if (pkt_size > 0)
        memcpy(out_buf, base + PR_PKT_HDR_SIZE, pkt_size);

    /* Advance read_pos */
    uint64_t new_rp = rp + PR_PKT_HDR_SIZE + pkt_size;
    if (new_rp >= cap)
        new_rp = 0;
    pr_write64(ring, PR_OFF_READ_POS, new_rp);

    return 1;
}

int pr_peek(PacketRing *ring,
            uint32_t *out_size, int64_t *out_pts, uint32_t *out_flags) {
    uint64_t wp   = pr_read64(ring, PR_OFF_WRITE_POS);
    uint64_t rp   = pr_read64(ring, PR_OFF_READ_POS);
    uint64_t wrap = pr_read64(ring, PR_OFF_WRAP_POS);

    if (rp >= wrap)
        rp = 0;
    if (rp == wp)
        return 0;

    uint8_t *base = (uint8_t *)ring->base + PR_HEADER_SIZE + rp;
    uint32_t pkt_size  = pr_read32_at(base, PR_PKT_SIZE);
    uint32_t pts_lo    = pr_read32_at(base, PR_PKT_PTS_LO);
    uint32_t pts_hi    = pr_read32_at(base, PR_PKT_PTS_HI);
    uint32_t pkt_flags = pr_read32_at(base, PR_PKT_FLAGS);

    *out_size  = pkt_size;
    *out_pts   = (int64_t)pts_lo | ((int64_t)pts_hi << 32);
    *out_flags = pkt_flags;

    return 1;
}

void pr_signal_eof(PacketRing *ring) {
    uint64_t f = pr_read64(ring, PR_OFF_FLAGS);
    pr_write64(ring, PR_OFF_FLAGS, f | PR_FLAG_EOF);
}

void pr_signal_flush(PacketRing *ring) {
    uint64_t f = pr_read64(ring, PR_OFF_FLAGS);
    pr_write64(ring, PR_OFF_FLAGS, f | PR_FLAG_FLUSH);
}

void pr_signal_error(PacketRing *ring) {
    uint64_t f = pr_read64(ring, PR_OFF_FLAGS);
    pr_write64(ring, PR_OFF_FLAGS, f | PR_FLAG_ERROR);
}

int pr_is_eof(PacketRing *ring) {
    return (pr_read64(ring, PR_OFF_FLAGS) & PR_FLAG_EOF) ? 1 : 0;
}

int pr_is_flush(PacketRing *ring) {
    return (pr_read64(ring, PR_OFF_FLAGS) & PR_FLAG_FLUSH) ? 1 : 0;
}

int pr_is_error(PacketRing *ring) {
    return (pr_read64(ring, PR_OFF_FLAGS) & PR_FLAG_ERROR) ? 1 : 0;
}

void pr_clear_flags(PacketRing *ring) {
    pr_write64(ring, PR_OFF_FLAGS, 0);
}

void pr_reset(PacketRing *ring) {
    uint64_t cap = pr_read64(ring, PR_OFF_CAPACITY);
    pr_write64(ring, PR_OFF_WRITE_POS, 0);
    pr_write64(ring, PR_OFF_READ_POS,  0);
    pr_write64(ring, PR_OFF_WRAP_POS,  cap);
    pr_write64(ring, PR_OFF_FLAGS,     0);
}
