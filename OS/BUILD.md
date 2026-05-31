# AILang OS — Build & Deploy Guide

## Architecture

AILang OS is a custom Linux-based operating system with:
- Custom PID 1 init (`Init.ailang` → `ailang_init`)
- PostgreSQL-backed service registry and settings
- Custom display server with window manager and compositor
- 15 windowed applications (IPC over Unix sockets)
- UEFI boot via EFI stub kernel (bzImage as BOOTX64.EFI)

### Disk Image Layout

```
ailang_os.img (2.5 GB GPT)
├── Partition 1: EFI System (200 MB, FAT32)
│   └── EFI/BOOT/BOOTX64.EFI    ← Linux bzImage with EFI stub
└── Partition 2: rootfs (2.1 GB, ext4)
    ├── /sbin/ailang_init         ← PID 1
    ├── /system/bin/              ← All AILang binaries
    ├── /config/                  ← HTML window configs
    ├── /usr/bin/postgres         ← PostgreSQL 16
    ├── /lib/modules/6.6.18/     ← Kernel modules (mt7921e WiFi)
    └── /lib/firmware/            ← Device firmware files
```

Root partition PARTUUID: `c49ed437-68e9-45a0-8988-c8fd735b40c1`

## Prerequisites

- **Host OS:** Ubuntu/Pop!_OS 22.04+ (x86_64)
- **Buildroot:** 2024.02.x (cloned separately, see below)
- **Tools:** `mtools`, `e2fsprogs`, `qemu-system-x86`, `ovmf`

```bash
sudo apt install mtools e2fsprogs qemu-system-x86 ovmf
```

## Buildroot Setup

```bash
# Clone buildroot (one-time)
cd ~
git clone https://gitlab.com/buildroot.org/buildroot.git
cd buildroot
git checkout 2024.02

# Copy board config from this repo
cp ~/Ailang-Self-Hosting-/board/ailang_os/linux_alldrv.config board/ailang_os/
cp ~/Ailang-Self-Hosting-/board/ailang_os/buildroot_defconfig .config

# Build base system (first build takes ~30-60 min)
make
```

### Key Buildroot Packages
- PostgreSQL 16 (`BR2_PACKAGE_POSTGRESQL=y`)
- OpenSSH (`BR2_PACKAGE_OPENSSH=y`)
- wpa_supplicant, iw, wireless-tools
- busybox (provides coreutils, modprobe, udhcpc, ifconfig, etc.)
- linux-firmware (MediaTek, Intel i915, regulatory.db)

### Kernel Config Highlights (`board/ailang_os/linux_alldrv.config`)
- `CONFIG_EFI_STUB=y` — Boot directly from UEFI
- `CONFIG_CMDLINE_OVERRIDE=y` — All boot params baked in
- `CONFIG_IP_PNP is not set` — Prevents boot hang without DHCP
- `CONFIG_MT7921E=m` — MediaTek WiFi as module (needs rootfs for firmware)
- `CONFIG_DRM_I915=y` — Intel HD Graphics built-in
- `CONFIG_HID_GENERIC=y` — USB keyboard/mouse support
- `CONFIG_FRAMEBUFFER_CONSOLE=y` — Console on framebuffer

## Compiling AILang Binaries

All AILang source compiles with the self-hosting compiler (`ailang.x`):

```bash
cd ~/Ailang-Self-Hosting-

# Core OS binaries
./ailang.x OS/Init.ailang      -o ailang_init
./ailang.x OS/Installer.ailang -o installer.x
./ailang.x OS/Login.ailang     -o login.x
./ailang.x OS/Schema.ailang    -o schema.x   # (compiled into Init)

# Display server + service daemon
./ailang.x Librarys/Display/System/Library.SysDisplay.ailang  # (compiled into display.x)
./ailang.x OS/ServiceDaemon.ailang -o svc_daemon.x

# Applications
./ailang.x Applications/terminal_ipc.ailang   -o terminal.x
./ailang.x Applications/notepad_ipc.ailang    -o notepad.x
./ailang.x Applications/calc_ipc.ailang       -o calc.x
./ailang.x Applications/grep_ipc.ailang       -o grep.x
./ailang.x Applications/wifi_ipc.ailang       -o wifi_ipc.x
./ailang.x Applications/browser_ipc.ailang    -o browser.x
./ailang.x Applications/chrome_ipc.ailang     -o chrome.x
./ailang.x Applications/ladybird_ipc.ailang   -o ladybird.x
./ailang.x Applications/claude_ipc.ailang     -o claude.x
./ailang.x Applications/vscode_ipc.ailang     -o vscode.x
./ailang.x Applications/installer_ipc.ailang  -o installer_ipc.x
```

