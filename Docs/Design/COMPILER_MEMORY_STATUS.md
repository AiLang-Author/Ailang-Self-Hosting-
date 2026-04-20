# Compiler Memory Rework — Session Status

Companion to `COMPILER_MEMORY_REWORK.md` (the plan). This file
tracks what shipped, what's next, and the measured deltas so the
next session picks up without re-deriving context.

Branch: `ast-pool-rework`
Last good commit: `7b12dc52` (lexer operator intern).

---

## Shipped

### AST node pool — commit `cc95e47e`

`Library.CASTCore.ailang` now allocates AST nodes from
`FixedPool.ASTNodePool` (256 K × 64 B slots, 16 MB reserved).
Field access is byte-offset `Dereference(Add(node, N))` instead of
`XArray.XGet/XSet`. Children still use a per-node `XArray.XCreate(8)`
stored at offset 56 — eager creation, no overflow path yet.

`AST_FreeAll` iterates the pool directly (no `all_nodes` list).

**Measured:**

| Workload | RSS before | RSS after | Wall before | Wall after |
|---|---|---|---|---|
| `regextest.ailang` | 104 MB | ~85 MB (-18%) | 0.26 s | 0.25 s |
| `grep.ailang` | 155 MB | ~110 MB (-29%) | 0.92 s | 0.35 s (2.6×) |
| `ailang_cli.ailang` | 1 769 MB | ~1 440 MB (-19%) | 5.28 s | 4.9 s |

The headline 20-40× win predicted in the plan didn't happen yet —
the children-XArray is still the dominant allocator. That's the
next block below.

### Parse_Branch comment skip — part of commit `cc95e47e`

`Parse_SkipNewlines` doesn't skip `P_COMMENT` tokens. Four sites in
`Parse_Branch` switched to `Parse_SkipWhitespace`. Pre-existing bug
surfaced by grep's inline `// EMPTY` / `// WHOLE_LINE` comments after
`}` in Case bodies. Not a memory issue; shipped in same commit
because it blocked rebuilds needed to measure the pool rework.

### Lexer operator interning — commit `7b12dc52`

`FixedPool.OpNames` holds the 9 two-char operator strings (`->`,
`==`, `!=`, `>=`, `<=`, `&&`, `||`, `<<`, `>>`) via `Initialize="..."`.
`FixedPool.SingleCharStrings` holds 256 × 2-byte single-char token
values, indexed by byte value.

`Lex_GetTwoCharOpValue` went from 10 `Allocate(24)+SetByte` sequences
to 9 one-line returns. `Lex_TokenizeSingleCharToken` returns
`Add(SingleCharStrings.buf, c*2)` instead of allocating.

Small RSS win (~3 MB) but the real value is that lexer no longer
heap-allocates for every operator/punctuation token. Also applies
automatically to `ailang_console` since the lexer is shared.

---

## Next — token record pool

`Library.CLexerCore.ailang:300` `Lex_AddToken` calls `ArrayCreate(5)`
per token. For an `ailang_cli.ailang` compile that's 200 K+ XArrays,
each with a 24 B header + 40 B backing = ~64 B rounded to 128 B slab.
**This is probably the single biggest remaining memory hotspot.**

Fields (`TokField` enum, `Library.CLexerCore.ailang:19-26`):

- `TYPE: 0`
- `VALUE: 1`
- `LINE: 2`
- `COL: 3`
- `LENGTH: 4`
- Slot size: 5 ints → 40 bytes

### Design

```
FixedPool.TokenPool {
    "buf":  Initialize=0, CanChange=True,
    "head": Initialize=0, CanChange=True,
    "cap":  Initialize=524288     // 512 K tokens × 40 B = 20 MB
}
```

`Lex_TokenPoolInit` (called from `Lex_Init`):
`TokenPool.buf = Allocate(TokenPool.cap * 40)`

`Lex_AddToken` rewrite:

```ailang
tok = Add(TokenPool.buf, Multiply(TokenPool.head, 40))
TokenPool.head = Add(TokenPool.head, 1)
StoreValue(Add(tok,  0), tok_type)
StoreValue(Add(tok,  8), tok_value)
StoreValue(Add(tok, 16), tok_line)
StoreValue(Add(tok, 24), tok_col)
StoreValue(Add(tok, 32), tok_len)
XArray.XPush(Lex.tokens, tok)
```

`Lex_GetType/Val/Line/Col` rewrite to byte-offset derefs:

```ailang
Function.Lex_GetType { Input: tok: Address; Output: Integer
    Body: { ReturnValue(Dereference(Add(tok, 0))) }
}
// etc. for 8, 16, 24
```

`Lex.tokens` stays an XArray of pointers-into-pool — 200 K × 8 B =
1.6 MB, fine.

### Call-site audit

Grep for `ArrayGet(tok` and `ArrayGet(` where arg0 is a token:

```
Grep pattern: ArrayGet\([a-z_]*tok[a-z_]*,
```

Any hit outside `Lex_Get*` needs migration. Most consumers already go
through `Lex_Get*` accessors, so blast radius is small. Double-check
`CParserCore.ailang`, `CParserExpressions.ailang`,
`CParserStatements.ailang`.

### Validation

1. 3-stage bootstrap byte-identical:
   ```
   ./ailangEX3.x ailang_cli.ailang ailangEX1.x
   ./ailangEX1.x ailang_cli.ailang ailangEX2.x
   ./ailangEX2.x ailang_cli.ailang ailangEX3.x
   cmp -s ailangEX2.x ailangEX3.x
   ```
2. `regextest` 24/24, `test_regex_dfa` 20/20.
3. `AiLang_CoreUtils/build_all_utils.sh` — all 57 green.
4. `smoke_ailang_utils.sh` — 40/40.
5. Measure `/usr/bin/time -v` RSS on `regextest.ailang`, `grep.ailang`,
   `ailang_cli.ailang`. Target: `ailang_cli.ailang` under 500 MB.

### Risk

- `Lex.tokens` contained owning XArrays; now it holds pointers into
  TokenPool. If anything mutates the XArray-style structure after the
  fact (e.g. `ArraySet` on the slot), it still works — same offset math.
- Lexer reset: `Lex_Reset` (if it exists) must reset `TokenPool.head = 0`
  too, same invariant as pool resets for regex.
- Out-of-pool: bump past `cap` needs a clear abort + instrumented
  message. The regex lib's pattern (`Halt` with a marker string) is
  the precedent.

---

## Follow-ups after token pool

In rough order of expected impact:

1. **AST children list** — still a per-node `XArray.XCreate(8)`. Swap
   to a `ChildSlotPool` with 8-entry slots + overflow pool for
   giant arg lists. This is what the original plan called the
   "20-40×" win — it's still on the table, just not shipped.
2. **Semantic symbol table entries** — each symbol is an XArray too.
   Same pattern.
3. **Intermediate parser XArrays** — parser allocates temporary lists
   during parse (e.g. function param lists). Audit for churn.
4. **Port `ailang_console` dump feature to `ailang_cli`** — user
   asked for this. The dump creates `combined_source.ailang` for
   debugging. Lives in whatever drives `[IMPORT] Starting
   conflict-only resolution...` flow; grep for that string.

---

## Untracked / scratch in working tree

Files that accumulated this session, flagged for the user to decide:

| File | Size | Likely disposition |
|---|---|---|
| `a.out` | 45 KB | Throwaway test binary — can delete |
| `grep.ailang` | 53 KB | Root-level copy; real one is `AiLang_CoreUtils/dist/grep_util/grep.ailang` — compare before deleting |
| `oldgrep.ailang` | 61 KB | Backup of pre-optimization grep — keep until grep perf work is stable |
| `nohup.out` | 1 KB | Background-job stdout — can delete |
| `test_debugperf.ailang` | 371 B | Ad-hoc perf probe |
| `test_dfa_stats.ailang` | 2 KB | DFA statistics scaffold |
| `test_ko_build.ailang` | 2 KB | Kernel-module build test |
| `test_module.ko` | 800 B | Built .ko output |
| `test_num2str.ailang` | 897 B | Num-to-string scratch |
| `test_pool_ast_branch.ailang` | 366 B | Minimal Branch repro for AST pool bug (now fixed) — safe to delete, bug has regression test elsewhere |
| `combined_source.ailang` | 159 KB | Dump from `ailang_console` — scratch |
| `--version` | ? | Accidental file from a bad CLI invocation — delete |
| `AILANG_STDLIB_INDEX.md` | 11 KB | Untracked doc — likely worth committing if it's real |
| `Librarys/Compiler/Output/Library.CELFKernelModule.ailang` | ? | Untracked library — check if real work |

**`Library.CCompileFunc.ailang` modified in working tree** — adds
`Scope_SaveAndClear` / `Scope_Restore` around SubRoutine compile.
Not from this session's memory work. Leave alone; ask user if it's
WIP from a parallel experiment.

---

## How to pick up next session

```
# 1. Verify current state
git log --oneline -5
git status

# 2. Reproduce the "before" number
/usr/bin/time -v ./ailang6.x ailang_cli.ailang /tmp/out.x 2>&1 | grep "Maximum resident"

# 3. Open Library.CLexerCore.ailang at line 300
# 4. Add FixedPool.TokenPool block near existing FixedPool.* definitions
# 5. Add Lex_TokenPoolInit, wire into Lex_Init
# 6. Rewrite Lex_AddToken + Lex_Get* accessors
# 7. Build EX1, bootstrap to EX2/EX3, verify fixed point
# 8. Run conformance suite
# 9. Measure RSS delta, commit with numbers in message
```
