/* cad_shell_gtk — compiled Gtk3 host for AILang CAD.
 * Chrome + blit + rubber-band + HUD. Kernel owns geometry.
 *
 *   make -C CAD/host gtk
 *   CAD_APP_STATE=/tmp/cad_app ./CAD/host/cad_shell_gtk
 */
#include <gtk/gtk.h>
#include <gdk/gdk.h>
#include <cairo.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdint.h>
#include <math.h>
#include <time.h>
#include <errno.h>
#include <signal.h>

static char g_dir[512];
static char path_meta[600], path_frame[600], path_gen[600], path_cmd[600];
static char path_status[600], path_tool[600], path_hud[600], path_path[600];
static char path_tools[600], path_cam[600], path_cmds[600], path_tree[600];
static char path_hist[600], path_dimhud[600], path_parts[600];

static void paths_init(const char *dir) {
    snprintf(g_dir, sizeof g_dir, "%s", dir);
    snprintf(path_meta, sizeof path_meta, "%s/meta.bin", dir);
    snprintf(path_frame, sizeof path_frame, "%s/frame.raw", dir);
    snprintf(path_gen, sizeof path_gen, "%s/gen.txt", dir);
    snprintf(path_cmd, sizeof path_cmd, "%s/cmd.txt", dir);
    snprintf(path_status, sizeof path_status, "%s/status.txt", dir);
    snprintf(path_tool, sizeof path_tool, "%s/tool.txt", dir);
    snprintf(path_hud, sizeof path_hud, "%s/hud.txt", dir);
    snprintf(path_path, sizeof path_path, "%s/path.txt", dir);
    snprintf(path_tools, sizeof path_tools, "%s/tools.json", dir);
    snprintf(path_cam, sizeof path_cam, "%s/cam.txt", dir);
    snprintf(path_cmds, sizeof path_cmds, "%s/cmds.txt", dir);
    snprintf(path_tree, sizeof path_tree, "%s/tree.txt", dir);
    snprintf(path_hist, sizeof path_hist, "%s/hist.txt", dir);
    snprintf(path_dimhud, sizeof path_dimhud, "%s/dimhud.txt", dir);
    snprintf(path_parts, sizeof path_parts, "%s/parts.txt", dir);
}

static void write_cmd(const char *s) {
    int tries;
    for (tries = 0; tries < 60; tries++) {
        FILE *cf = fopen(path_cmd, "r");
        int busy = 0;
        if (cf) {
            int c = fgetc(cf);
            if (c != EOF && c != '\n' && c != '\r') busy = 1;
            fclose(cf);
        }
        if (!busy) break;
        usleep(2000);
    }
    FILE *f = fopen(path_cmd, "w");
    if (!f) return;
    fputs(s, f);
    fputc('\n', f);
    fclose(f);
}

static int confirm_leave(const char *then_cmd);

static void request_quit(void) {
    write_cmd("quit");
    gtk_main_quit();
}

static void on_term(int) {
    request_quit();
}

static gboolean on_delete(GtkWidget *, GdkEvent *, gpointer) {
    if (!confirm_leave(NULL)) return TRUE;
    write_cmd("quit");
    return FALSE;
}

static void cb_cmd(GtkButton *, gpointer data) {
    if (data) write_cmd((const char *)data);
}

static void cb_menu_cmd(GtkMenuItem *, gpointer data) {
    if (data) write_cmd((const char *)data);
}

static int read_gen(void) {
    FILE *f = fopen(path_gen, "r");
    if (!f) return -1;
    int g = -1;
    if (fscanf(f, "%d", &g) != 1) g = -1;
    fclose(f);
    return g;
}

static void read_line_file(const char *path, char *buf, size_t n) {
    buf[0] = 0;
    FILE *f = fopen(path, "r");
    if (!f) return;
    if (fgets(buf, (int)n, f)) {
        size_t L = strlen(buf);
        while (L && (buf[L - 1] == '\n' || buf[L - 1] == '\r')) buf[--L] = 0;
    }
    fclose(f);
}

static void read_tool_state(int *mode, int *tool, int *nclick) {
    *mode = 0;
    *tool = 0;
    *nclick = 0;
    FILE *f = fopen(path_tool, "r");
    if (!f) return;
    int dirty = 0;
    if (fscanf(f, "%d %d %d %d", mode, tool, nclick, &dirty) < 1) {
        *mode = 0;
    }
    fclose(f);
}

/* ---------- app state ---------- */

struct App {
    GtkWidget *win;
    GtkWidget *da;
    GtkWidget *status;
    GtkWidget *hud_bar;
    GtkWidget *mode_lbl;
    GtkNotebook *ribbon;
    GtkWidget *cube;
    GtkWidget *cube_host;
    GtkWidget *treev;
    GtkWidget *navhdr;
    GtkWidget *fold_btn;
    int tree_open_all;
    GtkTreeStore *tstore;
    char tree_cache[4096];
    char tree_open[256];
    int tree_seen;
    GtkWidget *hist_win;
    GtkWidget *hist_scale;
    GtkWidget *hist_lbl;
    GtkWidget *tl_box;
    GtkWidget *tl_dock;
    char hist_cache[1024];
    int hist_ignore;
    char tree_edit_cmd[32];
    cairo_surface_t *frame;
    uint8_t *pix;
    int fw, fh, pitch;
    int last_gen;
    int ox, oy;
    int dragging, moved, pan_mode, mmb;
    int down_fx, down_fy, last_fx, last_fy;
    int cur_fx, cur_fy;
    int have_anchor, anchor_fx, anchor_fy;
    int click_sh;
    int pend_hover, hover_fx, hover_fy;
    int last_hover_fx, last_hover_fy;
    struct timespec down_ts;
    char hud_line[256];
    char status_line[256];
    double cam_yaw, cam_pitch;
    int cam_zoom_c;
    int cube_hover;
    int cube_drag, cube_moved;
    int cube_lx, cube_ly;
    int cube_move;
    int cube_mt, cube_me;
    char dimbuf[40];
    int dimn;
    int dim_kind;
    int dim_sel; /* 1 = current value selected; next digit replaces */
    char dimhud[128];
    int hud_blink;
    int hud_idle;
    int pie_on, pie_n, pie_hit, pie_cx, pie_cy;
    char pie_cmd[12][40];
    char pie_lab[12][40];
    int pie_sub;
    int pie_vn, pie_vhit;
    char pie_vcmd[8][40];
    char pie_vlab[8][24];
    int page_solid;
    int session_guest;
    char session_user[48];
    char doc_name[64];
    int dirty;
    GtkWidget *sess_btn;
};

static App G;

static void wait_kernel_idle(void) {
    int i;
    for (i = 0; i < 400; i++) {
        FILE *cf = fopen(path_cmd, "r");
        int busy = 0;
        if (cf) {
            int c = fgetc(cf);
            if (c != EOF && c != '\n' && c != '\r' && c != ' ') busy = 1;
            fclose(cf);
        }
        if (!busy) return;
        usleep(5000);
    }
}

typedef struct {
    char name[64];
    char kind[24];
} DocRow;

static int fetch_doc_rows(DocRow *rows, int maxn) {
    int n = 0;
    fprintf(stderr, "cad_shell: fetch_doc_rows → files\n");
    write_cmd("files");
    wait_kernel_idle();
    usleep(25000);
    fprintf(stderr, "cad_shell: fetch_doc_rows kernel idle, reading parts.txt\n");
    FILE *f = fopen(path_parts, "r");
    if (!f) f = fopen("/tmp/cad_app/parts.txt", "r");
    if (!f) return 0;
    char line[128];
    while (n < maxn && fgets(line, sizeof line, f)) {
        char *nl = strchr(line, '\n');
        if (nl) *nl = 0;
        char *cr = strchr(line, '\r');
        if (cr) *cr = 0;
        if (!line[0]) continue;
        if (line[0] == '(') continue;
        char *tab = strchr(line, '\t');
        if (tab) {
            *tab = 0;
            snprintf(rows[n].name, sizeof rows[n].name, "%s", line);
            snprintf(rows[n].kind, sizeof rows[n].kind, "%s", tab + 1);
        } else {
            snprintf(rows[n].name, sizeof rows[n].name, "%s", line);
            snprintf(rows[n].kind, sizeof rows[n].kind, "part");
        }
        if (!rows[n].name[0]) continue;
        n++;
    }
    fclose(f);
    return n;
}

enum { DOC_OPEN = 0, DOC_SAVE = 1, DOC_DELETE = 2 };

static int is_stash_name(const char *n) {
    size_t L = n ? strlen(n) : 0;
    return L >= 6 && strcmp(n + L - 6, "_dirty") == 0;
}

static int app_is_dirty(void) {
    int mode = 0, tool = 0, nclick = 0, dirty = 0;
    FILE *f = fopen(path_tool, "r");
    if (!f) return G.dirty;
    if (fscanf(f, "%d %d %d %d", &mode, &tool, &nclick, &dirty) >= 4)
        G.dirty = dirty ? 1 : 0;
    fclose(f);
    return G.dirty;
}

static const char *kind_token(int i) {
    switch (i) {
    case 1: return "assembly";
    case 2: return "group";
    case 3: return "machine";
    default: return "part";
    }
}

static void doc_fill_entry(GtkTreeView *tv, gpointer entp) {
    GtkEntry *ent = GTK_ENTRY(entp);
    if (!ent) return;
    GtkTreeSelection *sel = gtk_tree_view_get_selection(tv);
    GtkTreeModel *m = NULL;
    GtkTreeIter it;
    if (!gtk_tree_selection_get_selected(sel, &m, &it)) return;
    gchar *nm = NULL;
    gtk_tree_model_get(m, &it, 0, &nm, -1);
    if (nm) {
        gtk_entry_set_text(ent, nm);
        g_free(nm);
    }
}

static void on_doc_row(GtkTreeView *tv, GtkTreePath *, GtkTreeViewColumn *, gpointer ent) {
    doc_fill_entry(tv, ent);
}

static int doc_dialog(int mode); /* Save returns 1 if a save was sent */

/* 1 = proceed with leave, 0 = stay. then_cmd is close/newdoc or NULL. */
static int confirm_leave(const char *then_cmd) {
    if (!app_is_dirty()) {
        if (then_cmd && then_cmd[0]) write_cmd(then_cmd);
        return 1;
    }
    const char *who = G.doc_name[0] ? G.doc_name : "untitled";
    GtkWidget *ask = gtk_message_dialog_new(
        GTK_WINDOW(G.win), GTK_DIALOG_MODAL, GTK_MESSAGE_WARNING, GTK_BUTTONS_NONE,
        "'%s' has unsaved changes.\n\n"
        "Save writes the part.\n"
        "Stash keeps a dirty copy and asks when you open it again.\n"
        "Discard throws the changes away.", who);
    gtk_dialog_add_button(GTK_DIALOG(ask), "Save…", GTK_RESPONSE_YES);
    gtk_dialog_add_button(GTK_DIALOG(ask), "Stash", GTK_RESPONSE_APPLY);
    gtk_dialog_add_button(GTK_DIALOG(ask), "Discard", GTK_RESPONSE_NO);
    gtk_dialog_add_button(GTK_DIALOG(ask), "Cancel", GTK_RESPONSE_CANCEL);
    int r = gtk_dialog_run(GTK_DIALOG(ask));
    gtk_widget_destroy(ask);
    if (r == GTK_RESPONSE_CANCEL || r == GTK_RESPONSE_DELETE_EVENT) return 0;
    if (r == GTK_RESPONSE_YES) {
        if (!doc_dialog(DOC_SAVE)) return 0;
        wait_kernel_idle();
    } else if (r == GTK_RESPONSE_APPLY) {
        write_cmd("stash");
        wait_kernel_idle();
    }
    if (then_cmd && then_cmd[0]) write_cmd(then_cmd);
    return 1;
}

static void on_newdoc(GtkWidget *, gpointer) { confirm_leave("newdoc"); }
static void on_close_doc(GtkWidget *, gpointer) { confirm_leave("close"); }

static int doc_dialog(int mode) {
    const char *title = "Open document";
    const char *oklab = "Open";
    if (mode == DOC_SAVE) {
        title = "Save document";
        oklab = "Save";
    }
    if (mode == DOC_DELETE) {
        title = "Delete document";
        oklab = "Delete";
    }
    DocRow rows[50];
    int nr = fetch_doc_rows(rows, 50);

    GtkWidget *dlg = gtk_dialog_new_with_buttons(
        title, GTK_WINDOW(G.win), GTK_DIALOG_MODAL,
        "Cancel", GTK_RESPONSE_CANCEL, oklab, GTK_RESPONSE_ACCEPT, NULL);
    GtkWidget *box = gtk_dialog_get_content_area(GTK_DIALOG(dlg));
    gtk_widget_set_margin_start(box, 10);
    gtk_widget_set_margin_end(box, 10);
    gtk_widget_set_margin_top(box, 8);
    gtk_widget_set_margin_bottom(box, 8);

    GtkWidget *hint = gtk_label_new(
        mode == DOC_SAVE
            ? "Pick an existing name to overwrite, or type a new one."
            : "Saved documents in Postgres (cad_db). Click a row, then Open.");
    gtk_label_set_xalign(GTK_LABEL(hint), 0);
    gtk_box_pack_start(GTK_BOX(box), hint, FALSE, FALSE, 4);

    GtkListStore *store = gtk_list_store_new(2, G_TYPE_STRING, G_TYPE_STRING);
    int i;
    for (i = 0; i < nr; i++) {
        if (is_stash_name(rows[i].name)) continue;
        GtkTreeIter it;
        gtk_list_store_append(store, &it);
        gtk_list_store_set(store, &it, 0, rows[i].name, 1, rows[i].kind, -1);
    }
    GtkWidget *tv = gtk_tree_view_new_with_model(GTK_TREE_MODEL(store));
    g_object_unref(store);
    gtk_tree_view_set_headers_visible(GTK_TREE_VIEW(tv), TRUE);
    GtkCellRenderer *r0 = gtk_cell_renderer_text_new();
    GtkCellRenderer *r1 = gtk_cell_renderer_text_new();
    gtk_tree_view_append_column(GTK_TREE_VIEW(tv),
        gtk_tree_view_column_new_with_attributes("Name", r0, "text", 0, NULL));
    gtk_tree_view_append_column(GTK_TREE_VIEW(tv),
        gtk_tree_view_column_new_with_attributes("Kind", r1, "text", 1, NULL));
    GtkWidget *sc = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(sc),
        GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_size_request(sc, 420, 240);
    gtk_container_add(GTK_CONTAINER(sc), tv);
    gtk_box_pack_start(GTK_BOX(box), sc, TRUE, TRUE, 4);
    if (nr < 1) {
        gtk_box_pack_start(GTK_BOX(box),
            gtk_label_new("No documents yet. Save one first."), FALSE, FALSE, 2);
    }

    GtkWidget *ent = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(ent), "document name");
    gtk_entry_set_activates_default(GTK_ENTRY(ent), TRUE);
    if (mode == DOC_SAVE && G.doc_name[0])
        gtk_entry_set_text(GTK_ENTRY(ent), G.doc_name);
    gtk_box_pack_start(GTK_BOX(box), ent, FALSE, FALSE, 4);

    GtkWidget *combo = NULL;
    if (mode == DOC_SAVE) {
        GtkWidget *row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
        gtk_box_pack_start(GTK_BOX(row), gtk_label_new("Save as"), FALSE, FALSE, 0);
        combo = gtk_combo_box_text_new();
        gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo), "Part");
        gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo), "Assembly");
        gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo), "Group");
        gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo), "Machine");
        gtk_combo_box_set_active(GTK_COMBO_BOX(combo), 0);
        gtk_box_pack_start(GTK_BOX(row), combo, TRUE, TRUE, 0);
        gtk_box_pack_start(GTK_BOX(box), row, FALSE, FALSE, 4);
    }

    g_signal_connect(tv, "cursor-changed", G_CALLBACK(doc_fill_entry), ent);
    g_signal_connect(tv, "row-activated", G_CALLBACK(on_doc_row), ent);
    gtk_dialog_set_default_response(GTK_DIALOG(dlg), GTK_RESPONSE_ACCEPT);
    gtk_widget_show_all(dlg);

    int did = 0;
    if (gtk_dialog_run(GTK_DIALOG(dlg)) == GTK_RESPONSE_ACCEPT) {
        const char *t = gtk_entry_get_text(GTK_ENTRY(ent));
        if (t && t[0]) {
            if (mode == DOC_DELETE) {
                GtkWidget *ask = gtk_message_dialog_new(
                    GTK_WINDOW(G.win), GTK_DIALOG_MODAL, GTK_MESSAGE_WARNING,
                    GTK_BUTTONS_OK_CANCEL,
                    "Delete '%s' from Postgres? This cannot be undone.", t);
                if (gtk_dialog_run(GTK_DIALOG(ask)) == GTK_RESPONSE_OK) {
                    char cmd[96];
                    snprintf(cmd, sizeof cmd, "forget %.48s", t);
                    write_cmd(cmd);
                    did = 1;
                }
                gtk_widget_destroy(ask);
            } else if (mode == DOC_SAVE) {
                int exists = 0;
                for (i = 0; i < nr; i++) {
                    if (!is_stash_name(rows[i].name) && strcmp(rows[i].name, t) == 0)
                        exists = 1;
                }
                int do_save = 1;
                int overwrite = 0;
                if (exists) {
                    GtkWidget *ask = gtk_message_dialog_new(
                        GTK_WINDOW(G.win), GTK_DIALOG_MODAL, GTK_MESSAGE_QUESTION,
                        GTK_BUTTONS_NONE,
                        "'%s' already exists in Postgres.\n\n"
                        "Overwrite replaces that part's latest row.\n"
                        "Keep leaves it unchanged — pick another name.", t);
                    gtk_dialog_add_button(GTK_DIALOG(ask), "Keep", GTK_RESPONSE_REJECT);
                    gtk_dialog_add_button(GTK_DIALOG(ask), "Overwrite", GTK_RESPONSE_ACCEPT);
                    gtk_dialog_add_button(GTK_DIALOG(ask), "Cancel", GTK_RESPONSE_CANCEL);
                    int ar = gtk_dialog_run(GTK_DIALOG(ask));
                    gtk_widget_destroy(ask);
                    if (ar == GTK_RESPONSE_ACCEPT) overwrite = 1;
                    else do_save = 0;
                }
                if (do_save) {
                    int ki = combo ? gtk_combo_box_get_active(GTK_COMBO_BOX(combo)) : 0;
                    char cmd[96];
                    fprintf(stderr, "cad_shell: save name='%s' overwrite=%d kind=%d\n",
                            t, overwrite, ki);
                    snprintf(cmd, sizeof cmd, "setkind %s", kind_token(ki));
                    write_cmd(cmd);
                    snprintf(cmd, sizeof cmd, "name %.48s", t);
                    write_cmd(cmd);
                    snprintf(G.doc_name, sizeof G.doc_name, "%s", t);
                    write_cmd(overwrite ? "saveover" : "save");
                    did = 1;
                }
            } else {
                char stashn[72];
                snprintf(stashn, sizeof stashn, "%.56s_dirty", t);
                int has_stash = 0;
                for (i = 0; i < nr; i++) {
                    if (strcmp(rows[i].name, stashn) == 0) has_stash = 1;
                }
                if (has_stash) {
                    GtkWidget *ask = gtk_message_dialog_new(
                        GTK_WINDOW(G.win), GTK_DIALOG_MODAL, GTK_MESSAGE_QUESTION,
                        GTK_BUTTONS_NONE,
                        "'%s' has stashed unsaved changes.\n\n"
                        "Accept loads the dirty work.\n"
                        "Discard throws the stash away and opens the last save.", t);
                    gtk_dialog_add_button(GTK_DIALOG(ask), "Accept", GTK_RESPONSE_ACCEPT);
                    gtk_dialog_add_button(GTK_DIALOG(ask), "Discard", GTK_RESPONSE_NO);
                    gtk_dialog_add_button(GTK_DIALOG(ask), "Cancel", GTK_RESPONSE_CANCEL);
                    int ar = gtk_dialog_run(GTK_DIALOG(ask));
                    gtk_widget_destroy(ask);
                    if (ar == GTK_RESPONSE_CANCEL || ar == GTK_RESPONSE_DELETE_EVENT) {
                        gtk_widget_destroy(dlg);
                        return 0;
                    }
                    char cmd[96];
                    if (ar == GTK_RESPONSE_ACCEPT) {
                        snprintf(cmd, sizeof cmd, "name %.48s", stashn);
                        write_cmd(cmd);
                        write_cmd("load");
                        snprintf(cmd, sizeof cmd, "name %.48s", t);
                        write_cmd(cmd);
                    } else {
                        snprintf(cmd, sizeof cmd, "forget %.48s", stashn);
                        write_cmd(cmd);
                        snprintf(cmd, sizeof cmd, "name %.48s", t);
                        write_cmd(cmd);
                        write_cmd("load");
                    }
                    snprintf(G.doc_name, sizeof G.doc_name, "%s", t);
                    did = 1;
                } else {
                    char cmd[96];
                    snprintf(cmd, sizeof cmd, "name %.48s", t);
                    write_cmd(cmd);
                    snprintf(G.doc_name, sizeof G.doc_name, "%s", t);
                    write_cmd("load");
                    did = 1;
                }
            }
        }
    }
    gtk_widget_destroy(dlg);
    return did;
}

