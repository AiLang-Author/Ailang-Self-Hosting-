#!/usr/bin/env python3
"""
js_midgate.py — Fast multi-layer gate for the Ailang JS engine.

Layers (skip with flags):
  1. e2e          — DOM/script integration (test_js_e2e.x)
  2. core         — JS-tests/js_midgate.js via harness (~seconds)
  3. curated      — hand-picked test262 paths (~1–2 min, not 50k)
  4. categories   — call / function / arguments-object (optional)

Usage:
  python3 tools/js_midgate.py              # e2e + core + curated
  python3 tools/js_midgate.py --quick      # e2e + core only
  python3 tools/js_midgate.py --with-cats  # also category slices
  python3 tools/js_midgate.py --rebuild    # rebuild harness/e2e first

Exit 0 only if all selected layers pass.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "test262_harness.x"
BATCH = ROOT / "test262_harness_batch.x"
E2E = ROOT / "test_js_e2e.x"
MIDGATE_JS = ROOT / "JS-tests" / "js_midgate.js"
RUNNER = ROOT / "tools" / "test262_runner.py"
AILANG = ROOT / "ailang.x"

# Curated high-signal test262 paths (closures, spread, args restore, symbols).
# Keep short — this is the "not 50k" diagnostic net.
CURATED_PATHS = [
    # closures / scope
    "language/expressions/call/scope-var-close.js",
    "language/expressions/call/scope-var-open.js",
    "language/expressions/call/scope-lex-close.js",
    "language/expressions/call/scope-lex-open.js",
    # array / iterable call spread
    "language/expressions/call/spread-sngl-literal.js",
    "language/expressions/call/spread-sngl-expr.js",
    "language/expressions/call/spread-sngl-empty.js",
    "language/expressions/call/spread-mult-literal.js",
    "language/expressions/call/spread-mult-expr.js",
    "language/expressions/call/spread-sngl-iter.js",
    "language/expressions/call/spread-mult-iter.js",
    # object spread (Mole 11)
    "language/expressions/call/spread-sngl-obj-ident.js",
    "language/expressions/call/spread-mult-obj-ident.js",
    "language/expressions/call/spread-obj-null.js",
    "language/expressions/call/spread-obj-undefined.js",
    "language/expressions/call/spread-obj-overrides-prev-properties.js",
    "language/expressions/call/spread-obj-mult-spread.js",
    "language/expressions/call/spread-obj-skip-non-enumerable.js",
    "language/expressions/call/spread-obj-getter-init.js",
    "language/expressions/call/spread-mult-obj-null.js",
    "language/expressions/call/spread-mult-obj-undefined.js",
    # trailing-comma args (arguments restore signal)
    "language/arguments-object/func-decl-args-trailing-comma-single-args.js",
    "language/arguments-object/func-decl-args-trailing-comma-multiple.js",
    "language/arguments-object/meth-args-trailing-comma-spread-operator.js",
    "language/arguments-object/meth-args-trailing-comma-multiple.js",
]


def run(cmd, cwd=None, timeout=120):
    t0 = time.monotonic()
    try:
        r = subprocess.run(
            cmd,
            cwd=cwd or ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    return r.returncode, r.stdout, r.stderr


def rebuild():
    steps = [
        ([str(AILANG), "JS-tests/test_js_e2e.ailang", "-o", "test_js_e2e.x"], 180),
        ([str(AILANG), "JS-tests/test262_harness.ailang", "-o", "test262_harness.x"], 180),
        ([str(AILANG), "JS-tests/test262_harness_batch.ailang", "-o", "test262_harness_batch.x"], 180),
    ]
    for cmd, to in steps:
        print(f"  rebuild: {' '.join(cmd[-3:])} ...", flush=True)
        rc, out, err = run(cmd, timeout=to)
        if rc != 0:
            print(out[-500:] if out else "")
            print(err[-500:] if err else "")
            return False
    return True


def layer_e2e():
    print("== layer: e2e ==")
    if not E2E.is_file():
        print("  FAIL: test_js_e2e.x missing (pass --rebuild)")
        return False
    rc, out, err = run([str(E2E)], timeout=60)
    text = out + err
    print(text[-800:] if len(text) > 800 else text)
    ok = rc == 0 and "ALL TESTS PASSED" in text and "FAIL: 0" in text
    print("  =>", "PASS" if ok else "FAIL")
    return ok


def layer_core():
    print("== layer: core midgate (js_midgate.js) ==")
    if not HARNESS.is_file():
        print("  FAIL: test262_harness.x missing (pass --rebuild)")
        return False
    if not MIDGATE_JS.is_file():
        print("  FAIL: JS-tests/js_midgate.js missing")
        return False
    # harness reads /tmp/test262_current.js
    src = MIDGATE_JS.read_text()
    Path("/tmp/test262_current.js").write_text(src)
    rc, out, err = run([str(HARNESS)], timeout=30)
    text = out + err
    if "VM error" in text or rc != 0:
        print(text[-1200:])
        print("  => FAIL rc=", rc)
        return False
    print("  core midgate OK")
    print("  => PASS")
    return True


def layer_curated(jobs: int):
    print("== layer: curated test262 paths ==")
    if not BATCH.is_file() and not HARNESS.is_file():
        print("  FAIL: harness missing")
        return False
    paths = ",".join(CURATED_PATHS)
    cmd = [
        sys.executable,
        str(RUNNER),
        "--paths",
        paths,
        "-j",
        str(jobs),
        "--verbose",
    ]
    rc, out, err = run(cmd, timeout=180)
    text = out + err
    # print summary lines
    for line in text.splitlines():
        if line.strip().startswith("[") or "TOTAL" in line or line.startswith("Category"):
            print(" ", line)
        if "------" in line:
            print(" ", line)
    # parse TOTAL
    ok = False
    for line in text.splitlines():
        if line.startswith("TOTAL"):
            parts = line.split()
            # TOTAL total pass fail ...
            try:
                total, passed, failed = int(parts[1]), int(parts[2]), int(parts[3])
                ok = failed == 0 and passed == total and total > 0
                print(f"  curated: {passed}/{total}")
            except (IndexError, ValueError):
                pass
    print("  =>", "PASS" if ok else "FAIL")
    return ok


def layer_categories(jobs: int):
    print("== layer: categories call/function/args ==")
    cmd = [
        sys.executable,
        str(RUNNER),
        "--categories",
        "expressions/call,arguments-object,statements/function",
        "-j",
        str(jobs),
    ]
    rc, out, err = run(cmd, timeout=300)
    text = out + err
    for line in text.splitlines():
        if "expressions/call" in line or "arguments-object" in line or "statements/function" in line or line.startswith("TOTAL"):
            print(" ", line)
    print("  (category layer is informational — does not fail the gate)")
    print("  => DONE")
    return True


def main():
    ap = argparse.ArgumentParser(description="Ailang JS mid-gate")
    ap.add_argument("--quick", action="store_true", help="e2e + core only")
    ap.add_argument("--with-cats", action="store_true", help="also run call/function/args categories")
    ap.add_argument("--rebuild", action="store_true", help="rebuild e2e + harness first")
    ap.add_argument("-j", type=int, default=8, help="parallel jobs for test262 slices")
    args = ap.parse_args()

    os.chdir(ROOT)
    print("JS mid-gate — root:", ROOT)

    if args.rebuild:
        print("== rebuild ==")
        if not rebuild():
            sys.exit(1)

    results = []
    results.append(("e2e", layer_e2e()))
    results.append(("core", layer_core()))
    if not args.quick:
        results.append(("curated", layer_curated(args.j)))
    if args.with_cats:
        results.append(("categories", layer_categories(args.j)))

    print("\n======== SUMMARY ========")
    all_ok = True
    for name, ok in results:
        print(f"  {name}: {'PASS' if ok else 'FAIL'}")
        if not ok:
            all_ok = False
    print("=========================")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
