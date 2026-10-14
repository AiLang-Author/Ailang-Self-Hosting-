/* Sample player. A pack and a MIDI song in our format.
   Any instrument the song names is played if that pack has it.
   This is not the synthesizer.

   Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.
 */
#include <gtk/gtk.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <sys/stat.h>
#include <unistd.h>

#include "midi_in.h"

static char dir[512];
static char path_song[600], path_song_cmd[600], path_pack[600], path_inst[600];
static char path_pcm[600], path_midi[600], path_ctl[600], path_keys[600], path_cmd[600];
static char pack_dir[600];
static char pack_name[128];
static char midi_path[600];
static int volume = 80;
static GtkWidget *combo_inst;
static GtkWidget *lbl_status;
static GtkWidget *pack_fc;
static GtkWidget *midi_fc;
static std::vector<std::string> inst_names;

static void write_text(const char *path, const char *text) {
    FILE *f = fopen(path, "w");
    if (!f) return;
    fputs(text, f);
    fclose(f);
}

static void write_ctl() {
    char line[256];
    snprintf(line, sizeof line,
             "0 256 0 0 0 0 %d 4 80 180 2 64 0 0 0 0 0 0 0 0 2 180 0 0 0 0 0 0 0 0 0\n",
             volume);
    write_text(path_ctl, line);
}

static void set_status(const char *s) {
    if (lbl_status) gtk_label_set_text(GTK_LABEL(lbl_status), s);
}

static std::string read_file(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) return "";
    std::string s;
    char buf[4096];
    size_t n;
    while ((n = fread(buf, 1, sizeof buf, f)) > 0) s.append(buf, n);
    fclose(f);
    return s;
}

static void json_string_list(const std::string &js, const char *object_key,
                             std::vector<std::string> *out) {
    out->clear();
    std::string key = std::string("\"") + object_key + "\"";
    size_t at = js.find(key);
    if (at == std::string::npos) return;
    size_t brace = js.find('{', at + key.size());
    if (brace == std::string::npos) return;
    int depth = 0;
    for (size_t i = brace; i < js.size(); i++) {
        char c = js[i];
        if (c == '{') depth++;
        else if (c == '}') {
            depth--;
            if (depth == 0) break;
        } else if (c == '"' && depth == 1) {
            size_t e = js.find('"', i + 1);
            if (e == std::string::npos) break;
            std::string name = js.substr(i + 1, e - i - 1);
            size_t colon = js.find(':', e);
            size_t next = js.find_first_not_of(" \t\r\n", colon == std::string::npos ? e : colon + 1);
            if (colon != std::string::npos && next != std::string::npos && js[next] == '{')
                out->push_back(name);
            i = e;
        }
    }
}

static std::string json_name(const std::string &js) {
    size_t at = js.find("\"name\"");
    if (at == std::string::npos) return "";
    size_t q = js.find('"', js.find(':', at) + 1);
    if (q == std::string::npos) return "";
    size_t e = js.find('"', q + 1);
    if (e == std::string::npos) return "";
    return js.substr(q + 1, e - q - 1);
}

static void write_inst() {
    const char *name = "piano_grand";
    int id = combo_inst ? gtk_combo_box_get_active(GTK_COMBO_BOX(combo_inst)) : 0;
    if (id >= 0 && id < (int)inst_names.size()) name = inst_names[id].c_str();
    std::string line = std::string(name) + "\n";
    write_text(path_inst, line.c_str());
}

static void use_pack(const char *path) {
    while (*path == ' ' || *path == '\t') path++;
    snprintf(pack_dir, sizeof pack_dir, "%s", path);
    size_t n = strlen(pack_dir);
    while (n > 0 && (pack_dir[n - 1] == '\n' || pack_dir[n - 1] == '\r' || pack_dir[n - 1] == ' '))
        pack_dir[--n] = 0;
    std::string js = read_file((std::string(pack_dir) + "/pack.json").c_str());
    if (js.empty()) {
        pack_dir[0] = 0;
        set_status("That folder has no pack.json.");
        return;
    }
    std::string nm = json_name(js);
    snprintf(pack_name, sizeof pack_name, "%s", nm.empty() ? "pack" : nm.c_str());
    json_string_list(js, "instruments", &inst_names);
    if (combo_inst) {
        gtk_combo_box_text_remove_all(GTK_COMBO_BOX_TEXT(combo_inst));
        for (size_t i = 0; i < inst_names.size(); i++)
            gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_inst), inst_names[i].c_str());
        if (!inst_names.empty()) gtk_combo_box_set_active(GTK_COMBO_BOX(combo_inst), 0);
    }
    write_text(path_pack, (std::string(pack_dir) + "\n").c_str());
    write_inst();
    char msg[400];
    snprintf(msg, sizeof msg, "Pack %s is loaded (%zu instruments). Pick a song and press Play.",
             pack_name, inst_names.size());
    set_status(msg);
}

