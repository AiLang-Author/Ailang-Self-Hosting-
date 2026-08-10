# Ailang JS Engine — Master Status

**Living document** for the pure-Ailang JavaScript VM (Browser stack).  
**Updated:** 2026-08-05 · **Tip:** `9f4e6c52` (M128e7e1 full suite + Array.from fix)  
**Branch:** `master`

This file supersedes scattered plans and scoreboards for day-to-day navigation:

| Doc | Role now |
|-----|----------|
| **This file** | **Source of truth** — scores, architecture, roadmap, browser readiness |
| [`BROWSER_CONFORMANCE.md`](../../BROWSER_CONFORMANCE.md) | Short scoreboard pointer (kept for links) |
| [`Plans/JS_BUILTINS_PLAN.md`](../../Plans/JS_BUILTINS_PLAN.md) | Historical built-ins leg notes (superseded) |
| [`JS-DEPENDENCY-PLAN.md`](../../JS-DEPENDENCY-PLAN.md) | Language-march archive |
| [`JS-USABILITY-PLAN.md`](../../JS-USABILITY-PLAN.md) | Early usability notes (archive) |
| [`results/archive/`](../../results/archive/) | Old handoffs + intermediate test262 summaries |

---

## 1. What this is

A **self-hosted ECMAScript engine written in Ailang**, embedded in the Ailang native browser stack:

```
HTML/CSS (layout/render)  ↔  JSBridge  ↔  JSEngine
                                    ↕
                         Lexer → Parser → Compiler → JSVM
                                    ↕
                              Built-ins / natives
```

**Not** a V8/SpiderMonkey clone and **not** Node. Target: honest test262 progress, runnable page scripts, and an engine that is *fully specified where implemented* — weeds-level compliance, not demo stubs.

---

## 2. Current scores (authoritative)

### Full test262 (~49.7k)

| Metric | M128e7d6 (2026-08-03) | **M128e7e1 (2026-08-05)** |
|--------|----------------------:|--------------------------:|
| Pass | 33,494 | **34,218** |
| Overall pass/total | 67.4% | **68.8%** (runner table ~69.6% pass/(pass+fail)) |
| Language | 94.6% | **93.4%** pass/total |
| Built-ins | 43.1% | **47.3%** |
| Wall | ~53 min | ~50 min |

Artifacts: [`results/test262_full_m128e7e1_SUMMARY.md`](../../results/test262_full_m128e7e1_SUMMARY.md)

### Language G2 (primary metric)

| Metric | M128e7bt (2026-08-02) |
|--------|----------------------:|
| pass/(pass+fail) | **~95.9%** — G2 met |
| pass/total | ~94.6% |

Artifact: [`results/test262_lang_m128e7bt_SUMMARY.md`](../../results/test262_lang_m128e7bt_SUMMARY.md)

### Desert (ArrayBuffer / DataView / TypedArray / TAC)

| Tip | Pass/Total | % |
|-----|----------:|--:|
| e7d0 start | ~566/2931 | ~19% |
| **e7e1** | **2090/2931** | **71.6%** |

~2.5 weeks of desert grind: **+1,400** desert passes. Residual is mostly **BigInt TA**, **resizable**, **SAB/Atomics**, then thinner core.

### B-core product builtins (e7e1 full dump, approx)

| Builtin | Pass% |
|---------|------:|
| Object | ~82% |
| Array | ~85% |
| String | ~71% |
| Promise | ~66% |
| Function | ~69% |

---

## 3. Architecture map (where to edit)

| Area | Path |
|------|------|
| Realm / install / natives | `Librarys/Browser/JSVM/Library.JSVMBuiltins.ailang` |
| Opcode dispatch (large) | `Librarys/Browser/JSVM/Library.JSVMDispatch.ailang` |
| Array methods | `Librarys/Browser/JSVM/Library.JSVMArrayMethods.ailang` |
| TypedArray / AB / DataView | `Librarys/Browser/JSVM/Library.JSVMTypedArray.ailang` |
| String / RegExp methods | `Librarys/Browser/JSVM/Library.JSVMStringMethods.ailang` |
| Promise jobs | `Librarys/Browser/JSVM/Library.JSVMPromiseJobs.ailang` |
| Bridge IDs, Array.from, host | `Librarys/Browser/Library.JSBridge.ailang` |
| Engine entry | `Librarys/Browser/Library.JSEngine.ailang` |
| Compiler / parser / lexer | `Librarys/Browser/JSCompiler/`, `JSParser/`, `Library.JSLexer.ailang` |
| test262 runner | `tools/test262_runner.py` |
| Harness sources | `JS-tests/test262_harness.ailang`, `test262_harness_batch.ailang` |

**Rebuild harness after VM changes:**

```bash
./ailang.x JS-tests/test262_harness.ailang test262_harness.x
./ailang.x JS-tests/test262_harness_batch.ailang test262_harness_batch.x
```

**Score:**

