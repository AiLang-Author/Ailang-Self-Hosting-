# JS Engine — Built-ins Leg (post-G2 language)

**Status:** ACTIVE — primary grind  
**Supersedes (language march):** [`JS-DEPENDENCY-PLAN.md`](../JS-DEPENDENCY-PLAN.md), language sections of [`BROWSER_CONFORMANCE.md`](../BROWSER_CONFORMANCE.md)  
**Language tip:** M128e7bt — **language pass/(pass+fail) ≈ 95.9% (G2 met)**  
**Built-ins baseline:** M128e7bb full suite — **built-ins ≈ 32%** (7.6k / 23.5k)  
**Product goal:** a *real* JS engine (language + core standard library), not 100% of every desert.

---

## 1. Your read (confirmed)

| Claim | Verdict |
|-------|---------|
| Language compliance is where most hobby engines never go | **Yes.** G2 language (~96% primary metric) is past the “can parse modern JS” wall. |
| Closing language → 100% is the wrong next mountain | **Yes.** Residual is long-tail / exotic / bleeding (`using`, class error harness, unicode regexp edges). |
| Publish value = Ailang-readable engine + LLM-friendly structure | **Yes.** That is the contributor magnet; not chasing 100% Temporal. |
| Built-ins are when Pinocchio becomes a real boy | **Yes.** Syntax without `Array`/`Object`/`Promise`/`String` is a dialect, not a JS engine people run apps on. |

**Pinocchio frame:**  
- **Language (done enough)** = wooden body that walks and talks (classes, modules, async, import).  
- **Built-ins (this leg)** = nerves and hands: the *standard library* the web and Node assume exists.  
- **Not required for “real”:** Temporal, full TypedArray/Atomics, every Proxy trap, ShadowRealm — those are deserts. Stub or late-phase.

You don’t need to know JS deeply: **built-ins = the objects and methods that ship with every engine** (`[].map`, `Object.keys`, `Promise.then`, `"hi".slice`, …). test262 has ~**23.5k** tests for them — almost as large as the entire language suite.

---

## 2. What “built-ins” means (plain English)

```
Language  =  how you write programs   (if, class, import, await, …)
Built-ins =  what already exists when the program starts
             Object, Array, String, Function, Promise, Map, Math, …
```

In this repo they live mainly in:

| File | Role |
|------|------|
| `Librarys/Browser/JSVM/Library.JSVMBuiltins.ailang` | Realm install: construct natives, wire prototypes |
| `Librarys/Browser/JSVM/Library.JSVMArrayMethods.ailang` | `Array.prototype.*` |
| `Librarys/Browser/JSVM/Library.JSVMStringMethods.ailang` | `String` / `RegExp` methods |
| `Librarys/Browser/JSVM/Library.JSVMDispatch.ailang` | Native call dispatch (huge) |
| `Librarys/Browser/Library.JSBridge.ailang` | Bridge IDs, host glue |
| `Librarys/Browser/JSVM/Library.JSVMPromiseJobs.ailang` | Promise jobs / microtasks |

Contributors can open one method family, read Ailang, fix a mole, re-run a path. That is the design bet.

---

## 3. Mountain size (from last full suite M128e7bb)

| Section | Pass% | Pass | Fail-ish | Total |
|---------|------:|-----:|---------:|------:|
| **language** (since G2, ~e7bt) | **~96%** | ~22.4k | ~1.3k | 23.6k |
| **built-ins** | **~32%** | ~7.6k | ~16k | 23.5k |
| full suite (then) | ~59% | 29k | — | ~50k |

### Built-ins by volume (e7bb) — where the mass is

