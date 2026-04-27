# X11 App Porting Guide

How to port any X11/Electron/GTK/Qt application to the AiLang display server.

## Architecture

Every X11 app runs inside its own virtual framebuffer (Xvfb), completely isolated from the real display. The app thinks it has a normal X11 display. We capture its output via direct memory mapping and forward input via xdotool.

```
                     +-----------+
                     | Your App  |  (thinks it has a real X display)
                     +-----+-----+
                           |
                     +-----+-----+
                     |  Xvfb :N  |  writes framebuffer to /tmp/<app>_fb/Xvfb_screen0
                     +-----+-----+
                           |
  +----------+       +-----+-----+       +-----------+
  | xdotool  |<------| IPC App   |------>| ShmCanvas |
  | (pipe)   |       | (.ailang) |       | (/dev/shm)|
  +----------+       +-----+-----+       +-----+-----+
       |                   |                    |
       v                   v                    v
    Xvfb :N         Display Server         Display Server
    (input)         (IPC socket)           (pixel blit)
```

**3 processes per app:**
1. **Xvfb** `:N` — virtual X server, writes framebuffer to disk
2. **Your App** — runs on the virtual display, unmodified
3. **xdotool** — persistent stdin pipe for keyboard/mouse input

**Zero-copy frame capture:** Xvfb with `-fbdir` writes its framebuffer as a memory-mapped file in xwd format. The IPC app mmaps this file read-only and copies pixels to the ShmCanvas each tick. No encoding, no pipes, no ffmpeg.

## Step-by-Step Porting Checklist

### 1. Choose a Display Number

Each Xvfb app needs a unique display number. Current allocations:

| Display | App |
|---------|-----|
| `:98` | VS Code |
| `:99` | Chrome |

Pick an unused number (`:97`, `:96`, etc.).

### 2. Create the HTML Config

`config/<appname>.html`:
```html
<window title="App Name" design-w="1024" design-h="700" toolbar="about">
  <group layout="vbox" gap="0" padding="0" bg="#000000">
    <panel grow="1" bg="#000000"/>
  </group>
</window>
```

- `design-w` / `design-h` — initial window size (including toolbar)
- `toolbar` — `"about"` (default), `"file"`, `"full"`, or `"none"`
- `bg` — set to the app's background color for seamless loading appearance

### 3. Create the IPC App

Copy `Applications/vscode_ipc.ailang` (or `chrome_ipc.ailang`) and do find-and-replace:

| What to Change | Example (VS Code) |
|---|---|
| All `Vsc` prefixes | `MyApp` |
| `VscState` pool | `MyAppState` |
| `VSys` / `VMmap` / `VSig` etc. | `MASys` / `MAMmap` / `MASig` |
| `display_num` | Your chosen display (`:97`) |
| fbdir path | `/tmp/myapp_fb` |
| Xvfb_screen0 path | `/tmp/myapp_fb/Xvfb_screen0` |
| Lock file paths | `/tmp/.X97-lock`, `/tmp/.X11-unix/X97` |
| Service name | `"myapp"` |
| Window title | `"My App"` |
| HTML config path | `"config/myapp.html"` |

### 4. Configure the App Launch

The `LaunchApp` function is the only part that changes significantly per app. Key decisions:

**Binary path:** Where is the app installed?
```ailang
StoreValue(Add(argv, 0), "/usr/bin/myapp")
```

**App-specific flags:** Disable things that don't work in Xvfb:
```ailang
StoreValue(Add(argv, 8),  "--no-sandbox")       // Electron apps
StoreValue(Add(argv, 16), "--disable-gpu")       // No hardware GPU in Xvfb
StoreValue(Add(argv, 24), "--disable-updates")   // Prevent auto-update popups
```

**Startup wait time:** Electron apps need ~3s, simple X11 apps ~1s:
```ailang
// Wait for app to render first frame
StoreValue(ts_wait, 3)   // 3 seconds for Electron
StoreValue(ts_wait, 1)   // 1 second for lightweight X11 apps
```

