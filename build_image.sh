#!/bin/bash
# build_image.sh — Build AILang OS disk image from source
#
# Usage:
#   ./build_image.sh                  # full build (compile + image)
#   ./build_image.sh --image-only     # skip compilation, just rebuild image
#   ./build_image.sh --flash /dev/sdX # build + flash to USB
#   ./build_image.sh --qemu           # build + boot QEMU
#
# Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
set -e
cd "$(dirname "$0")"

# =============================================================================
# CONFIGURATION — edit these if paths change
# =============================================================================
BUILDROOT="/home/bob/buildroot"
OVERLAY="$BUILDROOT/board/ailang_os/rootfs_overlay"
IMAGES="$BUILDROOT/output/images"
TARGET_DIR="$BUILDROOT/output/target"

# AILang compiler
AILANG="./ailang.x"

# Disk image layout (GPT)
#   Partition 1: EFI System (FAT32) — sectors 2048..409599
#   Partition 2: Linux rootfs (ext4) — sectors 409600..end
#   PARTUUID for P2 must match kernel baked-in cmdline
DISK_IMAGE="$IMAGES/ailang_os.img"
ROOTFS_IMAGE="$IMAGES/rootfs.ext2"
KERNEL="$IMAGES/bzImage"
EFI_START_SECTOR=2048
EFI_END_SECTOR=409599
ROOTFS_START_SECTOR=409600
IMAGE_SIZE_MB=2500
PARTUUID="c49ed437-68e9-45a0-8988-c8fd735b40c1"

# OVMF firmware for QEMU EFI boot
OVMF_CODE="/usr/share/OVMF/OVMF_CODE_4M.fd"
OVMF_VARS="/usr/share/OVMF/OVMF_VARS_4M.fd"

# =============================================================================
# HELPERS
# =============================================================================
RED='\033[0;31m'
GRN='\033[0;32m'
YEL='\033[0;33m'
CYN='\033[0;36m'
RST='\033[0m'

info()  { echo -e "${CYN}[INFO]${RST}  $*"; }
ok()    { echo -e "${GRN}[OK]${RST}    $*"; }
warn()  { echo -e "${YEL}[WARN]${RST}  $*"; }
fail()  { echo -e "${RED}[FAIL]${RST}  $*"; exit 1; }

# =============================================================================
# PARSE ARGS
# =============================================================================
IMAGE_ONLY=0
FLASH_DEV=""
RUN_QEMU=0

while [ $# -gt 0 ]; do
    case "$1" in
        --image-only) IMAGE_ONLY=1 ;;
        --flash)      shift; FLASH_DEV="$1" ;;
        --qemu)       RUN_QEMU=1 ;;
        --help|-h)
            echo "Usage: $0 [--image-only] [--flash /dev/sdX] [--qemu]"
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

