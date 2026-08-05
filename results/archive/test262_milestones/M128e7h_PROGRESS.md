# M128e7h progress — no data placeholder for private setters

**Date:** 2026-07-29  
**Parent:** M128e7g

## This commit

DEF_SETTER / DEF_SETTER_COMPUTED: skip own-key `undefined` placeholder for
mangled private names. Placeholder made PrivateFieldGet treat setter-only
accessors as present data fields (static missing-getter failed).

## Measured

| Suite | Score |
|-------|------:|
| elements | **1357 pass / 89 fail** runner **93.8%** |
| vs e7g | **+1 fixed, 0 real fail reg** |
| with | **181/181** |

### Newly green
- get-access-of-missing-private-static-getter
