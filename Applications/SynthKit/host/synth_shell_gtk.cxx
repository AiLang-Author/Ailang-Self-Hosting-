/* synth_shell_gtk — keys + knobs. Kernel owns the synth.
 *
 *   SYNTH_APP_STATE=/dev/shm/synth_app ./host/synth_shell_gtk
 *
 * Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.
 */
#include <gtk/gtk.h>

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "midi_in.h"
#include "surge_fxp.h"

static char dir[512];
static char path_keys[600], path_ctl[600], path_cmd[600], path_pcm[600], path_midi[600];
static char path_song[600], path_song_cmd[600], path_surge[600], path_heard[600];
static char heard_last[256];

static int k_c, k_d, k_e, k_f, k_g, k_a, k_b, k_sus;
static int wave = 0, cutoff = 256, res = 0, delayms = 0, fb = 0, wet = 0, vol = 80, atk = 4, dec = 200, rel = 200, oct = 2, pw = 128;
static int detune = 0, fenv = 0, lforate = 0, lfopwm = 0, submix = 0, drive = 0;
static int wave2 = 0, oscmix = 0, o2oct = 2, suslvl = 256, lfofilt = 0, lfoamp = 0;
static int modv = 0, md0 = 0, ma0 = 0, md1 = 0, ma1 = 0, md2 = 0, ma2 = 0;
static int applying;
static void set_sc(GtkWidget *s, int *var, int v);

static GtkWidget *lbl_status;
static GtkWidget *win_main;
static GtkWidget *btn_patch;
static GtkWidget *btn_song;
static char surge_path[700];
static char song_path[700];
static GtkWidget *combo_wave;
static GtkWidget *combo_wave2;
static GtkWidget *lbl_wave;
static GtkWidget *lbl_wave2;
static GtkWidget *sc[25];
static GtkWidget *combo_md[3];
static char presets_dir[700];

static void write_file(const char *path, const char *s) {
    char tmp[600];
    snprintf(tmp, sizeof tmp, "%s.tmp", path);
    FILE *f = fopen(tmp, "w");
    if (!f) return;
    fputs(s, f);
    fclose(f);
    rename(tmp, path);
}

static void write_keys(void) {
    char buf[16];
    snprintf(buf, sizeof buf, "%d%d%d%d%d%d%d%d\n",
             k_c, k_d, k_e, k_f, k_g, k_a, k_b, k_sus);
    write_file(path_keys, buf);
}

static int ctl_ints[31];

static void load_ctl_file(void) {
    FILE *f = fopen(path_ctl, "r");
    if (!f) return;
    int n = 0;
    while (n < 31 && fscanf(f, "%d", &ctl_ints[n]) == 1) n++;
    fclose(f);
    if (n < 22) return;
    applying = 1;
    wave = ctl_ints[0];
    cutoff = ctl_ints[1];
    res = ctl_ints[2];
    delayms = ctl_ints[3];
    fb = ctl_ints[4];
    wet = ctl_ints[5];
    vol = ctl_ints[6];
    atk = ctl_ints[7];
    dec = ctl_ints[8];
    rel = ctl_ints[9];
    oct = ctl_ints[10];
    pw = ctl_ints[11];
    detune = ctl_ints[12];
    fenv = ctl_ints[13];
    lforate = ctl_ints[14];
    lfopwm = ctl_ints[15];
    submix = ctl_ints[16];
    drive = ctl_ints[17];
    wave2 = ctl_ints[18];
    oscmix = ctl_ints[19];
    o2oct = ctl_ints[20];
    suslvl = ctl_ints[21];
    if (n > 22) lfofilt = ctl_ints[22];
    if (n > 23) lfoamp = ctl_ints[23];
    if (wave < 0) wave = 0;
    if (wave > 7) wave = 7;
    if (wave2 < 0) wave2 = 0;
    if (wave2 > 7) wave2 = 7;
    if (combo_wave) gtk_combo_box_set_active(GTK_COMBO_BOX(combo_wave), wave);
    if (combo_wave2) gtk_combo_box_set_active(GTK_COMBO_BOX(combo_wave2), wave2);
    set_sc(sc[0], &cutoff, cutoff);
    set_sc(sc[1], &res, res);
    set_sc(sc[2], &pw, pw);
    set_sc(sc[3], &detune, detune);
    set_sc(sc[4], &fenv, fenv);
    set_sc(sc[5], &submix, submix);
    set_sc(sc[6], &drive, drive);
    set_sc(sc[7], &lforate, lforate);
    set_sc(sc[8], &lfopwm, lfopwm);
    set_sc(sc[9], &atk, atk);
    set_sc(sc[10], &dec, dec);
    set_sc(sc[11], &rel, rel);
    set_sc(sc[12], &vol, vol);
    set_sc(sc[13], &delayms, delayms);
    set_sc(sc[14], &fb, fb);
    set_sc(sc[15], &wet, wet);
    set_sc(sc[20], &oscmix, oscmix);
    set_sc(sc[21], &o2oct, o2oct);
    set_sc(sc[22], &suslvl, suslvl);
    set_sc(sc[23], &lfofilt, lfofilt);
    set_sc(sc[24], &lfoamp, lfoamp);
    applying = 0;
}

static void write_ctl(void) {
    char buf[384];
    snprintf(buf, sizeof buf,
             "%d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d\n",
             wave, cutoff, res, delayms, fb, wet, vol, atk, dec, rel, oct, pw,
             detune, fenv, lforate, lfopwm, submix, drive,
             wave2, oscmix, o2oct, suslvl, lfofilt, lfoamp,
             modv, md0, ma0, md1, ma1, md2, ma2);
    write_file(path_ctl, buf);
}

static void write_cmd(const char *s) { write_file(path_cmd, s); }

static void write_song_cmd(const char *s) { write_file(path_song_cmd, s); }

static void slurp_line(const char *path, char *dest, size_t n) {
    FILE *f = fopen(path, "r");
    if (n) dest[0] = 0;
    if (!f || n < 2) {
        if (f) fclose(f);
        return;
    }
    if (!fgets(dest, (int)n, f)) dest[0] = 0;
    fclose(f);
    size_t L = strlen(dest);
    while (L && (dest[L - 1] == '\n' || dest[L - 1] == '\r')) dest[--L] = 0;
}

static const char *base_name(const char *path) {
    const char *s = strrchr(path, '/');
    if (s && s[1]) return s + 1;
    return path;
}

