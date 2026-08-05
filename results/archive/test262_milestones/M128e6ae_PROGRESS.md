# M128e6ae progress — with suite Proxy + strict Function/eval

**Date:** 2026-07-28  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| Proxy `has`/`get`/`set` | Full ObjectEnv path via `HasProperty`/`GetProperty`/`SetProperty` on GET_WITH/SET_WITH + EnvLookup |
| HasProperty abrupt | Trap throw → rethrow (`-1`); unscopables Get via GetProperty |
| Function ctor | CALL/CONSTRUCT surface `SyntaxError` via `ThrowValue` (was swallowed → `undefined`) |
| Direct eval strict | `JSComp_Compile` preserves caller-inherited `is_strict` (with under strict eval) |
| Symbol ToString | `String(Symbol.unscopables)` → `Symbol(Symbol.unscopables)`; well-known descs |
| CompileFunc | Stop body compile on `error`; propagate strict+with |

### Measured

| Suite | Score |
|-------|------:|
| **statements/with** | **141/181 (77.9%)** — was 135/181 (~74.6%), **+6** |

### Wins this slice

- Proxy get-binding order logs (has → get unscopables → has → get)
- Function strict+with SyntaxError (`12.10.1-4-s`, `12.10.1-8-s`, …)
- Direct eval inherits caller strict (`12.10.1-10-s`)
- has-trap throw under with

### Residual with (~40 fails)

| Cluster | Notes |
|---------|--------|
| S12.10_A1.5/7/8/9/11/12, A3.4/5 | Classic for-in/with scope + this/delete |
| scope-var-open/close | `var` + free-var probe across ObjectEnv |
| cptn-abrupt-empty | UpdateEmpty(break/continue) completion |
| set-mutable-binding proxy | Need getOwnPropertyDescriptor/defineProperty traps for OrdinarySet log |
| unscopables-*-err | Accessor throw reaches catch but value/instanceof still wrong on free-var path |
| typed-array proto SetMutableBinding | TypedArray / proto chain |

### Next

1. Fix free-var unscopables accessor throw value (pending → catch)  
2. Minimal Proxy `getOwnPropertyDescriptor` / `defineProperty` for set logs  
3. scope-var-open/close + completion UpdateEmpty  
4. Classic S12.10 clusters  
