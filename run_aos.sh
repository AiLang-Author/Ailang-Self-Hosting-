#!/bin/sh
# Boot AILang OS in QEMU. Guest FB is 1152x864 (bochs-display EDID).
# virtio-vga ignores xres/yres on this QEMU and stays 640x480.
set -e
IMAGES=/home/bob/buildroot/output/images
DISK=$IMAGES/ailang_os.img
OVMF_CODE=/usr/share/OVMF/OVMF_CODE_4M.fd
OVMF_VARS=/usr/share/OVMF/OVMF_VARS_4M.fd
cp "$OVMF_VARS" /tmp/ovmf_vars.fd

exec qemu-system-x86_64 \
  -enable-kvm \
  -m 2G -smp 2 \
  -drive if=pflash,format=raw,readonly=on,unit=0,file="$OVMF_CODE" \
  -drive if=pflash,format=raw,unit=1,file=/tmp/ovmf_vars.fd \
  -drive file="$DISK",format=raw,if=none,id=disk0,snapshot=on \
  -device virtio-blk-pci,drive=disk0 \
  -vga none \
  -device bochs-display,edid=on,xres=1152,yres=864,xmax=1152,ymax=864 \
  -device qemu-xhci -device usb-kbd -device usb-mouse \
  -nic user,model=virtio-net-pci,hostfwd=tcp::2222-:22,hostfwd=tcp::15432-:5432 \
  -serial file:/tmp/qemu_serial.log \
  -display gtk \
  -name "AILang OS"
