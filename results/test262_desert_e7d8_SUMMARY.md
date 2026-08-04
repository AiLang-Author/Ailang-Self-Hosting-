# M128e7d8 — %TypedArray%/%ArrayBuffer% length accessors (dependency layer)

**Desert tip:** **1219 / 2931 (41.8%)**  
**vs e7d7:** 1112 → **1219** (**+107**)  
**vs e7d0:** 566 → **1219** (**+653**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | **27.0%** |
| DataView | 28.0% |
| TypedArray | **44.7%** |
| TypedArrayConstructors | **50.8%** |

## Why this order

`length` / `byteLength` / `byteOffset` / `buffer` were stamped as **own data** on every instance. ES puts them as **accessors on the prototype** reading internal slots. That blocked prop-desc tests and any code that expects `gOPD(instance, "length") === undefined` while `instance.length` still works via proto.

## Changes

1. **Stop stamping** public `length`/`byteLength`/`byteOffset`/`buffer` on TA instances (keep `__ta_*` / `__ab_*` slots).
2. **Install getters** on `%TypedArray%.prototype` and `ArrayBuffer.prototype.byteLength` via `__get_*` + placeholder + attr `{E:false,C:true}`.
3. Getters **TypeError** if `this` is not the right brand.
4. **`ArrayBufferCreate`** always sets `[[Prototype]] = ArrayBuffer.prototype` so buffers allocated from TA ctors get the accessor too.

## Next (dependency order)

- DataView `byteLength`/`byteOffset`/`buffer` accessors (same pattern)
- SpeciesCreate polish → map/filter/slice (~60 fails each)
- buffer-arg / object-arg ctor edges
- detach model; AB transfer/resize later

## Full-suite 95%

Built-ins morning ~30% → e7d6 full **43.1%**; desert tip **41.8%**. Keep peeling foundation before method surface.
