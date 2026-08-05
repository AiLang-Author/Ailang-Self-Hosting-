# Contributing to AILang OS

AILang OS is a vertically integrated operating system where every layer — from PID 1 to the display server to end-user applications — is written in AILang. The project is looking for contributors who want to work on real OS infrastructure, not toy projects.

## What We're Building

An operating system designed from the ground up for a world where AI agents are first-class users of the system. Current OS security models assume human users. Permission systems are coarse (this *user* can access these *files*). When you give an AI agent shell access, it inherits the user's full permission set with no semantic understanding of intent, no scoped capabilities, and no audit trail.

AILang OS controls every layer of the stack, which means we can build security and capability primitives that conventional operating systems cannot retrofit:

- **IPC is observable.** Every application talks through our message-passing system. An AI agent's communications can be filtered and audited at the OS level.
- **The display server is authoritative.** We see what the agent sees, what it clicks, what it types. No hidden UI actions.
- **PostgreSQL is the system database.** Services, permissions, user preferences, file metadata — all queryable and auditable. Not scattered across dotfiles.
- **Process-per-codec media pipeline.** Each worker touches only its own shared memory ring buffers. Natural capability boundaries.

The long-term goal is an OS where a user can say "reorganize my documents" and the agent gets a scoped, time-limited, auditable capability token — not root access with a prayer.

## Architecture Overview

```
Boot:     UEFI -> Linux 6.6.18 -> ailang_init (PID 1)
Database: PostgreSQL 16 (system DB for services, users, files, settings)
Display:  Framebuffer/DRM -> custom compositor -> Auckland UI toolkit
IPC:      Unix socket + JSON (length-prefixed), shared memory rings
Apps:     Separate processes, connect to display server via IPC
Media:    Process-per-codec workers, shared memory ring protocol
```

Key files to understand the system:

| File | What it does |
|------|-------------|
| `OS/Init.ailang` | PID 1 — mounts filesystems, loads modules, starts postgres, login, service daemon |
| `Main.ailang` | Display server entry point — imports ~60 library modules |
| `OS/Schema.ailang` | Database DDL — all system tables |
| `Librarys/Display/System/Library.SysDisplay.ailang` | Display server core — input routing, compositing, main loop |
| `Librarys/Display/UI/Library.Auckland.ailang` | Retained-mode UI toolkit — layout solver, hit testing, drawing |
| `Librarys/Display/IPC/Library.IPCBroker.ailang` | Application IPC — socket accept, message dispatch |
| `Librarys/Display/Menu/Library.Deskbar.ailang` | Taskbar — app launchers, window list, system tray |
| `MediaCenter/MediaCenter.ailang` | Media service — codec worker management, playback clock |
| `deploy.sh` | Build and deploy script — compiles AILang + C workers, pushes to target |

## Areas for Contribution

### 1. X11 Application Sandbox Hardening

**Impact: High | Difficulty: Medium**

Chrome and VS Code run inside Xvfb virtual X servers (`chrome_ipc.ailang`, `vscode_ipc.ailang`). The current sandbox launches Xvfb + the application as child processes with input forwarded via xdotool and framebuffer captured via direct mmap of the Xvfb shared memory segment.

What's missing:
- **Network namespace isolation** — Wrap the Xvfb+Chrome launch in `unshare --net --mount` with a filtered veth pair so the sandboxed app can only reach whitelisted endpoints.
- **Filesystem restriction** — Mount namespace with read-only bind mounts. The sandboxed process should only see what it needs.
- **Capability dropping** — Strip capabilities before exec. No `CAP_SYS_ADMIN`, no `CAP_NET_RAW`.
- **Seccomp filter** — Restrict available syscalls to what Chrome/Xvfb actually need.

The fork/exec plumbing is already in the AILang source. This work is primarily Linux namespace and seccomp configuration applied before the exec call.

Relevant files:
- `Applications/chrome_ipc.ailang` — Chrome sandbox (~1700 lines)
- `Applications/vscode_ipc.ailang` — VS Code sandbox (same pattern)

### 2. Auckland UI Toolkit — New Widgets

**Impact: High | Difficulty: Medium**

The Auckland retained-mode UI toolkit has: button, label, textfield, checkbox, radio, slider, progress, canvas, tabs, separator, image, panel. It needs:

- **Dropdown / Combobox** — Click to open a list, select an item, collapse. Needs: popup positioning, item list management, keyboard navigation.
- **Scrollbar** — Vertical and horizontal. The panel widget scrolls content but has no visible scrollbar handle. Needs: track/thumb rendering, drag-to-scroll, scroll wheel integration.
- **Tree View** — Expandable/collapsible hierarchy. Needed for file browsers, settings panels. Needs: indentation, expand/collapse state per node, icon support.
- **Table / List View** — Column headers, sortable, selectable rows. Needed for file manager, process list.
- **Tooltip** — Hover delay, positioned popup, auto-dismiss.

The widget system follows a clear pattern: each widget type has a draw function, a layout participation rule in the flex solver, and event handling in `AK_EventMouse`. Study `Library.Auckland.ailang` and `Library.AucklandEvent.ailang` to understand the pattern.

Relevant files:
- `Librarys/Display/UI/Library.Auckland.ailang` — Core toolkit (layout, drawing, node tree)
- `Librarys/Display/UI/Library.AucklandEvent.ailang` — Hit testing, focus, mouse/keyboard dispatch
- `Librarys/Display/UI/Library.AucklandDraw.ailang` — Widget rendering

### 3. WiFi Manager Application

**Impact: Medium | Difficulty: Low-Medium**

`Applications/wifi_ipc.ailang` exists but needs work to be a real daily-driver WiFi manager:

- Scan for available networks (parse `iwlist` or `iw` scan output)
- Display signal strength, security type (WPA2/WPA3/Open)
- Connect with password entry (write `wpa_supplicant.conf`, restart wpa_supplicant)
- Save known networks, auto-reconnect
- Show connection status in the deskbar system tray

The IPC protocol and window config system handle all the UI plumbing. This is primarily parsing wireless tool output and managing `wpa_supplicant.conf`.

### 4. Test Harness for AILang Programs

**Impact: Very High | Difficulty: Medium**

There are no automated tests for the OS components. A test framework would multiply every contributor's velocity. Proposal:

- A test runner that compiles AILang snippets, runs them, captures stdout/exit code, and compares against expected output.
- Test definitions in a simple format (input file, expected output, expected exit code).
- Integration with the compiler's analyzer for type/arity checking without full compilation.
- Regression tests for the display server IPC protocol (send JSON messages, verify responses).
- Boot sequence smoke tests (verify init mounts filesystems, starts postgres, etc.)

### 5. Capability System for AI Agents

**Impact: Transformative | Difficulty: High**

This is the core thesis of the project. Design and implement a capability-based permission system:

- **Capability tokens** — Scoped, time-limited, revocable. Example: `{read: /home/user/documents, write: /home/user/documents, network: none, exec: none, expires: +300s}`.
- **Intent declaration** — The agent declares what it wants to do in semantic terms before doing it. The OS policy engine approves or denies.
- **Audit log** — Append-only, cryptographically chained log of every agent action. User can review what happened and why.
- **IPC integration** — Capabilities are checked at the IPC broker level. An agent's messages are filtered based on its current capability set.
- **Multi-user scoping** — Capabilities are per-user, per-agent, per-session. User A's agent cannot access User B's data even if they're on the same system.

This requires design work before implementation. Start by reading the IPC broker (`Library.IPCBroker.ailang`) and the service registry (`OS/Schema.ailang`) to understand the current trust model, then propose a capability architecture.

### 6. IPC and Memory Encryption

**Impact: High | Difficulty: High**

Encrypt the shared memory surfaces used for IPC:

- **Ring buffer encryption** — Each CodecRing (`/dev/shm/ailang_codec_*`) gets a session key negotiated at connection time. Records encrypted in-place. Only the two endpoints hold the key.
- **Display surface encryption** — ShmCanvas regions encrypted so a compromised process can't read another window's framebuffer.
- **Binary memory protection** — Guard pages, stack canaries, ASLR for AILang binaries.
- **Disk encryption** — dm-crypt/LUKS at the block layer, unlocked at login.

The shared memory ring architecture (`Librarys/Media/Library.CodecRing.ailang`) makes per-channel encryption tractable. The key exchange can be mediated by the OS without the OS holding plaintext.

### 7. Multi-User Support

**Impact: High | Difficulty: Medium**

The PostgreSQL-backed architecture makes multi-user straightforward:

- **Per-user service registry** — Add `user_id` column to the `services` table. Users see only their registered applications.
- **Per-user file tree** — The `files` table already has parent-child relationships. Add `owner_id` and filter by current user.
- **Per-user settings** — The `settings` table gets a `user_id` column. Each user has their own theme, preferences, wallpaper.
- **Session isolation** — Each user's display session runs in a separate process group. Users cannot signal or ptrace each other's processes.
- **Fast user switching** — Save compositor state, switch to a new login session on a different VT.

