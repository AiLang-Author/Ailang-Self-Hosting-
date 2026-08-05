# M128e7g progress — private accessor get without getter → TypeError

**Date:** 2026-07-29  
**Parent:** M128e7e

## This commit

PrivateFieldGet on setter-only private accessor throws TypeError (instance home
path + fallback when only `__set_#name` is present).

## Measured

| Suite | Score |
|-------|------:|
| elements | **1356 pass / 90 fail** runner **93.8%** |
| vs e7e | **+5 fixed, 0 regressed** |
| with | **181/181** |

### Newly green
- get-access-of-missing-private-getter
- get-access-of-missing-shadowed-private-getter
- private-getter-shadowed-by-setter-on-nested-class
- private-method-access-on-inner-function
- private-method-shadowed-by-setter-on-nested-class
