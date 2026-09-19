/* MIDI → shm byte ring. Kernel MIDI_StreamFeed.
 * Rawmidi nodes plus ALSA sequencer (vmpk, USB clients).
 */
#include "midi_in.h"

#include <dirent.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

typedef struct snd_seq snd_seq_t;
typedef struct snd_seq_event snd_seq_event_t;
typedef struct snd_midi_event snd_midi_event_t;

static void *alsa;
static snd_seq_t *seq;
static snd_midi_event_t *midi_dec;
static int seq_port = -1;

static int (*fn_seq_open)(snd_seq_t **, const char *, int, int);
static int (*fn_seq_close)(snd_seq_t *);
static int (*fn_seq_set_client_name)(snd_seq_t *, const char *);
static int (*fn_seq_create_simple_port)(snd_seq_t *, const char *, unsigned, unsigned);
static int (*fn_seq_event_input)(snd_seq_t *, snd_seq_event_t **);
static int (*fn_seq_event_input_pending)(snd_seq_t *, int);
static int (*fn_midi_event_new)(size_t, snd_midi_event_t **);
static void (*fn_midi_event_free)(snd_midi_event_t *);
static long (*fn_midi_event_decode)(snd_midi_event_t *, unsigned char *, long, const snd_seq_event_t *);

static const int kCap = 4096;
static const int kHdr = 32;
static const int kMaxFd = 8;

struct MidiMap {
    uint8_t *base;
    size_t len;
    int fd;
};

static MidiMap map;
static int midi_fds[kMaxFd];
static int midi_n;
static int scan_div;

static uint64_t load_u64(const uint8_t *p) {
    uint64_t v = 0;
    memcpy(&v, p, 8);
    return v;
}

static void store_u64(uint8_t *p, uint64_t v) { memcpy(p, &v, 8); }

static void ring_push(const uint8_t *b, int n) {
    if (!map.base || n <= 0) return;
    uint64_t w = load_u64(map.base);
    uint64_t r = load_u64(map.base + 8);
    uint64_t cap = load_u64(map.base + 16);
    if (cap == 0) cap = kCap;
    uint8_t *data = map.base + kHdr;
    for (int i = 0; i < n; i++) {
        uint64_t used = w - r;
        if (used >= cap) break;
        data[w % cap] = b[i];
        w++;
    }
    store_u64(map.base, w);
}

static int seq_start(void) {
    alsa = dlopen("libasound.so.2", RTLD_NOW);
    if (!alsa) {
        fprintf(stderr, "synthkit midi: no libasound (vmpk needs ALSA seq)\n");
        return 0;
    }
    fn_seq_open = (int (*)(snd_seq_t **, const char *, int, int))dlsym(alsa, "snd_seq_open");
    fn_seq_close = (int (*)(snd_seq_t *))dlsym(alsa, "snd_seq_close");
    fn_seq_set_client_name = (int (*)(snd_seq_t *, const char *))dlsym(alsa, "snd_seq_set_client_name");
    fn_seq_create_simple_port =
        (int (*)(snd_seq_t *, const char *, unsigned, unsigned))dlsym(alsa, "snd_seq_create_simple_port");
    fn_seq_event_input = (int (*)(snd_seq_t *, snd_seq_event_t **))dlsym(alsa, "snd_seq_event_input");
    fn_seq_event_input_pending = (int (*)(snd_seq_t *, int))dlsym(alsa, "snd_seq_event_input_pending");
    fn_midi_event_new = (int (*)(size_t, snd_midi_event_t **))dlsym(alsa, "snd_midi_event_new");
    fn_midi_event_free = (void (*)(snd_midi_event_t *))dlsym(alsa, "snd_midi_event_free");
    fn_midi_event_decode =
        (long (*)(snd_midi_event_t *, unsigned char *, long, const snd_seq_event_t *))dlsym(alsa, "snd_midi_event_decode");
    if (!fn_seq_open || !fn_seq_create_simple_port || !fn_seq_event_input || !fn_midi_event_decode) {
        fprintf(stderr, "synthkit midi: alsa seq symbols missing\n");
        return 0;
    }
    /* SND_SEQ_OPEN_INPUT=2, SND_SEQ_NONBLOCK=1 */
    if (fn_seq_open(&seq, "default", 2, 1) < 0) {
        fprintf(stderr, "synthkit midi: snd_seq_open failed\n");
        seq = NULL;
        return 0;
    }
    fn_seq_set_client_name(seq, "SynthKit");
    /* WRITE | SUBS_WRITE so vmpk can connect to us */
    seq_port = fn_seq_create_simple_port(seq, "in", (1u << 1) | (1u << 6), (1u << 1) | (1u << 20));
    if (seq_port < 0) {
        fprintf(stderr, "synthkit midi: create port failed\n");
        return 0;
    }
    fn_midi_event_new(256, &midi_dec);
    fprintf(stderr, "synthkit midi: ALSA seq port 'SynthKit:in' (connect vmpk here)\n");
    return 1;
}

