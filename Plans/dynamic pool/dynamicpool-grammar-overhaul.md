# DynamicPool & Pool Operator Overhaul

## Summary

Define `DynamicPool` as the third pool type alongside `FixedPool` and `LinkagePool`. DynamicPool handles all eviction-based and lifecycle-managed memory patterns (LRU caches, FIFO queues, growable arrays, reference-counted slots) under a single construct with a `Policy` parameter. Introduce `&` as the access operator for DynamicPool slots, distinct from `.` (FixedPool fields) and `@` (LinkagePool chains).

DynamicPool currently exists in the grammar but is unspecified and undebugged. This is the right moment to nail down its semantics deliberately rather than retrofit later.

---

## Pool Type Taxonomy

Three pool types, three semantic contracts, three access operators:

| Pool Type | Semantic | Operator | Meaning |
|-----------|----------|----------|---------|
| FixedPool | Things stay the same | `.` | Fixed slots, all always live |
| LinkagePool | Things point at each other | `@` | Pointer-chained structures, stable references |
| DynamicPool | Things come and go | `&` | Managed slots with lifecycle, may be evicted |

The operator carries the semantic contract. A reader seeing `customer@account` knows they're traversing a stable pointer chain. A reader seeing `cache&key` knows they're touching managed lifecycle. The grammar enforces the distinction without needing comments.

---

## DynamicPool Grammar

```
DynamicPool.Cache {
    Policy=LRU
    Capacity=128
    "key": Initialize=0
    "value": Initialize=0
    "timestamp": Initialize=0
}
```

Pool-level configuration lives in the body, distinguished from fields by lack of quotes:
- Unquoted `Name=Value` at top of body → pool configuration
- Quoted `"name": attribute=value` → field declaration

This stays within the existing pool-body parsing pattern and adds one rule rather than introducing header-attribute grammar.

---

## Policy Values

Each policy specifies how membership changes after declaration:

| Policy | Behavior |
|--------|----------|
| `LRU` | Fixed capacity, evict least-recently-used when full |
| `FIFO` | Fixed capacity, evict oldest when full |
| `RefCount` | Slots evicted when reference count hits zero |
| `Manual` | Caller explicitly adds/removes slots |
| `Grow` | No capacity limit, allocates new slots as needed |

`Grow` is the only policy that doesn't evict — it expands. The others maintain a bounded slot count with explicit eviction semantics. Future policies (custom callback, generational) can be added without changing the grammar.

---

## The `&` Operator

`&` accesses managed slots in a DynamicPool. Mirrors `@` for LinkagePool but signals a different lifecycle contract:

```
slot = cache&"some_key"        // look up by key
slot&value = 42                // write to a field in the slot
result = cache&"key"&value     // chain: lookup then field access
```

Properties:
- Single-character operator (matches `@`)
- Grep-friendly — every DynamicPool access is one regex away
- Inherits C/C++ "reference to managed object" intuition
- Distinct from `.` (already overloaded across modules, fields, pool types)

Behavior on missing/evicted slots: returns 0/null, with explicit existence check via primitive (`PoolHasSlot(cache, key)` or similar).

---

## Open Design Questions

Decide these before implementation. Ordered roughly by impact:

### 1. Default Policy

What does `DynamicPool.Cache { ... }` without an explicit `Policy=` mean?

Options:
- **Error at definition time** ("DynamicPool requires explicit Policy")
- **Default to Manual** (caller controls add/remove)
- **Default to Grow** (acts like a growable array)

Leaning toward erroring out — implicit default for "dynamic" isn't obvious enough to be safe, and forcing the choice makes code self-documenting. Fits the "say what you mean" philosophy.

### 2. Capacity Units

Does `Capacity=128` mean:
- **128 slots** (record count) — fits eviction-driven policies cleanly
- **128 bytes** — fits arena-style Grow policy

Probably slots. Byte-level sizing can be a future optimization parameter if real usage demands it.

### 3. What `&` Actually Computes

- **Raw slot index** — fast but unsafe under eviction
- **Generation-counter handle** — slot index + version, errors loudly on stale access
- **Runtime-translated handle** — opaque, all validation in the runtime

Leaning toward generation-counter handle as the safe default. Invalidated references should error loudly, not silently corrupt. Cost is one extra word per handle.

### 4. Chaining Behavior

Does `cache&key&field` work? If yes:
- First `&` resolves the slot (by key)
- Second `&` accesses a field within the resolved slot

Parallels `@` chaining in LinkagePool. Probably yes, for consistency.

### 5. Missing / Evicted Semantics

What does `cache&missing_key` evaluate to?
- 0 / null (consistent with how absence is handled elsewhere)
- Trap / error
- Sentinel value

