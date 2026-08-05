# AILang OS — Build Guide

## Quick Reference

```bash
# Full build (compile + rootfs + disk image)
./build_image.sh

# Rebuild image only (skip compilation)
./build_image.sh --image-only

# Build + flash to USB
./build_image.sh --flash /dev/sdX

# Build + boot QEMU
./build_image.sh --qemu

# Live deploy to running target over SSH
./deploy.sh 10.0.0.2 display        # just display server
./deploy.sh 10.0.0.2                 # everything

# Boot QEMU from existing disk image
~/buildroot/board/ailang_os/run_qemu.sh
```

## Prerequisites

### Host machine (Ubuntu/Pop!_OS)

```bash
sudo apt install qemu-system-x86 ovmf parted mtools python3
```

### Buildroot

Buildroot lives at `/home/bob/buildroot` with the AILang OS board config:

| Buildroot setting | Value |
|---|---|
| Defconfig | `configs/ailang_os_defconfig` |
| Kernel config | `board/ailang_os/linux_alldrv.config` |
| Rootfs overlay | `board/ailang_os/rootfs_overlay` |
| Post-build script | `board/ailang_os/post_build.sh` |
| Rootfs size | 2 GB |

### AILang compiler

The compiler binary `ailang.x` must exist in the repo root (`/home/bob/Ailang-Self-Hosting-/ailang.x`).

## Disk Image Layout

GPT partition table, 2500 MB total:

| Partition | Type | Start sector | End sector | Size | Filesystem |
|---|---|---|---|---|---|
| 1 (EFI) | EFI System | 2048 | 409599 | ~200 MB | FAT32 |
| 2 (rootfs) | Linux | **409600** | end | ~2300 MB | ext4 |

**CRITICAL**: Partition 2 starts at **sector 409600**. All dd commands writing rootfs must use `seek=409600`. Getting this wrong causes kernel panic (VFS unable to mount root).

Partition 2 PARTUUID: `c49ed437-68e9-45a0-8988-c8fd735b40c1`

This PARTUUID is baked into the kernel cmdline (`CONFIG_CMDLINE_OVERRIDE=y`):

```
root=PARTUUID=c49ed437-68e9-45a0-8988-c8fd735b40c1 rootwait rw
init=/sbin/ailang_init console=tty0 loglevel=3
fbcon=map: vt.global_cursor_default=0 net.ifnames=0
```

## What Gets Compiled

| Binary | Source | Destination (overlay) | Destination (target) |
|---|---|---|---|
| ailang_init | `OS/Init.ailang` | `sbin/ailang_init` | `/sbin/ailang_init` |
| display.x | `Main.ailang` | `system/bin/display.x` | `/system/bin/display.x` |
| ide.x | `Applications/ide_ipc.ailang` | `system/bin/ide.x` | `/system/bin/ide.x` |

## Build Pipeline (what build_image.sh does)

### Step 1: Compile AILang binaries

```
ailang.x OS/Init.ailang      -> /tmp/ailang_init -> overlay/sbin/ailang_init
ailang.x Main.ailang          -> /tmp/display.x  -> overlay/system/bin/display.x
ailang.x Applications/ide_ipc.ailang -> /tmp/ide.x -> overlay/system/bin/ide.x
```

Config files from `config/*.html` and `config/*.cfg` are also synced to the overlay.

### Step 2: Build rootfs

```bash
# Workaround: buildroot fails if ld.so.conf exists in target dir
rm -f  $BUILDROOT/output/target/etc/ld.so.conf
rm -rf $BUILDROOT/output/target/etc/ld.so.conf.d

# Also remove stale binaries so overlay versions win
rm -f $BUILDROOT/output/target/sbin/ailang_init
rm -f $BUILDROOT/output/target/system/bin/display.x

cd $BUILDROOT && make rootfs-ext2
```

This produces `output/images/rootfs.ext2` (2 GB).

### Step 3: Build disk image

If no disk image exists (or partition layout is wrong):
1. Create blank 2500 MB image with `dd`
2. Create GPT table with `parted` (EFI + rootfs partitions)
3. Patch partition 2 PARTUUID with Python script
4. Create FAT32 EFI partition with kernel as `EFI/BOOT/BOOTX64.EFI`

Then always:
5. Write rootfs.ext2 at sector 409600: `dd if=rootfs.ext2 of=ailang_os.img bs=512 seek=409600 conv=notrunc`
6. Verify partition 2 starts at sector 409600

### Step 4 (optional): Flash to USB

```bash
sudo dd if=output/images/ailang_os.img of=/dev/sdX bs=4M status=progress conv=fsync
sync
```

### Step 5 (optional): Boot QEMU

EFI boot using OVMF firmware. Uses `snapshot=on` so disk image is not modified.

## EFI Boot

The kernel (`bzImage`) is an EFI stub. It's placed on the EFI System Partition as `EFI/BOOT/BOOTX64.EFI`. UEFI firmware loads it directly — no bootloader (no GRUB, no systemd-boot).

The kernel cmdline is baked in at compile time (`CONFIG_CMDLINE_OVERRIDE=y`), so QEMU's `-append` flag has no effect.

## QEMU

AILang OS uses **EFI boot only**. Direct kernel boot (`-kernel`/`-append`) does
not work because `CONFIG_CMDLINE_OVERRIDE=y` bakes `root=PARTUUID=...` into the
kernel — QEMU's `-append` is ignored, and the PARTUUID won't resolve without GPT.

```bash
# EFI boot (default, matches real hardware)
~/buildroot/board/ailang_os/run_qemu.sh

# Port forwards: host:2222 -> vm:22 (SSH), host:15432 -> vm:5432 (PG)
# SSH: ssh -p 2222 root@localhost (password: ailang)
# PG:  psql -h localhost -p 15432 -U bob ailang_system
```

See `OS/BUILD_REQUIREMENTS.md` for the full QEMU command line reference.

## Live Deployment (deploy.sh)

For iterating on individual components without rebuilding the full image:

```bash
./deploy.sh <target-ip> [component ...]
```

Components: `init`, `display`, `ide`, `terminal`, `notepad`, `calc`, `grep`, `wifi`, `browser`, `chrome`, `installer`

This compiles the component, scps it to the target, and (for display) restarts the display server. Init changes require a reboot.

## Target Hardware

- Intel Celeron G3930 (Kaby Lake)
- UEFI boot from USB
- Network: ethernet (DHCP), static fallback 10.0.0.2
- SSH: `ssh root@10.0.0.2` (password: ailang)

## Known Issues / Gotchas

1. **ld.so.conf** — Do NOT put `ld.so.conf` in the rootfs overlay. Buildroot refuses to build if it finds one in the target directory. The running system creates it at boot via init.

2. **Partition offset** — The rootfs MUST be written at sector 409600. If you recreate the disk image with parted, always verify with `parted -s ailang_os.img unit s print` that partition 2 starts at 409600s.

3. **Stale binaries in target dir** — Buildroot's `output/target/` persists between builds. Old binaries there can override the overlay. The build script removes known stale paths before `make rootfs-ext2`.

4. **Kernel cmdline is immutable** — Changing root device, init path, or console requires rebuilding the kernel. `CONFIG_CMDLINE_OVERRIDE=y` means boot parameters cannot be changed at boot time.

5. **QEMU pflash units** — OVMF_CODE must be `unit=0`, OVMF_VARS must be `unit=1`. Omitting these causes "drive with bus=0, unit=0 exists" errors.
