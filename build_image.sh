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

# Compile an AILang source file and abort on failure
# Usage: compile <source> <output>
compile() {
    local src="$1" out="$2"
    rm -f "$out"
    $AILANG "$src" -o "$out" 2>&1 | tail -1
    if [ ! -f "$out" ]; then
        echo ""
        echo -e "${RED}[FAIL]${RST}  Compilation failed for: $src"
        echo -e "${RED}[FAIL]${RST}  Re-running with full output:"
        $AILANG "$src" -o "$out" 2>&1 | tail -20
        exit 1
    fi
}

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
    compile OS/Init.ailang /tmp/ailang_init
    cp /tmp/ailang_init "$OVERLAY/sbin/ailang_init"
    chmod +x "$OVERLAY/sbin/ailang_init"
    ok "  ailang_init ($(stat -c%s /tmp/ailang_init) bytes)"

    # Display server
    info "  Compiling display.x..."
    compile Main.ailang /tmp/display.x
    cp /tmp/display.x "$OVERLAY/system/bin/display.x"
    chmod +x "$OVERLAY/system/bin/display.x"
    ok "  display.x ($(stat -c%s /tmp/display.x) bytes)"

    # Login
    info "  Compiling login.x..."
    compile OS/Login.ailang /tmp/login.x
    cp /tmp/login.x "$OVERLAY/system/bin/login.x"
    chmod +x "$OVERLAY/system/bin/login.x"
    ok "  login.x ($(stat -c%s /tmp/login.x) bytes)"

    # IDE
    if [ -f "Applications/ide_ipc.ailang" ]; then
        info "  Compiling ide.x..."
        compile Applications/ide_ipc.ailang /tmp/ide.x
        cp /tmp/ide.x "$OVERLAY/system/bin/ide.x"
        chmod +x "$OVERLAY/system/bin/ide.x"
        ok "  ide.x ($(stat -c%s /tmp/ide.x) bytes)"
    fi

    # Settings
    if [ -f "Applications/settings_ipc.ailang" ]; then
        info "  Compiling settings.x..."
        compile Applications/settings_ipc.ailang /tmp/settings.x
        cp /tmp/settings.x "$OVERLAY/system/bin/settings.x"
        chmod +x "$OVERLAY/system/bin/settings.x"
        ok "  settings.x ($(stat -c%s /tmp/settings.x) bytes)"
    fi

    # Service Daemon
    info "  Compiling svc_daemon.x..."
    compile OS/ServiceDaemon.ailang /tmp/svc_daemon.x
    cp /tmp/svc_daemon.x "$OVERLAY/system/bin/svc_daemon.x"
    chmod +x "$OVERLAY/system/bin/svc_daemon.x"
    ok "  svc_daemon.x ($(stat -c%s /tmp/svc_daemon.x) bytes)"

    # User Management
    if [ -f "Applications/usermgmt_ipc.ailang" ]; then
        info "  Compiling usermgmt.x..."
        compile Applications/usermgmt_ipc.ailang /tmp/usermgmt.x
        cp /tmp/usermgmt.x "$OVERLAY/system/bin/usermgmt.x"
        chmod +x "$OVERLAY/system/bin/usermgmt.x"
        ok "  usermgmt.x ($(stat -c%s /tmp/usermgmt.x) bytes)"
    fi

    # Installer
    if [ -f "Applications/installer_ipc.ailang" ]; then
        info "  Compiling installer_ipc.x..."
        compile Applications/installer_ipc.ailang /tmp/installer_ipc.x
        cp /tmp/installer_ipc.x "$OVERLAY/system/bin/installer_ipc.x"
        chmod +x "$OVERLAY/system/bin/installer_ipc.x"
        ok "  installer_ipc.x ($(stat -c%s /tmp/installer_ipc.x) bytes)"
    fi

    # Desktop IPC apps — clipboard lives in display.x; terminal/chrome must
    # be rebuilt so they speak clipboard.set/get/paste.
    for pair in \
        "Applications/terminal_ipc.ailang:terminal.x" \
        "Applications/notepad_ipc.ailang:notepad.x" \
        "Applications/chrome_ipc.ailang:chrome.x" \
        "Applications/calc_ipc.ailang:calc.x" \
        "Applications/grep_ipc.ailang:grep.x" \
        "Applications/wifi_ipc.ailang:wifi_ipc.x" \
        "Applications/browser_ipc.ailang:browser.x" \
        "Applications/vscode_ipc.ailang:vscode.x" \
        "Applications/deskbar_ipc.ailang:deskbar.x" \
        "Applications/document_ipc.ailang:document.x"
    do
        src="${pair%%:*}"
        bin="${pair##*:}"
        if [ -f "$src" ]; then
            info "  Compiling $bin..."
            compile "$src" "/tmp/$bin"
            cp "/tmp/$bin" "$OVERLAY/system/bin/$bin"
            chmod +x "$OVERLAY/system/bin/$bin"
            ok "  $bin ($(stat -c%s /tmp/$bin) bytes)"
        fi
    done

    # Telegram (TDLib worker + libtdjson)
    if [ -f "Telegram/tdlib_worker.c" ]; then
        info "  Building Telegram TDLib worker..."
        if [ ! -f "Telegram/tdlib-install/lib/libtdjson.so" ]; then
            chmod +x Telegram/build_tdlib.sh
            Telegram/build_tdlib.sh --skip-clone
        else
            make -C Telegram
        fi
        make -C Telegram install DESTDIR="$OVERLAY"
        ok "  Telegram worker + libtdjson installed to overlay"
    fi

    # Copy config files
    info "  Syncing config files to overlay..."
    for f in config/*.html config/*.cfg config/*.json; do
        [ -f "$f" ] && cp "$f" "$OVERLAY/$f"
        [ -f "$f" ] && cp "$f" "$OVERLAY/system/$f"
    done
    ok "  Config files synced"

    if [ -d "icons/chrome" ]; then
        info "  Syncing chrome icons..."
        mkdir -p "$OVERLAY/system/icons/chrome"
        cp -a icons/chrome/*.svg icons/chrome/*.tvg "$OVERLAY/system/icons/chrome/" 2>/dev/null || true
        ok "  Chrome icons synced"
    fi
    if [ -d "icons" ]; then
        info "  Syncing icon packs..."
        mkdir -p "$OVERLAY/system/icons"
        for vif in icons/*.vif; do
            [ -f "$vif" ] && cp "$vif" "$OVERLAY/system/icons/"
        done
        ok "  Icon packs synced"
    fi
else
    info "Step 1: SKIPPED (--image-only)"
fi

# =============================================================================
# STEP 1b: PRE-POPULATE POSTGRESQL DATA DIRECTORY
# Build a ready-to-boot PG data dir with schema + base services baked in.
# At runtime, Init just starts PG — no schema bootstrap needed.
# =============================================================================
PGDATA_OVERLAY="$OVERLAY/var/lib/postgresql/data"
SCHEMA_SQL="$OVERLAY/system/schema.sql"
PG_BUILD_PORT=54321
PGBIN="/usr/lib/postgresql/16/bin"

if [ -f "$SCHEMA_SQL" ]; then
    info "Step 1b: Pre-populating PostgreSQL data directory"

    # Clean previous data dir
    rm -rf "$PGDATA_OVERLAY"
    mkdir -p "$PGDATA_OVERLAY"

    # initdb
    "$PGBIN/initdb" -D "$PGDATA_OVERLAY" -U postgres --no-locale --encoding=UTF8 > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        fail "initdb failed"
    fi

    # Configure for local trust auth
    cat > "$PGDATA_OVERLAY/pg_hba.conf" << 'HBAEOF'
local all all trust
host all all 127.0.0.1/32 trust
host all all ::1/128 trust
HBAEOF

    # Listen on all interfaces (matches Init_InitPGData behavior), use non-conflicting port for build
    sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '0.0.0.0'/" "$PGDATA_OVERLAY/postgresql.conf"
    sed -i "s/#port = 5432/port = $PG_BUILD_PORT/" "$PGDATA_OVERLAY/postgresql.conf"

    # Use /tmp for unix socket during build (avoids /var/run/postgresql permission issues)
    mkdir -p /tmp/pg_build_sock
    echo "unix_socket_directories = '/tmp/pg_build_sock'" >> "$PGDATA_OVERLAY/postgresql.conf"

    # Start temp PG instance
    "$PGBIN/pg_ctl" start -D "$PGDATA_OVERLAY" -l /tmp/pg_build.log -w -o "-p $PG_BUILD_PORT" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        cat /tmp/pg_build.log
        fail "Failed to start temp PostgreSQL"
    fi

    # Create database + user
    "$PGBIN/createdb" -h 127.0.0.1 -p $PG_BUILD_PORT -U postgres ailang_system 2>/dev/null
    "$PGBIN/psql" -h 127.0.0.1 -p $PG_BUILD_PORT -U postgres -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='bob') THEN CREATE ROLE bob SUPERUSER LOGIN; END IF; END \$\$;" > /dev/null 2>&1

    # Load schema
    "$PGBIN/psql" -h 127.0.0.1 -p $PG_BUILD_PORT -U postgres -d ailang_system -f "$SCHEMA_SQL" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        "$PGBIN/pg_ctl" stop -D "$PGDATA_OVERLAY" -m fast > /dev/null 2>&1
        fail "Schema load failed"
    fi

    # Verify services were loaded
    SVC_COUNT=$("$PGBIN/psql" -h 127.0.0.1 -p $PG_BUILD_PORT -U postgres -d ailang_system -t -c "SELECT count(*) FROM services" 2>/dev/null | tr -d ' ')
    ok "  Schema loaded: $SVC_COUNT services registered"

    # Stop temp PG
    "$PGBIN/pg_ctl" stop -D "$PGDATA_OVERLAY" -m fast > /dev/null 2>&1

    # Reset port and socket dir back to defaults for runtime
    sed -i "s/port = $PG_BUILD_PORT/#port = 5432/" "$PGDATA_OVERLAY/postgresql.conf"
    sed -i "/unix_socket_directories = '\/tmp\/pg_build_sock'/d" "$PGDATA_OVERLAY/postgresql.conf"
    rm -rf /tmp/pg_build_sock /tmp/pg_build.log

    # Write runtime pg_hba.conf (trust auth, role-aware)
    cat > "$PGDATA_OVERLAY/pg_hba.conf" << 'HBAEOF'
local all postgres trust
local all bob trust
host all all 127.0.0.1/32 trust
host all all ::1/128 trust
host all all 10.0.2.0/24 trust
HBAEOF

    # Ownership: data dir is owned by host user (bob) in overlay.
    # ailang_init does chown -R postgres:postgres at runtime before starting PG.
    ok "  PostgreSQL data directory pre-populated"
else
    warn "Step 1b: SKIPPED — $SCHEMA_SQL not found"
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
        -vga none \
        -device bochs-display,edid=on,xres=1152,yres=864,xmax=1152,ymax=864 \
        -device qemu-xhci -device usb-kbd -device usb-mouse \
        -nic user,model=virtio-net-pci,hostfwd=tcp::2222-:22,hostfwd=tcp::15432-:5432 \
        -serial file:/tmp/qemu_serial.log \
        -display gtk
fi

ok "Build complete."
