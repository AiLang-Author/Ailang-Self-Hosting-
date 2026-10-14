#!/usr/bin/env python3
"""Check envelope, filter, delay, LFO, drive, and sub against a 440 Hz sine."""
import math
import struct
import sys

RATE = 48000


def load(path):
    raw = open(path, "rb").read()
    n = len(raw) // 4
    return [struct.unpack_from("<h", raw, i * 4)[0] for i in range(n)]


def env_at(x, t, win=0.01):
    a = int(t * RATE)
    b = a + int(win * RATE)
    if b > len(x):
        b = len(x)
    if a >= b:
        return 0
    seg = x[a:b]
    return max(abs(v) for v in seg)


def amp_at(x, freq, t0=0.05, t1=0.25):
    a = int(t0 * RATE)
    b = int(t1 * RATE)
    seg = x[a:b]
    w = 2 * math.pi * freq / RATE
    s1 = s2 = s3 = s4 = 0.0
    for i, v in enumerate(seg):
        c = math.cos(w * i)
        sn = math.sin(w * i)
        s1 += v * c
        s2 += v * sn
        s3 += c * c
        s4 += sn * sn
    return math.hypot(s1 / s3, s2 / s4)


def sine_fit(x, t0, t1):
    seg = x[int(t0 * RATE):int(t1 * RATE)]
    # frequency from rising crossings
    prev = 1 if seg[0] >= 0 else -1
    cross = []
    for i, v in enumerate(seg[1:], 1):
        s = 1 if v >= 0 else -1
        if prev < 0 and s > 0:
            cross.append(i)
        prev = s
    periods = [cross[i + 1] - cross[i] for i in range(len(cross) - 1)]
    freq = RATE / (sum(periods) / len(periods))
    w = 2 * math.pi * freq / RATE
    s1 = s2 = s3 = s4 = 0.0
    for i, v in enumerate(seg):
        c = math.cos(w * i)
        sn = math.sin(w * i)
        s1 += v * c
        s2 += v * sn
        s3 += c * c
        s4 += sn * sn
    A = s1 / s3
    B = s2 / s4
    err = sig = 0.0
    for i, v in enumerate(seg):
        y = A * math.cos(w * i) + B * math.sin(w * i)
        err += (v - y) ** 2
        sig += v * v
    return 1 - err / sig if sig else 0


def main():
    fail = 0

    def check(name, ok, detail):
        nonlocal fail
        if not ok:
            fail += 1
        print(("PASS " if ok else "FAIL ") + name + " " + detail)

    env = load("/tmp/mod_env.raw")
    full = env_at(env, 0.30)
    early = env_at(env, 0.04)
    late = env_at(env, 0.12)
    after = env_at(env, 0.50 + 0.05)
    gone = env_at(env, 0.50 + 0.25)
    check("attack 100ms", early < full * 0.55 and late > full * 0.85,
          f"early={early} at120ms={late} full={full}")
    check("release 200ms", after > full * 0.45 and gone < full * 0.15,
          f"at50ms={after} at250ms={gone}")

    long = load("/tmp/mod_env_long.raw")
    hold = env_at(long, 0.08)
    mid = env_at(long, 0.10 + 1.00)
    check("release 2000ms still up at 1s", mid > hold * 0.40,
          f"hold={hold} at1s={mid} ratio={mid / hold if hold else 0:.2f}")

    filt = load("/tmp/mod_filt.raw")
    open_ref = amp_at(env, 440)
    closed = amp_at(filt, 440)
    check("low cutoff attenuates", closed < open_ref * 0.35,
          f"open={open_ref:.0f} closed={closed:.0f}")

    delay = load("/tmp/mod_delay.raw")
    dry = env_at(delay, 0.02)
    gap = env_at(delay, 0.07)
    echo = env_at(delay, 0.12)
    check("delay 100ms echo", dry > 5000 and gap < dry * 0.2 and echo > dry * 0.4,
          f"dry={dry} gap={gap} echo={echo}")

    lfo = load("/tmp/mod_lfo.raw")
    wins = [env_at(lfo, 0.05 + i * 0.03, 0.02) for i in range(12)]
    span = max(wins) - min(wins)
    check("LFO loudness moves", span > max(wins) * 0.4,
          f"min={min(wins)} max={max(wins)}")

    drive = load("/tmp/mod_drive.raw")
    fit = sine_fit(drive, 0.05, 0.25)
    check("drive bends the sine", fit < 0.98, f"sine_fit={fit:.3f}")

    sub = load("/tmp/mod_sub.raw")
    a440 = amp_at(sub, 440)
    a220 = amp_at(sub, 220)
    check("sub adds octave down", a220 > a440 * 0.25,
          f"440={a440:.0f} 220={a220:.0f}")

    if fail:
        print(f"FAIL {fail}")
        sys.exit(1)
    print("PASS modifiers")


if __name__ == "__main__":
    main()
