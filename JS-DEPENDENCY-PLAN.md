# JS Engine — Dependency Plan

**Updated:** 2026-07-14  
**Goal:** Language compliance mass first; speed later. No false greens.

| Rule | |
|------|--|
| Order | Fix **dependencies first** (ops → assign → call → function → eval → class → modules → async) |
| Honesty | Generators / function / call: **`--no-batch`**. Batch OK after M18b (gval rewind). |
| Style | **Wrap over write** — use Ailang/runtime primitives; thin JS surface |
| Gate | Midgate green after every mole |

---

## Summary (now)

| Gate | Score | Notes |
|------|------:|-------|
| e2e + midgate core | **PASS** | |
| function dstr | **186/186** | |
| gen dstr | **372/372** | no-batch |
| fn dstr | **372/372** | no-batch |
| generators | **502/556 (90%)** | no-batch |
| function | **601/715 (84%)** | no-batch |
| call | **73/92 (79%)** | no-batch; M21 spread-err 16/16 |
| mapped args | **43/43** | |
| **language `--all`** | **13441/23899 (56.2%)** | honest batch; was 42% before gval fix |
| compound-assignment | **275/454 (60.6%)** | M19a boxing + M19c string ToNumber |
| full `--full` (~49k) | not run | milestone only |

**Batch fix (M18b):** `JSRT_Reset` rewinds `gval_pool` — batch no longer under-reports statements/function & generators.

**Timing:** Harness workers peg cores; ~150ms/test batch. Engine, not Python.

---

## Gates

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --categories expressions/compound-assignment -j 4
python3 tools/test262_runner.py --categories expressions/call --no-batch -j 4
python3 tools/test262_runner.py --categories statements/generators,expressions/generators --no-batch -j 4
# broad
python3 tools/test262_runner.py --all -j 4 --output-json /tmp/js_scorecard/language_all.json
# milestone
python3 tools/test262_runner.py --full -j 4 --output-json /tmp/js_scorecard/full.json
```

---

## Dependency-ordered march (forward)

Attack **fail volume × foundational** first. Class/modules/async sit on top of ops+function+iter.

| Mole | Target | Why first | Fail mass (lang-all) |
|------|--------|-----------|----------------------|
| **M19** | compound-assignment + core arith/bitwise | Pure opcode; unblocks assign/class code | ~280 compound alone |
| **M20** | assignment LHS / strict assign edges | Builds on M19 | ~200 assignment |
| **M21** | call spread **error paths** (not TCO) | Completes call; spread already partial | call residual ~29 |
| **M22** | function residual + function-code + TDZ defaults | Function surface after M18 | ~92 + ~172 |
| **M23** | eval-code | Needs call/function solid | ~292 @ 16% |
| **M24** | arguments edges (gen trailing-comma etc.) | Mapped done; gen/unmapped edges | ~139 |
| **M25** | for-of / iterator close | Gens solid; for-of next | ~386 for-of |
| **M26** | class (+ super) | Largest remaining volume | ~2000+2000 fails |
| **M27** | modules / import / dynamic-import | After class patterns | ~384+168+588 |
| **M28** | async / await / async-gen / for-await-of | Last major ES2017+ block | large |

**Skip / deprioritize:** TCO optional tests; forbidden-ext caller (legacy); pure whitespace unicode edges.

### M19 progress
- **Done:** Box `new Number/Boolean/String`; `ToNumber` unbox; `JSRT__ParseNumberStr` (invalid string → NaN). Compound **38%→60.6%**.  
- **Left:** private fields (#x) ~48; strict eval/arguments assign; remaining S11 Date/object ToPrimitive.

### M21 progress
- **Done:** `JSVM_IterableToArray` — `exc_prop` after factory/next/getters; `__get_` on @@iterator; `__get_value`/`__get_done`; generator `.next` fallback; GenNext pending rethrow.  
- **call:** **69%→79%** (63→73). All `spread-err-*` pass (16/16).  
- **Left on call:** eval-spread/strictness (M23), TCO (skip), object-spread order/symbols, with-base.

---

## Strong foundations (do not regress)

| Area | Status |
|------|--------|
| dstr (fn+gen) | 100% |
| generators | 90% (FDI-at-call, nest GenNext) |
| Function.name/length/call/apply/bind | M18 |
| mapped arguments | 43/43 |
| batch isolation | M18b gval rewind |
| control flow / keywords / ASI / block-scope | strong |

---

## History (compact)

| When | What |
|------|------|
| M15–16 | dstr 186/186, mapped 43/43 |
| M17a–c | GenNext CALL-like first-resume; assign clobber; FDI-at-call + nest → gen dstr **372/372**, gens **473→502** |
| M18 | Function.name/length + call/apply/bind + gen [[Prototype]] |
| M18b | Batch gval_pool rewind → language-all **42%→56%** (+3321 pure honesty) |
| M19a | Number/Boolean/String boxing + ToNumber unbox → compound **38%→59%** |
| M19c | `JSRT__ParseNumberStr` — string ToNumber invalid→NaN (not 0) |
| M21 | IterableToArray throw/getter/gen rethrow → call **69%→79%**, spread-err **16/16** |
| Scorecard 2026-07-14 | language-all **13441/23899**; gens 90%; function 84%; call **79%** |

---

## Agent rules

1. Midgate green after every mole.  
2. No false greens — generators/function/call claim only with `--no-batch` when in doubt.  
3. Update this file when a mole closes (one row in History + Status numbers).  
4. Smells → `AILANG-WARTS.md`.  
5. Compliance > speed. Wrap > write.
