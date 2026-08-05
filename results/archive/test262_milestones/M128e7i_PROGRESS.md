# M128e7i progress — computed field `#` string + private name division

**Date:** 2026-07-29  
**Parent:** M128e7h

## This commit

1. **Class parse:** clear `name_ptr` after computed ClassElementName so leftover
   private name from prior element does not false-dup (`#m` then `["#m"]`).
2. **Lexer:** `PRIVATE_NAME` is a division-preceding token (`this.#m / 11`).

## Measured

| Suite | Score |
|-------|------:|
| elements | **1362 pass / 83 fail** runner **94.3%** |
| vs e7h | **+7 fixed, 0 real fail reg** |
| with | **181/181** |

### Newly green (clobber / visibility cluster)
- private-field-is-not-clobbered-by-computed-property
- private-method/getter/accessor not-clobbered / visible-in-computed-properties
- private-field-with-initialized-id-is-visible-in-computed-properties
