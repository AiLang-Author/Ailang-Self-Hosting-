#!/usr/bin/env bash
# Full CPython-shaped conformance scorecard (test262 analog).
# curated = stdout vs python3; lib = transpile CPython stdlib; test = transpile Lib/test.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
exec python3 tools/aimacro_cpython_runner.py --corpus all \
  --timeout 20 \
  --output-json results/aimacro_conformance.json \
  --output-md AIMacro/CONFORMANCE.md \
  "$@"
