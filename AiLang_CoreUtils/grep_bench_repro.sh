#!/usr/bin/env bash
# grep_bench_repro.sh — reproducible AILang grep vs GNU grep benchmark
#
# Usage:
#   ./grep_bench_repro.sh
#   AILANG_GREP=/path/grep_exec GNU_GREP=/usr/bin/grep ./grep_bench_repro.sh
#
# Env knobs:
#   AILANG_GREP  AILang grep binary (default: build from dist/grep_util/grep.ailang)
#   GNU_GREP     reference grep, must report "GNU grep" (default: /usr/bin/grep)
#   LINES_N      lines of generated data (default: 2000000, ~128MB)
#   RUNS         timed runs per command (default: 10)
#   WARMUP       warmup runs per command (default: 3)
#   WORKDIR      data + results dir (default: /tmp/ailang_grep_bench)
#   KEEP_DATA    1 = keep the generated data file afterwards
#
# Method notes:
#   - LC_ALL=C for both tools. AILang grep is byte/ASCII-only; GNU grep under
#     a UTF-8 locale pays for multibyte handling, which would flatter AILang.
#   - Output goes to a pipe drained by hyperfine, NOT /dev/null. GNU grep
#     detects stdout == /dev/null and stops at the first match (like -q),
#     which produces bogus ~1ms timings.
#   - Every case is checked for byte-identical output before it is timed.
#   - Regex rows are included on purpose: that path is not yet competitive.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="${WORKDIR:-/tmp/ailang_grep_bench}"
LINES_N="${LINES_N:-2000000}"
RUNS="${RUNS:-10}"
WARMUP="${WARMUP:-3}"
GNU_GREP="${GNU_GREP:-/usr/bin/grep}"
export LC_ALL=C

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
command -v hyperfine >/dev/null || die "hyperfine not found (cargo install hyperfine, or apt install hyperfine)"
command -v python3 >/dev/null || die "python3 not found"
"$GNU_GREP" --version 2>/dev/null | head -1 | grep -q 'GNU grep' || die "$GNU_GREP is not GNU grep"

mkdir -p "$WORKDIR/json"
DATA="$WORKDIR/data.txt"
RESULTS="$WORKDIR/results.md"

if [[ -z "${AILANG_GREP:-}" ]]; then
  AILANG_GREP="$WORKDIR/grep_ailang"
  echo "==> Building AILang grep"
  ( cd "$ROOT" && AILANG_LIB_PATH=./Librarys ./ailang.x \
      AiLang_CoreUtils/dist/grep_util/grep.ailang "$AILANG_GREP" >/dev/null ) \
    || die "AILang build failed"
  chmod +x "$AILANG_GREP"
fi
[[ -x "$AILANG_GREP" ]] || die "AILANG_GREP not executable: $AILANG_GREP"

echo "==> Generating $LINES_N lines (seed 42)"
python3 -I - "$DATA" "$LINES_N" <<'PY'
import random, sys
path, n = sys.argv[1], int(sys.argv[2])
random.seed(42)
words = ['hello','world','function','variable','system','network','process','thread',
         'memory','buffer','kernel','socket','interface','protocol','daemon','signal',
         'CONFIG_OPTION','error_handler','parse_input','write_output','read_buffer']
with open(path, 'w') as f:
    for _ in range(n):
        line = ' '.join(random.choice(words) for _ in range(random.randint(3, 12)))
        if random.random() < 0.001:
            line += ' UNIQUE_MARKER_XYZ'
        f.write(line + '\n')
PY
DATA_SHA="$(sha256sum "$DATA" | cut -c1-16)"
DATA_SIZE="$(stat -c%s "$DATA")"

# label | grep arguments (one pattern argument; quoted for the shell)
CASES=(
  "literal|'kernel'"
  "fixed -F|-F 'kernel'"
  "icase -i|-i 'kernel'"
  "count -c|-c 'kernel'"
  "line numbers -n|-n 'kernel'"
  "invert -v|-v 'kernel'"
  "word -w|-w 'kernel'"
  "word count -wc|-wc 'kernel'"
  "rare literal|'UNIQUE_MARKER_XYZ'"
  "rare count|-c 'UNIQUE_MARKER_XYZ'"
  "long literal -F|-F 'error_handler'"
  "long count -Fc|-Fc 'error_handler'"
  "regex .*|'mem.*buf'"
  "regex class|'ker[nm]el'"
  "regex anchor|'^kernel'"
  "regex alternation -E|-E 'socket|daemon'"
)