static void set_btn_name(GtkWidget *btn, const char *fallback, const char *path) {
    if (!btn) return;
    if (!path || !path[0]) {
        gtk_button_set_label(GTK_BUTTON(btn), fallback);
        return;
    }
    char lab[200];
    snprintf(lab, sizeof lab, "%s", base_name(path));
    gtk_button_set_label(GTK_BUTTON(btn), lab);
}

/* GtkFileChooserButton aborts in gtkpathbar when the folder changes
   (GTK 3.24.41). The system dialog runs out of process. */
static int pick_path(const char *title, const char *folder, const char *cur,
                     const char *filt_name, const char *pat1, const char *pat2,
                     char *dest, size_t destn) {
    GtkFileChooserNative *native = gtk_file_chooser_native_new(
        title, GTK_WINDOW(win_main), GTK_FILE_CHOOSER_ACTION_OPEN,
        "_Open", "_Cancel");
    GtkFileFilter *pf = gtk_file_filter_new();
    gtk_file_filter_set_name(pf, filt_name);
    gtk_file_filter_add_pattern(pf, pat1);
    if (pat2 && pat2[0]) gtk_file_filter_add_pattern(pf, pat2);
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(native), pf);
    if (cur && cur[0] && g_file_test(cur, G_FILE_TEST_EXISTS))
        gtk_file_chooser_set_filename(GTK_FILE_CHOOSER(native), cur);
    else if (folder && folder[0])
        gtk_file_chooser_set_current_folder(GTK_FILE_CHOOSER(native), folder);
    int ok = 0;
    if (gtk_native_dialog_run(GTK_NATIVE_DIALOG(native)) == GTK_RESPONSE_ACCEPT) {
        char *fn = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(native));
        if (fn && fn[0]) {
            snprintf(dest, destn, "%s", fn);
            ok = 1;
        }
        g_free(fn);
    }
    g_object_unref(native);
    return ok;
}

static void on_song_play(GtkButton *, gpointer) {
    if (song_path[0]) {
        char line[700];
        snprintf(line, sizeof line, "%s\n", song_path);
        write_file(path_song, line);
        fprintf(stderr, "synth: song %s\n", song_path);
    }
    write_song_cmd("play\n");
}
static void on_song_stop(GtkButton *, gpointer) { write_song_cmd("stop\n"); }

static int map_key(guint kv, int on) {
    int *slot = NULL;
    if (kv == GDK_KEY_c || kv == GDK_KEY_C) slot = &k_c;
    else if (kv == GDK_KEY_d || kv == GDK_KEY_D) slot = &k_d;
    else if (kv == GDK_KEY_e || kv == GDK_KEY_E) slot = &k_e;
    else if (kv == GDK_KEY_f || kv == GDK_KEY_F) slot = &k_f;
    else if (kv == GDK_KEY_g || kv == GDK_KEY_G) slot = &k_g;
    else if (kv == GDK_KEY_a || kv == GDK_KEY_A) slot = &k_a;
    else if (kv == GDK_KEY_b || kv == GDK_KEY_B) slot = &k_b;
    else if (kv == GDK_KEY_bracketleft || kv == GDK_KEY_z || kv == GDK_KEY_Z) {
        if (on && oct > 0) { oct--; write_ctl(); }
        return 1;
    } else if (kv == GDK_KEY_bracketright || kv == GDK_KEY_x || kv == GDK_KEY_X) {
        if (on && oct < 4) { oct++; write_ctl(); }
        return 1;
    } else if (kv == GDK_KEY_space) {
        k_sus = on ? 1 : 0;
        write_keys();
        return 1;
    } else return 0;
    *slot = on ? 1 : 0;
    write_keys();
    return 1;
}

static gboolean on_key(GtkWidget *, GdkEventKey *e, gpointer) {
    if (e->keyval == GDK_KEY_Escape || e->keyval == GDK_KEY_q || e->keyval == GDK_KEY_Q) {
        write_cmd("quit");
        gtk_main_quit();
        return TRUE;
    }
    if (e->type == GDK_KEY_PRESS && (e->state & GDK_CONTROL_MASK) == 0)
        if (map_key(e->keyval, 1)) return TRUE;
    return FALSE;
}

static gboolean on_key_up(GtkWidget *, GdkEventKey *e, gpointer) {
    if (map_key(e->keyval, 0)) return TRUE;
    return FALSE;
}

static gboolean on_delete(GtkWidget *, GdkEvent *, gpointer) {
    write_cmd("quit");
    gtk_main_quit();
    return TRUE;
}

static void on_scale(GtkRange *r, gpointer p) {
    *static_cast<int *>(p) = (int)gtk_range_get_value(r);
    if (!applying) write_ctl();
}

static void on_wave(GtkComboBox *c, gpointer) {
    wave = gtk_combo_box_get_active(c);
    if (wave < 0) wave = 0;
    if (!applying) write_ctl();
}

static void on_wave2(GtkComboBox *c, gpointer) {
    wave2 = gtk_combo_box_get_active(c);
    if (wave2 < 0) wave2 = 0;
    if (!applying) write_ctl();
}

static const char *wave_names[] = {
    "Sine", "Square", "Pulse", "Saw", "Tri", "Noise", "NES tri", "User"
};

static void fill_wave(GtkComboBoxText *c) {
    for (int i = 0; i < 8; i++)
        gtk_combo_box_text_append_text(c, wave_names[i]);
}

/* Rebuild the menu. GTK 3.24 keeps the old word painted on the closed
   combo after set_active from a timer, so the row list is replaced. */
static void show_wave(GtkWidget *combo, gpointer cb, GtkWidget *lab,
                      const char *prefix, int active) {
    if (active < 0) active = 0;
    if (active > 7) active = 7;
    if (combo) {
        if (cb) g_signal_handlers_block_by_func(combo, cb, NULL);
        gtk_combo_box_text_remove_all(GTK_COMBO_BOX_TEXT(combo));
        fill_wave(GTK_COMBO_BOX_TEXT(combo));
        gtk_combo_box_set_active(GTK_COMBO_BOX(combo), active);
        if (cb) g_signal_handlers_unblock_by_func(combo, cb, NULL);
    }
    if (lab) {
        char t[64];
        snprintf(t, sizeof t, "%s: %s", prefix, wave_names[active]);
        gtk_label_set_text(GTK_LABEL(lab), t);
    }
}

