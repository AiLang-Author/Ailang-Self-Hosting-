#!/usr/bin/env python3
"""IEEE-754 double oracle for the f64 shape kernels. Prints ROW-like bits."""
import struct

PI = struct.unpack("<d", struct.pack("<Q", 4614256656552045848))[0]
HALF = 0.5
ONE = 1.0


def lcg_shapes(n):
    state = 1
    out = []
    for _ in range(n):
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        typ = (state >> 28) & 3
        w = float(1 + ((state >> 16) & 15))
        h = float(1 + ((state >> 8) & 15))
        if typ == 0 or typ == 3:
            h = w
        out.append((typ, w, h))
    return out


def bits(x):
    return struct.unpack("<Q", struct.pack("<d", x))[0]


def area_if(typ, w, h):
    if typ == 0:
        return w * w
    if typ == 1:
        return w * h
    if typ == 2:
        return (HALF * w) * h
    return (PI * w) * w


def area_table(typ, w, h):
    coeff = (1.0, 1.0, HALF, PI)[typ]
    return (coeff * w) * h


def corner_call(typ, w, h):
    corners = (4, 4, 3, 0)[typ]
    weight = ONE / float(corners + 1)
    return weight * area_if(typ, w, h)


def corner_table(typ, w, h):
    coeff = (ONE / 5.0, ONE / 5.0, HALF / 4.0, PI)[typ]
    return (coeff * w) * h


def fold(shapes, reps, fn):
    # One pass sum, then add those pass sums. Same association as the harness.
    acc = 0.0
    for _ in range(reps):
        pass_sum = 0.0
        for typ, w, h in shapes:
            pass_sum = pass_sum + fn(typ, w, h)
        acc = acc + pass_sum
    return acc


def main():
    shapes = lcg_shapes(4096)
    t, w, h = shapes[0]
    print("FIRST %d %d %d" % (t, int(w), int(h)))
    jobs = [
        (256, 200, "area-if", area_if),
        (256, 200, "area-table", area_table),
        (256, 200, "corner-call", corner_call),
        (256, 200, "corner-table", corner_table),
        (4096, 200, "area-if", area_if),
        (4096, 200, "area-table", area_table),
        (4096, 200, "corner-call", corner_call),
        (4096, 200, "corner-table", corner_table),
        (4096, 1, "area-if", area_if),
        (4096, 1, "area-table", area_table),
        (4096, 1, "corner-call", corner_call),
        (4096, 1, "corner-table", corner_table),
    ]
    cache = {}
    for n, reps, name, fn in jobs:
        key = (n, reps, name)
        if key not in cache:
            cache[key] = bits(fold(shapes[:n], reps, fn))
        print("ORACLE %d %d %s %d" % (n, reps, name, cache[key]))


if __name__ == "__main__":
    main()