**Environment variables:** Always pass DISPLAY, HOME, PATH, LANG:
```ailang
envp = Allocate(40)
StoreValue(Add(envp, 0),  denv)                   // DISPLAY=:N
StoreValue(Add(envp, 8),  "HOME=/home/bob")
StoreValue(Add(envp, 16), "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")
StoreValue(Add(envp, 24), "LANG=en_US.UTF-8")
StoreValue(Add(envp, 32), 0)                       // NULL terminator
```

### 5. Configure Keyboard Shortcuts

The `HandleKey` function maps IPC keycodes to xdotool commands. Common pattern:

```ailang
// Ctrl combos — app-specific
IfCondition EqualTo(ctrl, 1) ThenBlock: {
    IfCondition EqualTo(keycode, 31) ThenBlock: {   // Ctrl+S
        MyApp_XdotoolKey("ctrl+s")
        ReturnValue(0)
    }
}

// Standard keys — same for all apps
IfCondition EqualTo(keycode, 28) ThenBlock: {       // Enter
    MyApp_XdotoolKey("Return")
    ReturnValue(0)
}

// Printable chars — same for all apps
IfCondition And(GreaterEqual(ch, 32), LessEqual(ch, 126)) ThenBlock: {
    MyApp_XdotoolType(ch)
    ReturnValue(0)
}
```

**Linux evdev keycodes** (decimal):

| Key | Code | Key | Code | Key | Code |
|-----|------|-----|------|-----|------|
| Esc | 1 | Backspace | 14 | Tab | 15 |
| Enter | 28 | Space | 57 | Delete | 111 |
| Up | 103 | Down | 108 | Left | 105 |
| Right | 106 | Home | 102 | End | 107 |
| PageUp | 104 | PageDown | 109 | F1-F12 | 59-70 |
| A | 30 | S | 31 | D | 32 |
| F | 33 | G | 34 | Z | 44 |
| X | 45 | C | 46 | V | 47 |
| B | 48 | N | 49 | P | 25 |
| W | 17 | Y | 21 | ` | 41 |

### 6. Configure Mouse (Optional)

If your app needs mouse input, use `ShmCanvas_AttachCapture` instead of `ShmCanvas_Attach`. This enables VM-style mouse capture:

- Display server hides cursor when over the canvas
- All mouse events (move, down, up) forwarded to the app
- Mouse moves coalesced to one per tick (prevents flooding xdotool)

If your app is keyboard-only (e.g., terminal), use `ShmCanvas_Attach` (no capture).

### 7. Configure Privilege Drop

The display server (`SysDisplay.x`) runs as root on TTY2. Child processes inherit root, which causes problems:
- Electron/VS Code refuses to run as root
- Created files (fbdir, profiles) are root-owned, making cleanup fail for non-root
- Broader security risk

Add a `DropPriv()` function and call it in **every** child fork before `execve`:

```ailang
Function.MyApp_DropPriv {
    Body: {
        uid = SystemCall(MASys.SYS_GETUID, 0, 0, 0, 0, 0)
        IfCondition NotEqual(uid, 0) ThenBlock: { ReturnValue(0) }  // not root, skip
        sb = Allocate(144)   // struct stat
        sr = SystemCall(MASys.SYS_STAT, "/home/bob", sb, 0, 0, 0)
        IfCondition LessThan(sr, 0) ThenBlock: {
            Deallocate(sb, 144)
            ReturnValue(0)
        }
        ruid = Dereference(Add(sb, 28), "dword")   // st_uid
        rgid = Dereference(Add(sb, 32), "dword")   // st_gid
        Deallocate(sb, 144)
        IfCondition EqualTo(ruid, 0) ThenBlock: { ReturnValue(0) }  // home owned by root, skip
        SystemCall(MASys.SYS_SETGID, rgid, 0, 0, 0, 0)   // setgid first!
        SystemCall(MASys.SYS_SETUID, ruid, 0, 0, 0, 0)
    }
}
```

Required syscall constants: `SYS_STAT=4`, `SYS_GETUID=102`, `SYS_SETUID=105`, `SYS_SETGID=106`.

Call `MyApp_DropPriv()` as the **first line** inside each `IfCondition EqualTo(pid, 0)` block (Xvfb fork, app fork, xdotool fork).

### 8. Configure Cleanup

The `CleanupStale` function kills orphaned processes from prior crashes. Use PID files for reliable, targeted cleanup — **never** use broad `pkill` patterns (they kill desktop instances of the same app).

**PID file system:**
```ailang
// Write PID file after fork
MyApp_WritePidFile("/tmp/myapp_ailang_xvfb.pid", pid)
MyApp_WritePidFile("/tmp/myapp_ailang_app.pid", pid)
MyApp_WritePidFile("/tmp/myapp_ailang_xdotool.pid", pid)

