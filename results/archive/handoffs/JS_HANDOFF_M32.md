# JS Engine Handoff — M32 (new session start here)

**Date:** 2026-07-17  
**Branch:** `gpu-45-may-baseline-restore`  
**HEAD:** `9a02b96a` — *JS M32: OA/S climb toward 80% — propertyHelper + defineProperty*  
**Why new session:** Compaction API broken (tool_choice none + server tools → HTTP 400). Context too large; continue from this file + planning docs, not chat history.

---

## 0. First 60 seconds (new agent)

```bash
cd /home/bob/Ailang-Self-Hosting-
git log -5 --oneline
# Read these in order:
# 1. results/JS_HANDOFF_M32.md          (this file)
# 2. JS-DEPENDENCY-PLAN.md              (OA/S 80% campaign)
# 3. BROWSER_CONFORMANCE.md             (scoreboard)
# 4. results/FULL_SUITE_M31c.md         (full suite floor)
```

```bash
# Green check after rebuild
./ailang.x JS-tests/test262_harness.ailang -o test262_harness.x
./ailang.x JS-tests/test262_harness_batch.ailang -o test262_harness_batch.x
./ailang.x JS-tests/test_js_e2e.ailang -o test_js_e2e.x
python3 tools/js_midgate.py --quick
```

**Product gate (user):** Object, Array, String each **≥80%** on test262 trees.

---

## 1. Where we are (scores)

### Full suite (M31c harness, authoritative floor)

| Scope | Pass/Total | % | Notes |
|-------|-----------:|--:|-------|
| **Full** | **19129/49998** | **38.3%** | `/tmp/test262_full_m31c.json` · vs M29h **43.6%** (**−2654**) |
| language | 14446/23899 | 60.4% | class mass regression post-UTF-16 |
| built-ins | 4087/23521 | 17.4% | Temporal/TA desert + regressions |
| Wall | ~34 min @ 8 workers | | |

### Post-M32 slices (newer than full JSON — use these for OA/S)

| Suite | Pass/Total | % | Trend |
|-------|-----------:|--:|-------|
| **Object** | **1830/3411** | **53.7%** | was 36.5% full → reclaiming toward M29h 53.9% |
| **defineProperty** | **623/1131** | **55.1%** | was ~39% |
| **Array** | **1451/3081** | **47.5%** | was 43.4% |
| **String** | **375/1223** | **30.7%** | was 27.5% |
| midgate e2e+core | **PASS** | | after every rebuild |

### Gap to 80% product bar

| | Now | Need ~80% | Passes still needed |
|--|----:|----------:|--------------------:|
| Object | 53.7% | ~2729 | **~+900** |
| Array | 47.5% | ~2465 | **~+1010** |
| String | 30.7% | ~979 | **~+600** |

---

## 2. What landed this arc (commits)

| Commit | What |
|--------|------|
| `503b24fa` **M31a** | P0 UTF-16LE JS strings (`JSRT_StrLen/Unit/Eq/Cmp/ToC/Emit`), `codePointAt` |
| `7999ba13` **M31b** | `\p`/`\P` BMP tables + PROP NFA |
| `6b4f5ac7` **M31c** | Loose aliases, unicodeSets `v` surface, property-escapes climb |
| full suite | 38.3% floor; regression map |
| `f79f190e` **M31d** | gOPD + FuncPropGet StrEq for name/length |
| `b889cd8d` **M31e** | ObjHas/MakeAttrKey/defineProperty accessors/GlobalHash units |
| `e8a5911b` | Plan: Object/Array/String **≥80%** each |
| `9a02b96a` **M32** | propertyHelper polyfill, stronger !configurable redefine, at() WIP |

**Rule:** Prefer **int** over float in Ailang. Feature slices over full 50k until OA/S hit gates. Midgate green after moles.

---

## 3. Architecture notes (don’t re-break)

### UTF-16 strings
- Payload: magic `0x31553616` @ +0, unit count @ +8, units LE @ +16  
- **length** = code units; astral = 2 units  
- PropTable / object keys: use **`JSRT_StrEq` / `StrUnit` / `StrLen`**, never assume C `GetByte` on JS string keys  
- DOM/eval paths still often **`StrToC`** (Latin-1 flatten)

### RegExp
- Thompson NFA in `Library.JSRegex.ailang`  
- `\p`/`\P`: `Library.JSRegexPropData.ailang` (generated BMP bitmaps)  
- `v` flag = bit 128; implies UNICODE for match; u+v SyntaxError  
- property-escapes slice ~202/613; unicodeSets ~68/152 (earlier M31c)

### test262 runner polyfills (`tools/test262_runner.py`)
- **Skips** `propertyHelper.js` and `regExpUtils.js` — engine-safe replacements in POLYFILL  
- Enhanced `verifyProperty` unlocked large Object descriptor mass  
- Do **not** re-enable full propertyHelper without fixing `call.bind` support

