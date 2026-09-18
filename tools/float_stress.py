#!/usr/bin/env python3
"""Compile+run Ailang float builtins vs Python/libm. Exit 1 on mismatch."""
import math, os, struct, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CC = os.path.join(ROOT, "ailang-next.x")
if not os.path.isfile(CC):
    CC = os.path.join(ROOT, "ailang.x")

def bits(f):
    if isinstance(f, int):
        return f
    u = struct.unpack("<Q", struct.pack("<d", float(f)))[0]
    return u if u < 2**63 else u - 2**64

def from_bits(i):
    i = int(i)
    if i < 0:
        i += 2**64
    return struct.unpack("<d", struct.pack("<Q", i & ((1 << 64) - 1)))[0]

PINF = float("inf")
NINF = float("-inf")
NAN = float("nan")
N0 = -0.0

SPECIALS = [0.0, N0, 1.0, -1.0, 2.0, -2.0, 0.5, -0.5, math.pi, -math.pi,
            math.e, 1e-300, -1e-300, 1e300, -1e300, PINF, NINF, NAN]
GRID = SPECIALS + [n * 0.25 for n in range(-16, 17)] + [
    math.pi / 2, math.pi / 4, math.pi / 6, 3 * math.pi / 2,
    0.1, 0.9, 1.5, 10.0, -10.0, 100.0, math.sqrt(2),
]

def is_nan(x):
    return math.isnan(x)

def close(a, b, rel=1e-12, abs_eps=1e-15):
    if is_nan(a) and is_nan(b):
        return True
    if math.isinf(a) or math.isinf(b):
        return a == b
    if a == b:
        return True
    if abs(a - b) <= abs_eps:
        return True
    den = max(abs(a), abs(b), 1e-300)
    return abs(a - b) / den <= rel

cases = []  # (name, expr_ailang, expected_kind, expected)

def add_u(name, call, expect):
    cases.append((name, call, "i" if isinstance(expect, int) and expect in (0, 1) and name.startswith(("isnan", "isinf", "sbit")) else "f", expect))

# predicates + unary
for i, x in enumerate(SPECIALS):
    xb = bits(x)
    add_u(f"isnan_{i}", f"Float_IsNan({xb})", 1 if is_nan(x) else 0)
    add_u(f"isinf_{i}", f"Float_IsInf({xb})", 1 if math.isinf(x) else 0)
    add_u(f"sbit_{i}", f"Float_SignBit({xb})", 1 if (math.copysign(1.0, x) < 0 or (x == 0 and math.copysign(1.0, x) < 0)) else 0)
    if not is_nan(x):
        add_u(f"neg_{i}", f"Float_Neg({xb})", -x if not math.isinf(x) else (-x))
        add_u(f"abs_{i}", f"Float_Abs({xb})", abs(x) if not math.isinf(x) else abs(x))

# -0 signbit
add_u("sbit_n0", f"Float_SignBit({bits(N0)})", 1)
add_u("sbit_p0", f"Float_SignBit({bits(0.0)})", 0)

# copysign grid
for i, mag in enumerate([1.0, -1.0, 0.0, N0, PINF, 2.5]):
    for j, sgn in enumerate([1.0, -1.0, 0.0, N0, NINF]):
        add_u(f"cs_{i}_{j}", f"Float_Copysign({bits(mag)}, {bits(sgn)})", math.copysign(mag if not is_nan(mag) else 1.0, sgn))

# mod
for i, x in enumerate([0.0, 1.0, -1.0, 5.5, -5.5, 10.0, math.pi, 100.0]):
    for j, y in enumerate([1.0, 2.0, -2.0, 3.0, 0.5, math.pi]):
        add_u(f"mod_{i}_{j}", f"Float_Mod({bits(x)}, {bits(y)})", math.fmod(x, y))
add_u("mod_y0", f"Float_Mod({bits(1.0)}, {bits(0.0)})", NAN)