static void on_pack(GtkFileChooser *c, gpointer) {
    char *fn = gtk_file_chooser_get_filename(c);
    if (!fn) return;
    use_pack(fn);
    g_free(fn);
}

static void on_inst(GtkComboBox *, gpointer) { write_inst(); }

static void on_midi(GtkFileChooser *c, gpointer) {
    char *fn = gtk_file_chooser_get_filename(c);
    if (!fn) return;
    snprintf(midi_path, sizeof midi_path, "%s", fn);
    g_free(fn);
    set_status(midi_path);
}

static int ensure_songmap() {
    if (!midi_path[0]) return 0;
    std::string map = std::string(midi_path) + ".songmap";
    struct stat st;
    if (stat(map.c_str(), &st) == 0) return 1;
    const char *inst = inst_names.empty() ? "piano_grand" : inst_names[0].c_str();
    int id = combo_inst ? gtk_combo_box_get_active(GTK_COMBO_BOX(combo_inst)) : 0;
    if (id >= 0 && id < (int)inst_names.size()) inst = inst_names[id].c_str();
    const char *json = "/home/bob/Ailang-Self-Hosting-/Librarys/Media/opcode16.json";
    const char *tool = "/home/bob/Ailang-Self-Hosting-/Applications/SynthKit/tools/midi3_songmap.py";
    char cmd[2200];
    snprintf(cmd, sizeof cmd,
             "python3 \"%s\" --json \"%s\" --pack \"%s\" --default-inst \"%s\" -o \"%s\" \"%s\"",
             tool, json, pack_name, inst, map.c_str(), midi_path);
    int rc = system(cmd);
    if (rc != 0) {
        set_status("Could not write a songmap for that MIDI file.");
        return 0;
    }
    return 1;
}

static void on_play(GtkButton *, gpointer) {
    if (pack_fc) {
        char *fn = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(pack_fc));
        if (fn) { use_pack(fn); g_free(fn); }
    }
    if (!pack_dir[0]) {
        std::string already = read_file(path_pack);
        if (!already.empty()) use_pack(already.c_str());
    }
    if (midi_fc) {
        char *fn = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(midi_fc));
        if (fn) { snprintf(midi_path, sizeof midi_path, "%s", fn); g_free(fn); }
    }
    if (!pack_dir[0] || !midi_path[0]) {
        set_status("Pick a MIDI song, then press Play. The upright pack is already loaded.");
        fprintf(stderr, "sample player: Play ignored, song not chosen\n");
        return;
    }
    fprintf(stderr, "sample player: play %s\n", midi_path);
    write_text(path_pack, (std::string(pack_dir) + "\n").c_str());
    write_inst();
    if (!ensure_songmap()) return;
    write_text(path_song, (std::string(midi_path) + "\n").c_str());
    write_text(path_song_cmd, "play\n");
    set_status("Playing. If you just picked the pack, the first notes wait until those samples are loaded.");
}

static void on_stop(GtkButton *, gpointer) {
    write_text(path_song_cmd, "stop\n");
    set_status("Stopped.");
}

static void on_vol(GtkRange *r, gpointer) {
    volume = (int)gtk_range_get_value(r);
    write_ctl();
}

static gboolean on_tick(gpointer) {
    synthkit_midi_poll();
    return TRUE;
}

static gboolean on_delete(GtkWidget *, GdkEvent *, gpointer) {
    write_text(path_cmd, "quit\n");
    gtk_main_quit();
    return FALSE;
}