## Deploying to Disk Image

### Rootfs Overlay (before buildroot `make`)

Place binaries and configs in the overlay directory. Buildroot copies these into the rootfs during image generation:

```bash
OVERLAY=~/buildroot/board/ailang_os/rootfs_overlay

# System binaries
cp ailang_init $OVERLAY/sbin/ailang_init
cp display.x svc_daemon.x installer.x ailang.x $OVERLAY/system/bin/
cp terminal.x notepad.x calc.x grep.x wifi_ipc.x $OVERLAY/system/bin/
cp browser.x chrome.x ladybird.x claude.x vscode.x $OVERLAY/system/bin/
cp installer_ipc.x $OVERLAY/system/bin/

# HTML configs
cp config/*.html $OVERLAY/config/
cp config/*.html $OVERLAY/system/config/
cp config/*.cfg  $OVERLAY/config/

# Rebuild rootfs
cd ~/buildroot && make rootfs-ext2
```

### Hot-patching an Existing Image (without full rebuild)

Use `debugfs` for rootfs and `mtools` for the EFI partition:

```bash
cd ~/buildroot/output/images

# 1. Check filesystem
e2fsck -f -y rootfs.ext2

# 2. Inject updated binary into rootfs
debugfs -w -R "rm /sbin/ailang_init" rootfs.ext2
debugfs -w -R "write /path/to/new/ailang_init /sbin/ailang_init" rootfs.ext2
debugfs -w -R "set_inode_field /sbin/ailang_init mode 0100755" rootfs.ext2

# 3. Write rootfs into full disk image (partition 2 starts at sector 411648)
dd if=rootfs.ext2 of=ailang_os.img bs=512 seek=411648 conv=notrunc

# 4. Update kernel on EFI partition
cat > /tmp/mtoolsrc << 'EOF'
drive E: file="/home/bob/buildroot/output/images/ailang_os.img" offset=1048576
EOF
MTOOLSRC=/tmp/mtoolsrc mcopy -o bzImage E:/EFI/BOOT/BOOTX64.EFI
```

### Live Update via SSH (no USB re-flash)

If the target is accessible over SSH (eth0 at 10.0.0.2 or wlan0):

```bash
# Push a single updated binary
scp new_binary.x root@10.0.0.2:/system/bin/

# Push updated init (requires reboot)
scp ailang_init root@10.0.0.2:/sbin/ailang_init

# Push updated config
scp config/terminal.html root@10.0.0.2:/config/
```

## Flashing to USB

```bash
# Identify USB device (NEVER use sda — that's the host disk)
lsblk

# Flash (replace sdX with your USB device)
sudo dd if=~/buildroot/output/images/ailang_os.img of=/dev/sdX bs=4M status=progress conv=fsync
```

## Testing in QEMU (UEFI Boot)

Matches real hardware boot path exactly:

```bash
cp /usr/share/OVMF/OVMF_VARS_4M.fd /tmp/ovmf_vars.fd

qemu-system-x86_64 \
  -m 2G -enable-kvm \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
  -drive if=pflash,format=raw,file=/tmp/ovmf_vars.fd \
  -drive file=~/buildroot/output/images/ailang_os.img,format=raw,if=none,id=disk0,snapshot=on \
  -device virtio-blk-pci,drive=disk0 \
  -device virtio-vga,xres=1440,yres=900 \
  -usb -device usb-kbd -device usb-mouse \
  -display gtk -no-reboot
```

Note: `-snapshot=on` means changes don't persist to the image file.

## Boot Sequence

1. UEFI firmware loads `EFI/BOOT/BOOTX64.EFI` (bzImage with EFI stub)
2. Kernel boots with built-in cmdline (CONFIG_CMDLINE_OVERRIDE)
3. `/sbin/ailang_init` (PID 1) runs:
   - Mounts filesystems (proc, sys, devtmpfs, tmpfs, devpts)
   - Creates `/dev/input/` directory
   - Loads WiFi kernel module (`modprobe mt7921e`)
   - Waits for input devices (USB HID enumeration)
   - Starts PostgreSQL
   - Runs schema bootstrap + service seeding
   - Configures networking (DHCP with static fallback)
   - Enables ICMP echo
   - Starts SSH daemon
   - Starts service daemon (`svc_daemon.x`)
   - Starts display server (`display.x`)
   - Enters zombie reaper loop

