# Full test262 suite — M97 regression baseline

**Date:** 2026-07-22  
**Branch:** `gpu-45-may-baseline-restore`  
**HEAD at run:** M96 + uncommitted M97 (`JSComp__AddPropName` FloatToStr numeric PropertyName) — harness rebuilt 18:00 before suite  
**Post-run:** M97b (class computed TO_PROP_KEY) + M98 (async gen yield await / reject) in tree, not in this full score  
**JSON:** `results/test262_full_m97.json`  
**Log:** `results/test262_full_m97.log`

```bash
python3 tools/test262_runner.py --full -j8 --timeout 20 \
  --output-json results/test262_full_m97.json
```

**Wall time:** ~2794s (46.6 min) · **Workers:** 8 · **Mode:** batch

---

## Headline vs M94

| Scope | M94 | **M97** | Δ |
|-------|----:|--------:|--:|
| **Full** | 27419 / 49998 (**54.8%**) | **27975 / 49998 (56.0%)** | **+556 (+1.2pp)** |
| **language** | 17586 / 23899 (73.6%)* | **18642 / 24744 (75.3%)** | path-count / % up |
| **built-ins** | 8830 / 23521 (37.5%) | **8913 / 23770 (37.5%)** | ~flat |

\*Suite path counts drift slightly across runs.

**timeout:** 78

> Full-suite high-water: **56.0%** (was 54.8% M94, 51.5% M83).

---

## Full-suite language gates (same JSON; prefer multipath for class/object)

| Slice | Score |
|-------|------:|
| expressions/object | 1064/1165 = 91.3% |
| expressions/generators | 267/290 = 92.1% |
| statements/class | 3671/4369 = 84.0% |
| expressions/class | 3511/4059 = 86.5% |
| arguments-object | 216/266 = 81.2% |
| function-code | 194/376 = 51.6% |
| for-await-of | 724/1235 = 58.6% |
| module-code | 223/771 = 28.9% |
| dynamic-import | 359/997 = 36.0% |

M96 multipath class was higher (stmt 85.9% / expr 88.7%) — full-suite under-scores slightly.

---

## What moved M94→M97

- **M95:** class BindingIdentifier may be `await`/`yield`
- **M96:** class async* preserve N_OP (ASYNC_GEN_CLOSURE)
- **M97:** `JSComp__AddPropName` — numeric PropertyName ToPropertyKey (`0x10`→`"16"`, `.1`→`"0.1"`)

---

## Next (dependency order, multipath ≥90%)

1. **Class** — still #1 language gate (need ~+186 stmt / +60 expr from M96 multipath)
2. arguments-object / function-code
3. async / for-await-of
4. modules / dynamic-import
5. Built-ins deserts (Proxy/Temporal/TypedArray/…)


---

## Multipath after M97 (TO_PROP_KEY + AddPropName)

| Slice | M96 | **M97** | Δ |
|-------|----:|--------:|--:|
| statements/class | 3744/4367 (85.9%) | **3758/4367 (86.3%)** | +14 |
| expressions/class | 3594/4059 (88.7%) | **3603/4059 (88.9%)** | +9 |
| class combined | 7338/8426 (87.1%) | **7361/8426 (87.5%)** | +23 |
| accessor-name (stmt+expr) | ~95% | **84/84 = 100%** | ✓ |

To 90%: stmt needs +173, expr +51. Residual: private elements ~412, async-gen yield* ~222, subclass ~94.

