#!/usr/bin/env python3
"""
aimacro_cpython_runner.py — CPython-suite analog of tools/test262_runner.py.

Pipeline per file:
  1. py2aim.py     indent Python → AIMacro `{ }`
  2. ./aimacro.x   .aim → .ailang
  3. ./ailang.x    compile (and optionally run)
  4. For curated / --stage run: compare stdout/exit to python3

Corpora (test262 shape, not a unittest dump):
  curated  tests/python/curated/*.py  — stdout vs CPython (gold)
  lib      CPython stdlib .py         — parse/codegen coverage
  test     CPython Lib/test/*.py      — syntax coverage (almost all unittest)
  all      curated run + lib compile + test transpile

Usage:
    python3 tools/aimacro_cpython_runner.py
    python3 tools/aimacro_cpython_runner.py --verbose --output-json results/aimacro_cpython.json
    python3 tools/aimacro_cpython_runner.py --corpus all --output-json results/aimacro_conformance.json

Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import sysconfig
import tempfile
import time
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AIMACRO = ROOT / "aimacro.x"
AILANG = ROOT / "ailang.x"
PY2AIM = ROOT / "tools" / "py2aim.py"
CURATED = ROOT / "tests" / "python" / "curated"
PYTHON = sys.executable

LIB_EXCLUDE_DIRS = {
    "test",
    "tests",
    "site-packages",
    "lib-dynload",
    "ensurepip",
    "idlelib",
    "turtledemo",
    "tkinter",
    "distutils",
    "venv",
    "__pycache__",
}

# Feature tags (test262-style). Files are still attempted unless --skip-unsupported.
SKIP_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("unittest", re.compile(r"\b(?:import unittest|from unittest\b|from test\.support\b|import test\.support)")),
    ("async", re.compile(r"\b(?:async\s+(?:def|for|with)|await\s)")),
    ("generator", re.compile(r"\byield\b")),
    ("decorator", re.compile(r"(?m)^\s*@\w")),
    ("match", re.compile(r"(?m)^\s*match\s+.+:")),
    ("c-api", re.compile(r"\b(?:_testcapi|_testinternalcapi|_ctypes)\b")),
]


def run_cmd(
    cmd: list[str],
    timeout: float,
    cwd: Path | None = None,
    stdin_text: str | None = None,
) -> tuple[int, str, str]:
    try:
        import subprocess

        p = subprocess.run(
            cmd,
            cwd=cwd or ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=stdin_text,
        )
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def stdin_for(src: Path) -> str | None:
    p = src.with_suffix(".stdin")
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return None


def read_source(src: Path) -> tuple[str | None, str | None]:
    raw = src.read_bytes()
    if b"\0" in raw[:4096]:
        return None, "binary"
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(enc), None
        except UnicodeDecodeError:
            continue
    return None, "encoding"


def feature_tags(src_text: str) -> list[str]:
    tags: list[str] = []
    for name, rx in SKIP_RULES:
        if rx.search(src_text):
            tags.append(name)
    return tags


def py2aim_text(src_text: str, dest: Path) -> tuple[int, str]:
    rc, out, err = run_cmd(
        [PYTHON, str(PY2AIM), "--stdin"],
        15,
        stdin_text=src_text,
    )
    if rc != 0:
        return rc, err or out
    dest.write_text(out, encoding="utf-8")
    return 0, ""


def py2aim(src: Path, dest: Path) -> tuple[int, str]:
    rc, out, err = run_cmd([PYTHON, str(PY2AIM), str(src), str(dest)], 10)
    return rc, err or out


def run_cpython(src: Path, timeout: float) -> tuple[int, str]:
    rc, out, err = run_cmd([PYTHON, str(src)], timeout, stdin_text=stdin_for(src))
    return rc, out


def unique_stem(src: Path, root: Path) -> str:
    try:
        rel = src.relative_to(root)
    except ValueError:
        rel = Path(src.name)
    return "__".join(rel.with_suffix("").parts)


def run_aimacro_stage(
    aim: Path,
    timeout: float,
    work: Path,
    stage: str,
    src: Path | None = None,
    stem: str | None = None,
) -> tuple[int, str, str, str]:
    """Returns (rc, stdout, err, fail_stage). fail_stage is transpile|compile|run|''."""
    name = stem or aim.stem
    ailang_out = work / (name + ".ailang")
    bin_out = work / name
    rc, _, err = run_cmd(
        [str(AIMACRO), str(aim), str(ailang_out)], timeout, cwd=ROOT
    )
    if rc != 0:
        return rc, "", f"transpile: {err}", "transpile"
    if stage == "transpile":
        return 0, "", "", ""
    rc, _, err = run_cmd(
        [str(AILANG), str(ailang_out), str(bin_out)], timeout, cwd=ROOT
    )
    if rc != 0:
        return rc, "", f"compile: {err}", "compile"
    if stage == "compile":
        return 0, "", "", ""
    os.chmod(bin_out, 0o755)
    feed = stdin_for(src) if src is not None else stdin_for(aim)
    rc, out, err = run_cmd([str(bin_out)], timeout, cwd=ROOT, stdin_text=feed)
    if rc != 0:
        return rc, out, err, "run"
    return rc, out, err, ""


def run_aimacro(aim: Path, timeout: float, work: Path, src: Path | None = None) -> tuple[int, str, str]:
    rc, out, err, _ = run_aimacro_stage(aim, timeout, work, "run", src)
    return rc, out, err


def default_stdlib() -> Path:
    p = Path(sysconfig.get_path("stdlib"))
    return p


def discover_curated() -> list[Path]:
    if not CURATED.is_dir():
        return []
    return sorted(CURATED.glob("*.py"))


def discover_lib(stdlib: Path) -> list[Path]:
    files: list[Path] = []
    if not stdlib.is_dir():
        return files
    for p in stdlib.rglob("*.py"):
        parts = set(p.relative_to(stdlib).parts)
        if parts & LIB_EXCLUDE_DIRS:
            continue
        if any(part == "__pycache__" for part in p.parts):
            continue
        files.append(p)
    return sorted(files)


def discover_test(stdlib: Path) -> list[Path]:
    test_dir = stdlib / "test"
    if not test_dir.is_dir():
        return []
    files: list[Path] = []
    for p in test_dir.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        files.append(p)
    return sorted(files)


def discover(curated_only: bool, extra: Path | None) -> list[Path]:
    files: list[Path] = []
    if CURATED.is_dir():
        files.extend(sorted(CURATED.glob("*.py")))
    if extra and extra.is_dir():
        files.extend(sorted(extra.rglob("*.py")))
    return files


def summarize(results: list[dict], seconds: float) -> dict:
    ok = sum(1 for r in results if r["status"] == "pass")
    fail = sum(1 for r in results if r["status"] == "fail")
    skip = sum(1 for r in results if r["status"] == "skip")
    by_stage: Counter[str] = Counter()
    skip_reasons: Counter[str] = Counter()
    tags: Counter[str] = Counter()
    in_scope = [r for r in results if not r.get("tags")]
    in_scope_ok = sum(1 for r in in_scope if r["status"] == "pass")
    for r in results:
        if r["status"] == "fail":
            by_stage[r.get("stage") or "unknown"] += 1
        if r["status"] == "skip":
            skip_reasons[r.get("reason") or "unknown"] += 1
        for t in r.get("tags") or []:
            tags[t] += 1
    return {
        "ok": ok,
        "fail": fail,
        "skip": skip,
        "total": len(results),
        "seconds": round(seconds, 3),
        "fail_stages": dict(by_stage),
        "skip_reasons": dict(skip_reasons),
        "feature_tags": dict(tags),
        "in_scope_total": len(in_scope),
        "in_scope_ok": in_scope_ok,
        "in_scope_fail": sum(1 for r in in_scope if r["status"] == "fail"),
        "results": results,
    }


def run_suite(
    files: list[Path],
    stage: str,
    timeout: float,
    work: Path,
    verbose: bool,
    skip_unsupported: bool,
    name_root: Path,
    limit: int,
    compare_stdout: bool,
) -> dict:
    if limit and limit > 0:
        files = files[:limit]
    results: list[dict] = []
    t0 = time.time()
    n = len(files)
    for i, src in enumerate(files, 1):
        try:
            rel = str(src.relative_to(ROOT) if src.is_relative_to(ROOT) else src)
        except AttributeError:
            rel = str(src)
        text, why = read_source(src)
        if text is None:
            rec = {"file": rel, "status": "skip", "reason": why, "tags": []}
            results.append(rec)
            if verbose:
                print(f"SKIP {rel} ({why})")
            continue
        tags = feature_tags(text)
        if skip_unsupported and tags:
            rec = {
                "file": rel,
                "status": "skip",
                "reason": "unsupported:" + ",".join(tags),
                "tags": tags,
            }
            results.append(rec)
            if verbose:
                print(f"SKIP {rel} ({rec['reason']})")
            continue
        stem = unique_stem(src, name_root)
        aim = work / (stem + ".aim")
        if compare_stdout:
            rc_c, py_out = run_cpython(src, timeout)
            if rc_c != 0:
                rec = {
                    "file": rel,
                    "status": "skip",
                    "reason": "cpython non-zero",
                    "tags": tags,
                }
                results.append(rec)
                if verbose:
                    print(f"SKIP {rel} (cpython rc={rc_c})")
                continue
        else:
            py_out = None
        rc, err = py2aim_text(text, aim)
        if rc != 0:
            rec = {
                "file": rel,
                "status": "fail",
                "stage": "py2aim",
                "err": (err or "")[-500:],
                "tags": tags,
            }
            results.append(rec)
            print(f"FAIL {rel} py2aim")
            continue
        rc, am_out, am_err, fail_stage = run_aimacro_stage(
            aim, timeout, work, stage, src, stem=stem
        )
        # drop artifacts so /tmp does not fill
        for leftover in (aim, work / (stem + ".ailang"), work / stem):
            try:
                leftover.unlink()
            except FileNotFoundError:
                pass
        if rc != 0:
            rec = {
                "file": rel,
                "status": "fail",
                "stage": fail_stage or "aimacro",
                "rc": rc,
                "err": (am_err or "")[-500:],
                "tags": tags,
            }
            results.append(rec)
            print(f"FAIL {rel} {rec['stage']} rc={rc}")
            continue
        if compare_stdout and stage == "run":
            if am_out == py_out:
                rec = {"file": rel, "status": "pass", "tags": tags}
                results.append(rec)
                if verbose:
                    print(f"OK   {rel}")
            else:
                rec = {
                    "file": rel,
                    "status": "fail",
                    "stage": "stdout",
                    "python": py_out,
                    "aimacro": am_out,
                    "tags": tags,
                }
                results.append(rec)
                print(f"FAIL {rel} stdout mismatch")
                if verbose:
                    print("  python:", repr(py_out))
                    print("  aimacro:", repr(am_out))
        else:
            rec = {"file": rel, "status": "pass", "tags": tags, "stage_ok": stage}
            results.append(rec)
            if verbose:
                print(f"OK   {rel}")
        if not verbose and (i % 25 == 0 or i == n):
            print(f"  [{i}/{n}] {rel}", flush=True)
    return summarize(results, time.time() - t0)


def format_suite_line(name: str, s: dict) -> str:
    ins = s.get("in_scope_total") or 0
    ins_ok = s.get("in_scope_ok") or 0
    return (
        f"{name:<10} total={s['total']:<5} ok={s['ok']:<5} fail={s['fail']:<5} "
        f"skip={s['skip']:<5} in-scope {ins_ok}/{ins} {s['seconds']:.1f}s"
    )


def format_scorecard(payload: dict) -> str:
    lines = [
        "# AIMacro CPython conformance scorecard",
        "",
        f"Generated **{payload.get('generated')}**. "
        f"Python {payload.get('python')}. "
        f"Stdlib `{payload.get('cpython_lib')}`.",
        "",
        "Not CPython. Target is the 95th percentile of scripts, scored the same "
        "way JS scores test262: curated runtime gold, then a filtered mountain "
        "for parser/codegen coverage. `Lib/test` is unittest + C API — those "
        "files are syntax probes, not a unittest runner.",
        "",
        "## Suites",
        "",
        "| Suite | Stage | Total | Pass | Fail | Skip | In-scope pass | Seconds |",
        "|-------|-------|------:|-----:|-----:|-----:|--------------:|--------:|",
    ]
    for name, s in (payload.get("suites") or {}).items():
        ins = s.get("in_scope_total") or 0
        ins_ok = s.get("in_scope_ok") or 0
        ins_s = f"{ins_ok}/{ins}" if ins else "—"
        lines.append(
            f"| `{name}` | {s.get('stage', '')} | {s['total']} | {s['ok']} | "
            f"{s['fail']} | {s['skip']} | {ins_s} | {s['seconds']} |"
        )
    lines.extend(["", "## Fail stages", ""])
    for name, s in (payload.get("suites") or {}).items():
        fs = s.get("fail_stages") or {}
        if not fs:
            continue
        bits = ", ".join(f"{k}={v}" for k, v in fs.items())
        lines.append(f"- **{name}:** {bits}")
    lines.extend(["", "## Feature tags on attempted files", ""])
    for name, s in (payload.get("suites") or {}).items():
        tags = s.get("feature_tags") or {}
        if not tags:
            continue
        bits = ", ".join(f"{k}={v}" for k, v in tags.items())
        lines.append(f"- **{name}:** {bits}")
    lines.extend(
        [
            "",
            "## How to re-run",
            "",
            "```bash",
            "python3 tools/aimacro_cpython_runner.py --verbose",
            "python3 tools/aimacro_cpython_runner.py --corpus all \\",
            "    --output-json results/aimacro_conformance.json \\",
            "    --output-md AIMacro/CONFORMANCE.md",
            "```",
            "",
            "In-scope = files with no skip-tags (`unittest`, `async`, `generator`, "
            "`decorator`, `match`, `c-api`). Gross pass rate includes tagged files.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--timeout", type=float, default=8.0)
    ap.add_argument("--output-json", type=Path)
    ap.add_argument("--output-md", type=Path)
    ap.add_argument(
        "--cpython",
        type=Path,
        help="CPython stdlib root (Lib/) or extra .py tree in legacy mode",
    )
    ap.add_argument(
        "--corpus",
        choices=["curated", "lib", "test", "all"],
        help="curated (default), CPython Lib, Lib/test, or all three",
    )
    ap.add_argument(
        "--stage",
        choices=["run", "compile", "transpile"],
        help="Override per-corpus default stage",
    )
    ap.add_argument("--limit", type=int, default=0, help="Cap files per suite (smoke)")
    ap.add_argument(
        "--skip-unsupported",
        action="store_true",
        help="Skip files tagged unittest/async/yield/decorator/match/c-api",
    )
    args = ap.parse_args()

    if not AIMACRO.is_file() or not AILANG.is_file():
        print("error: need ./aimacro.x and ./ailang.x", file=sys.stderr)
        return 2

    stdlib = args.cpython if args.cpython else default_stdlib()

    # Legacy: no --corpus means curated (+ optional extra tree via --cpython)
    if args.corpus is None:
        tests = discover(True, args.cpython if args.cpython and not (args.cpython / "abc.py").exists() else None)
        if not tests:
            print("error: no tests under tests/python/curated/", file=sys.stderr)
            return 2
        t0 = time.time()
        with tempfile.TemporaryDirectory(prefix="aimacro_cpython_") as td:
            work = Path(td)
            summary = run_suite(
                tests,
                args.stage or "run",
                args.timeout,
                work,
                args.verbose,
                args.skip_unsupported,
                ROOT,
                args.limit,
                compare_stdout=True,
            )
        print("---")
        print(
            f"cpython-lite ok={summary['ok']} fail={summary['fail']} "
            f"skip={summary['skip']} total={summary['total']} {summary['seconds']:.1f}s"
        )
        payload = summary
        if args.output_json:
            args.output_json.parent.mkdir(parents=True, exist_ok=True)
            args.output_json.write_text(json.dumps(payload, indent=2) + "\n")
            print(f"wrote {args.output_json}")
        return 0 if summary["fail"] == 0 else 1

    suites_spec: list[tuple[str, list[Path], str, bool, Path]] = []
    if args.corpus in ("curated", "all"):
        suites_spec.append(
            ("curated", discover_curated(), args.stage or "run", True, ROOT)
        )
    if args.corpus in ("lib", "all"):
        suites_spec.append(
            ("lib", discover_lib(stdlib), args.stage or "transpile", False, stdlib)
        )
    if args.corpus in ("test", "all"):
        suites_spec.append(
            ("test", discover_test(stdlib), args.stage or "transpile", False, stdlib)
        )

    payload = {
        "generated": date.today().isoformat(),
        "python": sys.version.split()[0],
        "cpython_lib": str(stdlib),
        "skip_unsupported": args.skip_unsupported,
        "suites": {},
    }
    curated_fail = 0
    with tempfile.TemporaryDirectory(prefix="aimacro_conformance_") as td:
        work = Path(td)
        for name, files, stage, compare, name_root in suites_spec:
            print(f"=== {name} stage={stage} files={len(files)} ===", flush=True)
            if not files:
                print(f"  (none under {stdlib})")
                payload["suites"][name] = summarize([], 0.0)
                payload["suites"][name]["stage"] = stage
                continue
            summary = run_suite(
                files,
                stage,
                args.timeout,
                work,
                args.verbose,
                args.skip_unsupported,
                name_root,
                args.limit,
                compare_stdout=compare,
            )
            summary["stage"] = stage
            # JSON for the mountain: drop per-file stdout bodies
            slim = dict(summary)
            slim_results = []
            for r in summary["results"]:
                rr = {k: v for k, v in r.items() if k not in ("python", "aimacro")}
                slim_results.append(rr)
            slim["results"] = slim_results
            payload["suites"][name] = slim
            print("---")
            print(format_suite_line(name, summary), flush=True)
            if name == "curated":
                curated_fail = summary["fail"]

    print("=== scorecard ===")
    for name, s in payload["suites"].items():
        print(format_suite_line(name, s))

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"wrote {args.output_json}")
    if args.output_md:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(format_scorecard(payload))
        print(f"wrote {args.output_md}")
    return 0 if curated_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
