#!/bin/bash
#
# radeon_trace_boot.sh — Boot-time mmiotrace capture of amdgpu GPU init
#
# Designed to run as a systemd oneshot service BEFORE display-manager.
# Requires:
#   - GRUB: modprobe.blacklist=radeon,amdgpu  (neither driver loads at boot)
#   - GRUB: radeon.si_support=0               (radeon never touches SI cards)
#   - GRUB: NO amdgpu.si_support=0            (must NOT be on kernel cmdline)
#   - /etc/modprobe.d/amdgpu-si.conf:  options amdgpu si_support=0
#     (default off; our explicit modprobe si_support=1 overrides it)
#
# The script:
#   1. Enables mmiotrace
#   2. Loads amdgpu via modprobe with si_support=1 (resolves all deps)
#   3. Captures the full init sequence (MC, VM/TLB, CP, rings)
#   4. Saves trace + dmesg to disk
#   5. Unbinds bus 2 (leaves system clean for AILang driver)
#
# Install:
#   sudo cp gpu-mmiotrace.service /etc/systemd/system/
#   sudo systemctl daemon-reload
#   sudo systemctl enable gpu-mmiotrace.service
#   # Fix GRUB, create modprobe.d conf, update-grub, reboot
#   # After reboot, check ~/Ailang-Self-Hosting-/mmiotrace_boot/
#   sudo systemctl disable gpu-mmiotrace.service   # one-shot, disable after
#
set -uo pipefail

TRACE_DIR="/sys/kernel/debug/tracing"
BUS1="0000:01:00.0"
BUS2="0000:02:00.0"
OUTDIR="/home/bob/Ailang-Self-Hosting-/mmiotrace_boot"
LOGFILE="$OUTDIR/boot_trace.log"
DRIVER="amdgpu"

mkdir -p "$OUTDIR"
exec > >(tee "$LOGFILE") 2>&1

echo "=== GPU mmiotrace boot capture (amdgpu) ==="
echo "Started: $(date)"
echo "Kernel:  $(uname -r)"
echo ""

# ── Sanity checks ─────────────────────────────────────────────────────────

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: must run as root"
    exit 1
fi

# Mount debugfs if needed
if [[ ! -d "$TRACE_DIR" ]]; then
    mount -t debugfs none /sys/kernel/debug 2>/dev/null || true
fi
if [[ ! -d "$TRACE_DIR" ]]; then
    echo "ERROR: debugfs/tracing not available"
    exit 1
fi

if ! grep -q mmiotrace "$TRACE_DIR/available_tracers" 2>/dev/null; then
    echo "ERROR: mmiotrace not available in this kernel"
    exit 1
fi

# ── Verify amdgpu is NOT loaded ──────────────────────────────────────────

if lsmod | grep -q "^amdgpu "; then
    echo "ERROR: amdgpu is already loaded! Blacklist it in GRUB:"
    echo "  modprobe.blacklist=radeon,amdgpu,snd_hda_codec_atihdmi"
    exit 1
fi

# Check kernel cmdline for the si_support=0 poison
if grep -q 'amdgpu.si_support=0' /proc/cmdline; then
    echo "ERROR: amdgpu.si_support=0 is on kernel command line!"
    echo "  Remove it from GRUB. Use /etc/modprobe.d/amdgpu-si.conf instead."
    echo "  Current cmdline: $(cat /proc/cmdline)"
    exit 1
fi

echo "GOOD: amdgpu not loaded, si_support not poisoned on cmdline"

# Check bus states
for bus in "$BUS1" "$BUS2"; do
    if [[ -L "/sys/bus/pci/devices/$bus/driver" ]]; then
        drv=$(basename "$(readlink "/sys/bus/pci/devices/$bus/driver")")
        echo "  $bus: bound to $drv"
    else
        echo "  $bus: unbound"
    fi
done
echo ""

# ── Pre-bind register snapshot ───────────────────────────────────────────

PROBE_SCRIPT="/home/bob/Ailang-Self-Hosting-/gpu_probe_fullstate.py"
if [[ -f "$PROBE_SCRIPT" ]]; then
    echo "Taking pre-bind register snapshot..."
    python3 "$PROBE_SCRIPT" > "$OUTDIR/probe_pre_bind.txt" 2>&1 || true
    sync
    echo "  Saved: probe_pre_bind.txt"
    echo ""
fi

# ── Enable mmiotrace ────────────────────────────────────────────────────

echo "Enabling mmiotrace..."
echo 0       > "$TRACE_DIR/tracing_on"
echo nop     > "$TRACE_DIR/current_tracer"
echo         > "$TRACE_DIR/trace"              # clear buffer
echo 65536   > "$TRACE_DIR/buffer_size_kb"     # 64MB/cpu — GPU init is big
echo mmiotrace > "$TRACE_DIR/current_tracer"
echo 1       > "$TRACE_DIR/tracing_on"

BUF_KB=$(cat "$TRACE_DIR/buffer_size_kb")
echo "  mmiotrace ACTIVE — buffer ${BUF_KB} KB/cpu"
echo ""

# ── Start trace_pipe reader (background) ────────────────────────────────

