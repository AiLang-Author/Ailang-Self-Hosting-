#!/usr/bin/env bash
# AILang HDL → Tang Nano 9K bitstream (Yosys + nextpnr-himbaechel + gowin_pack)
#
# Usage:
#   ./dev/hdl_build_tang9k.sh                  # blink dogfood
#   ./dev/hdl_build_tang9k.sh path/to.ailang   # custom source
#   FLASH=1 ./dev/hdl_build_tang9k.sh          # also openFPGALoader
#
# Needs: ailang_hdl.x, yosys, nextpnr-himbaechel, gowin_pack
#        (and openFPGALoader if FLASH=1)
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/tools/oss-cad-suite/bin:${PATH}"

SRC="${1:-dev/hdl_tang_blink.ailang}"
BOARD_DIR="$ROOT/dev/boards/tang_nano_9k"
OUT_DIR="${HDL_TANG_OUT:-$BOARD_DIR/out}"
BASE="$OUT_DIR/blink"
HDL_BIN="${HDL_BIN:-$ROOT/ailang_hdl.x}"

# Gowin part (Tang Nano 9K)
DEVICE="GW1NR-LV9QN88PC6/I5"
FAMILY="GW1N-9C"   # himbaechel/gowin_pack family id that works with this suite

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "FAIL: missing $1 (install oss-cad-suite or put it on PATH)"
    exit 2
  }
}

need yosys
need nextpnr-himbaechel
need gowin_pack
if [[ ! -x "$HDL_BIN" ]]; then
  echo "FAIL: missing $HDL_BIN — build with: ./ailang.x ailang_cli.ailang ailang_hdl.x"
  exit 2
fi

mkdir -p "$OUT_DIR"

echo "== AILang HDL compile =="
echo "  src=$SRC"
# -period 37 ≈ 27 MHz (1000/27)
"$HDL_BIN" -hdl -period 37 "$SRC" "$BASE"

if [[ ! -f "$BASE.v" ]]; then
  echo "FAIL: no $BASE.v"
  exit 1
fi

# Board top = wrapper + ailang_top
cat "$BOARD_DIR/top_wrap.v" "$BASE.v" >"$OUT_DIR/top.v"

echo "== Yosys synth_gowin =="
yosys -q -p "read_verilog $OUT_DIR/top.v; synth_gowin -top top -json $OUT_DIR/top.json"

echo "== nextpnr-himbaechel (place & route) =="
nextpnr-himbaechel \
  --device "$DEVICE" \
  -o "family=$FAMILY" \
  -o "cst=$BOARD_DIR/tangnano9k.cst" \
  --json "$OUT_DIR/top.json" \
  --write "$OUT_DIR/top_pnr.json"

echo "== gowin_pack (bitstream) =="
gowin_pack -d "$FAMILY" -o "$OUT_DIR/blink.fs" "$OUT_DIR/top_pnr.json"

ls -la "$OUT_DIR/blink.fs"
echo
echo "Bitstream ready: $OUT_DIR/blink.fs"
echo "Flash with:  openFPGALoader -b tangnano9k $OUT_DIR/blink.fs"

if [[ "${FLASH:-0}" == "1" ]]; then
  need openFPGALoader
  echo "== openFPGALoader =="
  openFPGALoader -b tangnano9k "$OUT_DIR/blink.fs"
fi

echo "OK"
