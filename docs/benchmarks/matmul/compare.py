#!/usr/bin/env python3
"""Require the same f64 sum bits and the same xor of every C element."""
import sys

def load(path):
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) >= 8 and p[0] == "ROW" and p[2] == "bits" and p[4] == "mix":
                return int(p[1]), int(p[3]), int(p[5]), int(p[7])
    return None

cpp = load("cpp.txt")
ail = load("ailang.txt")
failed = 0
if cpp is None or ail is None:
    print("missing row")
    sys.exit(1)
print("N", ail[0], "bits", ail[1], "mix", ail[2])
if cpp[1] != ail[1] or cpp[2] != ail[2]:
    print("DIFFER cpp bits", cpp[1], "mix", cpp[2])
    failed = 1
else:
    print("match")
sys.exit(failed)