# arith / trans on a denser finite grid
FIN = [x for x in GRID if not is_nan(x) and not math.isinf(x) and abs(x) < 1e8]
for i, x in enumerate(FIN):
    if x >= 0:
        add_u(f"sqrt_{i}", f"Float_Sqrt({bits(x)})", math.sqrt(x))
    if -20 < x < 20:
        add_u(f"sin_{i}", f"Float_Sin({bits(x)})", math.sin(x))
        add_u(f"cos_{i}", f"Float_Cos({bits(x)})", math.cos(x))
        add_u(f"tan_{i}", f"Float_Tan({bits(x)})", math.tan(x))
    if 0.05 < x < 50:
        add_u(f"log_{i}", f"Float_Log({bits(x)})", math.log(x))
    if -5 < x < 5:
        add_u(f"exp_{i}", f"Float_Exp({bits(x)})", math.exp(x))
    add_u(f"add1_{i}", f"Float_Add({bits(x)}, {bits(1.0)})", x + 1.0)
    add_u(f"mul2_{i}", f"Float_Mul({bits(x)}, {bits(2.0)})", x * 2.0)

# atan2 / pow
for y in [-2.0, -1.0, 0.0, 1.0, 2.0, math.pi]:
    for x in [-2.0, -1.0, 0.0, 1.0, 2.0]:
        add_u(f"atan2_{bits(y)}_{bits(x)}", f"Float_Atan2({bits(y)}, {bits(x)})", math.atan2(y, x))
        if x > 0 and abs(y) < 8:
            add_u(f"pow_{bits(x)}_{bits(y)}", f"Float_Pow({bits(x)}, {bits(y)})", math.pow(x, y))

print(f"cases {len(cases)}", file=sys.stderr)

lines = [
    "SubRoutine.Main {\n",
]
for i, (name, call, kind, exp) in enumerate(cases):
    lines.append(f"    r{i} = {call}\n")
    lines.append(f"    PrintNumber(r{i})\n")
    lines.append("    PrintMessage(\"\\n\")\n")
lines.append("    ProcessExit(0)\n}\n\nRunTask(Main)\n")
src = "".join(lines)

td = tempfile.mkdtemp(prefix="fstress_")
srcp = os.path.join(td, "s.ailang")
binp = os.path.join(td, "s.x")
open(srcp, "w").write(src)
r = subprocess.run([CC, srcp, binp], cwd=ROOT, capture_output=True, text=True)
if r.returncode != 0:
    print(r.stdout[-2000:])
    print(r.stderr[-2000:])
    sys.exit("compile failed")
out = subprocess.check_output([binp], text=True)
got_lines = [ln for ln in out.splitlines() if ln.strip() != ""]
if len(got_lines) != len(cases):
    print(f"output lines {len(got_lines)} != cases {len(cases)}")
    sys.exit(1)

fail = 0
ulp_lim_trans = 4096  # exp/log/pow/trig not correctly rounded
ulp_lim_core = 4
for i, ((name, call, kind, exp), raw) in enumerate(zip(cases, got_lines)):
    gi = int(raw)
    if name.startswith(("isnan", "isinf", "sbit")):
        if gi != int(exp):
            print(f"FAIL {name} got {gi} expect {int(exp)}")
            fail += 1
        continue
    gf = from_bits(gi)
    ef = exp
    fam = name.split("_")[0]
    rel, aeps = 1e-15, 1e-18
    if fam in ("sin", "cos", "exp", "pow"):
        rel, aeps = 1e-12, 1e-14
    if fam in ("log", "atan2", "tan"):
        rel, aeps = 1e-6, 1e-12
    if fam == "mod":
        rel, aeps = 1e-12, 1e-15
    if not close(gf, ef, rel, aeps):
        print(f"FAIL {name} got {gf!r} expect {ef!r} bits={gi}")
        fail += 1

print(f"PASS {len(cases) - fail}/{len(cases)}  FAIL {fail}")
sys.exit(1 if fail else 0)
