/* cad_host_x11 — viewport presenter: keys, LMB orbit/click, scroll zoom
 *
 * Protocol (/tmp/cad_app):
 *   meta.bin frame.raw gen.txt cmd.txt status.txt
 *
 * 3D: LMB drag → orbit dx dy | scroll → zoom | LMB click (no drag) → click x y
 * Sketch: LMB click; scroll zoom; Shift+click multi-pick
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
#include <math.h>
#include <time.h>
/* sys/stat.h already for mkdir + overlay stat */

static char g_dir[512];
static char path_meta[600], path_frame[600], path_gen[600], path_cmd[600], path_status[600];
static char path_parts[600], path_sel[600], path_tool[600];

static void paths_init(const char *dir) {
    snprintf(g_dir, sizeof g_dir, "%s", dir);
    snprintf(path_meta, sizeof path_meta, "%s/meta.bin", dir);
    snprintf(path_frame, sizeof path_frame, "%s/frame.raw", dir);
    snprintf(path_gen, sizeof path_gen, "%s/gen.txt", dir);
    snprintf(path_cmd, sizeof path_cmd, "%s/cmd.txt", dir);
    snprintf(path_status, sizeof path_status, "%s/status.txt", dir);
    snprintf(path_parts, sizeof path_parts, "%s/parts.txt", dir);
    snprintf(path_sel, sizeof path_sel, "%s/sel.txt", dir);
    snprintf(path_tool, sizeof path_tool, "%s/tool.txt", dir);
}

/* tool.txt: mode tool nclick dirty [cstr npick] — mode 1 = sketch
 * Also true when nclick>0 so rubber-band hover is sent during Arc3/line placement. */
static int sketch_mode(void) {
    FILE *f = fopen(path_tool, "r");
    if (!f) return 0;
    int mode = 0, tool = 0, nclick = 0, dirty = 0, cstr = 0, np = 0;
    int n = fscanf(f, "%d %d %d %d %d %d", &mode, &tool, &nclick, &dirty, &cstr, &np);
    fclose(f);
    if (n < 4) return 0;
    return mode == 1;
}

/* nclick from tool.txt — host sends hover whenever placing (nclick>0) */
static int tool_nclick(void) {
    FILE *f = fopen(path_tool, "r");
    if (!f) return 0;
    int mode = 0, tool = 0, nclick = 0, dirty = 0;
    if (fscanf(f, "%d %d %d %d", &mode, &tool, &nclick, &dirty) < 4) nclick = 0;
    fclose(f);
    return nclick;
}

/* Draw left-side part list overlay from parts.txt + sel.txt */
static void draw_parts_overlay(Display *dpy, Window win, GC gc, int ox, int oy) {
    FILE *f = fopen(path_parts, "r");
    if (!f) return;
    int sel = 0;
    FILE *sf = fopen(path_sel, "r");
    if (sf) {
        if (fscanf(sf, "%d", &sel) != 1) sel = 0;
        fclose(sf);
    }
    XSetForeground(dpy, gc, 0x101018);
    XFillRectangle(dpy, win, gc, ox + 8, oy + 8, 200, 220);
    XSetForeground(dpy, gc, 0xC0C8D8);
    XDrawRectangle(dpy, win, gc, ox + 8, oy + 8, 200, 220);
    XDrawString(dpy, win, gc, ox + 16, oy + 24, "Parts (f list)", 14);
    char line[128];
    int row = 0;
    while (row < 12 && fgets(line, sizeof line, f)) {
        size_t L = strlen(line);
        while (L && (line[L-1] == '\n' || line[L-1] == '\r')) line[--L] = 0;
        if (!L) continue;
        int y = oy + 44 + row * 16;
        if (row == sel) {
            XSetForeground(dpy, gc, 0x304060);
            XFillRectangle(dpy, win, gc, ox + 12, y - 12, 192, 16);
            XSetForeground(dpy, gc, 0xFFE080);
        } else {
            XSetForeground(dpy, gc, 0xD0D8E8);
        }
        if (L > 28) line[28] = 0;
        XDrawString(dpy, win, gc, ox + 16, y, line, (int)strlen(line));
        row++;
    }
    fclose(f);
    XSetForeground(dpy, gc, 0xA0A8B8);
    XDrawString(dpy, win, gc, ox + 16, oy + 216, "j/i sel  g open  p save", 23);
}

