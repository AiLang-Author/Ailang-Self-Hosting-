# test262 status — tip M128e7bh (full suite 2026-08-01)

**Tip:** `70ad3b2b` (docs) / engine e7bh `b58baa0d`  
**Full suite wall:** 2965.6s (~49.4 min)  
**JSON:** `results/test262_full_m128e7bh.json`

---

## Headline (authoritative full suite)

| Metric | e7x (best prior) | e7bb | **e7bh (now)** |
|--------|-----------------:|-----:|---------------:|
| Overall pass | 30,505 (61.35%) | 29,162 (58.65%) | **30,123 (60.58%)** |
| Language | 21,607 (**91.42%**) | 20,679 (87.49%) | **20,964 (88.70%)** |
| Built-ins | 7,963 (33.86%) | 7,616 (32.38%) | **8,283 (35.22%)** |
| **G2 gap** (lang→95%) | **847** | 1,775 | **1,490** |

G2 need: **22,454** / 23,635 language passes.  
**Still short of G2 by 1,490 language passes.**

### Recovery narrative

- **e7x→e7bb:** mass CallFunc regression (−928 language).  
- **e7bc–e7bh:** partial recovery vs e7bb (**+285 language**, **+961 overall net**).  
- **vs e7x:** still **−643 language** / **−382 overall** (class bulk dominates regressions list).  
- **Built-ins:** best full yet (**35.22%**) — side benefit, not G2.

Transitions e7x→e7bh: fixed **1,631** / regressed **2,013**.  
Transitions e7bb→e7bh: fixed **1,219** / regressed **258**.

---

## Distance to G2 / built-ins

| Gate | Meaning | Status |
|------|---------|--------|
| **G2** | Language ≥ 95% | **Not met** — gap **1,490** |
| **Built-ins bulk** | Open Reflect/Proxy/TA/… | **~15.2k residual** at 35.2% — still after G2 |

Language residual bulk (e7bh knockout): `statements/class` (~1.1k), `expressions/class` (~575), for-of, import-defer, using, yield, regexp, …

---

## Regression testing status

| Layer | Status |
|-------|--------|
| **Full suite e7bh** | **Done** — artifacts under `results/test262_full_m128e7bh_*` |
| **vs e7x** | Net **−382**; language **−643** — watch class/async-gen regressions |
| **vs e7bb** | Net **+961** — e7bc path recovered most of the dip |
| **Safety no-batch** | Still green on known 100% chips (optional, array, template, …) |
| **Batch flake** | A few 100% no-batch cats show 1 residual in full batch |

### Re-run command
```bash
python3 tools/test262_runner.py --full -j 8 --timeout 12 \
  --output-json results/test262_full_m128e7bh.json
python3 tools/test262_baseline_report.py results/test262_full_m128e7bh.json \
  --prior results/test262_full_m128e7x.json --label M128e7bh --tip $(git rev-parse --short HEAD)
```

Progress: `results/M128e7_PROGRESS.md` · Knockout: `results/test262_full_m128e7bh_KNOCKOUT.md`