static gboolean recover_stashes(gpointer) {
    DocRow rows[50];
    int nr = fetch_doc_rows(rows, 50);
    int i;
    for (i = 0; i < nr; i++) {
        if (!is_stash_name(rows[i].name)) continue;
        char base[64];
        snprintf(base, sizeof base, "%s", rows[i].name);
        size_t L = strlen(base);
        if (L >= 6) base[L - 6] = 0;
        if (!base[0]) snprintf(base, sizeof base, "untitled");
        GtkWidget *ask = gtk_message_dialog_new(
            GTK_WINDOW(G.win), GTK_DIALOG_MODAL, GTK_MESSAGE_QUESTION,
            GTK_BUTTONS_NONE,
            "Stashed unsaved work for '%s' was found.\n\n"
            "Accept loads those changes.\n"
            "Discard throws the stash away.", base);
        gtk_dialog_add_button(GTK_DIALOG(ask), "Accept", GTK_RESPONSE_ACCEPT);
        gtk_dialog_add_button(GTK_DIALOG(ask), "Discard", GTK_RESPONSE_NO);
        gtk_dialog_add_button(GTK_DIALOG(ask), "Later", GTK_RESPONSE_CANCEL);
        int ar = gtk_dialog_run(GTK_DIALOG(ask));
        gtk_widget_destroy(ask);
        if (ar == GTK_RESPONSE_CANCEL || ar == GTK_RESPONSE_DELETE_EVENT)
            continue;
        char cmd[96];
        if (ar == GTK_RESPONSE_ACCEPT) {
            snprintf(cmd, sizeof cmd, "name %.48s", rows[i].name);
            write_cmd(cmd);
            write_cmd("load");
            snprintf(cmd, sizeof cmd, "name %.48s", base);
            write_cmd(cmd);
            snprintf(G.doc_name, sizeof G.doc_name, "%s", base);
        } else {
            snprintf(cmd, sizeof cmd, "forget %.48s", rows[i].name);
            write_cmd(cmd);
        }
    }
    return G_SOURCE_REMOVE;
}

static void prompt_name_cmd(const char *title, const char *then_cmd) {
    GtkWidget *dlg = gtk_dialog_new_with_buttons(
        title, GTK_WINDOW(G.win), GTK_DIALOG_MODAL,
        "Cancel", GTK_RESPONSE_CANCEL, "OK", GTK_RESPONSE_ACCEPT, NULL);
    GtkWidget *box = gtk_dialog_get_content_area(GTK_DIALOG(dlg));
    GtkWidget *ent = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(ent), "untitled");
    gtk_entry_set_activates_default(GTK_ENTRY(ent), TRUE);
    gtk_container_add(GTK_CONTAINER(box), ent);
    gtk_widget_set_margin_start(ent, 8);
    gtk_widget_set_margin_end(ent, 8);
    gtk_widget_set_margin_top(ent, 8);
    gtk_widget_show_all(dlg);
    gtk_dialog_set_default_response(GTK_DIALOG(dlg), GTK_RESPONSE_ACCEPT);
    if (gtk_dialog_run(GTK_DIALOG(dlg)) == GTK_RESPONSE_ACCEPT) {
        const char *t = gtk_entry_get_text(GTK_ENTRY(ent));
        if (t && t[0]) {
            char cmd[96];
            snprintf(cmd, sizeof cmd, "name %.60s", t);
            write_cmd(cmd);
            if (then_cmd && then_cmd[0]) write_cmd(then_cmd);
        }
    }
    gtk_widget_destroy(dlg);
}

static void on_save(GtkWidget *, gpointer) {
    if (G.doc_name[0]) {
        char cmd[96];
        fprintf(stderr, "cad_shell: Save overwrite name='%s'\n", G.doc_name);
        snprintf(cmd, sizeof cmd, "name %.48s", G.doc_name);
        write_cmd(cmd);
        write_cmd("saveover");
        return;
    }
    fprintf(stderr, "cad_shell: Save untitled → dialog\n");
    doc_dialog(DOC_SAVE);
}
static void on_save_as(GtkWidget *, gpointer) { doc_dialog(DOC_SAVE); }
static void on_load(GtkWidget *, gpointer) {
    if (!confirm_leave(NULL)) return;
    doc_dialog(DOC_OPEN);
}
static void on_delete_part(GtkWidget *, gpointer) { doc_dialog(DOC_DELETE); }
static void on_quit_btn(GtkWidget *, gpointer) {
    if (!confirm_leave(NULL)) return;
    request_quit();
}
static void on_export_step(GtkWidget *, gpointer) { write_cmd("step"); }
static void on_export_dxf(GtkWidget *, gpointer) { write_cmd("dxf"); }

static void session_set_guest(void) {
    G.session_guest = 1;
    snprintf(G.session_user, sizeof G.session_user, "guest");
    if (G.sess_btn) gtk_button_set_label(GTK_BUTTON(G.sess_btn), "Guest ▾");
}

static void session_set_user(const char *name) {
    G.session_guest = 0;
    snprintf(G.session_user, sizeof G.session_user, "%s", name && name[0] ? name : "user");
    if (G.sess_btn) {
        char lab[64];
        snprintf(lab, sizeof lab, "%s ▾", G.session_user);
        gtk_button_set_label(GTK_BUTTON(G.sess_btn), lab);
    }
}

static void on_login(GtkWidget *, gpointer) {
    GtkWidget *dlg = gtk_dialog_new_with_buttons(
        "Log in", GTK_WINDOW(G.win), GTK_DIALOG_MODAL,
        "Cancel", GTK_RESPONSE_CANCEL, "Log in", GTK_RESPONSE_ACCEPT, NULL);
    GtkWidget *box = gtk_dialog_get_content_area(GTK_DIALOG(dlg));
    GtkWidget *u = gtk_entry_new();
    GtkWidget *p = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(u), "user");
    gtk_entry_set_placeholder_text(GTK_ENTRY(p), "password");
    gtk_entry_set_visibility(GTK_ENTRY(p), FALSE);
    gtk_entry_set_activates_default(GTK_ENTRY(p), TRUE);
    gtk_container_add(GTK_CONTAINER(box), u);
    gtk_container_add(GTK_CONTAINER(box), p);
    gtk_widget_set_margin_start(u, 8);
    gtk_widget_set_margin_end(u, 8);
    gtk_widget_set_margin_top(u, 8);
    gtk_widget_set_margin_start(p, 8);
    gtk_widget_set_margin_end(p, 8);
    gtk_widget_set_margin_top(p, 4);
    gtk_widget_set_margin_bottom(p, 8);
    gtk_widget_show_all(dlg);
    gtk_dialog_set_default_response(GTK_DIALOG(dlg), GTK_RESPONSE_ACCEPT);
    if (gtk_dialog_run(GTK_DIALOG(dlg)) == GTK_RESPONSE_ACCEPT) {
        const char *name = gtk_entry_get_text(GTK_ENTRY(u));
        if (name && name[0]) session_set_user(name);
        /* password is not sent yet — pgcrypto / capabilities next */
    }
    gtk_widget_destroy(dlg);
}

static void on_guest(GtkWidget *, gpointer) { session_set_guest(); }

static void prompt_cmd_name(const char *title, const char *prefix, const char *seed) {
    GtkWidget *dlg = gtk_dialog_new_with_buttons(
        title, GTK_WINDOW(G.win), GTK_DIALOG_MODAL,
        "Cancel", GTK_RESPONSE_CANCEL, "OK", GTK_RESPONSE_ACCEPT, NULL);
    GtkWidget *box = gtk_dialog_get_content_area(GTK_DIALOG(dlg));
    GtkWidget *ent = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(ent), seed && seed[0] ? seed : "");
    gtk_entry_set_activates_default(GTK_ENTRY(ent), TRUE);
    gtk_container_add(GTK_CONTAINER(box), ent);
    gtk_widget_set_margin_start(ent, 8);
    gtk_widget_set_margin_end(ent, 8);
    gtk_widget_set_margin_top(ent, 8);
    gtk_widget_show_all(dlg);
    gtk_dialog_set_default_response(GTK_DIALOG(dlg), GTK_RESPONSE_ACCEPT);
    if (gtk_dialog_run(GTK_DIALOG(dlg)) == GTK_RESPONSE_ACCEPT) {
        const char *t = gtk_entry_get_text(GTK_ENTRY(ent));
        if (t && t[0]) {
            char cmd[96];
            snprintf(cmd, sizeof cmd, "%s %.48s", prefix, t);
            write_cmd(cmd);
        }
    }
    gtk_widget_destroy(dlg);
}

static void on_name_part(GtkWidget *, gpointer) {
    prompt_cmd_name("Part name", "name", "untitled");
}
static void on_name_sketch(GtkButton *, gpointer) {
    prompt_cmd_name("Sketch alias (Sketch_N stays)", "sname", "Machinebase");
}

static void on_plane_offset(GtkButton *, gpointer) {
    G.dim_kind = 1;
    G.dimn = 0;
    G.dimbuf[0] = 0;
    G.dim_sel = 0;
    write_cmd("plane_off");
    if (G.win) gtk_widget_grab_focus(G.win);
    if (G.da) gtk_widget_queue_draw(G.da);
}

static void on_plane_angle(GtkButton *, gpointer) {
    G.dim_kind = 2;
    G.dimn = 0;
    G.dimbuf[0] = 0;
    G.dim_sel = 0;
    write_cmd("plane_ang");
    if (G.win) gtk_widget_grab_focus(G.win);
    if (G.da) gtk_widget_queue_draw(G.da);
}

static void on_tree_fold(GtkButton *, gpointer) {
    if (!G.treev || !G.fold_btn) return;
    if (G.tree_open_all) {
        gtk_tree_view_collapse_all(GTK_TREE_VIEW(G.treev));
        gtk_button_set_label(GTK_BUTTON(G.fold_btn), "Expand");
        G.tree_open_all = 0;
    } else {
        gtk_tree_view_expand_all(GTK_TREE_VIEW(G.treev));
        gtk_button_set_label(GTK_BUTTON(G.fold_btn), "Collapse");
        G.tree_open_all = 1;
    }
}

static void hist_scale_changed(GtkRange *r, gpointer) {
    if (G.hist_ignore) return;
    int v = (int)gtk_range_get_value(r);
    char cmd[32];
    snprintf(cmd, sizeof cmd, "hist %d", v);
    write_cmd(cmd);
}

static void on_tl_chip(GtkButton *, gpointer data) {
    char cmd[32];
    snprintf(cmd, sizeof cmd, "hist %d", GPOINTER_TO_INT(data));
    write_cmd(cmd);
}

static void rebuild_tl_chips(const char *raw, int hn, int hc) {
    if (!G.tl_box) return;
    GList *kids = gtk_container_get_children(GTK_CONTAINER(G.tl_box));
    for (GList *l = kids; l; l = l->next)
        gtk_widget_destroy(GTK_WIDGET(l->data));
    g_list_free(kids);
    const char *p = strchr(raw, '\n');
    int i;
    for (i = 0; i < hn; i++) {
        char lab[32];
        snprintf(lab, sizeof lab, "%d", i + 1);
        if (p) {
            p++;
            const char *s = p;
            while (*s == ' ' || *s == '*' || *s == '.' || (*s >= '0' && *s <= '9')) s++;
            const char *nl = strchr(p, '\n');
            int n = nl ? (int)(nl - s) : (int)strlen(s);
            while (n > 0 && (s[n - 1] == '\n' || s[n - 1] == '\r' || s[n - 1] == ' ')) n--;
            if (n > 20) n = 20;
            if (n > 0) {
                memcpy(lab, s, (size_t)n);
                lab[n] = 0;
            }
            p = nl;
        }
        GtkWidget *b = gtk_button_new_with_label(lab);
        gtk_widget_set_name(b, i == hc ? "tlnow" : "tlchip");
        g_signal_connect(b, "clicked", G_CALLBACK(on_tl_chip), GINT_TO_POINTER(i));
        gtk_box_pack_start(GTK_BOX(G.tl_box), b, FALSE, FALSE, 0);
    }
    gtk_widget_show_all(G.tl_box);
}

static void load_hist(void) {
    char raw[1024];
    raw[0] = 0;
    FILE *f = fopen(path_hist, "r");
    if (f) {
        size_t n = fread(raw, 1, sizeof raw - 1, f);
        raw[n] = 0;
        fclose(f);
    }
    if (strcmp(raw, G.hist_cache) == 0) return;
    snprintf(G.hist_cache, sizeof G.hist_cache, "%s", raw);
    int hn = 0, hc = 0;
    sscanf(raw, "%d %d", &hn, &hc);
    if (hn < 1) hn = 1;
    if (hc < 0) hc = 0;
    if (hc >= hn) hc = hn - 1;
    if (G.hist_scale) {
        G.hist_ignore = 1;
        gtk_range_set_range(GTK_RANGE(G.hist_scale), 0, (double)(hn - 1));
        gtk_range_set_value(GTK_RANGE(G.hist_scale), (double)hc);
        G.hist_ignore = 0;
    }
    if (G.hist_lbl) {
        const char *lab = "—";
        char *p = strchr(raw, '\n');
        int i = 0;
        while (p && i <= hc) {
            p++;
            if (i == hc) {
                while (*p == ' ' || *p == '*' || *p == '.' || (*p >= '0' && *p <= '9')) p++;
                lab = p;
                break;
            }
            char *nl = strchr(p, '\n');
            if (!nl) break;
            p = nl;
            i++;
        }
        char shown[96];
        snprintf(shown, sizeof shown, "%d / %d   %s", hc + 1, hn, lab);
        char *nl = strchr(shown, '\n');
        if (nl) *nl = 0;
        gtk_label_set_text(GTK_LABEL(G.hist_lbl), shown);
    }
    rebuild_tl_chips(raw, hn, hc);
}

static void show_timeline(void) {
    if (G.tl_dock) {
        gtk_widget_show(G.tl_dock);
        gtk_widget_grab_focus(G.tl_dock);
    }
    G.hist_cache[0] = 0;
    load_hist();
}

