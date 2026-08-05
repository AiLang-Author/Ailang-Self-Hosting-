# M128e7d5 — OwnPropertyKeys + Delete + toLocaleString

**Desert tip:** **905 / 2931 (31.0%)**  
**vs e7d4b:** 898 → **905** (+7)  
**vs e7d0:** 566 → **905** (**+339**)

| Category | Pass% |
|----------|------:|
| ArrayBuffer | 24.0% |
| DataView | 28.0% |
| TypedArray | **27.1%** |
| TypedArrayConstructors | 42.8% |

## Changes

1. **[[OwnPropertyKeys]]** via getOwnPropertyNames — integer indexes first, then user string keys; hide internal slots (buffer/length/__ta_*)
2. **[[Delete]]** — in-range index → false (strict TypeError); OOB → true
3. **toLocaleString** alias of toString/join on %TypedArray%.prototype

## Full-suite 95%

~2.0k desert fails remain. Next: detach model, BigInt TAs, buffer-arg edges, map/filter species polish.