The schema migration is simple. The display server needs session-awareness.

### 8. MediaCenter Node Graph

**Impact: Medium | Difficulty: Medium-High**

The atomized codec pipeline (11 C workers: mp3, aac, opus, flac, vorbis, pcm, h264, h265, vp9, av1, demux) is built. The next step is a node graph manager that wires demux -> decode -> mix -> present:

- **Node types** — Source (demuxer), Decoder (codec worker), Mixer (N-input audio), Presenter (ALSA/ShmCanvas).
- **Pipeline builder** — `media.open(file)` creates the full pipeline automatically.
- **Hardware-authoritative clock** — ALSA period completion drives the master clock, not software timers.
- **N-input mixer** — Per-input volume, replaces the current flat 3-bus mixer. Enables DAW-style multi-track mixing.

See `MediaCenter/Codec/` for the existing workers and `Librarys/Media/Library.CodecRing.ailang` for the ring protocol.

### 9. Disk Installer

**Impact: Medium | Difficulty: Low-Medium**

A dedicated installer application that runs from a live USB and installs AILang OS to a target disk:

- Detect available disks, show sizes, warn about data loss
- Partition with GPT (200MB EFI + rest as ext4 rootfs)
- Set the correct PARTUUID to match the kernel cmdline
- Copy rootfs contents, set up EFI boot
- Run the existing first-boot Installer for user account creation

The partitioning logic already works (we use sfdisk). This is primarily UI and orchestration.

### 10. Boot Performance

**Impact: Low-Medium | Difficulty: Low**

Current boot: 11 seconds to desktop (17 with UEFI splash). The main bottleneck is modprobe scanning every PCI device on every boot. Optimization:

- **Module caching** — First boot: scan PCI, load all matching modules, save the list to `/etc/ailang_modules.cache`. Subsequent boots: load from cache. Background rescan after desktop is up.
- **Parallel service startup** — PostgreSQL and SSH can start concurrently. Network setup can overlap with module loading.
- **Deferred WiFi** — Don't block boot on WiFi association. Connect in the background after the desktop is up.

The boot sequence is in `OS/Init.ailang`, functions `Init_LoadModulesAuto()` (line ~438) and `Init_SetupNetwork()` (line ~970).

## Development Setup

### Requirements
- Linux x86-64 host machine
- The `ailang.x` compiler (in the repository root)
- For codec workers: `gcc`, `pkg-config`, `libavcodec-dev`, `libavutil-dev`, `libswresample-dev`, `libswscale-dev`
- For testing on hardware: a UEFI x86-64 machine, USB stick (2GB+)

### Building

```bash
# Compile any AILang program
./ailang.x Applications/terminal_ipc.ailang -o /tmp/terminal.x

# Compile all OS components and deploy to target
./deploy.sh 10.0.0.2

# Compile just one component
./deploy.sh 10.0.0.2 terminal

# Build codec workers (C, uses Makefile)
cd MediaCenter/Codec && make

# Create a bootable disk image
# (see OS/BUILD.md for full image build instructions)
```

### Testing on Real Hardware

Flash the disk image to a USB stick:
```bash
xz -d ailang_os_live.img.xz
dd if=ailang_os_live.img of=/dev/sdX bs=4M status=progress
```

Boot from USB on any UEFI x86-64 machine. Default login credentials are set during first-boot installation.

### Project Conventions

- **No libc.** AILang programs emit raw syscalls. The compiler handles everything.
- **Codec workers are C.** The `MediaCenter/Codec/` directory contains thin C wrappers around libavcodec. These are the only C code in the project.
- **PostgreSQL is the source of truth.** Don't store configuration in flat files. Use the `settings` table.
- **IPC is JSON over Unix sockets.** Length-prefixed (4-byte big-endian header). Keep messages small.
- **UI is HTML config + IPC.** Window layouts are declared in XML/HTML files in `config/`. Applications update them via IPC setlabel/addline/clear messages.
- **One binary per application.** Each app is a standalone ELF. No shared libraries, no dynamic linking (for AILang binaries).

## Getting Started

1. Read `INTRODUCTION.md` for the full architecture overview.
2. Read `PROGRAMMING_GUIDE.md` to understand AILang syntax.
3. Pick an area from the list above that interests you.
4. Read the relevant source files. The code is the documentation.
5. Submit changes upstream per the SCSL license terms.

## Contact

- Sean Collins — `smc.collins1977@gmail.com`
- Repository: [Codeberg](https://codeberg.org) (AILang OS)
- License: Sean Collins Software License (SCSL v1.0) — see `License.md`