static void on_tree_edit(GtkMenuItem *, gpointer) {
    if (G.tree_edit_cmd[0]) write_cmd(G.tree_edit_cmd);
}
static void on_tree_name(GtkMenuItem *, gpointer) {
    char kind = 0;
    int id = 0;
    if (sscanf(G.tree_edit_cmd, "tree %c %d", &kind, &id) != 2) return;
    char prefix[40];
    const char *title = "Name";
    const char *seed = "";
    if (kind == 'S') {
        title = "Name this sketch (Sketch_N stays)";
        snprintf(prefix, sizeof prefix, "sname %d", id);
        seed = "Machinebase";
    } else if (kind == 'M' || kind == 'P') {
        title = "Name this part";
        snprintf(prefix, sizeof prefix, "name");
        seed = "untitled";
    } else {
        title = "Name this feature (type stays)";
        snprintf(prefix, sizeof prefix, "fname %d", id);
        seed = "Boss";
    }
    prompt_cmd_name(title, prefix, seed);
}
static void on_tree_back(GtkMenuItem *, gpointer) { write_cmd("undo"); }
static void on_tree_fwd(GtkMenuItem *, gpointer) { write_cmd("redo"); }
static void on_tree_timeline(GtkMenuItem *, gpointer) { show_timeline(); }

static void popup_tree_menu(GdkEventButton *e) {
    GtkWidget *m = gtk_menu_new();
    const char *labs[] = {"Edit / Modify", "Name…", "Back", "Forward", "Timeline", NULL};
    void (*fns[])(GtkMenuItem *, gpointer) = {
        on_tree_edit, on_tree_name, on_tree_back, on_tree_fwd, on_tree_timeline
    };
    int i;
    for (i = 0; labs[i]; i++) {
        GtkWidget *it = gtk_menu_item_new_with_label(labs[i]);
        g_signal_connect(it, "activate", G_CALLBACK(fns[i]), NULL);
        gtk_menu_shell_append(GTK_MENU_SHELL(m), it);
    }
    gtk_widget_show_all(m);
    gtk_menu_popup_at_pointer(GTK_MENU(m), (GdkEvent *)e);
}

/* Kernel dimhud.txt is one line of KEY=val tokens; [KEY=val] is the active field.
 * Chrome turns that into a multi-line card so the typed value has a home. */
struct DimField {
    char key[8];
    char val[16];
    int active;
};
struct DimCard {
    char kind[16];
    DimField f[4];
    int n;
};

static void dim_label_unit(const char *kind, const char *key,
                           const char **lab, const char **unit) {
    *lab = key;
    *unit = "";
    if (key[0] == 'N') { *lab = "Sides"; *unit = ""; }
    else if (key[0] == 'D') {
        if (kind[0] == 'C' && kind[1] == 'H') { *lab = "Distance"; *unit = "mm"; }
        else { *lab = "Diameter"; *unit = "mm"; }
    }
    else if (key[0] == 'A') { *lab = "Angle"; *unit = "deg"; }
    else if (key[0] == 'R') { *lab = "Radius"; *unit = "mm"; }
    else if (key[0] == 'W') { *lab = "Width"; *unit = "mm"; }
    else if (key[0] == 'H') { *lab = "Height"; *unit = "mm"; }
    else if (key[0] == 'O') { *lab = "Operation"; *unit = ""; }
    else if (key[0] == 'X') { *lab = "X"; *unit = "mm"; }
    else if (key[0] == 'Y') { *lab = "Y"; *unit = "mm"; }
    else if (key[0] == 'U') { *lab = "U"; *unit = "mm"; }
    else if (key[0] == 'V') { *lab = "V"; *unit = "mm"; }
    else if (key[0] == 'L') {
        if (kind[0] == 'P') { *lab = "Side"; *unit = "mm"; }
        else { *lab = "Length"; *unit = "mm"; }
    }
}

static int parse_dimhud(const char *s, DimCard *d) {
    memset(d, 0, sizeof *d);
    if (!s || !s[0]) return 0;
    const char *p = s;
    int ki = 0;
    while (*p && *p != ' ' && ki < 15) d->kind[ki++] = *p++;
    while (*p) {
        while (*p == ' ') p++;
        if (!*p) break;
        int br = 0;
        if (*p == '[') { br = 1; p++; }
        char k[8]; int n = 0;
        while (*p && *p != '=' && *p != ' ' && *p != ']' && n < 7) k[n++] = *p++;
        k[n] = 0;
        if (*p != '=') {
            while (*p && *p != ' ' && *p != ']') p++;
            if (*p == ']') p++;
            continue;
        }
        p++;
        char v[16]; n = 0;
        while (*p && *p != ' ' && *p != ']' && n < 15) v[n++] = *p++;
        v[n] = 0;
        if (*p == ']') p++;
        if (d->n < 4 && k[0]) {
            snprintf(d->f[d->n].key, sizeof d->f[0].key, "%s", k);
            snprintf(d->f[d->n].val, sizeof d->f[0].val, "%s", v);
            d->f[d->n].active = br;
            d->n++;
        }
    }
    return d->n > 0 || d->kind[0];
}

static void draw_edit_hud(cairo_t *cr, GtkAllocation *al) {
    if (G.dimn <= 0 && G.dim_kind == 0 && !G.dimhud[0]) return;

    DimCard card;
    memset(&card, 0, sizeof card);
    int parsed = 0;
    if (G.dim_kind == 1) {
        snprintf(card.kind, sizeof card.kind, "OFFSET");
        snprintf(card.f[0].key, sizeof card.f[0].key, "OFF");
        snprintf(card.f[0].val, sizeof card.f[0].val, "%s", G.dimbuf[0] ? G.dimbuf : "");
        card.f[0].active = 1;
        card.n = 1;
        parsed = 1;
    } else if (G.dim_kind == 2) {
        snprintf(card.kind, sizeof card.kind, "ANGLE");
        snprintf(card.f[0].key, sizeof card.f[0].key, "A");
        snprintf(card.f[0].val, sizeof card.f[0].val, "%s", G.dimbuf[0] ? G.dimbuf : "");
        card.f[0].active = 1;
        card.n = 1;
        parsed = 1;
    } else if (G.dimhud[0]) {
        parsed = parse_dimhud(G.dimhud, &card);
    }
    if (!parsed) {
        snprintf(card.kind, sizeof card.kind, "DIM");
        snprintf(card.f[0].key, sizeof card.f[0].key, "L");
        card.f[0].active = 1;
        card.n = 1;
    }

    const char *title = card.kind;
    if (strcmp(card.kind, "POLY") == 0) title = "POLYGON";
    else if (strcmp(card.kind, "LINE") == 0) title = "LINE";
    else if (strcmp(card.kind, "CIRC") == 0) title = "CIRCLE";
    else if (strcmp(card.kind, "RECT") == 0) title = "RECTANGLE";
    else if (strcmp(card.kind, "FILLET") == 0) title = "FILLET";
    else if (strcmp(card.kind, "CHAMFER") == 0) title = "CHAMFER";
    else if (strcmp(card.kind, "EXTRUDE") == 0) title = "EXTRUDE";
    else if (strcmp(card.kind, "PAD") == 0) title = "EXTRUDE";
    else if (strcmp(card.kind, "CSTR") == 0) title = "CONSTRAINT";
    else if (strcmp(card.kind, "ABS") == 0) title = "ABSOLUTE  (origin)";
    else if (strcmp(card.kind, "REL") == 0) title = "RELATIVE  (geometry)";
    else if (strcmp(card.kind, "OFFSET") == 0) title = "OFFSET PLANE";
    else if (strcmp(card.kind, "ANGLE") == 0) title = "ANGLE PLANE";

    const int pad = 14;
    const int row_h = 30;
    const int title_h = 26;
    const int hint_h = 22;
    const int card_w = 292;
    int card_h = pad + title_h + card.n * row_h + hint_h + pad;
    int x = 20;
    int y = al->height - card_h - 20;
    if (y < 12) y = 12;

    cairo_set_source_rgb(cr, 0.07, 0.09, 0.12);
    cairo_rectangle(cr, x, y, card_w, card_h);
    cairo_fill(cr);
    cairo_set_source_rgb(cr, 1.0, 0.82, 0.16);
    cairo_set_line_width(cr, 1.6);
    cairo_rectangle(cr, x + 0.5, y + 0.5, card_w - 1, card_h - 1);
    cairo_stroke(cr);

    cairo_select_font_face(cr, "sans-serif", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_BOLD);
    cairo_set_font_size(cr, 17);
    cairo_set_source_rgb(cr, 1.0, 0.88, 0.30);
    cairo_move_to(cr, x + pad, y + pad + 16);
    cairo_show_text(cr, title);

    int i;
    for (i = 0; i < card.n; i++) {
        int ry = y + pad + title_h + i * row_h;
        const char *lab = card.f[i].key;
        const char *unit = "";
        dim_label_unit(card.kind, card.f[i].key, &lab, &unit);
        int act = card.f[i].active;
        if (act) {
            cairo_set_source_rgb(cr, 0.16, 0.18, 0.10);
            cairo_rectangle(cr, x + 6, ry, card_w - 12, row_h - 3);
            cairo_fill(cr);
            cairo_set_source_rgb(cr, 1.0, 0.82, 0.16);
            cairo_rectangle(cr, x + 6, ry, 4, row_h - 3);
            cairo_fill(cr);
        }
        cairo_select_font_face(cr, "sans-serif", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_BOLD);
        cairo_set_font_size(cr, 16);
        cairo_set_source_rgb(cr, act ? 1.0 : 0.70, act ? 0.95 : 0.73, act ? 0.70 : 0.76);
        cairo_move_to(cr, x + pad + 8, ry + 20);
        cairo_show_text(cr, lab);

        char rhs[48];
        const char *shown = card.f[i].val;
        if (act && (G.dimn > 0 || G.dim_sel)) shown = G.dimbuf;
        int empty = (!shown[0] || strcmp(shown, "_") == 0);
        if (act) {
            if (empty)
                snprintf(rhs, sizeof rhs, "=  ??");
            else
                snprintf(rhs, sizeof rhs, "=  %s", shown);
        } else {
            if (empty) snprintf(rhs, sizeof rhs, "   —");
            else snprintf(rhs, sizeof rhs, "   %s", shown);
        }
        cairo_move_to(cr, x + 118, ry + 20);
        cairo_show_text(cr, rhs);

        if (unit[0] && !(act && empty)) {
            cairo_select_font_face(cr, "sans-serif", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL);
            cairo_set_font_size(cr, 13);
            cairo_set_source_rgb(cr, 0.62, 0.66, 0.70);
            cairo_text_extents_t te;
            cairo_text_extents(cr, rhs, &te);
            cairo_move_to(cr, x + 118 + te.x_advance + 8, ry + 20);
            cairo_show_text(cr, unit);
        }
        if (act && G.hud_blink) {
            cairo_set_source_rgb(cr, 1.0, 0.90, 0.25);
            cairo_text_extents_t te;
            cairo_select_font_face(cr, "sans-serif", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_BOLD);
            cairo_set_font_size(cr, 16);
            cairo_text_extents(cr, rhs, &te);
            int cx = x + 118 + (int)te.x_advance + 3;
            cairo_rectangle(cr, cx, ry + 5, 2, 18);
            cairo_fill(cr);
        }
    }

    cairo_select_font_face(cr, "sans-serif", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL);
    cairo_set_font_size(cr, 11);
    cairo_set_source_rgb(cr, 0.55, 0.60, 0.66);
    cairo_move_to(cr, x + pad, y + card_h - pad + 2);
    cairo_show_text(cr, "Tab next   Enter apply   Esc close   F1 help");
}

static const char *k_help_fallback =
    "AILang CAD — quick help (F1)\n"
    "\n"
    "Yellow card (lower left): one field per row. The bright row with = and\n"
    "a blinking cursor is what you type. Empty looks like  Side = ??\n"
    "  Tab = next field    Enter = apply    Esc = close\n"
    "\n"
    "Line: click two points → Length (mm) and Angle (deg from +X).\n"
    "Polygon (Center): click center → Sides, Side length, Diameter.\n"
    "  Enter on Side or Diameter places the n-gon. Second click also places.\n"
    "\n"
    "Esc cancels the current click. Right-click = tool pie.\n"
    "The solid stays on screen in Sketch. On Face looks at that plane.\n"
    "Project (Sketch tab / pie) shows dashed face edges + gold anchors.\n"
    "Construct: Pick Plane / From Face / Origin / Through 3pt, then Offset\n"
    "or Angle, then Sketch on Plane. Tree Plane rows activate the plane.\n"
    "Solid tab: On Face or Profiles → Pad.\n"
    "Work tree names sketches; timeline at the bottom is undo/redo.\n"
    "\n"
    "Full notes: docs/cad/CAD_UI_MANUAL.md\n";

static void on_help(GtkButton *, gpointer) {
    GtkWidget *dlg = gtk_dialog_new_with_buttons(
        "How to use AILang CAD   (F1)", GTK_WINDOW(G.win),
        GTK_DIALOG_MODAL, "Close", GTK_RESPONSE_CLOSE, NULL);
    gtk_window_set_default_size(GTK_WINDOW(dlg), 640, 520);
    GtkWidget *box = gtk_dialog_get_content_area(GTK_DIALOG(dlg));
    GtkWidget *scr = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scr),
                                   GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_vexpand(scr, TRUE);
    GtkWidget *tv = gtk_text_view_new();
    gtk_text_view_set_wrap_mode(GTK_TEXT_VIEW(tv), GTK_WRAP_WORD);
    gtk_text_view_set_editable(GTK_TEXT_VIEW(tv), FALSE);
    gtk_text_view_set_cursor_visible(GTK_TEXT_VIEW(tv), FALSE);
    gtk_text_view_set_left_margin(GTK_TEXT_VIEW(tv), 12);
    gtk_text_view_set_right_margin(GTK_TEXT_VIEW(tv), 12);
    gtk_text_view_set_top_margin(GTK_TEXT_VIEW(tv), 10);
    GtkTextBuffer *tb = gtk_text_view_get_buffer(GTK_TEXT_VIEW(tv));
    const char *paths[] = {
        "docs/cad/CAD_UI_MANUAL.md",
        "/home/bob/Ailang-Self-Hosting-/docs/cad/CAD_UI_MANUAL.md",
        NULL
    };
    int loaded = 0;
    int i;
    for (i = 0; paths[i]; i++) {
        gchar *txt = NULL;
        if (g_file_get_contents(paths[i], &txt, NULL, NULL) && txt) {
            gtk_text_buffer_set_text(tb, txt, -1);
            g_free(txt);
            loaded = 1;
            break;
        }
    }
    if (!loaded) gtk_text_buffer_set_text(tb, k_help_fallback, -1);
    gtk_container_add(GTK_CONTAINER(scr), tv);
    gtk_box_pack_start(GTK_BOX(box), scr, TRUE, TRUE, 0);
    gtk_widget_set_margin_start(scr, 6);
    gtk_widget_set_margin_end(scr, 6);
    gtk_widget_set_margin_top(scr, 6);
    gtk_widget_set_margin_bottom(scr, 6);
    gtk_widget_show_all(dlg);
    gtk_dialog_run(GTK_DIALOG(dlg));
    gtk_widget_destroy(dlg);
}

