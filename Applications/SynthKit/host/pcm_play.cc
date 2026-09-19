/* Playhead: mmap pcm.bin ring, miniaudio callback. Kernel writes frames. */
#define MINIAUDIO_IMPLEMENTATION
#define MA_NO_ENCODING
#define MA_NO_FLAC
#define MA_NO_MP3
#define MA_NO_GENERATION
#include "miniaudio.h"

#include "pcm_play.h"

#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

static const int kHdr = 64;
static const int kCap = 8192;

struct PcmMap {
    uint8_t *base;
    size_t len;
    int fd;
};

static PcmMap map;
static ma_device device;
static int device_ok;

static uint64_t load_u64(const uint8_t *p) {
    uint64_t v = 0;
    memcpy(&v, p, 8);
    return v;
}

static void store_u64(uint8_t *p, uint64_t v) {
    memcpy(p, &v, 8);
}

static void data_callback(ma_device *, void *out, const void *, ma_uint32 frames) {
    auto *dst = (int16_t *)out;
    memset(dst, 0, (size_t)frames * 4);
    if (!map.base) return;
    uint64_t w = load_u64(map.base + 16);
    uint64_t r = load_u64(map.base + 24);
    uint64_t cap = load_u64(map.base + 8);
    if (cap == 0) cap = kCap;
    uint64_t avail = w - r;
    if (avail > cap) avail = cap;
    uint32_t n = frames;
    if ((uint64_t)n > avail) n = (uint32_t)avail;
    uint8_t *data = map.base + kHdr;
    for (uint32_t i = 0; i < n; i++) {
        uint64_t slot = (r + i) % cap;
        memcpy(dst + i * 2, data + slot * 4, 4);
    }
    store_u64(map.base + 24, r + n);
}

int synthkit_audio_init(const char *pcm_path) {
    int fd = open(pcm_path, O_RDWR | O_CREAT, 0666);
    if (fd < 0) {
        perror("pcm.bin");
        return 0;
    }
    size_t total = (size_t)kHdr + (size_t)kCap * 4;
    if (ftruncate(fd, (off_t)total) != 0) {
        perror("ftruncate pcm");
        close(fd);
        return 0;
    }
    void *p = mmap(NULL, total, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (p == MAP_FAILED) {
        perror("mmap pcm");
        close(fd);
        return 0;
    }
    map.base = (uint8_t *)p;
    map.len = total;
    map.fd = fd;
    store_u64(map.base + 8, kCap);

    ma_device_config cfg = ma_device_config_init(ma_device_type_playback);
    cfg.playback.format = ma_format_s16;
    cfg.playback.channels = 2;
    cfg.sampleRate = 48000;
    cfg.periodSizeInFrames = 256;
    cfg.dataCallback = data_callback;
    if (ma_device_init(NULL, &cfg, &device) != MA_SUCCESS) {
        fprintf(stderr, "synthkit audio: ma_device_init failed\n");
        return 0;
    }
    store_u64(map.base + 32, device.sampleRate ? device.sampleRate : 48000);
    if (ma_device_start(&device) != MA_SUCCESS) {
        fprintf(stderr, "synthkit audio: start failed\n");
        ma_device_uninit(&device);
        return 0;
    }
    device_ok = 1;
    fprintf(stderr, "synthkit audio: %u Hz stereo s16 (DAC callback is the clock)\n",
            device.sampleRate);
    return 1;
}

void synthkit_audio_shutdown(void) {
    if (device_ok) {
        ma_device_uninit(&device);
        device_ok = 0;
    }
    if (map.base) {
        munmap(map.base, map.len);
        map.base = NULL;
    }
    if (map.fd >= 0) {
        close(map.fd);
        map.fd = -1;
    }
}
