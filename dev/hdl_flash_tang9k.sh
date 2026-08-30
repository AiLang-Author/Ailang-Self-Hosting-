#!/usr/bin/env bash
# Simple Tang Nano 9K flash — AILang blink bitstream.
# Never programs PolarFire / FlashPro5 (1514:2008).
#
#   ./dev/hdl_flash_tang9k.sh              # flash AILang blink (SRAM)
#   ./dev/hdl_flash_tang9k.sh --flash      # external flash (survives power off)
#   ./dev/hdl_flash_tang9k.sh --detect     # cable check only
#   ./dev/hdl_flash_tang9k.sh --rebuild    # rebuild AILang then flash
#   BIT=.../ref_blink.fs ./dev/hdl_flash_tang9k.sh   # known-good Verilog blink
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/tools/oss-cad-suite/bin:${PATH}"

BIT="${BIT:-$ROOT/dev/boards/tang_nano_9k/out/blink.fs}"
MODE="sram"
REBUILD=0

for a in "$@"; do
  case "$a" in
    --flash|-f)   MODE="flash" ;;
    --detect|-d)  MODE="detect" ;;
    --rebuild|-r) REBUILD=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "Unknown: $a"; exit 2 ;;
  esac
done

OFL="$(command -v openFPGALoader || true)"
OFL="$(readlink -f "${OFL:-}" 2>/dev/null || echo "${OFL:-}")"
[[ -x "$OFL" ]] || OFL="$HOME/tools/oss-cad-suite/bin/openFPGALoader"
[[ -x "$OFL" ]] || { echo "ERROR: openFPGALoader not found (start OSS CAD Suite shell)"; exit 2; }

echo "=========================================="
echo " Flash Tang Nano 9K only (not PolarFire)"
echo "=========================================="
echo "tool: $OFL"
echo

# Show devices — Tang = 0403:6010, Polar = 1514:2008
echo "USB:"
if /usr/bin/lsusb | grep -q '0403:6010'; then
  /usr/bin/lsusb | grep '0403:6010' | sed 's/^/  TANG  /'
else
  echo "  TANG  NOT FOUND — plug in the Tang Nano USB cable"
  exit 1
fi
if /usr/bin/lsusb | grep -q '1514:2008'; then
  /usr/bin/lsusb | grep '1514:2008' | sed 's/^/  POLAR /'
  echo "         (ignored — we never program this)"
fi
echo

if [[ "$REBUILD" == "1" || ! -f "$BIT" ]]; then
  echo "Building bitstream..."
  bash "$ROOT/dev/hdl_build_tang9k.sh"
fi
[[ -f "$BIT" ]] || { echo "ERROR: no $BIT"; exit 1; }
echo "bitstream: $BIT"
echo

# Simple: board name only. Do NOT pin busdev — renumbering / dual FTDI breaks it.
# -b tangnano9k selects Gowin Tang path and the right FTDI channel.
run() {
  set +e
  "$OFL" -b tangnano9k "$@"
  local rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    echo
    echo "Retry with sudo (full tool path kept):"
    sudo env PATH="$PATH" "$OFL" -b tangnano9k "$@"
  fi
}

if [[ "$MODE" == "detect" ]]; then
  echo "== detect =="
  run --detect
  exit 0
fi

echo "== detect =="
run --detect
echo

if [[ "$MODE" == "flash" ]]; then
  echo "== write external flash =="
  run -f "$BIT"
else
  echo "== write SRAM =="
  run "$BIT"
fi

echo
echo "Done."
echo "Expect: 6 LEDs binary-counting ~twice per second."
echo "If one LED stuck on / all on: clock or design issue — rebuild with --rebuild."
echo "PolarFire was not programmed."
