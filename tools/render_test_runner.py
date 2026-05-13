#!/usr/bin/env python3
"""
render_test_runner.py — Visual regression test runner for Ailang Browser

Renders test HTML files through the headless browser and compares output
against reference PPM images. Reports pixel diff percentage.

Usage:
    python3 tools/render_test_runner.py                    # Run all tests
    python3 tools/render_test_runner.py --update           # Update reference images
    python3 tools/render_test_runner.py --test box_model   # Run single test
    python3 tools/render_test_runner.py --threshold 5.0    # Allow 5% pixel diff

Directory structure:
    TestCode/render_tests/
        test_box_model.html          <- test input
        ref_box_model.ppm            <- reference screenshot (auto-generated)
        diff_box_model.ppm           <- diff image (generated on failure)

Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
"""

import os
import sys
import struct
import subprocess
import argparse
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
HEADLESS_BIN = PROJECT_DIR / "browser_main.x"
TEST_DIR = PROJECT_DIR / "TestCode" / "render_tests"
INPUT_FILE = Path("/tmp/render_test.html")
OUTPUT_FILE = Path("/tmp/render_out.ppm")

# Image dimensions (must match headless binary)
WIDTH = 1024
HEIGHT = 700
PIXEL_COUNT = WIDTH * HEIGHT


def read_ppm(path):
    """Read a P6 PPM file, return (width, height, bytes) of RGB data."""
    with open(path, 'rb') as f:
        magic = f.readline().strip()
        if magic != b'P6':
            raise ValueError(f"Not a P6 PPM file: {path}")
        # Skip comments
        line = f.readline()
        while line.startswith(b'#'):
            line = f.readline()
        w, h = map(int, line.split())
        maxval = int(f.readline().strip())
        data = f.read()
    return w, h, data


def compare_ppm(ref_path, out_path, diff_path=None):
    """Compare two PPM files. Returns (match_pct, diff_count, total_pixels)."""
    w1, h1, data1 = read_ppm(ref_path)
    w2, h2, data2 = read_ppm(out_path)

    if (w1, h1) != (w2, h2):
        return 0.0, PIXEL_COUNT, PIXEL_COUNT

    total = w1 * h1
    diff_count = 0
    diff_data = bytearray(len(data1)) if diff_path else None

    for i in range(0, len(data1), 3):
        if i + 2 >= len(data1) or i + 2 >= len(data2):
            break
        r1, g1, b1 = data1[i], data1[i+1], data1[i+2]
        r2, g2, b2 = data2[i], data2[i+1], data2[i+2]

        if (r1, g1, b1) != (r2, g2, b2):
            diff_count += 1
            if diff_data is not None:
                # Highlight diff in red
                diff_data[i] = 255
                diff_data[i+1] = 0
                diff_data[i+2] = 0
        else:
            if diff_data is not None:
                # Dim the matching pixels
                diff_data[i] = r1 // 3
                diff_data[i+1] = g1 // 3
                diff_data[i+2] = b1 // 3

    if diff_path and diff_data:
        with open(diff_path, 'wb') as f:
            f.write(f"P6\n{w1} {h1}\n255\n".encode())
            f.write(diff_data)

    match_pct = ((total - diff_count) / total) * 100.0
    return match_pct, diff_count, total


def render_html(html_path):
    """Render an HTML file using the headless browser. Returns True on success."""
    # Copy test HTML to input location
    with open(html_path, 'rb') as f:
        html_data = f.read()
    with open(INPUT_FILE, 'wb') as f:
        f.write(html_data)

    # Remove old output
    if OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()

    # Run headless renderer
    result = subprocess.run(
        [str(HEADLESS_BIN)],
        capture_output=True,
        timeout=10,
        cwd=str(PROJECT_DIR)
    )

    if result.returncode != 0:
        print(f"  RENDERER FAILED (exit {result.returncode})")
        if result.stderr:
            print(f"  stderr: {result.stderr.decode('utf-8', errors='replace')[:200]}")
        return False

    if not OUTPUT_FILE.exists():
        print(f"  NO OUTPUT FILE generated")
        return False

    return True


def get_test_files():
    """Find all test_*.html files in the test directory."""
    if not TEST_DIR.exists():
        TEST_DIR.mkdir(parents=True, exist_ok=True)
    tests = sorted(TEST_DIR.glob("test_*.html"))
    return tests


def ref_path_for(test_path):
    """Get the reference image path for a test file."""
    name = test_path.stem.replace("test_", "ref_")
    return TEST_DIR / (name + ".ppm")


def diff_path_for(test_path):
    """Get the diff image path for a test file."""
    name = test_path.stem.replace("test_", "diff_")
    return TEST_DIR / (name + ".ppm")


def run_test(test_path, threshold=1.0, update=False):
    """Run a single test. Returns (name, passed, match_pct)."""
    name = test_path.stem.replace("test_", "")
    ref = ref_path_for(test_path)

    # Render
    if not render_html(test_path):
        return name, False, 0.0

    if update or not ref.exists():
        # Save as new reference
        import shutil
        shutil.copy2(OUTPUT_FILE, ref)
        print(f"  [{name}] REFERENCE UPDATED")
        return name, True, 100.0

    # Compare
    diff = diff_path_for(test_path)
    match_pct, diff_count, total = compare_ppm(ref, OUTPUT_FILE, diff)

    passed = match_pct >= (100.0 - threshold)

    if passed and diff.exists():
        diff.unlink()  # Clean up diff on pass

    return name, passed, match_pct