// In CleanupStale — read PID files and kill targeted processes
pid = MyApp_ReadPidFile("/tmp/myapp_ailang_app.pid")
IfCondition GreaterThan(pid, 1) ThenBlock: {
    MyApp_KillGroup(pid)       // kill process group (setsid'd children)
    MyApp_KillStalePid(pid, "MyApp")
}
// ... repeat for xdotool and xvfb PIDs ...

MyApp_RemovePidFiles()   // clean up PID files

// Remove fbdir and lock files
SystemCall(MASys.SYS_UNLINK, "/tmp/myapp_fb/Xvfb_screen0", 0, 0, 0, 0)
MyApp_ShellExec("rmdir /tmp/myapp_fb 2>/dev/null")
SystemCall(MASys.SYS_UNLINK, "/tmp/.X97-lock", 0, 0, 0, 0)
SystemCall(MASys.SYS_UNLINK, "/tmp/.X11-unix/X97", 0, 0, 0, 0)
```

**Process group kill** (`KillGroup`): Children call `setsid()`, so their PID equals their PGID. `kill(-pid, SIGKILL)` kills the entire group without touching desktop apps.

**EPERM handling**: If a stale process is root-owned and we're running as user, `KillStalePid` prints an actionable error message: `"Run: sudo kill -9 <pid>"`.

### 9. Register in PostgreSQL

```sql
INSERT INTO services (name, binary_path, display_name, enabled)
VALUES ('myapp', './myapp_ipc.x', 'My App', true);
```

This makes the app appear in the Start Menu.

### 10. Build and Test

```bash
# Build
./ailang.x Applications/myapp_ipc.ailang myapp_ipc.x

