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

#include "pcm_play.h"
#include "midi_in.h"

static char dir[512];
static char path_keys[600], path_ctl[600], path_cmd[600], path_pcm[600], path_bank[600], path_midi[600];
static char path_song[600], path_song_cmd[600];

static int k_c, k_d, k_e, k_f, k_g, k_a, k_b, k_sus;
static int wave, cutoff = 256, res, delayms, fb, wet, vol = 200, atk = 8, dec = 80, rel = 180, oct = 2, pw = 64;
static int detune, fenv, lforate, lfopwm, submix, drive;
static int wave2 = 3, oscmix, o2oct = 2, suslvl = 180, lfofilt, lfoamp;
static int modv, md0 = 1, ma0 = 200, md1, ma1, md2, ma2;
static int applying;
static void set_sc(GtkWidget *s, int *var, int v);

static GtkWidget *lbl_status;
static GtkWidget *win_main;
static GtkWidget *combo_wave;
static GtkWidget *combo_wave2;
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

static void write_bank(const char *p) {
    if (!p || !p[0]) return;
    write_file(path_bank, p);
    wave = 8;
    if (combo_wave) gtk_combo_box_set_active(GTK_COMBO_BOX(combo_wave), 8);
    write_ctl();
}

static void write_song_cmd(const char *s) { write_file(path_song_cmd, s); }

static void on_song_file(GtkFileChooserButton *b, gpointer) {
    char *fn = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(b));
    if (!fn) return;
    write_file(path_song, fn);
    g_free(fn);
}

static void on_song_play(GtkButton *, gpointer) { write_song_cmd("play\n"); }
static void on_song_stop(GtkButton *, gpointer) { write_song_cmd("stop\n"); }

static void on_bank_file(GtkFileChooserButton *b, gpointer) {
    char *fn = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(b));
    if (!fn) return;
    write_bank(fn);
    g_free(fn);
}

static void on_bank_combo(GtkComboBox *c, gpointer) {
    int id = gtk_combo_box_get_active(c);
    if (id <= 0) {
        wave = 3;
        if (combo_wave) gtk_combo_box_set_active(GTK_COMBO_BOX(combo_wave), 3);
        write_ctl();
        return;
    }
    const char *p = NULL;
    if (id == 1) p = "/home/bob/Downloads/PTQ.sf2";
    else if (id == 2) p = "/home/bob/Downloads/Studio_Grand_Concert.sf2";
    else if (id == 3) p = "/home/bob/Ailang-Self-Hosting-/tests/sample/sine_c4.sf2";
    else if (id == 4) p = "/home/bob/Downloads/GeneralUser-GS.sf2";
    else if (id == 5) p = "/home/bob/Downloads/FluidR3_GM.sf2";
    else if (id == 6) p = "/usr/share/sounds/sf2/FluidR3_GM.sf2";
    if (p) write_bank(p);
}

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

