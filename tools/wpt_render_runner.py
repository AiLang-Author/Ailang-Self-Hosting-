#!/usr/bin/env python3
"""
wpt_render_runner.py — WPT compliance render test runner for Ailang Browser

Renders WPT test HTML files through the headless browser engine and checks:
  1. Does it crash? (exit code != 0)
  2. Does it produce any render commands? (parse stdout)
  3. Does it produce a valid PPM output? (non-blank image)
  4. Ref-test comparison (if -ref.html exists, render both and compare)

Parallel execution: uses 8 workers, each with unique temp file paths piped
via stdin to browser_main.x (which reads input/output paths from stdin).

Usage:
    python3 tools/wpt_render_runner.py                         # Run default CSS2 suite
    python3 tools/wpt_render_runner.py --suite css-text        # Run css-text suite
    python3 tools/wpt_render_runner.py --dir /home/bob/wpt/html/rendering
    python3 tools/wpt_render_runner.py --file /path/to/test.html
    python3 tools/wpt_render_runner.py --all                   # Run all known suites
    python3 tools/wpt_render_runner.py --full                  # Run FULL WPT tree
    python3 tools/wpt_render_runner.py --dump-ppm /tmp/out     # Save PPMs for inspection
    python3 tools/wpt_render_runner.py -j 4                    # Use 4 workers (default 8)

Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
"""

import os
import sys
import subprocess
import argparse
import time
import shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
HEADLESS_BIN = PROJECT_DIR / "browser_main.x"
WPT_DIR = Path("/home/bob/wpt")
SHIM_PATH = SCRIPT_DIR / "testharness_shim.js"

# Cached shim content (loaded once per process)
_shim_cache = None

def _get_shim_content():
    """Load and cache the testharness shim JS content."""
    global _shim_cache
    if _shim_cache is None:
        try:
            with open(SHIM_PATH, 'r') as f:
                _shim_cache = f.read()
        except FileNotFoundError:
            _shim_cache = ""
    return _shim_cache


import re

# Patterns to match testharness.js and testharnessreport.js script tags
_RE_HARNESS = re.compile(
    rb'<script\s+src\s*=\s*["\']?/resources/testharness\.js["\']?\s*>\s*</script>',
    re.IGNORECASE
)
_RE_REPORT = re.compile(
    rb'<script\s+src\s*=\s*["\']?/resources/testharnessreport\.js["\']?\s*>\s*</script>',
    re.IGNORECASE
)


def _inject_shim(html_data):
    """Replace external testharness.js/testharnessreport.js with inline shim.
    Merges shim into the next inline <script> block so everything runs in one
    compilation unit (avoids cross-script global persistence issues).
    Returns modified html_data (bytes)."""
    if b'testharness.js' not in html_data:
        return html_data
    shim = _get_shim_content()
    if not shim:
        return html_data
    shim_bytes = shim.encode('utf-8')
    # Remove testharness.js script tag
    result = _RE_HARNESS.sub(b'', html_data)
    # Remove testharnessreport.js script tag
    result = _RE_REPORT.sub(b'', result)
    # Also remove other common external script refs that won't resolve
    result = re.sub(rb'<script\s+src\s*=\s*["\']?/resources/[^"\'>\s]+["\']?\s*>\s*</script>', b'', result, flags=re.IGNORECASE)
    # Find the first inline <script> tag (no src attribute) and prepend shim
    m = re.search(rb'<script\s*>', result, re.IGNORECASE)
    if m:
        insert_pos = m.end()
        result = result[:insert_pos] + b'\n' + shim_bytes + b'\n' + result[insert_pos:]
    else:
        # No inline script found — wrap the shim in its own script tag at end
        result = result + b'<script>\n' + shim_bytes + b'\n</script>'
    return result

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
    "css2-floats-clear": WPT_DIR / "css" / "CSS2" / "floats-clear",
    "css-position":     WPT_DIR / "css" / "css-position",
    "css2-positioning": WPT_DIR / "css" / "CSS2" / "positioning",
    "css2-abspos":      WPT_DIR / "css" / "CSS2" / "abspos",
    "css2-zindex":      WPT_DIR / "css" / "CSS2" / "zindex",
    "css2-linebox":     WPT_DIR / "css" / "CSS2" / "linebox",
    "css2-visuren":     WPT_DIR / "css" / "CSS2" / "visuren",
    "render-tests":     PROJECT_DIR / "TestCode" / "render_tests",
}

