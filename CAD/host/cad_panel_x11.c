/* cad_panel_x11 — separate tools / file panel dialog (IPC only)
 *
 * Reads  /tmp/cad_app/tool.txt  status.txt  parts.txt  sel.txt
 * Writes /tmp/cad_app/cmd.txt
 *
 * Viewport stays free for orbit/sketch; this window is the "toolbar".
 *
 * Build: cc -O2 -o cad_panel_x11 cad_panel_x11.c -lX11
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

static char g_dir[512];
static char path_cmd[600], path_status[600], path_tool[600];
static char path_parts[600], path_sel[600];

static void paths_init(const char *dir) {
    snprintf(g_dir, sizeof g_dir, "%s", dir);
    snprintf(path_cmd, sizeof path_cmd, "%s/cmd.txt", dir);
    snprintf(path_status, sizeof path_status, "%s/status.txt", dir);
    snprintf(path_tool, sizeof path_tool, "%s/tool.txt", dir);
    snprintf(path_parts, sizeof path_parts, "%s/parts.txt", dir);
    snprintf(path_sel, sizeof path_sel, "%s/sel.txt", dir);
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

static void read_line_file(const char *path, char *buf, size_t n) {
    buf[0] = 0;
    FILE *f = fopen(path, "r");
    if (!f) return;
    if (fgets(buf, (int)n, f)) {
        size_t L = strlen(buf);
        while (L && (buf[L-1] == '\n' || buf[L-1] == '\r')) buf[--L] = 0;
    }
    fclose(f);
}

/* tool.txt: "mode tool nclick dirty" */
static void read_tool(int *mode, int *tool, int *nclick, int *dirty) {
    *mode = 0; *tool = 0; *nclick = 0; *dirty = 0;
    FILE *f = fopen(path_tool, "r");
    if (!f) return;
    fscanf(f, "%d %d %d %d", mode, tool, nclick, dirty);
    fclose(f);
}

typedef struct {
    int x, y, w, h;
    const char *label;
    const char *cmd;
} Btn;

/* Layout: rows of buttons */
static Btn g_btns[] = {
    /* row 0: mode / pad */
    { 10,  40, 90, 28, "Sketch/3D", "mode" },
    {110,  40, 70, 28, "Pad (r)", "repad" },
    {190,  40, 70, 28, "Cut (u)", "cut" },
    {270,  40, 70, 28, "Wire",   "wire" },
    /* row 1: sketch tools */
    { 10,  80, 50, 28, "Line",    "tool_line" },
    { 64,  80, 50, 28, "Rect",    "tool_rect" },
    {118,  80, 50, 28, "Circ",    "tool_circ" },
    {172,  80, 50, 28, "Arc",     "tool_arc" },
    {226,  80, 50, 28, "Trim",    "tool_trim" },
    {280,  80, 50, 28, "Pick",    "tool_pick" },
    /* row 1b: profile select for multi-loop pad */
    { 10, 112, 80, 24, "Profiles", "profiles" },
    { 96, 112, 80, 24, "Next",     "y" },
    {182, 112, 70, 24, "Cancel",   "cancel" },
    /* row 2: file */
    { 10, 145, 70, 28, "List",    "f" },
    { 90, 145, 70, 28, "Open",    "g" },
    {170, 145, 70, 28, "Save",    "p" },
    {250, 145, 70, 28, "New",     "newdoc" },
    /* row 3: file cont */
    { 10, 185, 70, 28, "Close",   "k" },
    /* Clear model tree / last pad from viewport */
    {330, 145, 50, 28, "Clear",   "clear" },
    { 90, 185, 70, 28, "Reload",  "reload" },
    {170, 185, 70, 28, "STEP",    "step" },
    {250, 185, 70, 28, "BMP",     "bmp" },
    /* row 4: views */
    { 10, 225, 50, 28, "Iso",     "view0" },
    { 70, 225, 50, 28, "Top",     "view1" },
    {130, 225, 50, 28, "Front",   "view2" },
    {190, 225, 50, 28, "H-",      "hdec" },
    {250, 225, 50, 28, "H+",      "hinc" },
    {310, 225, 50, 28, "Quit",    "quit" },
};
static const int g_nbtn = (int)(sizeof g_btns / sizeof g_btns[0]);

