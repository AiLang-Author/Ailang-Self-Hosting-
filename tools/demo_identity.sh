#!/usr/bin/env bash
# Compile Demo Programs/programs with host and next. Never writes ailang.x.
# Reports: identical / diverged / next-reject / host-fail / both-fail.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

HOST="$ROOT/ailang.x"
NEXT="$ROOT/ailang-next.x"
DEMO_DIR="$ROOT/Demo Programs/programs"
OUT="$ROOT/tests/contract/_out/demos"
mkdir -p "$OUT"

[[ -x "$HOST" ]] || { echo "missing $HOST" >&2; exit 1; }
[[ -x "$NEXT" ]] || { echo "missing $NEXT" >&2; exit 1; }
[[ -d "$DEMO_DIR" ]] || { echo "missing $DEMO_DIR" >&2; exit 1; }

identical=0
diverged=0
next_reject=0
host_fail=0
both_fail=0
host_only=0
timeouts=0
total=0

compile_one() {
    local cc="$1" src="$2" dst="$3" log="$4"
    set +e
    timeout 45 "$cc" "$src" "$dst" >"$log" 2>&1
    local rc=$?
    set -e
    echo "$rc"
}

echo "Demo corpus: $DEMO_DIR"
echo "Host: $HOST"
echo "Next: $NEXT"
echo

shopt -s nullglob
for src in "$DEMO_DIR"/*.ailang; do
    total=$((total + 1))
    base="$(basename "$src" .ailang)"
    host_x="$OUT/${base}.host.x"
    next_x="$OUT/${base}.next.x"
    host_log="$OUT/${base}.host.log"
    next_log="$OUT/${base}.next.log"

    hrc="$(compile_one "$HOST" "$src" "$host_x" "$host_log")"
    nrc="$(compile_one "$NEXT" "$src" "$next_x" "$next_log")"

    if [[ "$hrc" -eq 124 || "$nrc" -eq 124 ]]; then
        timeouts=$((timeouts + 1))
        echo "TIMEOUT  $base  host=$hrc next=$nrc"
        continue
    fi

    if [[ "$hrc" -ne 0 && "$nrc" -ne 0 ]]; then
        both_fail=$((both_fail + 1))
        echo "BOTH_FAIL  $base"
        continue
    fi
    if [[ "$hrc" -ne 0 && "$nrc" -eq 0 ]]; then
        host_only=$((host_only + 1))
        echo "HOST_FAIL_NEXT_OK  $base"
        continue
    fi
    if [[ "$hrc" -eq 0 && "$nrc" -ne 0 ]]; then
        next_reject=$((next_reject + 1))
        echo "NEXT_REJECT  $base"
        continue
    fi

    if cmp -s "$host_x" "$next_x"; then
        identical=$((identical + 1))
        echo "IDENTICAL  $base"
    else
        diverged=$((diverged + 1))
        echo "DIVERGED   $base"
    fi
done

echo
echo "=== DEMO IDENTITY SUMMARY ==="
echo "total:        $total"
echo "identical:    $identical"
echo "diverged:     $diverged"
echo "next-reject:  $next_reject"
echo "host-fail:    $host_fail"
echo "both-fail:    $both_fail"
echo "host-only:    $host_only"
echo "timeout:      $timeouts"
echo
echo "Logs and ELFs: $OUT"
echo "Shipping ailang.x was not written."
