#define _GNU_SOURCE
#include "surge_fxp.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

static const char *osc_name(int t) {
    static const char *names[] = {
        "Classic", "Sine", "Wavetable", "S&H Noise", "Audio In",
        "FM3", "FM2", "Window", "Modern", "String", "Twist", "Alias"};
    if (t < 0 || t > 11) return "unknown";
    return names[t];
}

static int find_tag(const char *xml, const char *tag, const char **value) {
    char pat[96];
    snprintf(pat, sizeof pat, "<%s ", tag);
    const char *p = strstr(xml, pat);
    if (!p) return 0;
    const char *v = strstr(p, "value=\"");
    if (!v || v - p > 64) return 0;
    *value = v + 7;
    return 1;
}

static int tag_float(const char *xml, const char *tag, float *out) {
    const char *v = 0;
    if (!find_tag(xml, tag, &v)) return 0;
    *out = strtof(v, 0);
    return 1;
}

static int tag_int(const char *xml, const char *tag, int *out) {
    const char *v = 0;
    if (!find_tag(xml, tag, &v)) return 0;
    *out = (int)strtol(v, 0, 10);
    return 1;
}

static int clampi(int v, int lo, int hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

/* Surge envelope times are stored as log2(seconds). */
static int env_ms(float log2_seconds) {
    double sec = pow(2.0, (double)log2_seconds);
    int ms = (int)(sec * 1000.0 + 0.5);
    return clampi(ms, 1, 8000);
}

/* Classic shape is bipolar: negative pulse/square, positive saw. */
static int classic_wave(float shape) {
    if (shape <= -0.35f) return 1;
    if (shape >= 0.35f) return 3;
    return 2;
}

static int osc_wave(int type, float shape, int *partial) {
    if (type == 1) return 0;
    if (type == 3) return 5;
    if (type == 0) return classic_wave(shape);
    *partial = 1;
    return 3;
}

int surge_fxp_map(const char *path, SurgeMapped *out) {
    memset(out, 0, sizeof *out);
    snprintf(out->title, sizeof out->title, "(no patch)");
    snprintf(out->note, sizeof out->note, "Could not read the Surge patch.");
    out->wave = 0;
    out->wave2 = 0;
    out->cutoff = 256;
    out->sus = 200;
    out->atk = 4;
    out->dec = 200;
    out->rel = 200;
    out->vol = 80;

    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return 0; }
    long n = ftell(f);
    if (n < 64 || n > 8000000) { fclose(f); return 0; }
    rewind(f);
    char *buf = (char *)malloc((size_t)n + 1);
    if (!buf) { fclose(f); return 0; }
    if (fread(buf, 1, (size_t)n, f) != (size_t)n) {
        free(buf);
        fclose(f);
        return 0;
    }
    fclose(f);
    buf[n] = 0;
    const char *xml = (const char *)memmem(buf, (size_t)n, "<patch", 6);
    if (!xml) { free(buf); return 0; }

    const char *meta = strstr(xml, "<meta ");
    char name[96];
    char cat[64];
    name[0] = 0;
    cat[0] = 0;
    if (meta) {
        const char *np = strstr(meta, "name=\"");
        const char *cp = strstr(meta, "category=\"");
        if (np && np - meta < 40) {
            np += 6;
            int i = 0;
            while (np[i] && np[i] != '"' && i < 95) { name[i] = np[i]; i++; }
            name[i] = 0;
        }
        if (cp && cp - meta < 200) {
            cp += 10;
            int i = 0;
            while (cp[i] && cp[i] != '"' && i < 63) { cat[i] = cp[i]; i++; }
            cat[i] = 0;
        }
    }
    if (name[0]) {
        if (cat[0]) snprintf(out->title, sizeof out->title, "%s / %s", cat, name);
        else snprintf(out->title, sizeof out->title, "%s", name);
    } else {
        snprintf(out->title, sizeof out->title, "%s", path);
    }

    int osc1 = 1, osc2 = 1;
    float shape1 = 0, shape2 = 0;
    float cut = 3, res = 0, fenv = 0;
    float atk = -8, dec = -2, sus = 1, rel = -5;
    float vol = -6, l1 = 1, l2 = 0;
    tag_int(xml, "a_osc1_type", &osc1);
    tag_int(xml, "a_osc2_type", &osc2);
    tag_float(xml, "a_osc1_param0", &shape1);
    tag_float(xml, "a_osc2_param0", &shape2);
    tag_float(xml, "a_filter1_cutoff", &cut);
    tag_float(xml, "a_filter1_resonance", &res);
    tag_float(xml, "a_filter1_envmod", &fenv);
    tag_float(xml, "a_env1_attack", &atk);
    tag_float(xml, "a_env1_decay", &dec);
    tag_float(xml, "a_env1_sustain", &sus);
    tag_float(xml, "a_env1_release", &rel);
    tag_float(xml, "volume", &vol);
    tag_float(xml, "a_level_o1", &l1);
    tag_float(xml, "a_level_o2", &l2);

    int partial = 0;
    out->wave = osc_wave(osc1, shape1, &partial);
    int partial2 = 0;
    out->wave2 = osc_wave(osc2, shape2, &partial2);
    float sum = l1 + l2;
    if (sum < 0.01f) sum = 1;
    out->oscmix = clampi((int)(256.0f * l2 / sum), 0, 256);
    /* Cutoff in the file is semitones, -60..70. Knob 0..256 matches that span. */
    out->cutoff = clampi((int)(((cut + 60.0f) / 130.0f) * 256.0f), 0, 256);
    out->res = clampi((int)(res * 240.0f), 0, 240);
    if (fenv < 0) fenv = -fenv;
    out->fenv = clampi((int)(fenv * 256.0f), 0, 256);
    out->atk = env_ms(atk);
    out->dec = env_ms(dec);
    out->sus = clampi((int)(sus * 256.0f), 0, 256);
    out->rel = env_ms(rel);
    double lin = pow(10.0, (double)vol / 20.0);
    out->vol = clampi((int)(256.0 * lin), 8, 512);

    if (partial || partial2)
        snprintf(out->note, sizeof out->note,
                 "Scene A. %s/%s is not built yet, so that oscillator plays as a saw. "
                 "Wavetable, FM, and effects in the patch are ignored.",
                 osc_name(osc1), osc_name(osc2));
    else
        snprintf(out->note, sizeof out->note,
                 "Scene A %s + %s, filter and amp envelope. "
                 "FX, LFOs, and scene B are not sounded yet.",
                 osc_name(osc1), osc_name(osc2));
    free(buf);
    return 1;
}
