# Compiler Memory Rework — Pool-Allocated AST

Apply the same ring-buffer/FixedPool pattern that dropped regex
compile RSS from ~12 GB → 256 KB (see `GREP_PERF_NOTES.md` and
`Library.Regex_Thompson.ailang` pools) to the AST. The frontend is
today the single biggest consumer of RAM during a compile.

---

## Measured current state

Peak RSS to compile a source file with the current compiler:

| Source | Source size | AST nodes | Peak RSS | Wall |
|---|---|---|---|---|
| `regextest.ailang` | ~50 lines | ~5 K (est) | **104 MB** | 0.26 s |
| `AiLang_CoreUtils/dist/grep_util/grep.ailang` | ~1 000 lines | ~20 K (est) | **155 MB** | 0.92 s |
| `ailang_cli.ailang` (self-compile, with imports) | 12 kB source | **82 638 total nodes** | **1 769 MB / 1.77 GB** | 5.28 s |

The 12 KB source file pulls 82 638 AST nodes into memory because
every `LibraryImport.*` recursively parses the full library tree.
That's ~8 orders of magnitude more memory than output size.

---

## Why it blows up

`Library.CASTCore.ailang:82` — `AST_Create`:

```ailang
node = XArray.XCreate(8)            // allocate node struct
XArray.XPush(node, node_type)
XArray.XPush(node, ASTState.auto_line)
... (6 field pushes) ...

children = XArray.XCreate(ASTState.max_children)   // allocate child list
XArray.XPush(node, children)

ASTState.node_count = Add(ASTState.node_count, 1)
```

**Two `XArray.XCreate` calls per AST node.** `XArray.XCreate` in
`Library.XArrays.ailang:63` calls `Arena_Alloc24()` for the struct
header plus a backing-data allocation sized by capacity. The Arena
rounds every small allocation up to a fixed slab class (24, 32, 64,
128, 256, 512, 1024, 2048, 4096 B). For a 64-byte node struct the
slab is 64 B; for an 8-element children array (8 × 8 = 64 B backing
data) it's another 64 B.

For 82 638 AST nodes that's **165 276 small allocations** — each
alive for the lifetime of the compile. At ~80 B per allocation the
"real" memory is ~13 MB, but the Arena's slab bookkeeping, free-list
headers, per-class chunks, and fragmentation push RSS to ~1.77 GB.

This is the exact same shape of problem `Library.Regex_Thompson.ailang`
had before the pool rework — the fix is the same.

---

## Plan — three pools

### 1. `ASTNodePool` — fixed-size node-struct slots

Today: `XArray.XCreate(8)` for each node, allocating an 8-element
XArray that lives forever. Each carries XArray overhead (size,
capacity, flags, data pointer).

Proposed: one up-front `Allocate(NODE_CAP * NODE_SIZE)` where
`NODE_SIZE = 64` (8 int fields). `AST_Create` hands out
`buf + head*64`, bumps `head`. Field access becomes
`Add(node, offset)` instead of `XArray.XGet(node, index)` —
faster and cheaper.

Sizing: conservative 256 K slots × 64 B = 16 MB reserved up front.
Covers any self-compile workload we've seen (82 K) with 3× headroom.

### 2. `ASTChildPool` — variable-size child slots

Each node has a child array. Today: `XArray.XCreate(max_children)`
always allocates at maximum capacity regardless of how many children
the node actually has. Most AST nodes have 0-3 children (leaf
literals, binary ops, etc).

Proposed: fixed small-slot pool with 8-entry slots (64 B backing).
Nodes needing >8 children get promoted to the `ASTChildOverflowPool`
which uses 64-entry slots. Rare.

Sizing: 256 K × 64 B = 16 MB for the 8-entry pool.
16 K × 512 B = 8 MB for the 64-entry pool (covers giant
function-call arg lists, Program nodes at top level).
Total ~24 MB reserved.

### 3. `ASTStringPool` (optional, phase 2) — string-interning pool

Identifiers and literal strings in AST nodes currently live where
the lexer put them (pre-allocated lexer buffer). Re-using those
references from the AST rather than copying is already what the
code does, so this pool may not be needed at all — verify before
building.

---

## Expected result

| Metric | Today | Target |
|---|---|---|
| `ailang_cli.ailang` compile RSS | **1 769 MB** | **< 80 MB** |
| `grep.ailang` compile RSS | 155 MB | < 40 MB |
| `regextest.ailang` compile RSS | 104 MB | < 30 MB |

~20-40× reduction, matching the magnitude of the regex-pool fix.

Wall time: expect **modest improvement** (10-30%) from pool
allocation being cheaper than Arena-slab + XArray-bookkeeping.
The big win is memory, not speed.

---

## Implementation order

1. **Instrument first.** Count `AST_Create` calls per compile and
   track max-children-per-node and max-depth distributions. Verify
   the 8-entry-typical / 64-entry-rare split before committing to
   pool sizes.
2. **Add `ASTNodePool` + `ASTChildPool`** to `Library.CASTCore.ailang`.
   Use same `FixedPool` + `buf` / `head` / `cap` pattern as
   `RegexFragPool` et al.
