#!/usr/bin/env python3
"""Summarize a full test262_runner --full JSON dump into section/category stats."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def section_of(path: str) -> str:
    # .../test262/test/language/... or built-ins / annexB / staging
    parts = Path(path).parts
    if "test" in parts:
        i = parts.index("test")
        if i + 1 < len(parts):
            return parts[i + 1]
    return "other"


def lang_category(path: str) -> str:
    """language/<area>/... → area (statements, expressions, ...)."""
    parts = Path(path).parts
    if "language" not in parts:
        return ""
    i = parts.index("language")
    if i + 1 < len(parts):
        return parts[i + 1]
    return "language"


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "results/test262_full_m128e7l.json")
    d = json.loads(src.read_text())
    results = d.get("results") or d
    if not isinstance(results, list):
        print("bad json shape", type(results))
        sys.exit(1)

    by_status = Counter(r.get("status") for r in results)
    total = len(results)
    pass_n = by_status.get("pass", 0)
    fail_n = by_status.get("fail", 0)
    err_n = by_status.get("error", 0)
    to_n = by_status.get("timeout", 0)
    skip_n = by_status.get("skip", 0)

    sec = defaultdict(lambda: Counter())
    lang_area = defaultdict(lambda: Counter())
    bi_area = defaultdict(lambda: Counter())

    for r in results:
        p = r.get("path", "")
        st = r.get("status", "?")
        s = section_of(p)
        sec[s][st] += 1
        if s == "language":
            lang_area[lang_category(p)][st] += 1
        elif s == "built-ins":
            # built-ins/Object/... → Object
            parts = Path(p).parts
            if "built-ins" in parts:
                i = parts.index("built-ins")
                if i + 1 < len(parts):
                    bi_area[parts[i + 1]][st] += 1

    def pct(n, t):
        return 100.0 * n / t if t else 0.0

    print(f"# Full suite summary — {src.name}")
    print(f"total_tests_field: {d.get('total_tests', total)}")
    print(f"wall_time_s: {d.get('wall_time_s', '?')}")
    print()
    print("## Headline")
    print(f"| Metric | Value |")
    print(f"|--------|------:|")
    print(f"| Tests | {total} |")
    print(f"| Pass | {pass_n} (**{pct(pass_n, total):.1f}%**) |")
    print(f"| Fail | {fail_n} |")
    print(f"| Error | {err_n} |")
    print(f"| Timeout | {to_n} |")
    print(f"| Skip | {skip_n} |")
    print()
    print("## By section")
    print("| Section | Total | Pass | Fail | Err | T/O | Pass% |")
    print("|---------|------:|-----:|-----:|----:|----:|------:|")
    for s in sorted(sec.keys(), key=lambda x: -sum(sec[x].values())):
        c = sec[s]
        t = sum(c.values())
        p = c.get("pass", 0)
        print(f"| {s} | {t} | {p} | {c.get('fail',0)} | {c.get('error',0)} | {c.get('timeout',0)} | {pct(p,t):.1f}% |")
    print()
    print("## Language top areas")
    print("| Area | Total | Pass | Pass% |")
    print("|------|------:|-----:|------:|")
    rows = []
    for a, c in lang_area.items():
        t = sum(c.values())
        p = c.get("pass", 0)
        rows.append((a, t, p, pct(p, t)))
    for a, t, p, pc in sorted(rows, key=lambda x: -x[1])[:20]:
        print(f"| {a} | {t} | {p} | {pc:.1f}% |")
    print()
    print("## Built-ins top (by total)")
    print("| Builtin | Total | Pass | Pass% |")
    print("|---------|------:|-----:|------:|")
    brows = []
    for a, c in bi_area.items():
        t = sum(c.values())
        p = c.get("pass", 0)
        brows.append((a, t, p, pct(p, t)))
    for a, t, p, pc in sorted(brows, key=lambda x: -x[1])[:25]:
        print(f"| {a} | {t} | {p} | {pc:.1f}% |")
    print()
    # residual language fails sample
    print("## Sample language fails (first 30 paths)")
    n = 0
    for r in results:
        if r.get("status") not in ("fail", "error", "timeout"):
            continue
        if section_of(r.get("path", "")) != "language":
            continue
        print("-", r.get("path", "").split("test/")[-1] if "test/" in r.get("path","") else r.get("path"))
        n += 1
        if n >= 30:
            break


if __name__ == "__main__":
    main()
