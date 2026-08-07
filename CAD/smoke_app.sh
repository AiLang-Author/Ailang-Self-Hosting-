#!/usr/bin/env bash
# M-B + M-C: cad_app headless, sketch-demo, IPC, host build
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p test-stl /tmp/cad_app

echo "[app] build host"
cc -O2 -o CAD/host/cad_host_x11 CAD/host/cad_host_x11.c -lX11

echo "[app] build cad_app"
./ailang.x CAD/cad_app.ailang -o cad_app.x

echo "[app] headless DXF pad+view"
./cad_app.x --headless -i test-stl/test-dxf-files/cube.dxf -H 12 -o test-stl/cad_app.bmp
test -s test-stl/cad_app.bmp
test -s test-stl/cad_app.stp
test "$(grep -c ADVANCED_FACE test-stl/cad_app.stp)" -ge 6

echo "[app] sketch-demo (M-C: rect + line + pad + sketch BMP/DXF)"
./cad_app.x --headless --sketch-demo -H 8 -o test-stl/cad_app.bmp
test -s test-stl/cad_app_sketch.bmp
test -s test-stl/cad_app_sketch.dxf
test -s test-stl/cad_app.stp
test "$(grep -c ADVANCED_FACE test-stl/cad_app.stp)" -eq 6

echo "[app] buffer IPC publish (nohost + quit)"
rm -f /tmp/cad_app/cmd.txt
( sleep 1; echo quit > /tmp/cad_app/cmd.txt ) &
timeout 8 ./cad_app.x --nohost -i test-stl/test-dxf-files/cube.dxf -H 8 || true
test -s /tmp/cad_app/frame.raw
test -s /tmp/cad_app/meta.bin
test -s /tmp/cad_app/gen.txt

echo "[app] ALL OK"
