#!/usr/bin/env bash
# Build the Load fixtures and run them. One ailang.x at a time.
# Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
CC="${AILANG:-/usr/local/bin/ailang.x}"
OUT=/tmp/load-test
rm -rf "$OUT"
mkdir -p "$OUT/bins"
"$CC" Librarys/Load/load_child.ailang "$OUT/load_child.x"
"$CC" Librarys/Load/load_swap.ailang "$OUT/load_swap.x"
"$CC" Librarys/Load/test_load.ailang "$OUT/test_load.x"
cp "$OUT/load_child.x" "$OUT/load_swap.x" "$OUT/bins/"
printf 'not a program\n' > "$OUT/bins/notes.txt"
printf 'x\n' > "$OUT/bins/skip.x"
chmod a-x "$OUT/bins/skip.x"
"$OUT/test_load.x"
