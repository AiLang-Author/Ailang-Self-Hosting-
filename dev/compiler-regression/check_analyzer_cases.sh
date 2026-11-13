#!/bin/bash
# Run the analyzer case files.
# A bad function fails when a required MEM- code is missing.
# A quiet function fails when any MEM- code names it.
# gap and edge functions are printed and do not fail.
# Usage: dev/compiler-regression/check_analyzer_cases.sh [/path/to/analyzer]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ANALYZER="${1:-/tmp/analyzer-mem.x}"
CASE_DIR="$ROOT/dev/compiler-regression/analyzer-cases"
fail=0

if [[ ! -x "$ANALYZER" ]]; then
    echo "missing analyzer: $ANALYZER" >&2
    exit 2
fi

python3 - "$ANALYZER" "$CASE_DIR" <<'PY'
import subprocess, sys
from pathlib import Path

analyzer = sys.argv[1]
case_dir = Path(sys.argv[2])
files = [
    "bad_blocks.ailang",
    "bad_paths.ailang",
    "good_blocks.ailang",
    "good_edges.ailang",
]
fail = 0

def load_expects(path):
    funcs = []
    pending = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("// expect:"):
            pending.append(stripped.split(":", 1)[1].strip())
        elif stripped.startswith("Function.") or stripped.startswith("SubRoutine."):
            name = stripped.split(".", 1)[1].split()[0]
            funcs.append((name, pending))
            pending = []
    return funcs

for fname in files:
    path = case_dir / fname
    print(f"\n=== {fname} ===")
    proc = subprocess.run([analyzer, str(path), "--brief"], capture_output=True, text=True)
    text = proc.stdout + proc.stderr
    if proc.returncode not in (0, 1):
        print(f"FAIL {fname}: analyzer exit {proc.returncode}")
        sys.stderr.write(text)
        fail = 1
        continue
    mem_lines = [ln.strip() for ln in text.splitlines() if "MEM-" in ln]
    expects = load_expects(path)
    seen = {name: [] for name, _ in expects}
    for ln in mem_lines:
        for name in seen:
            if f"in '{name}'" in ln:
                seen[name].append(ln)
    for name, codes in expects:
        hits = seen.get(name, [])
        if codes == ["quiet"]:
            if hits:
                fail = 1
                print(f"FAIL {name}: quiet function was flagged")
                for ln in hits:
                    print(f"  {ln}")
            else:
                print(f"ok   {name}")
        elif codes == ["gap"] or codes == ["edge"]:
            label = codes[0].upper()
            if hits:
                print(f"{label} {name}")
                for ln in hits:
                    print(f"  {ln}")
            else:
                print(f"{label} {name}: no MEM- line")
        else:
            missing = []
            for code in codes:
                if not any(code in ln for ln in hits):
                    missing.append(code)
            extra = []
            for ln in hits:
                if not any(code in ln for code in codes):
                    extra.append(ln)
            if missing or extra:
                fail = 1
                if missing:
                    print(f"FAIL {name}: missing {', '.join(missing)}")
                if extra:
                    print(f"FAIL {name}: unexpected memory line")
                for ln in hits:
                    print(f"  {ln}")
            else:
                print(f"ok   {name}: {', '.join(codes)}")
    named = set()
    for ln in mem_lines:
        for name in seen:
            if f"in '{name}'" in ln:
                named.add(ln)
    orphans = [ln for ln in mem_lines if ln not in named]
    for ln in orphans:
        print(f"NOTE unscoped {ln}")

sys.exit(fail)
PY
