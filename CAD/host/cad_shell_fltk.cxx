/* cad_shell_fltk — FLTK presenter for AILang CAD
 *
 * Chrome only: menubar, HUD, status. Viewport blits kernel frame.raw.
 * Kernel never links FLTK. Protocol: /tmp/cad_app/* (same as cad_host_x11).
 *
 * Build (local FLTK under third_party/fltk):
 *   FLTK_CFG=third_party/fltk/bin/fltk-config
 *   g++ -O2 -o CAD/host/cad_shell_fltk CAD/host/cad_shell_fltk.cxx \
 *       $($FLTK_CFG --cxxflags) $($FLTK_CFG --ldflags --use-images)
 */
#include <FL/Fl.H>
#include <FL/Fl_Double_Window.H>
#include <FL/Fl_Menu_Bar.H>
#include <FL/Fl_Box.H>
#include <FL/Fl_Widget.H>
#include <FL/fl_draw.H>
#include <FL/Fl_Native_File_Chooser.H>
#include <FL/Fl_File_Chooser.H>
#include <FL/fl_ask.H>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <stdint.h>
#include <math.h>
#include <time.h>
#include <errno.h>

static char g_dir[512];
static char path_meta[600], path_frame[600], path_gen[600], path_cmd[600];
static char path_status[600], path_parts[600], path_sel[600], path_tool[600];
static char path_hud[600], path_path[600];

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
    snprintf(path_hud, sizeof path_hud, "%s/hud.txt", dir);
    snprintf(path_path, sizeof path_path, "%s/path.txt", dir);
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

static int sketch_mode(void) {
    FILE *f = fopen(path_tool, "r");
    if (!f) return 0;
    int mode = 0, tool = 0, nclick = 0, dirty = 0;
    int n = fscanf(f, "%d %d %d %d", &mode, &tool, &nclick, &dirty);
    fclose(f);
    if (n < 4) return 0;
    return mode == 1;
}