---

## 4. Fail mass → next moles (do this order)

### OA1 — Object.defineProperty (still largest Object bucket)
- **defineProperty** 623/1131 (55%) → need **≥70%** then Object **≥80%**  
- Fail themes: accessors, !configurable redefinition edges, symbols, array length, TypedArray (defer)  
- Code: `JSBridge__NDefineProperty` in `Library.JSBridge.ailang`  
- Attr bits: `JSBridge__MakeAttrKey` / `GetAttrBits` / `SetAttrBits` (UTF-16-aware)

### A1 — Array callbacks
- map/filter/reduce*/forEach/some/every ≈ half of Array fails  
- Holes, array-like, thisArg, species  
- Code: `Library.JSVMArrayMethods.ailang`

### A2 — splice/slice/concat/sort/push family
### A3 — `at` / `toSpliced`/`toSorted`/`toReversed`/`with` (partial `at` exists)

### S1 — String split / slice / substring / includes / starts / ends  
### S2 — replace/replaceAll, match/search, trim*  
### S3 — toString/valueOf boxing, remaining  

Code: `Library.JSVMStringMethods.ailang`

### Parallel support
- Class reclaim (was ~75% → ~62.5% post-UTF-16) helps method descriptors  
- RegExp depth **after** OA/S climb (user priority is Object/Array/String)

---

## 5. Known bugs / landmines

1. **Compaction failing (Grok CLI):**  
   `tool_choice 'none'` + server-side tools (`web_search`/`x_search`/`pdf_search`) → API 400.  
   Last good segment: `segment_015` (2026-07-16). Not fixable in-repo.

2. **String/Array `.at` method-call path flaky:**  
   `String.prototype.at.call("ab",0)` works; `"ab".at(0)` returned undefined in last smoke (MatchStringMethod/CALL_METHOD path). Needs finish if relying on `at` scores.

3. **Don’t re-open as primary:** Temporal, TypedArray, Map/Set, full UCD, Script `\p` mass.

4. **Unrelated dirty tree noise:** Accel/Display/AMDGPU/TextBuffer/notepad_ipc — **not** part of JS grind; leave alone unless asked.

5. **Batch vs no-batch:** generators/function/call honesty → `--no-batch` when grinding those.

---

## 6. Gates (run every mole)

```bash
python3 tools/js_midgate.py --rebuild --quick

python3 tools/test262_runner.py --paths 'built-ins/Object/defineProperty' -j 8
python3 tools/test262_runner.py --paths 'built-ins/Object' -j 8
python3 tools/test262_runner.py --paths 'built-ins/Array' -j 8
python3 tools/test262_runner.py --paths 'built-ins/String' -j 6
```

**Milestone:** all three Object/Array/String **≥80%**, then:

```bash
python3 tools/test262_runner.py --full -j 8 --output-json results/test262_full_<tag>.json
```

---

## 7. Key files

| Path | Role |
|------|------|
| `Librarys/Browser/Library.JSBridge.ailang` | defineProperty, Object natives, flags |
| `Librarys/Browser/JSRuntime/Library.JSRTObject.ailang` | ObjGet/Has/Keys, FuncProp* |
| `Librarys/Browser/JSRuntime/Library.PropTable.ailang` | keys + GlobalHash |
| `Librarys/Browser/JSVM/Library.JSVMArrayMethods.ailang` | Array methods |
| `Librarys/Browser/JSVM/Library.JSVMStringMethods.ailang` | String methods + array dispatch |
| `Librarys/Browser/Library.JSRegex.ailang` | RegExp NFA |
| `Librarys/Browser/Library.JSRegexPropData.ailang` | `\p` BMP tables (generated) |
| `tools/test262_runner.py` | harness polyfills |
| `JS-DEPENDENCY-PLAN.md` / `BROWSER_CONFORMANCE.md` | living plan |

---

## 8. Suggested first message in new session

> Read `results/JS_HANDOFF_M32.md`, `JS-DEPENDENCY-PLAN.md`, `BROWSER_CONFORMANCE.md`.  
> Branch `gpu-45-may-baseline-restore` @ `9a02b96a`.  
> Continue **Object/Array/String → 80% each**. Next mole: **OA1 defineProperty** residual (now 55%), then **A1 Array callbacks**, then **S1 String split/slice/includes**.  
> Midgate after every rebuild. No Temporal/TA. Prefer int. Full suite only at milestones.

---

## 9. User preferences (sticky)

- Prefer **int** over float in Ailang  
- Feature work / slices over constant full 50k rescores  
- Update planning docs when scores move  
- Object/Array/String **80%** is the product bar for usefulness  
- Ignore unrelated Claude/KVM/GPU dirt in the tree  

---

*Handoff complete. New session: open this file first.*