# Test (display server must be running on TTY2)
./myapp_ipc.x
```

## Common App Recipes

### Electron Apps (VS Code, Slack, Discord, etc.)

```ailang
StoreValue(Add(argv, 0),  "/usr/bin/appname")
StoreValue(Add(argv, 8),  "--no-sandbox")
StoreValue(Add(argv, 16), "--disable-gpu")
StoreValue(Add(argv, 24), "--disable-updates")
StoreValue(Add(argv, 32), "--new-window")
StoreValue(Add(argv, 40), "--user-data-dir=/tmp/myapp_ailang_profile")
StoreValue(Add(argv, 48), "--disable-dev-shm-usage")
StoreValue(Add(argv, 56), "--disable-breakpad")
```

Startup wait: 3 seconds. **Do NOT** use `--unity-launch` — it causes Electron to join the existing desktop instance instead of rendering in Xvfb. Use `--user-data-dir` to force an independent instance. `DropPriv()` is required — Electron refuses to run as root.

### GTK Apps (GIMP, Inkscape, etc.)

```ailang
StoreValue(Add(argv, 0), "/usr/bin/gimp")
StoreValue(Add(argv, 8), 0)   // Most GTK apps need no special flags
```

Startup wait: 2 seconds. May need `GDK_BACKEND=x11` in envp.

### Qt Apps (KDE apps, VLC, etc.)

```ailang
StoreValue(Add(argv, 0), "/usr/bin/vlc")
StoreValue(Add(argv, 8), "--no-video-title-show")
StoreValue(Add(argv, 16), 0)
```

May need `QT_QPA_PLATFORM=xcb` in envp.

### Chrome-based Browsers (Chromium, Brave, Edge)

Same as Chrome. Change binary path and user-data-dir:
```ailang
StoreValue(Add(argv, 0),   "/usr/bin/brave-browser")
StoreValue(Add(argv, 104), "--user-data-dir=/tmp/brave_ailang_profile")
```

### Simple X11 Apps (xterm, xclock, xeyes)

```ailang
StoreValue(Add(argv, 0), "/usr/bin/xterm")
StoreValue(Add(argv, 8), 0)
```

Startup wait: 500ms. No special flags needed.

## Frame Capture Details

### xwd Format (Xvfb -fbdir output)

| Offset | Size | Content |
|--------|------|---------|
| 0 | 160 bytes | xwd header (dimensions, depth, byte order) |
| 160 | 3072 bytes | Colormap (256 entries x 12 bytes) |
| 3232 | W x H x 4 | Pixel data (BGRX, 32bpp, LSBFirst) |

- **Total header:** 3232 bytes (constant for 24-bit depth)
- **Pixel format:** BGRX = BGRA with alpha always 0x00
- **Byte order:** LSBFirst on x86 (native)
- **Pitch:** width x 4 (no padding)
- **ShmCanvas format:** Also BGRA 32-bit — pixel-compatible, straight memcpy

### Performance

- **5ms tick** = ~200 fps capture rate (display server renders at ~60fps anyway)
- **MemoryCopy** = ~2.8GB/s on modern CPUs for 1024x700x4 = 2.87MB per frame
- **Latency:** mmap is zero-copy between Xvfb and our process (same physical pages)
- No encoding, no pipes, no compression — just pointer arithmetic and memcpy

## Troubleshooting

| Problem | Solution |
|---------|----------|
| App doesn't render | Check app is installed, binary path correct |
| Black screen | Increase startup wait time (app not ready before mmap) |
| Input not working | Verify xdotool is installed, check DISPLAY in envp |
| App crashes on start | Try `--no-sandbox --disable-gpu` flags |
| Stale processes after crash | Check PID files in `/tmp/*_ailang_*.pid`, kill manually if EPERM |
| Both Chrome and VSCode black | Each needs its own `-fbdir` directory |
| Xvfb won't start | Check for stale `/tmp/.XN-lock` files, remove them |
| Mouse feels laggy | Mouse moves are coalesced — this is by design |
| Electron "GPU process isn't usable" | Add `--disable-gpu` to argv |
| Electron refuses to run as root | Add `DropPriv()` call before execve in child fork |
| App kills desktop instance | Use PID file cleanup, never broad `pkill` |
| Root-owned fbdir won't clean | `sudo rm -rf /tmp/<app>_fb`, then restart |

## File Naming Convention

| File | Purpose |
|------|---------|
| `Applications/<app>_ipc.ailang` | IPC app source |
| `config/<app>.html` | Window layout |
| `/tmp/<app>_fb/Xvfb_screen0` | Xvfb framebuffer (runtime) |
| `/tmp/.<display>-lock` | Xvfb lock file (runtime) |

## Current Ported Apps

| App | Binary | Display | fbdir | Status |
|-----|--------|---------|-------|--------|
| Chrome | `chrome_ipc.x` | `:99` | `/tmp/chrome_fb/` | Working |
| VS Code | `vscode_ipc.x` | `:98` | `/tmp/vscode_fb/` | Working |

---

Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
