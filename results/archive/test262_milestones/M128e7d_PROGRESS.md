# M128e7d progress — static constructor method + PrivateFieldAdd

**Date:** 2026-07-29  
**Branch:** `master`  
**Parent:** M128e7c

---

## This commit

| Area | Change |
|------|--------|
| Class parse | `static constructor()` no longer sets constructor bit 8 — normal static method |
| PrivateFieldAdd | TypeError if private field already own on receiver (double add) |
| PrivateFieldAdd | TypeError if receiver non-extensible (`__extensible__` false / sealed / frozen) |

## Measured

| Suite | Score | Notes |
|-------|------:|-------|
| **class/elements** | **1350 pass / 96 fail / 8 t/o** | runner **93.4%** (was 93.0% e7c) |
| vs e7c_full | **+5 fixed, 0 regressed** | |
| statements/with | **181/181** | regression OK |
| syntax/valid (no-batch) | 27/30 | static-ctor-* green |

### Newly green

- privatefieldadd-typeerror
- grammar-static-ctor-meth-valid
- grammar-static-ctor-async-meth-valid
- grammar-static-ctor-async-gen-meth-valid
- grammar-static-ctor-accessor-meth-valid

## Residual notes

- private-class-field-on-nonextensible still fails on **private method/accessor** install (fields path green)
- static `['prototype']` field TypeError still open (blanket SET_PROP block breaks class setup)
- optional `o?.c.#f` short-circuit still open

## Next

Private method per-instance brand on non-extensible; optional-chain continuation; nested private shadow.