static gboolean on_draw(GtkWidget *w, cairo_t *cr, gpointer) {
    GtkAllocation al;
    gtk_widget_get_allocation(w, &al);
    cairo_set_source_rgb(cr, 15 / 255.0, 18 / 255.0, 23 / 255.0);
    cairo_paint(cr);

    if (G.frame && G.fw > 0 && G.fh > 0) {
        G.ox = (al.width - G.fw) / 2;
        G.oy = (al.height - G.fh) / 2;
        if (G.ox < 0) G.ox = 0;
        if (G.oy < 0) G.oy = 0;
        cairo_set_source_surface(cr, G.frame, G.ox, G.oy);
        cairo_paint(cr);
    }

    int mode = 0, tool = 0, nclick = 0;
    read_tool_state(&mode, &tool, &nclick);
    int show_rb = 0;
    if (mode == 1) {
        if (G.have_anchor || nclick > 0 || (G.dragging && !G.pan_mode)) show_rb = 1;
    }
    if (show_rb && !G.mmb) {
        int x0 = G.ox + (G.have_anchor ? G.anchor_fx : G.down_fx);
        int y0 = G.oy + (G.have_anchor ? G.anchor_fy : G.down_fy);
        int x1 = G.ox + G.cur_fx;
        int y1 = G.oy + G.cur_fy;
        int dx = x1 - x0;
        int dy = y1 - y0;
        double dist = sqrt((double)dx * dx + (double)dy * dy);
        double ang = atan2((double)-dy, (double)dx) * 180.0 / M_PI;
        if (ang < 0) ang += 360.0;

        cairo_set_source_rgb(cr, 0.0, 0.90, 0.91);
        cairo_set_line_width(cr, 1.6);
        if (tool == 1) {
            /* 2-point rect: corner → opposite corner */
            double dashes[] = {5.0, 3.0};
            cairo_set_dash(cr, dashes, 2, 0);
            cairo_rectangle(cr, (x0 < x1) ? x0 : x1, (y0 < y1) ? y0 : y1,
                            fabs((double)dx), fabs((double)dy));
            cairo_stroke(cr);
            cairo_set_dash(cr, NULL, 0, 0);
        } else if (tool == 15) {
            /* center rect: first click is center */
            double dashes[] = {5.0, 3.0};
            cairo_set_dash(cr, dashes, 2, 0);
            cairo_rectangle(cr, x0 - fabs((double)dx), y0 - fabs((double)dy),
                            2.0 * fabs((double)dx), 2.0 * fabs((double)dy));
            cairo_stroke(cr);
            cairo_set_dash(cr, NULL, 0, 0);
            cairo_move_to(cr, x0, y0);
            cairo_line_to(cr, x1, y1);
            cairo_stroke(cr);
        } else if (tool == 16) {
            /* 3-point: first click = edge start. After nclick>=2 kernel owns the box. */
            double dashes[] = {5.0, 3.0};
            cairo_set_dash(cr, dashes, 2, 0);
            if (nclick >= 2) {
                /* kernel framebuffer has the oriented preview */
            } else {
                cairo_move_to(cr, x0, y0);
                cairo_line_to(cr, x1, y1);
                cairo_stroke(cr);
            }
            cairo_set_dash(cr, NULL, 0, 0);
        } else if (tool == 2 || tool == 13 || tool == 14) {
            double dashes[] = {5.0, 3.0};
            cairo_set_dash(cr, dashes, 2, 0);
            cairo_arc(cr, x0, y0, dist > 1.0 ? dist : 1.0, 0, 6.283185307179586);
            cairo_stroke(cr);
            cairo_set_dash(cr, NULL, 0, 0);
            cairo_move_to(cr, x0, y0);
            cairo_line_to(cr, x1, y1);
            cairo_stroke(cr);
        } else if (tool == 3 || tool == 12 || tool == 9) {
            double dashes[] = {5.0, 3.0};
            cairo_set_dash(cr, dashes, 2, 0);
            cairo_arc(cr, x0, y0, dist > 1.0 ? dist : 1.0, 0, ang * M_PI / 180.0);
            cairo_stroke(cr);
            cairo_set_dash(cr, NULL, 0, 0);
            cairo_move_to(cr, x0, y0);
            cairo_line_to(cr, x1, y1);
            cairo_stroke(cr);
        } else if (tool == 17) {
            double dashes[] = {5.0, 3.0};
            cairo_set_dash(cr, dashes, 2, 0);
            int ns = 6;
            if (ns < 3) ns = 3;
            double a0 = atan2((double)dy, (double)dx);
            double step = 6.283185307179586 / (double)ns;
            int i;
            for (i = 0; i < ns; i++) {
                double a = a0 + step * i;
                double b = a0 + step * (i + 1);
                cairo_move_to(cr, x0 + dist * cos(a), y0 + dist * sin(a));
                cairo_line_to(cr, x0 + dist * cos(b), y0 + dist * sin(b));
            }
            cairo_stroke(cr);
            cairo_set_dash(cr, NULL, 0, 0);
        } else {
            cairo_move_to(cr, x0, y0);
            cairo_line_to(cr, x1, y1);
            cairo_stroke(cr);
        }
        cairo_set_source_rgb(cr, 1.0, 0.24, 0.24);
        cairo_rectangle(cr, x0 - 3, y0 - 3, 7, 7);
        cairo_fill(cr);
        cairo_set_source_rgb(cr, 0.0, 0.90, 0.91);
        cairo_move_to(cr, x1 - 10, y1);
        cairo_line_to(cr, x1 + 10, y1);
        cairo_move_to(cr, x1, y1 - 10);
        cairo_line_to(cr, x1, y1 + 10);
        cairo_stroke(cr);
        cairo_rectangle(cr, x1 - 3, y1 - 3, 7, 7);
        cairo_fill(cr);

        char tip[128];
        if (tool == 0) snprintf(tip, sizeof tip, "L %.1f px   %.1f deg", dist, ang);
        else if (tool == 1)
            snprintf(tip, sizeof tip, "W %d   H %d", abs(dx), abs(dy));
        else if (tool == 15)
            snprintf(tip, sizeof tip, "center  W %d  H %d", abs(dx) * 2, abs(dy) * 2);
        else if (tool == 16)
            snprintf(tip, sizeof tip, nclick >= 2 ? "3-pt rect  height" : "3-pt rect  first edge");
        else if (tool == 2 || tool == 13 || tool == 14)
            snprintf(tip, sizeof tip, "R %.1f   Dia %.1f", dist, dist * 2.0);
        else if (tool == 3 || tool == 9 || tool == 12)
            snprintf(tip, sizeof tip, "R %.1f   %.1f deg", dist, ang);
        else
            snprintf(tip, sizeof tip, "X %d  Y %d", G.cur_fx, G.cur_fy);

        cairo_select_font_face(cr, "Sans", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_BOLD);
        cairo_set_font_size(cr, 12);
        cairo_text_extents_t te;
        cairo_text_extents(cr, tip, &te);
        int tx = x1 + 14;
        int ty = y1 - 18;
        if (tx + (int)te.width + 16 > al.width) tx = x1 - (int)te.width - 22;
        if (ty < 8) ty = y1 + 20;
        cairo_set_source_rgb(cr, 16 / 255.0, 20 / 255.0, 28 / 255.0);
        cairo_rectangle(cr, tx - 4, ty - te.height - 4, te.width + 14, te.height + 10);
        cairo_fill(cr);
        cairo_set_source_rgb(cr, 0.0, 0.77, 0.78);
        cairo_rectangle(cr, tx - 4, ty - te.height - 4, te.width + 14, te.height + 10);
        cairo_stroke(cr);
        cairo_set_source_rgb(cr, 1, 1, 1);
        cairo_move_to(cr, tx + 2, ty);
        cairo_show_text(cr, tip);
    }

    if (G.pie_on && G.pie_n > 0) {
        const double R0 = 28, R1 = 96;
        int i;
        for (i = 0; i < G.pie_n; i++) {
            double a0 = (2 * M_PI * i) / G.pie_n;
            double a1 = (2 * M_PI * (i + 1)) / G.pie_n;
            cairo_move_to(cr, G.pie_cx + cos(a0) * R0, G.pie_cy + sin(a0) * R0);
            cairo_arc(cr, G.pie_cx, G.pie_cy, R1, a0, a1);
            cairo_arc_negative(cr, G.pie_cx, G.pie_cy, R0, a1, a0);
            cairo_close_path(cr);
            if (i == G.pie_hit) cairo_set_source_rgb(cr, 0.08, 0.78, 0.78);
            else cairo_set_source_rgb(cr, 0.10, 0.12, 0.16);
            cairo_fill_preserve(cr);
            cairo_set_source_rgb(cr, 0.95, 0.97, 1.0);
            cairo_set_line_width(cr, 1.2);
            cairo_stroke(cr);
            double am = 0.5 * (a0 + a1);
            double tx = G.pie_cx + cos(am) * 62;
            double ty = G.pie_cy + sin(am) * 62;
            cairo_select_font_face(cr, "sans-serif", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_BOLD);
            cairo_set_font_size(cr, 11);
            cairo_text_extents_t te;
            cairo_text_extents(cr, G.pie_lab[i], &te);
            cairo_set_source_rgb(cr, 1, 1, 1);
            cairo_move_to(cr, tx - te.width * 0.5, ty + te.height * 0.35);
            cairo_show_text(cr, G.pie_lab[i]);
        }
        cairo_set_source_rgb(cr, 0.07, 0.08, 0.10);
        cairo_arc(cr, G.pie_cx, G.pie_cy, 22, 0, 2 * M_PI);
        cairo_fill(cr);
        cairo_set_source_rgb(cr, 0.95, 0.97, 1.0);
        cairo_set_font_size(cr, 10);
        cairo_text_extents_t te;
        cairo_text_extents(cr, "ESC", &te);
        cairo_move_to(cr, G.pie_cx - te.width * 0.5, G.pie_cy + te.height * 0.35);
        cairo_show_text(cr, "ESC");
        if (G.pie_sub >= 0 && G.pie_vn > 0) {
            const double R1 = 96;
            double am = (2 * M_PI * (G.pie_sub + 0.5)) / G.pie_n;
            int lx = (int)(G.pie_cx + cos(am) * (R1 + 12));
            int ly = (int)(G.pie_cy + sin(am) * (R1 + 12) - G.pie_vn * 11);
            int vw = 148, vh = G.pie_vn * 22 + 6;
            if (lx + vw > al.width) lx = G.pie_cx - vw - (int)(R1 + 12);
            if (ly < 4) ly = 4;
            cairo_set_source_rgb(cr, 0.08, 0.10, 0.14);
            cairo_rectangle(cr, lx, ly, vw, vh);
            cairo_fill_preserve(cr);
            cairo_set_source_rgb(cr, 0.95, 0.97, 1.0);
            cairo_set_line_width(cr, 1.2);
            cairo_stroke(cr);
            int vi;
            for (vi = 0; vi < G.pie_vn; vi++) {
                int yy = ly + 3 + vi * 22;
                if (vi == G.pie_vhit) {
                    cairo_set_source_rgb(cr, 0.08, 0.78, 0.78);
                    cairo_rectangle(cr, lx + 2, yy, vw - 4, 20);
                    cairo_fill(cr);
                    cairo_set_source_rgb(cr, 0.04, 0.08, 0.10);
                } else {
                    cairo_set_source_rgb(cr, 1, 1, 1);
                }
                cairo_set_font_size(cr, 11);
                cairo_move_to(cr, lx + 8, yy + 14);
                cairo_show_text(cr, G.pie_vlab[vi]);
            }
        }
    }
    draw_edit_hud(cr, &al);
    return FALSE;
}

static void frame_xy(GdkEvent *ev, int *fx, int *fy) {
    double x = 0, y = 0;
    if (ev->type == GDK_BUTTON_PRESS || ev->type == GDK_BUTTON_RELEASE || ev->type == GDK_2BUTTON_PRESS)
        x = ev->button.x, y = ev->button.y;
    else if (ev->type == GDK_MOTION_NOTIFY)
        x = ev->motion.x, y = ev->motion.y;
    *fx = (int)x - G.ox;
    *fy = (int)y - G.oy;
}

static void load_palette(void) {
    G.pie_n = 0;
    FILE *f = fopen(path_cmds, "r");
    if (f) {
        char line[80];
        while (G.pie_n < 12 && fgets(line, sizeof line, f)) {
            char *bar = strchr(line, '|');
            if (!bar) continue;
            *bar++ = 0;
            size_t L = strlen(bar);
            while (L && (bar[L - 1] == '\n' || bar[L - 1] == '\r')) bar[--L] = 0;
            snprintf(G.pie_cmd[G.pie_n], sizeof G.pie_cmd[0], "%s", line);
            snprintf(G.pie_lab[G.pie_n], sizeof G.pie_lab[0], "%s", bar);
            G.pie_n++;
        }
        fclose(f);
    }
    if (G.pie_n < 1) {
        static const char *fb[][2] = {
            {"cancel", "Cancel"}, {"tool_line", "Line"}, {"tool_circ", "Circle"},
            {"tool_poly6", "Polygon"}, {"tool_pick", "Pick"}, {"ontop", "Sketch Face"},
            {"sketch_pln", "Sketch Plane"}, {"repad", "Pad"}, {"iso", "ISO"},
        };
        int i;
        for (i = 0; i < 9; i++) {
            snprintf(G.pie_cmd[i], sizeof G.pie_cmd[0], "%s", fb[i][0]);
            snprintf(G.pie_lab[i], sizeof G.pie_lab[0], "%s", fb[i][1]);
        }
        G.pie_n = 9;
    }
}

static int pie_pick_at(int x, int y) {
    if (!G.pie_on || G.pie_n < 1) return -1;
    double dx = x - G.pie_cx;
    double dy = y - G.pie_cy;
    double d = hypot(dx, dy);
    if (d < 22.0) return -1;
    if (d > 110.0) return -1;
    double ang = atan2(dy, dx);
    if (ang < 0) ang += 2 * M_PI;
    int i = (int)(ang / (2 * M_PI) * G.pie_n);
    if (i < 0) i = 0;
    if (i >= G.pie_n) i = G.pie_n - 1;
    return i;
}

static int pie_fill_variants(const char *cmd) {
    G.pie_vn = 0;
    G.pie_vhit = -1;
    struct PieVar { const char *c; const char *l; };
    const PieVar *v = NULL;
    int n = 0;
    static const PieVar linev[] = {
        {"tool_line", "Line"},
        {"tool_rect", "2-Point Rect"},
        {"tool_rectc", "Center Rect"},
        {"tool_rect3", "3-Point Rect"},
    };
    static const PieVar circv[] = {
        {"tool_circ", "Center Radius"},
        {"tool_circ2", "2-Point Circle"},
        {"tool_circ3", "3-Point Circle"},
        {"tool_arc3", "3-Point Arc"},
        {"tool_arc2", "2-Point Arc"},
        {"tool_arc", "Center Arc"},
    };
    static const PieVar polyv[] = {
        {"pmode 0", "Center"},
        {"pmode 1", "2-Point"},
        {"pmode 2", "3-Point"},
        {"tool_poly3", "Triangle"},
        {"tool_poly4", "Square"},
        {"tool_poly6", "Hexagon"},
        {"tool_poly8", "Octagon"},
    };
    if (strcmp(cmd, "tool_line") == 0) { v = linev; n = 4; }
    else if (strcmp(cmd, "tool_circ") == 0) { v = circv; n = 6; }
    else if (strcmp(cmd, "tool_poly6") == 0) { v = polyv; n = 7; }
    int i;
    for (i = 0; i < n && i < 8; i++) {
        snprintf(G.pie_vcmd[i], sizeof G.pie_vcmd[0], "%s", v[i].c);
        snprintf(G.pie_vlab[i], sizeof G.pie_vlab[0], "%s", v[i].l);
        G.pie_vn++;
    }
    return G.pie_vn;
}

static void pie_submenu_rect(int *ox, int *oy, int *vw, int *vh) {
    GtkAllocation al;
    gtk_widget_get_allocation(G.da, &al);
    const double R1 = 96;
    double am = (2 * M_PI * (G.pie_sub + 0.5)) / (G.pie_n > 0 ? G.pie_n : 1);
    *vw = 148;
    *vh = G.pie_vn * 22 + 6;
    *ox = (int)(G.pie_cx + cos(am) * (R1 + 12));
    *oy = (int)(G.pie_cy + sin(am) * (R1 + 12) - G.pie_vn * 11);
    if (*ox + *vw > al.width) *ox = G.pie_cx - *vw - (int)(R1 + 12);
    if (*oy < 4) *oy = 4;
}

static int pie_var_hit_at(int x, int y) {
    if (!G.pie_on || G.pie_sub < 0 || G.pie_vn < 1) return -1;
    int ox, oy, vw, vh;
    pie_submenu_rect(&ox, &oy, &vw, &vh);
    if (x < ox || y < oy || x >= ox + vw || y >= oy + vh) return -1;
    int i = (y - oy - 3) / 22;
    if (i < 0) i = 0;
    if (i >= G.pie_vn) i = G.pie_vn - 1;
    return i;
}

static void pie_close(void) {
    G.pie_on = 0;
    G.pie_sub = -1;
    G.pie_vn = 0;
    G.pie_vhit = -1;
}

static int pie_activate(int slice) {
    if (slice < 0 || slice >= G.pie_n) return 0;
    if (pie_fill_variants(G.pie_cmd[slice]) > 0) {
        G.pie_sub = slice;
        G.pie_hit = slice;
        return 0;
    }
    write_cmd(G.pie_cmd[slice]);
    pie_close();
    return 1;
}

static gboolean on_button(GtkWidget *, GdkEventButton *e, gpointer) {
    int fx = (int)e->x - G.ox;
    int fy = (int)e->y - G.oy;
    G.cur_fx = fx;
    G.cur_fy = fy;
    if (e->type == GDK_BUTTON_PRESS && e->button == 3) {
        if (G.pie_on) {
            int v = pie_var_hit_at((int)e->x, (int)e->y);
            if (v >= 0) {
                write_cmd(G.pie_vcmd[v]);
                pie_close();
                gtk_widget_queue_draw(G.da);
                return TRUE;
            }
            int h = pie_pick_at((int)e->x, (int)e->y);
            if (h >= 0) {
                pie_activate(h);
                gtk_widget_queue_draw(G.da);
                return TRUE;
            }
            pie_close();
            gtk_widget_queue_draw(G.da);
            return TRUE;
        }
        G.pie_on = 1;
        G.pie_cx = (int)e->x;
        G.pie_cy = (int)e->y;
        G.pie_hit = -1;
        G.pie_sub = -1;
        G.pie_vn = 0;
        G.pie_vhit = -1;
        load_palette();
        gtk_widget_queue_draw(G.da);
        return TRUE;
    }
    if (e->type == GDK_BUTTON_RELEASE && e->button == 3 && G.pie_on) {
        if (G.pie_sub >= 0) {
            int v = pie_var_hit_at((int)e->x, (int)e->y);
            if (v >= 0) {
                write_cmd(G.pie_vcmd[v]);
                pie_close();
            }
            gtk_widget_queue_draw(G.da);
            return TRUE;
        }
        if (G.pie_hit >= 0) pie_activate(G.pie_hit);
        else pie_close();
        gtk_widget_queue_draw(G.da);
        return TRUE;
    }
    if (e->type == GDK_BUTTON_PRESS && e->button == 2) {
        /* handle only — kernel owns pan */
        G.mmb = 1;
        G.last_fx = fx;
        G.last_fy = fy;
        return TRUE;
    }
    if (e->type == GDK_BUTTON_RELEASE && e->button == 2) {
        G.mmb = 0;
        return TRUE;
    }
    if (e->type == GDK_BUTTON_PRESS && e->button == 1 && G.pie_on) {
        int v = pie_var_hit_at((int)e->x, (int)e->y);
        if (v >= 0) {
            write_cmd(G.pie_vcmd[v]);
            pie_close();
            gtk_widget_queue_draw(G.da);
            return TRUE;
        }
        int h = pie_pick_at((int)e->x, (int)e->y);
        if (h >= 0) pie_activate(h);
        else pie_close();
        gtk_widget_queue_draw(G.da);
        return TRUE;
    }
    if (e->type == GDK_BUTTON_PRESS && e->button == 1) {
        G.dragging = 1;
        G.moved = 0;
        G.pan_mode = 0;
        G.down_fx = G.last_fx = fx;
        G.down_fy = G.last_fy = fy;
        G.click_sh = (e->state & GDK_SHIFT_MASK) ? 1 : 0;
        clock_gettime(CLOCK_MONOTONIC, &G.down_ts);
        gtk_widget_queue_draw(G.da);
        return TRUE;
    }
    if (e->type == GDK_BUTTON_RELEASE && e->button == 1 && G.dragging) {
        int mode = 0, tool = 0, nclick = 0;
        read_tool_state(&mode, &tool, &nclick);
        int adx = abs(fx - G.down_fx), ady = abs(fy - G.down_fy);
        G.dragging = 0;
        if (mode == 1) {
            /* drag with no pending click = camera (kernel). click = sketch. */
            if (G.moved && (adx >= 3 || ady >= 3) && nclick == 0 && !G.have_anchor) {
                gtk_widget_queue_draw(G.da);
                return TRUE;
            }
            if (G.fw > 0 && G.fh > 0) {
                int cx = (G.moved && (adx >= 3 || ady >= 3)) ? fx : G.down_fx;
                int cy = (G.moved && (adx >= 3 || ady >= 3)) ? fy : G.down_fy;
                if (cx >= 0 && cy >= 0 && cx < G.fw && cy < G.fh) {
                    char cmd[64];
                    snprintf(cmd, sizeof cmd, "click %d %d %d", cx, cy, G.click_sh);
                    write_cmd(cmd);
                    G.have_anchor = 1;
                    G.anchor_fx = cx;
                    G.anchor_fy = cy;
                }
            }
        } else {
            if (!G.moved && adx < 4) {
                if (G.fw > 0 && G.fh > 0 && G.down_fx >= 0 && G.down_fy >= 0 &&
                    G.down_fx < G.fw && G.down_fy < G.fh) {
                    char cmd[64];
                    snprintf(cmd, sizeof cmd, "click %d %d", G.down_fx, G.down_fy);
                    write_cmd(cmd);
                }
            }
        }
        gtk_widget_queue_draw(G.da);
        return TRUE;
    }
    return FALSE;
}

