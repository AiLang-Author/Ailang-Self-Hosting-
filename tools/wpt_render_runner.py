#!/usr/bin/env python3
"""
wpt_render_runner.py — WPT compliance render test runner for Ailang Browser

Renders WPT test HTML files through the headless browser engine and checks:
  1. Does it crash? (exit code != 0)
  2. Does it produce any render commands? (parse stdout)
  3. Does it produce a valid PPM output? (non-blank image)
  4. Ref-test comparison (if -ref.html exists, render both and compare)

Usage:
    python3 tools/wpt_render_runner.py                         # Run default CSS2 suite
    python3 tools/wpt_render_runner.py --suite css-text        # Run css-text suite
    python3 tools/wpt_render_runner.py --dir /home/bob/wpt/html/rendering
    python3 tools/wpt_render_runner.py --file /path/to/test.html
    python3 tools/wpt_render_runner.py --all                   # Run all known suites
    python3 tools/wpt_render_runner.py --dump-ppm /tmp/out     # Save PPMs for inspection

Suites (from ~/wpt/):
    css2-box, css2-backgrounds, css2-colors, css2-fonts, css2-floats,
    css-text, css-box, html-rendering

Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
"""

import os
import sys
import subprocess
import argparse
import json
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
HEADLESS_BIN = PROJECT_DIR / "browser_main.x"
INPUT_FILE = Path("/tmp/render_test.html")
OUTPUT_FILE = Path("/tmp/render_out.ppm")
WPT_DIR = Path("/home/bob/wpt")

# Known test suites with WPT paths
SUITES = {
    "css2-box":         WPT_DIR / "css" / "CSS2" / "box",
    "css2-box-display": WPT_DIR / "css" / "CSS2" / "box-display",
    "css2-backgrounds": WPT_DIR / "css" / "CSS2" / "backgrounds",
    "css2-borders":     WPT_DIR / "css" / "CSS2" / "borders",
    "css2-colors":      WPT_DIR / "css" / "CSS2" / "colors",
    "css2-fonts":       WPT_DIR / "css" / "CSS2" / "fonts",
    "css2-floats":      WPT_DIR / "css" / "CSS2" / "floats",
    "css2-cascade":     WPT_DIR / "css" / "CSS2" / "cascade",
    "css-text":         WPT_DIR / "css" / "css-text",
    "css-box":          WPT_DIR / "css" / "css-box",
    "css-color":        WPT_DIR / "css" / "css-color",
    "css-display":      WPT_DIR / "css" / "css-display",
    "html-rendering":   WPT_DIR / "html" / "rendering",
    "render-tests":     PROJECT_DIR / "TestCode" / "render_tests",
}

# Default suites to run when --all is not specified
DEFAULT_SUITES = ["css2-box", "css2-colors", "css2-backgrounds", "render-tests"]


def find_test_files(directory, max_files=200):
    """Find .html and .xht test files, excluding reference/support files."""
    tests = []
    if not directory.exists():
        return tests

    for ext in ("*.html", "*.xht"):
        for f in sorted(directory.rglob(ext)):
            # Skip reference images, support files, and nested refs
            rel = str(f.relative_to(directory))
            skip = False
            for part in ("reference", "support", "ref_", "-ref."):
                if part in rel.lower():
                    skip = True
                    break
            if f.stem.endswith("-ref") or f.stem.endswith("_ref"):
                skip = True
            if skip:
                continue
            tests.append(f)
            if len(tests) >= max_files:
                break
        if len(tests) >= max_files:
            break

    return tests