def print_summary(results):
    """Print test results summary."""
    total = len(results)
    passed = sum(1 for _, p, _ in results if p)
    failed = total - passed

    print("\n" + "=" * 60)
    print(f"  RENDER TEST RESULTS: {passed}/{total} passed")
    print("=" * 60)

    for name, p, pct in results:
        status = "PASS" if p else "FAIL"
        indicator = " " if p else "*"
        print(f"  {indicator} [{status}] {name:30s} {pct:6.2f}% match")

    if failed > 0:
        print(f"\n  {failed} test(s) FAILED")
        print("  Check diff_*.ppm files for visual comparison")
    else:
        print(f"\n  All {total} tests passed!")

    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Ailang Browser visual regression tests")
    parser.add_argument("--update", action="store_true", help="Update reference images")
    parser.add_argument("--test", type=str, help="Run single test by name")
    parser.add_argument("--threshold", type=float, default=1.0,
                        help="Allowed pixel diff percentage (default: 1.0)")
    parser.add_argument("--list", action="store_true", help="List available tests")
    args = parser.parse_args()

    # Check binary exists
    if not HEADLESS_BIN.exists():
        print(f"ERROR: Headless binary not found at {HEADLESS_BIN}")
        print("Build it with: ./ailang.x TestCode/browser_main.ailang browser_main.x")
        sys.exit(1)

    tests = get_test_files()

    if args.list:
        print("Available render tests:")
        for t in tests:
            name = t.stem.replace("test_", "")
            has_ref = "REF" if ref_path_for(t).exists() else "   "
            print(f"  [{has_ref}] {name}")
        return

    if not tests:
        print("No test files found in TestCode/render_tests/")
        print("Creating example tests...")
        create_example_tests()
        tests = get_test_files()

    if args.test:
        # Filter to single test
        tests = [t for t in tests if args.test in t.stem]
        if not tests:
            print(f"No test matching '{args.test}'")
            sys.exit(1)

    print(f"Running {len(tests)} render test(s) (threshold: {args.threshold}%)")
    print("-" * 60)

    results = []
    for test_path in tests:
        name, passed, pct = run_test(test_path, args.threshold, args.update)
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name} — {pct:.2f}% match")
        results.append((name, passed, pct))

    success = print_summary(results)
    sys.exit(0 if success else 1)


def create_example_tests():
    """Create initial example test HTML files."""
    TEST_DIR.mkdir(parents=True, exist_ok=True)

    tests = {
        "test_basic_text.html": """\
<html><body>
<h1>Hello World</h1>
<p>This is a paragraph of text.</p>
<p>Second paragraph with <b>bold</b> and <i>italic</i> text.</p>
</body></html>""",

        "test_box_model.html": """\
<html><body>
<div style="background-color: red; width: 200px; padding: 20px; margin: 30px;">
Red box with padding and margin
</div>
<div style="background-color: blue; width: 300px; padding: 10px; margin: 10px;">
Blue box wider
</div>
</body></html>""",

        "test_text_align.html": """\
<html><body>
<div style="text-align: left;">Left aligned text</div>
<div style="text-align: center;">Center aligned text</div>
<div style="text-align: right;">Right aligned text</div>
<center>Center tag text</center>
</body></html>""",

        "test_form_elements.html": """\
<html><body>
<h2>Form Test</h2>
<form action="/search">
<input type="text" placeholder="Search..." size="30">
<input type="submit" value="Go">
<input type="button" value="Cancel">
</form>
<button>Click Me</button>
<textarea></textarea>
<select><option>Option 1</option></select>
</body></html>""",

        "test_links_colors.html": """\
<html><body>
<p>Normal black text</p>
<a href="/page1">Blue link text</a>
<p style="color: red;">Red styled text</p>
<p style="color: green;">Green styled text</p>
</body></html>""",

        "test_headings.html": """\
<html><body>
<h1>Heading 1 (largest)</h1>
<h2>Heading 2</h2>
<h3>Heading 3</h3>
<h4>Heading 4</h4>
<p>Normal paragraph</p>
</body></html>""",

        "test_nested_divs.html": """\
<html><body>
<div style="background-color: #cccccc; padding: 20px;">
  <div style="background-color: #ffffff; padding: 10px; margin: 10px;">
    <p>Nested white box inside gray box</p>
  </div>
  <div style="background-color: #ffcccc; padding: 10px; margin: 10px;">
    <p>Nested pink box inside gray box</p>
  </div>
</div>
</body></html>""",

        "test_display_none.html": """\
<html>
<head><style>
.hidden { display: none; }
</style></head>
<body>
<p>Visible paragraph 1</p>
<p class="hidden">THIS SHOULD NOT APPEAR</p>
<p>Visible paragraph 2</p>
<div hidden>THIS SHOULD NOT APPEAR EITHER</div>
<p>Visible paragraph 3</p>
</body></html>""",

        "test_width_centering.html": """\
<html><body>
<div style="width: 400px; margin: 0 auto; background-color: #eee; padding: 20px;">
  <p style="text-align: center;">Centered block with auto margins</p>
  <p>Left-aligned text inside the centered block</p>
</div>
</body></html>""",

        "test_hr_br.html": """\
<html><body>
<p>Text before HR</p>
<hr>
<p>Text after HR</p>
<p>Line one<br>Line two<br>Line three</p>
</body></html>""",
    }

    for filename, content in tests.items():
        path = TEST_DIR / filename
        with open(path, 'w') as f:
            f.write(content)
        print(f"  Created {filename}")


if __name__ == "__main__":
    main()
