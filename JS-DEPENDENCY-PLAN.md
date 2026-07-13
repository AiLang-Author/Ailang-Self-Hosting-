# JS Engine — Dependency-Ordered Fix Plan

**Updated:** 2026-07-13  
**Rule:** Fix in dependency order. No false greens. Mid-gate after every mole; full ~50k only at milestones.

---

## Status

| Gate | Result |
|------|--------|
| e2e | **36 asserts / 0 fail** |
| mid-gate `--quick` | **e2e + core PASS** |
| dstr (`function/dstr`) | **186/186 (100%)** |
| mapped args | **43/43 (100%)** |
| generators (no-batch) | **347/556 (62.4%)** — was 222; **+125** |
| gen dstr | **248/372** (expr **124/186**, was 12) |
| statements/function | re-check after assign fix |
| expressions/call | re-check |

---

## Gates

```bash
python3 tools/js_midgate.py --rebuild
python3 tools/js_midgate.py --quick
python3 tools/test262_runner.py --categories statements/generators,expressions/generators --no-batch -j 4
```

**Generators: use `--no-batch` for honest scores.**

---

## March forward

### Done
| Mole | Outcome |
|------|---------|
| **15** | dstr 186/186 |
| **16** | mapped 43/43 |
| **17a** | GenNext CALL-like first-resume (rest, args, frames, yield env) |
| **17b** | **Assign clobber fix** — `f = function(){ n=1 }` no longer writes n; gen-expr dstr **+112** |

### Mole 17 residual (gen)
| Work | Notes |
|------|-------|
| Remaining gen dstr (~124 fail) | error paths, null/undef obj, iterator close edges |
| forbidden-ext / name / prototype | lower priority |
| yield* | 2 fails |

### Then
1. Strict function edges (`caller`/`callee`)  
2. Call leftovers  
3. Re-full test262  

---

## Progress log

| Milestone | Notes |
|-----------|-------|
| M16 | mapped 43/43 |
| M17a | gen first-resume → 231/556 |
| M17b | assign clobber → **347/556**, expr dstr 124/186 |

---

## Agent rules

1. Mid-gate green after every mole.  
2. Generators: `--no-batch` for honest scores.  
3. Update this file when a mole closes.  
4. Language smells → `AILANG-WARTS.md`.