static int json_nth_int(const char *js, const char *key, int nth, int def) {
    char pat[80];
    snprintf(pat, sizeof pat, "\"%s\"", key);
    const char *p = js;
    for (int i = 0; i <= nth; i++) {
        p = strstr(p, pat);
        if (!p) return def;
        if (i < nth) {
            p += strlen(pat);
            continue;
        }
        const char *c = strchr(p + strlen(pat), ':');
        if (!c) return def;
        return atoi(c + 1);
    }
    return def;
}

static int json_int(const char *js, const char *key, int def) {
    return json_nth_int(js, key, 0, def);
}

static void apply_values_to_widgets(void) {
    if (combo_wave) gtk_combo_box_set_active(GTK_COMBO_BOX(combo_wave), wave);
    if (combo_wave2) gtk_combo_box_set_active(GTK_COMBO_BOX(combo_wave2), wave2);
    if (combo_md[0]) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(combo_md[0]), md0);
        gtk_combo_box_set_active(GTK_COMBO_BOX(combo_md[1]), md1);
        gtk_combo_box_set_active(GTK_COMBO_BOX(combo_md[2]), md2);
    }
    set_sc(sc[0], &cutoff, cutoff);
    set_sc(sc[1], &res, res);
    set_sc(sc[2], &pw, pw);
    set_sc(sc[3], &detune, detune);
    set_sc(sc[4], &fenv, fenv);
    set_sc(sc[5], &submix, submix);
    set_sc(sc[6], &drive, drive);
    set_sc(sc[7], &lforate, lforate);
    set_sc(sc[8], &lfopwm, lfopwm);
    set_sc(sc[9], &atk, atk);
    set_sc(sc[10], &dec, dec);
    set_sc(sc[11], &rel, rel);
    set_sc(sc[12], &vol, vol);
    set_sc(sc[13], &delayms, delayms);
    set_sc(sc[14], &fb, fb);
    set_sc(sc[15], &wet, wet);
    set_sc(sc[16], &modv, modv);
    set_sc(sc[17], &ma0, ma0);
    set_sc(sc[18], &ma1, ma1);
    set_sc(sc[19], &ma2, ma2);
    set_sc(sc[20], &oscmix, oscmix);
    set_sc(sc[21], &o2oct, o2oct);
    set_sc(sc[22], &suslvl, suslvl);
    set_sc(sc[23], &lfofilt, lfofilt);
    set_sc(sc[24], &lfoamp, lfoamp);
}

static int load_patch_file(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    char *js = (char *)malloc(65536);
    if (!js) {
        fclose(f);
        return 0;
    }
    size_t n = fread(js, 1, 65535, f);
    fclose(f);
    js[n] = 0;
    if (!strstr(js, "synthkit.patch.v1")) {
        free(js);
        return 0;
    }
    applying = 1;
    wave = json_int(js, "wave", wave);
    wave2 = json_int(js, "wave2", wave2);
    oscmix = json_int(js, "osc_mix", oscmix);
    o2oct = json_int(js, "osc2_oct", o2oct);
    cutoff = json_int(js, "cutoff", cutoff);
    res = json_int(js, "res", res);
    delayms = json_int(js, "delay_ms", delayms);
    fb = json_int(js, "delay_fb", fb);
    wet = json_int(js, "delay_wet", wet);
    vol = json_int(js, "vol", vol);
    atk = json_int(js, "atk_ms", atk);
    dec = json_int(js, "dec_ms", dec);
    rel = json_int(js, "rel_ms", rel);
    suslvl = json_int(js, "sustain", suslvl);
    oct = json_int(js, "oct", oct);
    pw = json_int(js, "pw", pw);
    detune = json_int(js, "detune", detune);
    fenv = json_int(js, "fenv", fenv);
    lforate = json_int(js, "lfo_rate", lforate);
    lfopwm = json_int(js, "lfo_pwm", lfopwm);
    lfofilt = json_int(js, "lfo_filt", lfofilt);
    lfoamp = json_int(js, "lfo_amp", lfoamp);
    submix = json_int(js, "submix", submix);
    drive = json_int(js, "drive", drive);
    modv = json_int(js, "value", modv);
    md0 = json_nth_int(js, "dest", 0, md0);
    ma0 = json_nth_int(js, "depth", 0, ma0);
    md1 = json_nth_int(js, "dest", 1, md1);
    ma1 = json_nth_int(js, "depth", 1, ma1);
    md2 = json_nth_int(js, "dest", 2, md2);
    ma2 = json_nth_int(js, "depth", 2, ma2);
    apply_values_to_widgets();
    applying = 0;
    write_ctl();
    free(js);
    return 1;
}

static int save_patch_file(const char *path) {
    FILE *f = fopen(path, "w");
    if (!f) return 0;
    const char *slash = strrchr(path, '/');
    const char *stem = slash ? slash + 1 : path;
    char name[96];
    snprintf(name, sizeof name, "%s", stem);
    char *dot = strrchr(name, '.');
    if (dot) *dot = 0;
    fprintf(f,
            "{\n"
            "  \"format\": \"synthkit.patch.v1\",\n"
            "  \"name\": \"%s\",\n"
            "  \"engine\": {\n"
            "    \"wave\": %d,\n"
            "    \"wave2\": %d,\n"
            "    \"osc_mix\": %d,\n"
            "    \"osc2_oct\": %d,\n"
            "    \"cutoff\": %d,\n"
            "    \"res\": %d,\n"
            "    \"delay_ms\": %d,\n"
            "    \"delay_fb\": %d,\n"
            "    \"delay_wet\": %d,\n"
            "    \"vol\": %d,\n"
            "    \"atk_ms\": %d,\n"
            "    \"dec_ms\": %d,\n"
            "    \"rel_ms\": %d,\n"
            "    \"sustain\": %d,\n"
            "    \"oct\": %d,\n"
            "    \"pw\": %d,\n"
            "    \"detune\": %d,\n"
            "    \"fenv\": %d,\n"
            "    \"lfo_rate\": %d,\n"
            "    \"lfo_pwm\": %d,\n"
            "    \"lfo_filt\": %d,\n"
            "    \"lfo_amp\": %d,\n"
            "    \"submix\": %d,\n"
            "    \"drive\": %d\n"
            "  },\n"
            "  \"mod\": {\n"
            "    \"value\": %d,\n"
            "    \"slots\": [\n"
            "      {\"dest\": %d, \"depth\": %d},\n"
            "      {\"dest\": %d, \"depth\": %d},\n"
            "      {\"dest\": %d, \"depth\": %d}\n"
            "    ]\n"
            "  }\n"
            "}\n",
            name, wave, wave2, oscmix, o2oct, cutoff, res, delayms, fb, wet, vol,
            atk, dec, rel, suslvl, oct, pw, detune, fenv, lforate, lfopwm,
            lfofilt, lfoamp, submix, drive, modv, md0, ma0, md1, ma1, md2, ma2);
    fclose(f);
    return 1;
}