echo "==> Correctness check"
bad=0
for c in "${CASES[@]}"; do
  label="${c%%|*}"; args="${c#*|}"
  a=$(eval "\"$AILANG_GREP\" $args \"$DATA\"" | sha256sum | cut -c1-16) || true
  g=$(eval "\"$GNU_GREP\" $args \"$DATA\"" | sha256sum | cut -c1-16) || true
  if [[ "$a" != "$g" ]]; then echo "   MISMATCH: $label"; bad=1; fi
done
[[ $bad -eq 0 ]] || die "output mismatch; refusing to time"
echo "   all ${#CASES[@]} cases byte-identical"

echo "==> Timing (warmup=$WARMUP runs=$RUNS)"
cat "$DATA" > /dev/null
i=0
for c in "${CASES[@]}"; do
  label="${c%%|*}"; args="${c#*|}"
  echo "   $label"
  hyperfine -N --style none --warmup "$WARMUP" --runs "$RUNS" --output pipe \
    --export-json "$WORKDIR/json/$i.json" \
    -n ailang "$AILANG_GREP $args $DATA" \
    -n gnu "$GNU_GREP $args $DATA" >/dev/null
  i=$((i + 1))
done

CPU="$(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | xargs)"
GNU_VER="$("$GNU_GREP" --version | head -1)"
python3 -I - "$WORKDIR/json" "$RESULTS" "$CPU" "$(uname -r)" "$GNU_VER" \
  "$DATA_SIZE" "$LINES_N" "$DATA_SHA" "$RUNS" "$WARMUP" \
  "$(stat -c%s "$AILANG_GREP")" "$(stat -c%s "$(readlink -f "$GNU_GREP")")" \
  "${CASES[@]}" <<'PY'
import json, os, sys
(jdir, out, cpu, kern, gver, size, lines, sha, runs, warm,
 asz, gsz), cases = sys.argv[1:13], sys.argv[13:]
rows, wins = [], 0
for i, c in enumerate(cases):
    label, args = c.split('|', 1)
    res = {r['command']: r for r in json.load(open(os.path.join(jdir, f'{i}.json')))['results']}
    a, g = res['ailang'], res['gnu']
    am, gm = a['median'] * 1000, g['median'] * 1000
    if am <= gm:
        verdict, wins = f'AILang {gm/am:.2f}x', wins + 1
    else:
        verdict = f'GNU {am/gm:.2f}x'
    shown = args.replace('|', '\\|')
    rows.append(f"| {label} | `{shown}` | {am:.1f} ± {a['stddev']*1000:.1f} "
                f"| {gm:.1f} ± {g['stddev']*1000:.1f} | {verdict} |")
md = [
    '# AILang grep vs GNU grep',
    '',
    f'- CPU: {cpu}, kernel {kern}',
    f'- Reference: {gver}, `LC_ALL=C`',
    f'- Data: {int(size)/1e6:.0f} MB, {lines} lines, sha256 {sha}… (seed 42, warm page cache)',
    f'- hyperfine: {warm} warmup + {runs} runs per command, output drained through a pipe',
    f'- Binary size: AILang {int(asz)/1024:.0f} KB, GNU {int(gsz)/1024:.0f} KB',
    '- All cases produce byte-identical output.',
    '',
    '| Case | Args | AILang median ms | GNU median ms | Faster |',
    '|---|---|---|---|---|',
    *rows,
    '',
    f'AILang faster in {wins} of {len(cases)} cases.',
]
open(out, 'w').write('\n'.join(md) + '\n')
print('\n'.join(md))
PY

if [[ "${KEEP_DATA:-0}" != 1 ]]; then rm -f "$DATA"; fi
echo ""
echo "==> Results: $RESULTS"