DEFAULT_SUITES = ["css2-box", "css2-colors", "css2-backgrounds", "render-tests"]


def find_test_files(directory, max_files=0):
    """Find .html and .xht test files, excluding reference/support files."""
    tests = []
    if not directory.exists():
        return tests

    for ext in ("*.html", "*.xht"):
        for f in sorted(directory.rglob(ext)):
            rel = str(f.relative_to(directory))
            skip = False
            for part in ("reference", "support", "ref_", "-ref."):
                if part in rel.lower():
                    skip = True
                    break
            if f.stem.endswith("-ref") or f.stem.endswith("_ref"):
                skip = True
            if "/resources/" in rel or rel.startswith("resources/"):
                skip = True
            if skip:
                continue
            # Skip empty files (0 bytes crash the parser)
            try:
                if f.stat().st_size == 0:
                    continue
            except OSError:
                continue
            tests.append(f)
            if max_files > 0 and len(tests) >= max_files:
                break
        if max_files > 0 and len(tests) >= max_files:
            break

    return tests


def render_html(html_path, input_file, output_file, timeout=10):
    """Render HTML through headless browser with per-worker temp files.
    Pipes input/output paths via stdin to browser_main.x."""
    try:
        with open(html_path, 'rb') as f:
            html_data = f.read()
        # Inject testharness shim if test uses testharness.js
        html_data = _inject_shim(html_data)
        with open(input_file, 'wb') as f:
            f.write(html_data)
    except Exception as e:
        return False, str(e), 0, 0

    # Remove old output
    try:
        os.unlink(output_file)
    except FileNotFoundError:
        pass

    # Pipe input/output paths via stdin
    stdin_data = f"{input_file}\n{output_file}\n".encode()

    try:
        result = subprocess.run(
            [str(HEADLESS_BIN)],
            input=stdin_data,
            capture_output=True,
            timeout=timeout,
            cwd=str(PROJECT_DIR)
        )
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", 0, 0
    except Exception as e:
        return False, str(e), 0, 0

    stdout = result.stdout.decode('utf-8', errors='replace')

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

    success = result.returncode == 0 and os.path.exists(output_file)
    return success, stdout, cmd_count, dom_nodes