static void on_save_patch(GtkButton *, gpointer) {
    GtkWidget *d = gtk_file_chooser_dialog_new(
        "Save patch", GTK_WINDOW(win_main), GTK_FILE_CHOOSER_ACTION_SAVE,
        "_Cancel", GTK_RESPONSE_CANCEL, "_Save", GTK_RESPONSE_ACCEPT, NULL);
    gtk_file_chooser_set_do_overwrite_confirmation(GTK_FILE_CHOOSER(d), TRUE);
    gtk_file_chooser_set_current_folder(GTK_FILE_CHOOSER(d), presets_dir);
    gtk_file_chooser_set_current_name(GTK_FILE_CHOOSER(d), "patch.json");
    GtkFileFilter *jf = gtk_file_filter_new();
    gtk_file_filter_set_name(jf, "SynthKit patch");
    gtk_file_filter_add_pattern(jf, "*.json");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(d), jf);
    if (gtk_dialog_run(GTK_DIALOG(d)) == GTK_RESPONSE_ACCEPT) {
        char *fn = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(d));
        if (fn) {
            save_patch_file(fn);
            g_free(fn);
        }
    }
    gtk_widget_destroy(d);
}

static void on_load_patch(GtkButton *, gpointer) {
    GtkWidget *d = gtk_file_chooser_dialog_new(
        "Load patch", GTK_WINDOW(win_main), GTK_FILE_CHOOSER_ACTION_OPEN,
        "_Cancel", GTK_RESPONSE_CANCEL, "_Open", GTK_RESPONSE_ACCEPT, NULL);
    gtk_file_chooser_set_current_folder(GTK_FILE_CHOOSER(d), presets_dir);
    GtkFileFilter *jf = gtk_file_filter_new();
    gtk_file_filter_set_name(jf, "SynthKit patch");
    gtk_file_filter_add_pattern(jf, "*.json");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(d), jf);
    if (gtk_dialog_run(GTK_DIALOG(d)) == GTK_RESPONSE_ACCEPT) {
        char *fn = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(d));
        if (fn) {
            load_patch_file(fn);
            g_free(fn);
        }
    }
    gtk_widget_destroy(d);
}

static void fill_dest(GtkComboBoxText *c) {
    gtk_combo_box_text_append_text(c, "Off");
    gtk_combo_box_text_append_text(c, "Cutoff");
    gtk_combo_box_text_append_text(c, "Res");
    gtk_combo_box_text_append_text(c, "Pitch");
    gtk_combo_box_text_append_text(c, "LFO depth");
    gtk_combo_box_text_append_text(c, "PWM");
    gtk_combo_box_text_append_text(c, "Drive");
    gtk_combo_box_text_append_text(c, "Amp");
    gtk_combo_box_text_append_text(c, "Delay wet");
    gtk_combo_box_text_append_text(c, "Filt env");
    gtk_combo_box_text_append_text(c, "Sub");
}

static void on_md(GtkComboBox *c, gpointer p) {
    int slot = GPOINTER_TO_INT(p);
    int v = gtk_combo_box_get_active(c);
    if (v < 0) v = 0;
    if (slot == 0) md0 = v;
    else if (slot == 1) md1 = v;
    else md2 = v;
    if (!applying) write_ctl();
}

static GtkWidget *mk_scale(GtkWidget *grid, int col, int row, const char *name,
                           int lo, int hi, int *val, int def) {
    GtkWidget *lab = gtk_label_new(name);
    gtk_widget_set_halign(lab, GTK_ALIGN_START);
    gtk_grid_attach(GTK_GRID(grid), lab, col, row, 1, 1);
    GtkWidget *s = gtk_scale_new_with_range(GTK_ORIENTATION_HORIZONTAL, lo, hi, 1);
    gtk_range_set_value(GTK_RANGE(s), def);
    gtk_widget_set_hexpand(s, TRUE);
    gtk_widget_set_can_focus(s, FALSE);
    gtk_scale_set_value_pos(GTK_SCALE(s), GTK_POS_RIGHT);
    *val = def;
    g_signal_connect(s, "value-changed", G_CALLBACK(on_scale), val);
    gtk_grid_attach(GTK_GRID(grid), s, col + 1, row, 1, 1);
    return s;
}

static void set_sc(GtkWidget *s, int *var, int v) {
    *var = v;
    if (s) gtk_range_set_value(GTK_RANGE(s), v);
}

