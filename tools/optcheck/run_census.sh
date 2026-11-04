#!/usr/bin/env bash
# Side-effect census over many programs. Compiles nothing it runs, so it is safe on driver code.
#   run_census.sh <compiler> <list-of-programs> [out.tsv]
# Each line of the list is a program path relative to the repository root. Every program is
# built twice with -funcmap: optimized (with -optlog) and with every group but inline off.
# census.py prints a DROP row for each function whose optimized code has fewer syscalls or
# memory stores than the base build. No rows means nothing was dropped.
# Env: JOBS (default 7), AILANG_LIB_PATH (default <repo>/Librarys).
set -u
C=$(readlink -f "$1"); LIST=$(readlink -f "$2"); OUT=${3:-/dev/stdout}
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../.." && pwd)
export AILANG_LIB_PATH=${AILANG_LIB_PATH:-$REPO/Librarys}
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
BASE_OFF=linscan,regleaf,fold,dead,homes,select,magic,math,byte,scanrw,skip,reload
one() {
    f=$1; d=$TMP/$(echo "$f" | md5sum | cut -c1-12); mkdir -p "$d"; cd "$REPO" || exit
    timeout 300 "$C" -funcmap -optlog "$f" -o "$d/o.x" >/dev/null 2>&1 || { echo -e "BUILDFAIL\t$f"; rm -rf "$d"; return; }
    timeout 300 "$C" -funcmap -optoff=$BASE_OFF "$f" -o "$d/b.x" >/dev/null 2>&1 || { echo -e "BASEFAIL\t$f"; rm -rf "$d"; return; }
    python3 -I "$HERE/census.py" "$d/o.x" "$d/b.x" "$f" "$AILANG_LIB_PATH" | sed "s#^#$f\t#"
    rm -rf "$d"
}
export -f one; export C TMP HERE REPO BASE_OFF
xargs -a "$LIST" -d '\n' -P "${JOBS:-7}" -I{} bash -c 'one "$1"' _ {} > "$OUT"