def render_html(html_path, timeout=10):
    """Render HTML through headless browser. Returns (success, stdout, cmd_count, dom_nodes)."""
    # Copy test HTML to input location
    try:
        with open(html_path, 'rb') as f:
            html_data = f.read()
        with open(INPUT_FILE, 'wb') as f:
            f.write(html_data)
    except Exception as e:
        return False, str(e), 0, 0

    # Remove old output
    OUTPUT_FILE.unlink(missing_ok=True)

    try:
        result = subprocess.run(
            [str(HEADLESS_BIN)],
            capture_output=True,
            timeout=timeout,
            cwd=str(PROJECT_DIR)
        )
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", 0, 0
    except Exception as e:
        return False, str(e), 0, 0

    stdout = result.stdout.decode('utf-8', errors='replace')

    # Parse render stats from stdout
    cmd_count = 0
    dom_nodes = 0
    for line in stdout.split('\n'):
        if 'Render commands:' in line:
            try:
                cmd_count = int(line.split(':')[-1].strip())
            except ValueError:
                pass
        if 'DOM nodes:' in line:
            try:
                dom_nodes = int(line.split(':')[-1].strip())
            except ValueError:
                pass

    success = result.returncode == 0 and OUTPUT_FILE.exists()
    return success, stdout, cmd_count, dom_nodes