static void apply_preset(int id) {
    applying = 1;
    wave2 = 3; oscmix = 0; o2oct = 2; suslvl = 180; lfofilt = 0; lfoamp = 0;
    if (id == 1) { /* Analog Lead */
        wave = 3; cutoff = 105; res = 110; delayms = 0; fb = 0; wet = 0; vol = 170;
        atk = 4; dec = 220; rel = 320; pw = 64; detune = 8; fenv = 230;
        lforate = 0; lfopwm = 0; submix = 90; drive = 55;
        wave2 = 3; oscmix = 0; o2oct = 2;
    } else if (id == 2) { /* Fat Bass */
        wave = 3; cutoff = 72; res = 95; delayms = 0; fb = 0; wet = 0; vol = 190;
        atk = 2; dec = 280; rel = 120; pw = 64; detune = 7; fenv = 200;
        lforate = 0; lfopwm = 0; submix = 180; drive = 80;
        wave2 = 1; oscmix = 110; o2oct = 1; suslvl = 200;
    } else if (id == 3) { /* PWM Pad */
        wave = 2; cutoff = 110; res = 55; delayms = 380; fb = 90; wet = 140; vol = 150;
        atk = 120; dec = 400; rel = 1400; pw = 40; detune = 10; fenv = 120;
        lforate = 36; lfopwm = 180; submix = 40; drive = 35;
        wave2 = 4; oscmix = 128; o2oct = 2; lfoamp = 40; suslvl = 200;
    } else if (id == 4) { /* Pluck */
        wave = 3; cutoff = 95; res = 80; delayms = 0; fb = 0; wet = 0; vol = 180;
        atk = 1; dec = 140; rel = 180; pw = 64; detune = 5; fenv = 256;
        lforate = 0; lfopwm = 0; submix = 60; drive = 40;
        wave2 = 3; oscmix = 0; o2oct = 2; suslvl = 40;
    } else if (id == 5) { /* Square Lead */
        wave = 1; cutoff = 120; res = 70; delayms = 0; fb = 0; wet = 0; vol = 160;
        atk = 6; dec = 180; rel = 280; pw = 128; detune = 6; fenv = 200;
        lforate = 18; lfopwm = 80; submix = 50; drive = 45;
        wave2 = 2; oscmix = 90; o2oct = 2;
    } else if (id == 6) { /* Dual Saw */
        wave = 3; cutoff = 118; res = 70; delayms = 0; fb = 0; wet = 0; vol = 165;
        atk = 4; dec = 240; rel = 280; pw = 64; detune = 12; fenv = 180;
        lforate = 0; lfopwm = 0; submix = 40; drive = 40;
        wave2 = 3; oscmix = 128; o2oct = 2; suslvl = 180;
    } else if (id == 7) { /* Octave Lead */
        wave = 3; cutoff = 112; res = 85; delayms = 0; fb = 0; wet = 0; vol = 160;
        atk = 6; dec = 200; rel = 300; pw = 64; detune = 6; fenv = 210;
        lforate = 22; lfopwm = 0; submix = 50; drive = 50;
        wave2 = 3; oscmix = 140; o2oct = 3; lfofilt = 60; suslvl = 160;
    } else { /* Init */
        wave = 0; cutoff = 256; res = 0; delayms = 0; fb = 0; wet = 0; vol = 200;
        atk = 8; dec = 80; rel = 180; pw = 64; detune = 0; fenv = 0;
        lforate = 0; lfopwm = 0; submix = 0; drive = 0;
        wave2 = 0; oscmix = 0; o2oct = 2; suslvl = 180; lfofilt = 0; lfoamp = 0;
    }
    if (id == 3) { md0 = 5; ma0 = 180; md1 = 8; ma1 = 120; md2 = 1; ma2 = 80; }
    else if (id == 0) { md0 = 0; ma0 = 0; md1 = 0; ma1 = 0; md2 = 0; ma2 = 0; }
    else { md0 = 1; ma0 = 200; md1 = 0; ma1 = 0; md2 = 0; ma2 = 0; }
    apply_values_to_widgets();
    applying = 0;
    write_ctl();
}

static GtkWidget *lbl_patch;

static void apply_surge_file(const char *path) {
    char line[700];
    snprintf(line, sizeof line, "%s\n", path);
    write_file(path_surge, line);
    if (lbl_patch) {
        char msg[420];
        snprintf(msg, sizeof msg,
                 "%s — waveform and envelopes stay until you move those knobs.",
                 base_name(path));
        gtk_label_set_text(GTK_LABEL(lbl_patch), msg);
    }
    set_btn_name(btn_patch, "Choose preset…", path);
    fprintf(stderr, "synth: surge %s\n", path);
}

static const char *FACTORY = "/home/bob/.local/share/surge-xt/patches_factory";
static char preset_cat[80] = "Polysynths";

static int cmp_str(gconstpointer a, gconstpointer b) {
    return g_ascii_strcasecmp(*(char *const *)a, *(char *const *)b);
}

static GPtrArray *dir_names(const char *dir, int want_fxp) {
    GPtrArray *a = g_ptr_array_new_with_free_func(g_free);
    GDir *d = g_dir_open(dir, 0, NULL);
    if (!d) return a;
    const char *n;
    while ((n = g_dir_read_name(d))) {
        if (n[0] == '.') continue;
        char path[900];
        snprintf(path, sizeof path, "%s/%s", dir, n);
        if (want_fxp) {
            if (!g_str_has_suffix(n, ".fxp")) continue;
            if (!g_file_test(path, G_FILE_TEST_IS_REGULAR)) continue;
        } else if (!g_file_test(path, G_FILE_TEST_IS_DIR)) {
            continue;
        }
        g_ptr_array_add(a, g_strdup(n));
    }
    g_dir_close(d);
    if (a->len > 1) g_ptr_array_sort(a, cmp_str);
    return a;
}

static void clear_box(GtkWidget *box) {
    GList *ch = gtk_container_get_children(GTK_CONTAINER(box));
    for (GList *l = ch; l; l = l->next) gtk_widget_destroy(GTK_WIDGET(l->data));
    g_list_free(ch);
}

static void add_row(GtkListBox *box, const char *label, const char *key) {
    GtkWidget *row = gtk_list_box_row_new();
    GtkWidget *lab = gtk_label_new(label);
    gtk_label_set_xalign(GTK_LABEL(lab), 0);
    gtk_widget_set_margin_start(lab, 6);
    gtk_widget_set_margin_end(lab, 6);
    gtk_widget_set_margin_top(lab, 2);
    gtk_widget_set_margin_bottom(lab, 2);
    gtk_container_add(GTK_CONTAINER(row), lab);
    g_object_set_data_full(G_OBJECT(row), "key", g_strdup(key), g_free);
    gtk_container_add(GTK_CONTAINER(box), row);
    gtk_widget_show_all(row);
}

static void fill_fxps(GtkListBox *box, const char *dir) {
    clear_box(GTK_WIDGET(box));
    GPtrArray *names = dir_names(dir, 1);
    for (guint i = 0; i < names->len; i++) {
        const char *n = (const char *)names->pdata[i];
        char path[900];
        snprintf(path, sizeof path, "%s/%s", dir, n);
        add_row(box, n, path);
    }
    g_ptr_array_free(names, TRUE);
    GtkListBoxRow *first = gtk_list_box_get_row_at_index(box, 0);
    if (first) gtk_list_box_select_row(box, first);
}

static void on_cat_row(GtkListBox *, GtkListBoxRow *row, gpointer files) {
    if (!row) return;
    const char *name = (const char *)g_object_get_data(G_OBJECT(row), "key");
    if (!name) return;
    snprintf(preset_cat, sizeof preset_cat, "%s", name);
    char dir[900];
    snprintf(dir, sizeof dir, "%s/%s", FACTORY, name);
    fill_fxps(GTK_LIST_BOX(files), dir);
}

