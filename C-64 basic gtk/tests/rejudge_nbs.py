#!/usr/bin/env python3
"""Re-judge saved NBS .out files. Only execution after RUN counts."""
import glob
import os
import re

OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nbs", "out")

FAIL_LINE = re.compile(
    r"^\s*(\*\*\*\s*TEST FAILED|\*\*\*\s*TEST FAILS|TEST FAILED IN|RESULT:\s*FAILED)",
    re.I,
)
INSTR = re.compile(r"OTHERWISE|THEN THE TEST FAIL|IF SUBSEQUENT|SHOULD BE", re.I)


def after_run(text):
    key = "\nRUN\n"
    i = text.rfind(key)
    if i >= 0:
        return text[i + len(key):]
    return text


def classify(name, text):
    body = after_run(text)
    lines = body.splitlines()
    failed = False
    for ln in lines:
        if INSTR.search(ln) and "TEST FAILED IN" not in ln.upper():
            continue
        if FAIL_LINE.search(ln):
            failed = True
            break
        if re.search(r"\*\*\*\s+TEST FAILED", ln, re.I):
            failed = True
            break
    if failed:
        return "FAIL"
    up = body.upper()
    if " ERROR" in up and "?" in body:
        return "ERROR"
    if "BREAK" in up or "END PROGRAM" in up or "READY." in body:
        return "PASS"
    if not body.strip():
        return "EMPTY"
    return "UNKNOWN"


def main():
    files = sorted(glob.glob(os.path.join(OUTDIR, "P*.out")))
    counts = {}
    rows = []
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        st = classify(name, open(f).read())
        counts[st] = counts.get(st, 0) + 1
        rows.append((st, name))
    for st, name in rows:
        if st != "PASS":
            print("%-8s %s" % (st, name))
    print()
    tot = len(rows)
    print("judged %d  PASS %d  FAIL %d  ERROR %d  TIMEOUT %d  UNKNOWN %d  EMPTY %d" % (
        tot, counts.get("PASS", 0), counts.get("FAIL", 0), counts.get("ERROR", 0),
        counts.get("TIMEOUT", 0), counts.get("UNKNOWN", 0), counts.get("EMPTY", 0)))


if __name__ == "__main__":
    main()
