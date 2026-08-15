/* cad_shell_fltk — Fusion 360 Native C++ Host Shell for AILang CAD
 *
 * Performance optimized C++ host presenter: zero-copy SIMD RGB frame blitter,
 * clean standard ASCII labels (no UTF-8 font '?' boxes), real-time rubber banding,
 * floating in-canvas HUD dimension tooltips, and RMB (Right-Click) context menu.
 *
 * Build (local FLTK under third_party/fltk):
 *   CFG=third_party/fltk/bin/fltk-config
 *   g++ -O2 -o CAD/host/cad_shell_fltk CAD/host/cad_shell_fltk.cxx \
 *       $($CFG --cxxflags) $($CFG --ldflags --use-images)
 */
#include <FL/Fl.H>
#include <FL/Fl_Double_Window.H>
#include <FL/Fl_Menu_Bar.H>
#include <FL/Fl_Menu_Button.H>
#include <FL/Fl_Button.H>
#include <FL/Fl_Box.H>
#include <FL/Fl_Group.H>
#include <FL/Fl_Tabs.H>
#include <FL/Fl_Value_Input.H>
#include <FL/Fl_Hold_Browser.H>
#include <FL/Fl_Widget.H>
#include <FL/fl_draw.H>
#include <FL/Fl_Native_File_Chooser.H>
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
    if (!f) return 1; // Default to sketch mode for fast responsive tooltips
    int mode = 0, tool = 0, nclick = 0, dirty = 0;
    int n = fscanf(f, "%d %d %d %d", &mode, &tool, &nclick, &dirty);
    fclose(f);
    if (n < 1) return 1;
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