| Object | Pass% | Pass | Fail | Tot | Strategy |
|--------|------:|-----:|-----:|----:|----------|
| **Object** | ~65% | 2202 | 1203 | 3414 | **B1 core** — product path |
| **Array** | ~72% | 2192 | 857 | 3083 | **B2 core** |
| **String** | ~59% | 782 | 551 | 1334 | **B3 core** |
| **Promise** | ~66% | 447 | 230 | 677 | **B4 core** |
| **Function** | ~59% | 302 | 210 | 515 | **B4** |
| **RegExp** | ~30% | 578 | 1360 | 1945 | **B5** — hard; feeds String |
| **Number / Math** | ~38–51% | — | — | ~667 | **B4** light |
| **Map / Set** | ~33–44% | — | — | ~587 | **B4** |
| **Date** | ~8% | 49 | 569 | 618 | late / partial |
| **Proxy / Reflect** | ~18–37% | — | — | ~465 | partial (you already ship Reflect helpers) |
| **TypedArray + ctors** | ~0% | ~4 | ~2.1k | ~2.2k | **DESERT** — stub / late |
| **Temporal** | ~1% | 38 | 4550 | 4588 | **DESERT** — do not grind |
| **Atomics / SharedAB / DataView / AB** | ~0% | 0 | ~1.2k | — | **DESERT** |

**Rule:** deserts can stay near zero forever for a publishable engine. Core OA/S/P (Object/Array/String/Promise) cannot.

---

## 4. Goals (this leg)

| Tier | Target | Meaning |
|------|--------|---------|
| **G2 language** | ≥95% lang pass/(pass+fail) | **DONE** (e7bt) |
| **B-core** | Object, Array, String **each ≥80%**, then **≥90%** | Usable day-to-day JS |
| **B-async** | Promise **≥80%** → **≥90%** | Real async apps |
| **B-product** | Map/Set/Function/Number/Math **≥70%** each | “Runs normal library code” |
| **G3 full** | full test262 **≥70%** then **≥80%** | Optional milestone; deserts optional |
| **Not a goal** | 100% language or 100% built-ins | Diminishing returns |

Full-suite math (rough): language already ~22k pass. Built-ins need roughly **+8–12k passes** to feel “real”; Temporal alone is 4.5k fails you can ignore.

---

## 5. March order (dependency, not vanity)

```
PHASE L — Language          ✅ G2 met — opportunistic only
        │
        ▼
PHASE B — Built-ins (ACTIVE)
  B0  Baseline built-ins rescore (tip e7bt+) — pin Object/Array/String/Promise %
  B1  Object   → 80% → 90%     (keys, assign, create, defineProperty, proto, freeze family)
  B2  Array    → 80% → 90%     (mutate + iterate + higher-order: map/filter/reduce/…)
  B3  String   → 80% → 90%     (slice/split/replace; RegExp-backed last)
  B4  Promise + Function + Number/Math + Map/Set  (product cluster)
  B5  RegExp depth (only as needed by String / real apps)
  B6  Symbol / JSON / Reflect polish
        │
        ▼
PHASE D — Deserts (optional, published as “unsupported / partial”)
  Temporal · TypedArray · Atomics · SharedArrayBuffer · DataView full · import-bytes
        │
        ▼
PHASE P — Publish story
  README scoreboard · contributor “fix Array.prototype.X” map · Ailang-first layout
```

### Why this order

| First | Why |
|-------|-----|
| **Object** | Everything is an object; property model is the spine. |
| **Array** | App code + test harnesses + iterators touch arrays constantly. |
| **String** | UI, parsers, network; methods are discrete moles (good for contributors). |
| **Promise** | Without it, async language features are theater. |
| **Map/Set/Function** | Library code (bundlers, frameworks) assume them. |
| **RegExp last among core** | Large fail mass, unicode hell; only deepen when String demands it. |
| **Deserts never block publish** | Document “not yet” honestly. |

Language residuals (class error bucket, for-of edges, try/for-in) only get time when they **block** a built-in path (e.g. iterators ↔ Array methods).

---

## 6. How to work a mole (contributor / LLM loop)