static int tool_nclick(void) {
    FILE *f = fopen(path_tool, "r");
    if (!f) return 0;
    int mode = 0, tool = 0, nclick = 0, dirty = 0;
    if (fscanf(f, "%d %d %d %d", &mode, &tool, &nclick, &dirty) < 4) nclick = 0;
    fclose(f);
    return nclick;
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

static void write_path_and_import(const char *path) {
    FILE *f = fopen(path_path, "w");
    if (!f) return;
    fputs(path, f);
    fputc('\n', f);
    fclose(f);
    write_cmd("import");
}

/* Read current pad_H from hud.txt (kernel-owned). Default 10. */
static int read_pad_height_mm(void) {
    char line[256];
    read_line_file(path_hud, line, sizeof line);
    const char *p = strstr(line, "pad_H=");
    if (!p) return 10;
    int h = atoi(p + 6);
    if (h < 1) h = 10;
    if (h > 10000) h = 10000;
    return h;
}

/* Prompt for mm height; returns 1 and fills out if user OK. */
static int prompt_height_mm(const char *title, int *out) {
    char def[32];
    snprintf(def, sizeof def, "%d", read_pad_height_mm());
    /* fl_input label is printf-style; pass via %s to avoid format warning */
    const char *s = fl_input("%s", def, title);
    if (!s || !s[0]) return 0;
    int h = atoi(s);
    if (h < 1) h = 1;
    if (h > 10000) h = 10000;
    *out = h;
    return 1;
}

/* Set height then optional follow-up cmd (repad/cut) after slot free. */
static void height_then_cmd(const char *follow) {
    int h = 0;
    const char *title = follow && strcmp(follow, "cut") == 0
        ? "Cut depth (mm):"
        : "Pad / extrude height (mm):";
    if (!prompt_height_mm(title, &h)) return;
    char c[48];
    snprintf(c, sizeof c, "height %d", h);
    write_cmd(c);
    if (!follow || !follow[0]) return;
    for (int t = 0; t < 80; t++) {
        FILE *cf = fopen(path_cmd, "r");
        int busy = 0;
        if (cf) {
            int ch = fgetc(cf);
            if (ch != EOF && ch != '\n' && ch != '\r') busy = 1;
            fclose(cf);
        }
        if (!busy) break;
        usleep(5000);
    }
    write_cmd(follow);
}

/* ---------- Viewport widget ---------- */

class Viewport : public Fl_Widget {
public:
    uint8_t *pix;
    int fw, fh, pitch;
    int last_gen;
    int ox, oy;
    int dragging, moved, pan_mode;
    int down_x, down_y, last_x, last_y;
    int click_pending, click_sent, click_sh;
    struct timespec down_ts;
    int pend_ox, pend_oy, pend_zoom;
    int pend_panx, pend_pany;
    int pend_hover, hover_fx, hover_fy;
    int last_hover_fx, last_hover_fy;
    char hud_line[256];
    char status_line[256];

    Viewport(int X, int Y, int W, int H)
        : Fl_Widget(X, Y, W, H),
          pix(NULL), fw(0), fh(0), pitch(0), last_gen(-1),
          ox(0), oy(0),
          dragging(0), moved(0), pan_mode(0),
          down_x(0), down_y(0), last_x(0), last_y(0),
          click_pending(0), click_sent(0), click_sh(0),
          pend_ox(0), pend_oy(0), pend_zoom(0),
          pend_panx(0), pend_pany(0),
          pend_hover(0), hover_fx(0), hover_fy(0),
          last_hover_fx(-9999), last_hover_fy(-9999) {
        hud_line[0] = 0;
        status_line[0] = 0;
        box(FL_FLAT_BOX);
        color(fl_rgb_color(18, 20, 28));
    }

    ~Viewport() { free(pix); }

    void poll_frame() {
        int gen = read_gen();
        if (gen >= 0 && gen != last_gen) {
            uint8_t *np = NULL;
            int nw, nh, npitch;
            if (load_frame(&np, &nw, &nh, &npitch) == 0) {
                free(pix);
                pix = np;
                fw = nw; fh = nh; pitch = npitch;
                last_gen = gen;
                read_line_file(path_hud, hud_line, sizeof hud_line);
                read_line_file(path_status, status_line, sizeof status_line);
                redraw();
            }
        } else {
            /* refresh HUD/status even without new frame */
            char h[256], s[256];
            read_line_file(path_hud, h, sizeof h);
            read_line_file(path_status, s, sizeof s);
            if (strcmp(h, hud_line) || strcmp(s, status_line)) {
                snprintf(hud_line, sizeof hud_line, "%s", h);
                snprintf(status_line, sizeof status_line, "%s", s);
                redraw();
            }
        }
        flush_pending();
    }

    void flush_pending() {
        int cmd_busy = 0;
        FILE *cf = fopen(path_cmd, "r");
        if (cf) {
            int c = fgetc(cf);
            if (c != EOF && c != '\n' && c != '\r') cmd_busy = 1;
            fclose(cf);
        }
        if (cmd_busy) return;
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

    void draw() override {
        fl_rectf(x(), y(), w(), h(), fl_rgb_color(18, 20, 28));
        if (pix && fw > 0 && fh > 0) {
            ox = (w() - fw) / 2;
            oy = (h() - fh) / 2;
            if (ox < 0) ox = 0;
            if (oy < 0) oy = 0;
            /* frame.raw is BGRA/ARGB little-endian 32bpp; FLTK wants RGB */
            fl_push_clip(x(), y(), w(), h());
            for (int row = 0; row < fh; row++) {
                if (oy + row < 0 || oy + row >= h()) continue;
                const uint8_t *src = pix + (size_t)row * (size_t)pitch;
                /* draw scanline via fl_draw_image with BGR→RGB */
                static uint8_t linebuf[8192 * 3];
                int maxw = fw;
                if (maxw > 8192) maxw = 8192;
                for (int col = 0; col < maxw; col++) {
                    const uint8_t *p = src + col * 4;
                    /* X11 host used R=0xFF0000 G=0x00FF00 B=0x0000FF → BGRA layout */
                    linebuf[col * 3 + 0] = p[2]; /* R */
                    linebuf[col * 3 + 1] = p[1]; /* G */
                    linebuf[col * 3 + 2] = p[0]; /* B */
                }
                fl_draw_image(linebuf, x() + ox, y() + oy + row, maxw, 1, 3, 0);
            }
            fl_pop_clip();
        }

        /* HUD upper-right */
        if (hud_line[0]) {
            fl_font(FL_HELVETICA, 12);
            int tw = 0, th = 0;
            fl_measure(hud_line, tw, th);
            int hx = x() + w() - tw - 16;
            int hy = y() + 8;
            if (hx < x() + 8) hx = x() + 8;
            fl_color(fl_rgb_color(16, 20, 28));
            fl_rectf(hx - 6, hy - 2, tw + 12, th + 8);
            fl_color(fl_rgb_color(200, 220, 255));
            fl_draw(hud_line, hx, hy + th);
        }

        /* parts list overlay (left) when non-empty */
        {
            struct stat st;
            if (stat(path_parts, &st) == 0 && st.st_size > 0) {
                FILE *f = fopen(path_parts, "r");
                if (f) {
                    int sel = 0;
                    FILE *sf = fopen(path_sel, "r");
                    if (sf) {
                        if (fscanf(sf, "%d", &sel) != 1) sel = 0;
                        fclose(sf);
                    }
                    int lx = x() + ox + 8;
                    int ly = y() + oy + 8;
                    fl_color(fl_rgb_color(16, 16, 24));
                    fl_rectf(lx, ly, 200, 200);
                    fl_color(fl_rgb_color(192, 200, 216));
                    fl_rect(lx, ly, 200, 200);
                    fl_font(FL_HELVETICA, 11);
                    fl_draw("Parts (File → List)", lx + 8, ly + 16);
                    char line[128];
                    int row = 0;
                    while (row < 10 && fgets(line, sizeof line, f)) {
                        size_t L = strlen(line);
                        while (L && (line[L - 1] == '\n' || line[L - 1] == '\r')) line[--L] = 0;
                        if (!L) continue;
                        int yy = ly + 36 + row * 15;
                        if (row == sel) {
                            fl_color(fl_rgb_color(48, 64, 96));
                            fl_rectf(lx + 4, yy - 11, 192, 14);
                            fl_color(fl_rgb_color(255, 224, 128));
                        } else {
                            fl_color(fl_rgb_color(208, 216, 232));
                        }
                        if (L > 28) line[28] = 0;
                        fl_draw(line, lx + 8, yy);
                        row++;
                    }
                    fclose(f);
                }
            }
        }
    }

    int handle(int ev) override {
        int mx = Fl::event_x() - x();
        int my = Fl::event_y() - y();
        int fx = mx - ox;
        int fy = my - oy;

        switch (ev) {
        case FL_PUSH:
            take_focus();
            if (Fl::event_button() == FL_LEFT_MOUSE) {
                dragging = 1;
                moved = 0;
                pan_mode = 0;
                click_pending = 0;
                click_sent = 0;
                down_x = last_x = fx;
                down_y = last_y = fy;
                clock_gettime(CLOCK_MONOTONIC, &down_ts);
                if (sketch_mode() && fx >= 0 && fy >= 0 && (fw <= 0 || (fx < fw && fy < fh))) {
                    click_pending = 1;
                    click_sh = Fl::event_shift() ? 1 : 0;
                }
                return 1;
            }
            if (Fl::event_button() == FL_RIGHT_MOUSE) {
                write_cmd("cancel");
                return 1;
            }
            return 1;
        case FL_DRAG:
            if (dragging && (Fl::event_state() & FL_BUTTON1)) {
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
                        if (!pan_mode && !click_sent && ms >= 800) {
                            pan_mode = 1;
                            click_pending = 0;
                        }
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
                        } else if (abs(fx - last_hover_fx) >= 1 || abs(fy - last_hover_fy) >= 1) {
                            pend_hover = 1;
                            hover_fx = fx;
                            hover_fy = fy;
                            last_hover_fx = fx;
                            last_hover_fy = fy;
                        }
                    } else {
                        pend_ox += dx;
                        pend_oy += dy;
                        last_x = fx;
                        last_y = fy;
                    }
                }
                return 1;
            }
            return 1;
        case FL_RELEASE:
            if (Fl::event_button() == FL_LEFT_MOUSE && dragging) {
                int adx = abs(fx - down_x), ady = abs(fy - down_y);
                dragging = 0;
                if (sketch_mode()) {
                    if (pan_mode) {
                        pan_mode = 0;
                    } else if (fx >= 0 && fy >= 0 && (fw <= 0 || (fx < fw && fy < fh))) {
                        if (click_pending && !click_sent) {
                            char cmd[64];
                            snprintf(cmd, sizeof cmd, "click %d %d %d", down_x, down_y, click_sh);
                            write_cmd(cmd);
                            click_sent = 1;
                            click_pending = 0;
                        } else if (click_sent && (moved || adx >= 3 || ady >= 3)) {
                            char cmd[64];
                            int sh = Fl::event_shift() ? 1 : 0;
                            snprintf(cmd, sizeof cmd, "click %d %d %d", fx, fy, sh);
                            write_cmd(cmd);
                        }
                    }
                    click_pending = 0;
                } else {
                    if (!moved && adx < 4 && ady < 4) {
                        if (fx >= 0 && fy >= 0 && fx < fw && fy < fh) {
                            char cmd[64];
                            snprintf(cmd, sizeof cmd, "click %d %d", fx, fy);
                            write_cmd(cmd);
                        }
                    }
                }
                return 1;
            }
            return 1;
        case FL_MOUSEWHEEL: {
            int dy = Fl::event_dy();
            if (dy < 0) pend_zoom += 1;
            else if (dy > 0) pend_zoom -= 1;
            return 1;
        }
        case FL_MOVE:
            if (!dragging && sketch_mode()) {
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
            return 1;
        case FL_FOCUS:
        case FL_UNFOCUS:
            return 1;
        case FL_KEYDOWN: {
            int k = Fl::event_key();
            if (k == 'q' || k == FL_Escape) { write_cmd("quit"); return 1; }
            if (k == 'r') { height_then_cmd("repad"); return 1; }
            if (k == FL_Enter) { write_cmd("open"); return 1; }
            if (k == 'u') { write_cmd("cut"); return 1; }
            if (k == 'o') { write_cmd("reload"); return 1; }
            if (k == 'p') { write_cmd("p"); return 1; }
            if (k == 'g') { write_cmd("g"); return 1; }
            if (k == 'f') { write_cmd("f"); return 1; }
            if (k == 'j' || k == FL_Down) { write_cmd("j"); return 1; }
            if (k == 'i' || k == FL_Up) { write_cmd("i"); return 1; }
            if (k == 'k') { write_cmd("k"); return 1; }
            if (k == 'w') { write_cmd("wire"); return 1; }
            if (k == 's') { write_cmd("step"); return 1; }
            if (k == 'b') { write_cmd("bmp"); return 1; }
            if (k == 'm' || k == FL_Tab) { write_cmd("mode"); return 1; }
            if (k == 'l') { write_cmd("tool_line"); return 1; }
            if (k == 'e') { write_cmd("tool_rect"); return 1; }
            if (k == 'c') { write_cmd("tool_circ"); return 1; }
            if (k == 'a') { write_cmd("tool_arc"); return 1; }
            if (k == '.') { write_cmd("tool_point"); return 1; }
            if (k == 'z') { write_cmd("solve"); return 1; }
            if (k == 'y') { write_cmd("y"); return 1; }
            if (k == 'n') { write_cmd("newdoc"); return 1; }
            if (k == 'x') { write_cmd("dxf"); return 1; }
            if (k == '1') { write_cmd("view0"); return 1; }
            if (k == '2') { write_cmd("view1"); return 1; }
            if (k == '3') { write_cmd("view2"); return 1; }
            if (k == '[' || k == '-') { write_cmd("hdec"); return 1; }
            if (k == ']' || k == '=' || k == '+') { write_cmd("hinc"); return 1; }
            return 0;
        }
        default:
            break;
        }
        return Fl_Widget::handle(ev);
    }
};