static void fill_wave(GtkComboBoxText *c) {
    gtk_combo_box_text_append_text(c, "Sine");
    gtk_combo_box_text_append_text(c, "Square");
    gtk_combo_box_text_append_text(c, "Pulse");
    gtk_combo_box_text_append_text(c, "Saw");
    gtk_combo_box_text_append_text(c, "Tri");
    gtk_combo_box_text_append_text(c, "Noise");
    gtk_combo_box_text_append_text(c, "NES tri");
    gtk_combo_box_text_append_text(c, "User");
    gtk_combo_box_text_append_text(c, "Sample");
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

static void on_preset(GtkComboBox *c, gpointer) {
    int id = gtk_combo_box_get_active(c);
    if (id < 0) id = 0;
    apply_preset(id);
}

static gboolean on_tick(gpointer) {
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
    snprintf(path_cmd, sizeof path_cmd, "%s/cmd.txt", dir);
    snprintf(path_pcm, sizeof path_pcm, "%s/pcm.bin", dir);
    snprintf(path_bank, sizeof path_bank, "%s/bank.txt", dir);
    snprintf(path_midi, sizeof path_midi, "%s/midi.bin", dir);
    snprintf(path_song, sizeof path_song, "%s/song.txt", dir);
    snprintf(path_song_cmd, sizeof path_song_cmd, "%s/song_cmd.txt", dir);

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
    gtk_window_set_title(GTK_WINDOW(win), "SynthKit");
    gtk_window_set_default_size(GTK_WINDOW(win), 720, 860);
    gtk_widget_add_events(win, GDK_KEY_PRESS_MASK | GDK_KEY_RELEASE_MASK);
    g_signal_connect(win, "delete-event", G_CALLBACK(on_delete), NULL);
    g_signal_connect(win, "key-press-event", G_CALLBACK(on_key), NULL);
    g_signal_connect(win, "key-release-event", G_CALLBACK(on_key_up), NULL);

    GtkWidget *vbox = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_container_set_border_width(GTK_CONTAINER(vbox), 12);
    gtk_container_add(GTK_CONTAINER(win), vbox);

    GtkWidget *hint = gtk_label_new(
        "Notes: C D E F G A B     Space = sustain     [ / Z oct down     ] / X up     Esc quit\n"
        "Two oscillators: wave 2 + mix + osc2 octave. Save/Load JSON patches. vmpk → SynthKit:in.");
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

    GtkWidget *bankrow = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *blab = gtk_label_new("SoundFont");
    gtk_box_pack_start(GTK_BOX(bankrow), blab, FALSE, FALSE, 0);
    GtkWidget *bcombo = gtk_combo_box_text_new();
    gtk_widget_set_can_focus(bcombo, FALSE);
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(bcombo), "(oscillators)");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(bcombo), "PTQ.sf2");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(bcombo), "Studio Grand Concert");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(bcombo), "sine_c4 test");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(bcombo), "GeneralUser GS");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(bcombo), "FluidR3 GM (Downloads)");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(bcombo), "FluidR3 GM (system)");
    gtk_combo_box_set_active(GTK_COMBO_BOX(bcombo), 1);
    g_signal_connect(bcombo, "changed", G_CALLBACK(on_bank_combo), NULL);
    gtk_box_pack_start(GTK_BOX(bankrow), bcombo, TRUE, TRUE, 0);
    GtkWidget *fc = gtk_file_chooser_button_new("Browse .sf2", GTK_FILE_CHOOSER_ACTION_OPEN);
    gtk_widget_set_can_focus(fc, FALSE);
    GtkFileFilter *ff = gtk_file_filter_new();
    gtk_file_filter_set_name(ff, "SoundFont 2");
    gtk_file_filter_add_pattern(ff, "*.sf2");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(fc), ff);
    gtk_file_chooser_set_current_folder(GTK_FILE_CHOOSER(fc), "/home/bob/Downloads");
    g_signal_connect(fc, "file-set", G_CALLBACK(on_bank_file), NULL);
    gtk_box_pack_start(GTK_BOX(bankrow), fc, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(vbox), bankrow, FALSE, FALSE, 0);

    GtkWidget *songrow = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *slab = gtk_label_new("MIDI file");
    gtk_box_pack_start(GTK_BOX(songrow), slab, FALSE, FALSE, 0);
    GtkWidget *sfc = gtk_file_chooser_button_new("Browse .mid", GTK_FILE_CHOOSER_ACTION_OPEN);
    gtk_widget_set_can_focus(sfc, FALSE);
    GtkFileFilter *mf = gtk_file_filter_new();
    gtk_file_filter_set_name(mf, "MIDI");
    gtk_file_filter_add_pattern(mf, "*.mid");
    gtk_file_filter_add_pattern(mf, "*.midi");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(sfc), mf);
    gtk_file_chooser_set_current_folder(GTK_FILE_CHOOSER(sfc), "/home/bob/Downloads");
    if (g_file_test("/home/bob/Downloads/CV_Intro.mid", G_FILE_TEST_EXISTS))
        gtk_file_chooser_set_filename(GTK_FILE_CHOOSER(sfc), "/home/bob/Downloads/CV_Intro.mid");
    g_signal_connect(sfc, "file-set", G_CALLBACK(on_song_file), NULL);
    gtk_box_pack_start(GTK_BOX(songrow), sfc, TRUE, TRUE, 0);
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

    GtkWidget *plab = gtk_label_new("preset");
    gtk_widget_set_halign(plab, GTK_ALIGN_START);
    gtk_grid_attach(GTK_GRID(grid), plab, 0, 0, 1, 1);
    GtkWidget *combo_p = gtk_combo_box_text_new();
    gtk_widget_set_can_focus(combo_p, FALSE);
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_p), "Init (sine)");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_p), "Analog Lead");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_p), "Fat Bass");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_p), "PWM Pad");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_p), "Pluck");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_p), "Square Lead");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_p), "Dual Saw");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_p), "Octave Lead");
    gtk_combo_box_set_active(GTK_COMBO_BOX(combo_p), 1);
    g_signal_connect(combo_p, "changed", G_CALLBACK(on_preset), NULL);
    gtk_grid_attach(GTK_GRID(grid), combo_p, 1, 0, 1, 1);

    GtkWidget *wlab = gtk_label_new("wave 1");
    gtk_widget_set_halign(wlab, GTK_ALIGN_START);
    gtk_grid_attach(GTK_GRID(grid), wlab, 2, 0, 1, 1);
    combo_wave = gtk_combo_box_text_new();
    gtk_widget_set_can_focus(combo_wave, FALSE);
    fill_wave(GTK_COMBO_BOX_TEXT(combo_wave));
    gtk_combo_box_set_active(GTK_COMBO_BOX(combo_wave), 3);
    g_signal_connect(combo_wave, "changed", G_CALLBACK(on_wave), NULL);
    gtk_grid_attach(GTK_GRID(grid), combo_wave, 3, 0, 1, 1);

    GtkWidget *w2lab = gtk_label_new("wave 2");
    gtk_widget_set_halign(w2lab, GTK_ALIGN_START);
    gtk_grid_attach(GTK_GRID(grid), w2lab, 0, 1, 1, 1);
    combo_wave2 = gtk_combo_box_text_new();
    gtk_widget_set_can_focus(combo_wave2, FALSE);
    fill_wave(GTK_COMBO_BOX_TEXT(combo_wave2));
    gtk_combo_box_set_active(GTK_COMBO_BOX(combo_wave2), 3);
    g_signal_connect(combo_wave2, "changed", G_CALLBACK(on_wave2), NULL);
    gtk_grid_attach(GTK_GRID(grid), combo_wave2, 1, 1, 1, 1);
    sc[20] = mk_scale(grid, 2, 1, "osc mix", 0, 256, &oscmix, 0);

    sc[21] = mk_scale(grid, 0, 2, "osc2 octave", 0, 4, &o2oct, 2);
    sc[22] = mk_scale(grid, 2, 2, "sustain lvl", 0, 256, &suslvl, 180);
    sc[23] = mk_scale(grid, 0, 3, "LFO to filter", 0, 256, &lfofilt, 0);
    sc[24] = mk_scale(grid, 2, 3, "LFO to amp", 0, 256, &lfoamp, 0);

    GtkWidget *patchrow = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *bsave = gtk_button_new_with_label("Save patch");
    GtkWidget *bload = gtk_button_new_with_label("Load patch");
    gtk_widget_set_can_focus(bsave, FALSE);
    gtk_widget_set_can_focus(bload, FALSE);
    g_signal_connect(bsave, "clicked", G_CALLBACK(on_save_patch), NULL);
    g_signal_connect(bload, "clicked", G_CALLBACK(on_load_patch), NULL);
    gtk_box_pack_start(GTK_BOX(patchrow), bsave, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(patchrow), bload, FALSE, FALSE, 0);
    gtk_grid_attach(GTK_GRID(grid), patchrow, 0, 4, 4, 1);

    sc[0] = mk_scale(grid, 0, 5, "cutoff", 0, 256, &cutoff, 105);
    sc[1] = mk_scale(grid, 2, 5, "res", 0, 240, &res, 110);
    sc[2] = mk_scale(grid, 0, 6, "pulse width", 8, 248, &pw, 64);
    sc[3] = mk_scale(grid, 2, 6, "detune cents", 0, 80, &detune, 8);
    sc[4] = mk_scale(grid, 0, 7, "filter env", 0, 256, &fenv, 230);
    sc[5] = mk_scale(grid, 2, 7, "sub osc", 0, 256, &submix, 90);
    sc[6] = mk_scale(grid, 0, 8, "drive", 0, 256, &drive, 55);
    sc[7] = mk_scale(grid, 2, 8, "LFO rate", 0, 256, &lforate, 0);
    sc[8] = mk_scale(grid, 0, 9, "LFO depth", 0, 256, &lfopwm, 0);
    sc[9] = mk_scale(grid, 2, 9, "attack ms", 0, 2500, &atk, 4);
    sc[10] = mk_scale(grid, 0, 10, "decay ms", 0, 2500, &dec, 220);
    sc[11] = mk_scale(grid, 2, 10, "release ms", 0, 4000, &rel, 320);
    sc[12] = mk_scale(grid, 0, 11, "volume", 0, 320, &vol, 170);
    sc[13] = mk_scale(grid, 2, 11, "delay ms", 0, 1300, &delayms, 0);
    sc[14] = mk_scale(grid, 0, 12, "delay fb", 0, 250, &fb, 0);
    sc[15] = mk_scale(grid, 2, 12, "delay wet", 0, 256, &wet, 0);

    sc[16] = mk_scale(grid, 0, 13, "MOD", 0, 256, &modv, 0);

    const char *slotlab[3] = {"mod A dest", "mod B dest", "mod C dest"};
    int *mds[3] = {&md0, &md1, &md2};
    int *mas[3] = {&ma0, &ma1, &ma2};
    int defd[3] = {1, 0, 0};
    int defa[3] = {200, 0, 0};
    for (int s = 0; s < 3; s++) {
        int row = 14 + s;
        GtkWidget *lab = gtk_label_new(slotlab[s]);
        gtk_widget_set_halign(lab, GTK_ALIGN_START);
        gtk_grid_attach(GTK_GRID(grid), lab, 0, row, 1, 1);
        combo_md[s] = gtk_combo_box_text_new();
        gtk_widget_set_can_focus(combo_md[s], FALSE);
        fill_dest(GTK_COMBO_BOX_TEXT(combo_md[s]));
        gtk_combo_box_set_active(GTK_COMBO_BOX(combo_md[s]), defd[s]);
        g_signal_connect(combo_md[s], "changed", G_CALLBACK(on_md), GINT_TO_POINTER(s));
        gtk_grid_attach(GTK_GRID(grid), combo_md[s], 1, row, 1, 1);
        sc[17 + s] = mk_scale(grid, 2, row, "depth", -256, 256, mas[s], defa[s]);
        *mds[s] = defd[s];
    }

    lbl_status = gtk_label_new("");
    gtk_widget_set_halign(lbl_status, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(vbox), lbl_status, FALSE, FALSE, 0);

    write_keys();
    write_ctl();
    write_cmd("");
    write_bank("/home/bob/Downloads/PTQ.sf2");
    synthkit_audio_init(path_pcm);
    synthkit_midi_init(path_midi);
    g_timeout_add(30, on_tick, NULL);
    gtk_widget_show_all(win);
    gtk_main();
    write_cmd("quit");
    synthkit_midi_shutdown();
    synthkit_audio_shutdown();
    return 0;
}
