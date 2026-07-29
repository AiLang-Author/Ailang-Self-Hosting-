#!/usr/bin/env python3
"""Summarize test262 full suite JSON results."""
import json, sys, os
from collections import defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else "results/test262_full_m128e6ak.json"
if not os.path.exists(path):
    print("missing", path)
    sys.exit(1)
data = json.load(open(path))
tests = data if isinstance(data, list) else data.get("results", data.get("tests", []))
by_sec = defaultdict(lambda: {"total":0,"pass":0,"fail":0,"error":0,"timeout":0,"skip":0})
by_status = defaultdict(int)
for t in tests:
    st = t.get("status", "unknown")
    by_status[st] += 1
    p = t.get("path", "")
    # section: test262/test/<section>/...
    parts = p.replace("\\", "/").split("/")
    sec = "other"
    if "test" in parts:
        i = parts.index("test")
        if i + 1 < len(parts):
            sec = parts[i+1]
    by_sec[sec]["total"] += 1
    if st in by_sec[sec]:
        by_sec[sec][st] += 1
    elif st == "pass":
        by_sec[sec]["pass"] += 1
    else:
        by_sec[sec]["fail"] += 1

total = len(tests)
passed = by_status.get("pass", 0)
print(f"# Full test262 summary")
print(f"**Source:** `{path}`")
print(f"**Tests:** {total}")
print(f"**Pass:** {passed} ({100*passed/total:.1f}%)" if total else "empty")
print()
print("| Status | Count |")
print("|--------|------:|")
for k,v in sorted(by_status.items(), key=lambda x: -x[1]):
    print(f"| {k} | {v} |")
print()
print("| Section | Total | Pass | Pass% |")
print("|---------|------:|-----:|------:|")
for sec, d in sorted(by_sec.items(), key=lambda x: -x[1]["total"]):
    pct = 100*d["pass"]/d["total"] if d["total"] else 0
    print(f"| {sec} | {d['total']} | {d['pass']} | {pct:.1f}% |")
# language subsections if present
lang = defaultdict(lambda: {"total":0,"pass":0})
for t in tests:
    p = t.get("path","").replace("\\","/")
    if "/language/" not in p:
        continue
    rest = p.split("/language/",1)[1]
    sub = rest.split("/")[0] if rest else "language"
    lang[sub]["total"] += 1
    if t.get("status")=="pass":
        lang[sub]["pass"] += 1
if lang:
    print()
    print("## language subsections (top by size)")
    print("| Sub | Total | Pass | Pass% |")
    print("|-----|------:|-----:|------:|")
    for sub,d in sorted(lang.items(), key=lambda x: -x[1]["total"])[:25]:
        pct = 100*d["pass"]/d["total"] if d["total"] else 0
        print(f"| {sub} | {d['total']} | {d['pass']} | {pct:.1f}% |")
