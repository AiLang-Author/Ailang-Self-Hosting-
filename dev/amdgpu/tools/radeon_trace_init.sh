#!/bin/bash
#
# radeon_trace_init.sh — Capture GPU driver init sequence via mmiotrace
#
# Uses Linux kernel's mmiotrace to record every MMIO read/write the driver
# makes during probe()/init() on the SECONDARY GPU (bus 2, 0000:02:00.0).
#
# Supports both radeon and amdgpu drivers. Overrides si_support=1 so SI
# (Southern Islands / Cape Verde) GPUs are accepted even when the kernel
# command line has si_support=0.
#
# HEADLESS-SAFE: No interactive prompts. If the driver takes over the
# display GPU, the script keeps running. All files are sync'd to disk.
#
# Usage:
#   sudo ./radeon_trace_init.sh           # try amdgpu first, fall back to radeon
#   sudo ./radeon_trace_init.sh radeon    # force radeon
#   sudo ./radeon_trace_init.sh amdgpu    # force amdgpu
#
set -euo pipefail

TRACE_DIR="/sys/kernel/debug/tracing"
BUS1="0000:01:00.0"
BUS2="0000:02:00.0"
OUTDIR="$(cd "$(dirname "$0")" && pwd)"
RAW_LOG="$OUTDIR/mmiotrace_raw.log"
PARSED_LOG="$OUTDIR/mmiotrace_parsed.txt"
SCRIPT_LOG="$OUTDIR/radeon_trace_init.log"

# Which driver to use
DRV="${1:-auto}"

# Log everything to file (survives display death)
exec > >(tee -a "$SCRIPT_LOG") 2>&1

# ── Checks ──────────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    echo "ERROR: Must run as root (sudo)."
    exit 1
fi

if [[ ! -d "$TRACE_DIR" ]]; then
    mount -t debugfs none /sys/kernel/debug 2>/dev/null || true
    if [[ ! -d "$TRACE_DIR" ]]; then
        echo "ERROR: debugfs tracing not available."
        exit 1
    fi
fi

if ! grep -q mmiotrace "$TRACE_DIR/available_tracers" 2>/dev/null; then
    echo "ERROR: mmiotrace not in available_tracers."
    exit 1
fi

# ── Pick driver ─────────────────────────────────────────────────────────────
pick_driver() {
    if [[ "$DRV" == "radeon" || "$DRV" == "amdgpu" ]]; then
        echo "$DRV"
        return
    fi
    # Auto: prefer amdgpu, fall back to radeon
    if find /lib/modules/$(uname -r) -name "amdgpu.ko*" 2>/dev/null | grep -q .; then
        echo "amdgpu"
    else
        echo "radeon"
    fi
}

DRV_NAME=$(pick_driver)
echo "=== GPU Init Tracer (mmiotrace) ==="
echo "Started: $(date)"
echo "Driver:  $DRV_NAME (with si_support=1)"
echo ""

# ── Step 0: Check current state ─────────────────────────────────────────────
if [[ -L "/sys/bus/pci/devices/$BUS1/driver" ]]; then
    BUS1_DRV=$(basename "$(readlink "/sys/bus/pci/devices/$BUS1/driver")")
    echo "Bus 1 driver: $BUS1_DRV"
else
    echo "Bus 1 driver: none (unbound)"
fi

if [[ -L "/sys/bus/pci/devices/$BUS2/driver" ]]; then
    CURRENT_DRV=$(basename "$(readlink "/sys/bus/pci/devices/$BUS2/driver")")
    echo "Bus 2 driver: $CURRENT_DRV — unbinding..."
    echo "$BUS2" > "/sys/bus/pci/drivers/$CURRENT_DRV/unbind" 2>/dev/null || true
    sleep 1
    echo "  Unbound."
else
    echo "Bus 2 driver: none (unbound)"
fi

echo ""
sync

# ── Step 1: Unload existing GPU drivers, reload with si_support=1 ───────────
# si_support is read-only (0444) so we must rmmod and reload to override it.

echo "Preparing $DRV_NAME module with si_support=1..."

# Unload any existing GPU drivers (order matters for deps)
for mod in amdgpu radeon; do
    if lsmod | grep -q "^$mod "; then
        echo "  Unloading $mod..."
        # Unbind all devices first so rmmod doesn't fail
        if [[ -d "/sys/bus/pci/drivers/$mod" ]]; then
            for dev in /sys/bus/pci/drivers/$mod/0000:*; do
                if [[ -L "$dev" ]]; then
                    devid=$(basename "$dev")
                    echo "    Unbinding $devid from $mod..."
                    echo "$devid" > "/sys/bus/pci/drivers/$mod/unbind" 2>/dev/null || true
                fi
            done
        fi
        sleep 1
        rmmod "$mod" 2>/dev/null || {
            echo "  WARNING: rmmod $mod failed (may have dependents)"
            # Try harder — remove dependents
            for dep in $(lsmod | awk -v m="$mod" '$1==m{print $4}' | tr ',' ' '); do
                rmmod "$dep" 2>/dev/null || true
            done
            rmmod "$mod" 2>/dev/null || echo "  WARNING: still can't unload $mod"
        }
    fi