static void on_fxp_activate(GtkListBox *, GtkListBoxRow *, gpointer dlg) {
    gtk_dialog_response(GTK_DIALOG(dlg), GTK_RESPONSE_ACCEPT);
}

static void on_pick_patch(GtkButton *, gpointer) {
    GtkWidget *dlg = gtk_dialog_new_with_buttons(
        "Surge factory presets", GTK_WINDOW(win_main),
        GTK_DIALOG_MODAL,
        "_Cancel", GTK_RESPONSE_CANCEL,
        "_Open", GTK_RESPONSE_ACCEPT,
        NULL);
    gtk_window_set_default_size(GTK_WINDOW(dlg), 640, 480);
    GtkWidget *content = gtk_dialog_get_content_area(GTK_DIALOG(dlg));
    GtkWidget *panes = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_set_margin_start(panes, 8);
    gtk_widget_set_margin_end(panes, 8);
    gtk_widget_set_margin_top(panes, 8);
    gtk_widget_set_margin_bottom(panes, 8);
    gtk_box_pack_start(GTK_BOX(content), panes, TRUE, TRUE, 0);

    GtkWidget *cat_sc = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(cat_sc),
                                   GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_size_request(cat_sc, 160, -1);
    GtkWidget *cats = gtk_list_box_new();
    gtk_container_add(GTK_CONTAINER(cat_sc), cats);
    gtk_box_pack_start(GTK_BOX(panes), cat_sc, FALSE, FALSE, 0);

    GtkWidget *fxp_sc = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(fxp_sc),
                                   GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    GtkWidget *fxps = gtk_list_box_new();
    gtk_container_add(GTK_CONTAINER(fxp_sc), fxps);
    gtk_box_pack_start(GTK_BOX(panes), fxp_sc, TRUE, TRUE, 0);
    g_signal_connect(fxps, "row-activated", G_CALLBACK(on_fxp_activate), dlg);
    g_signal_connect(cats, "row-selected", G_CALLBACK(on_cat_row), fxps);

    GPtrArray *cnames = dir_names(FACTORY, 0);
    int sel = 0;
    for (guint i = 0; i < cnames->len; i++) {
        const char *n = (const char *)cnames->pdata[i];
        add_row(GTK_LIST_BOX(cats), n, n);
        if (strcmp(n, preset_cat) == 0) sel = (int)i;
    }
    g_ptr_array_free(cnames, TRUE);
    gtk_widget_show_all(dlg);
    GtkListBoxRow *crow = gtk_list_box_get_row_at_index(GTK_LIST_BOX(cats), sel);
    if (crow) gtk_list_box_select_row(GTK_LIST_BOX(cats), crow);

    if (gtk_dialog_run(GTK_DIALOG(dlg)) == GTK_RESPONSE_ACCEPT) {
        GtkListBoxRow *row = gtk_list_box_get_selected_row(GTK_LIST_BOX(fxps));
        const char *path = row ? (const char *)g_object_get_data(G_OBJECT(row), "key") : NULL;
        if (path && path[0]) {
            snprintf(surge_path, sizeof surge_path, "%s", path);
            apply_surge_file(surge_path);
        }
    }
    gtk_widget_destroy(dlg);
}

static void on_pick_song(GtkButton *, gpointer) {
    char got[700];
    if (!pick_path("MIDI file", "/home/bob/Downloads",
                   song_path, "MIDI", "*.mid", "*.midi", got, sizeof got))
        return;
    snprintf(song_path, sizeof song_path, "%s", got);
    char line[700];
    snprintf(line, sizeof line, "%s\n", song_path);
    write_file(path_song, line);
    fprintf(stderr, "synth: song %s\n", song_path);
    set_btn_name(btn_song, "Choose MIDI…", song_path);
}

static void on_preset(GtkComboBox *c, gpointer) {
    int id = gtk_combo_box_get_active(c);
    if (id < 0) id = 0;
    apply_preset(id);
}

static void osc_text(char *dst, size_t n, int typ, int wave) {
    const char *kind = "Other";
    const char *as = "saw";
    int gap = 1;
    if (wave == 0) as = "sine";
    else if (wave == 1) as = "square";
    else if (wave == 2) as = "pulse";
    else if (wave == 5) as = "noise";
    else as = "saw";
    if (typ == 0) { kind = "Classic"; gap = 0; }
    else if (typ == 1) { kind = "Sine"; gap = 0; }
    else if (typ == 2) kind = "Wavetable";
    else if (typ == 3) { kind = "Noise"; gap = 0; }
    else if (typ == 4) kind = "Audio input";
    else if (typ == 5) kind = "FM3";
    else if (typ == 6) kind = "FM2";
    else if (typ == 7) kind = "Window";
    else if (typ == 8) kind = "Modern";
    else if (typ == 10) kind = "Twist";
    if (gap)
        snprintf(dst, n, "%s, played as %s — that oscillator is not built yet", kind, as);
    else
        snprintf(dst, n, "%s %s", kind, as);
}

