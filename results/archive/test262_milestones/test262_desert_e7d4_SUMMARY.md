# M128e7d4 — TypedArray DefineOwnProperty / gOPD / Float32

**Desert tip:** **898 / 2931 (30.8%)**  
**vs e7d3b:** 882 → **898** (+16)  
**vs e7d0:** 566 → **898** (**+332**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | 24.0% |
| DataView | 28.0% |
| TypedArray | **26.6%** |
| TypedArrayConstructors | **42.8%** |

## Changes

1. **Integer-index [[DefineOwnProperty]]** — Object/Reflect.defineProperty sets buffer via TA_Set
2. **Integer-index [[GetOwnProperty]]** — gOPD returns {value,w:true,e:true,c:true}; OOB → undefined
3. **ValidIndex clobber fix** — Length call no longer ate index
4. **Float32 soft IEEE** — int↔f32 bit encode/decode for values in ±2^24

## Full-suite 95%

Still ~2.0k desert fails (detach, BigInt, SAB, transfer, deep species). Keep grinding.
