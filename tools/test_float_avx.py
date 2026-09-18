#!/usr/bin/env python3
"""AVX-module Assemble smoke. Baseline ISA is SSE2; Floor/FMA only run if CPU has flags."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEXT = os.path.join(ROOT, "ailang-next.x")
OUT = os.path.join(ROOT, "tests/contract/_out")
os.makedirs(OUT, exist_ok=True)
fails = 0


def run(cmd, timeout=60):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def fail(msg):
    global fails
    fails += 1
    print("FAIL:", msg)


def ok(msg):
    print("OK:", msg)


def cpu_flags():
    try:
        t = open("/proc/cpuinfo").read()
    except OSError:
        return set()
    for line in t.splitlines():
        if line.startswith("flags"):
            return set(line.split(":", 1)[1].split())
    return set()


flags = cpu_flags()
print("cpu flags: sse2=%s sse4_1=%s fma=%s avx=%s" % (
    "sse2" in flags, "sse4_1" in flags, "fma" in flags, "avx" in flags))

src = os.path.join(ROOT, "tests/contract/float_avx_probe.ailang")
dst = os.path.join(OUT, "float_avx_probe.x")
r = run([NEXT, src, dst], timeout=120)
log = r.stdout + r.stderr
if "Unknown instruction" in log:
    fail("X86Enc unknown during AVX probe compile")
    print(log)
if r.returncode != 0:
    fail("AVX probe failed to compile")
    print(log)
    sys.exit(1)
ok("AVX probe compiled")

if "sse4_1" not in flags:
    print("SKIP run: no sse4_1 (compiler baseline is SSE2; Floor/Ceil/Trunc not dispatched yet)")
else:
    r = run([dst], timeout=30)
    if r.returncode != 0:
        fail("AVX probe run rc=%s" % r.returncode)
        print(r.stdout)
    else:
        vals = {}
        for line in r.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                vals[k] = v.strip()
        if vals.get("floor") != "3":
            fail("floor 3.5 -> %s" % vals.get("floor"))
        else:
            ok("Float_Floor 3.5 -> 3")
        if vals.get("ceil") != "4":
            fail("ceil 3.5 -> %s" % vals.get("ceil"))
        else:
            ok("Float_Ceil 3.5 -> 4")
        if vals.get("trunc") != "3":
            fail("trunc 3.5 -> %s" % vals.get("trunc"))
        else:
            ok("Float_Trunc 3.5 -> 3")
        if "fma" not in flags:
            print("SKIP fma check: no fma flag")
        elif vals.get("fma") != "10":
            fail("FMA 2*3+4 -> %s" % vals.get("fma"))
        else:
            ok("Float_FMA 2*3+4 -> 10")

print()
if fails:
    print("%d FAILURES" % fails)
    sys.exit(1)
print("ALL FLOAT_AVX CHECKS PASSED")
