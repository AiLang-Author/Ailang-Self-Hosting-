/*
 * playbackclock.h — C mirror of Library.PlaybackClock.ailang
 * Wall-clock anchored playback synchronization over /dev/shm.
 *
 * Layout matches the Ailang implementation exactly.
 *
 * Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
 */

#ifndef PLAYBACKCLOCK_H
#define PLAYBACKCLOCK_H

#include <stdint.h>

/* Field offsets (64-byte shm region) */
#define PC_OFF_STATE        0
#define PC_OFF_EPOCH        8
#define PC_OFF_PAUSE_OFF   16
#define PC_OFF_RATE_NUM    24
#define PC_OFF_RATE_DEN    32
#define PC_OFF_SEEK_TARGET 40
#define PC_OFF_AUDIO_HW    48
#define PC_OFF_PAUSE_START 56
#define PC_SHM_SIZE        64

/* Playback states */
#define PC_STOPPED  0
#define PC_PLAYING  1
#define PC_PAUSED   2
#define PC_SEEKING  3

typedef struct {
    void *base;  /* mmap'd pointer to 64-byte region */
} PlaybackClock;

/* Lifecycle */
int  pc_create(PlaybackClock *clk, const char *name);
int  pc_open(PlaybackClock *clk, const char *name);
void pc_destroy(PlaybackClock *clk, const char *name);
void pc_close(PlaybackClock *clk);

/* Control (presenter writes these) */
void pc_play(PlaybackClock *clk);
void pc_pause(PlaybackClock *clk);
void pc_resume(PlaybackClock *clk);
void pc_stop(PlaybackClock *clk);
void pc_seek(PlaybackClock *clk, int64_t target_usec);
void pc_seek_done(PlaybackClock *clk);
void pc_set_rate(PlaybackClock *clk, int64_t num, int64_t den);
void pc_set_audio_hw_pos(PlaybackClock *clk, int64_t frames);

/* Queries (any node reads these) */
int64_t pc_media_time(PlaybackClock *clk);
int     pc_get_state(PlaybackClock *clk);
int64_t pc_get_seek_target(PlaybackClock *clk);

/* Monotonic clock helper */
int64_t pc_mono_usec(void);

/* Raw field access */
static inline int64_t pc_read64(PlaybackClock *clk, int offset) {
    return *(volatile int64_t *)((uint8_t *)clk->base + offset);
}
static inline void pc_write64(PlaybackClock *clk, int offset, int64_t val) {
    *(volatile int64_t *)((uint8_t *)clk->base + offset) = val;
}

#endif /* PLAYBACKCLOCK_H */