3. **Rewrite `AST_Create`** to hand out pool slots instead of
   calling `XArray.XCreate`. Field access migrates from
   `XArray.XGet/XSet(node, idx)` to `Dereference(Add(node, idx*8))`
   / `StoreValue(Add(node, idx*8), val)`. Every caller in the
   parser / semantic / codegen must move with it — this is the
   biggest surface-area change (~30-40 call sites).
4. **Replace the children-XArray** inside each node with a pool
   slot. Access functions `AST_GetChild`, `AST_AddChild`,
   `AST_GetChildCount` update to use the pool-backed slot instead
   of the embedded XArray.
5. **Do NOT reset the pools between compiles.** They're
   process-lifetime bump allocators, same invariant as the regex
   pools. (The regex lib's earlier "reset on each compile" bug
   corrupted prior handles by overwriting class-bitmap pointers —
   same category of risk applies here. Document in-line.)
6. **Verify with the 3-stage bootstrap.** EX1 = current compiler
   compiling patched source. EX2 = EX1 compiling patched source.
   EX3 = EX2 compiling patched source. `cmp -s EX2 EX3` must be
   byte-identical (fixed point).
7. **Run full conformance:**
   - `regextest.x` 24/24
   - `test_regex_dfa.x` 20/20
   - `test_pool_string_init.x`
   - `test_branch_return.x`
   - All 57 coreutils rebuild
   - `smoke_ailang_utils.sh` 40/40
8. **Measure.** Re-run the RSS table above under the new compiler.
   Expect the claimed reductions or explain the delta.

---

## Risk notes

- **Biggest risk is access-pattern migration.** Any code doing
  `XArray.XGet(node, ASTField.XXX)` needs to move to the new
  offset-based access. Miss one and you get a crash (or worse,
  silent corruption if XArray.XGet happens to return a consistent
  but wrong value from uninitialized pool memory). A helper like
  `AST_GetField(node, field)` that's identical across both
  implementations would let us migrate in two phases.
- **Child-array resize.** If a node ever exceeds 8 children, the
  current `XArray` would resize automatically. A fixed 8-slot pool
  can't. Need the overflow-pool path, or a "child count" gate in
  `AST_AddChild` that moves the node's children list from the
  small pool to the large pool when it crosses 8.
- **Bootstrap byte-identity.** The regex pool rework produced
  byte-identical output at stages 2 and 3. If AST pool rework
  doesn't reach a fixed point, something is non-deterministic
  about slot assignment (e.g. if an iteration order changed).

---

## Out of scope for this rework

- Lexer tokens. The lexer uses one big `XArray.XCreate(256)` as a
  growable token list (`Lex.tokens` in `Library.CLexerCore.ailang:79`).
  That's already a single allocation that grows — not the
  N-small-allocs problem. No action needed.
- Keyword table. Same pattern — one `XArray.XCreate(Keywords.table_size)`,
  one allocation. Fine.
- Arena itself. The Arena allocator's slab rounding is WHY this
  problem exists, but changing Arena would affect everything that
  calls `Allocate`. Rework the callers first; leave the Arena
  alone.
- XArray. It's fine in bulk-data uses; the problem is using it
  as a per-object struct.

---

## Stat utility — insufficiencies to clean up later

While auditing today, `stat` smoke-tested clean (6 invocation
modes, no crashes) but GNU feature-parity is rough. Logged here so
it doesn't get lost.

- **Device encoding.** We show raw `dev_t` as a single integer
  (e.g. `2096`). GNU shows `major,minor` (e.g. `8,48`). Cosmetic
  but scripts parsing `stat` output will mis-handle our format.
- **Permission format.** We show `(0/-rw-r--r--)` with a literal
  `0/` prefix; GNU shows the octal permissions `(0644/-rw-r--r--)`.
  Easy fix in the format string — compute octal from the mode bits.
- **User/group name lookup.** We emit `Uid: (1000)` numerically;
  GNU shows `Uid: ( 1000/    sean)`. Requires `/etc/passwd` and
  `/etc/group` lookup — not trivial but a one-time implementation.
- **Missing Access/Modify/Change/Birth timestamps.** GNU prints
  four timestamp lines. We emit none. This is a basic syscall
  wrap + strftime-equivalent.
- **No `--format` / `-c` flag.** Custom format strings are a common
  scripting need (`stat -c '%s'` for size, etc). Not implemented.

None of these are crashes or wrong answers — just feature gaps vs
GNU. Prioritize device encoding + permission format since those are
cheapest and most likely to break output-parsing scripts.

---

## Success criteria

A follow-up commit should include:

- `Library.CASTCore.ailang` with `ASTNodePool` + `ASTChildPool` +
  optional `ASTChildOverflowPool`.
- All call sites migrated to pool-slot offsets.
- `test_ast_pool.ailang` exercising:
  - Node with 0 children
  - Node with 1-8 children (fits in small pool)
  - Node with >8 children (promotes to overflow pool)
  - Deep tree (depth 100+)
- 3-stage bootstrap byte-identical.
- Full conformance suite green.
- RSS table updated in this doc (add "post-rework" column) showing
  the measured reduction.

Before-after wall-time measurement in the commit message.
