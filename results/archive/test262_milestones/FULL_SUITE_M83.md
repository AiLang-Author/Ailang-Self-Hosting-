# Full test262 suite — M83 baseline

**Date:** 2026-07-21  
**Branch:** `gpu-45-may-baseline-restore`  
**Commits:** `4f491fe7` (M83 str_buf/own_const) · `a39291c5` (M83b CallFunc EnterFuncCode)  
**JSON:** `results/test262_full_m83.json`  
**Log:** `results/test262_full_m83.log`  
**Note:** Full run was on M83 only (M83b landed mid-run; batch not rebuilt for full).

```bash
python3 tools/test262_runner.py --full -j 8 --timeout 20 \
  --output-json results/test262_full_m83.json
```

**Wall time:** ~48.1 min (2885 s) · **Workers:** 8 · **Mode:** batch

---

## Headline

| Scope | Pass | Total | % | vs M65 (49.6%) |
|-------|-----:|------:|--:|---------------:|
| **Full** | **25770** | **49998** | **51.5%** | **+963 (+1.9pp)** |
| **language** | **17538** | **24744** | **70.9%** | ~flat (path count drift) |
| **built-ins** | **7998** | **23770** | **33.6%** | **+~3pp** |

**Timeouts:** 77 · **error:** 47

> New full-suite high-water: **51.5%**.

---

## What fixed the flaky eval problem (M83)

**Root cause:** `eval` / `new Function` recompiled into `JSCompState.str_buf` while:
1. Outer const-pool STRING payloads still pointed into that buffer
2. PropTable keys for class methods/fields installed during eval were those C pointers

After eval restore, outer continuation and later method calls were **allocation-layout dependent** (classic flaky).

**M83 fix:**
- Save/restore compiler `str_buf` across `EvalSource`
- Permanent-ize live const STRING payloads before eval Run (PropTable keys survive)
- Clone FUNCTION descriptors into `own_const` for method survival after `func_pool` restore

**M83b (post full-run):** `JSVM__CallFunc` now `EnterFuncCode` so eval-created `__field_init__` / getters run their own bytecode image (instance fields via eval).

---

## Dedicated language rescore

### M83 only (pre-M83b)

| Slice | Pass / Total | % | vs pre-M83 |
|-------|-------------:|--:|-----------:|
| **class** (expr+stmt) | **6857 / 8426** | **81.4%** | **+207 (was 79.1%)** |
| **object** expr | **1004 / 1161** | **86.5%** | +1 |
| **arguments-object** | **121 / 263** | **46.0%** | flat |

### M83b batch (field_init CallFunc)

| Slice | Pass / Total | % | notes |
|-------|-------------:|--:|-------|
| **statements/class** | **3952 / 4367** | **90.7%** | **≥90% first time** |
| **expressions/class** | **3204 / 4059** | **79.1%** | residual async/private/super |
| **class combined** | **7156 / 8426** | **84.9%** | **+506 vs pre-M83** |
| **object** expr | **1011 / 1161** | **87.1%** | +8 vs M83 / +30 vs M70 |

JSON: `results/test262_m83b_class.json`

---

## OA/S inside full run

| Suite | Pass / Total | % |
|-------|-------------:|--:|
| **Object** | 2556 / 3414 | **74.9%** |
| **Array** | 2386 / 3083 | **77.4%** |
| **String** | 743 / 1334 | **55.7%** |

---

## Next toward 90%

1. **M83b batch rescore** — class fields via eval reclaim  
2. **L6 async / async-gen** — largest remaining language desert (~async 49.5% in full)  
3. **L5 mapped arguments** — nonconfigurable descriptor residual (~13 tests)  
4. **L2 class** residual — private/static brand realm, super, async methods  

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'language/expressions/class,language/statements/class' -j8
```
