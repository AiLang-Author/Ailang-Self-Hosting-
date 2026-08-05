# M128e6w progress — non-writable assign, Number constants, cover name

**Date:** 2026-07-28  
**Branch:** `master`  
**Tip:** after e6v PutValue Reference

---

## This commit

| Area | Change |
|------|--------|
| `JSBridge_CanAssign` | Walk `[[Prototype]]`; inherited non-writable data → fail (no own create) |
| `Number` builtins | `MAX_VALUE` / `MIN_VALUE` / safe integers / `EPSILON` + RO Infinity/NaN attrs 0 |
| `ASTType.PAREN_EXPR` | Parenthesized expr keeps Cover identity |
| Assign compile | Unwrap PAREN for store; **skip** SetFunctionName on cover LHS |
| `JSValidate` | AST table size 80; PAREN_EXPR is assign/postfix target |

### Measured

| Test | Result |
|------|--------|
| `8.14.4-8-b_1/2` | **pass** |
| `11.13.1-4-14-s` | **pass** |
| `fn-name-lhs-cover` | **pass** |
| assignment (batch) | **431** pass / 20 fail (+1 scored; some `harness_eof` flaky) |
| with | 133/181 held |

### Residual

dstr yield/iter-close, obj-rest computed, super-computed-null, …