/* ---------- App shell ---------- */

static Viewport *g_vp = NULL;
static Fl_Box *g_status = NULL;
static Fl_Double_Window *g_win = NULL;

static void on_timer(void *) {
    if (g_vp) g_vp->poll_frame();
    if (g_status && g_vp && g_vp->status_line[0]) {
        char buf[320];
        snprintf(buf, sizeof buf, "  %s", g_vp->status_line);
        if (strcmp(g_status->label() ? g_status->label() : "", buf) != 0) {
            g_status->copy_label(buf);
            g_status->redraw();
        }
    }
    Fl::repeat_timeout(0.012, on_timer);
}

static void menu_cb(Fl_Widget *, void *v) {
    const char *cmd = (const char *)v;
    if (!cmd) return;
    if (strcmp(cmd, "file_open_dxf") == 0) {
        Fl_Native_File_Chooser ch;
        ch.title("Open DXF");
        ch.type(Fl_Native_File_Chooser::BROWSE_FILE);
        ch.filter("DXF\t*.dxf\nAll\t*");
        if (ch.show() == 0 && ch.filename()) {
            write_path_and_import(ch.filename());
        }
        return;
    }
    if (strcmp(cmd, "file_save_as_name") == 0) {
        const char *name = fl_input("Part name (Postgres save):", "part");
        if (name && name[0]) {
            FILE *f = fopen(path_path, "w");
            if (f) {
                fputs(name, f);
                fputc('\n', f);
                fclose(f);
            }
            write_cmd("save");
        }
        return;
    }
    if (strcmp(cmd, "file_export_step") == 0) {
        write_cmd("step");
        return;
    }
    if (strcmp(cmd, "file_screenshot") == 0) {
        write_cmd("shot");
        return;
    }
    if (strcmp(cmd, "feature_pad") == 0) {
        height_then_cmd("repad");
        return;
    }
    if (strcmp(cmd, "feature_height") == 0) {
        height_then_cmd(NULL);
        return;
    }
    if (strcmp(cmd, "feature_cut") == 0) {
        height_then_cmd("cut");
        return;
    }
    write_cmd(cmd);
}

