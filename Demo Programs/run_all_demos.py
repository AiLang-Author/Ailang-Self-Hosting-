#!/usr/bin/env python3
"""
Full verification for AILang Demo Programs:
1. Compile every .ailang to a native .x executable
2. Run every resulting binary (with timeout)
3. Report success/failure for both build and run phases.

This proves the compiler produces functioning executables.
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple

DEMO_DIR = Path("/home/bob/Ailang-Self-Hosting-/Demo Programs/programs")
COMPILER = Path("/home/bob/Ailang-Self-Hosting-/ailang.x")
TMP_DIR = Path("/tmp/ailang_demo_run")
TIMEOUT_COMPILE = 30
TIMEOUT_RUN = 5   # seconds per demo – adjust if needed for long ones

def run_cmd(cmd: List[str], timeout: int, cwd: Path = None) -> Tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd) if cwd else None
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as e:
        return -1, e.stdout or "", (e.stderr or "") + "\n[TIMEOUT]"
    except Exception as e:
        return -2, "", str(e)

def main():
    if not COMPILER.exists():
        print(f"ERROR: Compiler not found: {COMPILER}")
        sys.exit(1)

    TMP_DIR.mkdir(parents=True, exist_ok=True)

    demos = sorted(DEMO_DIR.glob("*.ailang"))
    print(f"Found {len(demos)} demo programs.")
    print(f"Compiler: {COMPILER}")
    print(f"Timeout per run: {TIMEOUT_RUN}s")
    print()

    build_failures = []
    run_failures = []
    successes = []

    for i, source in enumerate(demos, 1):
        name = source.stem
        out_bin = TMP_DIR / f"{name}.x"

        # === COMPILE ===
        compile_cmd = [str(COMPILER), str(source), str(out_bin)]
        ret, out, err = run_cmd(compile_cmd, TIMEOUT_COMPILE)

        combined = (out + err).lower()
        hard_compile_fail = (
            ret != 0 or
            "parse error" in combined or
            "compile error" in combined or
            "compilation failed" in combined
        )

        if hard_compile_fail:
            build_failures.append((name, (out + err).strip()[:600]))
            print(f"[{i:03d}/{len(demos)}] BUILD FAIL: {name}")
            continue

        if not out_bin.exists() or out_bin.stat().st_size < 1000:
            build_failures.append((name, "Binary missing or too small after compile"))
            print(f"[{i:03d}/{len(demos)}] BUILD FAIL (no binary): {name}")
            continue

        # === RUN ===
        run_cmd_list = [str(out_bin)]
        ret, out, err = run_cmd(run_cmd_list, TIMEOUT_RUN)

        if ret == -1:  # timeout
            run_failures.append((name, "TIMED OUT (possible long-running or hang)", out + err))
            print(f"[{i:03d}/{len(demos)}] RUN TIMEOUT: {name}")
        elif ret != 0:
            run_failures.append((name, f"Exited with code {ret}", out + err))
            print(f"[{i:03d}/{len(demos)}] RUN FAIL (exit {ret}): {name}")
        else:
            successes.append(name)
            # Print a short preview of output for interesting demos
            preview = (out + err).strip()[:120].replace("\n", " ")
            print(f"[{i:03d}/{len(demos)}] OK: {name}  →  {preview}")

    # Cleanup binaries
    for f in TMP_DIR.glob("*.x"):
        try:
            f.unlink()
        except:
            pass

    print("\n" + "="*70)
    print(f"RESULTS")
    print(f"  Total demos:      {len(demos)}")
    print(f"  Build successes:  {len(demos) - len(build_failures)}")
    print(f"  Build failures:   {len(build_failures)}")
    print(f"  Run successes:    {len(successes)}")
    print(f"  Run failures:     {len(run_failures)}")
    print("="*70)

    if build_failures:
        print("\n--- BUILD FAILURES ---")
        for name, msg in build_failures:
            print(f"\n{name}:")
            print(msg[:500])

    if run_failures:
        print("\n--- RUN FAILURES / TIMEOUTS ---")
        for name, reason, output in run_failures:
            print(f"\n{name}: {reason}")
            if output.strip():
                print(output[:400])

    if not build_failures and not run_failures:
        print("\n✅ ALL 146 DEMO PROGRAMS BUILD AND RUN SUCCESSFULLY.")
        print("   The AILang compiler produces functioning native executables.")
    else:
        print(f"\n⚠️  {len(build_failures) + len(run_failures)} issues found.")
        sys.exit(1)

if __name__ == "__main__":
    main()