static gboolean on_motion(GtkWidget *, GdkEventMotion *e, gpointer) {
    if (G.pie_on) {
        int vh = pie_var_hit_at((int)e->x, (int)e->y);
        int h = pie_pick_at((int)e->x, (int)e->y);
        if (h != G.pie_hit || vh != G.pie_vhit) {
            G.pie_hit = h;
            G.pie_vhit = vh;
            gtk_widget_queue_draw(G.da);
        }
        return TRUE;
    }
    int fx = (int)e->x - G.ox;
    int fy = (int)e->y - G.oy;
    G.cur_fx = fx;
    G.cur_fy = fy;
    int mode = 0, tool = 0, nclick = 0;
    read_tool_state(&mode, &tool, &nclick);

    if (G.mmb && (e->state & GDK_BUTTON2_MASK)) {
        int dx = fx - G.last_fx;
        int dy = fy - G.last_fy;
        if (dx || dy) {
            char cmd[64];
            snprintf(cmd, sizeof cmd, "pan %d %d", dx, dy);
            write_cmd(cmd);
            G.last_fx = fx;
            G.last_fy = fy;
        }
        gtk_widget_queue_draw(G.da);
        return TRUE;
    }
    if (G.dragging && (e->state & GDK_BUTTON1_MASK)) {
        int dx = fx - G.last_fx;
        int dy = fy - G.last_fy;
        if (abs(fx - G.down_fx) >= 3 || abs(fy - G.down_fy) >= 3) G.moved = 1;
        /* rubber-band is tool hover; otherwise orbit — kernel remaps 2D vs 3D */
        if (mode == 1 && (nclick > 0 || G.have_anchor)) {
            if (dx || dy) {
                G.pend_hover = 1;
                G.hover_fx = fx;
                G.hover_fy = fy;
                G.last_fx = fx;
                G.last_fy = fy;
            }
        } else if (dx || dy) {
            char cmd[64];
            snprintf(cmd, sizeof cmd, "orbit %d %d", dx, dy);
            write_cmd(cmd);
            G.last_fx = fx;
            G.last_fy = fy;
        }
        gtk_widget_queue_draw(G.da);
        return TRUE;
    }

    /* free move after first click — this is the 2-click rubber-band */
    if (mode == 1 && (nclick > 0 || G.have_anchor)) {
        if (abs(fx - G.last_hover_fx) >= 1 || abs(fy - G.last_hover_fy) >= 1) {
            G.pend_hover = 1;
            G.hover_fx = fx;
            G.hover_fy = fy;
            G.last_hover_fx = fx;
            G.last_hover_fy = fy;
        }
        gtk_widget_queue_draw(G.da);
        return TRUE;
    }
    gtk_widget_queue_draw(G.da);
    return FALSE;
}

static gboolean on_scroll(GtkWidget *, GdkEventScroll *e, gpointer) {
    if (e->direction == GDK_SCROLL_UP) write_cmd("zoom 1");
    else if (e->direction == GDK_SCROLL_DOWN) write_cmd("zoom -1");
    return TRUE;
}

static int hud_active(void) {
    return G.dimhud[0] || G.dim_kind != 0 || G.dimn > 0 || G.dim_sel;
}

static void hud_clear_typein(void) {
    G.dimn = 0;
    G.dimbuf[0] = 0;
    G.dim_sel = 0;
    G.dim_kind = 0;
    G.hud_idle = 0;
}

static void hud_seed_from_card(void) {
    DimCard card;
    memset(&card, 0, sizeof card);
    if (G.dim_kind != 0) return;
    if (!G.dimhud[0] || !parse_dimhud(G.dimhud, &card)) {
        G.dimn = 0;
        G.dimbuf[0] = 0;
        G.dim_sel = 0;
        return;
    }
    const char *v = "";
    int i;
    for (i = 0; i < card.n; i++) {
        if (card.f[i].active) {
            v = card.f[i].val;
            break;
        }
    }
    if (!v[0] || strcmp(v, "_") == 0) {
        G.dimn = 0;
        G.dimbuf[0] = 0;
        G.dim_sel = 0;
        return;
    }
    snprintf(G.dimbuf, sizeof G.dimbuf, "%s", v);
    G.dimn = (int)strlen(G.dimbuf);
    G.dim_sel = 1;
}

static int hud_digit_char(guint keyval) {
    if (keyval >= GDK_KEY_0 && keyval <= GDK_KEY_9)
        return (int)('0' + (keyval - GDK_KEY_0));
    if (keyval >= GDK_KEY_KP_0 && keyval <= GDK_KEY_KP_9)
        return (int)('0' + (keyval - GDK_KEY_KP_0));
    return -1;
}

static int hud_is_enter(guint keyval) {
    return keyval == GDK_KEY_Return || keyval == GDK_KEY_KP_Enter
        || keyval == GDK_KEY_ISO_Enter;
}

static void hud_commit(void) {
    char cmd[64];
    cmd[0] = 0;
    if (G.dim_kind == 1)
        snprintf(cmd, sizeof cmd, "plane_off %s", G.dimbuf[0] ? G.dimbuf : "20");
    else if (G.dim_kind == 2)
        snprintf(cmd, sizeof cmd, "plane_ang %s", G.dimbuf[0] ? G.dimbuf : "45");
    else if (G.dimbuf[0] == 'n' || G.dimbuf[0] == 'N')
        snprintf(cmd, sizeof cmd, "nsides %s", G.dimbuf + 1);
    else if (G.dimbuf[0] == 's' || G.dimbuf[0] == 'S')
        snprintf(cmd, sizeof cmd, "side %s", G.dimbuf + 1);
    else {
        /* dim = store the typed field only. hudok = place / rebuild. */
        if (G.dimn > 0 && G.dimbuf[0] && !G.dim_sel) {
            snprintf(cmd, sizeof cmd, "dim %s", G.dimbuf);
            write_cmd(cmd);
        }
        if (G.dimhud[0])
            write_cmd("hudok");
        hud_clear_typein();
        gtk_widget_queue_draw(G.da);
        return;
    }
    if (cmd[0]) write_cmd(cmd);
    hud_clear_typein();
    gtk_widget_queue_draw(G.da);
}

static gboolean hud_handle_key(GdkEventKey *e) {
    if (!hud_active()) return FALSE;
    guint kv = e->keyval;

    if (hud_is_enter(kv)) {
        hud_commit();
        return TRUE;
    }
    if (kv == GDK_KEY_Tab || kv == GDK_KEY_ISO_Left_Tab) {
        if (G.dimhud[0]) {
            if (G.dimn > 0 && !G.dim_sel && G.dimbuf[0]) {
                char cmd[64];
                snprintf(cmd, sizeof cmd, "dim %s", G.dimbuf);
                write_cmd(cmd);
            }
            G.dimn = 0;
            G.dimbuf[0] = 0;
            G.dim_sel = 0;
            write_cmd("htab");
            G.hud_idle = 0;
            gtk_widget_queue_draw(G.da);
            return TRUE;
        }
    }
    if (kv == GDK_KEY_BackSpace || kv == GDK_KEY_Delete || kv == GDK_KEY_KP_Delete) {
        if (G.dim_sel || G.dimn <= 0) {
            G.dimn = 0;
            G.dimbuf[0] = 0;
            G.dim_sel = 0;
        } else {
            G.dimbuf[--G.dimn] = 0;
        }
        G.hud_idle = 0;
        gtk_widget_queue_draw(G.da);
        return TRUE;
    }

    int dig = hud_digit_char(kv);
    if (dig >= 0) {
        if (G.dim_sel) {
            G.dimn = 0;
            G.dimbuf[0] = 0;
            G.dim_sel = 0;
        }
        if (G.dimn < 16) {
            G.dimbuf[G.dimn++] = (char)dig;
            G.dimbuf[G.dimn] = 0;
        }
        G.hud_idle = 0;
        gtk_widget_queue_draw(G.da);
        return TRUE;
    }
    if ((kv == GDK_KEY_period || kv == GDK_KEY_KP_Decimal) && G.dimn < 16) {
        if (G.dim_sel) {
            G.dimn = 0;
            G.dimbuf[0] = 0;
            G.dim_sel = 0;
        }
        if (G.dimn > 0 && !strchr(G.dimbuf, '.')) {
            G.dimbuf[G.dimn++] = '.';
            G.dimbuf[G.dimn] = 0;
            G.hud_idle = 0;
            gtk_widget_queue_draw(G.da);
        }
        return TRUE;
    }
    if ((kv == GDK_KEY_minus || kv == GDK_KEY_KP_Subtract) && (G.dimn == 0 || G.dim_sel)) {
        G.dimbuf[0] = '-';
        G.dimbuf[1] = 0;
        G.dimn = 1;
        G.dim_sel = 0;
        G.hud_idle = 0;
        gtk_widget_queue_draw(G.da);
        return TRUE;
    }
    if ((kv == GDK_KEY_n || kv == GDK_KEY_N || kv == GDK_KEY_s || kv == GDK_KEY_S)
        && (G.dimn == 0 || G.dim_sel) && G.dim_kind == 0) {
        G.dimbuf[0] = (kv == GDK_KEY_s || kv == GDK_KEY_S) ? 's' : 'n';
        G.dimbuf[1] = 0;
        G.dimn = 1;
        G.dim_sel = 0;
        gtk_widget_queue_draw(G.da);
        return TRUE;
    }
    return FALSE;
}

static gboolean on_key(GtkWidget *, GdkEventKey *e, gpointer) {
    if (e->keyval == GDK_KEY_F1) {
        on_help(NULL, NULL);
        return TRUE;
    }
    if (e->keyval == GDK_KEY_Escape) {
        write_cmd("cancel");
        G.have_anchor = 0;
        pie_close();
        hud_clear_typein();
        gtk_widget_queue_draw(G.da);
        return TRUE;
    }
    if (hud_handle_key(e))
        return TRUE;
    if (e->keyval == GDK_KEY_m || e->keyval == GDK_KEY_M) {
        write_cmd("mode");
        return TRUE;
    }
    if ((e->state & GDK_CONTROL_MASK) &&
        (e->keyval == GDK_KEY_s || e->keyval == GDK_KEY_S)) {
        on_save(NULL, NULL);
        return TRUE;
    }
    if ((e->state & GDK_CONTROL_MASK) &&
        (e->keyval == GDK_KEY_q || e->keyval == GDK_KEY_Q)) {
        on_quit_btn(NULL, NULL);
        return TRUE;
    }
    return FALSE;
}

static void load_tree(void);

static int load_frame(void) {
    int fd = open(path_meta, O_RDONLY);
    if (fd < 0) return -1;
    int32_t hdr[3];
    if (read(fd, hdr, 12) != 12) {
        close(fd);
        return -1;
    }
    close(fd);
    int w = hdr[0], h = hdr[1], pitch = hdr[2];
    if (w < 16 || h < 16 || pitch < w * 4) return -1;
    size_t sz = (size_t)pitch * (size_t)h;
    uint8_t *pix = (uint8_t *)malloc(sz);
    if (!pix) return -1;
    fd = open(path_frame, O_RDONLY);
    if (fd < 0) {
        free(pix);
        return -1;
    }
    size_t got = 0;
    while (got < sz) {
        ssize_t n = read(fd, pix + got, sz - got);
        if (n <= 0) break;
        got += (size_t)n;
    }
    close(fd);
    if (got < sz) {
        free(pix);
        return -1;
    }
    cairo_surface_t *surf = cairo_image_surface_create(CAIRO_FORMAT_ARGB32, w, h);
    if (cairo_surface_status(surf) != CAIRO_STATUS_SUCCESS) {
        cairo_surface_destroy(surf);
        free(pix);
        return -1;
    }
    unsigned char *dst = cairo_image_surface_get_data(surf);
    int stride = cairo_image_surface_get_stride(surf);
    int y;
    for (y = 0; y < h; y++) {
        uint8_t *srow = pix + (size_t)y * (size_t)pitch;
        uint32_t *drow = (uint32_t *)(dst + (size_t)y * (size_t)stride);
        int x;
        for (x = 0; x < w; x++) {
            uint8_t b = srow[x * 4 + 0];
            uint8_t g = srow[x * 4 + 1];
            uint8_t r = srow[x * 4 + 2];
            drow[x] = (0xFFu << 24) | ((uint32_t)r << 16) | ((uint32_t)g << 8) | b;
        }
    }
    cairo_surface_mark_dirty(surf);
    if (G.frame) cairo_surface_destroy(G.frame);
    free(G.pix);
    G.frame = surf;
    G.pix = pix;
    G.fw = w;
    G.fh = h;
    G.pitch = pitch;
    return 0;
}

static gboolean poll_tick(gpointer) {
    if (G.pend_hover) {
        char cmd[64];
        snprintf(cmd, sizeof cmd, "hover %d %d", G.hover_fx, G.hover_fy);
        write_cmd(cmd);
        G.pend_hover = 0;
    }
    int g = read_gen();
    if (g != G.last_gen && g >= 0) {
        if (load_frame() == 0) G.last_gen = g;
        gtk_widget_queue_draw(G.da);
    }
    char hud[256], st[256], dh[128];
    read_line_file(path_hud, hud, sizeof hud);
    read_line_file(path_status, st, sizeof st);
    read_line_file(path_dimhud, dh, sizeof dh);
    if (strcmp(dh, G.dimhud) != 0) {
        int opened = (!G.dimhud[0] && dh[0]);
        snprintf(G.dimhud, sizeof G.dimhud, "%s", dh);
        G.hud_idle = 0;
        if (opened || (dh[0] && G.dimn == 0 && !G.dim_sel && G.dim_kind == 0))
            hud_seed_from_card();
        if (!dh[0] && G.dim_kind == 0)
            hud_clear_typein();
        gtk_widget_queue_draw(G.da);
    }
    if (G.dimhud[0] || G.dim_kind != 0 || G.dimn > 0 || G.dim_sel) {
        if (G.da && G.win && gtk_window_is_active(GTK_WINDOW(G.win)))
            gtk_widget_grab_focus(G.da);
        G.hud_idle++;
        if ((G.hud_idle % 28) == 0) {
            G.hud_blink = !G.hud_blink;
            gtk_widget_queue_draw(G.da);
        }
        /* ~20 s idle — card should not sit open forever */
        if (G.hud_idle > 1250) {
            write_cmd("hudoff");
            hud_clear_typein();
            gtk_widget_queue_draw(G.da);
        }
    } else {
        G.hud_idle = 0;
    }
    if (strcmp(hud, G.hud_line) != 0) {
        snprintf(G.hud_line, sizeof G.hud_line, "%s", hud);
        if (G.hud_bar) gtk_label_set_text(GTK_LABEL(G.hud_bar), hud[0] ? hud : " ");
        gtk_widget_queue_draw(G.da);
    }
    if (strcmp(st, G.status_line) != 0) {
        snprintf(G.status_line, sizeof G.status_line, "%s", st);
        if (G.status) gtk_label_set_text(GTK_LABEL(G.status), st[0] ? st : "ready");
        if (!G.doc_name[0] && strncmp(st, "DOC ", 4) == 0) {
            const char *p = st + 4;
            int i = 0;
            while (p[i] && p[i] != ' ' && p[i] != '\n' && i < 63) {
                G.doc_name[i] = p[i];
                i++;
            }
            G.doc_name[i] = 0;
            if (strcmp(G.doc_name, "untitled") == 0) G.doc_name[0] = 0;
        }
    }
    int mode = 0, tool = 0, nclick = 0;
    read_tool_state(&mode, &tool, &nclick);
    if (nclick == 0 && !G.dragging) G.have_anchor = 0;
    if (G.mode_lbl) {
        gtk_label_set_text(GTK_LABEL(G.mode_lbl),
                           mode == 1 ? "  SKETCH MODE  " : "  3D MODEL MODE  ");
    }
    {
        char cb[80];
        read_line_file(path_cam, cb, sizeof cb);
        int ym = 0, pm = 0, zc = 100;
        if (cb[0] && sscanf(cb, "%d %d %d", &ym, &pm, &zc) >= 2) {
            double ny = ym * (M_PI / 180000.0);
            double np = pm * (M_PI / 180000.0);
            if (fabs(ny - G.cam_yaw) > 1e-5 || fabs(np - G.cam_pitch) > 1e-5 ||
                zc != G.cam_zoom_c) {
                G.cam_yaw = ny;
                G.cam_pitch = np;
                G.cam_zoom_c = zc;
                if (G.cube) gtk_widget_queue_draw(G.cube);
            }
        }
    }
    load_tree();
    load_hist();
    return TRUE;
}

