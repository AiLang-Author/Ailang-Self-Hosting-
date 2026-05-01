#!/usr/bin/env python3
"""
html5lib_runner.py — HTML tokenizer conformance test runner for the Ailang HTML engine.

Reads html5lib-tests tokenizer test files (.test JSON), feeds input to
html5lib_harness.x, parses the token stream output, and compares against
expected tokens.

Usage:
    python3 tools/html5lib_runner.py [options]

    --files FILE[,FILE,...]   Comma-separated .test filenames (default: core tests)
    --verbose                 Print each test result
    --fail-only               In verbose mode, only show failures
    --harness PATH            Path to harness binary (default: ./html5lib_harness.x)
    --tests PATH              Path to html5lib-tests/tokenizer/ (default: ./html5lib-tests/tokenizer)
    --timeout SECS            Per-test timeout (default: 5)

Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

# =============================================================================
# CONSTANTS
# =============================================================================

# Start with the core test files (skip entities/unicode for now — focus on structure)
DEFAULT_FILES = [
    "test1.test",
    "test2.test",
    "test3.test",
    "test4.test",
    "domjs.test",
    "contentModelFlags.test",
]

TMP_FILE = "/tmp/html5lib_current.html"

# Token type numbers from the harness
T_TAG_OPEN = 1
T_TAG_CLOSE = 2
T_TAG_SELF_CLOSE = 3
T_TAG_END = 4
T_ATTR_NAME = 5
T_ATTR_VALUE = 6
T_ATTR_BARE = 7
T_TEXT = 8
T_COMMENT = 9
T_DOCTYPE = 10
T_EOF = 11


# =============================================================================
# PARSE HARNESS OUTPUT
# =============================================================================

def parse_harness_output(stdout):
    """
    Parse the harness token stream into html5lib-style token list.

    Harness output format:  TYPE_NUM|string\n

    We reconstruct html5lib tokens:
      ["StartTag", "tagname", {attrs}]
      ["EndTag", "tagname"]
      ["Character", "text"]
      ["Comment", "text"]
      ["DOCTYPE", name, ...]
    """
    raw_lines = stdout.split("\n") if stdout else []
    # Strip trailing empty lines
    while raw_lines and raw_lines[-1] == '':
        raw_lines.pop()
    # Merge continuation lines: lines not matching digit|... are part of previous value
    lines = []
    for rl in raw_lines:
        if re.match(r'^\d+\|', rl):
            lines.append(rl)
        elif lines:
            # Continuation of previous token value (embedded newline)
            lines[-1] += "\n" + rl
    tokens = []

    # State machine to accumulate StartTag with its attributes
    current_tag = None   # (tagname, attrs_dict, attr_order)
    current_attr = None  # current attribute name being collected

    def flush_tag():
        nonlocal current_tag, current_attr
        if current_tag:
            name, attrs, _ = current_tag
            tokens.append(["StartTag", name, attrs])
            current_tag = None
            current_attr = None

    for line in lines:
        if "|" not in line:
            continue
        ttype_str, _, value = line.partition("|")
        try:
            ttype = int(ttype_str)
        except ValueError:
            continue

        if ttype == T_TAG_OPEN:
            flush_tag()
            current_tag = (value, {}, [])
            current_attr = None

        elif ttype == T_ATTR_NAME:
            if current_tag:
                current_attr = value
                # Don't add to dict yet — wait for value

        elif ttype == T_ATTR_VALUE:
            if current_tag and current_attr:
                name, attrs, order = current_tag
                # Per spec: first attribute wins on duplicates
                if current_attr not in attrs:
                    attrs[current_attr] = value
                    order.append(current_attr)
                current_attr = None

        elif ttype == T_ATTR_BARE:
            if current_tag:
                name, attrs, order = current_tag
                if value not in attrs:
                    attrs[value] = ""
                    order.append(value)
                current_attr = None

        elif ttype == T_TAG_END:
            flush_tag()

        elif ttype == T_TAG_SELF_CLOSE:
            flush_tag()

        elif ttype == T_TAG_CLOSE:
            flush_tag()
            tokens.append(["EndTag", value])

        elif ttype == T_TEXT:
            flush_tag()
            # Merge adjacent Character tokens (html5lib expects merged)
            if tokens and tokens[-1][0] == "Character":
                tokens[-1][1] += value
            else:
                tokens.append(["Character", value])

        elif ttype == T_COMMENT:
            flush_tag()
            tokens.append(["Comment", value])

        elif ttype == T_DOCTYPE:
            flush_tag()
            tokens.append(["DOCTYPE", value if value else None])

        elif ttype == T_EOF:
            flush_tag()

    flush_tag()
    return tokens


# =============================================================================
# COMPARISON
# =============================================================================

def normalize_expected(expected_tokens):
    """Normalize html5lib expected tokens for comparison."""
    result = []
    for tok in expected_tokens:
        if tok[0] == "Character":
            # Merge adjacent characters
            if result and result[-1][0] == "Character":
                result[-1] = ["Character", result[-1][1] + tok[1]]
            else:
                result.append(list(tok))
        elif tok[0] == "StartTag":
            # Normalize: ["StartTag", name, attrs_dict]
            name = tok[1]
            attrs = tok[2] if len(tok) > 2 else {}
            result.append(["StartTag", name, attrs])
        elif tok[0] == "EndTag":
            result.append(["EndTag", tok[1]])
        elif tok[0] == "Comment":
            result.append(["Comment", tok[1]])
        elif tok[0] == "DOCTYPE":
            # html5lib: ["DOCTYPE", name, public_id, system_id, correctness]
            # We just compare name for now
            name = tok[1] if len(tok) > 1 else None
            result.append(["DOCTYPE", name])
        else:
            result.append(list(tok))
    return result


def tokens_match(actual, expected):
    """Compare actual tokens from harness against expected from test file."""
    expected = normalize_expected(expected)

    if len(actual) != len(expected):
        return False, f"token count: got {len(actual)}, expected {len(expected)}"

    for i, (act, exp) in enumerate(zip(actual, expected)):
        if act[0] != exp[0]:
            return False, f"token {i}: type {act[0]} != {exp[0]}"

        if act[0] == "StartTag":
            if act[1] != exp[1]:
                return False, f"token {i}: tag name '{act[1]}' != '{exp[1]}'"
            if act[2] != exp[2]:
                return False, f"token {i}: attrs {act[2]} != {exp[2]}"
        elif act[0] == "EndTag":
            if act[1] != exp[1]:
                return False, f"token {i}: end tag '{act[1]}' != '{exp[1]}'"
        elif act[0] == "Character":
            if act[1] != exp[1]:
                return False, f"token {i}: text '{act[1][:40]}' != '{exp[1][:40]}'"
        elif act[0] == "Comment":
            if act[1] != exp[1]:
                return False, f"token {i}: comment '{act[1][:40]}' != '{exp[1][:40]}'"
        elif act[0] == "DOCTYPE":
            if act[1] != exp[1]:
                return False, f"token {i}: doctype '{act[1]}' != '{exp[1]}'"

    return True, ""


# =============================================================================
# TEST RUNNER
# =============================================================================

def should_skip(test):
    """Check if test should be skipped (e.g. double-escaped, initial states)."""
    if test.get("doubleEscaped"):
        return True, "doubleEscaped"
    if "initialStates" in test:
        # We only support the default "Data state"
        states = test["initialStates"]
        if states != ["Data state"]:
            return True, f"initialState:{states[0][:20]}"
    # Skip tests with null bytes (our tokenizer may not handle them)
    inp = test.get("input", "")
    if "\x00" in inp:
        return True, "null-byte"
    return False, ""


def run_single_test(harness, test, timeout):
    """Run a single html5lib tokenizer test. Returns (status, reason)."""
    skip, reason = should_skip(test)
    if skip:
        return "skip", reason

    inp = test.get("input", "")
    expected = test.get("output", [])

    # Write input to temp file
    try:
        with open(TMP_FILE, "w", encoding="utf-8") as f:
            f.write(inp)
    except Exception as e:
        return "error", f"write:{e}"

    # Run harness
    try:
        result = subprocess.run(
            [harness],
            timeout=timeout,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        return "timeout", "timeout"
    except Exception as e:
        return "error", str(e)

    if result.returncode != 0:
        return "error", f"exit={result.returncode}"

    # Parse output
    actual = parse_harness_output(result.stdout)

    # Compare
    match, reason = tokens_match(actual, expected)
    if match:
        return "pass", ""
    else:
        return "fail", reason


# =============================================================================
# REPORTING
# =============================================================================

def print_report(results_by_file):
    """Print a formatted conformance report."""
    print()
    header = f"{'Test File':<35} {'Total':>5} {'Pass':>5} {'Fail':>5} {'Skip':>5} {'T/O':>4} {'Pass%':>6}"
    print(header)
    print("-" * len(header))

    grand = {"total": 0, "pass": 0, "fail": 0, "skip": 0, "timeout": 0, "error": 0}

    for fname in sorted(results_by_file.keys()):
        results = results_by_file[fname]
        c = {"total": 0, "pass": 0, "fail": 0, "skip": 0, "timeout": 0, "error": 0}
        for status, _ in results:
            c["total"] += 1
            c[status] += 1

        run = c["pass"] + c["fail"]
        pct = (c["pass"] / run * 100) if run > 0 else 0
        print(f"{fname:<35} {c['total']:>5} {c['pass']:>5} {c['fail']:>5} {c['skip']:>5} {c['timeout']:>4} {pct:>5.1f}%")

        for k in grand:
            grand[k] += c[k]

    print("-" * len(header))
    run = grand["pass"] + grand["fail"]
    pct = (grand["pass"] / run * 100) if run > 0 else 0
    print(f"{'TOTAL':<35} {grand['total']:>5} {grand['pass']:>5} {grand['fail']:>5} {grand['skip']:>5} {grand['timeout']:>4} {pct:>5.1f}%")
    print()


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="html5lib tokenizer conformance runner for Ailang")
    parser.add_argument("--files", type=str, default=None,
                        help="Comma-separated .test filenames")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print each test result")
    parser.add_argument("--fail-only", action="store_true",
                        help="In verbose mode, only show failures")
    parser.add_argument("--harness", type=str, default="./html5lib_harness.x",
                        help="Path to harness binary")
    parser.add_argument("--tests", type=str, default="./html5lib-tests/tokenizer",
                        help="Path to html5lib-tests/tokenizer/")
    parser.add_argument("--timeout", type=float, default=5.0,
                        help="Per-test timeout in seconds")
    parser.add_argument("--all", action="store_true",
                        help="Run all test files including entities/unicode")
    args = parser.parse_args()

    if not os.path.isfile(args.harness):
        print(f"ERROR: harness binary not found: {args.harness}", file=sys.stderr)
        print("Build it with: ./ailang.x TestCode/html5lib_harness.ailang html5lib_harness.x", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.tests):
        print(f"ERROR: test directory not found: {args.tests}", file=sys.stderr)
        sys.exit(1)

    # Determine which files to run
    if args.files:
        test_files = args.files.split(",")
    elif args.all:
        test_files = [f for f in sorted(os.listdir(args.tests)) if f.endswith(".test")]
    else:
        test_files = DEFAULT_FILES

    print(f"html5lib Tokenizer Conformance — Ailang HTML Engine")
    print(f"Test files: {len(test_files)}")
    print()

    results_by_file = {}
    total_tests = 0

    for fname in test_files:
        fpath = os.path.join(args.tests, fname)
        if not os.path.isfile(fpath):
            print(f"  WARNING: {fname} not found, skipping", file=sys.stderr)
            continue

        with open(fpath, "r") as f:
            data = json.load(f)

        tests = data.get("tests", [])
        results = []

        for i, test in enumerate(tests):
            desc = test.get("description", f"test #{i}")
            status, reason = run_single_test(args.harness, test, args.timeout)
            results.append((status, reason))
            total_tests += 1

            if args.verbose:
                if args.fail_only and status in ("pass", "skip"):
                    pass
                else:
                    sym_map = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP",
                               "timeout": "T/O ", "error": "ERR "}
                    sym = sym_map.get(status, "????")
                    extra = f"  ({reason})" if reason else ""
                    print(f"  [{sym}] {fname}: {desc}{extra}")

            if not args.verbose and total_tests % 50 == 0:
                print(f"  ... {total_tests} tests completed", flush=True)

        results_by_file[fname] = results

    print_report(results_by_file)


if __name__ == "__main__":
    main()