RAW_LOG="$OUTDIR/mmiotrace_raw.log"
cat "$TRACE_DIR/trace_pipe" > "$RAW_LOG" &
READER_PID=$!

# ── Load amdgpu via modprobe (resolves ALL dependencies) ────────────────

echo "Loading amdgpu with si_support=1 via modprobe..."
BIND_START=$(date +%s%N)

modprobe "$DRIVER" si_support=1 2>&1
MODPROBE_RC=$?

BIND_END=$(date +%s%N)
BIND_MS=$(( (BIND_END - BIND_START) / 1000000 ))

if [[ $MODPROBE_RC -ne 0 ]]; then
    echo "ERROR: modprobe $DRIVER si_support=1 failed (rc=$MODPROBE_RC)"
    dmesg | tail -20
    echo ""
    echo "Stopping mmiotrace and saving what we have..."
else
    echo "  modprobe succeeded in ${BIND_MS}ms"
fi

# Wait for deferred init (MC training, firmware loading, ring setup)
echo "  Waiting 15s for deferred init to complete..."
sleep 15

# Check what happened
echo ""
echo "Post-load state:"
for bus in "$BUS1" "$BUS2"; do
    if [[ -L "/sys/bus/pci/devices/$bus/driver" ]]; then
        drv=$(basename "$(readlink "/sys/bus/pci/devices/$bus/driver")")
        echo "  $bus: bound to $drv"
    else
        echo "  $bus: unbound"
    fi
done

SI_VAL=$(cat /sys/module/amdgpu/parameters/si_support 2>/dev/null || echo "?")
echo "  si_support = $SI_VAL"
echo ""

# ── Stop mmiotrace ──────────────────────────────────────────────────────

echo "Stopping mmiotrace..."
echo 0 > "$TRACE_DIR/tracing_on"

# Also grab the static buffer (trace_pipe only shows consumed events)
cat "$TRACE_DIR/trace" >> "$RAW_LOG"

kill $READER_PID 2>/dev/null || true
wait $READER_PID 2>/dev/null || true

echo nop > "$TRACE_DIR/current_tracer"
sync

TOTAL_LINES=$(wc -l < "$RAW_LOG")
WRITE_COUNT=$(grep -c "^W" "$RAW_LOG" 2>/dev/null || echo 0)
READ_COUNT=$(grep -c "^R" "$RAW_LOG" 2>/dev/null || echo 0)
MAP_COUNT=$(grep -c "^MAP" "$RAW_LOG" 2>/dev/null || echo 0)

echo "  Raw log: $RAW_LOG"
echo "  Total lines: $TOTAL_LINES"
echo "  MMIO writes: $WRITE_COUNT"
echo "  MMIO reads:  $READ_COUNT"
echo "  ioremap MAPs: $MAP_COUNT"
echo ""

# ── Post-bind register snapshot ─────────────────────────────────────────

if [[ -f "$PROBE_SCRIPT" ]]; then
    echo "Taking post-bind register snapshot..."
    python3 "$PROBE_SCRIPT" > "$OUTDIR/probe_post_bind.txt" 2>&1 || true
    sync
    echo "  Saved: probe_post_bind.txt"
    echo ""
fi

# ── Save dmesg ──────────────────────────────────────────────────────────

dmesg > "$OUTDIR/dmesg_full.txt" 2>/dev/null || true
dmesg | grep -iE "amdgpu|drm|gpu|error|fault|mmiotrace|si_support|gmc|gfx|psp" \
    > "$OUTDIR/dmesg_amdgpu.txt" 2>/dev/null || true
sync
echo "Saved dmesg"

# ── Parse trace (if parser exists) ──────────────────────────────────────

PARSER="/home/bob/Ailang-Self-Hosting-/parse_mmiotrace.py"
if [[ -f "$PARSER" ]]; then
    echo "Parsing trace..."
    python3 "$PARSER" "$RAW_LOG" --summary    > "$OUTDIR/mmiotrace_parsed.txt" 2>&1 || true
    python3 "$PARSER" "$RAW_LOG" --writes-only > "$OUTDIR/mmiotrace_full.txt" 2>&1 || true
    sync
    echo "  Parsed: mmiotrace_parsed.txt, mmiotrace_full.txt"
    echo ""
fi

# ── Unbind bus 2 (free for AILang driver) ───────────────────────────────

echo "Unbinding bus 2 from $DRIVER (freeing for AILang driver)..."
if [[ -L "/sys/bus/pci/devices/$BUS2/driver" ]]; then
    CUR=$(basename "$(readlink "/sys/bus/pci/devices/$BUS2/driver")")
    echo "$BUS2" > "/sys/bus/pci/drivers/$CUR/unbind" 2>/dev/null || true
    sleep 1
    echo "  Bus 2 unbound from $CUR."
else
    echo "  Bus 2 already unbound."
fi

# Note: amdgpu stays on bus 1. Removing it would kill display.

echo ""
echo "=== Boot mmiotrace capture complete — $(date) ==="
echo ""
echo "Files in $OUTDIR/:"
ls -la "$OUTDIR/"
echo ""

sync
sync

echo "All data on disk."
