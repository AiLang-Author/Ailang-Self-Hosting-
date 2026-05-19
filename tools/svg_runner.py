#!/usr/bin/env python3
"""
svg_runner.py — SVG rendering test runner for Ailang SVG Library

Renders SVG test files through the standalone svg_test.x binary and produces
diagnostic output: crash/success status, element count, edge count, pixel
analysis (blank check, color histogram), and optional PPM dump.

Usage:
    python3 tools/svg_runner.py                  # Run all SVG tests
    python3 tools/svg_runner.py --test rect      # Run only rect.svg
    python3 tools/svg_runner.py --dump-ppm /tmp  # Save PPM output files
    python3 tools/svg_runner.py --verbose        # Show full binary stdout
    python3 tools/svg_runner.py --timeout 30     # Custom timeout (seconds)
    python3 tools/svg_runner.py --size 256       # Render at 256x256

Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
"""

import os
import sys
import subprocess
import argparse
import shutil
from pathlib import Path
from collections import Counter

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
SVG_TEST_BIN = PROJECT_DIR / "svg_test.x"
SVG_TEST_DIR = PROJECT_DIR / "tests" / "svg" / "basic"


def render_svg(svg_path, output_ppm, width=512, height=512, timeout=15):
    """Render an SVG file through the svg_test.x binary.
    Returns (success, stdout, stderr, returncode, elem_count, edge_count)."""
    try:
        os.unlink(output_ppm)
    except FileNotFoundError:
        pass

    try:
        result = subprocess.run(
            [str(SVG_TEST_BIN), str(svg_path), output_ppm, str(width), str(height)],
            capture_output=True,
            timeout=timeout,
            cwd=str(PROJECT_DIR),
        )
    except subprocess.TimeoutExpired:
        return False, "", "TIMEOUT", -1, 0, 0
    except Exception as e:
        return False, "", str(e), -1, 0, 0

    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")

    elem_count = 0
    edge_count = 0
    for line in stdout.split("\n"):
        if "Elements rendered:" in line:
            try:
                elem_count = int(line.split(":")[-1].strip())
            except ValueError:
                pass
        if "Edge count:" in line:
            try:
                edge_count = int(line.split(":")[-1].strip())
            except ValueError:
                pass

    success = result.returncode == 0 and os.path.exists(output_ppm)
    return success, stdout, stderr, result.returncode, elem_count, edge_count


def read_ppm(ppm_path):
    """Read a P6 PPM file, return (width, height, pixel_data) or None."""
    try:
        with open(ppm_path, "rb") as f:
            magic = f.readline().strip()
            if magic != b"P6":
                return None
            line = f.readline()
            while line.startswith(b"#"):
                line = f.readline()
            w, h = map(int, line.split())
            f.readline()  # max value
            data = f.read()
        return w, h, data
    except Exception:
        return None


