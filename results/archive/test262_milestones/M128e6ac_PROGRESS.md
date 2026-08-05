# M128e6ac progress — minimal Proxy; assignment **100% of runnable**

**Date:** 2026-07-28  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| `Proxy` ctor (native 275) | `new Proxy(target, handler)` → object with `__p__` / `__p_t__` / `__p_h__` |
| CONSTRUCT allowlist | n_hid 275 constructible |
| `JSVM__HasProperty` | Proxy [[HasProperty]] via `has` trap |
| with ObjectEnv / `in` | Use HasProperty (GET_WITH + EnvLookup + IN) |

### Measured

| Suite | Score |
|-------|------:|
| **expressions/assignment** | **450 pass / 0 fail (100% of executed)** |
| with-bindings keyed order | **pass** |

### Notes

Minimal Proxy: has trap only (enough for with free-var ResolveBinding order). get/set/ownKeys later.