done

echo ""

# Load the driver with si_support=1
echo "Loading $DRV_NAME with si_support=1..."

# Ensure dependencies are available
modprobe drm 2>/dev/null || true
modprobe drm_kms_helper 2>/dev/null || true
modprobe ttm 2>/dev/null || true

if modprobe "$DRV_NAME" si_support=1 2>&1; then
    echo "  $DRV_NAME loaded successfully with si_support=1."
else
    echo "  modprobe failed. Trying alternate approach..."
    # For blacklisted modules, find and insmod with param
    MOD_KO=$(find /lib/modules/$(uname -r) -name "${DRV_NAME}.ko*" 2>/dev/null | head -1)
    if [[ -z "$MOD_KO" ]]; then
        echo "ERROR: Cannot find ${DRV_NAME}.ko"
        sync
        exit 1
    fi
    modprobe i2c-algo-bit 2>/dev/null || true
    insmod "$MOD_KO" si_support=1 2>&1 || {
        echo "ERROR: insmod also failed. Check dmesg."
        dmesg | tail -20
        sync
        exit 1
    }
    echo "  $DRV_NAME loaded via insmod with si_support=1."
fi

sleep 2

# Verify si_support is now 1
SI_VAL=$(cat "/sys/module/$DRV_NAME/parameters/si_support" 2>/dev/null || echo "?")
echo "  si_support = $SI_VAL"
if [[ "$SI_VAL" != "1" ]]; then
    echo "  WARNING: si_support is not 1! Driver may still refuse SI GPUs."
fi

echo ""

# Check if driver auto-probed GPUs
if [[ -L "/sys/bus/pci/devices/$BUS1/driver" ]]; then
    BUS1_NOW=$(basename "$(readlink "/sys/bus/pci/devices/$BUS1/driver")")
    echo "  Bus 1 auto-bound to: $BUS1_NOW"
    if [[ "$BUS1_NOW" == "$DRV_NAME" ]]; then
        echo "  (display may be taken over — script continues headless)"
    fi
fi

# Unbind bus 2 if driver auto-probed it (we need a clean traced re-bind)
if [[ -L "/sys/bus/pci/devices/$BUS2/driver" ]]; then
    BUS2_NOW=$(basename "$(readlink "/sys/bus/pci/devices/$BUS2/driver")")
    echo "  Bus 2 auto-bound to: $BUS2_NOW — unbinding for traced re-bind..."
    echo "$BUS2" > "/sys/bus/pci/drivers/$BUS2_NOW/unbind"
    sleep 1
    echo "  Unbound bus 2."
fi

echo ""
sync

# ── Step 2: Pre-bind register snapshot ──────────────────────────────────────
echo "Taking pre-bind register snapshot..."
PRE_SNAP="$OUTDIR/probe_pre_radeon_bind.txt"
if [[ -f "$OUTDIR/gpu_probe_fullstate.py" ]]; then
    python3 "$OUTDIR/gpu_probe_fullstate.py" > "$PRE_SNAP" 2>&1 || true
    sync
    echo "  Saved + sync'd: $PRE_SNAP"
fi

# ── Step 3: Enable mmiotrace ────────────────────────────────────────────────
echo ""
echo "Enabling mmiotrace..."

echo 0 > "$TRACE_DIR/tracing_on"
echo nop > "$TRACE_DIR/current_tracer"
echo > "$TRACE_DIR/trace"
echo 32768 > "$TRACE_DIR/buffer_size_kb"
echo mmiotrace > "$TRACE_DIR/current_tracer"
echo 1 > "$TRACE_DIR/tracing_on"

echo "  mmiotrace ACTIVE — buffer $(cat "$TRACE_DIR/buffer_size_kb") KB/cpu"
echo ""

# ── Step 4: Bind driver to bus 2 ────────────────────────────────────────────
echo "Binding $DRV_NAME to bus 2 ($BUS2)..."
echo "  Capturing full init sequence..."

# Background: drain trace_pipe into log file
cat "$TRACE_DIR/trace_pipe" > "$RAW_LOG" &
READER_PID=$!

# Bind
BIND_START=$(date +%s%N)
echo "$BUS2" > /sys/bus/pci/drivers/$DRV_NAME/bind 2>&1 || {
    echo "WARNING: bind returned error (partial init may still be captured)"
    echo "  dmesg tail:"
    dmesg | tail -5
}
BIND_END=$(date +%s%N)
BIND_MS=$(( (BIND_END - BIND_START) / 1000000 ))
echo "  Bind returned in ${BIND_MS}ms"

