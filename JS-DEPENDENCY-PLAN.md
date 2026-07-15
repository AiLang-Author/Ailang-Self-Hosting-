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
| **language `--all`** | **~14800/24700 (59.9%)** | full-run language slice post-M20e |
| compound-assignment | **298/454 (65.6%)** | M19d Number.Inf/NaN, Mod NaN, ToPrimitive, A7 key-once |
| assignment | **407/485 (86.0%)** | M20e rtrn-close 47/47; was 83.5% |
| full `--full` (49998) | **17617/49998 (35.3%)** | post-M20e batch; built-ins drag (Temporal/TA) |

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
- **Done (M20a):** LHS-first `base[prop]=`; SET_ELEM single ToPropertyKey.  
- **Done (M20b):** CoverToPattern default swap; stack pollution; RHS result stash → **341**.  
- **Done (M20c):** `EmitDstrBind` for MEMBER_DOT/BRACKET targets; `THROW_CONST` + const name registry; TDZ on write. **341→372 (78.6%)**.  
- **Done (M20d):** OBJ_SPREAD string/array index keys; array dstr try→`ITER_CLOSE` on throw; LRef-before-IteratorStep; `ITER_CLOSE` kind 0/1; CallFunc restore. Assign **372→395**.  
- **Done (M20e):** GenReturn closes open iter (rtrn-close); track open_iter on GET_ITER; GET_ITER defers next-callability; close suite **47/47**. Assign **395→407 (86.0%)**.  
- **Left:** yield-ident residual; put-let TDZ free; S11 with/eval; fn-name; ~12 timeouts.



### Full scorecard 2026-07-14 (post-M20e)
- **Full:** 17617/49998 (**35.3%**), T/O 42. JSON: `/tmp/js_scorecard/full_m20e.json`
- **Language:** ~14798/24712 (**59.9%**) — up from 56.2% language-all.
- **Built-ins:** ~2679/23744 (**11.3%**) — not mole-critical yet (Temporal 4.5k fails alone).

#### Language fail mass → next moles (adjust)
| Priority | Area | Fail ~ | Notes / mole |
|----------|------|--------|----------------|
| 1 | **class + super** | ~3800 | **M26** — largest language residual; expressions+statements class |
| 2 | **modules / dynamic-import** | ~1000 | **M27** — dynamic-import 588; module-code + import-defer |
| 3 | **for-of / for-in / iter** | ~970 | **M25** — for-of 195 fails; for-await is M28 |
| 4 | **eval-code** | ~690 | **M23** — direct+indirect; annexB eval piles on |
| 5 | **async / for-await / async-gen** | ~640+ | **M28** — after class/modules foundation |
| 6 | **function residual** | ~510 | **M22** — defaults/TDZ/arrow edges; function stmt ~80% |
| 7 | **compound-assignment** | ~167 | **M19 residual** — private #, with/eval putvalue |
| 8 | **arguments** | ~200 | **M24** — unmapped/strict edges |
| 9 | **with** | 163 | Defer or bundle with M23 (scope chain) |
| 10 | **assignment residual** | ~80 | M20 nearly done (86–89%); yield-ident / strict |
| — | call | ~28 | M21 nearly done |
| — | generators | gens ~80–83% | residual FDI/yield edges |

#### Built-ins (later / parallel tracks)
Temporal (4528), Object (2842), Array (2436), RegExp (1514), TypedArray (1438), Promise (576), Date, Iterator, Set/Map…

#### Mole order adjustment
Keep M22→M23→M24→M25, but **front-load M26 (class)** if chasing language % — class alone is ~38% of language fails.  
Alternatively: finish **M22 function** (unblocks class methods) then **M26**, with **M25 for-of** as a short parallel after M20 close work.

### M22 progress
- **Done (M22a):** Arrow formal default+pattern wrap → arrow **92.4%**.
- **Done (M22b):** Formal TDZ for defaults → trio **87.8%** (929/1058); arrow **93.0%**.
- **Left:** lexical this/super/new.target; scope-body-lex; strict 13.x; annexB function-code.

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
| M20b | dstr-assign: cover default swap; stack pollution fix; RHS result stash → assign **74.9%** |
| M20c | dstr member targets + const TypeError on reassign → assign **78.6%** |
| M20d | obj-rest-str; thrw/nrml IteratorClose + LRef-first; CallFunc restore → assign **83.5%** |
| M21 | IterableToArray throw/getter/gen rethrow → call **69%→79%**, spread-err **16/16** |
| M22a | `Object.prototype.isPrototypeOf`/`hasOwnProperty`; CONSTRUCT accepts fn as .prototype → function stmt **80%→81%** |
| Scorecard 2026-07-14 | language-all **13441/23899**; gens 90%; function stmt 81%; call **79%**; compound **66%** |
| Full 2026-07-14 post-M20e | full **17617/49998 (35.3%)**; language **~59.9%**; assign **86%**; close **47/47** |
| M22a | arrow formal default+pattern wrap → arrow **92.4%** |
| M22b | formal TDZ defaults → trio **87.8%** |

---

## Agent rules

1. Midgate green after every mole.  
2. No false greens — generators/function/call claim only with `--no-batch` when in doubt.  
3. Update this file when a mole closes (one row in History + Status numbers).  
4. Smells → `AILANG-WARTS.md`.  
5. Compliance > speed. Wrap > write.