static void write_cmd(const char *s) {
    /* wait briefly so a previous cmd is not overwritten (hover/orbit race) */
    int tries;
    for (tries = 0; tries < 40; tries++) {
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

    Display *dpy = NULL;
    const char *disp = getenv("DISPLAY");
    if (disp && disp[0]) dpy = XOpenDisplay(disp);
    if (!dpy) dpy = XOpenDisplay(":0");
    if (!dpy) dpy = XOpenDisplay(":0.0");
    if (!dpy) {
        fprintf(stderr, "cad_host_x11: cannot open X display\n");
        return 1;
    }
    fprintf(stderr, "cad_host_x11: connected to %s\n", disp && disp[0] ? disp : ":0");

    int screen = DefaultScreen(dpy);
    Window root = RootWindow(dpy, screen);
    int win_w = 800, win_h = 600;
    Window win = XCreateSimpleWindow(dpy, root, 40, 40, win_w, win_h, 1,
                                     BlackPixel(dpy, screen), BlackPixel(dpy, screen));
    XStoreName(dpy, win, "AILang CAD");
    XSelectInput(dpy, win,
                 ExposureMask | KeyPressMask | ButtonPressMask | ButtonReleaseMask |
                 ButtonMotionMask | PointerMotionMask | StructureNotifyMask);
    XMapWindow(dpy, win);

    GC gc = DefaultGC(dpy, screen);
    XImage *ximg = NULL;
    uint8_t *pix = NULL;
    int fw = 0, fh = 0, pitch = 0;
    int last_gen = -1;
    int running = 1;
    int ox = 0, oy = 0;

    int dragging = 0;
    int down_x = 0, down_y = 0;
    int last_x = 0, last_y = 0;
    int moved = 0;
    /* sketch pan: hold LMB ~1s then drag */
    int pan_mode = 0;
    int click_pending = 0;
    int click_sent = 0;
    int click_sh = 0;
    struct timespec down_ts;
    /* accumulate orbit/zoom/pan so intermediate motion is not lost while kernel polls */
    int pend_ox = 0, pend_oy = 0, pend_zoom = 0;
    int pend_panx = 0, pend_pany = 0;
    int pend_hover = 0, hover_fx = 0, hover_fy = 0;
    int last_hover_fx = -9999, last_hover_fy = -9999;

    fprintf(stderr,
        "cad_host_x11: %s\n"
        "  3D: LMB orbit | scroll zoom\n"
        "  Sketch: click | hold 1s+drag=pan | scroll zoom | Shift multi-pick\n"
        "  FILE: f=list  j/i=sel  g=open  p=save  n=new  k=close\n"
        "  EDIT: m sketch | l/e/c tools | r pad | u cut | o reload DXF\n"
        "  VIEW: 1-3 | [ ] H | w wire | s STEP | b BMP | q quit\n", dir);

    /* GC with font for list overlay */
    XFontStruct *font = XLoadQueryFont(dpy, "fixed");
    if (font) XSetFont(dpy, gc, font->fid);

    while (running) {
        while (XPending(dpy)) {
            XEvent ev;
            XNextEvent(dpy, &ev);
            if (ev.type == KeyPress) {
                KeySym ks = XLookupKeysym(&ev.xkey, 0);
                if (ks == XK_q || ks == XK_Escape) { write_cmd("quit"); running = 0; }
                else if (ks == XK_r || ks == XK_R) write_cmd("repad");
                else if (ks == XK_Return) write_cmd("open"); /* open selection / load */
                else if (ks == XK_u || ks == XK_U) write_cmd("cut");
                else if (ks == XK_o || ks == XK_O) write_cmd("reload");
                else if (ks == XK_p || ks == XK_P) write_cmd("p");
                else if (ks == XK_g || ks == XK_G) write_cmd("g");
                else if (ks == XK_f || ks == XK_F) write_cmd("f");      /* list parts */
                else if (ks == XK_j || ks == XK_J || ks == XK_Down) write_cmd("j"); /* sel next */
                else if (ks == XK_i || ks == XK_I || ks == XK_Up) write_cmd("i");   /* sel prev */
                else if (ks == XK_k || ks == XK_K) write_cmd("k");      /* close doc */
                else if (ks == XK_w || ks == XK_W) write_cmd("wire");
                else if (ks == XK_s || ks == XK_S) write_cmd("step");
                else if (ks == XK_b || ks == XK_B) write_cmd("bmp");
                else if (ks == XK_m || ks == XK_M || ks == XK_Tab) write_cmd("mode");
                else if (ks == XK_l || ks == XK_L) write_cmd("tool_line");
                else if (ks == XK_e || ks == XK_E) write_cmd("tool_rect");
                else if (ks == XK_c || ks == XK_C) write_cmd("tool_circ");
                else if (ks == XK_a || ks == XK_A) write_cmd("tool_arc");
                else if (ks == XK_period) write_cmd("tool_point"); /* place Point */
                else if (ks == XK_z || ks == XK_Z) write_cmd("solve"); /* run constraints */
                else if (ks == XK_y || ks == XK_Y) write_cmd("y"); /* next profile */
                else if (ks == XK_n || ks == XK_N) write_cmd("newdoc");
                else if (ks == XK_x || ks == XK_X) write_cmd("dxf");
                else if (ks == XK_1) write_cmd("view0");
                else if (ks == XK_2) write_cmd("view1");
                else if (ks == XK_3) write_cmd("view2");
                else if (ks == XK_bracketleft || ks == XK_minus) write_cmd("hdec");
                else if (ks == XK_bracketright || ks == XK_plus || ks == XK_equal) write_cmd("hinc");
            } else if (ev.type == ButtonPress) {
                int mx = ev.xbutton.x, my = ev.xbutton.y;
                int fx = mx - ox, fy = my - oy;
                if (ev.xbutton.button == Button1) {
                    dragging = 1;
                    moved = 0;
                    pan_mode = 0;
                    click_pending = 0;
                    click_sent = 0;
                    down_x = last_x = fx;
                    down_y = last_y = fy;
                    clock_gettime(CLOCK_MONOTONIC, &down_ts);
                    /* sketch: defer click — hold ~1s then drag = pan; short click = place */
                    if (sketch_mode() && fx >= 0 && fy >= 0 && (fw <= 0 || (fx < fw && fy < fh))) {
                        click_pending = 1;
                        click_sh = (ev.xbutton.state & ShiftMask) ? 1 : 0;
                    }
                } else if (ev.xbutton.button == Button3) {
                    /* RMB = cancel in-progress sketch tool */
                    write_cmd("cancel");
                } else if (ev.xbutton.button == Button4) {
                    pend_zoom += 1;
                } else if (ev.xbutton.button == Button5) {
                    pend_zoom -= 1;
                }
            } else if (ev.type == MotionNotify) {
                int fx = ev.xmotion.x - ox;
                int fy = ev.xmotion.y - oy;
                if (dragging && (ev.xmotion.state & Button1Mask)) {
                    int dx = fx - last_x;
                    int dy = fy - last_y;
                    if (dx || dy) {
                        int adx = abs(fx - down_x), ady = abs(fy - down_y);
                        if (adx >= 3 || ady >= 3) moved = 1;
                        if (sketch_mode()) {
                            struct timespec now;
                            clock_gettime(CLOCK_MONOTONIC, &now);
                            long ms = (now.tv_sec - down_ts.tv_sec) * 1000L
                                    + (now.tv_nsec - down_ts.tv_nsec) / 1000000L;
                            /* hold ~0.8s without having started a tool click → pan mode */
                            if (!pan_mode && !click_sent && ms >= 800) {
                                pan_mode = 1;
                                click_pending = 0; /* cancel deferred click */
                            }
                            /* moved before hold timer: commit click for tool drag */
                            if (!pan_mode && moved && click_pending && !click_sent) {
                                char cmd[64];
                                snprintf(cmd, sizeof cmd, "click %d %d %d", down_x, down_y, click_sh);
                                write_cmd(cmd);
                                click_sent = 1;
                                click_pending = 0;
                            }
                            if (pan_mode) {
                                pend_panx += dx;
                                pend_pany += dy;
                                last_x = fx;
                                last_y = fy;
                            } else {
                                /* rubber-band hover after first click committed */
                                if (abs(fx - last_hover_fx) >= 1 || abs(fy - last_hover_fy) >= 1) {
                                    pend_hover = 1;
                                    hover_fx = fx;
                                    hover_fy = fy;
                                    last_hover_fx = fx;
                                    last_hover_fy = fy;
                                }
                            }
                        } else {
                            pend_ox += dx;
                            pend_oy += dy;
                            last_x = fx;
                            last_y = fy;
                        }
                    }
                } else if (!dragging) {
                    /* free hover for rubber-band (Arc3/line need this after each click) */
                    if (sketch_mode()) {
                        int need = (tool_nclick() > 0) ? 1 : 2;
                        if (abs(fx - last_hover_fx) >= need || abs(fy - last_hover_fy) >= need) {
                            if (fx >= 0 && fy >= 0 && (fw <= 0 || (fx < fw && fy < fh))) {
                                pend_hover = 1;
                                hover_fx = fx;
                                hover_fy = fy;
                                last_hover_fx = fx;
                                last_hover_fy = fy;
                            }
                        }
                    }
                }
            } else if (ev.type == ButtonRelease) {
                if (ev.xbutton.button == Button1 && dragging) {
                    int fx = ev.xbutton.x - ox;
                    int fy = ev.xbutton.y - oy;
                    int adx = abs(fx - down_x), ady = abs(fy - down_y);
                    dragging = 0;
                    if (sketch_mode()) {
                        if (pan_mode) {
                            /* end pan — no click */
                            pan_mode = 0;
                        } else if (fx >= 0 && fy >= 0 && (fw <= 0 || (fx < fw && fy < fh))) {
                            if (click_pending && !click_sent) {
                                /* pure short click */
                                char cmd[64];
                                snprintf(cmd, sizeof cmd, "click %d %d %d", down_x, down_y, click_sh);
                                write_cmd(cmd);
                                click_sent = 1;
                                click_pending = 0;
                            } else if (click_sent && (moved || adx >= 3 || ady >= 3)) {
                                /* second click for drag tools (radius / end) */
                                char cmd[64];
                                int sh = (ev.xbutton.state & ShiftMask) ? 1 : 0;
                                snprintf(cmd, sizeof cmd, "click %d %d %d", fx, fy, sh);
                                write_cmd(cmd);
                            }
                        }
                        click_pending = 0;
                    } else {
                        /* 3D: click if little movement */
                        if (!moved && adx < 4 && ady < 4) {
                            if (fx >= 0 && fy >= 0 && fx < fw && fy < fh) {
                                char cmd[64];
                                snprintf(cmd, sizeof cmd, "click %d %d", fx, fy);
                                write_cmd(cmd);
                            }
                        }
                    }
                }
            } else if (ev.type == ConfigureNotify) {
                win_w = ev.xconfigure.width;
                win_h = ev.xconfigure.height;
            }
        }

        /* flush pending orbit/zoom only when cmd slot is free (empty or missing) */
        {
            int cmd_busy = 0;
            FILE *cf = fopen(path_cmd, "r");
            if (cf) {
                int c = fgetc(cf);
                if (c != EOF && c != '\n' && c != '\r') cmd_busy = 1;
                fclose(cf);
            }
            if (!cmd_busy) {
                if (pend_ox || pend_oy) {
                    char cmd[64];
                    snprintf(cmd, sizeof cmd, "orbit %d %d", pend_ox, pend_oy);
                    write_cmd(cmd);
                    pend_ox = pend_oy = 0;
                } else if (pend_panx || pend_pany) {
                    char cmd[64];
                    snprintf(cmd, sizeof cmd, "pan %d %d", pend_panx, pend_pany);
                    write_cmd(cmd);
                    pend_panx = pend_pany = 0;
                } else if (pend_zoom) {
                    char cmd[64];
                    snprintf(cmd, sizeof cmd, "zoom %d", pend_zoom);
                    write_cmd(cmd);
                    pend_zoom = 0;
                } else if (pend_hover) {
                    char cmd[64];
                    snprintf(cmd, sizeof cmd, "hover %d %d", hover_fx, hover_fy);
                    write_cmd(cmd);
                    pend_hover = 0;
                }
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
                fprintf(stderr, "cad_host_x11: frame gen=%d %dx%d pitch=%d\n",
                        gen, fw, fh, pitch);
                if (ximg) { ximg->data = NULL; XDestroyImage(ximg); ximg = NULL; }
                ximg = XCreateImage(dpy, DefaultVisual(dpy, screen),
                                    DefaultDepth(dpy, screen), ZPixmap, 0,
                                    (char *)pix, fw, fh, 32, pitch);
                if (ximg) {
                    ximg->byte_order = LSBFirst;
                    ximg->bitmap_bit_order = LSBFirst;
                    ximg->bits_per_pixel = 32;
                    ximg->bytes_per_line = pitch;
                    ximg->red_mask = 0xFF0000;
                    ximg->green_mask = 0x00FF00;
                    ximg->blue_mask = 0x0000FF;
                }
                char st[256];
                read_status(st, sizeof st);
                char title[320];
                if (st[0])
                    snprintf(title, sizeof title, "AILang CAD — %s", st);
                else
                    snprintf(title, sizeof title, "AILang CAD — gen %d", gen);
                XStoreName(dpy, win, title);
                XClearWindow(dpy, win);
            }
        }

        if (ximg && pix) {
            ox = (win_w - fw) / 2;
            oy = (win_h - fh) / 2;
            if (ox < 0) ox = 0;
            if (oy < 0) oy = 0;
            XPutImage(dpy, win, gc, ximg, 0, 0, ox, oy, fw, fh);
            /* part list overlay when parts.txt exists and non-empty */
            {
                struct stat st;
                if (stat(path_parts, &st) == 0 && st.st_size > 0)
                    draw_parts_overlay(dpy, win, gc, ox, oy);
            }
        }
        XFlush(dpy);
        usleep(12000);
    }

    if (font) XFreeFont(dpy, font);
    if (ximg) { ximg->data = NULL; XDestroyImage(ximg); }
    free(pix);
    XDestroyWindow(dpy, win);
    XCloseDisplay(dpy);
    return 0;
}
