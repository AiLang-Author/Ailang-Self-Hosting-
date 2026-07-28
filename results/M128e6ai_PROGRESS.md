# M128e6ai progress — with over the line (95.6%)

**Date:** 2026-07-28  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| GET_WITH resolve-only | No GetProperty (assignment no longer fires get trap early) |
| SET_WITH deleted binding | Sloppy: no Set recreate; strict: ReferenceError |
| Proxy | `getOwnPropertyDescriptor` + `defineProperty` traps |
| Reflect | Always in polyfill; `Reflect.set` OrdinarySet-with-Receiver |
| Int32Array | Minimal polyfill for TypedArray with tests |
| throw_delivered | Catch delivery flag (partial free-var has-trap path) |

### Measured (legacy single-process / `--no-batch`)

| Suite | Score |
|-------|------:|
| **statements/with** | **173/181 (95.6%)** — was 171/181 batch-equiv, **+2 real**; from 135 **+38** |

Batch mode can under-report (shared process pollution); use `--no-batch` for with.

### Green this slice

- set-mutable-binding-idref-with-proxy-env (+ compound)
- set-mutable-binding-binding-deleted-with-typed-array (sloppy)

### Residual (~8)

| Cluster | Notes |
|---------|--------|
| has-property-err, unscopables-*-err | Nested free-var has/get trap throw still becomes RE sometimes |
| binding-deleted unscopables (3) | Free-var / unscopables delete path |
| typed-array strict | assert.throws(ReferenceError) not firing |
| cptn-abrupt-empty | Flaky / completion edge |

### Carry forward

1. Free-var EnvLookup has-trap throw delivery (throw_delivered end-to-end)  
2. Batch harness full isolate between tests  
3. Strict deleted-binding ReferenceError under with  
4. G2 language ≥95% overall  