static void build_menu(Fl_Menu_Bar *m) {
    m->add("File/New",        FL_CTRL + 'n', menu_cb, (void *)"newdoc");
    m->add("File/Open DXF...", FL_CTRL + 'o', menu_cb, (void *)"file_open_dxf");
    m->add("File/List parts", 0, menu_cb, (void *)"f");
    m->add("File/Open selected", 0, menu_cb, (void *)"open");
    m->add("File/Save (repo)", FL_CTRL + 's', menu_cb, (void *)"p");
    m->add("File/Close", 0, menu_cb, (void *)"k");
    m->add("File/Reload DXF", 0, menu_cb, (void *)"reload");
    m->add("File/Export STEP", 0, menu_cb, (void *)"file_export_step");
    m->add("File/Screenshot", FL_CTRL + FL_SHIFT + 's', menu_cb, (void *)"file_screenshot");
    m->add("File/Quit", FL_CTRL + 'q', menu_cb, (void *)"quit");

    m->add("Sketch/Toggle 3D", FL_Tab, menu_cb, (void *)"mode");
    m->add("Sketch/Line", 0, menu_cb, (void *)"tool_line");
    m->add("Sketch/Rect", 0, menu_cb, (void *)"tool_rect");
    m->add("Sketch/Circle", 0, menu_cb, (void *)"tool_circ");
    m->add("Sketch/Arc", 0, menu_cb, (void *)"tool_arc");
    m->add("Sketch/Arc3", 0, menu_cb, (void *)"tool_3pt");
    m->add("Sketch/Point", 0, menu_cb, (void *)"tool_point");
    m->add("Sketch/Trim", 0, menu_cb, (void *)"tool_trim");
    m->add("Sketch/Pick", 0, menu_cb, (void *)"tool_pick");
    m->add("Sketch/Fillet", 0, menu_cb, (void *)"tool_fillet");
    m->add("Sketch/Profiles", 0, menu_cb, (void *)"profiles");
    m->add("Sketch/Next profile", 0, menu_cb, (void *)"y");
    m->add("Sketch/Solve", 0, menu_cb, (void *)"solve");
    m->add("Sketch/Cancel", 0, menu_cb, (void *)"cancel");
    m->add("Sketch/Mirror across X (y→-y)", 0, menu_cb, (void *)"mirror_x");
    m->add("Sketch/Mirror across Y (x→-x)", 0, menu_cb, (void *)"mirror_y");

    m->add("Plane/On face (OnTop)", 0, menu_cb, (void *)"plane_top");
    m->add("Plane/XY", 0, menu_cb, (void *)"plane_xy");
    m->add("Plane/XZ", 0, menu_cb, (void *)"plane_xz");
    m->add("Plane/YZ", 0, menu_cb, (void *)"plane_yz");
    m->add("Plane/Offset 50", 0, menu_cb, (void *)"plane_off 50");
    m->add("Plane/Flip", 0, menu_cb, (void *)"plane_flip");
    m->add("Plane/Angle 90", 0, menu_cb, (void *)"plane_ang 90");
    m->add("Plane/Sketch on plane", 0, menu_cb, (void *)"sketch_pln");

    m->add("Feature/Pad...", FL_CTRL + 'r', menu_cb, (void *)"feature_pad");
    m->add("Feature/Pad now (current H)", 0, menu_cb, (void *)"repad");
    m->add("Feature/Set height...", FL_CTRL + 'h', menu_cb, (void *)"feature_height");
    m->add("Feature/Height +1 mm", 0, menu_cb, (void *)"hinc");
    m->add("Feature/Height -1 mm", 0, menu_cb, (void *)"hdec");
    m->add("Feature/Revolve", 0, menu_cb, (void *)"revolve");
    m->add("Feature/Cut...", 0, menu_cb, (void *)"feature_cut");
    m->add("Feature/Cut now (current H)", 0, menu_cb, (void *)"cut");
    m->add("Feature/Clear model", 0, menu_cb, (void *)"clear");

    m->add("View/Iso", 0, menu_cb, (void *)"view0");
    m->add("View/Top", 0, menu_cb, (void *)"view1");
    m->add("View/Front", 0, menu_cb, (void *)"view2");
    m->add("View/Wireframe", 0, menu_cb, (void *)"wire");
    m->add("View/Grid toggle", 0, menu_cb, (void *)"grid");
    m->add("View/Grid on", 0, menu_cb, (void *)"grid 1");
    m->add("View/Grid off", 0, menu_cb, (void *)"grid 0");
}