static void poll_heard(void) {
    if (!path_heard[0]) return;
    FILE *f = fopen(path_heard, "r");
    if (!f) return;
    char buf[256];
    if (!fgets(buf, sizeof buf, f)) {
        fclose(f);
        return;
    }
    fclose(f);
    if (strcmp(buf, heard_last) == 0) return;
    int w, w2, t1, t2, mix, cut, rs, a, d, s, r, em;
    if (sscanf(buf, "%d %d %d %d %d %d %d %d %d %d %d %d",
               &w, &w2, &t1, &t2, &mix, &cut, &rs, &a, &d, &s, &r, &em) != 12)
        return;
    snprintf(heard_last, sizeof heard_last, "%s", buf);
    applying = 1;
    wave = w;
    wave2 = w2;
    oscmix = mix;
    cutoff = cut;
    res = rs;
    atk = a;
    dec = d;
    suslvl = s;
    rel = r;
    fenv = 0;
    lforate = 0;
    lfopwm = 0;
    lfofilt = 0;
    lfoamp = 0;
    submix = 0;
    drive = 0;
    detune = 0;
    delayms = 0;
    fb = 0;
    wet = 0;
    if (wave < 0) wave = 0;
    if (wave > 7) wave = 7;
    if (wave2 < 0) wave2 = 0;
    if (wave2 > 7) wave2 = 7;
    show_wave(combo_wave, (gpointer)on_wave, lbl_wave, "wave 1", wave);
    show_wave(combo_wave2, (gpointer)on_wave2, lbl_wave2, "wave 2", wave2);
    set_sc(sc[0], &cutoff, cutoff);
    set_sc(sc[1], &res, res);
    set_sc(sc[3], &detune, 0);
    set_sc(sc[4], &fenv, 0);
    set_sc(sc[5], &submix, 0);
    set_sc(sc[6], &drive, 0);
    set_sc(sc[7], &lforate, 0);
    set_sc(sc[8], &lfopwm, 0);
    set_sc(sc[9], &atk, atk);
    set_sc(sc[10], &dec, dec);
    set_sc(sc[11], &rel, rel);
    set_sc(sc[13], &delayms, 0);
    set_sc(sc[14], &fb, 0);
    set_sc(sc[15], &wet, 0);
    set_sc(sc[20], &oscmix, oscmix);
    set_sc(sc[22], &suslvl, suslvl);
    set_sc(sc[23], &lfofilt, 0);
    set_sc(sc[24], &lfoamp, 0);
    applying = 0;
    if (lbl_patch) {
        char o1[120], o2[120], msg[360];
        osc_text(o1, sizeof o1, t1, wave);
        osc_text(o2, sizeof o2, t2, wave2);
        if (em)
            snprintf(msg, sizeof msg,
                     "Osc 1: %s. Osc 2: %s. Filter envelope is on.", o1, o2);
        else
            snprintf(msg, sizeof msg,
                     "Osc 1: %s. Osc 2: %s. No filter envelope.", o1, o2);
        gtk_label_set_text(GTK_LABEL(lbl_patch), msg);
        fprintf(stderr, "synth ui: %s\n", msg);
    }
}

static gboolean on_tick(gpointer) {
    poll_heard();
    write_keys();
    char buf[128];
    synthkit_midi_poll();
    snprintf(buf, sizeof buf, "CDEFGAB %d%d%d%d%d%d%d  SUS %d  MOD %d  oct %d  MIDI ports %d",
             k_c, k_d, k_e, k_f, k_g, k_a, k_b, k_sus, modv, oct - 2, synthkit_midi_ports());
    gtk_label_set_text(GTK_LABEL(lbl_status), buf);
    return TRUE;
}

