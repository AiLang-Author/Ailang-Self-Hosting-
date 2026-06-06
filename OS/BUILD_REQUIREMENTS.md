# AILang OS — Build Requirements and Configuration

## QEMU Launch Requirements

```bash
qemu-system-x86_64 \
    -cpu max \
    -kernel /home/bob/buildroot/output/images/bzImage \
    -drive file=/home/bob/buildroot/output/images/rootfs.ext2,format=raw \
    -append "root=/dev/sda rw console=ttyS0,115200 net.ifnames=0 init=/sbin/ailang_init" \
    -m 512M \
    -netdev user,id=net0,hostfwd=tcp::2222-:22 \
    -device e1000,netdev=net0 \
    -serial file:/tmp/qemu_serial.log \
    -display gtk \
    -vga virtio \
    -daemonize
```

**Critical flags:**
- `-cpu max` — Required. The AILang compiler emits SSE2 instructions.
  QEMU's default `qemu64` CPU causes invalid opcode traps without this.
- `-vga virtio` — Framebuffer for the display server.
- `init=/sbin/ailang_init` — Custom init (not /sbin/init).

For UEFI boot from `ailang_os.img` (full disk image):
```bash
qemu-system-x86_64 \
    -cpu max \
    -bios /usr/share/ovmf/OVMF.fd \
    -drive file=ailang_os.img,format=raw,if=none,id=disk0 \
    -device ahci,id=ahci \
    -device ide-hd,drive=disk0,bus=ahci.0 \
    ...
```

The UEFI image has `STARTUP.NSH` with:
```
\EFI\BOOT\BOOTX64.EFI root=/dev/sda2 rw init=/sbin/ailang_init
```

## Rootfs Overlay Layout

All files under `buildroot/board/ailang_os/rootfs_overlay/` are copied
into the root filesystem during `make`.

```
rootfs_overlay/
  sbin/
    ailang_init             — PID 1 init binary (compiled from OS/Init.ailang)
  system/
    bin/                    — All application binaries
      display.x             — Display server (Main.ailang)
      svc_daemon.x          — Service daemon (OS/ServiceDaemon.ailang)
      terminal.x            — Terminal emulator (Applications/terminal_ipc.ailang)
      notepad.x             — Notepad (Applications/notepad_ipc.ailang)
      calc.x                — Calculator
      browser.x             — Browser
      chrome.x              — Chrome
      claude.x              — Claude Code
      vscode.x              — VS Code
      ladybird.x            — Ladybird
      grep.x                — Grep search
      ailang.x              — AILang compiler
      (+ coreutils: cat, ls, cp, mv, rm, grep, find, etc.)
    config/                 — HTML launch configs and UI config
      ui.cfg                — Theme, font, layout settings
      keymap.cfg            — MUST BE PRESENT (see below)
      terminal.html         — Terminal window definition
      notepad.html          — Notepad window definition
      (+ other app .html files)
    fonts/
      DejaVuSans.vif        — Primary UI font (vector format)
      AlteixSans.vif        — Secondary font
    icons/
      default.vif           — General icons (radix 16x16 pack)
      app_icons.vif         — Application icons (32x32 tvg pack)
      silver_atoms.vif      — System widget atoms (silver look)
  config/
    keymap.cfg              — CRITICAL: display server opens "config/keymap.cfg"
                              relative to cwd (which is / on boot).
                              Without this file, ALL keyboard character
                              translation returns 0 — no typing works.
    ui.cfg                  — Copy of system/config/ui.cfg
    *.html                  — Copies of system/config/*.html
```

## Config File: keymap.cfg

The display server's `KeyMap_Init()` loads `config/keymap.cfg` using a
**relative path** from the process working directory (`/`).
This means the file must exist at `/config/keymap.cfg` on the rootfs.

Source: `Ailang-Self-Hosting-/config/keymap.cfg`
Format:
```
key<scancode>=<ascii>       # normal key
key<scancode>s=<ascii>      # shift variant
```