```bash
# Rescore one mountain
python3 tools/test262_runner.py --paths 'built-ins/Object' -j 8 --timeout 12
python3 tools/test262_runner.py --paths 'built-ins/Array'  -j 8 --timeout 12
python3 tools/test262_runner.py --paths 'built-ins/String' -j 8 --timeout 12
python3 tools/test262_runner.py --paths 'built-ins/Promise' -j 8 --timeout 12

# Single method family (example)
python3 tools/test262_runner.py --paths 'built-ins/Array/prototype/map' -j 8

# Full suite only at milestones (slow ~50 min)
python3 tools/test262_runner.py --full -j 8 --timeout 12 --output-json results/test262_full_TIP.json
```

**Loop:** pick highest fail mass under B1–B3 → read one test → find native ID in `JSBridge` / dispatch → fix in Ailang → local commit every green round → no push unless asked.

**Code org (reader-first):**
- Prefer method-shaped functions and short comments; leave breadcrumbs (`M128e…`) as today.
- **Hard rule:** prefer **new library files** over growing any source past ~**1500 LOC**. Files larger than that are a smell and most models struggle. Split by concern (e.g. `Library.JSVMObjectMethods.ailang`, `Library.JSVMMapSet.ailang`) rather than stuffing `JSVMDispatch` / `JSBridge`.

---

## 7. Scoreboard (fill on each baseline)

| Slice | e7bb full | B0 (e7bt tip) | e7bu | tip e7c2 | Notes |
|-------|----------:|-------------:|-----:|---------:|-------|
| Object | 64.7% | **72.7%** | **73.1%** | **82.0%** ✅ B1 80% | defineProperty 85%; array attr spine; assign Set |
| Array | 71.9% | **74.9%** | | **78.4%** | concat IsConcatSpreadable; ARR_OF ID fix |
| String | 58.7% | **62.2%** | | **65.4%** | |
| Promise | 66.0% | **65.5%** | | **66.7%** | |
| built-ins overall | 32.3% | (core OA/SP **71.4%**) | | core climbing | deserts still drag full % |
| language | ~87% | **~96% G2** | G2 | — | freeze language campaign |

**e7bu:** `Library.JSVMObjectMethods.ailang` (new); symbol registry; assign boxes primitives.  
**e7bz–e7c2:** SET_PROP/GET_PROP ARRAY accessors; ArrSetLen non-config; length defineProperty; assign throw; concat; Array.of ID uncollide.

Update this table in place; don’t spawn another parallel plan file.

---

## 8. Doc hygiene (deprecate, don’t delete yet)

| Doc | Action |
|-----|--------|
| **`Plans/JS_BUILTINS_PLAN.md`** (this file) | **Canonical** for the built-ins leg |
| `JS-DEPENDENCY-PLAN.md` | Mark **HISTORICAL** — language march archive; point here for next work |
| `BROWSER_CONFORMANCE.md` | Mark **STALE** scores (M65); link this plan + `results/test262_lang_m128e7bt_SUMMARY.md` |
| `results/M128e*_PROGRESS.md` | Keep as mole diary; no longer the roadmap |
| Language SUMMARY e7bt | Freeze as G2 language certificate |

---

## 9. Publish narrative (value prop)

When you ship the story:

1. **Language:** modern ES (classes, modules, dynamic import, TLA) at G2-class compliance.  
2. **Engine written in Ailang** — readable, SSE/host-adjacent, LLM-navigable.  
3. **Built-ins in progress** with an honest map: core climbing, deserts labeled.  
4. **Contributor on-ramp:** “Implement `Array.prototype.flat` — here’s the file and the test path.”

That is more compelling than “we’re 0.3% from 100% language.”

---

## 10. Immediate next actions

1. **B0** — built-ins rescore on current tip (Object / Array / String / Promise paths) so B-core numbers are post-G2.  
2. **Deprecate banner** on `JS-DEPENDENCY-PLAN.md` + `BROWSER_CONFORMANCE.md` → link this plan.  
3. **B1 start** — Object fail mass: sort by subdirectory, crush highest ROI methods first.  
4. Language: no dedicated grind; only if a built-in is blocked.

---

## One-liner

> **Language made the puppet walk. Built-ins give it hands. Deserts can wait. Publish the readable engine.**
