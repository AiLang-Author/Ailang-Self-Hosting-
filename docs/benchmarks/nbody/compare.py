#!/usr/bin/env python3
"""Require the same n-body energy bits at each step count."""
import sys

def load(path):
    rows = {}
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) >= 8 and p[0] == "NBODY" and p[2] == "e0" and p[4] == "e1":
                rows[int(p[1])] = (int(p[3]), int(p[5]), int(p[7]))
    return rows

cpp = load("cpp.txt")
ail = load("ailang.txt")
failed = 0
if not cpp or not ail:
    print("missing row")
    sys.exit(1)
for n in sorted(ail):
    if n not in cpp:
        print("missing cpp", n)
        failed = 1
        continue
    print("N", n, "e0", ail[n][0], "e1", ail[n][1])
    if cpp[n][0] != ail[n][0] or cpp[n][1] != ail[n][1]:
        print("DIFFER cpp", cpp[n][0], cpp[n][1])
        failed = 1
    else:
        print("match")
sys.exit(failed)
