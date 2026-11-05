#!/usr/bin/env bash
# Compile (and optionally run) compiler-regression suite.
# Usage:
#   ./dev/compiler-regression/run_smoke.sh           # top-level *.ailang only
#   ./dev/compiler-regression/run_smoke.sh --all      # include subdirs
#   ./dev/compiler-regression/run_smoke.sh --run      # execute if compile ok
#   COMPILER=./ailang.x ./dev/compiler-regression/run_smoke.sh
#
# Display and GPU driver programs are not part of this suite. They are
# skipped before compile and are never executed. A headless import of
# Framebuffer still counts: a bad branch there opens /dev/fb0.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIR="$(cd "$(dirname "$0")" && pwd)"
COMPILER="${COMPILER:-$ROOT/ailang.x}"
OUTDIR="${TMPDIR:-/tmp}/ailang-regression-$$"
ALL=0
DO_RUN=0
for a in "$@"; do
  case "$a" in
    --all) ALL=1 ;;
    --run) DO_RUN=1 ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# //'; exit 0 ;;
  esac
done

if [[ ! -x "$COMPILER" ]]; then
  echo "ERROR: compiler not executable: $COMPILER" >&2
  exit 1
fi

mkdir -p "$OUTDIR"
trap 'rm -rf "$OUTDIR"' EXIT

mapfile -t FILES < <(
  if [[ "$ALL" -eq 1 ]]; then
    find "$DIR" -type f -name '*.ailang' | sort
  else
    find "$DIR" -maxdepth 1 -type f -name '*.ailang' | sort
  fi
)

# 0 when this source must not be compiled or run.
# Drivers talk to the GPU. Framebuffer / DRenderFB / DRenderTerm and
# /dev/fb* /dev/input open the live display or the input devices.
is_display_or_driver() {
  local src="$1"
  local base
  base="$(basename "$src")"
  case "$base" in
    TestDisplay*.ailang|TestLiveCompositor.ailang|TestEvdevRaw.ailang|TestInput.ailang|TestWindowBSP.ailang|Test.WinStack.ailang|Test.CopyPaste.ailang|TestComposeTick.ailang|TestDents.ailang|canvas_demo.ailang|reset_gpu.ailang|pci_reset.ailang|pci_bar_restore.ailang)
      return 0
      ;;
  esac
  if grep -q -E \
    'LibraryImport\.Drivers\.|LibraryImport\.Display\.Render\.Framebuffer|LibraryImport\.Display\.Render\.DRenderFB|LibraryImport\.DRenderTerm|RenderTerm_Init|SystemCall\([^)]*"/dev/fb|SystemCall\([^)]*"/dev/input' \
    "$src"
  then
    return 0
  fi
  return 1
}

ok=0
fail=0
skip=0
echo "Compiler: $COMPILER"
echo "Suite:    $DIR  (${#FILES[@]} files)"
echo

for f in "${FILES[@]}"; do
  base="$(basename "$f" .ailang)"
  if is_display_or_driver "$f"; then
    echo "SKIP display/driver  $base"
    skip=$((skip + 1))
    continue
  fi
  out="$OUTDIR/${base}.x"
  # some sources are intentionally incomplete — capture errors
  if "$COMPILER" "$f" -o "$out" >/tmp/ailang-reg-compile.log 2>&1; then
    if [[ "$DO_RUN" -eq 1 ]]; then
      if timeout 5s "$out" >/tmp/ailang-reg-run.log 2>&1; then
        echo "OK   compile+run  $base"
        ok=$((ok + 1))
      else
        echo "FAIL run          $base  (compile ok)"
        fail=$((fail + 1))
      fi
    else
      echo "OK   compile      $base"
      ok=$((ok + 1))
    fi
  else
    echo "FAIL compile      $base"
    tail -3 /tmp/ailang-reg-compile.log 2>/dev/null | sed 's/^/       /'
    fail=$((fail + 1))
  fi
done

echo
echo "Summary: ok=$ok fail=$fail skip=$skip (of ${#FILES[@]})"
[[ "$fail" -eq 0 ]]
