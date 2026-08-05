#!/bin/bash
#
# capture_working_pci.sh — one-boot PCI config-space capture of a WORKING
# amdgpu bringup on bus 2. Fills the §38 gap: no working-boot reference ever
# existed for the root port (00:03.0), the GPU's live MSI address/data, or the
# audio function. NO mmiotrace involved.
#
# Run as root on a cold boot where nothing has touched bus 2:
#   sudo bash capture_working_pci.sh
#
# After this boot the card is POSTed — cold reboot again before any replay run.
# Snapshots are taken BEFORE unbinding bus 2 (unbind clears bus-master/MSI,
# which is exactly the state we need to see).

set -uo pipefail

OUT=/home/bob/Ailang-Self-Hosting-/pci_working_boot
ROOTPORT=00:03.0
GPU=02:00.0
AUDIO=02:00.1
BUS2=0000:02:00.0

mkdir -p "$OUT"
exec > >(tee "$OUT/capture.log") 2>&1

echo "=== Working-boot PCI config capture — $(date) ==="

if [[ $EUID -ne 0 ]]; then echo "ERROR: run as root"; exit 1; fi

if lsmod | grep -q "^amdgpu "; then
    echo "ERROR: amdgpu already loaded — this boot is not clean. Reboot first."
    exit 1
fi

# Pre-bind reference (bus 2 un-posted, nothing bound)
lspci -vvvxxxx -s "$ROOTPORT" >  "$OUT/rootport_prebind.txt"
lspci -vvvxxxx -s "$GPU"      >  "$OUT/gpu_prebind.txt"
lspci -vvvxxxx -s "$AUDIO"    >  "$OUT/audio_prebind.txt"
echo "Pre-bind snapshots saved."

echo "Loading amdgpu si_support=1 (binds bus 1 + bus 2, same as capture boots)..."
modprobe amdgpu si_support=1 || { echo "ERROR: modprobe failed"; dmesg | tail -20; exit 1; }

echo "Waiting 25s for deferred init (MC training, fw load, ring tests)..."
sleep 25

echo ""
echo "--- bringup verification ---"
dmesg > "$OUT/dmesg_full.txt"
dmesg | grep -iE "amdgpu|\[drm\]" > "$OUT/dmesg_amdgpu.txt"
RINGOK=$(dmesg | grep -cE "ring test on .* succeeded" || true)
RINGBAD=$(dmesg | grep -ciE "ring test.*failed|failed to initialize|init failed" || true)
echo "ring-test-succeeded lines: $RINGOK   failure lines: $RINGBAD"
if [[ -L "/sys/bus/pci/devices/$BUS2/driver" ]]; then
    echo "bus 2 bound to: $(basename "$(readlink /sys/bus/pci/devices/$BUS2/driver)")"
else
    echo "WARNING: bus 2 NOT bound — capture may not represent a working bringup"
fi

echo ""
echo "--- WORKING-STATE snapshots (amdgpu still bound — do not reorder) ---"
lspci -vvvxxxx -s "$ROOTPORT" >  "$OUT/rootport_working.txt"
lspci -vvvxxxx -s "$GPU"      >  "$OUT/gpu_working.txt"
lspci -vvvxxxx -s "$AUDIO"    >  "$OUT/audio_working.txt"
lspci -vvvxxxx               >  "$OUT/lspci_all_working.txt"
cat /proc/interrupts          >  "$OUT/interrupts_working.txt"
sync
echo "Working-state snapshots saved to $OUT/"

echo ""
echo "Unbinding bus 2 (amdgpu stays on bus 1 — removing it would kill display)..."
if [[ -L "/sys/bus/pci/devices/$BUS2/driver" ]]; then
    CUR=$(basename "$(readlink /sys/bus/pci/devices/$BUS2/driver)")
    echo "$BUS2" > "/sys/bus/pci/drivers/$CUR/unbind" 2>/dev/null || true
    sleep 1
    echo "bus 2 unbound from $CUR."
fi

# Post-unbind snapshot: shows exactly what unbind tears down (MSI, bus master)
lspci -vvvxxxx -s "$GPU" > "$OUT/gpu_postunbind.txt"

sync; sync
echo ""
echo "=== Capture complete. Files in $OUT/ ==="
ls -la "$OUT/"
echo ""
echo "REMINDER: bus 2 is now POSTed. Cold reboot before any replay-harness run."