def analyze_ppm(ppm_path):
    """Analyze a PPM file: blank check, dominant colors, dimensions."""
    info = read_ppm(ppm_path)
    if info is None:
        return {"exists": False}

    w, h, data = info
    total_pixels = w * h
    color_counts = Counter()
    non_white = 0
    non_white_non_black = 0

    sample_step = max(1, total_pixels // 50000)
    sampled = 0
    for i in range(0, len(data) - 2, sample_step * 3):
        r, g, b = data[i], data[i + 1], data[i + 2]
        sampled += 1
        if (r, g, b) != (255, 255, 255):
            non_white += 1
        if (r, g, b) != (0, 0, 0) and (r, g, b) != (255, 255, 255):
            non_white_non_black += 1
        rq, gq, bq = r >> 3, g >> 3, b >> 3
        color_counts[(rq, gq, bq)] += 1

    top_colors = []
    for (rq, gq, bq), count in color_counts.most_common(10):
        r, g, b = rq << 3, gq << 3, bq << 3
        pct = (count / sampled) * 100 if sampled > 0 else 0
        top_colors.append(f"  rgb({r},{g},{b}): {pct:.1f}%")

    return {
        "exists": True,
        "width": w,
        "height": h,
        "total_pixels": total_pixels,
        "sampled": sampled,
        "non_white": non_white,
        "non_white_pct": (non_white / sampled * 100) if sampled > 0 else 0,
        "has_color": non_white_non_black > 0,
        "top_colors": top_colors,
    }


def run_svg_test(name, svg_path, dump_dir=None, width=512, height=512,
                 timeout=15, verbose=False):
    """Run a single SVG test and print detailed results."""
    print(f"\n{'='*70}")
    print(f"  SVG TEST: {name}")
    print(f"  File: {svg_path}")
    print(f"  Size: {width}x{height}")
    print(f"{'='*70}")

    if not svg_path.exists():
        print(f"  ERROR: Test file not found: {svg_path}")
        return "MISSING"

    output_ppm = f"/tmp/svg_{name}.ppm"
    success, stdout, stderr, rc, elems, edges = render_svg(
        svg_path, output_ppm, width, height, timeout
    )

    if rc == -1 and "TIMEOUT" in stderr:
        status = "TIMEOUT"
    elif not success:
        status = "CRASH"
    else:
        status = "RENDER"  # rendered successfully, visual inspection needed

    print(f"\n  Status:          {status}")
    print(f"  Exit code:       {rc}")
    print(f"  Elements:        {elems}")
    print(f"  Edges:           {edges}")

    if verbose and stdout.strip():
        print(f"\n  --- stdout ---")
        for line in stdout.strip().split("\n"):
            print(f"    {line}")

    if verbose and stderr.strip():
        print(f"\n  --- stderr ---")
        for line in stderr.strip().split("\n")[:30]:
            print(f"    {line}")

    # Analyze output image
    if success:
        ppm_info = analyze_ppm(output_ppm)
        if ppm_info["exists"]:
            print(f"\n  PPM Output:      {ppm_info['width']}x{ppm_info['height']}")
            print(
                f"  Non-white:       {ppm_info['non_white_pct']:.1f}% "
                f"({ppm_info['non_white']}/{ppm_info['sampled']} sampled)"
            )
            print(f"  Has color:       {ppm_info['has_color']}")
            print(f"  Top colors:")
            for c in ppm_info["top_colors"][:8]:
                print(f"    {c}")

            # Blank check — stroke-only SVGs may have <1% coverage, use 0.3% threshold
            if ppm_info["non_white_pct"] < 0.3:
                status = "BLANK"
                print(f"\n  WARNING: Image appears blank (< 0.3% non-white)")
            elif elems == 0:
                status = "NO_ELEMS"
                print(f"\n  WARNING: No SVG elements were processed")
            else:
                status = "RENDER"
        else:
            print(f"  PPM Output:      INVALID/MISSING")
            status = "FAIL"

        if dump_dir:
            dump_path = os.path.join(dump_dir, f"svg_{name}.ppm")
            try:
                shutil.copy2(output_ppm, dump_path)
                print(f"\n  PPM saved to:    {dump_path}")
            except Exception as e:
                print(f"\n  PPM save failed: {e}")

    print(f"\n  RESULT: {name} => {status}")
    print(f"{'='*70}")
    return status


def main():
    parser = argparse.ArgumentParser(
        description="SVG Rendering Test Runner for Ailang SVG Library"
    )
    parser.add_argument(
        "--test", metavar="NAME",
        help="Run specific test (e.g., rect, circle, path_curves)",
    )
    parser.add_argument(
        "--dump-ppm", metavar="DIR",
        help="Save PPM output to this directory",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show full binary output",
    )
    parser.add_argument(
        "--timeout", type=int, default=15,
        help="Timeout per render in seconds (default: 15)",
    )
    parser.add_argument(
        "--size", type=int, default=512,
        help="Render size WxW pixels (default: 512)",
    )
    args = parser.parse_args()

    if not SVG_TEST_BIN.exists():
        print(f"ERROR: SVG test binary not found at {SVG_TEST_BIN}")
        print(f"Build it first:")
        print(f"  ./ailang.x TestCode/svg_test.ailang svg_test.x")
        sys.exit(1)

    if not SVG_TEST_DIR.exists():
        print(f"ERROR: SVG test directory not found at {SVG_TEST_DIR}")
        sys.exit(1)

    if args.dump_ppm:
        os.makedirs(args.dump_ppm, exist_ok=True)

    # Collect test files
    if args.test:
        svg_file = SVG_TEST_DIR / f"{args.test}.svg"
        if not svg_file.exists():
            print(f"ERROR: Test file not found: {svg_file}")
            sys.exit(1)
        tests = [(args.test, svg_file)]
    else:
        tests = sorted(
            (p.stem, p)
            for p in SVG_TEST_DIR.glob("*.svg")
        )

    if not tests:
        print("No SVG test files found.")
        sys.exit(1)

    w = args.size
    h = args.size

    print(f"\nAilang SVG Library — Test Runner")
    print(f"Binary:    {SVG_TEST_BIN}")
    print(f"Test dir:  {SVG_TEST_DIR}")
    print(f"Size:      {w}x{h}")
    print(f"Tests:     {len(tests)}")

    results = {}
    for name, svg_path in tests:
        results[name] = run_svg_test(
            name, svg_path, args.dump_ppm, w, h, args.timeout, args.verbose
        )

    # Summary
    print(f"\n{'='*70}")
    print(f"  SVG TEST SUMMARY")
    print(f"{'='*70}")

    render_count = 0
    fail_count = 0
    blank_count = 0
    crash_count = 0

    for name, status in results.items():
        if status == "RENDER":
            icon = "[OK  ]"
            render_count += 1
        elif status == "BLANK":
            icon = "[BLNK]"
            blank_count += 1
        elif status in ("CRASH", "TIMEOUT"):
            icon = "[FAIL]"
            crash_count += 1
        else:
            icon = "[????]"
            fail_count += 1
        print(f"  {icon} {name}: {status}")

    total = len(results)
    print(f"\n  Rendered: {render_count}/{total}")
    if blank_count > 0:
        print(f"  Blank:    {blank_count}/{total}")
    if crash_count > 0:
        print(f"  Crashed:  {crash_count}/{total}")
    if fail_count > 0:
        print(f"  Failed:   {fail_count}/{total}")
    print(f"{'='*70}\n")

    sys.exit(0 if crash_count == 0 else 1)


if __name__ == "__main__":
    main()
