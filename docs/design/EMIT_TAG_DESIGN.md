# AILang Emit Tag System — Design Document

A post-pass peephole optimizer at the code-emission layer. Eliminates
redundant load-after-store patterns that the front-end naturally
produces from code like `x = expr; use(x)`.

Location: `Librarys/Compiler/CodeEmit/Library.CEmitTags.ailang`

---

## Motivation

AILang's statement lowering emits many `MOV [RBP+offset], RAX` (store
local) instructions immediately followed by `MOV RAX, [RBP+offset]`
(load that same local). Every `x = expr; use(x)` pair generates this.
Per-function that's tens to hundreds of wasted instructions. At hot-
loop scale (regex state machines, character classification, tight
arithmetic) it measurably shows up in wall time.

The second load is always redundant when it directly follows the
store: RAX already holds the value we're about to re-read. If we NOP
out the dead load, we pay the store once and the value flows through
RAX to whatever uses it next.

This module tags relevant instructions at emit time, runs a single
post-emit pass that NOPs out the dead loads, and reports the hit rate.

---

## Data structures

### `FixedPool.TagClass` — enumerated tag kinds

| Name | Value | Meaning |
|------|-------|---------|
| `NONE` | 0 | Tag has been cleared (e.g. a LOAD we NOP'd). |
| `STORE_LOCAL` | 1 | `MOV [RBP+operand], RAX` — stores RAX to a local. |
| `LOAD_LOCAL` | 2 | `MOV RAX, [RBP+operand]` — loads local into RAX. |

New tag classes (ADD/MUL with known side-effects, CALL, labels, etc.)
can be added without changing existing consumers — each new class is
just a new integer and new dispatch arm in `EmitTag_Optimize`.

### `FixedPool.EmitTag` — module state

| Field | Initialize | Meaning |
|-------|-----------|---------|
| `tags` | `0` | `XArray` of tag entries (lazily created in `_Init`). |
| `enabled` | `1` | Master switch. Set to 0 to disable the optimizer without removing tag calls. |
| `patched` | `0` | Count of successful patches from the last `_Optimize` call. Used for debug/bench reporting. |

### Tag entry layout — 32 bytes

| Offset | Field | Meaning |
|--------|-------|---------|
| 0 | `code_pos` | Byte offset into `Emit.code` where the tagged instruction begins. |
| 8 | `byte_len` | Length of the tagged instruction in bytes. |
| 16 | `tag_class` | One of `TagClass.*`. Mutable — the optimizer writes `NONE` here when NOPing. |
| 24 | `operand` | Class-specific payload. For `STORE_LOCAL`/`LOAD_LOCAL` this is the RBP offset. |

---

## API surface

Small functions on purpose. Each does one thing; debugger-friendly.

| Function | Role |
|----------|------|
| `EmitTag_Init()` | Reset state. Called once at the start of every compile, before any emit. |
| `EmitTag_Add(pos, len, class, operand)` | Register a just-emitted instruction. Caller captures `pos = Emit.code_size` before emit and `len = Emit.code_size - pos` after. |
| `EmitTag_Optimize()` | Walk the tag list once, apply all known peephole patterns, record the patch count in `EmitTag.patched`. |
| `EmitTag_CanFuseStoreLoad(entry, next)` | Predicate: may the store at `entry` and load at `next` be fused? Returns 1 if all constraints hold. Used by `_Optimize` and by tests. |
| `EmitTag_NopBytes(pos, len)` | Overwrite a byte range of `Emit.code` with 0x90 (single-byte NOP). |
| `EmitTag_Dump()` | Debug: print every tag in the list. Not called by the compile pipeline; available for interactive poking. |
| `EmitTag_Free()` | Release the `tags` XArray and each entry allocation. Called once during compiler teardown. |

---

## The optimization pass

One pattern wired up today: **redundant LOAD immediately after a STORE
to the same local**.

Pseudocode for `EmitTag_Optimize`:

```
for i in 0 .. count - 2:
    entry = tags[i]
    next  = tags[i + 1]
    if entry.class == STORE_LOCAL and next.class == LOAD_LOCAL:
        if EmitTag_CanFuseStoreLoad(entry, next):
            EmitTag_NopBytes(next.code_pos, next.byte_len)
            next.class = NONE            # prevent re-match on further passes
            EmitTag.patched += 1
print "[EMIT-OPT] Patched N redundant loads"
```

Isolating the decision into `EmitTag_CanFuseStoreLoad` keeps
`_Optimize` tiny and makes the correctness rules testable in
isolation. New patterns add new predicates (`_CanFuseLoadLoad`,
`_CanElideStoreBeforeStore`, etc.) rather than growing `_Optimize`
into a mega-function.

### `EmitTag_CanFuseStoreLoad` — the correctness predicate

Returns 1 iff **all** of:

1. `entry.class == STORE_LOCAL && next.class == LOAD_LOCAL`
2. **Byte-contiguous**: `entry.code_pos + entry.byte_len == next.code_pos`
3. **Same local**: `entry.operand == next.operand`

The contiguity check (rule 2) is the critical correctness guard.
Tag-space adjacency does **not** imply code-space adjacency — any
instruction that isn't tagged (a `CALL`, an arithmetic op, any other
`MOV`, a label) emits untagged bytes that sit between the two tags.
Every untagged instruction is potentially a RAX clobber.

