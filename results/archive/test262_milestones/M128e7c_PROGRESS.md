# M128e7c progress — private method not writable (PrivateSet)

**Date:** 2026-07-29  
**Branch:** `master`  
**Parent:** M128e7b

---

## This commit

| Area | Change |
|------|--------|
| Private SET | Method-kind: throw TypeError if private lives on proto (not own) or !CanAssign |
| Private method install | Attr bits `C` only (!W !E) so later PrivateSet fails |

## Measured (no-batch samples)

| Test | Result |
|------|--------|
| private-method-not-writable | **pass** |
| private-static-method-not-writable | **pass** |
| set-access-of-private-method | **pass** |
| static-field-init-with-this | pass (reg) |
| class-field-is-observable-by-proxy | pass (reg) |
| private residual sample (15) | 7/15 |

## Next

prod-private-method, double-init brand, nested shadowing, eval-in-class.
