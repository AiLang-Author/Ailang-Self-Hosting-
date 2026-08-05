# M128e7e progress — optional-chain continuation

**Date:** 2026-07-29  
**Tip parent:** M128e7d

## This commit

MEMBER_DOT / MEMBER_BRACKET: if left spine contains OPT_MEMBER|OPT_BRACKET|OPT_CALL,
emit JMP_IF_NULLISH before GET (and before key eval for brackets). Fixes `o?.c.#f`.

## Measured

| Suite | Score |
|-------|------:|
| elements | **1351 pass / 95 fail** (93.4% runner) |
| vs e7d | **+1 fixed, 0 reg** |
| with | **181/181** |

### New green
- private-field-after-optional-chain
