#!/usr/bin/env bash
# M-B: cad_app headless gate + host binary build
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p test-stl /tmp/cad_app

echo "[app] build host"
cc -O2 -o CAD/host/cad_host_x11 CAD/host/cad_host_x11.c -lX11

echo "[app] headless pad+view"
./ailang.x CAD/cad_app.ailang -o cad_app.x
./cad_app.x --headless -i test-stl/test-dxf-files/cube.dxf -H 12 -o test-stl/cad_app.bmp
test -s test-stl/cad_app.bmp
test -s test-stl/cad_app.stp
test "$(grep -c ADVANCED_FACE test-stl/cad_app.stp)" -ge 6

echo "[app] buffer IPC publish (nohost + quit)"
rm -f /tmp/cad_app/cmd.txt
( sleep 1; echo quit > /tmp/cad_app/cmd.txt ) &
timeout 8 ./cad_app.x --nohost -i test-stl/test-dxf-files/cube.dxf -H 8 || true
test -s /tmp/cad_app/frame.raw
test -s /tmp/cad_app/meta.bin
test -s /tmp/cad_app/gen.txt

echo "[app] ALL OK"
