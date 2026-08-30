#!/bin/sh
# Bind ONLY the compute HD7770 (02:00.0) to amdgpu for Mesa RADV.
# Leave the display HD7770 (01:00.0) on simple-framebuffer.
#
# Both cards share PCI ID 1002:683d. A naive modprobe will steal the
# display GPU and hard-lock X — that already happened once on this box.
#
# Does NOT delete GPU-VFIO-Test/bind_vfio.sh (that's the other project's
# kit). It clears vfio driver_override on the compute card only.
#
# Usage: sudo ./enable_compute_gpu_vulkan.sh
# Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
# Licensed under the Sean Collins Software License (SCSL v1.0).

set -eu

DISPLAY_GPU="0000:01:00.0"
COMPUTE_GPU="0000:02:00.0"
SYS=/sys/bus/pci/devices

die() { echo "[gpu-vk] ERROR: $*" >&2; exit 1; }

if [ "$(id -u)" -ne 0 ]; then
    die "must run as root (sudo). This script only touches $COMPUTE_GPU."
fi

[ -d "$SYS/$DISPLAY_GPU" ] || die "display GPU $DISPLAY_GPU missing"
[ -d "$SYS/$COMPUTE_GPU" ] || die "compute GPU $COMPUTE_GPU missing"

echo "[gpu-vk] pinning display GPU $DISPLAY_GPU away from amdgpu"
# driver_override=vfio-pci means amdgpu will not auto-bind this device.
echo vfio-pci > "$SYS/$DISPLAY_GPU/driver_override"

# If someone already bound vfio to the compute card, let it go.
if [ -e "$SYS/$COMPUTE_GPU/driver" ]; then
    cur=$(basename "$(readlink -f "$SYS/$COMPUTE_GPU/driver")")
    if [ "$cur" = "vfio-pci" ]; then
        echo "[gpu-vk] unbinding $COMPUTE_GPU from vfio-pci"
        echo "$COMPUTE_GPU" > "$SYS/$COMPUTE_GPU/driver/unbind"
    fi
fi
echo amdgpu > "$SYS/$COMPUTE_GPU/driver_override"

# Cmdline blacklists amdgpu. modprobe honors that; insmod does not.
# Load deps via modprobe (those are not blacklisted), then insmod amdgpu.
KVER=$(uname -r)
KO="/lib/modules/$KVER/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko"
if [ ! -f "$KO" ]; then
    if [ -f "$KO.zst" ]; then
        TMP=$(mktemp /tmp/amdgpu.XXXXXX.ko)
        zstd -dc "$KO.zst" > "$TMP"
        KO="$TMP"
    else
        die "amdgpu.ko not found for $KVER"
    fi
fi

echo "[gpu-vk] loading amdgpu deps"
# Best-effort; already-loaded is fine.
for m in drm drm_kms_helper ttm gpu-sched drm_exec drm_buddy \
         drm_suballoc_helper drm_ttm_helper drm_display_helper \
         drm_panel_backlight_quirks cec video i2c-algo-bit amdxcp; do
    modprobe "$m" 2>/dev/null || true
done

if ! lsmod | grep -q '^amdgpu '; then
    echo "[gpu-vk] insmod amdgpu si_support=1 dc=0 audio=0 (compute only)"
    insmod "$KO" si_support=1 dc=0 audio=0 || die "insmod amdgpu failed — see dmesg"
fi

if [ ! -e "$SYS/$COMPUTE_GPU/driver" ]; then
    echo "[gpu-vk] binding $COMPUTE_GPU to amdgpu"
    echo "$COMPUTE_GPU" > /sys/bus/pci/drivers/amdgpu/bind || \
        die "amdgpu bind failed — see dmesg"
fi

comp=$(basename "$(readlink -f "$SYS/$COMPUTE_GPU/driver" 2>/dev/null)" 2>/dev/null || echo none)
disp=$(basename "$(readlink -f "$SYS/$DISPLAY_GPU/driver" 2>/dev/null)" 2>/dev/null || echo none)
echo "[gpu-vk] compute $COMPUTE_GPU driver=$comp"
echo "[gpu-vk] display $DISPLAY_GPU driver=$disp (must NOT be amdgpu)"

if [ "$disp" = "amdgpu" ]; then
    echo "[gpu-vk] FATAL: amdgpu grabbed the display GPU. Unbinding it."
    echo "$DISPLAY_GPU" > /sys/bus/pci/drivers/amdgpu/unbind || true
    die "display GPU was claimed — desktop is at risk, check dmesg"
fi

if [ "$comp" != "amdgpu" ]; then
    die "compute GPU not on amdgpu"
fi

echo "[gpu-vk] /dev/dri:"
ls -l /dev/dri || true
echo "[gpu-vk] ready. Run: cd CAD/display3d && AILANG_VK_DEVICE=gpu make test"
