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
| function (stmt) | **364/451 (81%)** | no-batch; M22a isPrototypeOf |
| function (prior combined) | **601/715 (84%)** | no-batch; re-score later |
| call | **73/92 (79%)** | no-batch; M21 spread-err 16/16 |
| mapped args | **43/43** | |
| **language `--all`** | **13441/23899 (56.2%)** | honest batch; was 42% before gval fix |
| compound-assignment | **298/454 (65.6%)** | M19d Number.Inf/NaN, Mod NaN, ToPrimitive, A7 key-once |
| assignment | **289/485 (63.5%)** | M20a LHS-first bracket assign; was ~59% |
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
- **Done:** Boxing; ParseNumberStr; **Number.POSITIVE_INFINITY/NEGATIVE_INFINITY/NaN**; Mod 0%0→NaN; **ToPrimitive** (toString/valueOf); **TO_PROP_KEY + CHECK_COERCIBLE** for compound `base[prop] op=` (ES5 order, key once). Compound **38%→65.6%** (275→298).  
- **Left:** private #fields ~48; A5/A6 putvalue+**with**/eval (~66, needs `with` stmt); 11.13.2-s strict eval (~31, M23); putvalue global-delete (~22); whitespace ~11.

### M20 progress
- **Done:** Simple `base[prop]=rhs` evaluates base→key→RHS (not RHS-first); SET_ELEM ToPropertyKey once (no pre-ToNumber). assignment **285→289**; compound held.  
- **Left:** dstr-assign mass; S11.13.1 A5/A6 (with/eval); strict LHS; fn-name; timeouts.

### M21 progress
- **Done:** IterableToArray throw/getter/gen; call **79%**; spread-err **16/16**.  
- **Left on call:** eval-spread (M23), TCO (skip), object-spread, with.

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
| M19d | Number.Inf/NaN; Mod NaN edges; ToPrimitive; compound bracket key-once → compound **65.6%** |
| M20a | assignment LHS-first for `base[prop]=`; SET_ELEM single ToPropertyKey → assign **63.5%** |
| M21 | IterableToArray throw/getter/gen rethrow → call **69%→79%**, spread-err **16/16** |
| M22a | `Object.prototype.isPrototypeOf`/`hasOwnProperty`; CONSTRUCT accepts fn as .prototype → function stmt **80%→81%** |
| Scorecard 2026-07-14 | language-all **13441/23899**; gens 90%; function stmt 81%; call **79%**; compound **66%** |

---

## Agent rules

1. Midgate green after every mole.  
2. No false greens — generators/function/call claim only with `--no-batch` when in doubt.  
3. Update this file when a mole closes (one row in History + Status numbers).  
4. Smells → `AILANG-WARTS.md`.  
5. Compliance > speed. Wrap > write.
