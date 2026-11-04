#!/usr/bin/env bash
# Checks each -optoff group with the compiler itself, the largest program there is.
#   offtest.sh <compiler> [group ...]      (default: every group, then all)
# For each group: build the compiler with -optoff=<group>, let that compiler build the
# compiler again, and compare with the normal build. IDENTICAL means the plain path the
# group falls back to compiled 7 MB of real code correctly.
set -u
C=$(readlink -f "$1"); shift
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../.." && pwd)
export AILANG_LIB_PATH=${AILANG_LIB_PATH:-$REPO/Librarys}
GROUPS_=${*:-inline linscan regleaf fold dead homes select magic math byte scanrw skip reload all}
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
cd "$REPO" || exit 1
"$C" ailang_cli.ailang -o "$TMP/ref.x" >/dev/null 2>&1 || { echo "normal build failed"; exit 1; }
for g in $GROUPS_; do
    (
        "$C" -optoff=$g ailang_cli.ailang -o "$TMP/c_$g.x" >/dev/null 2>&1 || { echo "$g: build failed"; exit; }
        timeout 600 "$TMP/c_$g.x" ailang_cli.ailang -o "$TMP/o_$g.x" >/dev/null 2>&1
        if cmp -s "$TMP/o_$g.x" "$TMP/ref.x"; then echo "$g: IDENTICAL"; else echo "$g: DIFFERS"; fi
    ) &
    while [ "$(jobs -r | wc -l)" -ge "${JOBS:-7}" ]; do wait -n; done
done
wait