int main(int argc, char **argv) {
    const char *d = "/dev/shm/sample_player";
    if (argc > 1 && argv[1] && argv[1][0]) d = argv[1];
    snprintf(dir, sizeof dir, "%s", d);
    mkdir(dir, 0755);
    snprintf(path_song, sizeof path_song, "%s/song.txt", dir);
    snprintf(path_song_cmd, sizeof path_song_cmd, "%s/song_cmd.txt", dir);
    snprintf(path_pack, sizeof path_pack, "%s/pack.txt", dir);
    snprintf(path_inst, sizeof path_inst, "%s/inst.txt", dir);
    snprintf(path_pcm, sizeof path_pcm, "%s/pcm.bin", dir);
    snprintf(path_midi, sizeof path_midi, "%s/midi.bin", dir);
    snprintf(path_ctl, sizeof path_ctl, "%s/ctl.txt", dir);
    snprintf(path_keys, sizeof path_keys, "%s/keys.txt", dir);
    snprintf(path_cmd, sizeof path_cmd, "%s/cmd.txt", dir);
    write_text(path_keys, "00000000\n");
    write_ctl();

    gtk_init(&argc, &argv);
    GtkWidget *win = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(win), "Sample player");
    gtk_window_set_default_size(GTK_WINDOW(win), 720, 280);
    g_signal_connect(win, "delete-event", G_CALLBACK(on_delete), NULL);
    GtkWidget *vbox = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_container_set_border_width(GTK_CONTAINER(vbox), 12);
    gtk_container_add(GTK_CONTAINER(win), vbox);

    GtkWidget *hint = gtk_label_new(
        "Drop in a MIDI 3 pack and a MIDI song. Program changes pick the instrument\n"
        "from opcode16. Parts with no program use the instrument selected here.\n"
        "If the pack does not contain that instrument, the part is silent.");
    gtk_label_set_xalign(GTK_LABEL(hint), 0);
    gtk_box_pack_start(GTK_BOX(vbox), hint, FALSE, FALSE, 0);

    GtkWidget *row1 = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(row1), gtk_label_new("Pack"), FALSE, FALSE, 0);
    pack_fc = gtk_file_chooser_button_new("Sample pack", GTK_FILE_CHOOSER_ACTION_SELECT_FOLDER);
    gtk_file_chooser_set_current_folder(GTK_FILE_CHOOSER(pack_fc), "/home/bob/Downloads/midi3-packs");
    g_signal_connect(pack_fc, "file-set", G_CALLBACK(on_pack), NULL);
    gtk_box_pack_start(GTK_BOX(row1), pack_fc, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(vbox), row1, FALSE, FALSE, 0);

    GtkWidget *row2 = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(row2), gtk_label_new("Instrument"), FALSE, FALSE, 0);
    combo_inst = gtk_combo_box_text_new();
    g_signal_connect(combo_inst, "changed", G_CALLBACK(on_inst), NULL);
    gtk_box_pack_start(GTK_BOX(row2), combo_inst, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(vbox), row2, FALSE, FALSE, 0);

    GtkWidget *row3 = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(row3), gtk_label_new("Song"), FALSE, FALSE, 0);
    midi_fc = gtk_file_chooser_button_new("MIDI", GTK_FILE_CHOOSER_ACTION_OPEN);
    GtkFileFilter *mf = gtk_file_filter_new();
    gtk_file_filter_set_name(mf, "MIDI");
    gtk_file_filter_add_pattern(mf, "*.mid");
    gtk_file_filter_add_pattern(mf, "*.midi");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(midi_fc), mf);
    gtk_file_chooser_set_current_folder(GTK_FILE_CHOOSER(midi_fc), "/home/bob/Downloads");
    g_signal_connect(midi_fc, "file-set", G_CALLBACK(on_midi), NULL);
    gtk_box_pack_start(GTK_BOX(row3), midi_fc, TRUE, TRUE, 0);
    GtkWidget *play = gtk_button_new_with_label("Play");
    GtkWidget *stop = gtk_button_new_with_label("Stop");
    g_signal_connect(play, "clicked", G_CALLBACK(on_play), NULL);
    g_signal_connect(stop, "clicked", G_CALLBACK(on_stop), NULL);
    gtk_box_pack_start(GTK_BOX(row3), play, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(row3), stop, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(vbox), row3, FALSE, FALSE, 0);

    GtkWidget *vol = gtk_scale_new_with_range(GTK_ORIENTATION_HORIZONTAL, 0, 512, 1);
    gtk_range_set_value(GTK_RANGE(vol), volume);
    g_signal_connect(vol, "value-changed", G_CALLBACK(on_vol), NULL);
    gtk_box_pack_start(GTK_BOX(vbox), vol, FALSE, FALSE, 0);

    lbl_status = gtk_label_new("Pick a MIDI song and press Play.");
    gtk_label_set_xalign(GTK_LABEL(lbl_status), 0);
    gtk_label_set_line_wrap(GTK_LABEL(lbl_status), TRUE);
    gtk_box_pack_start(GTK_BOX(vbox), lbl_status, FALSE, FALSE, 0);
    std::string already = read_file(path_pack);
    if (!already.empty()) {
        use_pack(already.c_str());
        if (pack_dir[0]) gtk_file_chooser_set_filename(GTK_FILE_CHOOSER(pack_fc), pack_dir);
    }

    synthkit_midi_init(path_midi);
    g_timeout_add(30, on_tick, NULL);
    gtk_widget_show_all(win);
    gtk_main();
    write_text(path_cmd, "quit\n");
    synthkit_midi_shutdown();
    return 0;
}