```bash
# Desert (fast feedback)
python3 tools/test262_runner.py \
  --paths built-ins/ArrayBuffer,built-ins/TypedArray,built-ins/TypedArrayConstructors,built-ins/DataView \
  -j 4 --timeout 8 --output-json results/test262_desert_TIP.json

# Language
python3 tools/test262_runner.py --categories all -j 8 --timeout 12

# Full (~50 min)
python3 tools/test262_runner.py --full -j 8 --timeout 12 \
  --output-json results/test262_full_TIP.json
```

---

## 4. Roadmap — what still needs doing

### A. Near-term (high ROI, before other projects)

| Priority | Work | Why |
|----------|------|-----|
| P0 | Language clean rescore + fix real regressions (not load noise) | Hold G2; full dump showed 93.4% pass/total |
| P0 | Array / Object / String / Promise residual moles | Everyday app scripts |
| P1 | TypedArray core remainder (non-BigInt, non-resizable) | Finish desert core |
| P1 | `not-a-constructor` / IsConstructor consistency on natives | Spec hygiene |
| P2 | RegExp property-escapes / unicode (large fail mass) | Built-ins scoreboard |

### B. Deferred features (real work, not “holes”)

| Feature | Status | Note |
|---------|--------|------|
| **Temporal** | Effectively empty (~4.6k residual tests) | Stands on modern Date/Intl-ish substrate + large new surface. Correct to defer until core libs are solid. |
| **BigInt TypedArray** | Partial / failing | Needed for desert ≥90% |
| **Resizable ArrayBuffer** | Largely failing | ES2024; product-dependent |
| **SharedArrayBuffer / Atomics** | Thin / failing | Needs memory model + workers story |
| **Full Proxy** | Partial | Many traps still soft |
| **ShadowRealm / import defer edges** | Long tail | Language residual |

### C. Full suite 95% (~+13k passes)

Not a tip-grind. Requires Temporal **or** a redefined denominator, large RegExp/Date/Iterator/Atomics tracks, and multi-month effort. See §6.

### D. Browser shell (beyond pure JS)

| Layer | Rough state |
|-------|-------------|
| HTML tokenizer / DOM | Present |
| CSS / layout / flex/grid | Substantial Ailang layout stack |
| JS ↔ DOM bridge | Present; incomplete Web API surface |
| Networking (HTTP, URL, cookies) | Present libraries |
| Images (JPEG etc.) | Partial |
| Full Web platform (fetch completeness, workers, storage, media…) | Far |

---

## 5. How far from a *usable* browser engine?

Honest product answer — not test262 vanity:

| Use case | Ready? |
|----------|--------|
| Embedded scripting / demos / Ailang apps calling JS | **Yes** — language + core builtins are past “toy” |
| Simple interactive pages (DOM + event + Promise + Array/Object/String) | **Mostly** — expect API holes and layout/CSS gaps |
| “Runs real modern websites” | **No** — missing Web APIs, incomplete CSS/layout fidelity, no Temporal, weak RegExp unicode, no workers/SAB story |
| Spec-complete JS (test262 ≥95% full) | **No** — months; Temporal alone is a project |
| Spec-complete *language* (syntax/semantics) | **Close** — G2 met; residual is long-tail |

**Bottom line:** You have a **serious, weeds-level JS VM** with strong language compliance and mid-built-ins, plus a **real browser skeleton**. You do **not** yet have a general-purpose web browser competitor. That is expected and not a failure of the 2.5-week desert leg — that leg moved TypedArray/AB/DV from “empty desert” to **~72%** of a 3k hard suite.

**Temporal:** Correctly deferred. It is not “a few tests under Date”; it is a large standard library with its own abstract ops. It does not unlock everyday script usability the way Array/Object/Promise polish does.

---

## 6. ROI and pause recommendation

**Last ~2.5 weeks:** desert + full rescore — excellent ROI for typed binary data and engine credibility.

**Diminishing returns now** without opening BigInt-TA / Temporal / RegExp-unicode tracks.

**Suggested pause:** park JS at e7e1 tip, use this doc as resume point, spend 1–2 weeks on CAD/CAM or other product. Resume JS with either:

1. Language G2 hold + B-core polish, or  
2. BigInt TypedArray if desert 90%+ is the goal, or  
3. Web API / DOM bridge if *browser usable* is the goal.

---

## 7. Resume checklist

```bash
git log -1 --oneline
# expect M128e7e1-era tip
./ailang.x JS-tests/test262_harness_batch.ailang test262_harness_batch.x
python3 tools/test262_runner.py --paths built-ins/TypedArray -j 4 --timeout 8 | tail -15
# read this file §2 scores; re-run --full only after a major milestone
```

When landing a new tip: update **§2 scores** and the tip hash in the header — do not create another parallel “master plan” file.

---

## 8. Design principles (keep)

1. **Spec where implemented** — no fluffy half-stubs that lie to test262.  
2. **Pure Ailang VM** — self-hosted readability for contributors/LLMs.  
3. **Full suite after major milestones**, desert/path slices while grinding.  
4. **Local commits; push when intentional.**  
5. **Deserts last** relative to language G2 (already done); Temporal/SAB last relative to B-core.

---

*End of master status. Archive of older milestones: `results/archive/`.*