Example of the silent miscompile that rule 2 prevents:

```
MOV [RBP-8], RAX       ; tag 0: STORE_LOCAL offset=-8
CALL Something         ; UNTAGGED — returns a new value in RAX
MOV RAX, [RBP-8]       ; tag 1: LOAD_LOCAL offset=-8
```

Without the contiguity check, tags 0 and 1 look like a fuse candidate.
NOPing tag 1 leaves RAX holding `Something`'s return value when the
next instruction expects `[RBP-8]`. Silent wrong-result, no crash, no
warning. Rule 2 catches it because the `CALL` emits bytes that break
the `entry.code_pos + entry.byte_len == next.code_pos` invariant.

---

## Correctness invariants

### 1. Offset-based, not pointer-based, storage

Tags store byte offsets (`code_pos`), never raw pointers. Every use
re-reads `Emit.code` at call time. Consequence: the tag system is
robust against any future `Emit.code` realloc — the underlying buffer
can move, grow, or shrink and the offsets remain valid.

**Rule to uphold when extending:** never cache `Add(Emit.code, pos)`
across instruction emission. Always compute the effective address
fresh at the use site (inside `EmitTag_NopBytes`, inside any future
patcher). Violating this rule reintroduces a lifetime dependency on
the old buffer.

### 2. Contiguity implies RAX-preservation

For the STORE/LOAD pattern, byte-contiguity is a sound proxy for "no
intervening instruction clobbered RAX." Any instruction that could
clobber RAX emits at least one byte, so if the tags are byte-adjacent
there's nothing between them to clobber.

