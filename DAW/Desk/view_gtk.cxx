// View facilitator. Blits the desk framebuffer. No controls.
// Pointer events are written for the AILANG desk to read.
//
// Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.
#include <gtk/gtk.h>
#include <cairo.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>

enum { FB_W = 1280, FB_H = 720 };

static uint8_t *g_pix;
static uint8_t *g_stable;
static cairo_surface_t *g_surf;
static GtkWidget *g_area;
static int g_fd_ptr = -1;
static int g_down = 0;
static int g_x = 0;
static int g_y = 0;
static uint32_t g_kseq = 0;

static void write_ptr(int x, int y, int btn, int cmd) {
    if (g_fd_ptr < 0) return;
    static uint32_t seq;
    g_x = x;
    g_y = y;
    uint32_t ks = g_kseq;
    if (cmd) ks = ++g_kseq;
    uint32_t buf[6];
    buf[0] = (uint32_t)x;
    buf[1] = (uint32_t)y;
    buf[2] = (uint32_t)btn;
    buf[3] = ++seq;
    buf[4] = (uint32_t)cmd;
    buf[5] = ks;
    lseek(g_fd_ptr, 0, SEEK_SET);
    if (write(g_fd_ptr, buf, 24) < 0) {
        /* the desk still draws if the pointer file is busy */
    }
}

static int command_of(GdkEventKey *ev) {
    guint k = ev->keyval;
    if (k == GDK_KEY_Delete || k == GDK_KEY_BackSpace) return 5;
    if ((ev->state & GDK_CONTROL_MASK) == 0) return 0;
    if (k == GDK_KEY_c || k == GDK_KEY_C) return 1;
    if (k == GDK_KEY_x || k == GDK_KEY_X) return 2;
    if (k == GDK_KEY_v || k == GDK_KEY_V) return 3;
    if (k == GDK_KEY_d || k == GDK_KEY_D) return 4;
    return 0;
}

static gboolean tick(gpointer) {
    if (g_pix && g_stable) {
        memcpy(g_stable, g_pix, FB_W * FB_H * 4);
        cairo_surface_mark_dirty(g_surf);
    }
    if (g_area) gtk_widget_queue_draw(g_area);
    return TRUE;
}

static gboolean draw(GtkWidget *, cairo_t *cr, gpointer) {
    if (!g_surf) return FALSE;
    cairo_set_source_surface(cr, g_surf, 0, 0);
    cairo_paint(cr);
    return FALSE;
}

static gboolean motion(GtkWidget *, GdkEventMotion *ev, gpointer) {
    write_ptr((int)ev->x, (int)ev->y, g_down, 0);
    return FALSE;
}

static gboolean button(GtkWidget *w, GdkEventButton *ev, gpointer) {
    gtk_widget_grab_focus(w);
    if (ev->button == 1) {
        g_down = (ev->type == GDK_BUTTON_PRESS) ? 1 : 0;
        write_ptr((int)ev->x, (int)ev->y, g_down, 0);
        return FALSE;
    }
    if (ev->button == 3) {
        int btn = (ev->type == GDK_BUTTON_PRESS) ? 2 : g_down;
        write_ptr((int)ev->x, (int)ev->y, btn, 0);
    }
    return FALSE;
}

static void on_drop(GtkWidget *, GdkDragContext *, gint, gint,
                    GtkSelectionData *data, guint, guint, gpointer) {
    gchar **uris = gtk_selection_data_get_uris(data);
    if (!uris || !uris[0]) return;
    const char *u = uris[0];
    if (strncmp(u, "file://", 7) == 0) u += 7;
    FILE *f = fopen("/dev/shm/daw/drop.txt", "w");
    if (f) {
        fputs(u, f);
        fputc('\n', f);
        fclose(f);
    }
    g_strfreev(uris);
}

static gboolean key_press(GtkWidget *, GdkEventKey *ev, gpointer) {
    int cmd = command_of(ev);
    if (!cmd) return FALSE;
    write_ptr(g_x, g_y, g_down, cmd);
    return TRUE;
}

int main(int argc, char **argv) {
    const char *path = "/dev/shm/daw/desk.fb";
    if (argc > 1) path = argv[1];
    int fd = -1;
    for (int i = 0; i < 50 && fd < 0; i++) {
        fd = open(path, O_RDONLY);
        if (fd < 0) usleep(100000);
    }
    if (fd < 0) {
        fprintf(stderr, "desk view: no framebuffer\n");
        return 1;
    }
    void *p = mmap(nullptr, FB_W * FB_H * 4, PROT_READ, MAP_SHARED, fd, 0);
    if (p == MAP_FAILED) {
        fprintf(stderr, "desk view: mmap failed\n");
        return 1;
    }
    g_pix = (uint8_t *)p;
    g_stable = (uint8_t *)malloc(FB_W * FB_H * 4);
    if (!g_stable) return 1;
    memcpy(g_stable, g_pix, FB_W * FB_H * 4);
    g_surf = cairo_image_surface_create_for_data(
        g_stable, CAIRO_FORMAT_RGB24, FB_W, FB_H, FB_W * 4);
    g_fd_ptr = open("/dev/shm/daw/pointer.bin", O_RDWR | O_CREAT, 0644);
    if (g_fd_ptr >= 0) ftruncate(g_fd_ptr, 24);
    gtk_init(&argc, &argv);
    GtkWidget *win = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(win), "DAW");
    gtk_window_set_default_size(GTK_WINDOW(win), FB_W, FB_H);
    gtk_widget_set_app_paintable(win, TRUE);
    g_area = gtk_drawing_area_new();
    gtk_widget_set_size_request(g_area, FB_W, FB_H);
    gtk_widget_set_can_focus(g_area, TRUE);
    GtkTargetEntry drop_types[] = {{(gchar *)"text/uri-list", 0, 0}};
    gtk_drag_dest_set(g_area, GTK_DEST_DEFAULT_ALL, drop_types, 1, GDK_ACTION_COPY);
    g_signal_connect(g_area, "drag-data-received", G_CALLBACK(on_drop), nullptr);
    gtk_widget_add_events(g_area,
        GDK_POINTER_MOTION_MASK | GDK_BUTTON1_MOTION_MASK |
        GDK_BUTTON_PRESS_MASK | GDK_BUTTON_RELEASE_MASK |
        GDK_KEY_PRESS_MASK);
    gtk_container_add(GTK_CONTAINER(win), g_area);
    g_signal_connect(win, "destroy", G_CALLBACK(gtk_main_quit), nullptr);
    g_signal_connect(g_area, "draw", G_CALLBACK(draw), nullptr);
    g_signal_connect(g_area, "motion-notify-event", G_CALLBACK(motion), nullptr);
    g_signal_connect(g_area, "button-press-event", G_CALLBACK(button), nullptr);
    g_signal_connect(g_area, "button-release-event", G_CALLBACK(button), nullptr);
    g_signal_connect(g_area, "key-press-event", G_CALLBACK(key_press), nullptr);
    g_timeout_add(33, tick, nullptr);
    gtk_widget_show_all(win);
    gtk_widget_grab_focus(g_area);
    gtk_main();
    return 0;
}
