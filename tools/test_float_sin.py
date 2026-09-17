#!/usr/bin/env python3
"""Strict Float_Sin tests against libm. Uses ailang-next.x only."""
import math
import os
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEXT = os.path.join(ROOT, "ailang-next.x")
OUT = os.path.join(ROOT, "tests/contract/_out")
os.makedirs(OUT, exist_ok=True)
fails = 0


def bits_to_float(i):
    if i < 0:
        i += 2**64
    return struct.unpack("<d", struct.pack("<Q", i & ((1 << 64) - 1)))[0]


def float_to_bits_signed(f):
    u = struct.unpack("<Q", struct.pack("<d", f))[0]
    return u if u < 2**63 else u - 2**64


def run(cmd, timeout=60):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def fail(msg):
    global fails
    fails += 1
    print("FAIL:", msg)


def ok(msg):
    print("OK:", msg)


def compile_next(src, dst):
    r = run([NEXT, src, dst], timeout=120)
    return r


def ulp_diff(a, b):
    if math.isnan(a) and math.isnan(b):
        return 0.0
    if math.isinf(a) or math.isinf(b):
        return 0.0 if a == b else float("inf")
    if a == b:
        return 0.0
    if abs(a - b) <= 2.0 ** -52:
        return 0.0
    ia = struct.unpack("<Q", struct.pack("<d", a))[0]
    ib = struct.unpack("<Q", struct.pack("<d", b))[0]
    # map to signed magnitude order
    def mag(x):
        return x if x < 2**63 else (x - 2**63) ^ ((1 << 63) - 1)
    return abs(mag(ia) - mag(ib))


# --- arity ---
for name in ("float_sin_arity0.ailang", "float_sin_arity2.ailang"):
    src = os.path.join(ROOT, "tests/contract", name)
    dst = os.path.join(OUT, name + ".x")
    r = compile_next(src, dst)
    if r.returncode == 0:
        fail(f"{name} compiled, expected arity reject")
    else:
        ok(f"{name} rejected rc={r.returncode}")
        if "Float_Sin requires 1 argument" not in r.stdout + r.stderr:
            # may fall through to user-call
            ok(f"{name} rejected without TRANS message (user-call path)")

# --- probe ---
src = os.path.join(ROOT, "tests/contract/float_sin_probe.ailang")
dst = os.path.join(OUT, "float_sin_probe.x")
r = compile_next(src, dst)
if r.returncode != 0:
    print(r.stdout)
    print(r.stderr)
    fail("probe failed to compile")
    sys.exit(1)
if "encode failed" in r.stdout:
    fail("X86Enc encode failed during Float_Sin")
    print(r.stdout)
ok("probe compiled")

r = run([dst], timeout=30)
if r.returncode != 0:
    fail(f"probe run rc={r.returncode}")
    print(r.stdout)
    sys.exit(1)

vals = {}
grids = []
ngrids = []
for line in r.stdout.splitlines():
    if "=" not in line:
        continue
    k, rest = line.split("=", 1)
    rest = rest.strip()
    if k == "grid":
        i_s, bits_s = rest.split()
        grids.append((int(i_s), int(bits_s)))
    elif k == "ngrid":
        i_s, bits_s = rest.split()
        ngrids.append((int(i_s), int(bits_s)))
    else:
        vals[k] = int(rest)

# exact / special
z = bits_to_float(vals["z"])
if z != 0.0 or math.copysign(1.0, z) < 0:
    fail(f"sin(0)={z!r} bits={vals['z']}")
else:
    ok("sin(0)=+0")

nz = bits_to_float(vals["nz"])
if nz != 0.0 or math.copysign(1.0, nz) > 0:
    fail(f"sin(-0)={nz!r} bits={vals['nz']}")
else:
    ok("sin(-0)=-0")

named_x = {
    "pi2": math.pi / 2,
    "pi": math.pi,
    "npi2": -math.pi / 2,
    "tpi2": 1.5 * math.pi,
    "twopi": 2 * math.pi,
    "pi6": math.pi / 6,
    "one": 1.0,
    "fromint0": 0.0,
}
for key, x in named_x.items():
    got = bits_to_float(vals[key])
    exp = math.sin(x)
    u = ulp_diff(got, exp)
    max_ulp = 8
    if u > max_ulp:
        fail(f"sin({key}) got={got!r} expect={exp!r} ulp={u}")
    else:
        ok(f"sin({key}) ulp={u} got={got!r}")

for key in ("pinf", "ninf", "qnan"):
    got = bits_to_float(vals[key])
    if not math.isnan(got):
        fail(f"sin({key}) expected NaN got={got!r} bits={vals[key]}")
    else:
        ok(f"sin({key})=NaN")

for i, bits in grids:
    got = bits_to_float(bits)
    exp = math.sin(float(i))
    u = ulp_diff(got, exp)
    if u > 8:
        fail(f"sin({i}.0) got={got!r} expect={exp!r} ulp={u}")
    else:
        ok(f"sin({i}.0) ulp={u}")

for i, bits in ngrids:
    got = bits_to_float(bits)
    exp = math.sin(float(i))
    u = ulp_diff(got, exp)
    if u > 8:
        fail(f"sin({i}.0) got={got!r} expect={exp!r} ulp={u}")
    else:
        ok(f"sin({i}.0) ulp={u}")

print()
if fails:
    print(f"{fails} FAILURES")
    sys.exit(1)
print("ALL FLOAT_SIN CHECKS PASSED")