If this file is missing, the serial log will show:
```
[KeyMap] no config/keymap.cfg, tables empty
```
and keyboard input will not produce characters (only special keys
like Enter, Backspace, arrows will work by scancode).

## PostgreSQL Setup

### Requirements
- PostgreSQL user `bob` with SUPERUSER privilege
- Database `ailang_system` owned by `bob`
- TCP connections enabled: `listen_addresses = '*'` in postgresql.conf
- Trust auth for local TCP: `host all all 127.0.0.1/32 trust` in pg_hba.conf
- Display server connects as: `PG_Connect("127.0.0.1", 5432, "ailang_system", "bob", "")`

### Schema

The schema is defined in `OS/Schema.ailang` and bootstrapped by `svc_daemon.x`
on startup via `Schema_Bootstrap()`. Tables:

| Table | Purpose |
|-------|---------|
| services | Registered applications (name, binary_path, autostart, priority) |
| files | Virtual filesystem tree (parent_id hierarchy, blob storage) |
| users | User accounts (username, password_hash, is_admin) |
| sessions | Active login sessions |
| settings | Key-value configuration (app_id, key, value) |
| service_status | Runtime PID/state tracking |
| encryption_keys | Per-service encryption keys |
| windows | Window geometry persistence |

### Seed Data (from Schema_SeedData)

Services seeded on first boot:
- `display_server` — `/system/bin/display.x` (autostart=true, priority=10)
- `notepad` — `/system/bin/notepad.x`
- `terminal` — `/system/bin/terminal.x`
- `files` — `internal:app.files`
- `calculator` — `/system/bin/calc.x`
- `chrome` — `/system/bin/chrome.x`

Additional services added manually or by installer:
- `browser`, `claude`, `vscode`, `ladybird`, `grep`, `canvas_demo`, `videoplayer`

### Manual PG Setup (if not using installer)

```bash
# On the VM via SSH:
psql -U postgres -c "CREATE USER bob WITH SUPERUSER;"
createdb -U postgres -O bob ailang_system
# Schema is auto-bootstrapped by svc_daemon on next start
```

## Boot Sequence

1. Kernel boots, mounts rootfs ext4 on /dev/sda (or /dev/sda2 for UEFI)
2. `/sbin/ailang_init` runs as PID 1
3. Mounts /proc, /sys, /tmp, /dev/shm, /dev/pts, /run
4. Network setup (lo + eth0 via udhcpc)
5. Login screen — reads evdev keyboard, validates credentials
6. PostgreSQL: initdb (first boot) or start
7. Starts sshd
8. Starts svc_daemon.x
9. svc_daemon bootstraps schema, launches autostart services (display.x)
10. display.x initializes framebuffer, deskbar, IPC broker, keymap
11. Desktop ready — apps launched from start menu via IPC

## Rebuilding

```bash
# From buildroot directory:
cd /home/bob/buildroot

# Compile an AILang binary:
/home/bob/Ailang-Self-Hosting-/ailang.x SOURCE.ailang -o OUTPUT.x

# Copy to overlay:
cp OUTPUT.x board/ailang_os/rootfs_overlay/system/bin/

# Rebuild rootfs:
make

# Images at output/images/rootfs.ext2 (and rootfs.ext4 symlink)
```

**WARNING:** Rebuilding rootfs wipes any runtime state persisted in the
image (PG data directory, user sessions, etc.) since it creates a fresh
filesystem from the overlay. To preserve PG data across rebuilds, either:
1. Use the installer to re-setup PG after rebuild, or
2. Back up /var/lib/postgresql/data before rebuild and restore after boot

## Known Issues

- `config/keymap.cfg` path is relative — must be at `/config/keymap.cfg` on rootfs
- QEMU default CPU (`qemu64`) lacks SSE2 — use `-cpu max`
- PG data is lost on rootfs rebuild — installer needed to re-bootstrap
- svc_daemon only seeds 6 services; others must be added via installer or SQL
