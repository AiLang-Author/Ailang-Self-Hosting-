/*
 * playbackclock.c — C mirror of Library.PlaybackClock.ailang
 * Wall-clock anchored playback synchronization over /dev/shm.
 *
 * Layout matches the Ailang implementation exactly.
 *
 * Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
 */

#include "playbackclock.h"

#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <time.h>
#include <sys/mman.h>

static void build_path(char *buf, size_t bufsz, const char *name) {
    snprintf(buf, bufsz, "/dev/shm/ailang_media_clock_%s", name);
}

int64_t pc_mono_usec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)ts.tv_sec * 1000000 + ts.tv_nsec / 1000;
}

int pc_create(PlaybackClock *clk, const char *name) {
    char path[256];
    build_path(path, sizeof(path), name);

    int fd = open(path, O_CREAT | O_RDWR, 0666);
    if (fd < 0) {
        fprintf(stderr, "[PlaybackClock] open failed: %s\n", path);
        return 0;
    }

    if (ftruncate(fd, PC_SHM_SIZE) < 0) {
        close(fd);
        return 0;
    }

    void *ptr = mmap(NULL, PC_SHM_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);

    if (ptr == MAP_FAILED) {
        fprintf(stderr, "[PlaybackClock] mmap failed\n");
        return 0;
    }

    clk->base = ptr;

    /* Initialize */
    pc_write64(clk, PC_OFF_STATE,       PC_STOPPED);
    pc_write64(clk, PC_OFF_EPOCH,       0);
    pc_write64(clk, PC_OFF_PAUSE_OFF,   0);
    pc_write64(clk, PC_OFF_RATE_NUM,    1000);
    pc_write64(clk, PC_OFF_RATE_DEN,    1000);
    pc_write64(clk, PC_OFF_SEEK_TARGET, 0);
    pc_write64(clk, PC_OFF_AUDIO_HW,    0);
    pc_write64(clk, PC_OFF_PAUSE_START, 0);

    fprintf(stderr, "[PlaybackClock] created: %s\n", path);
    return 1;
}

int pc_open(PlaybackClock *clk, const char *name) {
    char path[256];
    build_path(path, sizeof(path), name);

    int fd = open(path, O_RDWR);
    if (fd < 0) {
        fprintf(stderr, "[PlaybackClock] open failed: %s\n", path);
        return 0;
    }

    void *ptr = mmap(NULL, PC_SHM_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);

    if (ptr == MAP_FAILED) {
        fprintf(stderr, "[PlaybackClock] mmap failed\n");
        return 0;
    }

    clk->base = ptr;
    fprintf(stderr, "[PlaybackClock] opened: %s\n", path);
    return 1;
}

void pc_destroy(PlaybackClock *clk, const char *name) {
    if (clk->base) {
        munmap(clk->base, PC_SHM_SIZE);
        clk->base = NULL;
    }
    char path[256];
    build_path(path, sizeof(path), name);
    unlink(path);
}

void pc_close(PlaybackClock *clk) {
    if (clk->base) {
        munmap(clk->base, PC_SHM_SIZE);
        clk->base = NULL;
    }
}

void pc_play(PlaybackClock *clk) {
    int64_t now = pc_mono_usec();
    pc_write64(clk, PC_OFF_EPOCH,       now);
    pc_write64(clk, PC_OFF_PAUSE_OFF,   0);
    pc_write64(clk, PC_OFF_PAUSE_START, 0);
    pc_write64(clk, PC_OFF_AUDIO_HW,    0);
    pc_write64(clk, PC_OFF_STATE,       PC_PLAYING);
}

void pc_pause(PlaybackClock *clk) {
    if (pc_read64(clk, PC_OFF_STATE) != PC_PLAYING)
        return;
    int64_t now = pc_mono_usec();
    pc_write64(clk, PC_OFF_PAUSE_START, now);
    pc_write64(clk, PC_OFF_STATE,       PC_PAUSED);
}

void pc_resume(PlaybackClock *clk) {
    if (pc_read64(clk, PC_OFF_STATE) != PC_PAUSED)
        return;
    int64_t now = pc_mono_usec();
    int64_t pause_start = pc_read64(clk, PC_OFF_PAUSE_START);
    int64_t pause_dur = now - pause_start;
    int64_t old_off = pc_read64(clk, PC_OFF_PAUSE_OFF);
    pc_write64(clk, PC_OFF_PAUSE_OFF,   old_off + pause_dur);
    pc_write64(clk, PC_OFF_PAUSE_START, 0);
    pc_write64(clk, PC_OFF_STATE,       PC_PLAYING);
}

void pc_stop(PlaybackClock *clk) {
    pc_write64(clk, PC_OFF_STATE, PC_STOPPED);
}

void pc_seek(PlaybackClock *clk, int64_t target_usec) {
    pc_write64(clk, PC_OFF_SEEK_TARGET, target_usec);
    pc_write64(clk, PC_OFF_STATE,       PC_SEEKING);
}

void pc_seek_done(PlaybackClock *clk) {
    int64_t target = pc_read64(clk, PC_OFF_SEEK_TARGET);
    int64_t now = pc_mono_usec();
    pc_write64(clk, PC_OFF_EPOCH,     now - target);
    pc_write64(clk, PC_OFF_PAUSE_OFF, 0);
    pc_write64(clk, PC_OFF_STATE,     PC_PLAYING);
}

void pc_set_rate(PlaybackClock *clk, int64_t num, int64_t den) {
    if (pc_read64(clk, PC_OFF_STATE) == PC_PLAYING) {
        int64_t cur = pc_media_time(clk);
        int64_t now = pc_mono_usec();
        /* Re-anchor: new_epoch = now - cur_media * new_den / new_num */
        int64_t new_epoch = now - (cur * den / num);
        pc_write64(clk, PC_OFF_EPOCH,     new_epoch);
        pc_write64(clk, PC_OFF_PAUSE_OFF, 0);
    }
    pc_write64(clk, PC_OFF_RATE_NUM, num);
    pc_write64(clk, PC_OFF_RATE_DEN, den);
}

void pc_set_audio_hw_pos(PlaybackClock *clk, int64_t frames) {
    pc_write64(clk, PC_OFF_AUDIO_HW, frames);
}

int64_t pc_media_time(PlaybackClock *clk) {
    int64_t state = pc_read64(clk, PC_OFF_STATE);

    if (state == PC_STOPPED)
        return 0;

    int64_t epoch     = pc_read64(clk, PC_OFF_EPOCH);
    int64_t pause_off = pc_read64(clk, PC_OFF_PAUSE_OFF);
    int64_t rate_num  = pc_read64(clk, PC_OFF_RATE_NUM);
    int64_t rate_den  = pc_read64(clk, PC_OFF_RATE_DEN);

    if (state == PC_PAUSED) {
        int64_t pause_start = pc_read64(clk, PC_OFF_PAUSE_START);
        int64_t elapsed = pause_start - epoch - pause_off;
        return elapsed * rate_num / rate_den;
    }

    /* PLAYING or SEEKING */
    int64_t now = pc_mono_usec();
    int64_t elapsed = now - epoch - pause_off;
    return elapsed * rate_num / rate_den;
}

int pc_get_state(PlaybackClock *clk) {
    return (int)pc_read64(clk, PC_OFF_STATE);
}

int64_t pc_get_seek_target(PlaybackClock *clk) {
    return pc_read64(clk, PC_OFF_SEEK_TARGET);
}
