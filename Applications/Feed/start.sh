#!/usr/bin/env bash
# Compile (if needed) and run Applications/Feed/feed_server.ailang.
# Does not overwrite the live ./ailang.x compiler.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${FEED_BIN:-/tmp/feed_server.x}"
cd "$ROOT"
if [[ ! -x ./ailang.x ]]; then
  echo "FAIL missing ./ailang.x" >&2
  exit 1
fi
need=0
if [[ ! -x "$OUT" ]]; then
  need=1
fi
if [[ $need -eq 0 && Applications/Feed/feed_server.ailang -nt "$OUT" ]]; then
  need=1
fi
if [[ $need -eq 0 && Librarys/Library.SQLite.ailang -nt "$OUT" ]]; then
  need=1
fi
if [[ $need -eq 0 && Librarys/Library.HTTP1.ailang -nt "$OUT" ]]; then
  need=1
fi
if [[ $need -eq 1 ]]; then
  ./ailang.x Applications/Feed/feed_server.ailang -o "$OUT"
fi
: "${SQLITE_PATH:?SQLITE_PATH is required}"
export JWT_SECRET="${JWT_SECRET:-twelve-dollar-challenge}"
export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-3000}"
exec "$OUT"