static int hit_btn(int mx, int my) {
    int i;
    for (i = 0; i < g_nbtn; i++) {
        Btn *b = &g_btns[i];
        if (mx >= b->x && mx < b->x + b->w && my >= b->y && my < b->y + b->h)
            return i;
    }
    return -1;
}

static void draw_btn(Display *dpy, Window win, GC gc, Btn *b, int hot, int active) {
    unsigned long bg = active ? 0x2A5080 : (hot ? 0x303848 : 0x1A2030);
    unsigned long fg = active ? 0xFFE080 : 0xD0D8E8;
    XSetForeground(dpy, gc, bg);
    XFillRectangle(dpy, win, gc, b->x, b->y, b->w, b->h);
    XSetForeground(dpy, gc, 0x6080A0);
    XDrawRectangle(dpy, win, gc, b->x, b->y, b->w, b->h);
    XSetForeground(dpy, gc, fg);
    int tw = (int)strlen(b->label) * 6;
    int tx = b->x + (b->w - tw) / 2;
    if (tx < b->x + 4) tx = b->x + 4;
    XDrawString(dpy, win, gc, tx, b->y + 18, b->label, (int)strlen(b->label));
}

static void redraw(Display *dpy, Window win, GC gc, int win_w, int win_h, int hover_i) {
    int mode = 0, tool = 0, nclick = 0, dirty = 0;
    read_tool(&mode, &tool, &nclick, &dirty);

    XSetForeground(dpy, gc, 0x12151C);
    XFillRectangle(dpy, win, gc, 0, 0, win_w, win_h);

    XSetForeground(dpy, gc, 0xE0E8F0);
    XDrawString(dpy, win, gc, 10, 22, "AILang CAD — Tools", 18);

    char st[256];
    read_line_file(path_status, st, sizeof st);
    if (st[0]) {
        XSetForeground(dpy, gc, 0x90A0B8);
        if ((int)strlen(st) > 52) st[52] = 0;
        XDrawString(dpy, win, gc, 10, 250, st, (int)strlen(st));
    }

    char info[80];
    {
        const char *tname = "LINE";
        if (tool == 1) tname = "RECT";
        else if (tool == 2) tname = "CIRC";
        else if (tool == 3) tname = "ARC";
        else if (tool == 4) tname = "PICK";
        else if (tool == 5) tname = "TRIM";
        snprintf(info, sizeof info, "mode=%s  tool=%s  place=%d  %s",
                 mode ? "SKETCH" : "3D",
                 tname,
                 nclick,
                 dirty ? "DIRTY*" : "clean");
    }
    XSetForeground(dpy, gc, dirty ? 0xFFAA66 : 0x88CC88);
    XDrawString(dpy, win, gc, 10, 268, info, (int)strlen(info));

    /* part list snippet */
    {
        FILE *f = fopen(path_parts, "r");
        int sel = 0;
        FILE *sf = fopen(path_sel, "r");
        if (sf) { fscanf(sf, "%d", &sel); fclose(sf); }
        if (f) {
            XSetForeground(dpy, gc, 0x708090);
            XDrawString(dpy, win, gc, 10, 290, "Parts (List then Open):", 23);
            char line[64];
            int row = 0;
            while (row < 6 && fgets(line, sizeof line, f)) {
                size_t L = strlen(line);
                while (L && (line[L-1]=='\n'||line[L-1]=='\r')) line[--L]=0;
                if (!L) continue;
                if (L > 40) line[40] = 0;
                XSetForeground(dpy, gc, row == sel ? 0xFFE080 : 0xA0A8B8);
                char prefix[8];
                snprintf(prefix, sizeof prefix, row == sel ? "> " : "  ");
                char out[72];
                snprintf(out, sizeof out, "%s%s", prefix, line);
                XDrawString(dpy, win, gc, 10, 308 + row * 14, out, (int)strlen(out));
                row++;
            }
            fclose(f);
        }
    }

    int i;
    for (i = 0; i < g_nbtn; i++) {
        int active = 0;
        /* highlight current sketch tool */
        if (mode == 1) {
            if (tool == 0 && strcmp(g_btns[i].cmd, "tool_line") == 0) active = 1;
            if (tool == 1 && strcmp(g_btns[i].cmd, "tool_rect") == 0) active = 1;
            if (tool == 2 && strcmp(g_btns[i].cmd, "tool_circ") == 0) active = 1;
            if (tool == 3 && strcmp(g_btns[i].cmd, "tool_arc") == 0) active = 1;
            if (tool == 4 && strcmp(g_btns[i].cmd, "tool_pick") == 0) active = 1;
            if (tool == 5 && strcmp(g_btns[i].cmd, "tool_trim") == 0) active = 1;
        }
        if (mode == 1 && strcmp(g_btns[i].cmd, "mode") == 0) active = 1;
        draw_btn(dpy, win, gc, &g_btns[i], i == hover_i, active);
    }

    XSetForeground(dpy, gc, 0x606878);
    XDrawString(dpy, win, gc, 10, win_h - 12,
                "Click buttons → IPC cmd.txt  |  Viewport: draw/orbit", 52);
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
        fprintf(stderr, "cad_panel_x11: cannot open X display\n");
        return 1;
    }

    int screen = DefaultScreen(dpy);
    Window root = RootWindow(dpy, screen);
    int win_w = 380, win_h = 420;
    Window win = XCreateSimpleWindow(dpy, root, 860, 40, win_w, win_h, 2,
                                     0x6080A0, 0x12151C);
    XStoreName(dpy, win, "AILang CAD — Tools");
    XSelectInput(dpy, win,
                 ExposureMask | ButtonPressMask | ButtonReleaseMask |
                 PointerMotionMask | KeyPressMask | StructureNotifyMask);
    XMapWindow(dpy, win);

    GC gc = DefaultGC(dpy, screen);
    XFontStruct *font = XLoadQueryFont(dpy, "fixed");
    if (font) XSetFont(dpy, gc, font->fid);

    int hover_i = -1;
    int running = 1;
    int last_tool_sig = -1;
    char last_status[256];
    last_status[0] = 0;

    fprintf(stderr, "cad_panel_x11: %s (tools dialog)\n", dir);

    while (running) {
        while (XPending(dpy)) {
            XEvent ev;
            XNextEvent(dpy, &ev);
            if (ev.type == Expose) {
                redraw(dpy, win, gc, win_w, win_h, hover_i);
            } else if (ev.type == ConfigureNotify) {
                win_w = ev.xconfigure.width;
                win_h = ev.xconfigure.height;
            } else if (ev.type == MotionNotify) {
                int hi = hit_btn(ev.xmotion.x, ev.xmotion.y);
                if (hi != hover_i) {
                    hover_i = hi;
                    redraw(dpy, win, gc, win_w, win_h, hover_i);
                }
            } else if (ev.type == ButtonPress && ev.xbutton.button == Button1) {
                int hi = hit_btn(ev.xbutton.x, ev.xbutton.y);
                if (hi >= 0) {
                    const char *cmd = g_btns[hi].cmd;
                    write_cmd(cmd);
                    fprintf(stderr, "cad_panel: cmd %s\n", cmd);
                    if (strcmp(cmd, "quit") == 0) running = 0;
                    usleep(30000);
                    redraw(dpy, win, gc, win_w, win_h, hover_i);
                }
            } else if (ev.type == KeyPress) {
                KeySym ks = XLookupKeysym(&ev.xkey, 0);
                if (ks == XK_q || ks == XK_Escape) {
                    write_cmd("quit");
                    running = 0;
                } else if (ks == XK_l) write_cmd("tool_line");
                else if (ks == XK_e) write_cmd("tool_rect");
                else if (ks == XK_c) write_cmd("tool_circ");
                else if (ks == XK_r) write_cmd("repad");
                else if (ks == XK_m) write_cmd("mode");
                else if (ks == XK_p) write_cmd("p");
                else if (ks == XK_f) write_cmd("f");
                else if (ks == XK_g) write_cmd("g");
                else if (ks == XK_n) write_cmd("newdoc");
            }
        }

        /* refresh when tool/status change */
        int mode=0, tool=0, nclick=0, dirty=0;
        read_tool(&mode, &tool, &nclick, &dirty);
        int sig = mode + tool*10 + nclick*100 + dirty*1000;
        char st[256];
        read_line_file(path_status, st, sizeof st);
        if (sig != last_tool_sig || strcmp(st, last_status) != 0) {
            last_tool_sig = sig;
            snprintf(last_status, sizeof last_status, "%s", st);
            redraw(dpy, win, gc, win_w, win_h, hover_i);
        }

        XFlush(dpy);
        usleep(40000);
    }

    if (font) XFreeFont(dpy, font);
    XDestroyWindow(dpy, win);
    XCloseDisplay(dpy);
    return 0;
}
