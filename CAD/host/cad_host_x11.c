/* cad_host_x11 — present ARGB frames from cad_app, send key commands back.
 *
 * Protocol (state directory, default /tmp/cad_app):
 *   meta.bin   3× int32 LE: width, height, pitch
 *   frame.raw  pitch*height bytes ARGB (or XRGB) little-endian
 *   gen.txt    integer generation counter (app writes after each frame)
 *   cmd.txt    host writes one-line command, app reads & truncates
 *   status.txt app writes status line for window title
 *
 * Keys → cmd:
 *   q/Esc quit | r repad | w wire | 1/2/3 view | [ ] height
 *   s save STEP | b save BMP | +/- height fine
 *
 * Build: cc -O2 -o cad_host_x11 cad_host_x11.c -lX11
 */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/keysym.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <stdint.h>
#include <errno.h>

static char g_dir[512];
static char path_meta[600], path_frame[600], path_gen[600], path_cmd[600], path_status[600];

static void paths_init(const char *dir) {
    snprintf(g_dir, sizeof g_dir, "%s", dir);
    snprintf(path_meta, sizeof path_meta, "%s/meta.bin", dir);
    snprintf(path_frame, sizeof path_frame, "%s/frame.raw", dir);
    snprintf(path_gen, sizeof path_gen, "%s/gen.txt", dir);
    snprintf(path_cmd, sizeof path_cmd, "%s/cmd.txt", dir);
    snprintf(path_status, sizeof path_status, "%s/status.txt", dir);
}

static void write_cmd(const char *s) {
    FILE *f = fopen(path_cmd, "w");
    if (!f) return;
    fputs(s, f);
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

static int load_frame(uint8_t **out_pix, int *out_w, int *out_h, int *out_pitch) {
    int fd = open(path_meta, O_RDONLY);
    if (fd < 0) return -1;
    int32_t hdr[3];
    if (read(fd, hdr, 12) != 12) { close(fd); return -1; }
    close(fd);
    int w = hdr[0], h = hdr[1], pitch = hdr[2];
    if (w < 16 || h < 16 || pitch < w * 4) return -1;
    size_t sz = (size_t)pitch * (size_t)h;
    uint8_t *pix = (uint8_t *)malloc(sz);
    if (!pix) return -1;
    fd = open(path_frame, O_RDONLY);
    if (fd < 0) { free(pix); return -1; }
    size_t got = 0;
    while (got < sz) {
        ssize_t n = read(fd, pix + got, sz - got);
        if (n <= 0) break;
        got += (size_t)n;
    }
    close(fd);
    if (got < sz) { free(pix); return -1; }
    *out_pix = pix;
    *out_w = w;
    *out_h = h;
    *out_pitch = pitch;
    return 0;
}

static void read_status(char *buf, size_t n) {
    buf[0] = 0;
    FILE *f = fopen(path_status, "r");
    if (!f) return;
    if (fgets(buf, (int)n, f)) {
        size_t L = strlen(buf);
        while (L && (buf[L-1] == '\n' || buf[L-1] == '\r')) buf[--L] = 0;
    }
    fclose(f);
}

int main(int argc, char **argv) {
    const char *dir = "/tmp/cad_app";
    if (argc > 1) dir = argv[1];
    paths_init(dir);
    mkdir(dir, 0755);

    Display *dpy = XOpenDisplay(NULL);
    if (!dpy) {
        fprintf(stderr, "cad_host_x11: cannot open DISPLAY\n");
        return 1;
    }
    int screen = DefaultScreen(dpy);
    Window root = RootWindow(dpy, screen);
    int win_w = 800, win_h = 600;
    Window win = XCreateSimpleWindow(dpy, root, 40, 40, win_w, win_h, 1,
                                     BlackPixel(dpy, screen), BlackPixel(dpy, screen));
    XStoreName(dpy, win, "AILang CAD");
    XSelectInput(dpy, win, ExposureMask | KeyPressMask | StructureNotifyMask);
    XMapWindow(dpy, win);

    GC gc = DefaultGC(dpy, screen);
    XImage *ximg = NULL;
    uint8_t *pix = NULL;
    int fw = 0, fh = 0, pitch = 0;
    int last_gen = -1;
    int running = 1;

    fprintf(stderr, "cad_host_x11: watching %s  (q quit, r repad, [/] height, w wire, 1-3 view, s STEP, b BMP)\n", dir);

    while (running) {
        while (XPending(dpy)) {
            XEvent ev;
            XNextEvent(dpy, &ev);
            if (ev.type == KeyPress) {
                KeySym ks = XLookupKeysym(&ev.xkey, 0);
                if (ks == XK_q || ks == XK_Escape) { write_cmd("quit"); running = 0; }
                else if (ks == XK_r || ks == XK_R) write_cmd("repad");
                else if (ks == XK_w || ks == XK_W) write_cmd("wire");
                else if (ks == XK_s || ks == XK_S) write_cmd("step");
                else if (ks == XK_b || ks == XK_B) write_cmd("bmp");
                else if (ks == XK_1) write_cmd("view0");
                else if (ks == XK_2) write_cmd("view1");
                else if (ks == XK_3) write_cmd("view2");
                else if (ks == XK_bracketleft || ks == XK_minus) write_cmd("hdec");
                else if (ks == XK_bracketright || ks == XK_plus || ks == XK_equal) write_cmd("hinc");
            } else if (ev.type == ConfigureNotify) {
                win_w = ev.xconfigure.width;
                win_h = ev.xconfigure.height;
            }
        }

        int gen = read_gen();
        if (gen >= 0 && gen != last_gen) {
            uint8_t *np = NULL;
            int nw, nh, npitch;
            if (load_frame(&np, &nw, &nh, &npitch) == 0) {
                free(pix);
                pix = np;
                fw = nw; fh = nh; pitch = npitch;
                last_gen = gen;
                if (ximg) { ximg->data = NULL; XDestroyImage(ximg); ximg = NULL; }
                /* X11 wants ZPixmap 32bpp; our buffer is BGRA/ARGB little-endian on LE */
                ximg = XCreateImage(dpy, DefaultVisual(dpy, screen), 24, ZPixmap, 0,
                                    (char *)pix, fw, fh, 32, pitch);
                if (ximg) {
                    ximg->byte_order = LSBFirst;
                    ximg->bitmap_bit_order = LSBFirst;
                }
                char st[256];
                read_status(st, sizeof st);
                char title[320];
                if (st[0])
                    snprintf(title, sizeof title, "AILang CAD — %s", st);
                else
                    snprintf(title, sizeof title, "AILang CAD — gen %d", gen);
                XStoreName(dpy, win, title);
            }
        }

        if (ximg && pix) {
            /* center if window larger */
            int ox = (win_w - fw) / 2;
            int oy = (win_h - fh) / 2;
            if (ox < 0) ox = 0;
            if (oy < 0) oy = 0;
            XPutImage(dpy, win, gc, ximg, 0, 0, ox, oy, fw, fh);
        }
        XFlush(dpy);
        usleep(16000);
    }

    if (ximg) { ximg->data = NULL; XDestroyImage(ximg); }
    free(pix);
    XDestroyWindow(dpy, win);
    XCloseDisplay(dpy);
    return 0;
}
