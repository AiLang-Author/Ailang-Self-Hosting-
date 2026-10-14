#!/usr/bin/env python3
"""Check square, pulse, saw, and triangle renders against their harmonic shape.

Each file is stereo s16, 48 kHz. Left channel, after 20 ms of attack.
A band-limited square is mostly odd harmonics (3rd near 1/3).
A 25% pulse has a strong 2nd harmonic. A saw falls off as 1/n.
A triangle is almost a sine, with a weak 3rd.
"""
import math
import struct
import sys

RATE = 48000
TARGET = 440.0


def load(path):
    raw = open(path, "rb").read()
    n = len(raw) // 4
    left = [struct.unpack_from("<h", raw, i * 4)[0] for i in range(n)]
    return left[int(0.02 * RATE):]


def tone(x):
    prev = 1 if x[0] >= 0 else -1
    cross = []
    for i, v in enumerate(x[1:], 1):
        s = 1 if v >= 0 else -1
        if prev < 0 and s > 0:
            cross.append(i)
        prev = s
    periods = [cross[i + 1] - cross[i] for i in range(len(cross) - 1)]
    avg = sum(periods) / len(periods)
    return RATE / avg


def amp_at(x, freq):
    w = 2 * math.pi * freq / RATE
    s1 = s2 = s3 = s4 = 0.0
    for i, v in enumerate(x):
        c = math.cos(w * i)
        sn = math.sin(w * i)
        s1 += v * c
        s2 += v * sn
        s3 += c * c
        s4 += sn * sn
    a = s1 / s3
    b = s2 / s4
    return math.hypot(a, b)


def main():
    fail = 0
    specs = [
        ("square", "/tmp/synth_square_440.raw", {"h2": (0.0, 0.08), "h3": (0.22, 0.45)}),
        ("pulse25", "/tmp/synth_pulse_440.raw", {"h2": (0.35, 0.80), "h3": (0.15, 0.55)}),
        ("saw", "/tmp/synth_saw_440.raw", {"h2": (0.35, 0.65), "h3": (0.22, 0.45)}),
        ("triangle", "/tmp/synth_tri_440.raw", {"h2": (0.0, 0.08), "h3": (0.04, 0.20)}),
    ]
    for name, path, bounds in specs:
        x = load(path)
        freq = tone(x)
        h1 = amp_at(x, freq)
        h2 = amp_at(x, freq * 2) / h1
        h3 = amp_at(x, freq * 3) / h1
        peak = max(abs(v) for v in x)
        ok = abs(freq - TARGET) <= 1.0 and peak > 8000
        for key, (lo, hi) in bounds.items():
            val = h2 if key == "h2" else h3
            if not (lo <= val <= hi):
                ok = False
        mark = "PASS" if ok else "FAIL"
        if not ok:
            fail += 1
        print(f"{mark} {name} freq={freq:.2f} h2={h2:.3f} h3={h3:.3f} peak={peak}")
    if fail:
        print(f"FAIL {fail}")
        sys.exit(1)
    print("PASS waves")


if __name__ == "__main__":
    main()
