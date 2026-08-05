#!/usr/bin/env python3
"""
Build a clean full-suite baseline report + knockout list + regression watch.

Usage:
  python3 tools/test262_baseline_report.py \
      results/test262_full_m128e7bb.json \
      --prior results/test262_full_m128e7x.json \
      --label M128e7bb \
      --tip 6dbf7744

Writes:
  results/test262_full_<label>_SUMMARY.md
  results/test262_full_<label>_STATS.json
  results/test262_full_<label>_KNOCKOUT.md   (language residuals, near-complete)
  results/test262_full_<label>_REGRESSION.md (vs --prior)
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def section_of(path: str) -> str:
    parts = Path(path.replace("\\", "/")).parts
    if "test" in parts:
        i = parts.index("test")
        if i + 1 < len(parts):
            return parts[i + 1]
    return "other"


def lang_area(path: str) -> str:
    parts = Path(path.replace("\\", "/")).parts
    if "language" not in parts:
        return ""
    i = parts.index("language")
    # language/expressions/in/... → expressions/in
    segs = parts[i + 1 :]
    if len(segs) >= 2:
        return f"{segs[0]}/{segs[1]}"
    if segs:
        return segs[0]
    return "language"


def bi_area(path: str) -> str:
    parts = Path(path.replace("\\", "/")).parts
    if "built-ins" not in parts:
        return ""
    i = parts.index("built-ins")
    if i + 1 < len(parts):
        return parts[i + 1]
    return "built-ins"


def norm_path(path: str) -> str:
    p = path.replace("\\", "/")
    if "test/" in p:
        return p.split("test/", 1)[-1]
    return p


def load_results(src: Path):
    d = json.loads(src.read_text())
    results = d.get("results") or d
    if not isinstance(results, list):
        raise SystemExit(f"bad json shape in {src}: {type(results)}")
    return d, results


def pct(n, t):
    return 100.0 * n / t if t else 0.0


def status_map(results):
    m = {}
    for r in results:
        p = norm_path(r.get("path", ""))
        m[p] = r.get("status", "?")
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path")
    ap.add_argument("--prior", default="results/test262_full_m128e7x.json")
    ap.add_argument("--label", default="M128e7bb")
    ap.add_argument("--tip", default="")
    ap.add_argument("--out-dir", default="results")
    args = ap.parse_args()

    src = Path(args.json_path)
    out_dir = Path(args.out_dir)
    label = args.label
    tip = args.tip

    d, results = load_results(src)
    by = Counter(r.get("status") for r in results)
    total = len(results)
    pass_n = by.get("pass", 0)
    fail_n = by.get("fail", 0)
    err_n = by.get("error", 0)
    to_n = by.get("timeout", 0)
    skip_n = by.get("skip", 0)
    wall = d.get("wall_time_s")

    sec = defaultdict(Counter)
    lang_cat = defaultdict(Counter)
    bi_cat = defaultdict(Counter)
    lang_fails = []

    for r in results:
        p = r.get("path", "")
        st = r.get("status", "?")
        s = section_of(p)
        sec[s][st] += 1
        if s == "language":
            lang_cat[lang_area(p)][st] += 1
            if st in ("fail", "error", "timeout"):
                lang_fails.append(r)
        elif s == "built-ins":
            bi_cat[bi_area(p)][st] += 1

    lang_total = sum(sec["language"].values()) if "language" in sec else 0
    lang_pass = sec["language"].get("pass", 0) if "language" in sec else 0
    g2_need = math.ceil(lang_total * 0.95) if lang_total else 0
    g2_gap = g2_need - lang_pass

    bi_total = sum(sec["built-ins"].values()) if "built-ins" in sec else 0
    bi_pass = sec["built-ins"].get("pass", 0) if "built-ins" in sec else 0

    stats = {
        "tip": tip,
        "label": label,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_json": str(src),
        "total_tests": total,
        "wall_time_s": wall,
        "status": dict(by),
        "sections": {},
        "pass_pct_overall": round(pct(pass_n, total), 2),
        "pass_pct_language": round(pct(lang_pass, lang_total), 2) if lang_total else 0,
        "pass_pct_builtins": round(pct(bi_pass, bi_total), 2) if bi_total else 0,
        "language_pass": lang_pass,
        "language_total": lang_total,
        "g2_need_passes": g2_need,
        "g2_gap": g2_gap,
        "builtins_pass": bi_pass,
        "builtins_total": bi_total,
    }
    for s, c in sec.items():
        t = sum(c.values())
        p = c.get("pass", 0)
        stats["sections"][s] = {
            **dict(c),
            "total": t,
            "pass_pct": round(pct(p, t), 2),
        }

    # --- SUMMARY ---
    sum_path = out_dir / f"test262_full_{label.lower()}_SUMMARY.md"
    lines = []
    lines.append(f"# Full test262 regression — {label}")
    lines.append("")
    lines.append(f"**Tip:** `{tip}`  ")
    lines.append(f"**Harness:** test262_harness_batch.x  ")
    lines.append(f"**JSON:** `{src}`  ")
    if wall is not None:
        lines.append(f"**Wall time:** {wall:.1f}s (~**{wall/60:.1f} min**)  ")
    lines.append(f"**Generated:** {stats['generated_at']}  ")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|------:|")
    lines.append(f"| Tests discovered | **{total:,}** |")
    lines.append(f"| **Pass** | **{pass_n:,}** |")
    lines.append(f"| Fail | {fail_n:,} |")
    lines.append(f"| Error | {err_n:,} |")
    lines.append(f"| Timeout | {to_n:,} |")
    lines.append(f"| Skip | {skip_n:,} |")
    lines.append(f"| **Overall pass rate** | **{stats['pass_pct_overall']}%** |")
    lines.append(f"| Language pass rate | **{stats['pass_pct_language']}%** |")
    lines.append(f"| Built-ins pass rate | **{stats['pass_pct_builtins']}%** |")
    lines.append("")
    lines.append("## Language → G2 (95%)")
    lines.append("")
    lines.append("| | Value |")
    lines.append("|--|------:|")
    lines.append(f"| Language pass | {lang_pass:,} |")
    lines.append(f"| Language total | {lang_total:,} |")
    lines.append(f"| Pass% | {stats['pass_pct_language']}% |")
    lines.append(f"| G2 need (ceil 95%) | {g2_need:,} |")
    lines.append(f"| **G2 gap** | **{g2_gap:,}** |")
    lines.append("")
    lines.append("## By section")
    lines.append("")
    lines.append("| Section | Pass | Fail | Error | T/O | Total | Pass% |")
    lines.append("|---------|-----:|-----:|------:|----:|------:|------:|")
    for s in sorted(sec.keys(), key=lambda x: -sum(sec[x].values())):
        c = sec[s]
        t = sum(c.values())
        p = c.get("pass", 0)
        lines.append(
            f"| {s} | {p:,} | {c.get('fail',0):,} | {c.get('error',0):,} | "
            f"{c.get('timeout',0):,} | {t:,} | {pct(p,t):.2f}% |"
        )
    lines.append("")
    lines.append("## Language top residual categories (by non-pass count)")
    lines.append("")
    lines.append("| Category | Pass | Residual | Total | Pass% |")
    lines.append("|----------|-----:|---------:|------:|------:|")
    rows = []
    for a, c in lang_cat.items():
        t = sum(c.values())
        p = c.get("pass", 0)
        bad = t - p - c.get("skip", 0)
        rows.append((bad, a, p, t, pct(p, t)))
    for bad, a, p, t, pc in sorted(rows, key=lambda x: -x[0])[:40]:
        lines.append(f"| {a} | {p} | {bad} | {t} | {pc:.1f}% |")
    lines.append("")
    lines.append("## Near-complete language categories (1–25 residual)")
    lines.append("")
    lines.append("| Category | Pass | Residual | Total | Pass% |")
    lines.append("|----------|-----:|---------:|------:|------:|")
    near = [r for r in rows if 1 <= r[0] <= 25 and r[4] >= 50]
    for bad, a, p, t, pc in sorted(near, key=lambda x: (x[0], -x[4]))[:50]:
        lines.append(f"| {a} | {p} | {bad} | {t} | {pc:.1f}% |")
    lines.append("")
    sum_path.write_text("\n".join(lines) + "\n")

    # --- STATS JSON ---
    stats_path = out_dir / f"test262_full_{label.lower()}_STATS.json"
    # language category residuals for tooling
    stats["language_categories"] = {
        a: {
            **dict(c),
            "total": sum(c.values()),
            "residual": sum(c.values()) - c.get("pass", 0) - c.get("skip", 0),
            "pass_pct": round(pct(c.get("pass", 0), sum(c.values())), 2),
        }
        for a, c in lang_cat.items()
    }
    stats_path.write_text(json.dumps(stats, indent=2) + "\n")

    # --- KNOCKOUT LIST ---
    ko_path = out_dir / f"test262_full_{label.lower()}_KNOCKOUT.md"
    ko = []
    ko.append(f"# Knockout list — {label} (language residuals)")
    ko.append("")
    ko.append(f"Tip `{tip}` · language residual **{lang_total - lang_pass:,}** "
              f"(fail+error+timeout) · G2 gap **{g2_gap:,}**")
    ko.append("")
    ko.append("## Priority bands")
    ko.append("")
    ko.append("| Band | Criteria | Use |")
    ko.append("|------|----------|-----|")
    ko.append("| **P0 near-complete** | residual 1–25, pass% ≥ 70% | grind 100% chips |")
    ko.append("| **P1 medium residual** | residual 26–80 | engine feature slices |")
    ko.append("| **P2 bulk residual** | residual > 80 | class/private/for-of/eval |")
    ko.append("")

    p0 = [r for r in rows if 1 <= r[0] <= 25 and r[4] >= 70]
    p1 = [r for r in rows if 26 <= r[0] <= 80]
    p2 = [r for r in rows if r[0] > 80]

    def emit_band(title, band):
        ko.append(f"## {title}")
        ko.append("")
        ko.append("| Category | Residual | Pass/Total | Pass% |")
        ko.append("|----------|---------:|-----------:|------:|")
        for bad, a, p, t, pc in sorted(band, key=lambda x: (x[0], -x[4])):
            ko.append(f"| `{a}` | {bad} | {p}/{t} | {pc:.1f}% |")
        ko.append("")

    emit_band("P0 — near-complete (knock out first)", p0)
    emit_band("P1 — medium residual", p1)
    emit_band("P2 — bulk residual", p2)

    # Per-test sample for P0 categories
    ko.append("## P0 failing paths (sample ≤15 per category)")
    ko.append("")
    p0_names = {a for _, a, *_ in p0}
    by_cat_fails = defaultdict(list)
    for r in lang_fails:
        a = lang_area(r.get("path", ""))
        if a in p0_names:
            by_cat_fails[a].append(
                (r.get("status"), norm_path(r.get("path", "")), r.get("reason", "")[:80])
            )
    for a in sorted(p0_names):
        items = by_cat_fails.get(a, [])
        ko.append(f"### `{a}` ({len(items)} residual)")
        for st, path, reason in items[:15]:
            ko.append(f"- **{st}** `{path}` {reason}")
        if len(items) > 15:
            ko.append(f"- … +{len(items)-15} more")
        ko.append("")

    ko_path.write_text("\n".join(ko) + "\n")

    # --- REGRESSION WATCH vs prior ---
    reg_path = out_dir / f"test262_full_{label.lower()}_REGRESSION.md"
    reg = []
    reg.append(f"# Regression watch — {label} vs prior")
    reg.append("")
    prior_path = Path(args.prior)
    if not prior_path.is_file():
        reg.append(f"**No prior baseline** at `{prior_path}` — first clean baseline.")
        reg_path.write_text("\n".join(reg) + "\n")
    else:
        pd, presults = load_results(prior_path)
        pmap = status_map(presults)
        nmap = status_map(results)
        all_paths = set(pmap) | set(nmap)

        fixed = []  # was bad → pass
        regressed = []  # was pass → bad
        still_bad = []
        new_bad = []  # only in new, bad
        new_pass = []  # only in new, pass

        bad_set = {"fail", "error", "timeout"}
        for p in sorted(all_paths):
            os = pmap.get(p)
            ns = nmap.get(p)
            if os is None and ns is not None:
                if ns == "pass":
                    new_pass.append(p)
                elif ns in bad_set:
                    new_bad.append((p, ns))
                continue
            if ns is None:
                continue
            if os in bad_set and ns == "pass":
                fixed.append(p)
            elif os == "pass" and ns in bad_set:
                regressed.append((p, ns))
            elif os in bad_set and ns in bad_set:
                still_bad.append((p, os, ns))

        p_by = Counter(r.get("status") for r in presults)
        p_total = len(presults)
        p_pass = p_by.get("pass", 0)

        # language-only fixed/regressed
        def is_lang(p):
            return p.startswith("language/") or "/language/" in p

        fixed_lang = [p for p in fixed if is_lang(p)]
        regressed_lang = [(p, s) for p, s in regressed if is_lang(p)]

        reg.append(f"**New:** `{src.name}` tip `{tip}` · **Prior:** `{prior_path.name}`")
        reg.append("")
        reg.append("## Headline delta")
        reg.append("")
        reg.append("| Metric | Prior | New | Δ |")
        reg.append("|--------|------:|----:|--:|")
        reg.append(f"| Total | {p_total:,} | {total:,} | {total - p_total:+,} |")
        reg.append(f"| Pass | {p_pass:,} | {pass_n:,} | {pass_n - p_pass:+,} |")
        reg.append(
            f"| Overall % | {pct(p_pass,p_total):.2f}% | {stats['pass_pct_overall']}% | "
            f"{stats['pass_pct_overall'] - pct(p_pass,p_total):+.2f} pp |"
        )

        # prior language stats
        p_lang_pass = p_lang_tot = 0
        for r in presults:
            if section_of(r.get("path", "")) == "language":
                p_lang_tot += 1
                if r.get("status") == "pass":
                    p_lang_pass += 1
        reg.append(
            f"| Language pass | {p_lang_pass:,} | {lang_pass:,} | {lang_pass - p_lang_pass:+,} |"
        )
        reg.append(
            f"| Language % | {pct(p_lang_pass,p_lang_tot):.2f}% | {stats['pass_pct_language']}% | "
            f"{stats['pass_pct_language'] - pct(p_lang_pass,p_lang_tot):+.2f} pp |"
        )
        p_g2_gap = math.ceil(p_lang_tot * 0.95) - p_lang_pass if p_lang_tot else 0
        reg.append(f"| G2 gap | {p_g2_gap:,} | {g2_gap:,} | {g2_gap - p_g2_gap:+,} |")
        reg.append("")
        reg.append("## Pass/fail transitions")
        reg.append("")
        reg.append(f"| Transition | Count |")
        reg.append(f"|------------|------:|")
        reg.append(f"| **Fixed** (bad→pass) | **{len(fixed):,}** |")
        reg.append(f"| Fixed (language only) | {len(fixed_lang):,} |")
        reg.append(f"| **Regressed** (pass→bad) | **{len(regressed):,}** |")
        reg.append(f"| Regressed (language only) | {len(regressed_lang):,} |")
        reg.append(f"| Still bad (both) | {len(still_bad):,} |")
        reg.append(f"| New paths bad | {len(new_bad):,} |")
        reg.append("")

        reg.append("## Regressions (pass → fail/error/timeout)")
        reg.append("")
        if not regressed:
            reg.append("_None — clean vs prior._")
            reg.append("")
        else:
            reg.append(f"**{len(regressed)} regressions** (language: {len(regressed_lang)}):")
            reg.append("")
            # group by category
            by_c = defaultdict(list)
            for p, st in regressed:
                by_c[lang_area(p) if is_lang(p) else section_of(p) or "other"].append((p, st))
            for cat in sorted(by_c.keys(), key=lambda c: -len(by_c[c])):
                items = by_c[cat]
                reg.append(f"### `{cat}` ({len(items)})")
                for p, st in items[:40]:
                    reg.append(f"- **{st}** `{p}`")
                if len(items) > 40:
                    reg.append(f"- … +{len(items)-40} more")
                reg.append("")

        reg.append("## Fixed sample (language, first 80)")
        reg.append("")
        if not fixed_lang:
            reg.append("_No language fixes vs prior._")
        else:
            for p in fixed_lang[:80]:
                reg.append(f"- `{p}`")
            if len(fixed_lang) > 80:
                reg.append(f"- … +{len(fixed_lang)-80} more language fixes")
        reg.append("")

        reg_path.write_text("\n".join(reg) + "\n")

        # also dump machine-readable regression list
        reg_json = {
            "label": label,
            "tip": tip,
            "prior": str(prior_path),
            "fixed_count": len(fixed),
            "regressed_count": len(regressed),
            "fixed_language_count": len(fixed_lang),
            "regressed_language_count": len(regressed_lang),
            "regressed": [{"path": p, "status": s} for p, s in regressed],
            "fixed_language_sample": fixed_lang[:500],
            "delta_pass": pass_n - p_pass,
            "delta_language_pass": lang_pass - p_lang_pass,
            "delta_g2_gap": g2_gap - p_g2_gap,
        }
        (out_dir / f"test262_full_{label.lower()}_REGRESSION.json").write_text(
            json.dumps(reg_json, indent=2) + "\n"
        )

    print(f"Wrote {sum_path}")
    print(f"Wrote {stats_path}")
    print(f"Wrote {ko_path}")
    print(f"Wrote {reg_path}")
    print(
        f"HEADLINE pass={pass_n}/{total} ({stats['pass_pct_overall']}%) "
        f"lang={lang_pass}/{lang_total} ({stats['pass_pct_language']}%) "
        f"g2_gap={g2_gap}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
