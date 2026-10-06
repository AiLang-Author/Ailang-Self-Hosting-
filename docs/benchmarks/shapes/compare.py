#!/usr/bin/env python3
"""Check f64 sums. C++ and AILANG rows that share a formula must share bits."""
import collections
import sys

cpp = collections.defaultdict(dict)
ail = collections.defaultdict(dict)

def load(path, dest):
    with open(path) as f:
        for line in f:
            p = line.split()
            if not p or p[0] != "ROW":
                continue
            tier, n, name, cyc, bits = p[1], p[2], p[3], p[4], p[5]
            dest[(tier, n, name)] = (cyc, bits)

load("cpp.txt", cpp)
load("ailang.txt", ail)

# Same association, so the bit patterns are required to match.
pairs = [
    ("area-if", "area-if"),
    ("area-if", "area-if-call"),
    ("area-if", "area-fork"),
    ("area-if", "area-fork-call"),
    ("area-if", "area-branch"),
    ("area-if", "area-branch-call"),
    ("area-switch", "area-branch"),
    ("area-table", "area-table"),
    ("area-table", "area-table-call"),
    ("area-table-x4", "area-table-x4"),
    ("corner-call", "corner-call"),
    ("corner-two", "corner-two"),
    ("corner-one", "corner-one"),
    ("corner-table", "corner-table"),
    ("loop-int", "loop-int"),
    ("loop-fadd", "loop-fadd"),
    ("loop-fmul", "loop-fmul"),
]

bad = 0
for tier, n in (("hot", "256"), ("hot", "4096"), ("cold", "4096")):
    for cname, aname in pairs:
        ck = (tier, n, cname)
        ak = (tier, n, aname)
        if ck not in cpp or ak not in ail:
            print("MISSING", tier, n, cname, aname)
            bad += 1
            continue
        if cpp[ck][1] != ail[ak][1]:
            print("DIFF", tier, n, cname, cpp[ck][1], aname, ail[ak][1])
            bad += 1
print("mismatches", bad)
sys.exit(1 if bad else 0)
