#!/usr/bin/env python3
"""Compare a rendered synth sine against a calculated 440 Hz tone.

The engine file is stereo s16 at 48 kHz. This checks the left channel
after the short attack: the strongest frequency, and that a pure sine
of that length correlates with it.
"""
import math
import struct
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/synth_sine_440.raw"
RATE = 48000
TARGET = 440.0

raw = open(PATH, "rb").read()
n = len(raw) // 4
left = [struct.unpack_from("<h", raw, i * 4)[0] for i in range(n)]
# skip 20 ms of attack
a = int(0.02 * RATE)
x = left[a:]
if len(x) < RATE // 5:
    print("FAIL short file", len(left))
    sys.exit(1)

prev = 1 if x[0] >= 0 else -1
cross = []
for i, v in enumerate(x[1:], 1):
    s = 1 if v >= 0 else -1
    if prev < 0 and s > 0:
        cross.append(i)
    prev = s
if len(cross) < 8:
    print("FAIL too few cycles", len(cross))
    sys.exit(1)
periods = [cross[i + 1] - cross[i] for i in range(len(cross) - 1)]
avg = sum(periods) / len(periods)
freq = RATE / avg
w = 2 * math.pi * freq / RATE
s1 = s2 = s3 = s4 = 0.0
for i, v in enumerate(x):
    c = math.cos(w * i)
    sn = math.sin(w * i)
    s1 += v * c
    s2 += v * sn
    s3 += c * c
    s4 += sn * sn
A = s1 / s3
B = s2 / s4
err = sig = 0.0
for i, v in enumerate(x):
    y = A * math.cos(w * i) + B * math.sin(w * i)
    err += (v - y) ** 2
    sig += v * v
fit = 1 - err / sig if sig else 0
print(f"samples={len(x)} freq={freq:.2f} Hz sine_fit={fit:.4f}")
if abs(freq - TARGET) > 1.0 or fit < 0.98:
    print("FAIL sine is not a clean 440 Hz tone")
    sys.exit(1)
print("PASS sine")
