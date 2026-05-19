#!/usr/bin/env python3
"""
acid_runner.py — ACID test runner for Ailang Browser

Renders ACID 1/2/3 tests through the headless browser engine and produces
detailed diagnostic output: crash/success status, render command count,
DOM node count, pixel analysis (blank check, color histogram), and
optional PPM dump for visual inspection.

For ACID2, also renders the reference page and does a pixel-by-pixel
comparison (same approach as wpt_render_runner.py).

Usage:
    python3 tools/acid_runner.py                  # Run all ACID tests
    python3 tools/acid_runner.py --test acid1      # Run only ACID1
    python3 tools/acid_runner.py --test acid2      # Run only ACID2
    python3 tools/acid_runner.py --test acid3      # Run only ACID3
    python3 tools/acid_runner.py --dump-ppm /tmp   # Save PPM output files
    python3 tools/acid_runner.py --verbose         # Show full browser stdout
    python3 tools/acid_runner.py --timeout 30      # Custom timeout (seconds)

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
HEADLESS_BIN = PROJECT_DIR / "browser_ipc.x"
ACID_DIR = PROJECT_DIR / "tests" / "acid"

# Test definitions: (name, test_html, reference_html_or_none)
ACID_TESTS = {
    "acid1": {
        "test": ACID_DIR / "acid1" / "test.html",
        "ref": None,  # GIF reference — visual only, no pixel compare
        "desc": "CSS1 box model, floats, clear, display",
    },
    "acid2": {
        "test": ACID_DIR / "acid2" / "test.html",
        "ref": ACID_DIR / "acid2" / "reference.html",
        "desc": "CSS2.1 box model, positioning, PNG, data URIs, fixed positioning",
    },
    "acid3": {
        "test": ACID_DIR / "acid3" / "test.html",
        "ref": None,  # JS-driven scoring test — needs JS engine
        "desc": "DOM/CSS/JS integration (100-point score)",
    },
}


def render_html(html_path, output_ppm, timeout=15):
    """Render an HTML file through the headless browser.
    Returns (success, stdout, stderr, returncode, cmd_count, dom_nodes)."""
    # Remove old output
    try:
        os.unlink(output_ppm)
    except FileNotFoundError:
        pass

    stdin_data = f"{html_path}\n{output_ppm}\n".encode()

    try:
        result = subprocess.run(
            [str(HEADLESS_BIN), "--headless"],
            input=stdin_data,
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

    cmd_count = 0
    dom_nodes = 0
    for line in stdout.split("\n"):
        if "Render commands:" in line:
            try:
                cmd_count = int(line.split(":")[-1].strip())
            except ValueError:
                pass
        if "DOM nodes:" in line:
            try:
                dom_nodes = int(line.split(":")[-1].strip())
            except ValueError:
                pass

    success = result.returncode == 0 and os.path.exists(output_ppm)
    return success, stdout, stderr, result.returncode, cmd_count, dom_nodes


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

    # Sample up to 50k pixels for speed
    sample_step = max(1, total_pixels // 50000)
    sampled = 0
    for i in range(0, len(data) - 2, sample_step * 3):
        r, g, b = data[i], data[i + 1], data[i + 2]
        sampled += 1
        if (r, g, b) != (255, 255, 255):
            non_white += 1
        if (r, g, b) != (0, 0, 0) and (r, g, b) != (255, 255, 255):
            non_white_non_black += 1
        # Bucket colors for histogram (quantize to 32 levels)
        rq, gq, bq = r >> 3, g >> 3, b >> 3
        color_counts[(rq, gq, bq)] += 1

    # Top colors (de-quantize for display)
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


def compare_ppms(ref_ppm, test_ppm):
    """Compare two PPM files pixel-by-pixel. Returns match percentage."""
    ref = read_ppm(ref_ppm)
    test = read_ppm(test_ppm)
    if ref is None or test is None:
        return 0.0
    w1, h1, d1 = ref
    w2, h2, d2 = test
    if (w1, h1) != (w2, h2):
        return 0.0
    total = w1 * h1
    diff = 0
    min_len = min(len(d1), len(d2))
    for i in range(0, min_len - 2, 3):
        if d1[i : i + 3] != d2[i : i + 3]:
            diff += 1
    return ((total - diff) / total) * 100.0


def run_acid_test(name, config, dump_dir=None, timeout=15, verbose=False):
    """Run a single ACID test and print detailed results."""
    test_html = config["test"]
    ref_html = config["ref"]
    desc = config["desc"]

    print(f"\n{'='*70}")
    print(f"  ACID TEST: {name.upper()}")
    print(f"  {desc}")
    print(f"  File: {test_html}")
    print(f"{'='*70}")

    if not test_html.exists():
        print(f"  ERROR: Test file not found: {test_html}")
        return "MISSING"

    # Render the test
    output_ppm = f"/tmp/acid_{name}_test.ppm"
    success, stdout, stderr, rc, cmds, nodes = render_html(
        test_html, output_ppm, timeout
    )

    # Status — strict pass/fail: only >=99.9% ref match counts as PASS
    if rc == -1 and "TIMEOUT" in stderr:
        status = "TIMEOUT"
    elif not success:
        status = "CRASH"
    else:
        status = "FAIL"  # default until proven PASS via reference match

    print(f"\n  Status:          {status}")
    print(f"  Exit code:       {rc}")
    print(f"  DOM nodes:       {nodes}")
    print(f"  Render commands: {cmds}")

    if verbose and stdout.strip():
        print(f"\n  --- Browser stdout ---")
        for line in stdout.strip().split("\n"):
            print(f"    {line}")

    if verbose and stderr.strip():
        print(f"\n  --- Browser stderr ---")
        for line in stderr.strip().split("\n")[:30]:
            print(f"    {line}")

    # Analyze output image
    if success:
        ppm_info = analyze_ppm(output_ppm)
        if ppm_info["exists"]:
            print(f"\n  PPM Output:      {ppm_info['width']}x{ppm_info['height']}")
            print(
                f"  Non-white:       {ppm_info['non_white_pct']:.1f}% ({ppm_info['non_white']}/{ppm_info['sampled']} sampled pixels)"
            )
            print(f"  Has color:       {ppm_info['has_color']}")
            print(f"  Top colors:")
            for c in ppm_info["top_colors"][:8]:
                print(f"    {c}")
        else:
            print(f"  PPM Output:      INVALID/MISSING")

        # Save PPM if requested
        if dump_dir:
            dump_path = os.path.join(dump_dir, f"acid_{name}.ppm")
            try:
                shutil.copy2(output_ppm, dump_path)
                print(f"\n  PPM saved to:    {dump_path}")
            except Exception as e:
                print(f"\n  PPM save failed: {e}")

    # Reference comparison (ACID2)
    if success and ref_html and ref_html.exists():
        ref_ppm = f"/tmp/acid_{name}_ref.ppm"
        ref_success, _, _, ref_rc, _, _ = render_html(ref_html, ref_ppm, timeout)
        if ref_success:
            match_pct = compare_ppms(ref_ppm, output_ppm)
            print(f"\n  Reference match: {match_pct:.2f}%")
            if match_pct >= 99.9:
                status = "PASS"
            else:
                status = "FAIL"
            print(f"  Verdict:         {status} ({match_pct:.2f}% — need 99.9%)")

            if dump_dir:
                ref_dump = os.path.join(dump_dir, f"acid_{name}_ref.ppm")
                try:
                    shutil.copy2(ref_ppm, ref_dump)
                    print(f"  Ref PPM saved:   {ref_dump}")
                except Exception:
                    pass
        else:
            print(f"\n  Reference render failed (exit {ref_rc})")

    print(f"\n  RESULT: {name.upper()} => {status}")
    print(f"{'='*70}")
    return status


def main():
    parser = argparse.ArgumentParser(description="ACID Test Runner for Ailang Browser")
    parser.add_argument(
        "--test",
        choices=["acid1", "acid2", "acid3"],
        help="Run specific ACID test (default: all)",
    )
    parser.add_argument(
        "--dump-ppm", metavar="DIR", help="Save PPM output to this directory"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show full browser output"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="Timeout per render in seconds (default: 15)",
    )
    args = parser.parse_args()

    if not HEADLESS_BIN.exists():
        print(f"ERROR: Headless browser not found at {HEADLESS_BIN}")
        print(f"Build it first: ./build.sh")
        sys.exit(1)

    if args.dump_ppm:
        os.makedirs(args.dump_ppm, exist_ok=True)

    tests_to_run = (
        [args.test] if args.test else ["acid1", "acid2", "acid3"]
    )

    print(f"\nAilang Browser — ACID Test Suite")
    print(f"Headless binary: {HEADLESS_BIN}")
    print(f"Tests to run:    {', '.join(t.upper() for t in tests_to_run)}")

    results = {}
    for name in tests_to_run:
        config = ACID_TESTS[name]
        results[name] = run_acid_test(
            name, config, args.dump_ppm, args.timeout, args.verbose
        )

    # Summary
    print(f"\n{'='*70}")
    print(f"  ACID TEST SUMMARY")
    print(f"{'='*70}")
    pass_count = 0
    fail_count = 0
    for name, status in results.items():
        icon = "[PASS]" if status == "PASS" else "[FAIL]"
        if status == "PASS":
            pass_count += 1
        else:
            fail_count += 1
        print(f"  {icon} {name.upper()}")
    total = pass_count + fail_count
    print(f"\n  Score: {pass_count}/{total}")
    print(f"{'='*70}\n")

    # Exit code: 0 only if all pass
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
