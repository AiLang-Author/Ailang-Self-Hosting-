# Browser JS Conformance — Living Scoreboard

**Updated:** 2026-07-16  
**Branch:** `gpu-45-may-baseline-restore`  
**Audience:** grind sessions + product planning for the embedded browser

---

## 0. Progress reality check (do not undersell this)

In roughly **four days** of focused grind (one CLI / agent track on this branch):

| Horizon | Score | Context |
|---------|------:|---------|
| Early full-suite / category baselines | **~18–38%** | midgate language slice / early full runs |
| Full suite 2026-07-15 (`full49k`) | **19244 / 49998 (38.5%)** | post-M26k class foundation |
| Full suite 2026-07-16 post Object/Array | **21783 / 49998 (43.6%)** | `/tmp/test262_full_m29h.json` |

**Δ on full 50k:** **+~2.5k passes** in a short window after class private work, then Object property model (M27a–c), then Array (M29h).  
Language alone moved into the **high 60s**; Object **~37% → ~54%**; Array **~46% → ~49%**.  

That is **engine-rewrite pace**, not “slow polish.” Keep reporting absolute deltas (pass count + pp), not only “still under 50% full suite.” Full-suite % is **dragged by Temporal/TypedArray/Map deserts**, not by idle work.

---

## 1. Goals (agreed)

### What “browser ready” means

A page script should reliably:

1. Functions, objects, arrays, control flow, classes (incl. private basics)  
2. Property model that matches developer intuition (defineProperty, create, freeze/seal)  
3. Arrays + strings that work on array-likes and common methods  
4. Promises enough for fetch / UI  
5. RegExp usable for validation  
6. DOM bridge path (not full WPT)  

**Not required for this phase:** Temporal, TypedArray/Atomics, full Proxy/Reflect, complete modules, full async-iterator `yield*`.

### Target bars

| Track | Definition | Near-term (days) | Browser-usable bar |
|-------|------------|------------------:|-------------------:|
| **Language** | `test/language` | **≥72–75%** | **≥80%** |
| **Core built-ins** | Object + Array + String + Function + Number + Math + JSON + Error + Promise | **≥55–60%** combined | **≥70–75%** |
| **Full suite** | `--full` (~50k) | **≥48–52%** | **≥75–80%** multi-phase only |

**Product pitch (honest):**  
> Target **75%+ language** and **70%+ core built-ins** (browser track).  
> Full test262 **50%+ this phase**; **75% of all of test262** needs Map/Set/TypedArray/RegExp depth and either Temporal impl or Temporal excluded from the score.

Optional score hygiene: report **full-suite excluding Temporal** (~45.5k tests) so 4.5k @ 1% does not drown progress.

---

## 2. Latest scoreboard (2026-07-16 post-M29h)

| Scope | Pass / Total | % |
|-------|-------------:|--:|
| **Full `--full`** | **21783 / 49998** | **43.6%** |
| language | 16310 / 23899 | 68.2% |
| built-ins | 4848 / 23521 | 20.6% |
| statements/class | ~3282 / 4369 | ~75% |
| expressions/class | ~3099 / 4059 | ~76% |
| Object | 1837 / 3411 | 53.9% |
| Array | 1502–1504 / 3081 | ~49% |
| String | ~294 / 1334 | ~22% |
| Promise | ~110 / 677 | ~16% |
| Temporal | 60 / 4588 | 1.3% |
| TypedArray / Map / Set / Proxy | ~0 | 0% |

JSON: `/tmp/test262_full_m29h.json` (also mirror under `results/` when re-baselined).

### Recent moles (this arc)

| Commit / mole | Focus |
|---------------|--------|
| M26k.8–k.11 | Private fields, yield*, class-factory brand, gOPD own |
| M27a | Large Number ToString; defineProperty ToPropertyDescriptor |
| M27b | Object.create(props); attr defaults; isFrozen/isSealed |
| M27c / M27c2 | getOwnPropertyNames / getOwnPropertyDescriptors |
| M29h | Array.of, copyWithin, findLast*, primitive array-like ToObject |

---

