#!/usr/bin/env bash
# Build a Telegram-friendly AILang CAD dogfood zip (Linux x86_64).
# Output: dist/AILang-CAD-dogfood-YYYYMMDD.zip  (typically < 10 MB)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
STAMP="${DOGFOOD_STAMP:-$(date +%Y%m%d)}"
NAME="AILang-CAD-dogfood-${STAMP}"
OUT="$ROOT/dist/${NAME}"
ZIP="$ROOT/dist/${NAME}.zip"

echo "== dogfood package: $NAME =="

# Ensure hosts + app built
if [[ ! -x CAD/host/cad_host_x11 ]] || [[ CAD/host/cad_host_x11 -ot CAD/host/cad_host_x11.c ]]; then
  cc -O2 -o CAD/host/cad_host_x11 CAD/host/cad_host_x11.c -lX11 -lm
fi
if [[ ! -x CAD/host/cad_panel_x11 ]] || [[ CAD/host/cad_panel_x11 -ot CAD/host/cad_panel_x11.c ]]; then
  cc -O2 -o CAD/host/cad_panel_x11 CAD/host/cad_panel_x11.c -lX11
fi
if [[ ! -x cad_app.x ]] || [[ cad_app.x -ot CAD/cad_app.ailang ]]; then
  ./ailang.x CAD/cad_app.ailang -o /tmp/cad_app_dogfood.x
  cp -f /tmp/cad_app_dogfood.x cad_app.x
  chmod +x cad_app.x
fi

rm -rf "$OUT"
mkdir -p "$OUT/bin" "$OUT/scripts" "$OUT/samples" "$OUT/docs"

cp -f dist/dogfood/README.md "$OUT/README.md"
cp -f LICENSE "$OUT/LICENSE" 2>/dev/null || cp -f License.md "$OUT/LICENSE"
cp -f WORKSPACE.md "$OUT/WORKSPACE.md" 2>/dev/null || true
cp -f docs/cad/CAD_UI_PLAN.md "$OUT/docs/CAD_UI_PLAN.md" 2>/dev/null || true

cp -f cad_app.x "$OUT/bin/cad_app.x"
cp -f CAD/host/cad_host_x11 "$OUT/bin/cad_host_x11"
cp -f CAD/host/cad_panel_x11 "$OUT/bin/cad_panel_x11"
chmod +x "$OUT/bin/"*

# Prefer dogfood-kit scripts (state dir /tmp/cad_app_dogfood); fall back to monorepo
if [[ -f dist/dogfood/scripts/cad_cmd.sh ]]; then
  cp -f dist/dogfood/scripts/cad_cmd.sh dist/dogfood/scripts/cad_shot.sh \
    dist/dogfood/scripts/frame_to_png.py dist/dogfood/scripts/run_dogfood.sh "$OUT/scripts/"
else
  cp -f CAD/scripts/cad_cmd.sh CAD/scripts/cad_shot.sh CAD/scripts/frame_to_png.py \
    dist/dogfood/scripts/run_dogfood.sh "$OUT/scripts/"
fi
chmod +x "$OUT/scripts/"*.sh

# sample DXF if present
for f in test-stl/test-dxf-files/diamond.dxf test-stl/test-dxf-files/bridge.dxf \
         test-stl/sample_fusion_sketch.dxf; do
  [[ -f "$f" ]] && cp -f "$f" "$OUT/samples/" && break
done

# one viewport shot if we have a recent smoke image
for f in /tmp/cad_ang.png /tmp/cad_restored.png /tmp/cad_ui_smoke.png; do
  if [[ -f "$f" ]]; then
    cp -f "$f" "$OUT/docs/viewport_sample.png"
    break
  fi
done

cat > "$OUT/GITHUB.txt" <<'EOF'
AILang Self-Hosting monorepo
https://github.com/AiLang-Author/Ailang-Self-Hosting-

Clone for full compiler, libraries, FLTK shell, browser, GPU kit, and docs.
This zip is only a CAD dogfood binary kit for design feedback.
EOF

rm -f "$ZIP"
( cd "$ROOT/dist" && zip -r -9 "${NAME}.zip" "$NAME" -x '*.DS_Store' )
SIZE=$(du -h "$ZIP" | awk '{print $1}')
echo "Wrote $ZIP ($SIZE)"
echo "Drop into Telegram with a short note pointing at the GitHub URL above."
ls -la "$ZIP"
