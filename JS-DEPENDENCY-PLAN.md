# JS Engine — Dependency-Ordered Fix Plan

**Updated:** 2026-07-13  
**Rule:** Fix in dependency order. No false greens. Mid-gate after every mole; full ~50k only at milestones.

---

## Status (post Mole 15 residual + Mole 16)

| Gate | Result |
|------|--------|
| e2e | **36 asserts / 0 fail** |
| mid-gate curated | **25/25** + Mole 15/16 smokes |
| dstr (`function/dstr`) | **186/186 (100%)** |
| Full test262 (last re-full: post-Mole-9) | **10688 / 49998 (21.4%)** — re-full after Mole 16 residual |

**Δ Mole 15 closed:** CallFunc live-nest; gen THROW + ctor-this; custom Array @@iterator + this; computed obj keys; SetFunctionName for class.

---

## Gates

```bash
python3 tools/js_midgate.py --rebuild   # after engine edits
python3 tools/js_midgate.py             # e2e + js_midgate.js + curated ~25
python3 tools/js_midgate.py --quick     # e2e + core only
python3 tools/test262_runner.py --categories expressions/call,arguments-object,statements/function -j 8
python3 tools/test262_runner.py --full -j 8 --output-json /tmp/test262_full.json   # milestones only
```

**Any mid-gate red = stop and fix.**

---

## Load-bearing foundation (do not regress)

| Layer | What’s live |
|-------|-------------|
| Core | arith, strings, typeof, control, try/catch, throw |
| Objects | props, descriptors, freeze/seal, getters/setters, delete (**Symbol keys** via ToPropertyKey) |
| Arrays | methods, array + **iterable** spread; **`[][Symbol.iterator]` via Array.prototype** |
| Functions | call, arrow, defaults, rest, **closures (`__cenv`)**, eval re-entry (**func_pool restore**) |
| Call/args | CALL_SPREAD, arguments restore, **mapped + unmapped**, SetGlobal rebind, **args[@@iterator]** |
| OOP | `new`, prototypes, instanceof, basic classes |
| Builtins | Math, JSON, RegExp.test, Date.now, console, Symbol |
| Browser | DOM innerHTML/textContent, e2e green |

---

## March forward

### Done recently
| Mole | Outcome |
|------|---------|
| **11** | Object spread `{...o}`; polyfill no longer shadows `Object` |
| **12** | Mapped args × defineProperty; **SetGlobal never mutates shared gval slots** |
| **13** | Param dstr: bindings as locals, rest object, numeric keys, fn.name; **dstr →152/186** |
| **14** | Unmapped args when rest/default/dstr (bit 30); **args/fn jump** |
| **15** | **CLOSED — dstr 186/186**. CallFunc nest; gen throw+ctor-this; custom Array@@iterator; computed keys; class SetFunctionName |
| **16** | **CLOSED — mapped 43/43**. Per-fn strict; accessor defineProperty; free-var gval sync; CallFunc args restore; DELETE_PROP unmap; defineProperty reject !C; arrows lexical `arguments` |

### NEXT
| Work | Done when |
|------|-----------|
| Generators residual | gen-args surface green |
| Strict function edges | `13.*-s`, caller/callee forbidden |
| Call leftovers | eval-spread, typed spread-err (low browser value) |
| Re-full test262 | claim milestone |

### Then (dependency-ordered)
1. **Generators** — unlocks remaining gen-args surface  
2. **Strict function edges** (`13.*-s`, caller/callee forbidden)  
3. **Call leftovers** — eval-spread, typed spread-err (low browser value)  
4. **Re-full test262** — claim milestone  

### Explicitly deprioritize
async/gen/class trailing-comma args (~125 fails), TCO, `with`, full Date/String until core dstr/args clean.

---

## Progress log (compact)

| When | Milestone | e2e | Notes |
|------|-----------|-----|-------|
| start | baseline | 29/32 | 38% partial suite |
| Waves 0–3 | safety, DOM, descriptors, typed errors | **32/32** | full **7102 (14.2%)** |
| Moles 1–5 | strict assign, finally, args/callee, eval, prop gval | 32/32 | property persistence load-bearing |
| Moles 6–7 | closures → per-activation `__cenv` | 32/32 | free-var ops 90–92 |
| Moles 8–10 | call spread, Symbol.iterator, realm poison | 32/32 | full **10688 (21.4%)** |
| Mole 11 | object spread; polyfill `var Object` hoist fix | 36/0 | call **60/92** |
| Mole 12 | mapped defineProperty; SetGlobal rebind | green | mapped **6→36/43** |
| Mole 13 | dstr locals/rest/fn-name/numeric keys | green | dstr **100→152/186** |
| Mole 14 | unmapped args bit 30 | green | **fn 288/451, args 111/263** |
| Mole 15–16 | elision/close; ARRAY proto+@@iterator; eval func_pool | green | **dstr 154; mapped 37; SI 2/2** |
| M15 residual | CallFunc nest; gen throw; custom Array iter; class name | green | **dstr 186/186 (100%)** |

---

## Historical notes (compressed)

Key load-bearing bugs already fixed — don’t reintroduce:

| Theme | Fix |
|-------|-----|
| Property/func values die on return | `gval_pool`; stop rewinding `func_slab` for escaped fns |
| Closures share last loop value | `__cenv` / `__parent` + GET/SET_FREE, SET_FRAME_ENV |
| Nested call clobbers `arguments` | snapshot + restore via hash insert; never `undef_val` singleton |
| `typeof undefined === "object"` | SetGlobal refuses immortal singletons; restore fresh undef gval |
| Free-var / iterator during expand | CallFunc PushFrame+SetupCallEnv; IsSymbol full match |
| Object spread under CALL | OBJ_SPREAD stack = SET_PROP (no push after DUP) |
| `var Object = {}` in polyfill | hoist shadows builtin — never `var Object`/`var Array` |
| `var m = arguments; nested()` | **SetGlobal must rebind**, not mutate gval slot in place |
| Pattern params under-bind | AddPatternBindings + real local_count |
| Non-simple params | unmapped arguments (bit 30) |
| `[][Symbol.iterator]` undefined | ARRAY ObjGet walks `__proto__`; GET_ELEM Symbol → ObjGet |
| Post-eval function hang | **eval saves/restores `JSCompState.func_pool`** (CLOSURE payloads) |
| gOPD / delete ignore Symbol | **ToPropertyKey** not ToString |

---

## Agent rules

1. Mid-gate green after every mole.  
2. Prefer dependency order over raw fail counts (async/gen args are not “args moles”).  
3. One root cause per mole; don’t thrash unrelated surfaces.  
4. Update this file’s **Status** + **March forward** when a mole closes.  
5. Re-full only after 2–3 moles or before claiming a % milestone.  
6. Language-level smells → `AILANG-WARTS.md` (stdlib / ergonomics), not engine hacks forever.
