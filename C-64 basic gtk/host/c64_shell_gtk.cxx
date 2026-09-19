/* c64_shell_gtk — Gtk3 chrome for C64 BASIC.
 * Kernel (c64_basic_gtk.x) owns the 80x24 cell buffer:
 *   /tmp/c64_basic/screen.bin  width*height bytes
 *   /tmp/c64_basic/gen.txt     generation
 *   /tmp/c64_basic/keys.txt    host writes decimal key + newline
 *
 * Fonts: Pango monospace now. Swap for VIF/TVG like HalCodeGTK/fonts later.
 *
 * Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.
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
#include <sys/stat.h>

static char dir[512];
static char path_screen[600], path_gen[600], path_keys[600], path_paste[600], path_cur[600];
static int cur_r = 23, cur_c = 1;
static GtkWidget *win, *da;
static int last_gen = -1;
static int cols = 80, rows = 24;
static unsigned char cells[80 * 24];
static int cell_w = 10, cell_h = 18;
static int sel_on, sel_r0, sel_c0, sel_r1, sel_c1, dragging;

static void paths_init(const char *d) {
    snprintf(dir, sizeof dir, "%s", d);
    snprintf(path_screen, sizeof path_screen, "%s/screen.bin", d);
    snprintf(path_gen, sizeof path_gen, "%s/gen.txt", d);
    snprintf(path_keys, sizeof path_keys, "%s/keys.txt", d);
    snprintf(path_paste, sizeof path_paste, "%s/paste.txt", d);
    snprintf(path_cur, sizeof path_cur, "%s/cursor.txt", d);
}

static void write_key(int k) {
    FILE *f = fopen(path_keys, "w");
    if (!f) return;
    fprintf(f, "%d\n", k);
    fclose(f);
}

static void cell_at(GtkWidget *w, double wx, double wy, int *rr, int *cc) {
    GtkAllocation a;
    gtk_widget_get_allocation(w, &a);
    int r = 0, c = 0;
    if (a.width > 0 && a.height > 0) {
        c = (int)(wx * cols / a.width);
        r = (int)(wy * rows / a.height);
    }
    if (c < 0) c = 0;
    if (r < 0) r = 0;
    if (c >= cols) c = cols - 1;
    if (r >= rows) r = rows - 1;
    *rr = r;
    *cc = c;
}

static void sel_norm(int *r0, int *c0, int *r1, int *c1) {
    int t;
    *r0 = sel_r0;
    *c0 = sel_c0;
    *r1 = sel_r1;
    *c1 = sel_c1;
    if (*r1 < *r0) { t = *r0; *r0 = *r1; *r1 = t; t = *c0; *c0 = *c1; *c1 = t; }
    else if (*r1 == *r0 && *c1 < *c0) { t = *c0; *c0 = *c1; *c1 = t; }
}

static char *screen_text(int all) {
    GString *s = g_string_new(NULL);
    int r0 = 0, c0 = 0, r1 = rows - 1, c1 = cols - 1;
    int r, c, last;
    if (!all && sel_on) sel_norm(&r0, &c0, &r1, &c1);
    for (r = r0; r <= r1; r++) {
        int a = (r == r0) ? c0 : 0;
        int b = (r == r1) ? c1 : cols - 1;
        last = a - 1;
        for (c = a; c <= b; c++) {
            unsigned char ch = cells[r * cols + c];
            if (ch > 32 && ch < 127) last = c;
        }
        for (c = a; c <= last; c++) {
            unsigned char ch = cells[r * cols + c];
            if (ch < 32 || ch > 126) ch = 32;
            g_string_append_c(s, (char)ch);
        }
        if (r < r1) g_string_append_c(s, '\n');
    }
    return g_string_free(s, FALSE);
}

static void copy_to_clipboard(void) {
    char *t = screen_text(sel_on ? 0 : 1);
    GtkClipboard *cb = gtk_clipboard_get(GDK_SELECTION_CLIPBOARD);
    if (cb && t) gtk_clipboard_set_text(cb, t, -1);
    g_free(t);
}

static void write_paste_text(const char *t) {
    FILE *f;
    FILE *dbg;
    size_t n, i;
    if (!t) return;
    n = strlen(t);
    f = fopen(path_paste, "wb");
    if (!f) return;
    i = 0;
    while (i < n) {
        while (i < n && (t[i] == ' ' || t[i] == '\t' || t[i] == '\r')) i++;
        if (i >= n) break;
        if (t[i] == '\n') { i++; continue; }
        while (i < n && t[i] != '\n' && t[i] != '\r') {
            unsigned char c = (unsigned char)t[i];
            if (c >= 32 && c < 127) fputc(c, f);
            i++;
        }
        fputc('\n', f);
        if (i < n && t[i] == '\r') i++;
        if (i < n && t[i] == '\n') i++;
    }
    fclose(f);
    dbg = fopen("/tmp/c64_basic/debug.log", "a");
    if (dbg) {
        fprintf(dbg, "paste %zu bytes -> %s\n", n, path_paste);
        fclose(dbg);
    }
}

static void on_clip_text(GtkClipboard *cb, const gchar *text, gpointer data) {
    (void)cb;
    (void)data;
    write_paste_text(text);
}

static void paste_clipboard(GdkAtom which) {
    GtkClipboard *cb = gtk_clipboard_get(which);
    if (!cb) return;
    gtk_clipboard_request_text(cb, on_clip_text, NULL);
}

static int read_gen(void) {
    FILE *f = fopen(path_gen, "r");
    int g = -1;
    if (!f) return -1;
    if (fscanf(f, "%d", &g) != 1) g = -1;
    fclose(f);
    return g;
}

static void load_screen(void) {
    FILE *f = fopen(path_screen, "rb");
    if (!f) return;
    memset(cells, 32, sizeof cells);
    fread(cells, 1, cols * rows, f);
    fclose(f);
}

static gboolean on_draw(GtkWidget *w, cairo_t *cr, gpointer data) {
    (void)data;
    GtkAllocation a;
    gtk_widget_get_allocation(w, &a);
    cairo_set_source_rgb(cr, 0.0, 0.0, 0.0);
    cairo_paint(cr);
    double cw = (double)a.width / (double)cols;
    double ch = (double)a.height / (double)rows;
    if (cw < 4) cw = 4;
    if (ch < 8) ch = 8;
    if (sel_on) {
        int r0, c0, r1, c1;
        sel_norm(&r0, &c0, &r1, &c1);
        cairo_set_source_rgba(cr, 0.35, 0.35, 0.35, 0.45);
        cairo_rectangle(cr, c0 * cw, r0 * ch,
            (c1 - c0 + 1) * cw, (r1 - r0 + 1) * ch);
        cairo_fill(cr);
        cairo_set_source_rgb(cr, 0.85, 0.85, 0.85);
        cairo_set_line_width(cr, 1.0);
        cairo_rectangle(cr, c0 * cw + 0.5, r0 * ch + 0.5,
            (c1 - c0 + 1) * cw - 1.0, (r1 - r0 + 1) * ch - 1.0);
        cairo_stroke(cr);
    }
    cairo_select_font_face(cr, "DejaVu Sans Mono",
        CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL);
    cairo_set_font_size(cr, ch * 0.8);
    char buf[2] = {0, 0};
    int sr0 = 0, sc0 = 0, sr1 = 0, sc1 = 0;
    if (sel_on) sel_norm(&sr0, &sc0, &sr1, &sc1);
    for (int r = 0; r < rows; r++) {
        for (int c = 0; c < cols; c++) {
            int hit = 0;
            if (sel_on) {
                if (r > sr0 && r < sr1) hit = 1;
                else if (r == sr0 && r == sr1 && c >= sc0 && c <= sc1) hit = 1;
                else if (r == sr0 && r < sr1 && c >= sc0) hit = 1;
                else if (r == sr1 && r > sr0 && c <= sc1) hit = 1;
            }
            if (hit) {
                cairo_set_source_rgb(cr, 0.28, 0.28, 0.28);
                cairo_rectangle(cr, c * cw, r * ch, cw, ch);
                cairo_fill(cr);
            }
            unsigned char chv = cells[r * cols + c];
            if (chv < 32 || chv > 126) chv = 32;
            buf[0] = (char)chv;
            cairo_set_source_rgb(cr, 1.0, 1.0, 1.0);
            cairo_move_to(cr, c * cw + 1, (r + 0.8) * ch);
            cairo_show_text(cr, buf);
        }
    }
    {
        int crw = cur_r - 1, ccl = cur_c - 1;
        if (crw >= 0 && crw < rows && ccl >= 0 && ccl < cols) {
            cairo_set_source_rgb(cr, 1.0, 1.0, 1.0);
            cairo_rectangle(cr, ccl * cw, crw * ch, cw, ch);
            cairo_fill(cr);
            unsigned char chv = cells[crw * cols + ccl];
            if (chv >= 32 && chv < 127 && chv != 32) {
                buf[0] = (char)chv;
                cairo_set_source_rgb(cr, 0.0, 0.0, 0.0);
                cairo_move_to(cr, ccl * cw + 1, (crw + 0.8) * ch);
                cairo_show_text(cr, buf);
            }
        }
    }
    return FALSE;
}

static gboolean on_key(GtkWidget *w, GdkEventKey *e, gpointer data) {
    (void)w;
    (void)data;
    int k = 0;
    guint mods = e->state;
    if ((mods & GDK_CONTROL_MASK) && (e->keyval == GDK_KEY_v || e->keyval == GDK_KEY_V)) {
        paste_clipboard(GDK_SELECTION_CLIPBOARD);
        return TRUE;
    }
    if ((mods & GDK_CONTROL_MASK) && (e->keyval == GDK_KEY_c || e->keyval == GDK_KEY_C)) {
        copy_to_clipboard();
        return TRUE;
    }
    if ((mods & GDK_CONTROL_MASK) && (e->keyval == GDK_KEY_a || e->keyval == GDK_KEY_A)) {
        sel_on = 1;
        sel_r0 = 0;
        sel_c0 = 0;
        sel_r1 = rows - 1;
        sel_c1 = cols - 1;
        if (da) gtk_widget_queue_draw(da);
        return TRUE;
    }
    if ((mods & GDK_SHIFT_MASK) && e->keyval == GDK_KEY_Insert) {
        paste_clipboard(GDK_SELECTION_CLIPBOARD);
        return TRUE;
    }
    if (e->keyval == GDK_KEY_Return || e->keyval == GDK_KEY_KP_Enter) k = 13;
    else if (e->keyval == GDK_KEY_BackSpace) k = 8;
    else if (e->keyval == GDK_KEY_Escape) k = 27;
    else if (e->length == 1) k = (unsigned char)e->string[0];
    else if (e->keyval >= 32 && e->keyval < 127) k = (int)e->keyval;
    if (k) write_key(k);
    return TRUE;
}

static void on_menu_copy(GtkMenuItem *it, gpointer data) {
    (void)it;
    (void)data;
    copy_to_clipboard();
}

static void on_menu_paste(GtkMenuItem *it, gpointer data) {
    (void)it;
    (void)data;
    paste_clipboard(GDK_SELECTION_CLIPBOARD);
}

static void on_menu_select_all(GtkMenuItem *it, gpointer data) {
    (void)it;
    (void)data;
    sel_on = 1;
    sel_r0 = 0;
    sel_c0 = 0;
    sel_r1 = rows - 1;
    sel_c1 = cols - 1;
    if (da) gtk_widget_queue_draw(da);
}

static void popup_edit_menu(GdkEventButton *e) {
    GtkWidget *menu = gtk_menu_new();
    GtkWidget *copy = gtk_menu_item_new_with_label("Copy");
    GtkWidget *paste = gtk_menu_item_new_with_label("Paste");
    GtkWidget *all = gtk_menu_item_new_with_label("Select All");
    g_signal_connect(copy, "activate", G_CALLBACK(on_menu_copy), NULL);
    g_signal_connect(paste, "activate", G_CALLBACK(on_menu_paste), NULL);
    g_signal_connect(all, "activate", G_CALLBACK(on_menu_select_all), NULL);
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), copy);
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), paste);
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), all);
    gtk_widget_show_all(menu);
    gtk_menu_popup_at_pointer(GTK_MENU(menu), (GdkEvent *)e);
}

static gboolean on_button(GtkWidget *w, GdkEventButton *e, gpointer data) {
    (void)data;
    int r, c;
    GtkWidget *sz = da ? da : w;
    if (e->type == GDK_BUTTON_PRESS && e->button == 2) {
        paste_clipboard(GDK_SELECTION_PRIMARY);
        return TRUE;
    }
    if (e->type == GDK_BUTTON_PRESS && e->button == 3) {
        popup_edit_menu(e);
        return TRUE;
    }
    if (e->type == GDK_BUTTON_PRESS && e->button == 1) {
        cell_at(sz, e->x, e->y, &r, &c);
        dragging = 1;
        sel_on = 1;
        sel_r0 = sel_r1 = r;
        sel_c0 = sel_c1 = c;
        if (da) gtk_widget_queue_draw(da);
        gtk_widget_grab_focus(da);
        return TRUE;
    }
    if (e->type == GDK_BUTTON_RELEASE && e->button == 1) {
        dragging = 0;
        return TRUE;
    }
    return FALSE;
}

static gboolean on_motion(GtkWidget *w, GdkEventMotion *e, gpointer data) {
    (void)data;
    int r, c;
    GtkWidget *sz = da ? da : w;
    if (!dragging) return FALSE;
    cell_at(sz, e->x, e->y, &r, &c);
    sel_r1 = r;
    sel_c1 = c;
    if (da) gtk_widget_queue_draw(da);
    if (e->is_hint && gtk_widget_get_window(w))
        gdk_event_request_motions(e);
    return TRUE;
}

static gboolean tick(gpointer data) {
    (void)data;
    int g = read_gen();
    if (g != last_gen && g >= 0) {
        last_gen = g;
        load_screen();
        {
            FILE *cf = fopen(path_cur, "r");
            if (cf) {
                int rr = cur_r, cc = cur_c;
                if (fscanf(cf, "%d %d", &rr, &cc) == 2) {
                    cur_r = rr;
                    cur_c = cc;
                }
                fclose(cf);
            }
        }
        if (da) gtk_widget_queue_draw(da);
    }
    return TRUE;
}

int main(int argc, char **argv) {
    const char *st = getenv("C64_APP_STATE");
    if (!st || !st[0]) st = "/tmp/c64_basic";
    if (argc > 1) st = argv[1];
    paths_init(st);
    mkdir(st, 0755);
    gtk_init(&argc, &argv);
    win = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(win), "Commodore 64 BASIC");
    gtk_window_set_default_size(GTK_WINDOW(win), 800, 480);
    g_signal_connect(win, "destroy", G_CALLBACK(gtk_main_quit), NULL);
    da = gtk_drawing_area_new();
    gtk_widget_set_can_focus(da, TRUE);
    g_signal_connect(da, "draw", G_CALLBACK(on_draw), NULL);
    {
        GtkWidget *ebox = gtk_event_box_new();
        int emask = GDK_BUTTON_PRESS_MASK | GDK_BUTTON_RELEASE_MASK
            | GDK_POINTER_MOTION_MASK | GDK_POINTER_MOTION_HINT_MASK
            | GDK_BUTTON_MOTION_MASK | GDK_BUTTON1_MOTION_MASK
            | GDK_BUTTON3_MOTION_MASK;
        gtk_widget_add_events(ebox, emask);
        gtk_event_box_set_above_child(GTK_EVENT_BOX(ebox), TRUE);
        gtk_container_add(GTK_CONTAINER(ebox), da);
        gtk_container_add(GTK_CONTAINER(win), ebox);
        g_signal_connect(ebox, "button-press-event", G_CALLBACK(on_button), NULL);
        g_signal_connect(ebox, "button-release-event", G_CALLBACK(on_button), NULL);
        g_signal_connect(ebox, "motion-notify-event", G_CALLBACK(on_motion), NULL);
        g_signal_connect(da, "realize", G_CALLBACK(+[](GtkWidget *w, gpointer) {
            GdkWindow *gw = gtk_widget_get_window(w);
            if (!gw) return;
            GdkCursor *cur = gdk_cursor_new_from_name(gdk_display_get_default(), "crosshair");
            if (!cur) cur = gdk_cursor_new_for_display(gdk_display_get_default(), GDK_CROSSHAIR);
            gdk_window_set_cursor(gw, cur);
            if (cur) g_object_unref(cur);
        }), NULL);
    }
    g_signal_connect(win, "key-press-event", G_CALLBACK(on_key), NULL);
    gtk_widget_show_all(win);
    gtk_widget_grab_focus(da);
    g_timeout_add(50, tick, NULL);
    gtk_main();
    return 0;
}
