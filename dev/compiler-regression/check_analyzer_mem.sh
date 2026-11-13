#!/bin/bash
# Lock the memory-analyzer scoreboard. The probe is not a runtime test.
# Usage: dev/compiler-regression/check_analyzer_mem.sh [/path/to/analyzer]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ANALYZER="${1:-/tmp/analyzer-mem.x}"
PROBE="$ROOT/dev/compiler-regression/analyzer_mem_probe.ailang"
OUT="$(mktemp)"
trap 'rm -f "$OUT"' EXIT

if [[ ! -x "$ANALYZER" ]]; then
    echo "missing analyzer: $ANALYZER" >&2
    exit 2
fi

set +e
"$ANALYZER" "$PROBE" --brief >"$OUT"
code=$?
set -e
if [[ "$code" -ne 1 ]]; then
    echo "expected exit 1, got $code" >&2
    exit 1
fi

expect() {
    local label="$1"
    local n="$2"
    if ! grep -q "^${label}: ${n}$" "$OUT"; then
        echo "missing scoreboard line: ${label}: ${n}" >&2
        grep -n "Memory issues" -A 20 "$OUT" >&2 || true
        exit 1
    fi
}

expect "Leaks (never freed)" 5
expect "Dropped (overwritten live block)" 1
expect "Discarded (result not stored)" 1
expect "Returned and freed" 1
expect "Use after free" 6
expect "Double free" 2
expect "Alloc in loop" 2
expect "Freed on one path" 5
expect "Size mismatch" 2
expect "Arena temporary" 2
expect "Kind mismatch" 1
expect "Unowned free" 2
expect "Freed inside loop" 1

# These functions must stay free of memory codes.
for name in Clean RightSize BothSides StoredConcat PassedConcat UsesGiveTake HalfAllocFree ArrayClean; do
    if grep -E "MEM-.* in '${name}'" "$OUT"; then
        echo "unexpected memory code in ${name}" >&2
        exit 1
    fi
done

# And the new codes must name the function that produces them.
for pair in \
    "MEM-KIND:KindMix" \
    "MEM-REPEAT:SpinFree" \
    "MEM-FREE:FreeGhost" \
    "MEM-FREE:HalfFree" \
    "MEM-PATH:HalfAlloc" \
    "MEM-SIZE:BothAlloc" \
    "MEM-ARENA:ArenaFree" \
    "MEM-LOOP:ForLeak"
do
    code="${pair%%:*}"
    func="${pair##*:}"
    if ! grep -E "${code} .* in '${func}'" "$OUT"; then
        echo "missing ${code} in ${func}" >&2
        exit 1
    fi
done

if grep -q "Memory & Structure" "$OUT"; then
    echo "--brief still printed pass stats" >&2
    exit 1
fi

echo "analyzer memory checks passed ($ANALYZER)"
