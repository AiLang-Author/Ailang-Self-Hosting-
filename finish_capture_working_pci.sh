#!/bin/bash
#
# finish_capture_working_pci.sh — completes the interrupted capture_working_pci.sh
# run (2026-07-02 23:00 boot: script died during the 25s sleep; amdgpu is still
# bound to bus 2, so the working state is still live). Takes only the snapshots
# the original script missed. Run: sudo bash finish_capture_working_pci.sh

set -uo pipefail

OUT=/home/bob/Ailang-Self-Hosting-/pci_working_boot
ROOTPORT=00:03.0
GPU=02:00.0
AUDIO=02:00.1
BUS2=0000:02:00.0

exec > >(tee -a "$OUT/capture.log") 2>&1

echo "=== finish capture — $(date) ==="
if [[ $EUID -ne 0 ]]; then echo "ERROR: run as root"; exit 1; fi
if [[ ! -L "/sys/bus/pci/devices/$BUS2/driver" ]]; then
    echo "ERROR: bus 2 not bound — the working state is gone. Full re-capture needed."
    exit 1
fi
echo "bus 2 bound to: $(basename "$(readlink /sys/bus/pci/devices/$BUS2/driver)")"

dmesg > "$OUT/dmesg_full.txt"
dmesg | grep -iE "amdgpu|\[drm\]" > "$OUT/dmesg_amdgpu.txt"
# NOTE: modern amdgpu logs no "ring test succeeded" lines (radeon-era format).
# Success criterion = "Initialized amdgpu ... for 0000:02:00.0" present, no
# "ring test ... failed"/"init failed" lines.
grep -c "Initialized amdgpu .* for 0000:02:00.0" "$OUT/dmesg_amdgpu.txt" \
    && echo "bringup OK (Initialized line present)" \
    || echo "WARNING: no Initialized line for bus 2"

echo "--- WORKING-STATE snapshots (amdgpu still bound) ---"
lspci -vvvxxxx -s "$ROOTPORT" >  "$OUT/rootport_working.txt"
lspci -vvvxxxx -s "$GPU"      >  "$OUT/gpu_working.txt"
lspci -vvvxxxx -s "$AUDIO"    >  "$OUT/audio_working.txt"
lspci -vvvxxxx                >  "$OUT/lspci_all_working.txt"
cat /proc/interrupts          >  "$OUT/interrupts_working.txt"
sync
echo "Working-state snapshots saved."

echo "--- live MSI address/data (the §38 thread-2 payload) ---"
grep -A2 "MSI:" "$OUT/gpu_working.txt" | head -6

echo "Unbinding bus 2..."
CUR=$(basename "$(readlink /sys/bus/pci/devices/$BUS2/driver)")
echo "$BUS2" > "/sys/bus/pci/drivers/$CUR/unbind" 2>/dev/null || true
sleep 1
echo "bus 2 unbound from $CUR."
lspci -vvvxxxx -s "$GPU" > "$OUT/gpu_postunbind.txt"

sync; sync
echo "=== finish-capture complete ==="
ls -la "$OUT/"
echo "REMINDER: bus 2 is POSTed. Cold reboot before any replay-harness run."
