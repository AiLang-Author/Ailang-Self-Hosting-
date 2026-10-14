/* ALSA playback and capture names for the desk patch bay.
 * Reads /proc/asound only. Does not open a PCM or a control device.
 * The card is the one that owns the first playback PCM. Each line is
 * the driver's own PCM name: "O <device> <name>" or "I <device> <name>".
 *
 * Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.
 */
#include <ctype.h>
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define MAX_PCM 64
#define NAME_N 48

typedef struct {
    int card;
    int dev;
    int play;
    char name[NAME_N];
} Pcm;

static void trim_copy(char *dst, int n, const char *src) {
    while (*src == ' ' || *src == '\t') {
        src++;
    }
    int i = 0;
    while (src[i] != 0 && src[i] != '\n' && src[i] != '\r' && i < n - 1) {
        dst[i] = src[i];
        i++;
    }
    while (i > 0 && (dst[i - 1] == ' ' || dst[i - 1] == '\t')) {
        i--;
    }
    dst[i] = 0;
}

static int parse_pcm(const char *ent, int *dev, int *play) {
    if (strncmp(ent, "pcm", 3) != 0) {
        return 0;
    }
    const char *s = ent + 3;
    if (!isdigit((unsigned char)*s)) {
        return 0;
    }
    int d = 0;
    while (isdigit((unsigned char)*s)) {
        d = d * 10 + (*s - '0');
        s++;
    }
    if ((*s != 'p' && *s != 'c') || s[1] != 0) {
        return 0;
    }
    *dev = d;
    *play = (*s == 'p');
    return 1;
}

static int card_number(const char *ent) {
    if (strncmp(ent, "card", 4) != 0) {
        return -1;
    }
    const char *s = ent + 4;
    if (!isdigit((unsigned char)*s)) {
        return -1;
    }
    int n = 0;
    while (isdigit((unsigned char)*s)) {
        n = n * 10 + (*s - '0');
        s++;
    }
    if (*s != 0) {
        return -1;
    }
    return n;
}

static void read_pcm_name(const char *path, char *name) {
    name[0] = 0;
    char id[NAME_N];
    id[0] = 0;
    FILE *f = fopen(path, "r");
    if (!f) {
        return;
    }
    char line[256];
    while (fgets(line, sizeof line, f)) {
        if (strncmp(line, "name: ", 6) == 0) {
            trim_copy(name, NAME_N, line + 6);
        } else if (strncmp(line, "id: ", 4) == 0) {
            trim_copy(id, NAME_N, line + 4);
        }
    }
    fclose(f);
    if (name[0] == 0) {
        trim_copy(name, NAME_N, id);
    }
}

static int by_dev(const void *a, const void *b) {
    const Pcm *pa = a;
    const Pcm *pb = b;
    if (pa->play != pb->play) {
        return pb->play - pa->play;
    }
    return pa->dev - pb->dev;
}

static void fallback(Pcm *p) {
    if (p->name[0] != 0) {
        return;
    }
    if (p->play) {
        snprintf(p->name, NAME_N, "Playback %d", p->dev);
    } else {
        snprintf(p->name, NAME_N, "Capture %d", p->dev);
    }
}

static void unique_names(Pcm *list, int n) {
    int clash[MAX_PCM];
    for (int i = 0; i < n; i++) {
        clash[i] = 0;
    }
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            if (list[i].play == list[j].play && strcmp(list[i].name, list[j].name) == 0) {
                clash[i] = 1;
                clash[j] = 1;
            }
        }
    }
    for (int i = 0; i < n; i++) {
        if (!clash[i]) {
            continue;
        }
        char buf[NAME_N];
        snprintf(buf, NAME_N, "%s %d", list[i].name, list[i].dev);
        memcpy(list[i].name, buf, NAME_N);
    }
}

int main(int argc, char **argv) {
    const char *dest = "/dev/shm/daw/alsa_io.txt";
    if (argc > 1 && argv[1] != 0 && argv[1][0] != 0) {
        dest = argv[1];
    }
    mkdir("/dev/shm/daw", 0755);
    Pcm all[MAX_PCM];
    int n = 0;
    DIR *root = opendir("/proc/asound");
    if (!root) {
        return 1;
    }
    struct dirent *ent;
    while ((ent = readdir(root)) != 0) {
        int card = card_number(ent->d_name);
        if (card < 0) {
            continue;
        }
        char dirpath[320];
        snprintf(dirpath, sizeof dirpath, "/proc/asound/%s", ent->d_name);
        DIR *carddir = opendir(dirpath);
        if (!carddir) {
            continue;
        }
        struct dirent *pcm;
        while ((pcm = readdir(carddir)) != 0 && n < MAX_PCM) {
            int dev = 0;
            int play = 0;
            if (!parse_pcm(pcm->d_name, &dev, &play)) {
                continue;
            }
            char info[384];
            snprintf(info, sizeof info, "%s/%s/info", dirpath, pcm->d_name);
            all[n].card = card;
            all[n].dev = dev;
            all[n].play = play;
            all[n].name[0] = 0;
            read_pcm_name(info, all[n].name);
            n++;
        }
        closedir(carddir);
    }
    closedir(root);
    int want = -1;
    for (int i = 0; i < n; i++) {
        if (!all[i].play) {
            continue;
        }
        if (want < 0 || all[i].card < want) {
            want = all[i].card;
        }
    }
    Pcm keep[MAX_PCM];
    int k = 0;
    for (int i = 0; i < n; i++) {
        if (all[i].card != want) {
            continue;
        }
        keep[k] = all[i];
        fallback(&keep[k]);
        k++;
    }
    qsort(keep, (size_t)k, sizeof(Pcm), by_dev);
    unique_names(keep, k);
    FILE *out = fopen(dest, "w");
    if (!out) {
        return 1;
    }
    for (int i = 0; i < k; i++) {
        char kind = keep[i].play ? 'O' : 'I';
        fprintf(out, "%c %d %s\n", kind, keep[i].dev, keep[i].name);
    }
    fclose(out);
    return 0;
}
