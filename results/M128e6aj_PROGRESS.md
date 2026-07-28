# M128e6aj progress — with 98.9% (free-var has-trap + ObjectEnv PutValue)

**Date:** 2026-07-28  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| THROW catch delivery | Pop intermediate frames (`LeaveFuncCode` / `RestoreArguments`) + set `throw_delivered` (parity with `JSVM_ThrowValue`) |
| `throw_delivered` lifetime | Clear at start of each `JSVM_Step` so catch-body free-var reads work; nested CallFunc still sees flag mid-opcode |
| GET_FREE / EnvLookup | Abort cleanly when has-trap already delivered catch |
| always GET_FREE | Non-local function idents walk `__cenv` (with ObjectEnv after with ends) |
| RESOLVE_FREE | Always for non-local assign; ObjectEnv HasBinding (HasProperty then unscopables) |
| SET_FREE / EnvAssign | ObjectEnv SetMutableBinding (strict deleted → RE; sloppy Set recreates); no GlobalHash clobber on ObjectEnv put; undeclared free-var → global (sloppy) |
| SET_WITH deleted | Sloppy still Set (spec); only strict throws RE |

### Measured (`--no-batch`)

| Suite | Score |
|-------|------:|
| **statements/with** | **179/181 (98.9%)** — was 173/181 (95.6%) |

### Residual (2)

| Test | Notes |
|------|--------|
| `cptn-abrupt-empty.js` | break/continue completion UpdateEmpty under with+eval |
| `set-mutable-binding-binding-deleted-with-typed-array-in-proto-chain.js` | VM error (Int32Array / deleted NaN path) |

### Green this slice

- has-property-err + free-var has-trap throws (assert.throws / outer free-var)
- unscopables deleted binding set (sloppy + strict free-var)
- typed-array-in-proto-chain **strict** ReferenceError
- prior A1.7 / with-nested function assign clusters retained

### Carry forward

1. cptn-abrupt-empty completion  
2. typed-array proto-chain deleted binding (sloppy)  
3. G2 language ≥95% overall  
4. Batch harness isolation (with still prefers `--no-batch`)
