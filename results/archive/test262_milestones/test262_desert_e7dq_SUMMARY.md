# M128e7dq — TypedArray fill converts value once

**Desert tip:** **1617 / 2931 (55.5%)** (stable vs e7dp)  
**vs e7d0:** 566 → **1617** (**+1051**)

## Changes

- **`%TypedArray%.prototype.fill`**: `ToNumber` / `ToBigInt` once before the index loop (ES contentType conversion), so `valueOf` is not re-invoked per element.

## Ladder

```
e7dp 1617 → e7dq 1617 (fill once; conversion-once green)
```