/* ---------- chrome ---------- */

static GtkWidget *mk_btn(const char *label, const char *cmd) {
    GtkWidget *b = gtk_button_new_with_label(label);
    gtk_widget_set_name(b, "tool-btn");
    if (cmd) g_signal_connect(b, "clicked", G_CALLBACK(cb_cmd), (gpointer)cmd);
    return b;
}

/* One chip like Constrain ▾ — no separate action button + tiny "v". */
static GtkWidget *mk_split(const char *label, const char *cmd, const char **vlabs, const char **vcmds) {
    GtkWidget *mb = gtk_menu_button_new();
    char lab[48];
    snprintf(lab, sizeof lab, "%s ▾", label ? label : "");
    gtk_button_set_label(GTK_BUTTON(mb), lab);
    gtk_widget_set_name(mb, "tool-btn");
    GtkWidget *menu = gtk_menu_new();
    int i;
    if (vlabs) {
        for (i = 0; vlabs[i]; i++) {
            GtkWidget *it = gtk_menu_item_new_with_label(vlabs[i]);
            if (vcmds && vcmds[i])
                g_signal_connect(it, "activate", G_CALLBACK(cb_menu_cmd), (gpointer)vcmds[i]);
            gtk_menu_shell_append(GTK_MENU_SHELL(menu), it);
        }
    }
    if ((!vlabs || !vlabs[0]) && cmd) {
        GtkWidget *it = gtk_menu_item_new_with_label(label ? label : cmd);
        g_signal_connect(it, "activate", G_CALLBACK(cb_menu_cmd), (gpointer)cmd);
        gtk_menu_shell_append(GTK_MENU_SHELL(menu), it);
    }
    gtk_widget_show_all(menu);
    gtk_menu_button_set_popup(GTK_MENU_BUTTON(mb), menu);
    return mb;
}

static GtkWidget *tab_box(void) {
    GtkWidget *b = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_set_margin_start(b, 10);
    gtk_widget_set_margin_end(b, 10);
    gtk_widget_set_margin_top(b, 8);
    gtk_widget_set_margin_bottom(b, 8);
    return b;
}

static void add_tab(GtkNotebook *nb, const char *title, GtkWidget *body) {
    GtkWidget *scr = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scr),
                                   GTK_POLICY_AUTOMATIC, GTK_POLICY_NEVER);
    gtk_scrolled_window_set_propagate_natural_height(GTK_SCROLLED_WINDOW(scr), TRUE);
    gtk_container_add(GTK_CONTAINER(scr), body);
    gtk_notebook_append_page(nb, scr, gtk_label_new(title));
}

static void size_window_to_monitor(GtkWindow *w) {
    int ww = 1100, hh = 720;
    GdkScreen *sc = gtk_window_get_screen(w);
    if (sc) {
        gint px = 0, py = 0;
        GdkDisplay *disp = gdk_screen_get_display(sc);
        GdkSeat *seat = gdk_display_get_default_seat(disp);
        GdkDevice *ptr = seat ? gdk_seat_get_pointer(seat) : NULL;
        int mon = 0;
        if (ptr) {
            gdk_device_get_position(ptr, NULL, &px, &py);
            mon = gdk_screen_get_monitor_at_point(sc, px, py);
        }
        GdkRectangle wa;
        gdk_screen_get_monitor_workarea(sc, mon, &wa);
        ww = wa.width * 85 / 100;
        hh = wa.height * 85 / 100;
        if (ww > 1200) ww = 1200;
        if (hh > 780) hh = 780;
        if (ww > wa.width - 32) ww = wa.width - 32;
        if (hh > wa.height - 32) hh = wa.height - 32;
        if (ww < 640) ww = wa.width > 640 ? 640 : wa.width;
        if (hh < 480) hh = wa.height > 480 ? 480 : wa.height;
    }
    gtk_window_set_default_size(w, ww, hh);
}

static void on_ribbon_page(GtkNotebook *, GtkWidget *, guint page, gpointer) {
    if ((int)page == G.page_solid) write_cmd("profiles");
}

static void on_import(GtkWidget *, gpointer) {
    GtkWidget *dlg = gtk_file_chooser_dialog_new(
        "Import DXF", GTK_WINDOW(G.win), GTK_FILE_CHOOSER_ACTION_OPEN,
        "Cancel", GTK_RESPONSE_CANCEL, "Open", GTK_RESPONSE_ACCEPT, NULL);
    GtkFileFilter *ff = gtk_file_filter_new();
    gtk_file_filter_set_name(ff, "DXF");
    gtk_file_filter_add_pattern(ff, "*.dxf");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(dlg), ff);
    if (gtk_dialog_run(GTK_DIALOG(dlg)) == GTK_RESPONSE_ACCEPT) {
        char *fn = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(dlg));
        if (fn) {
            FILE *f = fopen(path_path, "w");
            if (f) {
                fputs(fn, f);
                fputc('\n', f);
                fclose(f);
                write_cmd("import");
            }
            g_free(fn);
        }
    }
    gtk_widget_destroy(dlg);
}

/* ---------- view cube (host chrome; kernel owns camera) ---------- */

typedef struct { double x, y, z; } CubeV;

static void cube_basis(double yaw, double pitch, CubeV *r, CubeV *u, CubeV *c) {
    double cy = cos(yaw), sy = sin(yaw), cp = cos(pitch), sp = sin(pitch);
    c->x = cp * sy;
    c->y = cp * cy;
    c->z = sp;
    r->x = -c->y;
    r->y = c->x;
    r->z = 0;
    double rl = hypot(r->x, r->y);
    if (rl < 1e-9) {
        r->x = 1;
        r->y = 0;
        rl = 1;
    }
    r->x /= rl;
    r->y /= rl;
    u->x = c->y * r->z - c->z * r->y;
    u->y = c->z * r->x - c->x * r->z;
    u->z = c->x * r->y - c->y * r->x;
}

static void cube_proj(CubeV p, CubeV r, CubeV u, double *sx, double *sy) {
    *sx = p.x * r.x + p.y * r.y + p.z * r.z;
    *sy = p.x * u.x + p.y * u.y + p.z * u.z;
}

typedef struct {
    CubeV n;
    CubeV v[4];
    const char *lab;
    const char *cmd;
    double rgb[3];
    double depth;
    int vis;
} CubeFace;

static void cube_faces(CubeFace *f) {
    /* +X right, -X left, +Y front, -Y back, +Z top, -Z bottom — matches CAD.View */
    static const CubeFace src[6] = {
        {{1, 0, 0}, {{1, -1, -1}, {1, 1, -1}, {1, 1, 1}, {1, -1, 1}}, "RIGHT", "view4", {0.28, 0.62, 0.42}, 0, 0},
        {{-1, 0, 0}, {{-1, 1, -1}, {-1, -1, -1}, {-1, -1, 1}, {-1, 1, 1}}, "LEFT", "view5", {0.28, 0.62, 0.42}, 0, 0},
        {{0, 1, 0}, {{-1, 1, -1}, {1, 1, -1}, {1, 1, 1}, {-1, 1, 1}}, "FRONT", "view2", {0.78, 0.38, 0.30}, 0, 0},
        {{0, -1, 0}, {{1, -1, -1}, {-1, -1, -1}, {-1, -1, 1}, {1, -1, 1}}, "BACK", "view6", {0.78, 0.38, 0.30}, 0, 0},
        {{0, 0, 1}, {{-1, -1, 1}, {1, -1, 1}, {1, 1, 1}, {-1, 1, 1}}, "TOP", "view1", {0.30, 0.50, 0.78}, 0, 0},
        {{0, 0, -1}, {{-1, 1, -1}, {1, 1, -1}, {1, -1, -1}, {-1, -1, -1}}, "BOTTOM", "view7", {0.30, 0.50, 0.78}, 0, 0},
    };
    memcpy(f, src, sizeof src);
}

static int cube_in_quad(double px, double py, double *xs, double *ys) {
    int i, c = 0;
    for (i = 0; i < 4; i++) {
        int j = (i + 1) & 3;
        double y0 = ys[i], y1 = ys[j];
        if ((y0 > py) == (y1 > py)) continue;
        double t = (py - y0) / (y1 - y0);
        if (px < xs[i] + t * (xs[j] - xs[i])) c = !c;
    }
    return c;
}

static void cube_layout(CubeFace *f, CubeV r, CubeV u, CubeV c, double cx, double cy, double sc) {
    int i, k;
    cube_faces(f);
    for (i = 0; i < 6; i++) {
        double nd = f[i].n.x * c.x + f[i].n.y * c.y + f[i].n.z * c.z;
        f[i].vis = nd > 0.04;
        CubeV mid = {0, 0, 0};
        for (k = 0; k < 4; k++) {
            mid.x += f[i].v[k].x;
            mid.y += f[i].v[k].y;
            mid.z += f[i].v[k].z;
        }
        mid.x *= 0.25;
        mid.y *= 0.25;
        mid.z *= 0.25;
        f[i].depth = mid.x * c.x + mid.y * c.y + mid.z * c.z;
        (void)r;
        (void)u;
        (void)cx;
        (void)cy;
        (void)sc;
    }
}

static void cube_face_xy(const CubeFace *f, CubeV r, CubeV u, double cx, double cy, double sc,
                         double *xs, double *ys) {
    int k;
    for (k = 0; k < 4; k++) {
        double sx, sy;
        cube_proj(f->v[k], r, u, &sx, &sy);
        xs[k] = cx + sx * sc;
        ys[k] = cy - sy * sc;
    }
}

static int cube_hit_face(double px, double py) {
    CubeV r, u, c;
    CubeFace f[6];
    cube_basis(G.cam_yaw, G.cam_pitch, &r, &u, &c);
    cube_layout(f, r, u, c, 0, 0, 0);
    int best = -1;
    double bd = -1e9;
    int i;
    for (i = 0; i < 6; i++) {
        if (!f[i].vis) continue;
        double xs[4], ys[4];
        cube_face_xy(&f[i], r, u, 68.0, 64.0, 44.0, xs, ys);
        if (cube_in_quad(px, py, xs, ys) && f[i].depth > bd) {
            bd = f[i].depth;
            best = i;
        }
    }
    return best;
}

static gboolean on_cube_draw(GtkWidget *w, cairo_t *cr, gpointer) {
    GtkAllocation al;
    gtk_widget_get_allocation(w, &al);
    double cx = al.width * 0.5;
    double cy = al.height * 0.5 - 6;
    double sc = 44.0;

    cairo_set_source_rgba(cr, 0.09, 0.10, 0.13, 0.55);
    cairo_arc(cr, cx, cy, 62, 0, 2 * M_PI);
    cairo_fill(cr);

    CubeV r, u, c;
    CubeFace f[6];
    cube_basis(G.cam_yaw, G.cam_pitch, &r, &u, &c);
    cube_layout(f, r, u, c, cx, cy, sc);

    int order[6] = {0, 1, 2, 3, 4, 5};
    int a, b;
    for (a = 0; a < 5; a++) {
        for (b = a + 1; b < 6; b++) {
            if (f[order[a]].depth > f[order[b]].depth) {
                int t = order[a];
                order[a] = order[b];
                order[b] = t;
            }
        }
    }

    int i;
    for (i = 0; i < 6; i++) {
        CubeFace *fa = &f[order[i]];
        if (!fa->vis) continue;
        double xs[4], ys[4];
        cube_face_xy(fa, r, u, cx, cy, sc, xs, ys);
        cairo_move_to(cr, xs[0], ys[0]);
        cairo_line_to(cr, xs[1], ys[1]);
        cairo_line_to(cr, xs[2], ys[2]);
        cairo_line_to(cr, xs[3], ys[3]);
        cairo_close_path(cr);
        double br = 1.0;
        if (G.cube_hover == order[i]) br = 1.18;
        cairo_set_source_rgb(cr, fa->rgb[0] * br, fa->rgb[1] * br, fa->rgb[2] * br);
        cairo_fill_preserve(cr);
        cairo_set_source_rgb(cr, 0.92, 0.94, 0.97);
        cairo_set_line_width(cr, 1.4);
        cairo_stroke(cr);
        double mx = 0, my = 0;
        int k;
        for (k = 0; k < 4; k++) {
            mx += xs[k];
            my += ys[k];
        }
        mx *= 0.25;
        my *= 0.25;
        cairo_select_font_face(cr, "sans-serif", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_BOLD);
        cairo_set_font_size(cr, 10);
        cairo_text_extents_t te;
        cairo_text_extents(cr, fa->lab, &te);
        cairo_set_source_rgb(cr, 0.97, 0.98, 1.0);
        cairo_move_to(cr, mx - te.width * 0.5, my + te.height * 0.35);
        cairo_show_text(cr, fa->lab);
    }

    /* ISO chip */
    cairo_set_source_rgb(cr, 0.18, 0.20, 0.26);
    cairo_rectangle(cr, cx - 16, al.height - 18, 32, 14);
    cairo_fill(cr);
    cairo_set_source_rgb(cr, 0.85, 0.90, 1.0);
    cairo_set_font_size(cr, 9);
    cairo_text_extents_t te;
    cairo_text_extents(cr, "ISO", &te);
    cairo_move_to(cr, cx - te.width * 0.5, al.height - 7);
    cairo_show_text(cr, "ISO");
    return FALSE;
}

static gboolean on_cube_button(GtkWidget *, GdkEventButton *e, gpointer) {
    if (e->type == GDK_BUTTON_PRESS && e->button == 3) {
        G.cube_move = 1;
        G.cube_lx = (int)e->x_root;
        G.cube_ly = (int)e->y_root;
        return TRUE;
    }
    if (e->type == GDK_BUTTON_RELEASE && e->button == 3) {
        G.cube_move = 0;
        return TRUE;
    }
    if (e->type == GDK_BUTTON_PRESS && e->button == 1) {
        G.cube_drag = 1;
        G.cube_moved = 0;
        G.cube_lx = (int)e->x;
        G.cube_ly = (int)e->y;
        return TRUE;
    }
    if (e->type == GDK_BUTTON_RELEASE && e->button == 1) {
        G.cube_drag = 0;
        if (!G.cube_moved) {
            GtkAllocation al;
            gtk_widget_get_allocation(G.cube, &al);
            if (e->y > al.height - 20) {
                write_cmd("iso");
            } else {
                int hit = cube_hit_face(e->x, e->y);
                CubeFace f[6];
                cube_faces(f);
                if (hit >= 0) write_cmd(f[hit].cmd);
                else write_cmd("iso");
            }
        }
        return TRUE;
    }
    return FALSE;
}

static gboolean on_cube_motion(GtkWidget *, GdkEventMotion *e, gpointer) {
    if (G.cube_move && (e->state & GDK_BUTTON3_MASK) && G.cube_host) {
        int dx = (int)e->x_root - G.cube_lx;
        int dy = (int)e->y_root - G.cube_ly;
        G.cube_lx = (int)e->x_root;
        G.cube_ly = (int)e->y_root;
        G.cube_me -= dx;
        G.cube_mt += dy;
        if (G.cube_me < 0) G.cube_me = 0;
        if (G.cube_mt < 0) G.cube_mt = 0;
        if (G.cube_me > 800) G.cube_me = 800;
        if (G.cube_mt > 600) G.cube_mt = 600;
        gtk_widget_set_margin_end(G.cube_host, G.cube_me);
        gtk_widget_set_margin_top(G.cube_host, G.cube_mt);
        return TRUE;
    }
    if (G.cube_drag && (e->state & GDK_BUTTON1_MASK)) {
        int dx = (int)e->x - G.cube_lx;
        int dy = (int)e->y - G.cube_ly;
        if (abs(dx) >= 2 || abs(dy) >= 2) G.cube_moved = 1;
        if (dx || dy) {
            char cmd[64];
            snprintf(cmd, sizeof cmd, "orbit %d %d", dx, dy);
            write_cmd(cmd);
            G.cube_lx = (int)e->x;
            G.cube_ly = (int)e->y;
        }
        return TRUE;
    }
    int h = cube_hit_face(e->x, e->y);
    if (h != G.cube_hover) {
        G.cube_hover = h;
        if (G.cube) gtk_widget_queue_draw(G.cube);
    }
    return TRUE;
}

static gboolean on_cube_scroll(GtkWidget *, GdkEventScroll *e, gpointer) {
    if (e->direction == GDK_SCROLL_UP) write_cmd("zoom 1");
    else if (e->direction == GDK_SCROLL_DOWN) write_cmd("zoom -1");
    return TRUE;
}

static void on_tree_row(GtkTreeView *, GtkTreePath *path, GtkTreeViewColumn *, gpointer);
static void tree_send(GtkTreeView *, GtkTreePath *path, int edit);