static void seq_poll(void) {
    if (!seq || !fn_seq_event_input_pending || !fn_seq_event_input) return;
    while (fn_seq_event_input_pending(seq, 0) > 0) {
        snd_seq_event_t *ev = NULL;
        if (fn_seq_event_input(seq, &ev) < 0 || !ev) break;
        unsigned char out[12];
        long n = fn_midi_event_decode(midi_dec, out, (long)sizeof out, ev);
        if (n > 0) ring_push(out, (int)n);
    }
}

static void scan_ports(void) {
    for (int i = 0; i < midi_n; i++) {
        if (midi_fds[i] >= 0) close(midi_fds[i]);
        midi_fds[i] = -1;
    }
    midi_n = 0;
    DIR *d = opendir("/dev/snd");
    if (!d) return;
    struct dirent *e;
    while ((e = readdir(d)) != NULL) {
        if (strncmp(e->d_name, "midiC", 5) != 0) continue;
        if (midi_n >= kMaxFd) break;
        char path[128];
        snprintf(path, sizeof path, "/dev/snd/%s", e->d_name);
        int fd = open(path, O_RDONLY | O_NONBLOCK);
        if (fd < 0) continue;
        midi_fds[midi_n++] = fd;
        fprintf(stderr, "synthkit midi: %s\n", path);
    }
    closedir(d);
}

int synthkit_midi_init(const char *midi_path) {
    for (int i = 0; i < kMaxFd; i++) midi_fds[i] = -1;
    midi_n = 0;
    int fd = open(midi_path, O_RDWR | O_CREAT, 0666);
    if (fd < 0) {
        perror("midi.bin");
        return 0;
    }
    size_t total = (size_t)kHdr + (size_t)kCap;
    if (ftruncate(fd, (off_t)total) != 0) {
        perror("ftruncate midi");
        close(fd);
        return 0;
    }
    void *p = mmap(NULL, total, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (p == MAP_FAILED) {
        perror("mmap midi");
        close(fd);
        return 0;
    }
    map.base = (uint8_t *)p;
    map.len = total;
    map.fd = fd;
    store_u64(map.base, 0);
    store_u64(map.base + 8, 0);
    store_u64(map.base + 16, kCap);
    scan_ports();
    seq_start();
    return 1;
}

void synthkit_midi_poll(void) {
    seq_poll();
    if (++scan_div >= 40) {
        scan_div = 0;
        if (midi_n == 0) scan_ports();
    }
    uint8_t buf[256];
    for (int i = 0; i < midi_n; i++) {
        if (midi_fds[i] < 0) continue;
        ssize_t n = read(midi_fds[i], buf, sizeof buf);
        if (n > 0) ring_push(buf, (int)n);
        else if (n < 0) {
            close(midi_fds[i]);
            midi_fds[i] = -1;
        }
    }
}

void synthkit_midi_shutdown(void) {
    for (int i = 0; i < midi_n; i++) {
        if (midi_fds[i] >= 0) close(midi_fds[i]);
        midi_fds[i] = -1;
    }
    midi_n = 0;
    if (midi_dec && fn_midi_event_free) fn_midi_event_free(midi_dec);
    midi_dec = NULL;
    if (seq && fn_seq_close) fn_seq_close(seq);
    seq = NULL;
    if (alsa) dlclose(alsa);
    alsa = NULL;
    if (map.base) {
        munmap(map.base, map.len);
        map.base = NULL;
    }
    if (map.fd >= 0) {
        close(map.fd);
        map.fd = -1;
    }
}

int synthkit_midi_ports(void) { return midi_n + (seq ? 1 : 0); }
