# Language suite rescore — M128e7bt

**Tip:** `4b2ab85e` (TLA wrap for async + import-defer store/globalThis fixes)  
(+ prior `e7a8596b` module Reflect install fix)

**Date:** 2026-08-02

**JSON:** `results/test262_lang_m128e7bt.json`

**Wall:** ~23.8 min (batch, -j 8, timeout 12s)

## Headline

| Metric | Value |
|--------|------:|
| Tests | 23635 |
| Pass | 22355 |
| Fail | 946 |
| Timeout | 51 |
| Error | 283 |
| **pass/(pass+fail)** | **95.94%** |
| pass/(pass+fail+err) | 94.79% |
| pass/total | 94.58% |

### vs prior full-language baselines

| Tip | Language pass/(pass+fail) | Notes |
|-----|--------------------------:|-------|
| M128e7l full | 90.1% | G1 met |
| M128e7br language --all | 91.35% | class/Reflect wall |
| **M128e7bt language --all** | **95.94%** | **G2 (≥95%) met** |
| G2 target | 95% | **cleared** on primary metric |

Net: **+1065 passes** vs e7br (21290 → 22355).

## Import / module surfaces (this grind)

| Surface | e7br | e7bt | Δ pass |
|---------|-----:|-----:|-------:|
| `expressions/dynamic-import` | 313/941 (33%) | **934/941 (99.5%)** | +621 |
| `module-code/top-level-await` | 12/251 (5%) | **244/251 (97%)** | +232 |
| `import/import-defer` | 7/101 (7%) | **82/101 (81%)** | +75 |
| `module-code/namespace` | 0/38 (0%) | **34/38 (89%)** | +34 |
| `import/import-attributes` | 2/17 | **16/17** | +14 |

## Fixes in this tip (e7bt + e7bs)

1. **e7bs** — `_MODULE_REFLECT_STUB`: no `var Reflect` hoist; install Reflect helpers via try + `defineProperty` (bare `Reflect.x =` killed dyn-import async).
2. **e7bt** — wrap TLA even when flags include `[async]` (engine has no bare top-level await).
3. **e7bt** — deferred NS export bindings + done-flag on a store object (free-var SET breaks past ~80 funcs with module stub).
4. **e7bt** — single `__defOp` for deferred property access.
5. **e7bt** — do not IIFE-isolate fixtures that touch `globalThis` (`setup_FIXTURE` dual-bind).

## Top residual categories (by fail count)

| Category | Pass | Fail | T/O | Tot | Pass%* |
|----------|-----:|-----:|----:|----:|-------:|
| `statements/class` | 4030 | 120 | 16 | 4367 | 97.1% |
| `statements/for-of` | 690 | 42 | 0 | 751 | 94.3% |
| `expressions/class` | 3991 | 47 | 16 | 4059 | 98.8% |
| `statements/using` | 38 | 40 | 0 | 78 | 48.7% |
| `expressions/object` | 1131 | 30 | 0 | 1161 | 97.4% |
| `expressions/yield` | 31 | 25 | 4 | 63 | 55.4% |
| `literals/regexp` | 207 | 27 | 4 | 238 | 88.5% |
| `import/import-defer` | 82 | 17 | 0 | 101 | 82.8% |
| `module-code/top-level-await` | 244 | 7 | 0 | 251 | 97.2% |
| `expressions/dynamic-import` | 934 | 4 | 2 | 941 | 99.6% |

\*pass/(pass+fail); class also has ~201 **error** (harness) status unchanged from e7br.

## Remaining import-ish hard cases

- TLA: async module graph rejection/ticks (~7)
- import-defer: evaluation-while-evaluating errors, super-property triggers, TLA+defer graphs (~17)
- dyn-import: import-attributes 2nd-param, a few root cases (~6)

## Next grind candidates

- class **error** bucket (~201) / remaining class fails
- `using` / `await-using`
- for-of / for-in residuals
- true engine free-var SET fix (would simplify module stubs)