# Wait for deferred init (MC training, firmware load, etc.)
echo "  Waiting 8s for deferred init..."
sleep 8

# ── Step 5: Stop mmiotrace, flush everything ────────────────────────────────
echo ""
echo "Stopping mmiotrace..."
echo 0 > "$TRACE_DIR/tracing_on"

# Grab the static buffer too
cat "$TRACE_DIR/trace" >> "$RAW_LOG"

kill $READER_PID 2>/dev/null || true
wait $READER_PID 2>/dev/null || true

echo nop > "$TRACE_DIR/current_tracer"

# SYNC immediately
sync
echo "  Raw log sync'd to disk."

TOTAL_LINES=$(wc -l < "$RAW_LOG")
WRITE_COUNT=$(grep -c "^W" "$RAW_LOG" 2>/dev/null || echo 0)
READ_COUNT=$(grep -c "^R" "$RAW_LOG" 2>/dev/null || echo 0)
MAP_COUNT=$(grep -c "^MAP" "$RAW_LOG" 2>/dev/null || echo 0)

echo "  Total lines: $TOTAL_LINES"
echo "  MMIO writes: $WRITE_COUNT"
echo "  MMIO reads:  $READ_COUNT"
echo "  ioremap MAPs: $MAP_COUNT"
echo ""

# ── Step 6: Post-bind register snapshot ─────────────────────────────────────
echo "Taking post-bind register snapshot..."
POST_SNAP="$OUTDIR/probe_post_radeon_bind.txt"
if [[ -f "$OUTDIR/gpu_probe_fullstate.py" ]]; then
    python3 "$OUTDIR/gpu_probe_fullstate.py" > "$POST_SNAP" 2>&1 || true
    sync
    echo "  Saved + sync'd: $POST_SNAP"
fi

# ── Step 7: Parse the trace ─────────────────────────────────────────────────
echo ""
echo "Parsing trace..."
if [[ -f "$OUTDIR/parse_mmiotrace.py" ]]; then
    python3 "$OUTDIR/parse_mmiotrace.py" "$RAW_LOG" --summary > "$PARSED_LOG" 2>&1 || true
    sync
    echo "  Parsed + sync'd: $PARSED_LOG"

    FULL_LOG="$OUTDIR/mmiotrace_full.txt"
    python3 "$OUTDIR/parse_mmiotrace.py" "$RAW_LOG" --writes-only > "$FULL_LOG" 2>&1 || true
    sync
    echo "  Full write log: $FULL_LOG"
else
    echo "  parse_mmiotrace.py not found — run manually after reboot:"
    echo "    python3 parse_mmiotrace.py mmiotrace_raw.log --summary"
fi

# ── Step 8: Unbind driver from bus 2 ────────────────────────────────────────
echo ""
echo "Unbinding $DRV_NAME from bus 2..."
if [[ -L "/sys/bus/pci/devices/$BUS2/driver" ]]; then
    CUR=$(basename "$(readlink "/sys/bus/pci/devices/$BUS2/driver")")
    echo "$BUS2" > "/sys/bus/pci/drivers/$CUR/unbind" 2>/dev/null || true
    sleep 1
    echo "  Bus 2 unbound."
fi

# Report final state
echo ""
echo "Final state:"
if [[ -L "/sys/bus/pci/devices/$BUS1/driver" ]]; then
    echo "  Bus 1: $(basename "$(readlink "/sys/bus/pci/devices/$BUS1/driver")")"
else
    echo "  Bus 1: unbound"
fi
if [[ -L "/sys/bus/pci/devices/$BUS2/driver" ]]; then
    echo "  Bus 2: $(basename "$(readlink "/sys/bus/pci/devices/$BUS2/driver")")"
else
    echo "  Bus 2: unbound"
fi

# ── Capture dmesg + final sync ──────────────────────────────────────────────
echo ""
dmesg | grep -iE "radeon|amdgpu|drm|gpu|error|fault|mmiotrace" > "$OUTDIR/dmesg_radeon.txt" 2>/dev/null || true
sync
echo "  dmesg saved: $OUTDIR/dmesg_radeon.txt"

echo ""
echo "=== DONE — $(date) ==="
echo ""
echo "All files sync'd to disk. Safe to hard reboot if display is dead."
echo ""
echo "Files:"
echo "  $RAW_LOG"
echo "  $PARSED_LOG"
[[ -f "$OUTDIR/mmiotrace_full.txt" ]] && echo "  $OUTDIR/mmiotrace_full.txt"
[[ -f "$PRE_SNAP" ]] && echo "  $PRE_SNAP"
[[ -f "$POST_SNAP" ]] && echo "  $POST_SNAP"
echo "  $SCRIPT_LOG"
echo "  $OUTDIR/dmesg_radeon.txt"
echo ""

sync
sync

echo "All data on disk. You can hard reboot now if needed."