static gboolean collect_open(GtkTreeModel *m, GtkTreePath *path, GtkTreeIter *it, gpointer) {
    if (!gtk_tree_view_row_expanded(GTK_TREE_VIEW(G.treev), path)) return FALSE;
    gchar *cmd = NULL;
    gtk_tree_model_get(m, it, 1, &cmd, -1);
    if (cmd && cmd[0]) {
        char k = 0;
        int id = 0;
        if (sscanf(cmd, "tree %c %d", &k, &id) == 2) {
            char tmp[16];
            snprintf(tmp, sizeof tmp, "%c%d ", k, id);
            size_t used = strlen(G.tree_open);
            if (used + strlen(tmp) < sizeof G.tree_open)
                memcpy(G.tree_open + used, tmp, strlen(tmp) + 1);
        }
        g_free(cmd);
    }
    return FALSE;
}

static gboolean restore_open(GtkTreeModel *m, GtkTreePath *path, GtkTreeIter *it, gpointer) {
    gchar *cmd = NULL;
    gtk_tree_model_get(m, it, 1, &cmd, -1);
    if (cmd && cmd[0]) {
        char k = 0;
        int id = 0;
        if (sscanf(cmd, "tree %c %d", &k, &id) == 2) {
            char tmp[16];
            snprintf(tmp, sizeof tmp, "%c%d ", k, id);
            if (strstr(G.tree_open, tmp))
                gtk_tree_view_expand_to_path(GTK_TREE_VIEW(G.treev), path);
        }
        g_free(cmd);
    }
    return FALSE;
}

static void load_tree(void) {
    char raw[4096];
    raw[0] = 0;
    FILE *f = fopen(path_tree, "r");
    if (f) {
        size_t n = fread(raw, 1, sizeof raw - 1, f);
        raw[n] = 0;
        fclose(f);
    }
    if (strcmp(raw, G.tree_cache) == 0) return;
    snprintf(G.tree_cache, sizeof G.tree_cache, "%s", raw);
    if (!G.tstore) return;
    G.tree_open[0] = 0;
    if (G.tree_seen && G.treev)
        gtk_tree_model_foreach(GTK_TREE_MODEL(G.tstore), collect_open, NULL);
    gtk_tree_store_clear(G.tstore);
    GtkTreeIter stack[4];
    int have[4] = {0, 0, 0, 0};
    char *p = raw;
    while (*p) {
        char *nl = strchr(p, '\n');
        if (nl) *nl = 0;
        int depth = 0, id = 0;
        char kind = 0, mark = 0;
        char lab[80];
        lab[0] = 0;
        int n = sscanf(p, "%d %c %d %c %79[^\n]", &depth, &kind, &id, &mark, lab);
        if (n >= 4) {
            if (kind == 'P') {
                if (G.navhdr) {
                    char hdr[96];
                    gtk_label_set_text(GTK_LABEL(G.navhdr), "  WORK TREE");
                }
            } else {
                if (depth < 0) depth = 0;
                if (depth > 3) depth = 3;
                char cmd[32], shown[96];
                snprintf(cmd, sizeof cmd, "tree %c %d", kind, id);
                snprintf(shown, sizeof shown, "%s%s", mark == '*' ? "● " : "", lab);
                GtkTreeIter it;
                if (depth == 0 || !have[depth - 1])
                    gtk_tree_store_append(G.tstore, &it, NULL);
                else
                    gtk_tree_store_append(G.tstore, &it, &stack[depth - 1]);
                gtk_tree_store_set(G.tstore, &it, 0, shown, 1, cmd, -1);
                stack[depth] = it;
                have[depth] = 1;
                for (int d = depth + 1; d < 4; d++) have[d] = 0;
            }
        }
        if (!nl) break;
        p = nl + 1;
    }
    if (!G.tree_seen) {
        gtk_tree_view_expand_all(GTK_TREE_VIEW(G.treev));
        G.tree_seen = 1;
    } else {
        gtk_tree_model_foreach(GTK_TREE_MODEL(G.tstore), restore_open, NULL);
    }
}

static gboolean on_tree_btn(GtkWidget *w, GdkEventButton *e, gpointer) {
    if (e->type == GDK_BUTTON_PRESS && e->button == 3) {
        GtkTreePath *path = NULL;
        if (gtk_tree_view_get_path_at_pos(GTK_TREE_VIEW(w), (int)e->x, (int)e->y,
                                          &path, NULL, NULL, NULL)) {
            GtkTreeIter it;
            gchar *cmd = NULL;
            if (gtk_tree_model_get_iter(GTK_TREE_MODEL(G.tstore), &it, path)) {
                gtk_tree_model_get(GTK_TREE_MODEL(G.tstore), &it, 1, &cmd, -1);
                if (cmd) {
                    snprintf(G.tree_edit_cmd, sizeof G.tree_edit_cmd, "%s", cmd);
                    g_free(cmd);
                }
            }
            gtk_tree_path_free(path);
        }
        popup_tree_menu(e);
        return TRUE;
    }
    if (e->type == GDK_BUTTON_RELEASE && e->button == 1) {
        GtkTreePath *path = NULL;
        GtkTreeViewColumn *col = NULL;
        if (gtk_tree_view_get_path_at_pos(GTK_TREE_VIEW(w), (int)e->x, (int)e->y,
                                          &path, &col, NULL, NULL)) {
            GdkRectangle area;
            gtk_tree_view_get_cell_area(GTK_TREE_VIEW(w), path, col, &area);
            if ((int)e->x >= area.x)
                tree_send(GTK_TREE_VIEW(w), path, 0);
            gtk_tree_path_free(path);
        }
    }
    return FALSE;
}

static void tree_send(GtkTreeView *, GtkTreePath *path, int edit) {
    GtkTreeIter it;
    gchar *cmd = NULL;
    if (!G.tstore) return;
    if (!gtk_tree_model_get_iter(GTK_TREE_MODEL(G.tstore), &it, path)) return;
    gtk_tree_model_get(GTK_TREE_MODEL(G.tstore), &it, 1, &cmd, -1);
    if (cmd && cmd[0]) {
        if (edit) {
            write_cmd(cmd);
        } else {
            char k = 0;
            int id = 0;
            if (sscanf(cmd, "tree %c %d", &k, &id) == 2) {
                char out[32];
                snprintf(out, sizeof out, "tsel %c %d", k, id);
                write_cmd(out);
            } else {
                write_cmd(cmd);
            }
        }
    }
    g_free(cmd);
}

static void on_tree_row(GtkTreeView *, GtkTreePath *path, GtkTreeViewColumn *, gpointer) {
    tree_send(NULL, path, 1);
}

