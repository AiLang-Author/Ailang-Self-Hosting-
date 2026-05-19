#!/usr/bin/env python3
"""WPT DOM test runner for the Ailang browser.

Extracts inline <script> content from WPT .html test files,
prepends our testharness.js shim, and feeds through the
test262 batch harness binary (which provides JSEngine_EvalString).

Usage:
    python3 tools/wpt_dom_runner.py [--dir dom/nodes] [--file path.html]
"""

import os
import re
import sys
import struct
import subprocess
import argparse
from pathlib import Path

WPT_ROOT = Path("/home/bob/wpt")
HARNESS_JS = Path(__file__).parent / "wpt_harness.js"
BATCH_BIN = Path("wpt_batch.x")
PROJECT_ROOT = Path(__file__).parent.parent

def extract_inline_scripts(html_path):
    """Extract all inline <script> blocks (skip external src= scripts)."""
    text = html_path.read_text(errors="replace")
    # Remove scripts that load testharness.js / testharnessreport.js
    # Keep only inline scripts
    scripts = []
    for m in re.finditer(r'<script(?:\s[^>]*)?>(.+?)</script>', text, re.DOTALL):
        tag_full = m.group(0)
        if 'src=' in tag_full[:tag_full.index('>')]:
            continue  # External script, skip
        scripts.append(m.group(1))
    return "\n".join(scripts)

def run_test(batch_proc, js_source):
    """Send JS source to batch harness and get pass/fail result."""
    encoded = js_source.encode("utf-8", errors="replace")
    # Protocol: 4 bytes LE length + source
    batch_proc.stdin.write(struct.pack("<I", len(encoded)))
    batch_proc.stdin.write(encoded)
    batch_proc.stdin.flush()

    # Read 1-byte result from fd 4 (which we redirected)
    result = batch_proc.stdout.read(1)
    if not result:
        return None  # Process died
    return result[0]  # 0 = pass, 1 = fail, 2 = timeout

def main():
    parser = argparse.ArgumentParser(description="WPT DOM test runner")
    parser.add_argument("--dir", default="dom/nodes",
                        help="WPT subdirectory to scan (relative to wpt root)")
    parser.add_argument("--file", default=None,
                        help="Run a single test file")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max tests to run (0=all)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print each test result")
    args = parser.parse_args()

    # Read harness shim
    harness_js = HARNESS_JS.read_text()

    # Collect test files
    if args.file:
        test_files = [WPT_ROOT / args.file]
    else:
        test_dir = WPT_ROOT / args.dir
        test_files = sorted(test_dir.glob("*.html"))

    if args.limit > 0:
        test_files = test_files[:args.limit]

    # Build batch binary if needed
    batch_path = PROJECT_ROOT / BATCH_BIN
    if not batch_path.exists():
        print(f"Building {BATCH_BIN}...")
        r = subprocess.run(
            ["./ailang.x", "TestCode/wpt_batch.ailang", str(BATCH_BIN)],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True
        )
        if r.returncode != 0:
            print(f"Build failed: {r.stderr}")
            sys.exit(1)

    # Start batch process
    # The batch harness reads from stdin (4-byte len + source)
    # and writes 1-byte results. Original stdout saved to fd 4.
    proc = subprocess.Popen(
        [str(batch_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(PROJECT_ROOT)
    )

    total = 0
    passed = 0
    failed = 0
    errors = 0

    for test_file in test_files:
        # Extract inline scripts
        inline_js = extract_inline_scripts(test_file)
        if not inline_js.strip():
            continue  # No inline JS, skip

        # Prepend harness + summary reporter
        full_js = harness_js + "\n" + inline_js + "\n" + "done();\n"

        total += 1
        result = run_test(proc, full_js)

        if result is None:
            errors += 1
            if args.verbose:
                print(f"  CRASH: {test_file.name}")
            # Restart process
            proc.kill()
            proc = subprocess.Popen(
                [str(batch_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(PROJECT_ROOT)
            )
            continue

        if result == 0:
            passed += 1
            if args.verbose:
                print(f"  PASS: {test_file.name}")
        elif result == 2:
            errors += 1
            if args.verbose:
                print(f"  TIMEOUT: {test_file.name}")
        else:
            failed += 1
            if args.verbose:
                print(f"  FAIL: {test_file.name}")

    proc.stdin.close()
    proc.wait()

    print(f"\n{'='*50}")
    print(f"WPT DOM Results ({args.dir}):")
    print(f"  Total:   {total}")
    print(f"  Pass:    {passed}")
    print(f"  Fail:    {failed}")
    print(f"  Error:   {errors}")
    if total > 0:
        print(f"  Rate:    {passed}/{total} ({100*passed//total}%)")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