Probably null with explicit existence check, consistent with elsewhere in the language. Lets caller decide whether absence is an error or expected.

### 6. Bitwise Infix Collision

If infix is ever extended to include bitwise operators (`x & y` for BitwiseAnd in math contexts), `&` would collide with the pool access operator.

Resolutions:
- Require space-separated `x & y` for infix vs. no-space `cache&key` for pool access
- Decide bitwise stays named (BitwiseAnd) forever, never competes for `&`

Lean toward the second — consistent with current "bitwise stays named" stance, removes ambiguity permanently.

### 7. Pinning Semantics

How does a slot get pinned (excluded from eviction) and unpinned?
- Per-access pin (pin while in use, auto-unpin after expression)
- Explicit `Pin(slot)` / `Unpin(slot)` primitives with reference counting
- Pin flag on slot, manual lifecycle

Probably explicit primitives with refcount. Per-access is too implicit, manual flag is too error-prone.

---

## Implementation Plan

Parallel structure to `CCompilePool.ailang`:

1. Create `Library.CCompileDynamicPool.ailang` modeled on `CCompilePool.ailang`
2. Define `FixedPool.DynamicPoolRegistry` — same shape as PoolRegistry, plus policy and capacity fields
3. Add policy constants: `DynamicPolicy.LRU`, `DynamicPolicy.FIFO`, `DynamicPolicy.RefCount`, `DynamicPolicy.Manual`, `DynamicPolicy.Grow`
4. Implement `CompileDynamicPool_Declaration` — parse pool block, validate Policy and Capacity, register
5. Implement `CompileDynamicPool_SlotAccess` for `&` operator (lookup and field access)
6. Add introspection primitives: `DynamicPoolSize`, `DynamicPoolPolicy`, `DynamicPoolCapacity`, `DynamicPoolFillRate`
7. Add operations: `AllocateSlot`, `ReleaseSlot`, `TouchSlot` (LRU update), `PinSlot`, `UnpinSlot`, `HasSlot`
8. Wire into `CompilePool_TryCompile` dispatcher
9. Add static analysis pass for DynamicPool-specific bugs:
   - Slot access after release
   - Pin/unpin mismatch (refcount goes negative)
   - Capacity overflow without eviction policy
   - Iteration during modification

The dispatcher pattern is already in place. Compiler additions parallel what CCompilePool does — the template is proven.

---

## Migration / Compatibility

- FixedPool and LinkagePool grammar and semantics unchanged
- DynamicPool was previously unused, so no existing code breaks
- Arena library stays as a lower-level primitive that DynamicPool implementations can use internally
- The LRUPool / FIFOPool / RingPool ideas considered earlier all collapse into DynamicPool with policy

---

## Why This Design

**Three pool types, three operators, three contracts.** The grammar tells you which kind of pool you're touching without having to look back at the declaration. Each operator visually signals which pool semantics are in play. Reader doesn't have to hold extra context.

**Parameters specialize existing semantics, not switch between them.** Adding `Policy=LRU` to DynamicPool specializes its "things come and go" semantic. Adding the same to FixedPool would violate its "things stay the same" semantic. The architectural distinction is real and the language reflects it.

**Eviction is fundamentally about slots, not fields.** Policy belongs at the pool level. A "value" field doesn't evict independently from "key" in the same slot — the whole slot goes or stays together. Pool-level policy is the natural granularity.

**Reserved-but-unspecified is the cheapest time to define semantics.** DynamicPool exists in the grammar but has no entrenched usage. Nailing down what it means now is essentially free; doing it after years of usage would require migration.

**Generalize one construct, don't add new ones.** LRUPool, FIFOPool, RingPool — all the eviction-flavored variants — collapse into DynamicPool with different policies. Fewer keywords, single mental model, semantically consistent.

**The operator system pays interest.** Three pool types each with a clear access operator means future pool types (if any) follow a known pattern. The system has shape now.

---

## Status: Pre-implementation

Design ready to review. Implementation gated on:

1. Resolving open design questions above (especially Default Policy and `&` handle representation)
2. Bandwidth — don't disrupt in-flight browser work for this
3. Consider prototyping LRU policy as a library first to battle-test the API before grammar commit (the "library first, language second" discipline)

---

## Future Considerations (Out of Scope for v1)

- Custom eviction policies (user-supplied callback)
- Generational sub-pools within DynamicPool (young-gen / old-gen split)
- Per-slot metrics (hit rate, age, last-touch timestamp) exposed via introspection
- Cross-pool LRU (a single LRU ordering across multiple DynamicPools)
- Persistent backing (DynamicPool slots that survive process restart)

These are interesting but should not block v1. Add when real usage justifies them.
