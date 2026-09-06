/* paint_shell_gtk — thin Gtk3 host for ImageEdit.
 * Chrome + blit + pointer. Kernel owns pixels (Paint/paint_app.ailang).
 *
 *   make -C Paint/host
 *   PAINT_APP_STATE=/tmp/paint_app ./Paint/host/paint_shell_gtk
 *
 * Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.
 */
#include <gtk/gtk.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdint.h>
#include <sys/stat.h>

static char dir[512];
static char path_meta[600], path_frame[600], path_gen[600];
static char path_cmd[600], path_ptr[600], path_path[600];

static GtkWidget *win, *draw_area, *status;
static cairo_surface_t *surf;
static int last_gen = -1, fw = 800, fh = 600;
static int btn_down, ptr_x, ptr_y, last_mx = -1, last_my = -1;

static void view_map(double wx, double wy, int *cx, int *cy) {
    GtkAllocation a;
    gtk_widget_get_allocation(draw_area, &a);
    if (fw < 1) fw = 800;
    if (fh < 1) fh = 600;
    if (a.width < 1 || a.height < 1) {
        *cx = 0;
        *cy = 0;
        return;
    }
    double sx = (double)a.width / (double)fw;
    double sy = (double)a.height / (double)fh;
    double s = sx < sy ? sx : sy;
    if (s < 0.01) s = 0.01;
    double ox = (a.width - fw * s) * 0.5;
    double oy = (a.height - fh * s) * 0.5;
    int x = (int)((wx - ox) / s);
    int y = (int)((wy - oy) / s);
    if (x < 0) x = 0;
    if (y < 0) y = 0;
    if (x >= fw) x = fw - 1;
    if (y >= fh) y = fh - 1;
    *cx = x;
    *cy = y;
}

static int le32(const uint8_t *p) {
    return (int)(p[0] | (p[1] << 8) | (p[2] << 16) | (p[3] << 24));
}

