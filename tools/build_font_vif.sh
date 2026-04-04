#!/bin/bash
# build_font_vif.sh — Full font build pipeline
# TTF/OTF → SVG glyphs → TVG glyphs → VIF font package
#
# Usage:
#   ./build_font_vif.sh NotoSans-Regular.ttf fonts/noto-sans/
#   ./build_font_vif.sh Roboto-Regular.ttf fonts/roboto/ --range 32-126
#
# Requirements:
#   - fontforge + python3-fontforge (apt install fontforge python3-fontforge)
#   - svg2tvg from TinyVG tools (https://github.com/TinyVG/sdk)
#
# Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.

set -e

FONT_FILE="$1"
OUTPUT_DIR="$2"
shift 2
EXTRA_ARGS="$@"

if [ -z "$FONT_FILE" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Usage: $0 <font.ttf> <output_dir> [--range 32-126]"
    exit 1
fi

if [ ! -f "$FONT_FILE" ]; then
    echo "ERROR: Font file not found: $FONT_FILE"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GLYPH_DIR="$OUTPUT_DIR/glyphs"
TVG_DIR="$OUTPUT_DIR/tvg"

echo "=== AILang Font Build Pipeline ==="
echo "Font: $FONT_FILE"
echo "Output: $OUTPUT_DIR"

# Step 1: Export glyphs as SVG + metrics
echo ""
echo "--- Step 1: FontForge export ---"
mkdir -p "$OUTPUT_DIR"
fontforge -script "$SCRIPT_DIR/export_font_glyphs.py" "$FONT_FILE" "$OUTPUT_DIR" $EXTRA_ARGS

# Count exported glyphs
SVG_COUNT=$(ls "$GLYPH_DIR"/*.svg 2>/dev/null | wc -l)
echo "SVG glyphs: $SVG_COUNT"

if [ "$SVG_COUNT" -eq 0 ]; then
    echo "ERROR: No glyphs exported"
    exit 1
fi

# Step 2: Convert SVG → TVG
echo ""
echo "--- Step 2: SVG → TVG conversion ---"
mkdir -p "$TVG_DIR"

# Check for svg2tvg
if ! command -v svg2tvg &> /dev/null; then
    echo "WARNING: svg2tvg not found in PATH"
    echo "Install TinyVG SDK from: https://github.com/TinyVG/sdk"
    echo "Or set PATH to include the svg2tvg binary"
    echo ""
    echo "Skipping TVG conversion. SVGs are ready in: $GLYPH_DIR"
    echo "Convert manually with:"
    echo "  for f in $GLYPH_DIR/*.svg; do svg2tvg \$f $TVG_DIR/\$(basename \$f .svg).tvg; done"
    exit 0
fi

CONVERTED=0
FAILED=0
for svg in "$GLYPH_DIR"/*.svg; do
    base=$(basename "$svg" .svg)
    tvg="$TVG_DIR/${base}.tvg"
    if svg2tvg "$svg" "$tvg" 2>/dev/null; then
        CONVERTED=$((CONVERTED + 1))
    else
        FAILED=$((FAILED + 1))
        rm -f "$tvg"
    fi
done

echo "Converted: $CONVERTED TVG files"
if [ "$FAILED" -gt 0 ]; then
    echo "Failed: $FAILED (empty or unsupported glyphs)"
fi

# Step 3: Summary
echo ""
echo "--- Build Complete ---"
echo "Font metadata: $OUTPUT_DIR/font_meta.json"
echo "Glyph metrics: $OUTPUT_DIR/metrics.json"
echo "Kerning pairs: $OUTPUT_DIR/kerning.json"
echo "SVG glyphs:    $GLYPH_DIR/ ($SVG_COUNT files)"
echo "TVG glyphs:    $TVG_DIR/ ($CONVERTED files)"
echo ""
echo "Next: Use the VIF packer to bundle TVGs + metrics into a .vif font file"
echo "=== Done ==="