def check_ppm_not_blank(ppm_path):
    """Check if PPM has any non-white pixels."""
    try:
        with open(ppm_path, 'rb') as f:
            magic = f.readline().strip()
            if magic != b'P6':
                return False
            line = f.readline()
            while line.startswith(b'#'):
                line = f.readline()
            w, h = map(int, line.split())
            f.readline()
            data = f.read()

        total_pixels = w * h
        sample_size = min(10000, total_pixels)
        step = max(1, total_pixels // sample_size)
        for i in range(0, len(data) - 2, step * 3):
            r, g, b = data[i], data[i+1], data[i+2]
            if (r, g, b) != (255, 255, 255):
                return True
        return False
    except Exception:
        return False


def compare_ppms(ref_ppm, test_ppm):
    """Compare two PPM files, return match percentage."""
    try:
        with open(ref_ppm, 'rb') as f:
            f.readline()  # magic
            line1 = f.readline()
            while line1.startswith(b'#'):
                line1 = f.readline()
            w1, h1 = map(int, line1.split())
            f.readline()
            data1 = f.read()

        with open(test_ppm, 'rb') as f:
            f.readline()  # magic
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


# ── Worker function (runs in child process) ──────────────────────────────────

def _worker_run_test(args_tuple):
    """Run a single test in a worker process. Must be top-level for pickling.
    args_tuple = (test_path_str, dump_dir, timeout)
    Returns (test_path_str, status, details)"""
    test_path_str, dump_dir, timeout = args_tuple
    test_path = Path(test_path_str)

    # Per-process temp files (PID is unique per concurrent process)
    pid = os.getpid()
    wdir = f"/tmp/wpt_w{pid}"
    os.makedirs(wdir, exist_ok=True)
    input_file = f"{wdir}/render_test.html"
    output_file = f"{wdir}/render_out.ppm"
    ref_ppm_file = f"{wdir}/render_ref.ppm"

    success, stdout, cmd_count, dom_nodes = render_html(test_path, input_file, output_file, timeout)

    if not success:
        if "TIMEOUT" in stdout:
            return (test_path_str, "TIMEOUT", {"cmd": 0, "dom": 0})
        return (test_path_str, "CRASH", {"cmd": 0, "dom": 0})

    if dom_nodes == 0:
        return (test_path_str, "PARSE_FAIL", {"cmd": cmd_count, "dom": dom_nodes})

    has_content = check_ppm_not_blank(output_file)

    if dump_dir:
        dump_name = test_path.stem + ".ppm"
        dump_path = os.path.join(dump_dir, dump_name)
        try:
            shutil.copy2(output_file, dump_path)
        except Exception:
            pass

    # Check for ref-test
    ref_path = test_path.parent / (test_path.stem + "-ref" + test_path.suffix)
    if not ref_path.exists():
        ref_path = test_path.parent / "reference" / (test_path.stem + "-ref" + test_path.suffix)

    if ref_path.exists():
        ref_success, _, _, _ = render_html(ref_path, input_file, output_file, timeout)
        if ref_success and os.path.exists(output_file):
            shutil.copy(output_file, ref_ppm_file)
            # Re-render the test
            render_html(test_path, input_file, output_file, timeout)
            match_pct = compare_ppms(ref_ppm_file, output_file)
            if match_pct >= 95.0:
                return (test_path_str, "PASS", {"cmd": cmd_count, "dom": dom_nodes, "match": f"{match_pct:.1f}%"})
            elif match_pct >= 50.0:
                return (test_path_str, "PARTIAL", {"cmd": cmd_count, "dom": dom_nodes, "match": f"{match_pct:.1f}%"})
            else:
                return (test_path_str, "FAIL", {"cmd": cmd_count, "dom": dom_nodes, "match": f"{match_pct:.1f}%"})

    # No ref-test
    if cmd_count > 0 and has_content:
        return (test_path_str, "RENDERED", {"cmd": cmd_count, "dom": dom_nodes})
    elif cmd_count > 0:
        return (test_path_str, "CMDS_ONLY", {"cmd": cmd_count, "dom": dom_nodes})
    elif dom_nodes > 0:
        return (test_path_str, "PARSED", {"cmd": 0, "dom": dom_nodes})
    else:
        return (test_path_str, "EMPTY", {"cmd": 0, "dom": 0})


# ── Single-threaded fallback (for --file) ────────────────────────────────────

def run_single_test(test_path, dump_dir=None, timeout=10):
    """Run a single test (backwards compat)."""
    result = _worker_run_test((str(test_path), dump_dir, timeout))
    return result[1], result[2]


# ── Suite runner with parallel workers ────────────────────────────────────────

def run_suite(name, directory, max_files=0, dump_dir=None, num_workers=8, timeout=10):
    """Run all tests in a suite directory using parallel workers."""
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
    print(f"  Suite: {name} ({total} tests, {num_workers} workers)")
    print(f"  Dir:   {directory}")
    print(f"{'='*70}")

    # Build work items (worker dirs created on-demand per process PID)
    work = [(str(test_path), dump_dir, timeout) for test_path in tests]

    # Progress tracking
    step = 500 if total > 5000 else (100 if total > 500 else 20)
    done = 0
    suite_start = time.time()

    with ProcessPoolExecutor(max_workers=num_workers) as pool:
        futures = {pool.submit(_worker_run_test, w): w for w in work}
        for future in as_completed(futures):
            test_path_str, status, details = future.result()
            test_path = Path(test_path_str)
            results[status] = results.get(status, 0) + 1
            done += 1

            if status in ("CRASH", "TIMEOUT", "FAIL"):
                try:
                    rel = test_path.relative_to(directory)
                except ValueError:
                    rel = test_path.name
                failures.append((rel, status, details))
                print(f"  [{done:5d}/{total}] {status:11s} {rel}")
            elif status == "PARTIAL":
                try:
                    rel = test_path.relative_to(directory)
                except ValueError:
                    rel = test_path.name
                match_str = details.get("match", "?") if details else "?"
                print(f"  [{done:5d}/{total}] PARTIAL      {rel}  ({match_str})")
            else:
                if done % step == 0 or done == total:
                    good = results["PASS"] + results["RENDERED"] + results["PARTIAL"]
                    elapsed = time.time() - suite_start
                    rate = done / elapsed if elapsed > 0 else 0
                    print(f"  [{done:5d}/{total}] progress: {good} good, "
                          f"{results['CRASH']} crash, {results['TIMEOUT']} timeout  "
                          f"({rate:.1f} tests/s)")

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
    parser.add_argument("--full", action="store_true", help="Run FULL WPT tree (~78k tests)")
    parser.add_argument("--max", type=int, default=0, help="Max tests per suite (default 0=unlimited)")
    parser.add_argument("--dump-ppm", type=str, help="Save PPM output to this directory")
    parser.add_argument("--list-suites", action="store_true", help="List available suites")
    parser.add_argument("--timeout", type=int, default=10, help="Per-test timeout (default 10s)")
    parser.add_argument("-j", "--jobs", type=int, default=8, help="Number of parallel workers (default 8)")
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
        status, details = run_single_test(test_path, args.dump_ppm, args.timeout)
        print(f"  {status}: {test_path.name}  {details}")
        return

    num_workers = args.jobs
    all_results = {}
    start = time.time()

    if args.suite:
        if args.suite in SUITES:
            all_results[args.suite] = run_suite(args.suite, SUITES[args.suite], args.max,
                                                 args.dump_ppm, num_workers, args.timeout)
        else:
            d = Path(args.suite)
            if d.exists():
                all_results[args.suite] = run_suite(args.suite, d, args.max,
                                                     args.dump_ppm, num_workers, args.timeout)
            else:
                print(f"Unknown suite: {args.suite}")
                print(f"Available: {', '.join(sorted(SUITES.keys()))}")
                sys.exit(1)
    elif args.dir:
        d = Path(args.dir)
        all_results["custom"] = run_suite("custom", d, args.max,
                                           args.dump_ppm, num_workers, args.timeout)
    elif args.full:
        full_dirs = []
        css_dir = WPT_DIR / "css"
        if css_dir.exists():
            for d in sorted(css_dir.iterdir()):
                if d.is_dir() and d.name not in ("tools", "work-in-progress"):
                    if d.name == "CSS2":
                        for sd in sorted(d.iterdir()):
                            if sd.is_dir() and sd.name not in ("reference", "support", "resources"):
                                full_dirs.append((f"css2/{sd.name}", sd))
                    else:
                        full_dirs.append((f"css/{d.name}", d))
        html_dir = WPT_DIR / "html"
        if html_dir.exists():
            for d in sorted(html_dir.iterdir()):
                if d.is_dir() and d.name not in ("tools", "resources"):
                    full_dirs.append((f"html/{d.name}", d))
        for top in ["dom", "fetch", "xhr", "uievents", "domparsing", "svg",
                     "encoding", "url", "selection", "trusted-types",
                     "2dcontext", "quirks", "acid"]:
            td = WPT_DIR / top
            if td.exists():
                full_dirs.append((top, td))

        print(f"  Full WPT scan: {len(full_dirs)} directories, {num_workers} workers")
        for name, path in full_dirs:
            r = run_suite(name, path, args.max, args.dump_ppm, num_workers, args.timeout)
            if r:
                all_results[name] = r
    elif args.all:
        for name, path in sorted(SUITES.items()):
            if path.exists():
                all_results[name] = run_suite(name, path, args.max,
                                               args.dump_ppm, num_workers, args.timeout)
    else:
        for name in DEFAULT_SUITES:
            if name in SUITES and SUITES[name].exists():
                all_results[name] = run_suite(name, SUITES[name], args.max,
                                               args.dump_ppm, num_workers, args.timeout)

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
            print(f"  {name:30s}  {good:5d}/{total:<5d} good ({pct:3d}%), {crash} crash")

        pct = grand_good * 100 // max(grand_total, 1)
        print(f"  {'─'*30}  {'─'*30}")
        print(f"  {'TOTAL':30s}  {grand_good:5d}/{grand_total:<5d} good ({pct:3d}%), {grand_crash} crash")
        print(f"  Elapsed: {elapsed:.1f}s ({grand_total/elapsed:.1f} tests/s)")


if __name__ == "__main__":
    main()