def check_ppm_not_blank(ppm_path):
    """Check if PPM has any non-white pixels (i.e., something was rendered)."""
    try:
        with open(ppm_path, 'rb') as f:
            magic = f.readline().strip()
            if magic != b'P6':
                return False
            line = f.readline()
            while line.startswith(b'#'):
                line = f.readline()
            w, h = map(int, line.split())
            f.readline()  # maxval
            data = f.read()

        # Sample pixels at regular intervals to check for non-white content
        total_pixels = w * h
        sample_size = min(10000, total_pixels)
        step = max(1, total_pixels // sample_size)
        non_white = 0
        for i in range(0, len(data) - 2, step * 3):
            r, g, b = data[i], data[i+1], data[i+2]
            if (r, g, b) != (255, 255, 255):
                non_white += 1

        return non_white > 0
    except Exception:
        return False


def compare_ppms(ref_ppm, test_ppm):
    """Compare two PPM files, return match percentage."""
    try:
        with open(ref_ppm, 'rb') as f:
            magic1 = f.readline().strip()
            line1 = f.readline()
            while line1.startswith(b'#'):
                line1 = f.readline()
            w1, h1 = map(int, line1.split())
            f.readline()
            data1 = f.read()

        with open(test_ppm, 'rb') as f:
            magic2 = f.readline().strip()
            line2 = f.readline()
            while line2.startswith(b'#'):
                line2 = f.readline()
            w2, h2 = map(int, line2.split())
            f.readline()
            data2 = f.read()

        if (w1, h1) != (w2, h2):
            return 0.0

        total = w1 * h1
        diff_count = 0
        min_len = min(len(data1), len(data2))
        for i in range(0, min_len - 2, 3):
            if data1[i:i+3] != data2[i:i+3]:
                diff_count += 1

        return ((total - diff_count) / total) * 100.0
    except Exception:
        return 0.0


def run_single_test(test_path, dump_dir=None):
    """Run a single WPT test. Returns (status, details)."""
    success, stdout, cmd_count, dom_nodes = render_html(test_path)

    if not success:
        if "TIMEOUT" in stdout:
            return "TIMEOUT", {"cmd": 0, "dom": 0}
        return "CRASH", {"cmd": 0, "dom": 0}

    # Check for parse success
    if dom_nodes == 0:
        return "PARSE_FAIL", {"cmd": cmd_count, "dom": dom_nodes}

    has_content = check_ppm_not_blank(OUTPUT_FILE)

    # Save PPM if dump dir specified
    if dump_dir:
        dump_name = test_path.stem + ".ppm"
        dump_path = Path(dump_dir) / dump_name
        try:
            import shutil
            shutil.copy2(OUTPUT_FILE, dump_path)
        except Exception:
            pass

    # Check for ref-test (WPT pattern: foo.html + foo-ref.html)
    ref_path = test_path.parent / (test_path.stem + "-ref" + test_path.suffix)
    if not ref_path.exists():
        ref_path = test_path.parent / "reference" / (test_path.stem + "-ref" + test_path.suffix)

    if ref_path.exists():
        # Render reference too
        ref_success, _, _, _ = render_html(ref_path)
        if ref_success and OUTPUT_FILE.exists():
            import shutil
            ref_ppm = Path("/tmp/render_ref.ppm")
            shutil.copy(OUTPUT_FILE, ref_ppm)

            # Re-render test
            render_html(test_path)

            match_pct = compare_ppms(ref_ppm, OUTPUT_FILE)
            if match_pct >= 95.0:
                return "PASS", {"cmd": cmd_count, "dom": dom_nodes, "match": f"{match_pct:.1f}%"}
            elif match_pct >= 50.0:
                return "PARTIAL", {"cmd": cmd_count, "dom": dom_nodes, "match": f"{match_pct:.1f}%"}
            else:
                return "FAIL", {"cmd": cmd_count, "dom": dom_nodes, "match": f"{match_pct:.1f}%"}

    # No ref-test: classify by render output
    if cmd_count > 0 and has_content:
        return "RENDERED", {"cmd": cmd_count, "dom": dom_nodes}
    elif cmd_count > 0:
        return "CMDS_ONLY", {"cmd": cmd_count, "dom": dom_nodes}
    elif dom_nodes > 0:
        return "PARSED", {"cmd": 0, "dom": dom_nodes}
    else:
        return "EMPTY", {"cmd": 0, "dom": 0}


def run_suite(name, directory, max_files=200, dump_dir=None):
    """Run all tests in a suite directory."""
    tests = find_test_files(directory, max_files)
    if not tests:
        print(f"  No test files found in {directory}")
        return {}

    results = {
        "PASS": 0, "PARTIAL": 0, "RENDERED": 0, "CMDS_ONLY": 0,
        "PARSED": 0, "EMPTY": 0, "PARSE_FAIL": 0, "CRASH": 0, "TIMEOUT": 0, "FAIL": 0
    }
    total = len(tests)
    failures = []

    print(f"\n{'='*70}")
    print(f"  Suite: {name} ({total} tests)")
    print(f"  Dir:   {directory}")
    print(f"{'='*70}")

    for i, test_path in enumerate(tests):
        rel = test_path.relative_to(directory) if directory != test_path.parent else test_path.name
        status, details = run_single_test(test_path, dump_dir)
        results[status] = results.get(status, 0) + 1

        # Print progress every 10 tests or on failure/partial
        if status in ("CRASH", "TIMEOUT", "FAIL"):
            failures.append((rel, status, details))
            print(f"  [{i+1:3d}/{total}] {status:11s} {rel}")
        elif status == "PARTIAL":
            match_str = details.get("match", "?") if details else "?"
            print(f"  [{i+1:3d}/{total}] PARTIAL      {rel}  ({match_str})")
        elif (i + 1) % 20 == 0 or i == total - 1:
            # Progress line
            done = i + 1
            good = results["PASS"] + results["RENDERED"] + results["PARTIAL"]
            print(f"  [{done:3d}/{total}] progress: {good} good, "
                  f"{results['CRASH']} crash, {results['TIMEOUT']} timeout")

    # Summary
    good = results["PASS"] + results["RENDERED"] + results["PARTIAL"]
    print(f"\n  Results for {name}:")
    print(f"    PASS (ref match >=95%):  {results['PASS']}")
    print(f"    PARTIAL (ref 50-95%):    {results['PARTIAL']}")
    print(f"    RENDERED (pixels drawn): {results['RENDERED']}")
    print(f"    CMDS_ONLY (no pixels):   {results['CMDS_ONLY']}")
    print(f"    PARSED (DOM only):       {results['PARSED']}")
    print(f"    EMPTY (nothing):         {results['EMPTY']}")
    print(f"    PARSE_FAIL:              {results['PARSE_FAIL']}")
    print(f"    CRASH:                   {results['CRASH']}")
    print(f"    TIMEOUT:                 {results['TIMEOUT']}")
    print(f"    FAIL (ref match <50%):   {results['FAIL']}")
    print(f"    ---")
    print(f"    Total: {total}, Good (pass+render+partial): {good} ({good*100//max(total,1)}%)")

    if failures:
        print(f"\n  Failures:")
        for rel, status, details in failures[:20]:
            print(f"    {status}: {rel}")

    return results


def main():
    parser = argparse.ArgumentParser(description="WPT render compliance test runner")
    parser.add_argument("--suite", type=str, help="Run named suite (e.g. css2-box)")
    parser.add_argument("--dir", type=str, help="Run all tests in a directory")
    parser.add_argument("--file", type=str, help="Run single test file")
    parser.add_argument("--all", action="store_true", help="Run all known suites")
    parser.add_argument("--max", type=int, default=200, help="Max tests per suite (default 200)")
    parser.add_argument("--dump-ppm", type=str, help="Save PPM output to this directory")
    parser.add_argument("--list-suites", action="store_true", help="List available suites")
    parser.add_argument("--timeout", type=int, default=10, help="Per-test timeout (default 10s)")
    args = parser.parse_args()

    if not HEADLESS_BIN.exists():
        print(f"ERROR: {HEADLESS_BIN} not found")
        print("Build: ./ailang.x TestCode/browser_main.ailang browser_main.x")
        sys.exit(1)

    if args.list_suites:
        print("Available suites:")
        for name, path in sorted(SUITES.items()):
            exists = "OK" if path.exists() else "MISSING"
            count = len(find_test_files(path, 9999)) if path.exists() else 0
            print(f"  {name:25s} [{exists:7s}] {count:5d} tests  {path}")
        return

    if args.dump_ppm:
        os.makedirs(args.dump_ppm, exist_ok=True)

    if args.file:
        test_path = Path(args.file)
        if not test_path.exists():
            print(f"ERROR: {test_path} not found")
            sys.exit(1)
        status, details = run_single_test(test_path, args.dump_ppm)
        print(f"  {status}: {test_path.name}  {details}")
        return

    all_results = {}
    start = time.time()

    if args.suite:
        if args.suite in SUITES:
            all_results[args.suite] = run_suite(args.suite, SUITES[args.suite], args.max, args.dump_ppm)
        else:
            # Try as directory path
            d = Path(args.suite)
            if d.exists():
                all_results[args.suite] = run_suite(args.suite, d, args.max, args.dump_ppm)
            else:
                print(f"Unknown suite: {args.suite}")
                print(f"Available: {', '.join(sorted(SUITES.keys()))}")
                sys.exit(1)
    elif args.dir:
        d = Path(args.dir)
        all_results["custom"] = run_suite("custom", d, args.max, args.dump_ppm)
    elif args.all:
        for name, path in sorted(SUITES.items()):
            if path.exists():
                all_results[name] = run_suite(name, path, args.max, args.dump_ppm)
    else:
        # Default: run default suites
        for name in DEFAULT_SUITES:
            if name in SUITES and SUITES[name].exists():
                all_results[name] = run_suite(name, SUITES[name], args.max, args.dump_ppm)

    elapsed = time.time() - start

    # Grand summary
    if len(all_results) > 1:
        print(f"\n{'='*70}")
        print(f"  GRAND SUMMARY")
        print(f"{'='*70}")
        grand_total = 0
        grand_good = 0
        grand_crash = 0
        for name, results in sorted(all_results.items()):
            total = sum(results.values())
            good = results.get("PASS", 0) + results.get("RENDERED", 0) + results.get("PARTIAL", 0)
            crash = results.get("CRASH", 0) + results.get("TIMEOUT", 0)
            grand_total += total
            grand_good += good
            grand_crash += crash
            pct = good * 100 // max(total, 1)
            print(f"  {name:25s}  {good:4d}/{total:<4d} good ({pct}%), {crash} crash")

        pct = grand_good * 100 // max(grand_total, 1)
        print(f"  {'TOTAL':25s}  {grand_good:4d}/{grand_total:<4d} good ({pct}%), {grand_crash} crash")
        print(f"  Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
