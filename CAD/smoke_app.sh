#!/usr/bin/env bash
# M-B + M-C: cad_app headless, sketch-demo, IPC, host build
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p test-stl /tmp/cad_app

echo "[app] build host + tools panel"
cc -O2 -o CAD/host/cad_host_x11 CAD/host/cad_host_x11.c -lX11
cc -O2 -o CAD/host/cad_panel_x11 CAD/host/cad_panel_x11.c -lX11

echo "[app] build cad_app"
./ailang.x CAD/cad_app.ailang -o cad_app.x

echo "[app] headless DXF pad+view"
./cad_app.x --headless -i test-stl/test-dxf-files/cube.dxf -H 12 -o test-stl/cad_app.bmp
test -s test-stl/cad_app.bmp
test -s test-stl/cad_app.stp
test "$(grep -c ADVANCED_FACE test-stl/cad_app.stp)" -ge 6

echo "[app] DXF solid: keyhole poly pad"
./cad_app.x --headless -i test-stl/test-dxf-files/keyhole.dxf -H 8 -o test-stl/cad_app_keyhole.bmp
test -s test-stl/cad_app_keyhole.bmp
test "$(grep -c ADVANCED_FACE test-stl/cad_app.stp)" -ge 10

echo "[app] DXF solid: multi-loop plate+hole (single file)"
./cad_app.x --headless -i test-stl/test-dxf-files/lwpoly_plate_hole.dxf -H 5 -o test-stl/cad_app_plate_hole.bmp
test -s test-stl/cad_app_plate_hole.bmp
# outer box + through hole → more than 6 faces
test "$(grep -c ADVANCED_FACE test-stl/cad_app.stp)" -ge 8

echo "[app] DXF solid: plate + hole DXF pair (escutcheon)"
./cad_app.x --headless \
  -i test-stl/test-dxf-files/escutcheon_plate.dxf \
  --hole test-stl/test-dxf-files/keyhole_flared.dxf \
  -H 4 -o test-stl/cad_app_escutcheon.bmp
test -s test-stl/cad_app_escutcheon.bmp
test "$(grep -c ADVANCED_FACE test-stl/cad_app.stp)" -ge 8

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

echo "[app] M-D orbit/zoom IPC (gen advances, free cam persists)"
rm -rf /tmp/cad_app
mkdir -p /tmp/cad_app
wait_gen() {
  # wait until gen.txt >= $1 (max ~30s)
  want=$1
  for _ in $(seq 1 300); do
    g=$(cat /tmp/cad_app/gen.txt 2>/dev/null || echo 0)
    g=${g//[^0-9]/}
    g=${g:-0}
    [ "$g" -ge "$want" ] && { echo "$g"; return 0; }
    sleep 0.1
  done
  echo "${g:-0}"
  return 1
}
(
  wait_gen 1 >/dev/null
  echo "orbit 80 -40" > /tmp/cad_app/cmd.txt
  g1=$(wait_gen 2)
  echo "zoom 3" > /tmp/cad_app/cmd.txt
  g2=$(wait_gen $((g1 + 1)))
  echo "orbit -30 20" > /tmp/cad_app/cmd.txt
  g3=$(wait_gen $((g2 + 1)))
  # nav cube top face: 400x300 → x0=298 y0=12 s3=30 → top ~313,27
  echo "click 313 27" > /tmp/cad_app/cmd.txt
  g4=$(wait_gen $((g3 + 1)))
  echo "$g1 $g2 $g3 $g4" > /tmp/cad_app/md_gens.txt
  echo quit > /tmp/cad_app/cmd.txt
) &
# smaller FB so software re-render is fast enough for CI
timeout 60 ./cad_app.x --nohost -i test-stl/test-dxf-files/diamond.dxf -H 15 -W 400 --imgh 300 || true
test -s /tmp/cad_app/md_gens.txt
read g1 g2 g3 g4 < /tmp/cad_app/md_gens.txt
echo "[app] M-D gens: orbit=$g1 zoom=$g2 orbit2=$g3 cube=$g4"
test "$g1" -ge 2
test "$g2" -gt "$g1"
test "$g3" -gt "$g2"
test "$g4" -gt "$g3"

echo "[app] Postgres CAD_Repo (skip if no cad_db)"
if pg_isready -q 2>/dev/null && psql -d cad_db -c "SELECT 1" >/dev/null 2>&1; then
  ./ailang.x CAD/test_repo_live.ailang -o test_repo_live.x
  ./test_repo_live.x
  test -s test-stl/cad_repo_load.stp
  ./cad_app.x --headless -i test-stl/test-dxf-files/diamond.dxf -H 11 \
    --name smoke_app_part --save -o test-stl/cad_app_repo_save.bmp
  ./cad_app.x --headless --load --name smoke_app_part -o test-stl/cad_app_repo_load.bmp
  test -s test-stl/cad_app_repo_load.bmp
  test "$(grep -c ADVANCED_FACE test-stl/cad_app.stp)" -ge 6
  echo "[app] Postgres CAD_Repo OK"
else
  echo "[app] Postgres CAD_Repo SKIPPED (create DB: createdb cad_db)"
fi

echo "[app] ALL OK"