This proxy is pattern-specific. If a future pattern wants to fuse
across a small number of "RAX-safe" instructions (e.g. a store to a
different local, which reads but doesn't write RAX), the predicate
must walk the byte range and verify safety explicitly — a more
expensive analysis, but bounded in scope.

### 3. NOPing is jump-target-safe

`0x90` is a single-byte NOP that falls through. Replacing a
multi-byte instruction with an equal run of NOPs preserves any jump
target that lands at the start (it just falls through to the next
real instruction). Jump targets that land **inside** the NOP'd region
are the risk — but the contiguity check means the only bytes being
NOP'd are the LOAD instruction itself, which is not a typical
branch target. A label placed between STORE and LOAD would break
contiguity and the fuse would be rejected.

### 4. Post-pass ordering

`EmitTag_Optimize()` runs after `Emit_ResolveFixups()` and
`Emit_ApplyDataRelocations()`. At that point all jump offsets are
baked into the code; NOPing bytes doesn't invalidate a fixup because
the fixup has already been resolved. Running before fixups would be
wrong — the optimizer could move code that fixups still point at.

---

## How to add a new peephole pattern

Three steps:

1. **Add a tag class.** Extend `FixedPool.TagClass` with a new
   integer value. Existing consumers ignore unfamiliar classes.

2. **Tag the emit site.** In the X86 layer, capture `tag_pos =
   Emit.code_size` before the instruction bytes, emit normally, then
   call `EmitTag_Add(tag_pos, Subtract(Emit.code_size, tag_pos),
   TagClass.YOUR_CLASS, operand)`.

3. **Add a fusing predicate and dispatch arm.** Write a small
   `EmitTag_CanFuse<Pattern>(entry, next)` returning 1/0, and add a
   dispatch clause to `EmitTag_Optimize`. Keep the predicate pure — no
   side effects, just rule checks.

Do **not** inline new patterns into `_Optimize` directly. The dispatch
function must stay small enough to read in one screen. Predicates go
in siblings; emitters go in `EmitTag_NopBytes`-style helpers.

---

## Debug facilities

- `EmitTag_Dump()` prints every tag with class, position, length, and
  operand. Useful when a test produces wrong output — run with
  optimizer disabled, dump, enable, dump again, compare.

- `EmitTag.patched` exposes the hit count from the last
  `_Optimize` call. The optimizer prints it unconditionally. Watching
  it over the course of a compile gives a rough feel for how often
  the pattern fires.

- `EmitTag.enabled` can be flipped at runtime to bypass the optimizer
  without touching tag generation. Useful for A/B diffing compiled
  output: compile twice, diff the `.x` files, see exactly which bytes
  changed.

---

## Expected hit rate

The `x = expr; use(x)` pattern occurs in nearly every AILang
statement lowering. Rough estimate before measurement: 30-70% of
`LOAD_LOCAL` instructions will be immediately preceded by a matching
`STORE_LOCAL` and thus eliminable.

Calibration protocol once the module lands:

1. Compile `ailang_cli.ailang` with the optimizer — note
   `EmitTag.patched` and the final binary size.
2. Compile the same source with `EmitTag.enabled = 0` — note size.
3. Size delta / `patched` = average bytes saved per fuse. Expect 3-4
   bytes per eliminated LOAD (the `MOV RAX, [RBP+disp8]` encoding).
4. Rerun grep/regex benchmarks pre and post. Expected wall-clock
   impact: meaningful in tight loops (character classification,
   state dispatch), marginal in I/O-bound code.

---

## Future extensions, ranked by expected payoff

1. **Multi-load fusion.** After a fused STORE+LOAD, any *further*
   contiguous LOAD of the same local is also redundant. Extend the
   scan to walk forward from each STORE.

2. **CALL tagging.** Tag every call instruction. Opens up more
   patterns by letting predicates ask "is there an intervening
   RAX-clobber in this byte range?" without the full byte-contiguity
   requirement.

3. **Dead-store elimination.** `STORE_LOCAL X` followed eventually by
   another `STORE_LOCAL X` with no intervening `LOAD_LOCAL X` — first
   store is dead. Needs intra-basic-block reasoning; harder to verify
   across labels.

4. **Store-to-store immediate.** `MOV [RBP+X], RAX; MOV RAX, imm; MOV
   [RBP+Y], RAX` when Y is an independent slot and the intermediate
   RAX load could be rematerialized — niche.

5. **Commutative-operand canonicalization.** Not a peephole optimizer
   concern per se; belongs earlier in the pipeline
   (`Optimize_BinaryMathOp`).

---

## Integration checklist

- [x] `Library.CEmitTags.ailang` — module body.
- [x] `Library.CEmitX86Mem.ailang` — tag `X86_MovRbpOffsetRax`
      (STORE_LOCAL) and `X86_MovRaxRbpOffset` (LOAD_LOCAL).
- [x] `ailang_cli.ailang` — import, `EmitTag_Init()` before
      `Compile_Init()`, `EmitTag_Optimize()` after
      `Emit_ApplyDataRelocations()`, `EmitTag_Free()` during cleanup.
- [ ] `EmitTag_CanFuseStoreLoad` predicate with byte-contiguity rule.
      **This is the correctness guard. Do not ship without it.**
- [ ] 3-stage bootstrap (`ailang6.x` → EX1 → EX2 → EX3) to confirm
      the compiler compiles itself under the new optimizer.
- [ ] Conformance sweep: `regextest.x` 24/24, `test_regex_dfa.x`
      20/20, all 57 CoreUtils rebuild, `smoke_ailang_utils.sh` 40/40.
- [ ] Post-land measurement: `EmitTag.patched` hit count on a full
      `ailang_cli.ailang` self-compile, and before/after wall time on
      grep no-prefix monster pattern.
