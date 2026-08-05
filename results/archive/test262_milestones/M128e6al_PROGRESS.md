# M128e6al progress — with 100% (181/181)

**Date:** 2026-07-29  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| SET_WITH deleted After resolve | If binding deleted and `[[Prototype]]` is ARRAY (TypedArray polyfill): fall through to outer PutValue (avoids ObjSet corruption). Plain objects still Set/recreate (unscopables). |
| stillExists check | Drop `__get_*` ObjHasOnChain walk for stillExists (array protos crash). |

### Measured (`--no-batch`)

| Suite | Score |
|-------|------:|
| **statements/with** | **181/181 (100%)** |

### Residual

None in statements/with.

### Full suite

Full `--full` run started against e6ak harness (in progress) as M128e6ak baseline; e6al with-100% lands in parallel.