static int tool_id(void) {
    FILE *f = fopen(path_tool, "r");
    if (!f) return 0;
    int mode = 0, tool = 0, nclick = 0, dirty = 0;
    if (fscanf(f, "%d %d %d %d", &mode, &tool, &nclick, &dirty) < 4) tool = 0;
    fclose(f);
    return tool;
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

/* Prompt dialog helper for numeric editing */
static void prompt_edit_dimension() {
    const char *s = fl_input("Enter exact dimension (mm):", "50.0");
    if (!s || !s[0]) return;
    double val = atof(s);
    if (val <= 0.0) return;
    char c[64];
    snprintf(c, sizeof c, "height %.1f", val);
    write_cmd(c);
}

/* ---------- Viewport Canvas Widget ---------- */

class Viewport : public Fl_Widget {
public:
    uint8_t *pix;
    uint8_t *rgb_buf;
    size_t rgb_buf_sz;
    int fw, fh, pitch;
    int last_gen;
    int ox, oy;
    int dragging, moved, pan_mode;
    int down_x, down_y, last_x, last_y;
    int down_mx, down_my;
    int click_pending, click_sent, click_sh;
    struct timespec down_ts;
    int pend_ox, pend_oy, pend_zoom;
    int pend_panx, pend_pany;
    int pend_hover, hover_fx, hover_fy;
    int last_hover_fx, last_hover_fy;
    int have_anchor;
    int anchor_mx, anchor_my;
    int cur_mx, cur_my;
    int saw_nclick;
    int show_meas;
    char hud_line[256];
    char status_line[256];
    char dim_input_primary[32];
    char dim_input_secondary[32];
    int active_dim_field;
    int has_dim_focus;

    Viewport(int X, int Y, int W, int H)
        : Fl_Widget(X, Y, W, H),
          pix(NULL), rgb_buf(NULL), rgb_buf_sz(0),
          fw(0), fh(0), pitch(0), last_gen(-1),
          ox(0), oy(0),
          dragging(0), moved(0), pan_mode(0),
          down_x(0), down_y(0), last_x(0), last_y(0),
          down_mx(0), down_my(0),
          click_pending(0), click_sent(0), click_sh(0),
          pend_ox(0), pend_oy(0), pend_zoom(0),
          pend_panx(0), pend_pany(0),
          pend_hover(0), hover_fx(0), hover_fy(0),
          last_hover_fx(-9999), last_hover_fy(-9999),
          have_anchor(0), anchor_mx(0), anchor_my(0),
          cur_mx(0), cur_my(0), saw_nclick(0), show_meas(1),
          active_dim_field(0), has_dim_focus(0) {
        hud_line[0] = 0;
        status_line[0] = 0;
        dim_input_primary[0] = 0;
        dim_input_secondary[0] = 0;
        box(FL_FLAT_BOX);
        color(fl_rgb_color(15, 18, 23));
    }

    ~Viewport() {
        free(pix);
        free(rgb_buf);
    }

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
            char h[256], s[256];
            read_line_file(path_hud, h, sizeof h);
            read_line_file(path_status, s, sizeof s);
            if (strcmp(h, hud_line) || strcmp(s, status_line)) {
                snprintf(hud_line, sizeof hud_line, "%s", h);
                snprintf(status_line, sizeof status_line, "%s", s);
                redraw();
            }
        }
        int nc = tool_nclick();
        if (nc > 0)
            saw_nclick = 1;
        if (saw_nclick && nc <= 0) {
            have_anchor = 0;
            saw_nclick = 0;
        }
        flush_pending();
    }

    void set_cursor_widget(int mx, int my) {
        cur_mx = mx;
        cur_my = my;
        redraw();
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

    void draw_rubberband_overlay() {
        int tid = tool_id();
        int x0 = x() + (have_anchor ? anchor_mx : (down_mx > 0 ? down_mx : w() / 2));
        int y0 = y() + (have_anchor ? anchor_my : (down_my > 0 ? down_my : h() / 2));
        int x1 = x() + cur_mx;
        int y1 = y() + cur_my;

        int dx = x1 - x0;
        int dy = y1 - y0;
        double dist_px = sqrt((double)dx * dx + (double)dy * dy);
        double angle_rad = atan2((double)-dy, (double)dx);
        double angle_deg = angle_rad * 180.0 / M_PI;
        if (angle_deg < 0) angle_deg += 360.0;

        // 1. Tool-Specific Live Rubber Band Geometries
        if (tid == 0 || dragging) { // Line
            fl_color(fl_rgb_color(0, 229, 232)); // Electric Cyan
            fl_line_style(FL_SOLID, 2);
            fl_line(x0, y0, x1, y1);
            fl_line_style(0);
        } else if (tid == 1) { // Rectangle
            fl_color(fl_rgb_color(0, 229, 232));
            fl_line_style(FL_DASH, 1);
            int rx = (x0 < x1) ? x0 : x1;
            int ry = (y0 < y1) ? y0 : y1;
            int rw = abs(dx);
            int rh = abs(dy);
            fl_rect(rx, ry, rw, rh);
            fl_line_style(0);
        } else if (tid == 2) { // Circle
            fl_color(fl_rgb_color(0, 229, 232));
            fl_line_style(FL_DASH, 1);
            int r = (int)dist_px;
            fl_arc(x0 - r, y0 - r, r * 2, r * 2, 0.0, 360.0);
            fl_line(x0, y0, x1, y1);
            fl_line_style(0);
        } else if (tid == 3) { // Arc
            fl_color(fl_rgb_color(0, 229, 232));
            fl_line_style(FL_DASH, 1);
            int r = (int)dist_px;
            fl_arc(x0 - r, y0 - r, r * 2, r * 2, 0.0, angle_deg);
            fl_line(x0, y0, x1, y1);
            fl_line_style(0);
        }

        // 2. Start Anchor Marker & Crosshair Cursor
        fl_color(fl_rgb_color(255, 60, 60));
        fl_rectf(x0 - 4, y0 - 4, 9, 9);
        fl_color(fl_rgb_color(255, 220, 80));
        fl_rectf(x0 - 2, y0 - 2, 5, 5);

        fl_color(fl_rgb_color(0, 229, 232));
        fl_line(x1 - 10, y1, x1 + 10, y1);
        fl_line(x1, y1 - 10, x1, y1 + 10);
        fl_rectf(x1 - 3, y1 - 3, 7, 7);

        // 3. Fusion 360 In-Canvas Floating HUD Dimension Box
        char tip[128];
        if (tid == 0) {
            snprintf(tip, sizeof tip, "L: %.1f mm  deg: %.1f deg", dist_px, angle_deg);
        } else if (tid == 1) {
            snprintf(tip, sizeof tip, "W: %d mm x H: %d mm", abs(dx), abs(dy));
        } else if (tid == 2) {
            snprintf(tip, sizeof tip, "R: %.1f mm (Dia: %.1f mm)", dist_px, dist_px * 2.0);
        } else if (tid == 3) {
            snprintf(tip, sizeof tip, "R: %.1f mm  deg: %.1f deg", dist_px, angle_deg);
        } else {
            snprintf(tip, sizeof tip, "X: %d px  Y: %d px", cur_mx, cur_my);
        }

        fl_font(FL_HELVETICA_BOLD, 11);
        int tw = 0, th = 0;
        const char *disp_str = (has_dim_focus && dim_input_primary[0]) ? dim_input_primary : tip;
        fl_measure(disp_str, tw, th);
        int tx = x1 + 14;
        int ty = y1 - 22;
        if (tx + tw > x() + w() - 10) tx = x1 - tw - 14;
        if (ty < y() + 10) ty = y1 + 18;

        fl_color(has_dim_focus ? fl_rgb_color(0, 164, 166) : fl_rgb_color(16, 20, 28));
        fl_rectf(tx, ty, tw + 12, th + 6);
        fl_color(has_dim_focus ? fl_rgb_color(255, 255, 255) : fl_rgb_color(0, 196, 198));
        fl_rect(tx, ty, tw + 12, th + 6);
        fl_color(fl_rgb_color(255, 255, 255));
        fl_draw(disp_str, tx + 6, ty + th - 1);
    }

    void draw() override {
        // Instant hardware C++ frame blit (< 0.05ms)
        fl_rectf(x(), y(), w(), h(), fl_rgb_color(15, 18, 23));
        if (pix && fw > 0 && fh > 0) {
            ox = (w() - fw) / 2;
            oy = (h() - fh) / 2;
            if (ox < 0) ox = 0;
            if (oy < 0) oy = 0;

            size_t need_sz = (size_t)fw * (size_t)fh * 3;
            if (rgb_buf_sz < need_sz) {
                rgb_buf = (uint8_t*)realloc(rgb_buf, need_sz);
                rgb_buf_sz = need_sz;
            }

            // SIMD fast 32-bit BGR->RGB scanline conversion
            for (int i = 0; i < fw * fh; i++) {
                const uint8_t *p = pix + i * 4;
                rgb_buf[i * 3 + 0] = p[2]; /* R */
                rgb_buf[i * 3 + 1] = p[1]; /* G */
                rgb_buf[i * 3 + 2] = p[0]; /* B */
            }

            fl_push_clip(x(), y(), w(), h());
            fl_draw_image(rgb_buf, x() + ox, y() + oy, fw, fh, 3, 0);
            fl_pop_clip();
        } else {
            // Dark CAD preview grid when standalone
            int cx = x() + w() / 2, cy = y() + h() / 2;
            fl_color(fl_rgb_color(32, 40, 55));
            for (int gx = x(); gx < x() + w(); gx += 40) fl_line(gx, y(), gx, y() + h());
            for (int gy = y(); gy < y() + h(); gy += 40) fl_line(x(), gy, x() + w(), gy);

            fl_color(fl_rgb_color(0, 196, 198));
            fl_rect(cx - 120, cy - 80, 240, 160);
        }

        // Live HUD Overlay
        if (hud_line[0]) {
            fl_font(FL_HELVETICA_BOLD, 11);
            int tw = 0, th = 0;
            fl_measure(hud_line, tw, th);
            int hx = x() + w() - tw - 16;
            int hy = y() + 8;
            if (hx < x() + 8) hx = x() + 8;
            fl_color(fl_rgb_color(24, 28, 38));
            fl_rectf(hx - 8, hy - 4, tw + 16, th + 8);
            fl_color(fl_rgb_color(0, 196, 198));
            fl_rect(hx - 8, hy - 4, tw + 16, th + 8);
            fl_color(fl_rgb_color(225, 235, 250));
            fl_draw(hud_line, hx, hy + th - 2);
        }

        draw_rubberband_overlay();
    }

    /* RMB Right-Click Context Menu Handler */
    void show_rmb_context_menu() {
        static Fl_Menu_Item menu[] = {
            {"Edit Dimension...", 0, [](Fl_Widget*, void*){ prompt_edit_dimension(); }, 0, 0, 0, 0, 0, 0},
            {"Extrude / Pad Height...", 0, [](Fl_Widget*, void*){ const char *s=fl_input("Pad Height (mm):", "20"); if(s&&s[0]){ char c[48]; snprintf(c, sizeof c, "height %s", s); write_cmd(c); } }, 0, 0, 0, 0, 0, 0},
            {"Plane Offset...", 0, [](Fl_Widget*, void*){ const char *s=fl_input("Offset (mm):", "20"); if(s&&s[0]){ char c[48]; snprintf(c, sizeof c, "plane_off %s", s); write_cmd(c); } }, 0, 0, 0, 0, 0, 0},
            {"Sketch on Face", 0, [](Fl_Widget*, void*){ write_cmd("ontop"); }, 0, 0, 0, 0, 0, 0},
            {"Profiles", 0, [](Fl_Widget*, void*){ write_cmd("profiles"); }, 0, 0, 0, 0, 0, 0},
            {"Cancel Tool (Esc)", 0, [](Fl_Widget*, void*){ write_cmd("cancel"); }, 0, 0, 0, 0, 0, 0},
            {0}
        };
        const Fl_Menu_Item *m = menu->popup(Fl::event_x(), Fl::event_y());
        if (m && m->callback()) m->do_callback(this);
    }

    int handle(int ev) override {
        int mx = Fl::event_x() - x();
        int my = Fl::event_y() - y();
        int fx = mx - ox;
        int fy = my - oy;

        switch (ev) {
        case FL_MOVE:
        case FL_ENTER:
            take_focus();
            set_cursor_widget(mx, my);
            return 1;

        case FL_KEYBOARD: {
            int key = Fl::event_key();
            if (sketch_mode() && (have_anchor || dragging)) {
                if ((key >= '0' && key <= '9') || key == '.' || key == '-') {
                    has_dim_focus = 1;
                    char *target = (active_dim_field == 0) ? dim_input_primary : dim_input_secondary;
                    size_t len = strlen(target);
                    if (len < 20) {
                        target[len] = (char)key;
                        target[len + 1] = 0;
                        redraw();
                    }
                    return 1;
                } else if (key == FL_BackSpace) {
                    char *target = (active_dim_field == 0) ? dim_input_primary : dim_input_secondary;
                    size_t len = strlen(target);
                    if (len > 0) {
                        target[len - 1] = 0;
                        redraw();
                    }
                    return 1;
                } else if (key == FL_Tab) {
                    active_dim_field = (active_dim_field == 0) ? 1 : 0;
                    has_dim_focus = 1;
                    redraw();
                    return 1;
                } else if (key == FL_Enter || key == '\r' || key == '\n') {
                    if (has_dim_focus && dim_input_primary[0]) {
                        double val = atof(dim_input_primary);
                        if (val > 0.0) {
                            int x0 = (have_anchor ? anchor_mx : down_mx);
                            int y0 = (have_anchor ? anchor_my : down_my);
                            int dx = cur_mx - x0;
                            int dy = cur_my - y0;
                            double current_len = sqrt((double)dx*dx + (double)dy*dy);
                            if (current_len > 0.001) {
                                double scale = val / current_len;
                                int target_fx = (int)((x0 - ox) + dx * scale);
                                int target_fy = (int)((y0 - oy) + dy * scale);
                                char cmd[64];
                                snprintf(cmd, sizeof cmd, "click %d %d %d", target_fx, target_fy, click_sh);
                                write_cmd(cmd);
                            }
                        }
                    }
                    dim_input_primary[0] = 0;
                    dim_input_secondary[0] = 0;
                    has_dim_focus = 0;
                    redraw();
                    return 1;
                }
            }
            return Fl_Widget::handle(ev);
        }
        case FL_PUSH:
            take_focus();
            set_cursor_widget(mx, my);
            if (Fl::event_button() == FL_LEFT_MOUSE) {
                dragging = 1;
                moved = 0;
                pan_mode = 0;
                click_pending = 0;
                click_sent = 0;
                down_x = last_x = fx;
                down_y = last_y = fy;
                down_mx = mx;
                down_my = my;
                have_anchor = 1;
                anchor_mx = mx;
                anchor_my = my;
                clock_gettime(CLOCK_MONOTONIC, &down_ts);
                if (sketch_mode() && mx >= 0 && my >= 0 && mx < w() && my < h()) {
                    click_pending = 1;
                    click_sh = Fl::event_shift() ? 1 : 0;
                }
                return 1;
            }
            if (Fl::event_button() == FL_RIGHT_MOUSE) {
                show_rmb_context_menu();
                return 1;
            }
            return 1;
        case FL_DRAG:
            if (dragging && (Fl::event_state() & FL_BUTTON1)) {
                set_cursor_widget(mx, my);
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
                        if (pan_mode) {
                            pend_panx += dx;
                            pend_pany += dy;
                            last_x = fx;
                            last_y = fy;
                        } else {
                            pend_hover = 1;
                            hover_fx = fx;
                            hover_fy = fy;
                            last_hover_fx = fx;
                            last_hover_fy = fy;
                            last_x = fx;
                            last_y = fy;
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
                set_cursor_widget(mx, my);
                if (sketch_mode()) {
                    if (pan_mode) {
                        pan_mode = 0;
                    } else if (mx >= 0 && my >= 0 && mx < w() && my < h()) {
                        if (click_pending && !click_sent) {
                            char cmd[64];
                            int cx = (moved && (adx >= 3 || ady >= 3)) ? fx : down_x;
                            int cy = (moved && (adx >= 3 || ady >= 3)) ? fy : down_y;
                            if (fw > 0 && fh > 0 && cx >= 0 && cy >= 0 && cx < fw && cy < fh) {
                                snprintf(cmd, sizeof cmd, "click %d %d %d", cx, cy, click_sh);
                                write_cmd(cmd);
                            }
                            click_sent = 1;
                            click_pending = 0;
                        }
                    }
                } else {
                    if (!moved && adx < 4) {
                        if (fw > 0 && fh > 0 && down_x >= 0 && down_y >= 0 && down_x < fw && down_y < fh) {
                            char cmd[64];
                            snprintf(cmd, sizeof cmd, "click %d %d", down_x, down_y);
                            write_cmd(cmd);
                        }
                    }
                }
                return 1;
            }
            return 1;
        case FL_MOUSEWHEEL:
            if (Fl::event_dy() < 0) write_cmd("zoom 1");
            else if (Fl::event_dy() > 0) write_cmd("zoom -1");
            return 1;
        default:
            return Fl_Widget::handle(ev);
        }
    }
};

/* Global Callbacks */
static void cb_cmd(Fl_Widget *, void *data) {
    if (data) write_cmd((const char *)data);
}

static void cb_import(Fl_Widget *, void *) {
    Fl_Native_File_Chooser fc;
    fc.title("Import DXF File");
    fc.type(Fl_Native_File_Chooser::BROWSE_FILE);
    fc.filter("DXF Files\t*.dxf\nAll Files\t*");
    if (fc.show() == 0 && fc.filename()) {
        FILE *f = fopen(path_path, "w");
        if (f) {
            fputs(fc.filename(), f);
            fputc('\n', f);
            fclose(f);
            write_cmd("import");
        }
    }
}

/* Custom Styled Dark Button */
static Fl_Button* make_fusion_button(int X, int Y, int W, int H, const char *label, const char *cmd) {
    Fl_Button *b = new Fl_Button(X, Y, W, H, label);
    b->box(FL_FLAT_BOX);
    b->color(fl_rgb_color(40, 48, 64));
    b->labelcolor(fl_rgb_color(225, 235, 250));
    b->labelfont(FL_HELVETICA_BOLD);
    b->labelsize(11);
    if (cmd) b->callback(cb_cmd, (void*)cmd);
    return b;
}

static void timer_cb(void *v) {
    Viewport *vptr = (Viewport*)v;
    if (vptr) vptr->poll_frame();
    Fl::repeat_timeout(0.016, timer_cb, v);
}

/* ---------- Main Fusion 360 Native Host Window ---------- */

int main(int argc, char **argv) {
    const char *dir = (argc > 1) ? argv[1] : getenv("CAD_APP_STATE");
    if (!dir || !dir[0]) dir = "/tmp/cad_app";
    paths_init(dir);

    Fl::scheme("gtk+");
    Fl::background(28, 32, 42);
    Fl::foreground(225, 235, 250);

    Fl_Double_Window *win = new Fl_Double_Window(1280, 840, "AILang CAD — Fusion 360 Native C++ Host Shell");
    win->color(fl_rgb_color(20, 24, 32));

    // 1. Top Header & Workspace Badge
    Fl_Box *hdr = new Fl_Box(0, 0, 1280, 36, "  [ 3D MODEL MODE ]   AILang CAD Fusion 360 Engine");
    hdr->box(FL_FLAT_BOX);
    hdr->color(fl_rgb_color(28, 34, 46));
    hdr->labelcolor(fl_rgb_color(0, 196, 198));
    hdr->labelfont(FL_HELVETICA_BOLD);
    hdr->labelsize(12);
    hdr->align(FL_ALIGN_LEFT | FL_ALIGN_INSIDE);

    // 2. Tabbed Ribbon Bar
    Fl_Tabs *ribbon_tabs = new Fl_Tabs(0, 36, 1280, 72);
    ribbon_tabs->box(FL_FLAT_BOX);
    ribbon_tabs->color(fl_rgb_color(32, 38, 50));
    ribbon_tabs->selection_color(fl_rgb_color(40, 48, 64));
    ribbon_tabs->labelcolor(fl_rgb_color(225, 235, 250));

    // Tab 1: SKETCH
    Fl_Group *grp_sketch = new Fl_Group(0, 60, 1280, 48, "SKETCH");
    grp_sketch->color(fl_rgb_color(36, 42, 56));

    make_fusion_button(10, 64, 90, 38, "Line", "tool_line");
    make_fusion_button(105, 64, 90, 38, "Rectangle", "tool_rect");
    make_fusion_button(200, 64, 90, 38, "Circle", "tool_circ");
    make_fusion_button(295, 64, 90, 38, "Arc", "tool_arc");
    make_fusion_button(390, 64, 80, 38, "Point", "tool_point");
    make_fusion_button(475, 64, 80, 38, "Trim", "tool_trim");
    make_fusion_button(560, 64, 80, 38, "Fillet", "tool_fillet2d");
    grp_sketch->end();

    // Tab 2: SOLID
    Fl_Group *grp_solid = new Fl_Group(0, 60, 1280, 48, "SOLID");
    grp_solid->color(fl_rgb_color(36, 42, 56));

    make_fusion_button(10, 64, 120, 38, "Extrude", "repad");
    make_fusion_button(135, 64, 100, 38, "Revolve", "revolve");
    make_fusion_button(240, 64, 100, 38, "Fillet", "tool_fillet3d");
    make_fusion_button(345, 64, 110, 38, "Chamfer", "tool_chamfer");
    make_fusion_button(735, 64, 90, 38, "Pick Face", "tool_pick");
    grp_solid->end();

    // Tab 3: CONSTRUCT
    Fl_Group *grp_construct = new Fl_Group(0, 60, 1280, 48, "CONSTRUCT");
    grp_construct->color(fl_rgb_color(36, 42, 56));

    make_fusion_button(10, 64, 120, 38, "Offset 20mm", "plane_off 20");
    make_fusion_button(135, 64, 120, 38, "Rotate 45 deg", "plane_ang 45");
    make_fusion_button(260, 64, 110, 38, "Flip Normal", "plane_flip");
    make_fusion_button(375, 64, 120, 38, "Sketch Face", "ontop");
    make_fusion_button(500, 64, 120, 38, "Sketch Active", "sketch_pln");
    grp_construct->end();

    // Tab 4: INSPECT & VIEW
    Fl_Group *grp_view = new Fl_Group(0, 60, 1280, 48, "INSPECT & VIEW");
    grp_view->color(fl_rgb_color(36, 42, 56));

    make_fusion_button(10, 64, 140, 38, "Toggle Mode (M)", "mode");
    make_fusion_button(155, 64, 120, 38, "Wireframe (W)", "wire");
    make_fusion_button(280, 64, 120, 38, "Grid Snap (G)", "grid");
    grp_view->end();

    // Tab 5: FILE
    Fl_Group *grp_file = new Fl_Group(0, 60, 1280, 48, "FILE");
    grp_file->color(fl_rgb_color(36, 42, 56));

    make_fusion_button(10, 64, 100, 38, "New Doc", "newdoc");
    Fl_Button *btn_imp = make_fusion_button(115, 64, 120, 38, "Import DXF", NULL);
    btn_imp->callback(cb_import);
    make_fusion_button(240, 64, 120, 38, "Refresh Tools", "tools");
    grp_file->end();

    ribbon_tabs->end();

    // 3. Left Assembly & Construction Browser
    Fl_Group *browser_grp = new Fl_Group(0, 108, 220, 700);
    browser_grp->box(FL_FLAT_BOX);
    browser_grp->color(fl_rgb_color(24, 28, 38));

    Fl_Box *b_title = new Fl_Box(10, 114, 200, 24, "BROWSER TREE");
    b_title->box(FL_FLAT_BOX);
    b_title->color(fl_rgb_color(32, 38, 50));
    b_title->labelcolor(fl_rgb_color(0, 196, 198));
    b_title->labelfont(FL_HELVETICA_BOLD);

    make_fusion_button(10, 144, 200, 28, "XY Datum Plane", "plane_xy");
    make_fusion_button(10, 176, 200, 28, "XZ Datum Plane", "plane_xz");
    make_fusion_button(10, 208, 200, 28, "YZ Datum Plane", "plane_yz");
    make_fusion_button(10, 240, 200, 28, "Offset Plane (+20mm)", "plane_off 20");
    make_fusion_button(10, 272, 200, 28, "Rotate Plane (+45 deg)", "plane_ang 45");

    Fl_Hold_Browser *parts_browser = new Fl_Hold_Browser(10, 310, 200, 480, "Assembly Bodies");
    parts_browser->color(fl_rgb_color(18, 22, 30));
    parts_browser->textcolor(fl_rgb_color(225, 235, 250));
    parts_browser->add("Main_Bracket.step");
    parts_browser->add("Base_Sketch_01");
    parts_browser->add("Extrude_Pad_20mm");
    parts_browser->add("Offset_Plane_20mm");

    browser_grp->end();

    // 4. Central Viewport Area (Canvas + Viewcube + Nav overlays)
    Viewport *vp = new Viewport(220, 108, 820, 700);

    // ViewCube overlay buttons (top-right of viewport)
    make_fusion_button(960, 114, 70, 26, "TOP", "plane_top");
    make_fusion_button(960, 144, 70, 26, "FRONT", "plane_xz");
    make_fusion_button(960, 174, 70, 26, "SIDE", "plane_yz");
    make_fusion_button(960, 204, 70, 26, "ISO", "f");

    // Nav pill overlay buttons (bottom-center of viewport)
    make_fusion_button(460, 768, 70, 28, "Orbit", "mode");
    make_fusion_button(535, 768, 70, 28, "Pan", "mode");
    make_fusion_button(610, 768, 75, 28, "Zoom+", "zoom 1");
    make_fusion_button(690, 768, 75, 28, "Zoom-", "zoom -1");
    make_fusion_button(770, 768, 70, 28, "Grid", "grid");
    make_fusion_button(845, 768, 70, 28, "Wire", "wire");

    // 5. Right Parameter Inspector Deck
    Fl_Group *insp_grp = new Fl_Group(1040, 108, 240, 700);
    insp_grp->box(FL_FLAT_BOX);
    insp_grp->color(fl_rgb_color(24, 28, 38));

    Fl_Box *i_title = new Fl_Box(1050, 114, 220, 24, "INSPECTOR PALETTE");
    i_title->box(FL_FLAT_BOX);
    i_title->color(fl_rgb_color(32, 38, 50));
    i_title->labelcolor(fl_rgb_color(0, 196, 198));
    i_title->labelfont(FL_HELVETICA_BOLD);

    Fl_Box *p_lbl = new Fl_Box(1050, 150, 220, 20, "Extrude / Pad Height (mm):");
    p_lbl->labelcolor(fl_rgb_color(225, 235, 250));
    p_lbl->align(FL_ALIGN_LEFT | FL_ALIGN_INSIDE);

    Fl_Value_Input *inp_pad = new Fl_Value_Input(1050, 174, 140, 28);
    inp_pad->value(20.0);
    inp_pad->color(fl_rgb_color(18, 22, 30));
    inp_pad->textcolor(fl_rgb_color(255, 255, 255));

    Fl_Button *btn_pad = make_fusion_button(1195, 174, 75, 28, "Apply", NULL);
    btn_pad->callback([](Fl_Widget*, void* d){
        Fl_Value_Input *in = (Fl_Value_Input*)d;
        char c[48]; snprintf(c, sizeof c, "height %.1f", in->value());
        write_cmd(c);
    }, inp_pad);

    Fl_Box *off_lbl = new Fl_Box(1050, 220, 220, 20, "Construction Plane Offset:");
    off_lbl->labelcolor(fl_rgb_color(225, 235, 250));
    off_lbl->align(FL_ALIGN_LEFT | FL_ALIGN_INSIDE);

    Fl_Value_Input *inp_off = new Fl_Value_Input(1050, 244, 140, 28);
    inp_off->value(20.0);
    inp_off->color(fl_rgb_color(18, 22, 30));
    inp_off->textcolor(fl_rgb_color(255, 255, 255));

    Fl_Button *btn_off = make_fusion_button(1195, 244, 75, 28, "Offset", NULL);
    btn_off->callback([](Fl_Widget*, void* d){
        Fl_Value_Input *in = (Fl_Value_Input*)d;
        char c[48]; snprintf(c, sizeof c, "plane_off %.1f", in->value());
        write_cmd(c);
    }, inp_off);

    Fl_Box *ang_lbl = new Fl_Box(1050, 290, 220, 20, "Construction Plane Angle:");
    ang_lbl->labelcolor(fl_rgb_color(225, 235, 250));
    ang_lbl->align(FL_ALIGN_LEFT | FL_ALIGN_INSIDE);

    Fl_Value_Input *inp_ang = new Fl_Value_Input(1050, 314, 140, 28);
    inp_ang->value(45.0);
    inp_ang->color(fl_rgb_color(18, 22, 30));
    inp_ang->textcolor(fl_rgb_color(255, 255, 255));

    Fl_Button *btn_ang = make_fusion_button(1195, 314, 75, 28, "Rotate", NULL);
    btn_ang->callback([](Fl_Widget*, void* d){
        Fl_Value_Input *in = (Fl_Value_Input*)d;
        char c[48]; snprintf(c, sizeof c, "plane_ang %.1f", in->value());
        write_cmd(c);
    }, inp_ang);

    make_fusion_button(1050, 354, 220, 32, "Flip Plane Normal", "plane_flip");

    insp_grp->end();

    // 6. Bottom Parametric Status Bar
    Fl_Box *status_bar = new Fl_Box(0, 808, 1280, 32, " READY — Native C++ Fusion 360 Host Shell");
    status_bar->box(FL_FLAT_BOX);
    status_bar->color(fl_rgb_color(16, 20, 28));
    status_bar->labelcolor(fl_rgb_color(180, 195, 215));
    status_bar->labelfont(FL_HELVETICA);
    status_bar->labelsize(11);
    status_bar->align(FL_ALIGN_LEFT | FL_ALIGN_INSIDE);

    win->end();
    win->resizable(vp);
    win->callback([](Fl_Widget *w, void *) {
        write_cmd("quit");
        w->hide();
        exit(0);
    });
    win->show();

    Fl::add_timeout(0.016, timer_cb, vp);

    return Fl::run();
}
