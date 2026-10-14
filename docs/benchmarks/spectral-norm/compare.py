#!/usr/bin/env python3
"""Require the same f64 bits. N=5500 must format as the published 1.274224153."""
import struct
import sys

def load(path):
    rows = {}
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) >= 6 and p[0] == "ROW" and p[2] == "bits":
                rows[int(p[1])] = int(p[3])
    return rows

def fmt9(bits):
    raw = struct.pack("<q", bits)
    return format(struct.unpack("<d", raw)[0], ".9f")

cpp = load("cpp.txt")
ail = load("ailang.txt")
sizes = [100, 5500]
failed = 0
for n in sizes:
    if n not in cpp or n not in ail:
        print("missing", n)
        failed = 1
        continue
    same = cpp[n] == ail[n]
    print("N", n, "bits", ail[n], "text", fmt9(ail[n]), "match" if same else "DIFFER", "cpp", fmt9(cpp[n]))
    if not same:
        failed = 1
if 5500 in ail and fmt9(ail[5500]) != "1.274224153":
    print("N 5500 text is not the published answer")
    failed = 1
sys.exit(failed)
