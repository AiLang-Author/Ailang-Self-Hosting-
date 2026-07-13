# JS Engine — Dependency-Ordered Fix Plan

**Updated:** 2026-07-13  
**Rule:** Fix in dependency order. No false greens. Mid-gate after every mole; full ~50k only at milestones.

---

## Status (post Mole 16 + Mole 17 WIP)

| Gate | Result |
|------|--------|
| e2e | **36 asserts / 0 fail** |
| mid-gate `--quick` | **e2e + core PASS** |
| dstr (`function/dstr`) | **186/186 (100%)** |
| mapped args | **43/43 (100%)** |
| generators (no-batch) | **231/556 (41.5%)** — was **222/556**; **+9** |
| generators (batch) | **~204/556** — undercounts; prefer `--no-batch` for gen |
| statements/function | **324/451 (71.8%)** |
| expressions/call | **57/92 (62.0%)** |

---

## Gates

```bash
python3 tools/js_midgate.py --rebuild   # after engine edits
python3 tools/js_midgate.py --quick     # e2e + core
python3 tools/test262_runner.py --categories statements/generators,expressions/generators --no-batch -j 4
python3 tools/test262_runner.py --categories statements/function,expressions/call -j 8
python3 tools/test262_runner.py --full -j 8 --output-json /tmp/test262_full.json   # milestones only
```

**Any mid-gate red = stop and fix.**

---

## March forward

### Done
| Mole | Outcome |
|------|---------|
| **15** | **CLOSED** dstr 186/186 |
| **16** | **CLOSED** mapped 43/43 — strict, accessor, free-var gval, CallFunc args, DELETE unmap, defineProperty !C, arrow lexical args |

### Mole 17 — Generators first-resume (IN PROGRESS)
| Work | Status |
|------|--------|
| GenNext: PushFrame + rest packing + arguments | **done** |
| RETURN base frame via `fp==0` after pop | **done** |
| Save/restore `frame_envs` across yield | **done** |
| `JSVM_Reset` clears gen slab pos | **done** |
| Gen param **dstr** (236 fails, stmt 124/186 vs expr 12/186) | **next** |
| forbidden-ext / name / prototype / yield* | later |

**Honest score:** no-batch **231/556 (+9)**. Prefer `--no-batch` for gen gates until batch isolation is solid.

### NEXT after Mole 17
1. Finish gen dstr (close gap expr vs stmt; error paths)  
2. Strict function edges (`caller`/`callee`, `13.*-s`)  
3. Call leftovers (eval-spread)  
4. Re-full test262 milestone  

### Explicitly deprioritize
async/gen/class trailing-comma args, TCO, `with`, full Date/String until gen/strict cleaner.

---

## Progress log (compact)

| When | Milestone | Notes |
|------|-----------|-------|
| M15 residual | dstr **186/186** | CallFunc nest; gen throw; class name |
| M16 | mapped **43/43** | accessor + free-var + arrow args |
| M17 WIP | gen **231/556** | first-resume CALL-like; +9 no-batch |

---

## Agent rules

1. Mid-gate green after every mole.  
2. Generators: use `--no-batch` for honest scores (batch gen slab / isolation still weak).  
3. Prefer dependency order over raw fail counts.  
4. Update Status + March forward when a mole closes.  
5. Language smells → `AILANG-WARTS.md`.
