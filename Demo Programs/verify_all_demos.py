#!/usr/bin/env python3
"""
Verify that all AILang demo programs compile and (where possible) run successfully.
"""

import os
import subprocess
import sys
from pathlib import Path

DEMO_DIR = Path("/home/bob/Ailang-Self-Hosting-/Demo Programs/programs")
COMPILER = Path("/home/bob/Ailang-Self-Hosting-/ailang.x")
TMP_OUT = Path("/tmp/ailang_demo_verify")

def main():
    if not COMPILER.exists():
        print("ERROR: Compiler not found at", COMPILER)
        sys.exit(1)

    TMP_OUT.mkdir(parents=True, exist_ok=True)

    demos = sorted(DEMO_DIR.glob("*.ailang"))
    print(f"Found {len(demos)} demo programs.\n")

    failures = []
    successes = []

    for demo in demos:
        out_name = TMP_OUT / (demo.stem + ".x")
        cmd = [str(COMPILER), str(demo), str(out_name)]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            stdout = result.stdout + result.stderr

            stdout_lower = stdout.lower()
            hard_fail = (result.returncode != 0 or
                         "parse error" in stdout_lower or
                         "compile error" in stdout_lower or
                         "compilation failed" in stdout_lower)
            if hard_fail:
                failures.append((demo.name, stdout.strip()[:800]))
            else:
                successes.append(demo.name)
                # Optional: try to run it briefly (many demos are interactive or long)
                # For now we just check that it produced a valid executable
                if out_name.exists() and out_name.stat().st_size > 1000:
                    pass  # looks like a real binary
                else:
                    failures.append((demo.name, "Compiled but output binary too small or missing"))
        except subprocess.TimeoutExpired:
            failures.append((demo.name, "Compilation timed out (>30s)"))
        except Exception as e:
            failures.append((demo.name, str(e)))

    print(f"\n=== RESULTS ===")
    print(f"Successes: {len(successes)}")
    print(f"Failures:  {len(failures)}")

    if failures:
        print("\n--- FAILURES ---")
        for name, err in failures:
            print(f"\n{name}:")
            print(err[:600])
            print("---")

    # Cleanup
    for f in TMP_OUT.glob("*.x"):
        f.unlink(missing_ok=True)

    if failures:
        print(f"\n❌ {len(failures)} demos failed to build or produce valid output.")
        sys.exit(1)
    else:
        print("\n✅ All demos built successfully!")

if __name__ == "__main__":
    main()