static void apply_css(void) {
    GtkCssProvider *p = gtk_css_provider_new();
    const char *css =
        "window, box, notebook, headerbar { background:#14171e; color:#c5cbd8; }"
        "button { background:#2a3142; color:#e1ebfa; border:1px solid #1a1f2a;"
        "  padding:6px 10px; min-height:28px; }"
        "button:hover { background:#3a4560; }"
        "notebook tab { padding:6px 12px; background:#1c202a; color:#9aa4b8; }"
        "notebook tab:checked { background:#2a3142; color:#00c4c6; }"
        "label { color:#c5cbd8; }"
        /* File / Import / Guest / Constrain popups: light pane, dark ink */
        "menu, .menu { background-color:#e8ecf4; background-image:none;"
        "  color:#1a2030; border:1px solid #8a93a8; }"
        "menu menuitem, .menu menuitem { background-color:#e8ecf4;"
        "  background-image:none; color:#1a2030; padding:6px 14px; }"
        "menu menuitem label, menu menuitem *, .menu menuitem label, .menu menuitem * {"
        "  color:#1a2030; }"
        "menu menuitem:hover, menu menuitem:prelight,"
        "  .menu menuitem:hover, .menu menuitem:prelight {"
        "  background-color:#00c4c6; background-image:none; color:#061014; }"
        "menu menuitem:hover label, menu menuitem:hover *,"
        "  menu menuitem:prelight label, menu menuitem:prelight * {"
        "  color:#061014; }"
        "menu menuitem:disabled, menu menuitem:disabled label,"
        "  menu menuitem:insensitive, menu menuitem:insensitive label {"
        "  color:#6a7388; }"
        "menu separator, .menu separator { background-color:#b4bccb; min-height:1px; }"
        "dialog, messagedialog { background-color:#e8ecf4; color:#1a2030; }"
        "dialog box, messagedialog box, dialog label, messagedialog label {"
        "  background-color:#e8ecf4; color:#1a2030; }"
        "entry { background-color:#ffffff; color:#1a2030; border:1px solid #8a93a8;"
        "  padding:4px 8px; }"
        "filechooser, filechooserwidget { background-color:#e8ecf4; color:#1a2030; }"
        "filechooser treeview, filechooser list, filechooser label {"
        "  background-color:#ffffff; color:#1a2030; }"
        "#modepill { background:#12383a; color:#00c4c6; padding:4px 10px; font-weight:bold; }"
        "#hudbar { color:#d8e4f4; font-family:monospace; font-size:11px; }"
        "#statbar { background:#10141b; color:#9aa4b8; padding:4px 8px; }"
        "treeview { background:#161a22; color:#e8eef8; font-size:12px;"
        "  font-family:monospace; }"
        "treeview:selected { background:#1a5c5e; color:#ffffff; }"
        "#navhdr { background:#12161e; color:#8fdfe0; padding:6px 8px; font-weight:bold; }"
        "#foldbar { padding:2px 8px; min-height:22px; }"
        "#tldock { background:#0e1218; padding:4px 8px; }"
        "#tlchip { background:#2a3142; color:#c5cbd8; padding:3px 8px; min-height:22px; font-size:11px; }"
        "#tlnow { background:#1a5c5e; color:#ffffff; padding:3px 8px; min-height:22px; font-size:11px; }"
        "menubar { background:#0e1218; padding:0 4px; }"
        "menubar > menuitem { padding:4px 12px; color:#e8eef8; }"
        "menubar > menuitem:hover, menubar > menuitem:prelight { background:#1a5c5e; }"
        "#topbar { background:#0e1218; }"
        "#sess-btn { min-height:22px; padding:2px 12px; background:#0e1218;"
        "  color:#8fdfe0; border:none; }"
        "#sess-btn:hover { background:#1a5c5e; color:#ffffff; }";
    gtk_css_provider_load_from_data(p, css, -1, NULL);
    gtk_style_context_add_provider_for_screen(
        gdk_screen_get_default(), GTK_STYLE_PROVIDER(p),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(p);
}

int main(int argc, char **argv) {
    const char *dir = (argc > 1) ? argv[1] : getenv("CAD_APP_STATE");
    if (!dir || !dir[0]) dir = "/tmp/cad_app";
    paths_init(dir);
    memset(&G, 0, sizeof G);
    G.last_gen = -1;
    G.last_hover_fx = -9999;
    G.last_hover_fy = -9999;

    gtk_init(&argc, &argv);
    signal(SIGTERM, on_term);
    signal(SIGINT, on_term);
    apply_css();

    G.win = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(G.win), "AILang CAD");
    size_window_to_monitor(GTK_WINDOW(G.win));
    g_signal_connect(G.win, "delete-event", G_CALLBACK(on_delete), NULL);
    g_signal_connect(G.win, "destroy", G_CALLBACK(gtk_main_quit), NULL);
    g_signal_connect(G.win, "key-press-event", G_CALLBACK(on_key), NULL);

    GtkWidget *root = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_container_add(GTK_CONTAINER(G.win), root);

    GtkWidget *topbar = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_set_name(topbar, "topbar");
    GtkWidget *mbar = gtk_menu_bar_new();
    {
        GtkWidget *file = gtk_menu_item_new_with_label("File");
        GtkWidget *fm = gtk_menu_new();
        GtkWidget *it;
        it = gtk_menu_item_new_with_label("New");
        g_signal_connect(it, "activate", G_CALLBACK(on_newdoc), NULL);
        gtk_menu_shell_append(GTK_MENU_SHELL(fm), it);
        it = gtk_menu_item_new_with_label("Open…");
        g_signal_connect(it, "activate", G_CALLBACK(on_load), NULL);
        gtk_menu_shell_append(GTK_MENU_SHELL(fm), it);
        it = gtk_menu_item_new_with_label("Save");
        g_signal_connect(it, "activate", G_CALLBACK(on_save), NULL);
        gtk_menu_shell_append(GTK_MENU_SHELL(fm), it);
        it = gtk_menu_item_new_with_label("Save As…");
        g_signal_connect(it, "activate", G_CALLBACK(on_save_as), NULL);
        gtk_menu_shell_append(GTK_MENU_SHELL(fm), it);
        it = gtk_menu_item_new_with_label("Close");
        g_signal_connect(it, "activate", G_CALLBACK(on_close_doc), NULL);
        gtk_menu_shell_append(GTK_MENU_SHELL(fm), it);
        it = gtk_menu_item_new_with_label("Delete…");
        g_signal_connect(it, "activate", G_CALLBACK(on_delete_part), NULL);
        gtk_menu_shell_append(GTK_MENU_SHELL(fm), it);
        gtk_menu_shell_append(GTK_MENU_SHELL(fm), gtk_separator_menu_item_new());
        it = gtk_menu_item_new_with_label("Name Part…");
        g_signal_connect(it, "activate", G_CALLBACK(on_name_part), NULL);
        gtk_menu_shell_append(GTK_MENU_SHELL(fm), it);
        it = gtk_menu_item_new_with_label("List Docs");
        g_signal_connect(it, "activate", G_CALLBACK(on_load), NULL);
        gtk_menu_shell_append(GTK_MENU_SHELL(fm), it);
        gtk_menu_shell_append(GTK_MENU_SHELL(fm), gtk_separator_menu_item_new());
        it = gtk_menu_item_new_with_label("Quit");
        g_signal_connect(it, "activate", G_CALLBACK(on_quit_btn), NULL);
        gtk_menu_shell_append(GTK_MENU_SHELL(fm), it);
        gtk_menu_item_set_submenu(GTK_MENU_ITEM(file), fm);
        gtk_menu_shell_append(GTK_MENU_SHELL(mbar), file);

        GtkWidget *xfer = gtk_menu_item_new_with_label("Import / Export");
        GtkWidget *xm = gtk_menu_new();
        it = gtk_menu_item_new_with_label("Import DXF…");
        g_signal_connect(it, "activate", G_CALLBACK(on_import), NULL);
        gtk_menu_shell_append(GTK_MENU_SHELL(xm), it);
        gtk_menu_shell_append(GTK_MENU_SHELL(xm), gtk_separator_menu_item_new());
        it = gtk_menu_item_new_with_label("Export STEP");
        g_signal_connect(it, "activate", G_CALLBACK(on_export_step), NULL);
        gtk_menu_shell_append(GTK_MENU_SHELL(xm), it);
        it = gtk_menu_item_new_with_label("Export DXF");
        g_signal_connect(it, "activate", G_CALLBACK(on_export_dxf), NULL);
        gtk_menu_shell_append(GTK_MENU_SHELL(xm), it);
        gtk_menu_item_set_submenu(GTK_MENU_ITEM(xfer), xm);
        gtk_menu_shell_append(GTK_MENU_SHELL(mbar), xfer);
    }
    gtk_box_pack_start(GTK_BOX(topbar), mbar, TRUE, TRUE, 0);
    {
        G.sess_btn = gtk_menu_button_new();
        gtk_widget_set_name(G.sess_btn, "sess-btn");
        gtk_button_set_relief(GTK_BUTTON(G.sess_btn), GTK_RELIEF_NONE);
        gtk_widget_set_tooltip_text(G.sess_btn, "Session: Guest or logged-in (pgcrypto / capabilities next)");
        GtkWidget *sm = gtk_menu_new();
        GtkWidget *g = gtk_menu_item_new_with_label("Continue as Guest");
        g_signal_connect(g, "activate", G_CALLBACK(on_guest), NULL);
        gtk_menu_shell_append(GTK_MENU_SHELL(sm), g);
        GtkWidget *li = gtk_menu_item_new_with_label("Log in…");
        g_signal_connect(li, "activate", G_CALLBACK(on_login), NULL);
        gtk_menu_shell_append(GTK_MENU_SHELL(sm), li);
        gtk_widget_show_all(sm);
        gtk_menu_button_set_popup(GTK_MENU_BUTTON(G.sess_btn), sm);
        session_set_guest();
        gtk_box_pack_end(GTK_BOX(topbar), G.sess_btn, FALSE, FALSE, 4);
    }
    gtk_box_pack_start(GTK_BOX(root), topbar, FALSE, FALSE, 0);

    GtkWidget *hdr = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_set_margin_start(hdr, 8);
    gtk_widget_set_margin_top(hdr, 4);
    gtk_widget_set_margin_bottom(hdr, 4);
    G.mode_lbl = gtk_label_new("  SKETCH MODE  ");
    gtk_widget_set_name(G.mode_lbl, "modepill");
    gtk_box_pack_start(GTK_BOX(hdr), G.mode_lbl, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(hdr), gtk_label_new("AILang CAD"), FALSE, FALSE, 8);
    {
        GtkWidget *hb = gtk_button_new_with_label("Help");
        gtk_widget_set_name(hb, "tool-btn");
        gtk_widget_set_tooltip_text(hb, "How to use the UI  (F1)");
        g_signal_connect(hb, "clicked", G_CALLBACK(on_help), NULL);
        gtk_box_pack_start(GTK_BOX(hdr), hb, FALSE, FALSE, 0);
    }
    G.hud_bar = gtk_label_new(" ");
    gtk_widget_set_name(G.hud_bar, "hudbar");
    gtk_label_set_xalign(GTK_LABEL(G.hud_bar), 1.0);
    gtk_label_set_ellipsize(GTK_LABEL(G.hud_bar), PANGO_ELLIPSIZE_START);
    gtk_box_pack_end(GTK_BOX(hdr), G.hud_bar, TRUE, TRUE, 8);
    gtk_box_pack_start(GTK_BOX(root), hdr, FALSE, FALSE, 0);

    G.ribbon = GTK_NOTEBOOK(gtk_notebook_new());
    gtk_box_pack_start(GTK_BOX(root), GTK_WIDGET(G.ribbon), FALSE, FALSE, 0);

    /* SKETCH */
    GtkWidget *sk = tab_box();
    gtk_box_pack_start(GTK_BOX(sk), mk_btn("Line", "tool_line"), FALSE, FALSE, 0);
    {
        static const char *rl[] = {"2-Point Rect", "Center Rect", "3-Point Rect", NULL};
        static const char *rc[] = {"tool_rect", "tool_rectc", "tool_rect3", NULL};
        gtk_box_pack_start(GTK_BOX(sk), mk_split("Rect", "tool_rect", rl, rc), FALSE, FALSE, 0);
    }
    {
        static const char *cl[] = {"Center Radius", "2-Point Circle", "3-Point Circle", NULL};
        static const char *cc[] = {"tool_circ", "tool_circ2", "tool_circ3", NULL};
        gtk_box_pack_start(GTK_BOX(sk), mk_split("Circle", "tool_circ", cl, cc), FALSE, FALSE, 0);
    }
    {
        static const char *al[] = {"3-Point Arc", "2-Point Arc", "Center Arc", NULL};
        static const char *ac[] = {"tool_arc3", "tool_arc2", "tool_arc", NULL};
        gtk_box_pack_start(GTK_BOX(sk), mk_split("Arc", "tool_arc3", al, ac), FALSE, FALSE, 0);
    }
    {
        static const char *pl[] = {
            "Center", "2-Point", "3-Point",
            "Triangle", "Square", "Pentagon", "Hexagon", "Octagon",
            NULL
        };
        static const char *pc[] = {
            "pmode 0", "pmode 1", "pmode 2",
            "tool_poly3", "tool_poly4", "tool_poly5", "tool_poly6", "tool_poly8",
            NULL
        };
        gtk_box_pack_start(GTK_BOX(sk), mk_split("Polygon", "tool_poly6", pl, pc), FALSE, FALSE, 0);
    }
    {
        static const char *sl[] = {"Control Points", "Finish Spline", NULL};
        static const char *sc[] = {"tool_spline", "done", NULL};
        gtk_box_pack_start(GTK_BOX(sk), mk_split("Spline", "tool_spline", sl, sc), FALSE, FALSE, 0);
    }
    gtk_box_pack_start(GTK_BOX(sk), mk_btn("Trim", "tool_trim"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(sk), mk_btn("Fillet 2D", "tool_fillet2d"), FALSE, FALSE, 0);
    {
        GtkWidget *mb = gtk_menu_button_new();
        gtk_button_set_label(GTK_BUTTON(mb), "Constrain ▾");
        gtk_widget_set_name(mb, "tool-btn");
        GtkWidget *menu = gtk_menu_new();
        GtkWidget *habs = gtk_menu_item_new_with_label("Absolute  (origin / axes)");
        gtk_widget_set_sensitive(habs, FALSE);
        gtk_menu_shell_append(GTK_MENU_SHELL(menu), habs);
        static const char *alabs[] = {
            "Point", "Fix to O", "Fix X", "Fix Y", "Dist to O",
            "Horiz", "Vert", "Radius",
            NULL
        };
        static const char *acmds[] = {
            "tool_point", "cstr_fixo", "cstr_fixx", "cstr_fixy", "cstr_disto",
            "cstr_h", "cstr_v", "cstr_rad",
            NULL
        };
        int ai;
        for (ai = 0; alabs[ai]; ai++) {
            GtkWidget *it = gtk_menu_item_new_with_label(alabs[ai]);
            g_signal_connect(it, "activate", G_CALLBACK(cb_menu_cmd), (gpointer)acmds[ai]);
            gtk_menu_shell_append(GTK_MENU_SHELL(menu), it);
        }
        gtk_menu_shell_append(GTK_MENU_SHELL(menu), gtk_separator_menu_item_new());
        GtkWidget *hrel = gtk_menu_item_new_with_label("Relative  (other geometry)");
        gtk_widget_set_sensitive(hrel, FALSE);
        gtk_menu_shell_append(GTK_MENU_SHELL(menu), hrel);
        static const char *rlabs[] = {
            "Coincident", "On Line", "Tangent", "Equal R", "Distance",
            "Solve", NULL
        };
        static const char *rcmds[] = {
            "cstr_coinc", "cstr_pon", "cstr_tang", "cstr_eqr", "cstr_dist",
            "solve", NULL
        };
        int ri;
        for (ri = 0; rlabs[ri]; ri++) {
            GtkWidget *it = gtk_menu_item_new_with_label(rlabs[ri]);
            g_signal_connect(it, "activate", G_CALLBACK(cb_menu_cmd), (gpointer)rcmds[ri]);
            gtk_menu_shell_append(GTK_MENU_SHELL(menu), it);
        }
        gtk_widget_show_all(menu);
        gtk_menu_button_set_popup(GTK_MENU_BUTTON(mb), menu);
        gtk_box_pack_start(GTK_BOX(sk), mb, FALSE, FALSE, 0);
    }
    gtk_box_pack_start(GTK_BOX(sk), mk_btn("Project", "proj"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(sk), mk_btn("Clear Sketch", "csk"), FALSE, FALSE, 0);
    add_tab(G.ribbon, "Sketch", sk);

    GtkWidget *so = tab_box();
    gtk_box_pack_start(GTK_BOX(so), mk_btn("Pick", "tool_pick"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(so), mk_btn("On Face", "plane_top"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(so), mk_btn("Extrude", "repad"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(so), mk_btn("Revolve", "revolve"), FALSE, FALSE, 0);
    {
        static const char *ml[] = {"Fillet", "Chamfer", NULL};
        static const char *mc[] = {"tool_fillet3d", "tool_chamfer", NULL};
        gtk_box_pack_start(GTK_BOX(so), mk_split("Modify", "tool_fillet3d", ml, mc), FALSE, FALSE, 0);
    }
    add_tab(G.ribbon, "Solid", so);
    G.page_solid = 1;

    GtkWidget *cn = tab_box();
    {
        static const char *dl[] = {"XY", "XZ", "YZ", NULL};
        static const char *dc[] = {"plane_xy", "plane_xz", "plane_yz", NULL};
        gtk_box_pack_start(GTK_BOX(cn), mk_split("Datum", "plane_xy", dl, dc), FALSE, FALSE, 0);
    }
    gtk_box_pack_start(GTK_BOX(cn), mk_btn("Pick Plane", "plane_pick"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(cn), mk_btn("From Face", "plane_from"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(cn), mk_btn("Origin", "plane_org"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(cn), mk_btn("Through 3pt", "plane_3pt"), FALSE, FALSE, 0);
    {
        GtkWidget *ob = gtk_button_new_with_label("Offset");
        gtk_widget_set_name(ob, "tool-btn");
        g_signal_connect(ob, "clicked", G_CALLBACK(on_plane_offset), NULL);
        gtk_box_pack_start(GTK_BOX(cn), ob, FALSE, FALSE, 0);
    }
    {
        GtkWidget *ab = gtk_button_new_with_label("Angle");
        gtk_widget_set_name(ab, "tool-btn");
        g_signal_connect(ab, "clicked", G_CALLBACK(on_plane_angle), NULL);
        gtk_box_pack_start(GTK_BOX(cn), ab, FALSE, FALSE, 0);
    }
    gtk_box_pack_start(GTK_BOX(cn), mk_btn("Flip", "plane_flip"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(cn), mk_btn("Sketch on Plane", "sketch_pln"), FALSE, FALSE, 0);
    add_tab(G.ribbon, "Construct", cn);

    GtkWidget *ms = tab_box();
    gtk_box_pack_start(GTK_BOX(ms), gtk_label_new("  Measure — later"), FALSE, FALSE, 8);
    add_tab(G.ribbon, "Measure", ms);

    GtkWidget *sf = tab_box();
    gtk_box_pack_start(GTK_BOX(sf), gtk_label_new("  Surface — later"), FALSE, FALSE, 8);
    add_tab(G.ribbon, "Surface", sf);

    GtkWidget *vw = tab_box();
    gtk_box_pack_start(GTK_BOX(vw), mk_btn("2D / 3D", "mode"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(vw), mk_btn("ISO", "iso"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(vw), mk_btn("Top", "view1"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(vw), mk_btn("Front", "view2"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(vw), mk_btn("Right", "view4"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(vw), mk_btn("Left", "view5"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(vw), mk_btn("Back", "view6"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(vw), mk_btn("Bottom", "view7"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(vw), mk_btn("Grid", "grid"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(vw), mk_btn("Wire", "wire"), FALSE, FALSE, 0);
    add_tab(G.ribbon, "View", vw);
    g_signal_connect(G.ribbon, "switch-page", G_CALLBACK(on_ribbon_page), NULL);

    /* viewport + viewcube overlay + navigator */
    GtkWidget *work = gtk_paned_new(GTK_ORIENTATION_HORIZONTAL);
    gtk_box_pack_start(GTK_BOX(root), work, TRUE, TRUE, 0);

    GtkWidget *side = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_set_size_request(side, 240, -1);
    G.navhdr = gtk_label_new("  WORK TREE");
    gtk_widget_set_name(G.navhdr, "navhdr");
    gtk_label_set_xalign(GTK_LABEL(G.navhdr), 0.0);
    gtk_box_pack_start(GTK_BOX(side), G.navhdr, FALSE, FALSE, 0);
    G.tree_open_all = 1;
    G.fold_btn = gtk_button_new_with_label("Collapse");
    gtk_widget_set_name(G.fold_btn, "foldbar");
    gtk_widget_set_tooltip_text(G.fold_btn, "Collapse or expand the work tree");
    gtk_widget_set_hexpand(G.fold_btn, TRUE);
    gtk_widget_set_halign(G.fold_btn, GTK_ALIGN_FILL);
    g_signal_connect(G.fold_btn, "clicked", G_CALLBACK(on_tree_fold), NULL);
    gtk_box_pack_start(GTK_BOX(side), G.fold_btn, FALSE, FALSE, 0);
    G.tstore = gtk_tree_store_new(2, G_TYPE_STRING, G_TYPE_STRING);
    G.treev = gtk_tree_view_new_with_model(GTK_TREE_MODEL(G.tstore));
    gtk_tree_view_set_headers_visible(GTK_TREE_VIEW(G.treev), FALSE);
    gtk_tree_view_set_enable_tree_lines(GTK_TREE_VIEW(G.treev), TRUE);
    gtk_tree_view_set_show_expanders(GTK_TREE_VIEW(G.treev), TRUE);
    GtkCellRenderer *cr = gtk_cell_renderer_text_new();
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(G.treev), -1, "", cr, "text", 0, NULL);
    g_signal_connect(G.treev, "row-activated", G_CALLBACK(on_tree_row), NULL);
    g_signal_connect(G.treev, "button-press-event", G_CALLBACK(on_tree_btn), NULL);
    g_signal_connect(G.treev, "button-release-event", G_CALLBACK(on_tree_btn), NULL);
    GtkWidget *scr = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scr), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scr), G.treev);
    gtk_box_pack_start(GTK_BOX(side), scr, TRUE, TRUE, 0);
    gtk_paned_pack1(GTK_PANED(work), side, FALSE, FALSE);

    GtkWidget *ov = gtk_overlay_new();
    gtk_paned_pack2(GTK_PANED(work), ov, TRUE, FALSE);
    gtk_paned_set_position(GTK_PANED(work), 248);
    G.da = gtk_drawing_area_new();
    gtk_widget_set_hexpand(G.da, TRUE);
    gtk_widget_set_vexpand(G.da, TRUE);
    gtk_widget_set_can_focus(G.da, TRUE);
    gtk_widget_add_events(G.da,
                          GDK_BUTTON_PRESS_MASK | GDK_BUTTON_RELEASE_MASK |
                              GDK_POINTER_MOTION_MASK | GDK_SCROLL_MASK |
                              GDK_KEY_PRESS_MASK);
    g_signal_connect(G.da, "draw", G_CALLBACK(on_draw), NULL);
    g_signal_connect(G.da, "key-press-event", G_CALLBACK(on_key), NULL);
    g_signal_connect(G.da, "button-press-event", G_CALLBACK(on_button), NULL);
    g_signal_connect(G.da, "button-release-event", G_CALLBACK(on_button), NULL);
    g_signal_connect(G.da, "motion-notify-event", G_CALLBACK(on_motion), NULL);
    g_signal_connect(G.da, "scroll-event", G_CALLBACK(on_scroll), NULL);
    gtk_container_add(GTK_CONTAINER(ov), G.da);

    G.cube_mt = 10;
    G.cube_me = 10;
    G.cube_hover = -1;
    G.cube_host = gtk_event_box_new();
    gtk_widget_set_halign(G.cube_host, GTK_ALIGN_END);
    gtk_widget_set_valign(G.cube_host, GTK_ALIGN_START);
    gtk_widget_set_margin_top(G.cube_host, G.cube_mt);
    gtk_widget_set_margin_end(G.cube_host, G.cube_me);
    G.cube = gtk_drawing_area_new();
    gtk_widget_set_size_request(G.cube, 136, 152);
    gtk_widget_add_events(G.cube,
                          GDK_BUTTON_PRESS_MASK | GDK_BUTTON_RELEASE_MASK |
                              GDK_POINTER_MOTION_MASK | GDK_SCROLL_MASK);
    g_signal_connect(G.cube, "draw", G_CALLBACK(on_cube_draw), NULL);
    g_signal_connect(G.cube, "button-press-event", G_CALLBACK(on_cube_button), NULL);
    g_signal_connect(G.cube, "button-release-event", G_CALLBACK(on_cube_button), NULL);
    g_signal_connect(G.cube, "motion-notify-event", G_CALLBACK(on_cube_motion), NULL);
    g_signal_connect(G.cube, "scroll-event", G_CALLBACK(on_cube_scroll), NULL);
    gtk_container_add(GTK_CONTAINER(G.cube_host), G.cube);
    gtk_overlay_add_overlay(GTK_OVERLAY(ov), G.cube_host);

    GtkWidget *navbar = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 4);
    gtk_widget_set_halign(navbar, GTK_ALIGN_CENTER);
    gtk_widget_set_valign(navbar, GTK_ALIGN_END);
    gtk_widget_set_margin_bottom(navbar, 10);
    gtk_box_pack_start(GTK_BOX(navbar), mk_btn("Zoom+", "zoom 1"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(navbar), mk_btn("Zoom-", "zoom -1"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(navbar), mk_btn("Grid", "grid"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(navbar), mk_btn("Wire", "wire"), FALSE, FALSE, 0);
    gtk_overlay_add_overlay(GTK_OVERLAY(ov), navbar);

    /* global timeline — same hist.txt as the popout / tree Back-Forward */
    G.tl_dock = gtk_box_new(GTK_ORIENTATION_VERTICAL, 2);
    gtk_widget_set_name(G.tl_dock, "tldock");
    gtk_widget_set_can_focus(G.tl_dock, TRUE);
    GtkWidget *tlrow = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_box_pack_start(GTK_BOX(tlrow), mk_btn("◀", "undo"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(tlrow), mk_btn("▶", "redo"), FALSE, FALSE, 0);
    G.hist_lbl = gtk_label_new("timeline");
    gtk_widget_set_name(G.hist_lbl, "hudbar");
    gtk_label_set_xalign(GTK_LABEL(G.hist_lbl), 0.0);
    gtk_widget_set_size_request(G.hist_lbl, 140, -1);
    gtk_box_pack_start(GTK_BOX(tlrow), G.hist_lbl, FALSE, FALSE, 4);
    G.hist_scale = gtk_scale_new_with_range(GTK_ORIENTATION_HORIZONTAL, 0, 1, 1);
    gtk_scale_set_digits(GTK_SCALE(G.hist_scale), 0);
    gtk_scale_set_draw_value(GTK_SCALE(G.hist_scale), FALSE);
    gtk_widget_set_hexpand(G.hist_scale, TRUE);
    g_signal_connect(G.hist_scale, "value-changed", G_CALLBACK(hist_scale_changed), NULL);
    gtk_box_pack_start(GTK_BOX(tlrow), G.hist_scale, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(tlrow), mk_btn("Prune", "prune"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(G.tl_dock), tlrow, FALSE, FALSE, 0);
    GtkWidget *tlscr = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(tlscr),
                                   GTK_POLICY_AUTOMATIC, GTK_POLICY_NEVER);
    gtk_widget_set_size_request(tlscr, -1, 36);
    G.tl_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 3);
    gtk_container_add(GTK_CONTAINER(tlscr), G.tl_box);
    gtk_box_pack_start(GTK_BOX(G.tl_dock), tlscr, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(root), G.tl_dock, FALSE, FALSE, 0);

    G.status = gtk_label_new("ready");
    gtk_widget_set_name(G.status, "statbar");
    gtk_label_set_xalign(GTK_LABEL(G.status), 0.0);
    gtk_box_pack_start(GTK_BOX(root), G.status, FALSE, FALSE, 0);

    g_timeout_add(16, poll_tick, NULL);
    gtk_widget_show_all(G.win);
    g_timeout_add(700, recover_stashes, NULL);
    gtk_main();

    if (G.frame) cairo_surface_destroy(G.frame);
    free(G.pix);
    return 0;
}