## 3. Next few days (ordered — agreed 1→5)

| # | Work | Why | Success signal |
|---|------|-----|----------------|
| **1** | **Array holes + reduce/map/filter/forEach** | Highest residual fail mass in Array; already warm | Array **≥55%** |
| **2** | **String.prototype depth** | Surface exists; edges unlock volume | String **≥35–45%** |
| **3** | **Promise + async enough for real scripts** | Browser UX path | Promise **≥25–35%**; fewer async flakes |
| **4** | **RegExp usable (not property-escapes)** | Forms / validation | Non-escape RegExp climb; defer Unicode props |
| **5** | **Defer** Temporal, TypedArray, Map/Set/Proxy unless a concrete page needs them | Desert greenfield | Stay out of tirage until core solid |

Supporting: Object defineProperty residual + gOPD polish when unblocking Array/String.

---

## 4. Test strategy (targeted + full regression)

This is what we have been hovering around — **make it explicit**.

### Tracks

| Track | Command / path | When |
|-------|----------------|------|
| **Midgate** | `python3 tools/js_midgate.py --rebuild --quick` | After **every** mole rebuild |
| **Feature slice** | `--paths built-ins/Array` or `--categories statements/class/elements` | While implementing; tight loop |
| **Core built-ins pack** | Object + Array + String + Function + Promise paths | After a multi-hour Object/Array/String push |
| **Language pack** | `--all` or language categories | After language moles |
| **Full regression** | `python3 tools/test262_runner.py --full -j 8 --output-json results/test262_full_<tag>.json` | After **every major feature milestone** (not every micro-fix) |

### Recommended cadence

1. **Micro-fix:** midgate + 1–2 path slices (e.g. `Array/prototype/map`).  
2. **Feature land (commit-sized):** midgate + feature suite (e.g. all `built-ins/Array`) + no class/elements regression if language-touching.  
3. **Major milestone** (e.g. “Array ≥55%”, “Object property model done”): **full `--full` rescore** + write `results/test262_full_<tag>.md` summary.  
4. Keep **`--no-batch`** for flaky language areas (generators/function) when diagnosing; batch for full suite wall-clock.

### Browser-track report (to add in runner when convenient)

```
language:          pass/total  %
core-builtins:     Object+Array+String+Function+Number+Math+JSON+Error+Promise
full-suite:        pass/total  %
full-ex-temporal:  pass/total  %   # optional
```

Until the runner prints this automatically, compute from JSON after full runs (as in grind sessions).

### Artifact convention

```bash
python3 tools/test262_runner.py --full -j 8 \
  --output-json results/test262_full_<mole>.json
# hand or script → results/test262_full_<mole>.md scoreboard
```

---

## 5. Deferred libraries (not “invalid JS”)

| Bucket | Treatment |
|--------|-----------|
| Temporal (~4.5k @ ~1%) | Exclude from browser-track %; last-round or never for shell |
| TypedArray / DataView / ArrayBuffer / Atomics | After core Array/String; needed for media/wasm later |
| Map / Set / Weak* | After Object/Array spine; high real-world value, medium size |
| Proxy / Reflect | After property model honesty |
| Staging / annexB piles | Only when unblocking a core mole |

---

## 6. Process rules (unchanged spirit)

- Midgate green after rebuild  
- No false greens; measure with test262  
- Wrap over write — thin JS surface on Ailang primitives  
- Celebrate **pass deltas** (+N, +pp) alongside remaining %  
- One major full rescore per milestone, not every edit  

---

## 7. Commands cheat sheet

```bash
# Rebuild harnesses
python3 tools/js_midgate.py --rebuild --quick

# Feature
python3 tools/test262_runner.py --paths built-ins/Array -j 8 --output-json /tmp/arr.json
python3 tools/test262_runner.py --paths built-ins/Object -j 8 --output-json /tmp/obj.json
python3 tools/test262_runner.py --categories statements/class/elements -j 8

# Milestone full regression (~32 min @ 8 workers)
python3 tools/test262_runner.py --full -j 8 --output-json results/test262_full_<tag>.json
```