int main(int argc, char **argv) {
    const char *d = "/dev/shm/synth_app";
    if (argc > 1 && argv[1] && argv[1][0]) d = argv[1];
    snprintf(dir, sizeof dir, "%s", d);
    mkdir(dir, 0755);
    snprintf(path_keys, sizeof path_keys, "%s/keys.txt", dir);
    snprintf(path_ctl, sizeof path_ctl, "%s/ctl.txt", dir);
    snprintf(path_surge, sizeof path_surge, "%s/surge.txt", dir);
    snprintf(path_heard, sizeof path_heard, "%s/heard.txt", dir);
    snprintf(path_cmd, sizeof path_cmd, "%s/cmd.txt", dir);
    snprintf(path_pcm, sizeof path_pcm, "%s/pcm.bin", dir);
    snprintf(path_midi, sizeof path_midi, "%s/midi.bin", dir);
    snprintf(path_song, sizeof path_song, "%s/song.txt", dir);
    snprintf(path_song_cmd, sizeof path_song_cmd, "%s/song_cmd.txt", dir);

    g_setenv("GTK_USE_PORTAL", "1", TRUE);
    gtk_init(&argc, &argv);
    if (!getcwd(presets_dir, sizeof presets_dir))
        snprintf(presets_dir, sizeof presets_dir, ".");
    {
        char tmp[700];
        snprintf(tmp, sizeof tmp, "%s/presets", presets_dir);
        mkdir(tmp, 0755);
        snprintf(presets_dir, sizeof presets_dir, "%s", tmp);
    }
    GtkWidget *win = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    win_main = win;
    gtk_window_set_title(GTK_WINDOW(win), "Synth");
    gtk_window_set_default_size(GTK_WINDOW(win), 720, 860);
    gtk_widget_add_events(win, GDK_KEY_PRESS_MASK | GDK_KEY_RELEASE_MASK);
    g_signal_connect(win, "delete-event", G_CALLBACK(on_delete), NULL);
    g_signal_connect(win, "key-press-event", G_CALLBACK(on_key), NULL);
    g_signal_connect(win, "key-release-event", G_CALLBACK(on_key_up), NULL);

    GtkWidget *vbox = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_container_set_border_width(GTK_CONTAINER(vbox), 12);
    gtk_container_add(GTK_CONTAINER(win), vbox);

    GtkWidget *hint = gtk_label_new(
        "Standalone synth. Load a Surge XT .fxp patch, then play the keys or a MIDI keyboard.\n"
        "C D E F G A B    Space = sustain    [ / Z oct down    ] / X up    Esc quit");
    gtk_label_set_xalign(GTK_LABEL(hint), 0);
    gtk_box_pack_start(GTK_BOX(vbox), hint, FALSE, FALSE, 0);

    GtkWidget *keys = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    const char *names[] = {"C", "D", "E", "F", "G", "A", "B"};
    for (int i = 0; i < 7; i++) {
        GtkWidget *b = gtk_button_new_with_label(names[i]);
        gtk_widget_set_can_focus(b, FALSE);
        gtk_box_pack_start(GTK_BOX(keys), b, TRUE, TRUE, 0);
    }
    gtk_box_pack_start(GTK_BOX(vbox), keys, FALSE, FALSE, 0);

    slurp_line(path_surge, surge_path, sizeof surge_path);
    slurp_line(path_song, song_path, sizeof song_path);
    if (!song_path[0] &&
        g_file_test("/home/bob/Downloads/Beverly Hills Cop Theme.mid", G_FILE_TEST_EXISTS))
        snprintf(song_path, sizeof song_path,
                 "/home/bob/Downloads/Beverly Hills Cop Theme.mid");

    GtkWidget *patchrow = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(patchrow), gtk_label_new("Surge patch"), FALSE, FALSE, 0);
    btn_patch = gtk_button_new_with_label("Choose preset…");
    gtk_widget_set_can_focus(btn_patch, FALSE);
    gtk_widget_set_hexpand(btn_patch, TRUE);
    set_btn_name(btn_patch, "Choose preset…", surge_path);
    g_signal_connect(btn_patch, "clicked", G_CALLBACK(on_pick_patch), NULL);
    gtk_box_pack_start(GTK_BOX(patchrow), btn_patch, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(vbox), patchrow, FALSE, FALSE, 0);
    lbl_patch = gtk_label_new("Sine until you load a Surge .fxp. The patch selects the waveform.");
    gtk_label_set_xalign(GTK_LABEL(lbl_patch), 0);
    gtk_label_set_line_wrap(GTK_LABEL(lbl_patch), TRUE);
    gtk_box_pack_start(GTK_BOX(vbox), lbl_patch, FALSE, FALSE, 0);
    if (surge_path[0]) {
        char msg[420];
        snprintf(msg, sizeof msg,
                 "%s — waveform and envelopes stay until you move those knobs.",
                 base_name(surge_path));
        gtk_label_set_text(GTK_LABEL(lbl_patch), msg);
    }

    GtkWidget *songrow = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(songrow), gtk_label_new("MIDI file"), FALSE, FALSE, 0);
    btn_song = gtk_button_new_with_label("Choose MIDI…");
    gtk_widget_set_can_focus(btn_song, FALSE);
    gtk_widget_set_hexpand(btn_song, TRUE);
    set_btn_name(btn_song, "Choose MIDI…", song_path);
    g_signal_connect(btn_song, "clicked", G_CALLBACK(on_pick_song), NULL);
    gtk_box_pack_start(GTK_BOX(songrow), btn_song, TRUE, TRUE, 0);
    GtkWidget *bplay = gtk_button_new_with_label("Play");
    GtkWidget *bstop = gtk_button_new_with_label("Stop");
    gtk_widget_set_can_focus(bplay, FALSE);
    gtk_widget_set_can_focus(bstop, FALSE);
    g_signal_connect(bplay, "clicked", G_CALLBACK(on_song_play), NULL);
    g_signal_connect(bstop, "clicked", G_CALLBACK(on_song_stop), NULL);
    gtk_box_pack_start(GTK_BOX(songrow), bplay, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(songrow), bstop, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(vbox), songrow, FALSE, FALSE, 0);

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll),
                                   GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_box_pack_start(GTK_BOX(vbox), scroll, TRUE, TRUE, 0);
    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(grid), 4);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 8);
    gtk_container_add(GTK_CONTAINER(scroll), grid);

    lbl_wave = gtk_label_new("wave 1: Sine");
    gtk_widget_set_halign(lbl_wave, GTK_ALIGN_START);
    gtk_grid_attach(GTK_GRID(grid), lbl_wave, 2, 0, 1, 1);
    combo_wave = gtk_combo_box_text_new();
    gtk_widget_set_can_focus(combo_wave, FALSE);
    fill_wave(GTK_COMBO_BOX_TEXT(combo_wave));
    gtk_combo_box_set_active(GTK_COMBO_BOX(combo_wave), 0);
    g_signal_connect(combo_wave, "changed", G_CALLBACK(on_wave), NULL);
    gtk_grid_attach(GTK_GRID(grid), combo_wave, 3, 0, 1, 1);

    lbl_wave2 = gtk_label_new("wave 2: Sine");
    gtk_widget_set_halign(lbl_wave2, GTK_ALIGN_START);
    gtk_grid_attach(GTK_GRID(grid), lbl_wave2, 0, 1, 1, 1);
    combo_wave2 = gtk_combo_box_text_new();
    gtk_widget_set_can_focus(combo_wave2, FALSE);
    fill_wave(GTK_COMBO_BOX_TEXT(combo_wave2));
    gtk_combo_box_set_active(GTK_COMBO_BOX(combo_wave2), 0);
    g_signal_connect(combo_wave2, "changed", G_CALLBACK(on_wave2), NULL);
    gtk_grid_attach(GTK_GRID(grid), combo_wave2, 1, 1, 1, 1);
    sc[20] = mk_scale(grid, 2, 1, "osc 2 level", 0, 256, &oscmix, 0);

    sc[21] = mk_scale(grid, 0, 2, "osc 2 octave", 0, 4, &o2oct, 2);
    sc[22] = mk_scale(grid, 2, 2, "sustain", 0, 256, &suslvl, 256);
    sc[23] = mk_scale(grid, 0, 3, "LFO to filter", 0, 256, &lfofilt, 0);
    sc[24] = mk_scale(grid, 2, 3, "LFO to loudness", 0, 256, &lfoamp, 0);

    sc[0] = mk_scale(grid, 0, 4, "cutoff", 0, 256, &cutoff, 256);
    sc[1] = mk_scale(grid, 2, 4, "resonance", 0, 240, &res, 0);
    sc[2] = mk_scale(grid, 0, 5, "pulse width", 8, 248, &pw, 128);
    sc[3] = mk_scale(grid, 2, 5, "detune cents", 0, 80, &detune, 0);
    sc[4] = mk_scale(grid, 0, 6, "filter envelope", 0, 256, &fenv, 0);
    sc[5] = mk_scale(grid, 2, 6, "sub oscillator", 0, 256, &submix, 0);
    sc[6] = mk_scale(grid, 0, 7, "drive", 0, 256, &drive, 0);
    sc[7] = mk_scale(grid, 2, 7, "LFO rate", 0, 256, &lforate, 0);
    sc[8] = mk_scale(grid, 0, 8, "LFO depth", 0, 256, &lfopwm, 0);
    sc[9] = mk_scale(grid, 2, 8, "attack ms", 0, 2500, &atk, 4);
    sc[10] = mk_scale(grid, 0, 9, "decay ms", 0, 2500, &dec, 200);
    sc[11] = mk_scale(grid, 2, 9, "release ms", 0, 4000, &rel, 200);
    sc[12] = mk_scale(grid, 0, 10, "master", 0, 2048, &vol, 80);
    sc[13] = mk_scale(grid, 2, 10, "delay ms", 0, 1300, &delayms, 0);
    sc[14] = mk_scale(grid, 0, 11, "delay feedback", 0, 250, &fb, 0);
    sc[15] = mk_scale(grid, 2, 11, "delay mix", 0, 256, &wet, 0);

    lbl_status = gtk_label_new("");
    gtk_widget_set_halign(lbl_status, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(vbox), lbl_status, FALSE, FALSE, 0);

    load_ctl_file();
    write_keys();
    write_ctl();
    write_cmd("");
    synthkit_midi_init(path_midi);
    g_timeout_add(30, on_tick, NULL);
    gtk_widget_show_all(win);
    gtk_main();
    write_cmd("quit");
    synthkit_midi_shutdown();
    return 0;
}
