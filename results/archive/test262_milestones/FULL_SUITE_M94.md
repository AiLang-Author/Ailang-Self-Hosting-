# Full test262 suite — M94 regression baseline

**Date:** 2026-07-22  
**Branch:** `gpu-45-may-baseline-restore`  
**HEAD at run:** `ad99960c` (M94 async-gen FDI) — harness rebuilt before suite  
**Post-run:** M95 class BindingIdentifier name work in tree (not in this full score)  
**JSON:** `results/test262_full_m94.json`  
**Log:** `results/test262_full_m94.log`

```bash
python3 tools/test262_runner.py --full -j8 --timeout 20 \
  --output-json results/test262_full_m94.json
```

**Wall time:** ~54.6 min (3274 s) · **Workers:** 8 · **Mode:** batch

---

## Headline vs M83

| Scope | M83 | **M94** | Δ |
|-------|----:|--------:|--:|
| **Full** | 25770 / 49998 (**51.5%**) | **27419 / 49998 (54.8%)** | **+1649 (+3.3pp)** |
| **language** | 17538 / 24744 (70.9%)* | **17586 / 23899 (73.6%)** | path-count drift; % up |
| **built-ins** | 7998 / 23770 (33.6%) | **8830 / 23521 (37.5%)** | **+~4pp** |

\*M83 language totals differ slightly (suite path drift).

**timeout:** 80 · **error:** 49

> Full-suite high-water: **54.8%** (was 51.5% M83).

---

## Dedicated multipath (same tree, preferred language gates)

| Slice | Score | Gate |
|-------|------:|------|
| **expressions/object** | **1072 / 1161 = 92.3%** | ≥90% ✓ (`test262_m94_object.json`) |
| **expressions/generators** | **269 / 290 = 92.8%** | ≥90% ✓ |
| **statements/class** | **3466 / 4367 = 79.4%** | need +465 (`test262_m94_class.json`) |
| **expressions/class** | **3405 / 4059 = 83.9%** | need +249 |
| **class combined** | **6871 / 8426 = 81.5%** | |

Full-suite path counts can under-score slightly (object 91.6% in full vs 92.3% multipath). **Prefer multipath for language gates.**

---

## What drove +3.3pp (M86–M94)

- Yield ASI / BindingIdentifier / bare yield (M86–M87)
- ToPropertyKey accessors + GeneratorPrototype (M88)
- Generator this + nested RETURN RestoreArguments (M89, M91)
- await identifier outside async (M90)
- **Promise real constructor + instance [[Prototype]]** (M92)
- Async throw → reject Promise (M93)
- **Async-gen GenInitParams at call** (M94) — large object/dstr win

---

## Next dependency order (<90% first)

1. **Class** (stmt 79% / expr 84%) — private elements, dstr, async methods/gens, subclass  
2. **arguments-object** ~69% · **function-code** ~56%  
3. **for-await-of** ~59% · **await** · async iteration / yield*  
4. **modules** ~29% · dynamic-import ~36%  
5. Built-ins: Promise ~38%, String ~57%, Function ~53%; TypedArray/Proxy/Temporal still near-zero  

Object is done for the 90% language-slice gate; grind **class** next.

---

## Full-suite top built-in deserts (n≥100, lowest %)

SharedArrayBuffer, Proxy, Temporal, DataView, Atomics, TypedArray*, Reflect, Iterator — infrastructure, not language core.
