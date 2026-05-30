# AILang OS

## What Is This?

AILang OS is a self-hosted operating system written entirely in the AILang programming language. Every layer — from PID 1 init to the display server, window compositor, widget toolkit, database driver, and end-user applications — is implemented in a single language that compiles directly to x86-64 Linux ELF binaries. There are no C libraries, no libc dependency, and no runtime. The compiler emits raw syscalls.

The system runs on real hardware. It boots from UEFI, authenticates through a graphical login screen rendered directly to the Linux framebuffer, starts PostgreSQL for structured data, launches a compositing display server, and presents a desktop with a taskbar, start menu, and windowed applications.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Applications                       │
│  Terminal  Calculator  Notepad  Grep  WiFi  Browser  │
│  VS Code   Claude     Video    Installer   Chrome    │
├─────────────────────────────────────────────────────┤
│              Display Server (IPC)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │ Auckland  │ │ Compositor│ │    IPC Broker        │ │
│  │ (Layout) │ │ (Float)   │ │ (Unix Socket + JSON) │ │
│  └──────────┘ └──────────┘ └──────────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │ Widget   │ │ Renderer │ │   Window Manager     │ │
│  │ Toolkit  │ │ (FB/DRM) │ │   + Start Menu       │ │
│  └──────────┘ └──────────┘ └──────────────────────┘ │
├─────────────────────────────────────────────────────┤
│              System Services                         │
│  Service Daemon  │  PostgreSQL  │  SSH Daemon        │
├─────────────────────────────────────────────────────┤
│              OS Layer                                │
│  Init (PID 1)  │  Schema  │  Login  │  Installer    │
├─────────────────────────────────────────────────────┤
│              AILang Libraries (~80 modules)           │
│  Arena  Socket  JSON  Arrays  Hash  StringUtils      │
│  HTTP  Regex  PostgreSQL_Complete  SVG  CSV  Math    │
├─────────────────────────────────────────────────────┤
│              Linux Kernel (x86-64)                   │
│  Framebuffer  evdev  Networking  Filesystems         │
└─────────────────────────────────────────────────────┘
```

## Boot Sequence

AILang OS boots through a deterministic 8-step sequence, all managed by a single Init binary that runs as PID 1:

1. **Mount Filesystems** — proc, sysfs, devtmpfs, tmpfs, devpts. Create `/data/blobs` for the UUID-based file store.

2. **Network** — Bring up loopback, attempt DHCP on eth0. If ethernet fails, detect WiFi interfaces (wlan0-3), check for `/etc/wpa_supplicant.conf`, and attempt WiFi connection with automatic DHCP.

3. **SSH** — Fork/exec sshd for remote access.

4. **Login** — If `/dev/fb0` exists, render a graphical login screen directly to the framebuffer using the TermFont library. Block until the user authenticates against the `users` table in PostgreSQL (or the default credentials on first boot).

5. **PostgreSQL** — Check for existing data directory. Run `initdb` on first boot. Fork/exec the postgres binary. Poll TCP 5432 for up to 60 seconds.

6. **Schema Bootstrap** — Connect to PostgreSQL, create the `ailang_system` database, create superuser, and run idempotent DDL to create all tables (services, files, users, sessions, settings, service_status, packages).

7. **First-Boot Installer** — If no user has a password configured, run the graphical Installer which creates the admin account and seeds default services and packages.

8. **Service Daemon + Watchdog** — Start the service daemon (which reads the `services` table and launches autostart services like the display server). Enter an infinite watchdog loop that reaps children and restarts any dead critical processes.

## The Display Server

The display server is a monolithic binary built from ~60 library modules. It runs as a service launched by the service daemon and provides:

- **Framebuffer rendering** — Direct writes to `/dev/fb0` or DRM. No X11, no Wayland.
- **Floating window compositor** — Overlapping windows with focus-follows-click, drag-to-move, window decorations.
- **Auckland layout engine** — A constraint-based layout solver that implements hbox/vbox flex layouts, similar to CSS flexbox.
- **HTML widget parser** — Window UIs are defined in XML/HTML config files that declare widgets, layouts, colors, and actions.
- **IPC broker** — An embedded message broker that accepts Unix socket connections from application processes, dispatches input events, and routes UI updates.
- **SVG rasterizer** — Full SVG path/shape/gradient parser and software rasterizer for vector graphics.
- **Input subsystem** — evdev-based keyboard and mouse input with hotplug device discovery.
- **Start menu and taskbar** — Desktop shell with application launcher and window list.

## IPC Protocol

Applications communicate with the display server over a Unix domain socket at `/tmp/ailang_display.sock`. Messages are JSON objects prefixed with a 4-byte big-endian length header:

```
[len_byte_3][len_byte_2][len_byte_1][len_byte_0][JSON payload...]
```

The protocol supports:
- `register` — Identify the application to the server
- `window.create` — Open a window using an HTML config file
- `window.setlabel` — Update a label widget by ID
- `window.addline` — Append a line to a panel widget
- `window.clear` — Clear a panel's contents
- `input.action` — Server sends button click events (action codes)
- `input.key` — Server sends keyboard events (keycode + character)
- `window.closed` — Server notifies the app that its window was closed

## PostgreSQL

PostgreSQL is the central data store. It is not optional — the OS uses it for:

- **Service registry** — What services exist, their binaries, autostart policy, and priority
- **Service status** — Runtime PID tracking, state, restart counts
- **User accounts** — Authentication, admin flags, home directories
- **Sessions** — Active login tracking
- **Virtual filesystem** — A `files` table with parent-child relationships, blob UUIDs, permissions
- **Settings** — Per-application key-value configuration
- **Packages** — Package manager registry tracking what's installed

All schema DDL is idempotent. `CREATE TABLE IF NOT EXISTS` and `ALTER TABLE ADD COLUMN IF NOT EXISTS` are used everywhere so the schema bootstrap can run repeatedly without error.

## Widget Toolkit

Window UIs are declared in HTML/XML config files. The Auckland layout engine parses these and renders them using the display server's software renderer. Available widgets:

| Widget | Description |
|--------|-------------|
| `<window>` | Top-level container with title, dimensions, toolbar mode |
| `<group>` | Layout container (hbox or vbox) with gap, padding, background |
| `<panel>` | Scrollable container, targetable by ID for addline/clear |
| `<button>` | Clickable button with label and action code |
| `<label>` | Text display, targetable by ID for setlabel |
| `<textfield>` | Text input field |
| `<checkbox>` | Toggle checkbox with action code |
| `<separator>` | Visual divider line |
| `<canvas>` | Drawing surface for custom rendering |
| `<slider>` | Value slider |
| `<progress>` | Progress bar |
| `<image>` | Image display |
| `<tabs>` / `<tab>` | Tabbed container |

Layout uses a flex model: `grow="1"` makes a widget expand to fill available space. Fixed sizes are set with `width` and `height` in pixels. Colors use hex notation (`bg="#2D2D44"`, `fg="#00FF88"`).

## Applications

All graphical applications are IPC clients — separate processes that connect to the display server socket, create a window, and handle events in a loop. Current applications:

| Application | Description | Size |
|-------------|-------------|------|
| Terminal | PTY-based terminal emulator | 92 KB |
| Calculator | Standard calculator with expression evaluation | 13 KB |
| Notepad | Text editor with file I/O | — |
| Grep Search | Regex file search tool | 31 KB |
| VS Code | Code editor | 55 KB |
| Chrome | Web browser (WIP) | 63 KB |
| Ladybird | Web browser (WIP) | — |
| Claude | Claude AI assistant interface | 93 KB |
| Video Player | Media player | — |
| WiFi Config | WiFi network manager | 36 KB |
| Package Manager | System package installer/tracker | 69 KB |

## Libraries

The AILang standard library contains ~80 modules:

**Core** — Arena (memory allocator), Arrays, Hash, StringUtils, JSON, Socket, HTTP, Regex (Thompson NFA), CSV, RESP (Redis protocol), PostgreSQL_Complete, Math, LinearAlgebra, FixedPointTrig, TimeDate, TextBuffer, OAuth, MessagePort

**Display** — 60 modules covering the full display stack: SysDisplay, Auckland (layout), Framebuffer, DRenderFB, DSurface, DComposeFloat, Fonts, TermFont, SVG, VIF, HTMLParse, WinManager, WinToolbar, IPCBroker, InputRouter, DInputEvdev, Cursor, UITheme, StartMenu, Deskbar, CascadeMenu, FileDialog, Dialog, TextRegion

**Special** — C64CPU (6502 emulator), KernelShim, PlaybackClock

## Self-Hosting

The AILang compiler is written in AILang. The `ailang.x` binary in the repository root compiles `.ailang` source files directly to x86-64 ELF executables. There is no intermediate representation, no linker, and no external toolchain dependency. The compiler handles:

- Lexing and parsing of AILang syntax
- Library import resolution with namespace conflict handling
- Pool-backed AST with 17,000+ nodes for large programs
- Direct x86-64 code emission with redundant load optimization
- ELF binary construction with code and data segments
- Static data relocation

A typical application compiles in under a second and produces a standalone binary between 13 KB and 337 KB.

## Hardware Requirements

AILang OS runs on standard x86-64 hardware with:
- UEFI boot (GPT partition table, EFI System Partition)
- Linux framebuffer or DRM for display
- evdev-compatible keyboard and mouse
- Ethernet or WiFi (44 wireless drivers built into the kernel, extensive firmware for Intel, Atheros, Broadcom, Realtek, MediaTek)
- Storage for the root filesystem (ext4, ~2 GB)

The system has been tested in QEMU/KVM and on bare metal.

## Project Structure

```
Ailang-Self-Hosting-/
├── ailang.x                    # The self-hosted compiler
├── OS/                         # Operating system modules
│   ├── Init.ailang             # PID 1 — boot sequence
│   ├── Schema.ailang           # Database DDL
│   ├── ServiceDaemon.ailang    # Service lifecycle manager
│   ├── Login.ailang            # Graphical login screen
│   ├── Installer.ailang        # First-boot setup
│   ├── FileTree.ailang         # Virtual filesystem
│   └── UUIDStore.ailang        # Blob storage
├── Applications/               # IPC client applications
│   ├── terminal_ipc.ailang
│   ├── grep_ipc.ailang
│   ├── wifi_ipc.ailang
│   ├── installer_ipc.ailang
│   └── ...
├── Librarys/                   # Library modules
│   ├── Display/                # Display server stack (60 modules)
│   ├── Library.Arena.ailang
│   ├── Library.Socket.ailang
│   ├── Library.JSON.ailang
│   └── ...
├── config/                     # Window UI definitions (HTML/XML)
│   ├── grep.html
│   ├── calculator.html
│   ├── wifi.html
│   └── ...
└── Programs/                   # Standalone demo programs
```

## License

Copyright 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved. SCSL.
