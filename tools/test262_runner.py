#!/usr/bin/env python3
"""
test262_runner.py — ECMAScript conformance test runner for the Ailang JS engine.

Discovers tests from tc39/test262, filters for supported features, prepends a
polyfill preamble, preprocesses throw statements, executes via test262_harness.x,
and prints a per-category conformance report.

Usage:
    python3 tools/test262_runner.py [options]

    --categories CAT[,CAT,...]   Comma-separated subdirs under test/language/
                                 (default: all target categories)
    --verbose                    Print each test result
    --output-json FILE           Write JSON results to FILE
    --harness PATH               Path to harness binary (default: ./test262_harness.x)
    --test262 PATH               Path to test262 repo (default: ./test262)
    --timeout SECS               Per-test timeout (default: 5)

Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_CATEGORIES = [
    "statements/if",
    "statements/while",
    "statements/for",
    "statements/do-while",
    "statements/switch",
    "statements/break",
    "statements/continue",
    "statements/return",
    "statements/variable",
    "statements/block",
    "statements/empty",
    "statements/expression",
    "statements/labeled",
    "expressions/typeof",
    "expressions/addition",
    "expressions/assignment",
    "expressions/call",
    "expressions/object",
    "expressions/equals",
    "expressions/does-not-equals",
    "expressions/strict-equals",
    "expressions/strict-does-not-equal",
    "expressions/less-than",
    "expressions/greater-than",
    "expressions/less-than-or-equal",
    "expressions/greater-than-or-equal",
    "expressions/subtraction",
    "expressions/multiplication",
    "expressions/division",
    "expressions/modulus",
    "expressions/comma",
    "expressions/logical-or",
    "expressions/logical-and",
    "expressions/logical-not",
    "expressions/void",
    "expressions/delete",
    "expressions/grouping",
    "expressions/compound-assignment",
    "expressions/prefix-increment",
    "expressions/prefix-decrement",
    "expressions/postfix-increment",
    "expressions/postfix-decrement",
    "expressions/conditional",
    "expressions/bitwise-and",
    "expressions/bitwise-or",
    "expressions/bitwise-xor",
    "expressions/bitwise-not",
    "expressions/left-shift",
    "expressions/right-shift",
    "expressions/unsigned-right-shift",
    "expressions/unary-minus",
    "expressions/unary-plus",
]

UNSUPPORTED_FEATURES = {
    "arrow-function", "class", "destructuring-binding",
    "destructuring-assignment", "for-of", "generators", "template",
    "Symbol", "Symbol.iterator", "Symbol.toPrimitive", "Symbol.hasInstance",
    "Symbol.species", "Symbol.match", "Symbol.replace", "Symbol.search",
    "Symbol.split", "Symbol.toStringTag", "Symbol.unscopables",
    "Proxy", "Promise", "WeakMap", "WeakSet", "WeakRef",
    "Map", "Set", "RegExp", "BigInt", "ArrayBuffer", "DataView",
    "SharedArrayBuffer", "Atomics", "TypedArray", "Float16Array",
    "async-functions", "async-iteration", "top-level-await",
    "import.meta", "dynamic-import", "import-assertions",
    "optional-chaining", "nullish-coalescing",
    "numeric-separator-literal", "optional-catch-binding",
    "rest-parameters", "spread", "default-parameters",
    "computed-property-names", "object-spread", "object-rest",
    "String.prototype.matchAll", "String.prototype.replaceAll",
    "String.prototype.trimStart", "String.prototype.trimEnd",
    "Array.prototype.flat", "Array.prototype.flatMap",
    "Array.prototype.includes", "Array.prototype.at",
    "Object.entries", "Object.values", "Object.fromEntries",
    "globalThis", "AggregateError", "FinalizationRegistry",
    "logical-assignment-operators", "Intl",
    "new.target", "super",
    "tail-call-optimization", "Reflect", "Reflect.construct",
    "Reflect.set", "Reflect.get",
    "json-superset", "well-formed-json-stringify",
    "string-trimming", "coalesce-expression",
    "exponentiation", "u180e",
    "caller",
}

UNSUPPORTED_SOURCE_PATTERNS = [
    r'\beval\s*\(',
    r'\bwith\s*\(',
    r'"use strict"',
    r"'use strict'",
    r'\bnew\s+Error\s*\(',
    r'\bnew\s+TypeError\s*\(',
    r'\bnew\s+ReferenceError\s*\(',
    r'\bnew\s+SyntaxError\s*\(',
    r'\bnew\s+RangeError\s*\(',
    r'\bnew\s+URIError\s*\(',
    r'\bnew\s+EvalError\s*\(',
    r'\bString\.prototype\b',
    r'\bObject\s*\.\s*defineProperty\b',
    r'\bObject\s*\.\s*getOwnPropertyDescriptor\b',
    r'\bObject\s*\.\s*keys\b',
    r'\bObject\s*\.\s*create\b',
    r'\bObject\s*\.\s*freeze\b',
    r'\bObject\s*\.\s*seal\b',
    r'\bObject\s*\.\s*is\b',
    r'\bObject\s*\.\s*assign\b',
    r'\bJSON\s*\.',
    r'\b__proto__\b',
    r'\bObject\s*\.\s*getPrototypeOf\b',
    r'\bObject\s*\.\s*setPrototypeOf\b',
    r'\bArray\s*\.\s*isArray\b',
    r'\bArray\s*\.\s*from\b',
    r'\bencodeURI\b',
    r'\bdecodeURI\b',
    r'\bsetTimeout\b',
    r'\bsetInterval\b',
    r'\barguments\b',
    r'\.\s*call\s*\(',
    r'\.\s*apply\s*\(',
    r'\.\s*bind\s*\(',
    r'\.\s*hasOwnProperty\s*\(',
    r'\.\s*toString\s*\(',
    r'\.\s*valueOf\s*\(',
    r'\.\s*prototype\b',
    r'\.\s*constructor\b',
    r'\blet\b',
    r'\bconst\b',
    r'(?<!["\'])/[^/\n]+/[gimsuy]*(?=\s*[;,.\)\]\}])',  # regex literal
    r'=>',  # arrow function
    r'`',   # template literal
    r'\bclass\b',
    r'\.\.\.',  # spread/rest
    r'\byield\b',
    r'\bawait\b',
    r'\basync\b',
    r'\bimport\b',
    r'\bexport\b',
]

# Compiled combined pattern for fast matching
_UNSUPPORTED_RE = re.compile("|".join(UNSUPPORTED_SOURCE_PATTERNS))

POLYFILL = """\
var __test262_failed = 0;
function Test262Error(m) { __test262_failed = 1; }
function $ERROR(m) { __test262_failed = 1; }
function $DONOTEVALUATE() { __test262_failed = 1; }
var assert = {};
assert.sameValue = function(a, e, m) { if (a !== e) { __test262_failed = 1; } };
assert.notSameValue = function(a, u, m) { if (a === u) { __test262_failed = 1; } };
assert.throws = function(E, fn, m) { try { fn(); __test262_failed = 1; } catch (e) { } };
"""

EPILOGUE = """
if (__test262_failed) { __force_fail__(); }
"""

TMP_FILE = "/tmp/test262_current.js"

# =============================================================================
# FRONTMATTER PARSER
# =============================================================================

_FRONTMATTER_RE = re.compile(r'/\*---\s*\n(.*?)\n\s*---\*/', re.DOTALL)


def strip_comments(source):
    """Remove single-line (//) and multi-line (/* */) comments from JS source.

    Preserves string contents (won't strip // inside "..." or '...')."""
    result = []
    i = 0
    n = len(source)
    while i < n:
        # String literals — skip over them
        if source[i] in ('"', "'"):
            q = source[i]
            result.append(q)
            i += 1
            while i < n and source[i] != q:
                if source[i] == '\\' and i + 1 < n:
                    result.append(source[i])
                    result.append(source[i + 1])
                    i += 2
                else:
                    result.append(source[i])
                    i += 1
            if i < n:
                result.append(source[i])
                i += 1
        # Multi-line comment
        elif source[i] == '/' and i + 1 < n and source[i + 1] == '*':
            end = source.find('*/', i + 2)
            if end == -1:
                i = n
            else:
                i = end + 2
        # Single-line comment
        elif source[i] == '/' and i + 1 < n and source[i + 1] == '/':
            end = source.find('\n', i)
            if end == -1:
                i = n
            else:
                i = end  # keep the newline
        else:
            result.append(source[i])
            i += 1
    return "".join(result)

def parse_frontmatter(source):
    """Extract YAML-ish frontmatter from test262 test file."""
    m = _FRONTMATTER_RE.search(source)
    if not m:
        return {}

    raw = m.group(1)
    meta = {}

    # Parse features list
    feat_match = re.search(r'^features:\s*\[([^\]]*)\]', raw, re.MULTILINE)
    if feat_match:
        meta["features"] = [f.strip().strip("'\"") for f in feat_match.group(1).split(",") if f.strip()]
    else:
        feat_lines = []
        in_feat = False
        for line in raw.split("\n"):
            if re.match(r'^features:\s*$', line):
                in_feat = True
                continue
            if in_feat:
                fm = re.match(r'^\s+-\s+(.+)', line)
                if fm:
                    feat_lines.append(fm.group(1).strip().strip("'\""))
                else:
                    in_feat = False
        if feat_lines:
            meta["features"] = feat_lines

    # Parse flags
    flags_match = re.search(r'^flags:\s*\[([^\]]*)\]', raw, re.MULTILINE)
    if flags_match:
        meta["flags"] = [f.strip().strip("'\"") for f in flags_match.group(1).split(",") if f.strip()]
    else:
        flag_lines = []
        in_flags = False
        for line in raw.split("\n"):
            if re.match(r'^flags:\s*$', line):
                in_flags = True
                continue
            if in_flags:
                fm = re.match(r'^\s+-\s+(.+)', line)
                if fm:
                    flag_lines.append(fm.group(1).strip().strip("'\""))
                else:
                    in_flags = False
        if flag_lines:
            meta["flags"] = flag_lines

    # Parse includes
    inc_match = re.search(r'^includes:\s*\[([^\]]*)\]', raw, re.MULTILINE)
    if inc_match:
        meta["includes"] = [f.strip().strip("'\"") for f in inc_match.group(1).split(",") if f.strip()]

    # Parse negative
    neg_match = re.search(r'^negative:', raw, re.MULTILINE)
    if neg_match:
        meta["negative"] = True
        phase_match = re.search(r'phase:\s*(\w+)', raw[neg_match.start():])
        if phase_match:
            meta["negative_phase"] = phase_match.group(1)
        type_match = re.search(r'type:\s*(\w+)', raw[neg_match.start():])
        if type_match:
            meta["negative_type"] = type_match.group(1)

    # Parse description
    desc_match = re.search(r'^description:\s*[>|]?\s*\n?\s*(.*)', raw, re.MULTILINE)
    if desc_match:
        meta["description"] = desc_match.group(1).strip()

    return meta


# =============================================================================
# FILTER
# =============================================================================

def should_skip(source, meta):
    """Return (True, reason) if test should be skipped, else (False, '')."""
    flags = set(meta.get("flags", []))

    if "onlyStrict" in flags:
        return True, "onlyStrict"
    if "module" in flags:
        return True, "module"
    if "async" in flags:
        return True, "async"
    if "noStrict" in flags and "raw" in flags:
        pass  # OK

    features = set(meta.get("features", []))
    unsup = features & UNSUPPORTED_FEATURES
    if unsup:
        return True, f"feature:{next(iter(unsup))}"

    includes = meta.get("includes", [])
    for inc in includes:
        if inc not in ("assert.js", "sta.js", "propertyHelper.js", "compareArray.js"):
            return True, f"include:{inc}"

    # Strip comments before checking source patterns (avoids false positives
    # from words like "in", "new Error" appearing in comments/descriptions)
    code_only = strip_comments(source)
    if _UNSUPPORTED_RE.search(code_only):
        m = _UNSUPPORTED_RE.search(code_only)
        snippet = m.group(0)[:30]
        return True, f"source:{snippet}"

    return False, ""


# =============================================================================
# PREPROCESSOR
# =============================================================================

def preprocess(source):
    """Clean up test source for the Ailang JS engine."""
    # Strip the frontmatter block itself
    source = _FRONTMATTER_RE.sub("", source)

    # Replace throw statements with $ERROR calls
    source = re.sub(
        r'throw\s+new\s+Test262Error\(([^)]*)\)',
        r'$ERROR(\1)',
        source,
    )
    source = re.sub(
        r'throw\s+new\s+\w+Error\(([^)]*)\)',
        r'$ERROR(\1)',
        source,
    )
    # Plain throw "string" is now handled natively (no conversion needed)

    return source


# =============================================================================
# RUNNER
# =============================================================================

def discover_tests(test262_dir, categories):
    """Yield .js test file paths for the given categories."""
    test_root = Path(test262_dir) / "test" / "language"
    for cat in categories:
        cat_dir = test_root / cat
        if not cat_dir.exists():
            continue
        for js_file in sorted(cat_dir.rglob("*.js")):
            # Skip _FIXTURE files
            if js_file.name.startswith("_"):
                continue
            yield str(js_file)


def run_test(harness, test_path, timeout, verbose=False):
    """
    Run a single test262 test.

    Returns dict: {path, status, reason, time_ms}
    status is one of: 'pass', 'fail', 'skip', 'timeout', 'error'
    """
    try:
        source = open(test_path, "r", errors="replace").read()
    except Exception as e:
        return {"path": test_path, "status": "error", "reason": str(e), "time_ms": 0}

    meta = parse_frontmatter(source)

    skip, reason = should_skip(source, meta)
    if skip:
        return {"path": test_path, "status": "skip", "reason": reason, "time_ms": 0}

    # Build test source
    processed = preprocess(source)
    full_source = POLYFILL + processed + EPILOGUE

    # Write to temp file
    try:
        with open(TMP_FILE, "w") as f:
            f.write(full_source)
    except Exception as e:
        return {"path": test_path, "status": "error", "reason": f"write:{e}", "time_ms": 0}

    # Execute
    is_negative = meta.get("negative", False)
    neg_phase = meta.get("negative_phase", "runtime")

    t0 = time.monotonic()
    try:
        result = subprocess.run(
            [harness],
            timeout=timeout,
            capture_output=True,
        )
        elapsed = (time.monotonic() - t0) * 1000
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        elapsed = timeout * 1000
        return {"path": test_path, "status": "timeout", "reason": "timeout", "time_ms": elapsed}
    except Exception as e:
        elapsed = (time.monotonic() - t0) * 1000
        return {"path": test_path, "status": "error", "reason": str(e), "time_ms": elapsed}

    # Interpret result
    if is_negative:
        # Negative test: SHOULD fail (exit != 0)
        if neg_phase == "parse":
            # Parse-phase negative: engine should reject during parse
            if exit_code != 0:
                status = "pass"
            else:
                status = "fail"
        else:
            # Runtime negative
            if exit_code != 0:
                status = "pass"
            else:
                status = "fail"
    else:
        # Positive test: should succeed (exit == 0)
        if exit_code == 0:
            status = "pass"
        else:
            status = "fail"

    return {
        "path": test_path,
        "status": status,
        "reason": f"exit={exit_code}" if status == "fail" else "",
        "time_ms": round(elapsed, 1),
    }


# =============================================================================
# REPORTING
# =============================================================================

def categorize_path(test_path, test262_dir):
    """Extract category from test path (e.g. 'statements/if')."""
    rel = os.path.relpath(test_path, os.path.join(test262_dir, "test", "language"))
    parts = rel.split(os.sep)
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return parts[0]


def print_report(results, test262_dir):
    """Print a formatted conformance report."""
    cats = {}
    for r in results:
        cat = categorize_path(r["path"], test262_dir)
        if cat not in cats:
            cats[cat] = {"total": 0, "pass": 0, "fail": 0, "skip": 0, "timeout": 0, "error": 0}
        cats[cat]["total"] += 1
        cats[cat][r["status"]] += 1

    print()
    header = f"{'Category':<42} {'Total':>5} {'Pass':>5} {'Fail':>5} {'Skip':>5} {'T/O':>4} {'Pass%':>6}"
    print(header)
    print("-" * len(header))

    totals = {"total": 0, "pass": 0, "fail": 0, "skip": 0, "timeout": 0, "error": 0}

    for cat in sorted(cats.keys()):
        c = cats[cat]
        run = c["pass"] + c["fail"]
        pct = (c["pass"] / run * 100) if run > 0 else 0
        print(f"{cat:<42} {c['total']:>5} {c['pass']:>5} {c['fail']:>5} {c['skip']:>5} {c['timeout']:>4} {pct:>5.1f}%")
        for k in totals:
            totals[k] += c[k]

    print("-" * len(header))
    run = totals["pass"] + totals["fail"]
    pct = (totals["pass"] / run * 100) if run > 0 else 0
    print(f"{'TOTAL':<42} {totals['total']:>5} {totals['pass']:>5} {totals['fail']:>5} {totals['skip']:>5} {totals['timeout']:>4} {pct:>5.1f}%")
    print()


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Test262 conformance runner for Ailang JS engine")
    parser.add_argument("--categories", type=str, default=None,
                        help="Comma-separated categories (e.g. statements/if,statements/while)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print each test result")
    parser.add_argument("--output-json", type=str, default=None,
                        help="Write JSON results to file")
    parser.add_argument("--harness", type=str, default="./test262_harness.x",
                        help="Path to harness binary")
    parser.add_argument("--test262", type=str, default="./test262",
                        help="Path to test262 repo")
    parser.add_argument("--timeout", type=float, default=5.0,
                        help="Per-test timeout in seconds")
    parser.add_argument("--fail-only", action="store_true",
                        help="In verbose mode, only show failures")
    args = parser.parse_args()

    # Validate
    if not os.path.isfile(args.harness):
        print(f"ERROR: harness binary not found: {args.harness}", file=sys.stderr)
        print("Build it with: ./ailang.x TestCode/test262_harness.ailang test262_harness.x", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.test262):
        print(f"ERROR: test262 directory not found: {args.test262}", file=sys.stderr)
        print("Clone it with: git clone --depth 1 https://github.com/tc39/test262.git test262", file=sys.stderr)
        sys.exit(1)

    categories = args.categories.split(",") if args.categories else DEFAULT_CATEGORIES

    # Discover tests
    test_files = list(discover_tests(args.test262, categories))
    if not test_files:
        print("No test files found for specified categories.", file=sys.stderr)
        sys.exit(1)

    print(f"Test262 Conformance — Ailang JS Engine")
    print(f"Tests discovered: {len(test_files)}")
    print(f"Categories: {len(categories)}")
    print()

    # Run tests
    results = []
    t_start = time.monotonic()

    for i, tf in enumerate(test_files):
        r = run_test(args.harness, tf, args.timeout, args.verbose)
        results.append(r)

        if args.verbose:
            short = os.path.relpath(tf, args.test262)
            if args.fail_only and r["status"] in ("pass", "skip"):
                pass
            else:
                status_sym = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP",
                              "timeout": "T/O ", "error": "ERR "}
                sym = status_sym.get(r["status"], "????")
                extra = f"  ({r['reason']})" if r["reason"] else ""
                print(f"  [{sym}] {short}{extra}")

        # Progress every 100 tests (non-verbose)
        if not args.verbose and (i + 1) % 100 == 0:
            print(f"  ... {i + 1}/{len(test_files)} tests completed", flush=True)

    t_total = time.monotonic() - t_start

    # Report
    print_report(results, args.test262)
    print(f"Wall time: {t_total:.1f}s")

    # JSON output
    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump({
                "total_tests": len(results),
                "wall_time_s": round(t_total, 2),
                "results": results,
            }, f, indent=2)
        print(f"JSON results written to: {args.output_json}")


if __name__ == "__main__":
    main()
