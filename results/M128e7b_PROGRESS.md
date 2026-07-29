# M128e7b progress — static this, field Proxy define, Proxy GET

**Date:** 2026-07-29  
**Branch:** `master`  
**Parent:** M128e7 (field_init free-var)

---

## This commit

| Area | Change |
|------|--------|
| Static fields | Set `this = ctor` before initializer (DefineField receiver = F) |
| SET_PROP field_define | Proxy `[[DefineOwnProperty]]` trap + data descriptor W/E/C |
| SET_PROP_COMPUTED | same Proxy define path |
| SET_PROP | SetFunctionName for anon function values (literal keys) |
| GET_PROP | Proxy `[[Get]]` via `JSVM__GetProperty` (forward get trap / target) |

## Measured (elements, merged batch + no-batch recheck of error/timeout)

| Suite | Score | Notes |
|-------|------:|-------|
| **statements/class/elements** | **1404 pass / 122 fail / 8 t/o** | **91.5%** of 1534 |
| vs base (1326 pass) | **+79 fixed, 0 real regress** | batch harness_eof noise ignored |
| statements/with | **181/181** | regression OK |
| static-field-init-with-this | pass | |
| static-field-anonymous-function-name | pass | |
| public-class-field…proxy | pass | |
| class-field-is-observable-by-proxy | pass | |

### e7 full class (pre-e7b binary, still useful baseline)

| Slice | Pass | Fail | T/O | Pass% |
|-------|-----:|-----:|----:|------:|
| statements/class | 3640 | 516 | 98 | 87.6% |
| expressions/class | 3906 | 124 | 19 | 96.9% |

## Residual elements (true fails ~122)

private methods/fields, eval-in-class super, yield/async-gen private, syntax early-errors, nested shadowing.

## Next

L-B private residual → L-C subclass/super → L-D eval-code.
