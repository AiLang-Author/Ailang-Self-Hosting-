# Ailang — Smelly Warts & Library Upgrade Candidates

**Living doc.** Capture language / stdlib friction that shows up while building the JS engine (and other large programs). Prefer a real library or language fix over another engine-local workaround when the pattern repeats.

Not a commitment to change anything tomorrow — a backlog of “this hurt, and a broader fix would pay rent.”

---

## Context

Ailang is already pleasant for LLM-assisted systems work: explicit FixedPools, named opcodes, no hidden GC surprises in the hot path, readable control flow. The VS Code shorthand mode is attractive; **without model fine-tuning** it will stay messy for free-form codegen — prefer long-form for anything that lands in-repo until a tuned model or formatter exists.

This file is about **stdlib / primitive gaps**, not “make Ailang into JS.”

---

## High-value library / language upgrades

### 1. String-keyed maps that are not PropTable-shaped
**Smell:** Every JS object/array side table reinvents “string → pointer” with hand-rolled PropTable, ArrSide, GlobalHash, attr keys (`__a_` + name). Symbol keys become `@@sN` strings by convention.

**Want:** First-class `Map[String, Address]` (or typed maps) in the system library with:
- insert / lookup / delete / iterate
- optional tombstones
- stable pointer identity for keys

**Payoff:** JS engine, DOM attr tables, compiler symbol tables, HTTP headers.

### 2. Growable byte buffers / string builders
**Smell:** Fixed `str_slab`, `STR_CAP`, manual `SetByte` loops to spell `"use strict"` and `"__proto__"`. Eval/func_pool backups hard-code sizes (`4096 * 40`).

**Want:** `ByteBuf` / `StringBuilder` with grow, append, freeze-to-c-string.

**Payoff:** Compiler string interning, JSON, HTTP, error messages.

### 3. Option / Result instead of `0` / `-1` / `XERROR` soup
**Smell:** `Array.Get` returns 0 for OOB (not a sentinel object); `PropTable_Lookup` returns `-1`; many call sites forget to check and crash or hang. JS dstr hangs were rooted in null JSValue pointers from ArrGet.

**Want:** Lightweight `Optional[T]` or explicit `Result[T, E]` in the standard library, or at least **one** documented null/error convention for Collections.

**Payoff:** Fewer silent hangs; better LLM codegen (model can pattern-match `if IsNone`).

### 4. Safe integer bitfields / flags type
**Smell:** Compiler packs rest / unmapped / (future) strict into `param_count` bits 29–31; formal count masks are easy to get wrong (`0x3FFFFFFF` vs `0x1FFFFFFF`). Frame offset 40 overloaded for async marker *and* constructor `this`.

**Want:** Either a `Flags32` helper with named bits, or room in descriptors for a real `flags` field without stealing from counts.

**Payoff:** Per-function strict mode, more CALL metadata without frame packing games.

### 5. Stack / arena scoped to a “transaction”
**Smell:** Eval must manually snapshot code, const pool, **func_pool**, stack, frames. Miss one (func_pool) → post-eval CLOSURE hangs after 60k steps.

**Want:** A standard “nested compile/execute session” or arena checkpoint API: `Checkpoint()` / `Restore()` covering compiler + VM side tables the language owns.

**Payoff:** eval, workers, multi-script documents, REPL.

### 6. Case-sensitive / consistent builtin names
**Smell:** `equalTo` vs `EqualTo` — one fails compile, one works; easy LLM footgun. Mixed `Or(equalTo(...), EqualTo(...))` in older code.

**Want:** Either accept both as aliases at compile time, or a formatter/linter that rewrites.

**Payoff:** Fewer “unknown function” rebuild loops for humans and models.

### 7. First-class slices / views over arrays
**Smell:** Manual `Add(ptr, Multiply(i, 8))` + `Dereference` for every arg buffer and property table walk.

**Want:** `Slice[T]` or typed pointer arithmetic helpers with bounds checks in debug builds.

**Payoff:** VM stack, arg packing, binary protocols.

### 8. Short-hand mode vs long-form (tooling, not runtime)
**Smell:** VS Code plugin shorthand is great for speed, risky for LLMs without fine-tuning (ambiguous sugar → wrong FixedPool layout).

**Want:**  
- Format-on-save that expands shorthand → canonical long form for git  
- Optional “strict long-form only” mode for agent sessions  
- Later: fine-tuned model on long-form Ailang corpus  

**Not a language wart** — a workflow wart worth documenting next to the plugin.

---

## JS-engine-local smells that might stay engine-local

These are *engine* design choices, not necessarily Ailang gaps:

| Smell | Note |
|-------|------|
| ARRAY vs OBJECT dual representation | Named props on ArrSide; indices on XArray. Proto walk must be duplicated (GET_ELEM / ObjGet). A single “object with elements” model would shrink code. |
| `typeof Symbol === "object"` | Spec is `"symbol"`; engine reports object. Polyfills and `typeof name === "string"` branches suffer. |
| Global `is_strict` | Needs per-function bit + CALL save/restore (Mole 16 residual). |
| verifyProperty in test polyfill | Incomplete vs real propertyHelper; Symbol-aware gOPD is load-bearing. |

---

## Suggested order if we invest in stdlib

1. **Map[String, Address] + ByteBuf** — highest reuse in this repo  
2. **Checkpoint/Restore for compile sessions** — eval-class bugs go away  
3. **Optional/Result convention** — hang-class bugs go away  
4. **Flags / descriptor fields** — clean per-fn strict, async, generator markers  
5. **Tooling: expand-shorthand + EqualTo alias** — LLM quality of life  

---

## How to add an entry

When something burns you twice:

```markdown
### N. Short title
**Smell:** what you wrote / hit  
**Want:** concrete library or language shape  
**Payoff:** who benefits  
```

Link from `JS-DEPENDENCY-PLAN.md` agent rules item 6.