# =============================================================================
# STEP 1: COMPILE BINARIES (unless --image-only)
# =============================================================================
if [ "$IMAGE_ONLY" -eq 0 ]; then
    info "Step 1: Compiling AILang binaries"

    if [ ! -x "$AILANG" ]; then
        fail "AILang compiler not found: $AILANG"
    fi

    # Init (PID 1)
    info "  Compiling ailang_init..."
    $AILANG OS/Init.ailang -o /tmp/ailang_init 2>&1 | tail -1
    cp /tmp/ailang_init "$OVERLAY/sbin/ailang_init"
    chmod +x "$OVERLAY/sbin/ailang_init"
    ok "  ailang_init ($(stat -c%s /tmp/ailang_init) bytes)"

    # Display server
    info "  Compiling display.x..."
    $AILANG Main.ailang -o /tmp/display.x 2>&1 | tail -1
    cp /tmp/display.x "$OVERLAY/system/bin/display.x"
    chmod +x "$OVERLAY/system/bin/display.x"
    ok "  display.x ($(stat -c%s /tmp/display.x) bytes)"

    # IDE
    if [ -f "Applications/ide_ipc.ailang" ]; then
        info "  Compiling ide.x..."
        $AILANG Applications/ide_ipc.ailang -o /tmp/ide.x 2>&1 | tail -1
        cp /tmp/ide.x "$OVERLAY/system/bin/ide.x"
        chmod +x "$OVERLAY/system/bin/ide.x"
        ok "  ide.x ($(stat -c%s /tmp/ide.x) bytes)"
    fi

    # Copy config files
    info "  Syncing config files to overlay..."
    for f in config/*.html config/*.cfg; do
        [ -f "$f" ] && cp "$f" "$OVERLAY/$f"
    done
    ok "  Config files synced"
else
    info "Step 1: SKIPPED (--image-only)"
fi

# =============================================================================
# STEP 2: BUILD ROOTFS
# =============================================================================
info "Step 2: Building rootfs"

# WORKAROUND: buildroot fails if ld.so.conf exists in target
# The overlay has ld.so.conf for the running system, but buildroot
# barfs if it sees one during image creation.
rm -f  "$TARGET_DIR/etc/ld.so.conf"
rm -rf "$TARGET_DIR/etc/ld.so.conf.d"

# Also remove stale binaries so overlay versions take precedence
rm -f "$TARGET_DIR/sbin/ailang_init"
rm -f "$TARGET_DIR/system/bin/display.x"

cd "$BUILDROOT"
make rootfs-ext2 2>&1 | tail -3
cd "$(dirname "$0")"

if [ ! -f "$ROOTFS_IMAGE" ]; then
    fail "rootfs build failed: $ROOTFS_IMAGE not found"
fi
ok "rootfs built ($(stat -c%s "$ROOTFS_IMAGE") bytes)"

# =============================================================================
# STEP 3: BUILD DISK IMAGE
# =============================================================================
info "Step 3: Building disk image"

# Check if disk image exists with correct partition layout
NEED_NEW_IMAGE=0
if [ ! -f "$DISK_IMAGE" ]; then
    NEED_NEW_IMAGE=1
    info "  No existing disk image, creating new one"
else
    # Verify partition 2 starts at expected sector
    P2_START=$(parted -s "$DISK_IMAGE" unit s print 2>/dev/null | grep "^ 2" | awk '{print $2}' | tr -d 's')
    if [ "$P2_START" != "$ROOTFS_START_SECTOR" ]; then
        NEED_NEW_IMAGE=1
        warn "  Partition 2 at sector $P2_START, expected $ROOTFS_START_SECTOR — recreating"
    fi
fi

if [ "$NEED_NEW_IMAGE" -eq 1 ]; then
    info "  Creating ${IMAGE_SIZE_MB}MB disk image..."
    dd if=/dev/zero of="$DISK_IMAGE" bs=1M count=$IMAGE_SIZE_MB 2>/dev/null

    info "  Creating GPT partition table..."
    # EFI partition: sectors 2048-409599 (200MB)
    # Rootfs partition: sector 409600 to end
    EFI_END_BYTES=$(( (EFI_END_SECTOR + 1) * 512 ))
    ROOTFS_START_BYTES=$(( ROOTFS_START_SECTOR * 512 ))
    parted -s "$DISK_IMAGE" mklabel gpt
    parted -s "$DISK_IMAGE" mkpart EFI fat32 ${EFI_START_SECTOR}s ${EFI_END_SECTOR}s
    parted -s "$DISK_IMAGE" set 1 esp on
    parted -s "$DISK_IMAGE" mkpart rootfs ext4 ${ROOTFS_START_SECTOR}s 100%

    info "  Patching PARTUUID to $PARTUUID..."
    python3 -c "
import struct, uuid, zlib
TARGET = uuid.UUID('$PARTUUID')
with open('$DISK_IMAGE', 'r+b') as f:
    f.seek(512); hdr = bytearray(f.read(512))
    part_lba = struct.unpack_from('<Q', hdr, 72)[0]
    num_parts = struct.unpack_from('<I', hdr, 80)[0]
    part_size = struct.unpack_from('<I', hdr, 84)[0]
    backup_lba = struct.unpack_from('<Q', hdr, 32)[0]
    f.seek(part_lba * 512); entries = bytearray(f.read(num_parts * part_size))
    entries[part_size+16:part_size+32] = TARGET.bytes_le
    part_crc = zlib.crc32(bytes(entries)) & 0xFFFFFFFF
    f.seek(part_lba * 512); f.write(bytes(entries))
    struct.pack_into('<I', hdr, 88, part_crc)
    hdr[16:20] = b'\\x00\\x00\\x00\\x00'
    hdr_crc = zlib.crc32(bytes(hdr[:92])) & 0xFFFFFFFF
    struct.pack_into('<I', hdr, 16, hdr_crc)
    f.seek(512); f.write(bytes(hdr))
    bp_lba = backup_lba - (num_parts * part_size + 511) // 512
    f.seek(bp_lba * 512); f.write(bytes(entries))
    f.seek(backup_lba * 512); bhdr = bytearray(f.read(512))
    struct.pack_into('<I', bhdr, 88, part_crc)
    bhdr[16:20] = b'\\x00\\x00\\x00\\x00'
    bhdr_crc = zlib.crc32(bytes(bhdr[:92])) & 0xFFFFFFFF
    struct.pack_into('<I', bhdr, 16, bhdr_crc)
    f.seek(backup_lba * 512); f.write(bytes(bhdr))
"

    info "  Creating EFI partition (FAT32 + kernel)..."
    EFI_SECTORS=$(( EFI_END_SECTOR - EFI_START_SECTOR + 1 ))
    dd if=/dev/zero of=/tmp/efi_part.img bs=512 count=$EFI_SECTORS 2>/dev/null
    mkfs.vfat -F 32 /tmp/efi_part.img >/dev/null 2>&1
    mmd -i /tmp/efi_part.img ::EFI
    mmd -i /tmp/efi_part.img ::EFI/BOOT
    mcopy -i /tmp/efi_part.img "$KERNEL" ::EFI/BOOT/BOOTX64.EFI
    dd if=/tmp/efi_part.img of="$DISK_IMAGE" bs=512 seek=$EFI_START_SECTOR conv=notrunc 2>/dev/null
    rm -f /tmp/efi_part.img

    ok "  New disk image created"
fi

# Write rootfs at correct partition offset
info "  Writing rootfs at sector $ROOTFS_START_SECTOR..."
dd if="$ROOTFS_IMAGE" of="$DISK_IMAGE" bs=512 seek=$ROOTFS_START_SECTOR conv=notrunc 2>/dev/null
ok "  Rootfs written"

# Verify
info "  Verifying image..."
P2_CHECK=$(parted -s "$DISK_IMAGE" unit s print 2>/dev/null | grep "^ 2" | awk '{print $2}' | tr -d 's')
if [ "$P2_CHECK" != "$ROOTFS_START_SECTOR" ]; then
    fail "Partition 2 verification failed: at sector $P2_CHECK, expected $ROOTFS_START_SECTOR"
fi
ok "Disk image ready: $DISK_IMAGE ($(du -h "$DISK_IMAGE" | cut -f1))"

# Print layout summary
echo ""
echo "  Disk layout:"
parted -s "$DISK_IMAGE" unit s print 2>/dev/null | grep -E "Number|^ [12]"
echo "  PARTUUID P2: $PARTUUID"
echo ""

# =============================================================================
# STEP 4: FLASH (if --flash)
# =============================================================================
if [ -n "$FLASH_DEV" ]; then
    if [ ! -b "$FLASH_DEV" ]; then
        fail "$FLASH_DEV is not a block device"
    fi
    info "Step 4: Flashing to $FLASH_DEV"
    warn "  This will ERASE $FLASH_DEV. Press Ctrl-C within 3 seconds to abort."
    sleep 3
    sudo dd if="$DISK_IMAGE" of="$FLASH_DEV" bs=4M status=progress conv=fsync
    ok "Flashed to $FLASH_DEV"
fi

# =============================================================================
# STEP 5: QEMU (if --qemu)
# =============================================================================
if [ "$RUN_QEMU" -eq 1 ]; then
    info "Step 5: Booting QEMU (EFI)"

    if [ ! -f "$OVMF_CODE" ]; then
        fail "OVMF firmware not found: $OVMF_CODE"
    fi

    exec qemu-system-x86_64 \
        -enable-kvm \
        -m 2G \
        -drive if=pflash,format=raw,readonly=on,unit=0,file="$OVMF_CODE" \
        -drive if=pflash,format=raw,snapshot=on,unit=1,file="$OVMF_VARS" \
        -drive file="$DISK_IMAGE",format=raw,if=none,id=disk0,snapshot=on \
        -device virtio-blk-pci,drive=disk0 \
        -device virtio-vga,xres=1024,yres=768 \
        -device qemu-xhci -device usb-kbd -device usb-mouse \
        -nic user,model=virtio-net-pci,hostfwd=tcp::2222-:22,hostfwd=tcp::15432-:5432 \
        -display gtk
fi

ok "Build complete."