static void write_cmd(const char *s) {
    int tries;
    for (tries = 0; tries < 60; tries++) {
        FILE *cf = fopen(path_cmd, "r");
        int busy = 0;
        if (cf) {
            int c = fgetc(cf);
            if (c != EOF && c != '\n' && c != '\r' && c != ' ') busy = 1;
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

static void write_ptr(const char *s) {
    char tmp[600];
    snprintf(tmp, sizeof tmp, "%s/ptr.tmp", dir);
    FILE *f = fopen(tmp, "w");
    if (!f) return;
    fputs(s, f);
    if (s[0] && s[strlen(s) - 1] != '\n') fputc('\n', f);
    fclose(f);
    rename(tmp, path_ptr);
}

static void write_path(const char *p) {
    FILE *f = fopen(path_path, "w");
    if (!f) return;
    fputs(p, f);
    fputc('\n', f);
    fclose(f);
}

static int read_gen(void) {
    FILE *f = fopen(path_gen, "r");
    if (!f) return -1;
    int g = -1;
    if (fscanf(f, "%d", &g) != 1) g = -1;
    fclose(f);
    return g;
}

static int load_frame(void) {
    int fd = open(path_meta, O_RDONLY);
    if (fd < 0) return 0;
    uint8_t hdr[16];
    ssize_t nr = read(fd, hdr, 16);
    close(fd);
    if (nr < 12) return 0;
    int w = le32(hdr + 0);
    int h = le32(hdr + 4);
    int p = le32(hdr + 8);
    if (w < 16 || h < 16 || w > 4096 || h > 4096) return 0;
    fw = w;
    fh = h;
    fd = open(path_frame, O_RDONLY);
    if (fd < 0) return 0;
    if (!surf || cairo_image_surface_get_width(surf) != w ||
        cairo_image_surface_get_height(surf) != h) {
        if (surf) cairo_surface_destroy(surf);
        surf = cairo_image_surface_create(CAIRO_FORMAT_ARGB32, w, h);
    }
    uint8_t *dst = cairo_image_surface_get_data(surf);
    int dp = cairo_image_surface_get_stride(surf);
    int ok = 1;
    if (dp == p) {
        size_t n = (size_t)p * (size_t)h;
        if (read(fd, dst, n) != (ssize_t)n) ok = 0;
    } else {
        for (int y = 0; y < h && ok; y++) {
            if (read(fd, dst + y * dp, (size_t)w * 4) != (ssize_t)w * 4) ok = 0;
        }
    }
    close(fd);
    if (!ok) return 0;
    cairo_surface_mark_dirty(surf);
    gtk_widget_queue_draw(draw_area);
    return 1;
}

static gboolean on_draw(GtkWidget *w, cairo_t *cr, gpointer) {
    GtkAllocation a;
    gtk_widget_get_allocation(w, &a);
    cairo_set_source_rgb(cr, 0.10, 0.10, 0.12);
    cairo_paint(cr);
    if (!surf || fw < 1 || fh < 1) return FALSE;
    double sx = (double)a.width / (double)fw;
    double sy = (double)a.height / (double)fh;
    double s = sx < sy ? sx : sy;
    if (s < 0.01) s = 0.01;
    double ox = (a.width - fw * s) * 0.5;
    double oy = (a.height - fh * s) * 0.5;
    cairo_translate(cr, ox, oy);
    cairo_scale(cr, s, s);
    cairo_set_source_surface(cr, surf, 0, 0);
    cairo_pattern_set_filter(cairo_get_source(cr), CAIRO_FILTER_BILINEAR);
    cairo_paint(cr);
    return FALSE;
}

static gboolean on_press(GtkWidget *w, GdkEventButton *e, gpointer) {
    gtk_widget_grab_focus(w);
    if (e->type == GDK_2BUTTON_PRESS) {
        write_cmd("apply");
        return TRUE;
    }
    if (e->button == 3) {
        write_cmd("apply");
        return TRUE;
    }
    if (e->button != 1) return FALSE;
    btn_down = 1;
    view_map(e->x, e->y, &ptr_x, &ptr_y);
    last_mx = ptr_x;
    last_my = ptr_y;
    char buf[64];
    snprintf(buf, sizeof buf, "d %d %d", ptr_x, ptr_y);
    write_ptr(buf);
    return TRUE;
}

static gboolean on_release(GtkWidget *, GdkEventButton *e, gpointer) {
    if (e->button != 1) return FALSE;
    btn_down = 0;
    view_map(e->x, e->y, &ptr_x, &ptr_y);
    char buf[64];
    snprintf(buf, sizeof buf, "u %d %d", ptr_x, ptr_y);
    write_ptr(buf);
    return TRUE;
}

static gboolean on_motion(GtkWidget *, GdkEventMotion *e, gpointer) {
    view_map(e->x, e->y, &ptr_x, &ptr_y);
    return TRUE;
}

static gboolean on_configure(GtkWidget *, GdkEventConfigure *, gpointer) {
    gtk_widget_queue_draw(draw_area);
    return FALSE;
}

static void cb_size(GtkComboBox *c, gpointer) {
    gchar *t = gtk_combo_box_text_get_active_text(GTK_COMBO_BOX_TEXT(c));
    if (!t) return;
    char buf[32];
    snprintf(buf, sizeof buf, "size %s", t);
    write_cmd(buf);
    g_free(t);
}

static void send_shape(GtkComboBox *c) {
    gint i = gtk_combo_box_get_active(c);
    if (i < 0) return;
    char buf[32];
    snprintf(buf, sizeof buf, "shape %d", (int)i);
    write_cmd(buf);
}

static void cb_shape(GtkComboBox *c, gpointer) {
    send_shape(c);
}

static gboolean on_shape_press(GtkWidget *w, GdkEventButton *, gpointer) {
    send_shape(GTK_COMBO_BOX(w));
    return FALSE;
}

static gboolean on_key(GtkWidget *, GdkEventKey *e, gpointer) {
    if (e->keyval == GDK_KEY_Return || e->keyval == GDK_KEY_KP_Enter) {
        write_cmd("apply");
        return TRUE;
    }
    if (e->keyval == GDK_KEY_Escape) {
        write_cmd("cancel");
        return TRUE;
    }
    return FALSE;
}

static gboolean on_tick(gpointer) {
    int g = read_gen();
    if (g != last_gen && g >= 0) {
        if (load_frame()) last_gen = g;
    }
    int dx = ptr_x - last_mx;
    int dy = ptr_y - last_my;
    if (dx < 0) dx = -dx;
    if (dy < 0) dy = -dy;
    if (dx + dy >= 2) {
        last_mx = ptr_x;
        last_my = ptr_y;
        char buf[64];
        snprintf(buf, sizeof buf, "m %d %d", ptr_x, ptr_y);
        write_ptr(buf);
    }
    return TRUE;
}

static gboolean on_delete(GtkWidget *, GdkEvent *, gpointer) {
    write_cmd("quit");
    gtk_main_quit();
    return TRUE;
}

static void cb_cmd(GtkButton *, gpointer data) {
    if (data) write_cmd((const char *)data);
}

static void cb_menu(GtkMenuItem *, gpointer data) {
    if (data) write_cmd((const char *)data);
}

static void pick_file(int save) {
    GtkWidget *dlg = gtk_file_chooser_dialog_new(
        save ? "Save BMP" : "Open BMP", GTK_WINDOW(win),
        save ? GTK_FILE_CHOOSER_ACTION_SAVE : GTK_FILE_CHOOSER_ACTION_OPEN,
        "Cancel", GTK_RESPONSE_CANCEL,
        save ? "Save" : "Open", GTK_RESPONSE_ACCEPT, NULL);
    GtkFileFilter *ff = gtk_file_filter_new();
    gtk_file_filter_set_name(ff, "BMP");
    gtk_file_filter_add_pattern(ff, "*.bmp");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(dlg), ff);
    if (save) gtk_file_chooser_set_current_name(GTK_FILE_CHOOSER(dlg), "untitled.bmp");
    if (gtk_dialog_run(GTK_DIALOG(dlg)) == GTK_RESPONSE_ACCEPT) {
        char *fn = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(dlg));
        if (fn) {
            write_path(fn);
            write_cmd(save ? "saveas" : "open");
            g_free(fn);
        }
    }
    gtk_widget_destroy(dlg);
}

static void cb_open(GtkMenuItem *, gpointer) { pick_file(0); }
static void cb_saveas(GtkMenuItem *, gpointer) { pick_file(1); }

static GtkWidget *mk_btn(const char *lab, const char *cmd) {
    GtkWidget *b = gtk_button_new_with_label(lab);
    g_signal_connect(b, "clicked", G_CALLBACK(cb_cmd), (gpointer)cmd);
    return b;
}

int main(int argc, char **argv) {
    const char *d = "/tmp/paint_app";
    if (argc > 1 && argv[1] && argv[1][0]) d = argv[1];
    snprintf(dir, sizeof dir, "%s", d);
    mkdir(dir, 0755);
    snprintf(path_meta, sizeof path_meta, "%s/meta.bin", dir);
    snprintf(path_frame, sizeof path_frame, "%s/frame.raw", dir);
    snprintf(path_gen, sizeof path_gen, "%s/gen.txt", dir);
    snprintf(path_cmd, sizeof path_cmd, "%s/cmd.txt", dir);
    snprintf(path_ptr, sizeof path_ptr, "%s/ptr.txt", dir);
    snprintf(path_path, sizeof path_path, "%s/path.txt", dir);

    gtk_init(&argc, &argv);
    win = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(win), "Paint");
    gtk_window_set_default_size(GTK_WINDOW(win), 720, 560);
    gtk_window_set_resizable(GTK_WINDOW(win), TRUE);
    g_signal_connect(win, "delete-event", G_CALLBACK(on_delete), NULL);
    g_signal_connect(win, "key-press-event", G_CALLBACK(on_key), NULL);

    GtkWidget *vbox = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_container_add(GTK_CONTAINER(win), vbox);

    GtkWidget *menu = gtk_menu_bar_new();
    GtkWidget *file_item = gtk_menu_item_new_with_label("File");
    GtkWidget *file_menu = gtk_menu_new();
    gtk_menu_item_set_submenu(GTK_MENU_ITEM(file_item), file_menu);
    GtkWidget *mi;
    mi = gtk_menu_item_new_with_label("New");
    g_signal_connect(mi, "activate", G_CALLBACK(cb_menu), (gpointer)"new");
    gtk_menu_shell_append(GTK_MENU_SHELL(file_menu), mi);
    mi = gtk_menu_item_new_with_label("Open…");
    g_signal_connect(mi, "activate", G_CALLBACK(cb_open), NULL);
    gtk_menu_shell_append(GTK_MENU_SHELL(file_menu), mi);
    mi = gtk_menu_item_new_with_label("Save");
    g_signal_connect(mi, "activate", G_CALLBACK(cb_menu), (gpointer)"save");
    gtk_menu_shell_append(GTK_MENU_SHELL(file_menu), mi);
    mi = gtk_menu_item_new_with_label("Save As…");
    g_signal_connect(mi, "activate", G_CALLBACK(cb_saveas), NULL);
    gtk_menu_shell_append(GTK_MENU_SHELL(file_menu), mi);
    mi = gtk_menu_item_new_with_label("Quit");
    g_signal_connect(mi, "activate", G_CALLBACK(cb_menu), (gpointer)"quit");
    g_signal_connect(mi, "activate", G_CALLBACK(gtk_main_quit), NULL);
    gtk_menu_shell_append(GTK_MENU_SHELL(file_menu), mi);
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), file_item);
    gtk_box_pack_start(GTK_BOX(vbox), menu, FALSE, FALSE, 0);

    GtkWidget *bar = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 3);
    gtk_container_set_border_width(GTK_CONTAINER(bar), 3);
    gtk_box_pack_start(GTK_BOX(bar), mk_btn("Pencil", "pencil"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(bar), mk_btn("Airbrush", "airbrush"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(bar), mk_btn("Line", "line"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(bar), mk_btn("Arc", "arc"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(bar), mk_btn("Curve", "curve"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(bar), mk_btn("Spline", "spline"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(bar), gtk_label_new(" Shape"), FALSE, FALSE, 4);
    GtkWidget *sh = gtk_combo_box_text_new();
    const char *shapes[] = {
        "Triangle", "Square", "Rect", "Diamond",
        "Pentagon", "Hexagon", "Star", "Oval"
    };
    for (unsigned i = 0; i < sizeof shapes / sizeof shapes[0]; i++)
        gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(sh), shapes[i]);
    g_signal_connect(sh, "changed", G_CALLBACK(cb_shape), NULL);
    g_signal_connect(sh, "button-press-event", G_CALLBACK(on_shape_press), NULL);
    gtk_box_pack_start(GTK_BOX(bar), sh, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(bar), mk_btn("Apply", "apply"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(bar), mk_btn("Cancel", "cancel"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(bar), mk_btn("Eraser", "eraser"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(vbox), bar, FALSE, FALSE, 0);

    GtkWidget *bar2 = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 3);
    gtk_container_set_border_width(GTK_CONTAINER(bar2), 3);
    gtk_box_pack_start(GTK_BOX(bar2), mk_btn("Black", "black"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(bar2), mk_btn("Red", "red"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(bar2), mk_btn("Blue", "blue"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(bar2), mk_btn("White", "white"), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(bar2), gtk_label_new("  Size"), FALSE, FALSE, 4);
    GtkWidget *sz = gtk_combo_box_text_new();
    const char *sizes[] = {"1", "2", "4", "8", "12", "16", "24", "32", "48", "64"};
    for (unsigned i = 0; i < sizeof sizes / sizeof sizes[0]; i++)
        gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(sz), sizes[i]);
    gtk_combo_box_set_active(GTK_COMBO_BOX(sz), 3);
    g_signal_connect(sz, "changed", G_CALLBACK(cb_size), NULL);
    gtk_box_pack_start(GTK_BOX(bar2), sz, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(vbox), bar2, FALSE, FALSE, 0);

    draw_area = gtk_drawing_area_new();
    gtk_widget_set_hexpand(draw_area, TRUE);
    gtk_widget_set_vexpand(draw_area, TRUE);
    gtk_widget_set_size_request(draw_area, 240, 180);
    gtk_widget_set_can_focus(draw_area, TRUE);
    gtk_widget_add_events(draw_area,
        GDK_BUTTON_PRESS_MASK | GDK_BUTTON_RELEASE_MASK |
        GDK_POINTER_MOTION_MASK | GDK_KEY_PRESS_MASK);
    g_signal_connect(draw_area, "draw", G_CALLBACK(on_draw), NULL);
    g_signal_connect(draw_area, "configure-event", G_CALLBACK(on_configure), NULL);
    g_signal_connect(draw_area, "button-press-event", G_CALLBACK(on_press), NULL);
    g_signal_connect(draw_area, "button-release-event", G_CALLBACK(on_release), NULL);
    g_signal_connect(draw_area, "motion-notify-event", G_CALLBACK(on_motion), NULL);
    gtk_box_pack_start(GTK_BOX(vbox), draw_area, TRUE, TRUE, 0);

    status = gtk_label_new("Shape: pick Triangle/Square/… then drag a box. Arc/Curve: 3 clicks. Spline: clicks then Enter/right-click. Esc cancels.");
    gtk_widget_set_halign(status, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(vbox), status, FALSE, FALSE, 2);

    g_timeout_add(16, on_tick, NULL);
    gtk_widget_show_all(win);
    load_frame();
    gtk_main();
    write_cmd("quit");
    if (surf) cairo_surface_destroy(surf);
    return 0;
}