## Target Hardware (Reference Machine)

- **CPU:** Intel Celeron G3930 @ 2.90 GHz (Kaby Lake, 2 cores)
- **RAM:** 4 GB DDR4
- **GPU:** Intel HD Graphics 610 (i915)
- **Ethernet:** Realtek RTL8168 (r8169 driver)
- **WiFi:** MediaTek MT7961 PCIe (mt7921e driver, module)
- **WiFi 2:** Intel Dual Band Wireless-AC 3168 (iwlmvm — not yet enabled)
- **Bluetooth:** Intel (8087:0aa7 — not yet enabled)
- **Input:** HP 510 Wireless KBMS Combo (USB HID)
- **Display:** 1366x768 via HDMI

## SSH Access (Direct Ethernet)

```bash
# Dev machine (e.g., 10.0.0.1)
sudo ip addr add 10.0.0.1/24 dev enp6s0
sudo ip link set enp6s0 up

# Target gets 10.0.0.2 automatically (static fallback in init)
ssh root@10.0.0.2

# Optional: NAT forwarding so target can reach internet via dev's WiFi
sudo sysctl -w net.ipv4.ip_forward=1
sudo iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -o wlp4s0 -j MASQUERADE
```

---

## Known Issues / Punchlist

### P0 — Critical

| Issue | Detail |
|-------|--------|
| i915 DMC firmware fails at boot | Loads at 0.29s before rootfs mounted. File exists at `/lib/firmware/i915/kbl_dmc_ver1_04.bin` but kernel can't find it. Disables GPU runtime power management. Fix: build i915 as module or use initramfs. |
| regulatory.db fails at boot | Same timing issue — cfg80211 loads at 0.68s before rootfs. WiFi regulatory compliance disabled. |
| Hostname not set | `hostname` returns `(none)`. Settings DB has `hostname = ailang-os` but init never calls `sethostname()`. |
| WiFi no auto-connect | mt7921e module loads, wlan0 appears, but no wpa_supplicant starts. Need stored credentials + auto-connect logic in init or service daemon. |

### P1 — High

| Issue | Detail |
|-------|--------|
| canvas_demo.x missing | Registered in services DB but binary not compiled/deployed. |
| videoplayer.x missing | Same — registered but no binary. |
| Intel WiFi not enabled | CONFIG_IWLMVM not set. Intel 3168 card (8086:24fb) goes unused. |
| Bluetooth not working | Intel BT adapter on USB, needs CONFIG_BT + userspace tools. |
| packages table empty | Package manager schema exists (14 columns) but zero rows seeded. |
| Login screen disabled | Removed to debug boot issues; needs re-enabling with proper flow. |
| Installer-to-disk untested | The disk installer path has never been tested end-to-end. |

### P2 — Medium

| Issue | Detail |
|-------|--------|
| Timezone = UTC | No timezone configuration in init or settings. |
| No wallpaper | No wallpaper image file on the system. |
| Display locked 1366x768 | May be monitor native; modesetting not verified for other resolutions. |
| Audio hardware unused | HDA Intel PCH detected, `/dev/snd/` populated, no mixer/player app. |
| No user privilege separation | Everything runs as root. PostgreSQL needs proper user roles. |
| No binary encryption | Binaries deployed unencrypted. Encryption infrastructure exists in schema but unused. |

### P3 — Low

| Issue | Detail |
|-------|--------|
| GPT backup table warning | `Use GNU Parted to correct GPT errors` — cosmetic from dd. |
| Syslog empty | syslogd running but no messages logged. |
| No locale support | No locale command. Minor for embedded OS. |
| .gitattributes warnings | Invalid attribute names in .gitattributes (Programs/**, Docs\, Manuals/**). |

## Resources

- **Buildroot:** https://buildroot.org/docs.html
- **OVMF/UEFI:** https://github.com/tianocore/edk2
- **MT7921 firmware:** https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/tree/mediatek
- **i915 firmware:** https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/tree/i915
- **mtools (FAT32):** https://www.gnu.org/software/mtools/
- **debugfs (ext2/3/4):** Part of e2fsprogs
