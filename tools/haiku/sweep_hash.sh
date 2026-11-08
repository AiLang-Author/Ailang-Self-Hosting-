#!/bin/bash
# usage: sweep_hash.sh COMPILER TREE ENTRIES OUT WORKDIR
# Compiles every entry program for the Linux and --haiku targets.
# One line per program: path, rc, sha (Linux target), rc, sha (--haiku).
export CC=$1 TREE=$2 WORK=$5
ENTRIES=$3 OUT=$4
export AILANG_LIB_PATH=$TREE/Librarys
mkdir -p "$WORK"
one() {
    f=$1
    id=$(printf %s "$f" | md5sum | cut -c1-12)
    w=$WORK/$id
    mkdir -p "$w"
    cd "$TREE/$(dirname "$f")" || { printf '%s\tNODIR\n' "$f"; return; }
    timeout 600 "$CC" "$(basename "$f")" "$w/l" >/dev/null 2>&1; rl=$?
    hl=none; [ -f "$w/l" ] && hl=$(sha256sum < "$w/l" | cut -c1-16)
    timeout 600 "$CC" --haiku "$(basename "$f")" "$w/h" >/dev/null 2>&1; rh=$?
    hh=none; [ -f "$w/h" ] && hh=$(sha256sum < "$w/h" | cut -c1-16)
    printf '%s\t%s\t%s\t%s\t%s\n' "$f" "$rl" "$hl" "$rh" "$hh"
    rm -rf "$w"
}
export -f one
tr '\n' '\0' < "$ENTRIES" | xargs -0 -P4 -I{} bash -c 'one "$1"' _ {} | sort > "$OUT"
echo "done $(wc -l < "$OUT") programs -> $OUT"