int main(int argc, char **argv) {
    const char *dir = "/tmp/cad_app";
    if (argc > 1) dir = argv[1];
    paths_init(dir);
    mkdir(dir, 0755);

    Fl::scheme("gtk+");
    g_win = new Fl_Double_Window(900, 700, "AILang CAD");
    Fl_Menu_Bar *menu = new Fl_Menu_Bar(0, 0, 900, 28);
    build_menu(menu);
    g_vp = new Viewport(0, 28, 900, 700 - 28 - 24);
    g_status = new Fl_Box(0, 700 - 24, 900, 24, "  starting…");
    g_status->box(FL_FLAT_BOX);
    g_status->color(fl_rgb_color(28, 32, 42));
    g_status->labelcolor(fl_rgb_color(180, 190, 210));
    g_status->align(FL_ALIGN_LEFT | FL_ALIGN_INSIDE);
    g_status->labelfont(FL_HELVETICA);
    g_status->labelsize(12);
    g_win->resizable(g_vp);
    g_win->end();
    g_win->show(argc, argv);

    fprintf(stderr,
        "cad_shell_fltk: %s\n"
        "  viewport: LMB orbit/click | scroll zoom | sketch hold-drag=pan | RMB cancel\n"
        "  menus: File Sketch Plane Feature View\n"
        "  IPC drive: echo 'cmd' > %s/cmd.txt ; ./CAD/scripts/cad_shot.sh\n",
        dir, dir);

    Fl::add_timeout(0.05, on_timer);
    return Fl::run();
}
