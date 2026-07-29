# M128e7 progress — class field_init free-var

**Date:** 2026-07-29  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| `JSCompState.in_field_init` | Flag while compiling `__field_init__` body |
| `JSComp__EmitVarGet/Set` | Force free-var (slot=-1 → GET_FREE/SET_FREE) when in_field_init — field_init only has local 0 = `this` |
| CONSTRUCT base path | On field-init throw: rethrow pending + pop construct frame if still live |

## Measured

| Suite | Score | Notes |
|-------|------:|-------|
| **statements/class/elements** | **1351 pass / 107 fail / 8 t/o / 68 err** | runner pass% **92.7%** (pass/(pass+fail)); base was 1326 pass |
| elements delta vs base | **+25 fixed, 0 regressed** | free-var + abrupt instance fields |
| **statements/with** | **181/181 (100%)** | regression OK |
| **class/dstr** | 1860 pass + 60 batch `harness_eof` | sample 20/20 no-batch green; batch flake not real fail |
| free-var probe `f = x + 1` | pass | |

### Notable fixes (base → e7)

- literal-names family (after-same-line / multiple-definitions / …)
- `init-value-defined-after-class`, `init-value-incremental`, `init-err-evaluation`
- `fielddefinition-initializer-abrupt-completion` (+ super variant)
- several former timeouts → pass

### Residual (elements)

- private* bulk (~122)
- static computed propname constructor/prototype
- proxy field define observability
- eval/supercall-in-field edges
- `abrupt-completition-on-field-initializer` (static half of combined test)

## Next

L-B residual: static fields, private, then L-C subclass/super.
