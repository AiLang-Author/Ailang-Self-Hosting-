#!/usr/bin/env python3
"""
export_font_glyphs.py — FontForge glyph exporter for AILang VIF pipeline.
Extracts every glyph from a TTF/OTF as individual SVG + metrics JSON.

Usage:
    python3 export_font_glyphs.py NotoSans-Regular.ttf output_dir/
    python3 export_font_glyphs.py Roboto-Regular.ttf output_dir/ --size 1024
    python3 export_font_glyphs.py MyFont.otf output_dir/ --range 32-126

Requires: fontforge (apt install fontforge python3-fontforge)

Output:
    output_dir/
        font_meta.json          — font-level metrics
        glyphs/
            0065_A.svg          — glyph SVG (codepoint_name.svg)
            0061_a.svg
            ...
        metrics.json            — per-glyph metrics (advance, bearing, bbox)
        kerning.json            — kerning pairs

Then run svg2tvg on each SVG to get TVG files for the VIF pipeline.

Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
"""

import sys
import os
import json
import argparse

try:
    import fontforge
except ImportError:
    print("ERROR: fontforge module not found.")
    print("Install with: sudo apt install fontforge python3-fontforge")
    sys.exit(1)


def export_font(font_path, output_dir, em_size=1024, cp_range=None):
    """Export all glyphs from font_path into output_dir."""

    # Open font
    font = fontforge.open(font_path)
    font_name = font.fontname
    family = font.familyname

    print(f"[export] Font: {font_name} ({family})")
    print(f"[export] EM size: {font.em}")
    print(f"[export] Ascent: {font.ascent}, Descent: {font.descent}")

    # Create output dirs
    glyph_dir = os.path.join(output_dir, "glyphs")
    os.makedirs(glyph_dir, exist_ok=True)

    # Scale to target EM if needed
    if em_size and em_size != font.em:
        print(f"[export] Scaling EM from {font.em} to {em_size}")
        font.em = em_size

    # Font-level metadata
    font_meta = {
        "name": font_name,
        "family": family,
        "em": font.em,
        "ascent": font.ascent,
        "descent": font.descent,
        "os2_typo_ascent": font.os2_typoascent,
        "os2_typo_descent": font.os2_typodescent,
        "os2_typo_linegap": font.os2_typolinegap,
        "weight": font.weight,
        "version": font.version if hasattr(font, 'version') else "",
    }

    # Determine codepoint range
    if cp_range:
        start, end = cp_range
    else:
        # Default: Basic Latin + Latin-1 Supplement + common punctuation
        start, end = 32, 0xFFFF  # We'll filter to only existing glyphs

    # Export glyphs
    glyph_metrics = []
    exported = 0
    skipped = 0

    font.selection.all()

    for glyph in font.glyphs():
        cp = glyph.unicode
        if cp < 0:
            continue
        if cp_range and (cp < start or cp > end):
            continue

        # Skip empty glyphs (no outlines)
        if not glyph.isWorthOutputting():
            continue

        # Get glyph name
        gname = glyph.glyphname
        if not gname or gname == ".notdef":
            continue

        # Build filename: codepoint_name.svg
        fname = f"{cp:04X}_{gname}.svg"
        svg_path = os.path.join(glyph_dir, fname)

        # Composite glyphs (colon = two periods, quotedbl, etc.) export
        # as an empty <g/> unless references are unlinked first.
        try:
            glyph.unlinkRef()
        except Exception:
            pass

        # Export SVG
        try:
            glyph.export(svg_path)
        except Exception as e:
            print(f"  [skip] U+{cp:04X} {gname}: {e}")
            skipped += 1
            continue

        # Check file was actually created and has content
        if not os.path.exists(svg_path) or os.path.getsize(svg_path) == 0:
            skipped += 1
            continue

        # Collect metrics
        bbox = glyph.boundingBox()  # (xmin, ymin, xmax, ymax)
        metrics = {
            "codepoint": cp,
            "name": gname,
            "file": fname,
            "advance": glyph.width,
            "vadvance": glyph.vwidth,
            "bearing_x": int(bbox[0]) if bbox else 0,
            "bearing_y": int(bbox[3]) if bbox else 0,
            "bbox": {
                "xmin": int(bbox[0]) if bbox else 0,
                "ymin": int(bbox[1]) if bbox else 0,
                "xmax": int(bbox[2]) if bbox else 0,
                "ymax": int(bbox[3]) if bbox else 0,
            },
        }
        glyph_metrics.append(metrics)
        exported += 1

    print(f"[export] Exported {exported} glyphs, skipped {skipped}")

    # Extract kerning pairs
    kern_pairs = []
    for glyph in font.glyphs():
        cp_left = glyph.unicode
        if cp_left < 0:
            continue
        pst = glyph.getPosSub("*")
        for entry in pst:
            # Kerning is typically in GPOS pair positioning
            if len(entry) >= 5 and entry[1] == "Pair":
                right_name = entry[2]
                x_adj = entry[3] if len(entry) > 3 else 0
                # Find right codepoint
                right_glyph = font[right_name] if right_name in font else None
                if right_glyph and right_glyph.unicode >= 0:
                    kern_pairs.append({
                        "left": cp_left,
                        "right": right_glyph.unicode,
                        "adjust_x": x_adj,
                    })

    print(f"[export] Found {len(kern_pairs)} kerning pairs")

    # Write metadata files
    meta_path = os.path.join(output_dir, "font_meta.json")
    with open(meta_path, "w") as f:
        json.dump(font_meta, f, indent=2)
    print(f"[export] Wrote {meta_path}")

    metrics_path = os.path.join(output_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(glyph_metrics, f, indent=2)
    print(f"[export] Wrote {metrics_path}")

    kern_path = os.path.join(output_dir, "kerning.json")
    with open(kern_path, "w") as f:
        json.dump(kern_pairs, f, indent=2)
    print(f"[export] Wrote {kern_path}")

    font.close()
    print(f"[export] Done. Run svg2tvg on glyphs/ to convert to TVG.")
    return exported


def main():
    parser = argparse.ArgumentParser(
        description="Export font glyphs as SVG + metrics for AILang VIF pipeline"
    )
    parser.add_argument("font", help="Path to TTF/OTF font file")
    parser.add_argument("output", help="Output directory")
    parser.add_argument("--size", type=int, default=1024,
                        help="Target EM size (default: 1024)")
    parser.add_argument("--range", type=str, default=None,
                        help="Codepoint range, e.g. 32-126 for ASCII")

    args = parser.parse_args()

    cp_range = None
    if args.range:
        parts = args.range.split("-")
        cp_range = (int(parts[0]), int(parts[1]))

    if not os.path.exists(args.font):
        print(f"ERROR: Font file not found: {args.font}")
        sys.exit(1)

    export_font(args.font, args.output, args.size, cp_range)


if __name__ == "__main__":
    main()