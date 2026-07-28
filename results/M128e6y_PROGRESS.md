# M128e6y progress — OwnPropertyKeys integer-index order + Object.keys symbols

**Date:** 2026-07-28  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| `JSRT__StringIsIntIndex` | Canonical integer-index string → value or -1 |
| `JSRT_ObjKeys` | Integer-index keys ascending, then other strings (OwnPropertyKeys order) |
| `Object.keys` | Filter engine symbol keys `@@sN` (not string keys in ES) |
| OBJ_SPREAD / rest | Still uses full ObjKeys incl. symbols for getter side effects |

### Measured

| Suite | Score |
|-------|------:|
| **obj-rest** | **26/26 (100%)** |
| **assignment/dstr** | **333/368 (99.1%)** |
| A6 / 8.14.4 / cover | held |

### Residual dstr (~3 fails)

Iterator-close / throw paths on residual.
