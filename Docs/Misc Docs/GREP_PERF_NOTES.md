# What Makes a Fast Grep — Measured, Not Speculated

Running tally of optimizations we applied to AILANG's `grep_util` during
the April 2026 perf pass, ranked by **observed** impact on real
benchmarks. This is a field note, not a theory. Every number in it was
measured on this box against GNU grep 3.11.

Two corpora used throughout:
- **Small** — 5.5 MB source tree (223 `.ailang` files under `Librarys/`)
- **Big**   — 536 MB concatenation of the same tree ×100

---

## The S-tier wins

### 1. Pool-based parser node allocator for the regex NFA

**Impact:** RSS 12 GB → 256 KB on big corpus. ~50 000× reduction. Unlocked
everything else that followed — without this, perf tuning was pointless
because the process would OOM first.

**Why it matters:** the AILANG Arena rounds every small `Allocate` to a
4 KB slab, 16-byte aligned. A 16-byte AST fragment node burns a full
4 KB. The regex parser produces hundreds of fragments per compile.
`Deallocate` is effectively cosmetic; the slab can't return until
arena teardown.

**Fix:** three `FixedPool` ring-buffer slot allocators
(`RegexFragPool`, `RegexListPool`, `RegexClassPool`) — one up-front
`Allocate(cap × slot_size)` per pool, slot handed out as
`buf + head × size`, `Deallocate` becomes a no-op. Pools are
process-lifetime bump allocators; **do not reset `head` between
compiles** — parser state nodes hold raw bitmap pointers into the
class pool, and resetting would corrupt previously-compiled handles.

### 2. Regex literal-prefix extraction + Boyer-Moore pre-filter

**Impact:** 60 s → 1.24 s on `Function\.([A-Z][a-z]+)+` over 536 MB
(**~48× speedup**). The single biggest wall-clock win of the session.

**Why it matters:** most lines don't match the pattern. Running the
full Thompson NFA at every byte of every non-matching line is pure
waste. Most non-trivial regexes have a literal anchor; extracting it
lets us use a fast substring search to skip 99.95% of bytes, invoking
the regex engine only at candidate positions.

**Fix:** `Regex_GetPrefix` walks the NFA start chain for a
`CHAR → CHAR → …` run (transparently skipping one leading
`ASSERT_START`). Grep builds a Boyer-Moore bad-char table on the
prefix per pattern at compile time. The hot path BMs on the raw line;
only on a BM hit do we materialize the `Scratch.rx` NUL-terminated
buffer and call `Regex_Match` to verify.

### 3. Lazy DFA with bounded state cache

**Impact:** 60 s → 2.62 s on `(F[a-z]+|[A-Z][a-z]+)\.([A-Z][a-z]+)+`
(no-prefix alternation) over 536 MB (**~23× speedup**). At that point
we're faster than GNU (8.38 s) by 3.2×.

**Why it matters:** patterns with no literal prefix (alternation, `*`,
`?`, class-led) can't be skipped with BM. The Thompson NFA pays
per-byte per-active-thread dispatch cost. A DFA memoizes
(state-set, byte) → next-state-set, turning a worst-case
O(bytes × active-states × dispatch-ops) loop into O(bytes × 1 table
lookup).

**Fix:** lazy DFA with a 1024-state cache. State-set represented as a
512-byte bitset. Transitions cached in a 256-entry table per DFA
state. Start state includes epsilon-closure of `{start_state}`;
unanchored semantics by OR-ing that closure into every computed
transition before interning. Bail and fall back to NFA if the regex
contains `^` / `$` assertions, or if we overflow the state cap
(never observed in practice — 8 states were enough for our stress
patterns).

### 4. Zero-copy hot path — skip the per-line MemoryCopy

**Impact:** 59 s → 3.7 s on no-prefix monster pattern with DFA
already in place (**~16× on top of DFA**). This was larger than the
DFA win itself.

**Why it matters:** every `Regex_Match` call needs its text buffer
NUL-terminated at `line_len` (it calls `StringLength`). So the
previous code did a per-line `MemoryCopy(Scratch.rx, line, line_len)`
before every regex invocation. For 6.7 M lines × ~80 bytes, that's
~540 MB of needless copies — ~10× the actual work.

**Fix:** `Regex_DFASearch` and `Regex_Search` take an explicit
`text_len`, so they don't need a NUL terminator and can read `line_buf`
directly. Moved the DFA / NFA calls to operate on raw line, and only
keep the copy for the BM-prefix path's `Regex_Match` verify (rare:
only on BM hits).

### 5. Inlining hot-loop function calls

**Impact:** cut per-byte cost in `Regex_DFASearch` roughly in half
(3.34 s → ~2.6 s on complex no-prefix on 536 MB).

**Why it matters:** AILANG's function-call prologue/epilogue is
non-trivial — spill, save registers, stack alignment. At 540 M
per-byte iterations, that's ~20 s of pure dispatch overhead if each
`DFA_GetTrans(cur)` is a real call.

**Fix:** inline the trans lookup — hoist `DFA.trans_buf` and
`DFA.match_buf` addresses into locals once per call, then index
directly with `Add(base, (cur * 2048) + (b * 8))`.

---

## The A-tier — solid wins, cheap to implement

### 6. Boyer-Moore for fixed-string patterns (`-F` mode)

**Impact:** 6.9 s → 1.0 s for `-F Function` over 536 MB. 7× for
literal-mode grep.

**Why it matters:** without skip-ahead, sliding-window string compare
touches every byte. BM's bad-character heuristic skips by up to
`pattern_len` bytes at a time — for a 9-byte pattern against random
text, average skip is ~7 bytes.

**Fix:** `BuildBadCharTable(pat, plen)` returns a 256-byte table
giving the shift distance for each possible text byte. `SearchBoyerMoore`
checks the last pattern byte first (fast rejection), then `MemCompare`
on the candidate. Single-byte patterns short-circuit to `MemChr`.

### 7. 1 MB read buffer (up from 64 KB)

**Impact:** small but real — fewer `read()` syscalls on big inputs.
For small files the kernel cache makes this invisible.

**Why it matters:** system call overhead is ~1 µs. At 64 KB/syscall,
reading 536 MB is ~8200 syscalls = ~8 ms overhead. At 1 MB/syscall,
~540 syscalls = 0.5 ms. Small absolute win, but free.

### 8. `MemChr` for newline scanning

**Impact:** moderate — replaces byte-by-byte `GetByte` loop with a
SIMD-accelerated primitive.

**Why it matters:** per-byte AILANG inner loops pay function-call
overhead and don't auto-vectorize. `MemChr` is a compiler builtin
with SSE2 codegen.

**Fix:** in `ProcessStream`, use `MemChr(buf+pos, '\n', remaining)` to
find the next line boundary, then `MemoryCopy` the line fragment into
`line_buf`. Same logic, but the inner loop runs on the FPU side of
the compiler.

### 9. `MemCompare` on the case-sensitive `CompareAt` fast path

**Impact:** small — same argument as MemChr, but applied to the
substring-compare branch of the literal matcher.

**Why it matters:** replaces a per-byte `GetByte(line,pos+i) ==
GetByte(pat,i)` loop with a vectorized memcmp. Per-byte overhead
gone. Case-insensitive path kept byte-wise because line isn't
pre-lowercased.

### 10. Single-pass unanchored `Regex_Search`

**Impact:** small (~6 %) in isolation, but unlocks the DFA integration.

**Why it matters:** the old code called `Regex_Match` once per byte
start position. Each `Regex_Match` ran `StringLength(text)` on entry —
O(text_len) setup × text_len calls = quadratic setup cost.
`Regex_Search` makes a single forward pass keeping the start state
alive at every position (textbook unanchored Thompson driver) and
takes `text_len` explicitly so no `StringLength`.

**Caveat:** on pre-2-byte-prefix patterns where threads die fast
anyway, the theoretical O(N²) was really O(N × const), so the
algorithmic savings are real but small. Main value is as the
fallback path when DFA bails out.

---

## The B-tier — nice to have, not load-bearing

### 11. Process-lifetime BM tables

One `Allocate(256)` per pattern at `CompileAllPatterns` time. No
per-line work. Marginal impact since pattern count is small; still
correct-by-construction.

### 12. Grep-side prefix-hit scratch materialization

Inside the BM-prefix-hit loop, we do the `MemoryCopy(Scratch.rx, line,
line_len)` exactly once per matched line (not per BM candidate).
Trivial win but cleaner code. Filed under "good hygiene."

---

## The "does nothing measurable" pile

### `OUT_BUF` bumped 64 KB → 1 MB

**Impact:** zero. Verified with strace: a 5 MB-input verbose `-n` run
produced **one** `write()` call even at 64 KB (the buffer doesn't fill
on that workload). On 536 MB verbose runs the kernel's `write()` cost
is negligible vs the match path. Rolled back.

### Branch-based dispatch in `ProcessState`

Replacing the `IfCondition` chain with `Branch type { Case N: {...} }`
in the per-byte NFA state dispatch was expected to save ~2 comparisons
per call. In practice:
- Prefix-path regex went from **1.24 s → 4.44 s** (3.5× regression)
- `regextest.x` silently broke — `ReturnValue(1)` inside a `Case`
  block didn't propagate out of the enclosing function.

The `Branch` syntax itself is valid (confirmed against the self-hosted
compiler parser at `Library.CParserStatements.ailang:372`). But:
- **Don't put `ReturnValue` inside a `Case`** until codegen is verified.
- The generated code is **slower than the equivalent `IfCondition` chain**
  for the cases we tested.

Reverted. Kept the IfCondition chain.

### Auto-lifting nested expressions

Proposed converting `f(a, g(b, c))` → `t = g(b, c); f(a, t)` in a
compiler lowering pass. Rejected for this codebase: DO-178C traceability
requires the source-to-object mapping to be 1:1. A silent
source→IR transform violates that. Manual hoisting is the discipline
instead — and the compiler's existing hoist module gave worse code
when enabled, so it needs refinement before being trusted.

### Auto-vectorizing the regex state dispatch via `Branch`

See above — the AILANG `Branch` codegen wasn't a win for this
pattern in this compiler. May be revisited after codegen work on
the `Branch` lowering path.

---

## Still on the table (not yet measured)

- **4-byte-unrolled `ToLowerInline`** — would help `-i` mode. The
  oldgrep variant unrolled to 4 chars at a time; we haven't ported.
- **Multi-line threading via a per-thread pool + ping-pong buffer**
  (user's sketch). Each worker thread gets its own `FragPool` /
  `ListPool` / `ClassPool` instance, or CAS-advance on a shared head
  (Threading library v0.1 already has `AtomicCompareSwap`). Would
  need CPU-core detection + thread-count tuning — non-trivial. User
  classified as "not worth it for grep" for now.
- **SIMD substring search** — our Boyer-Moore touches one byte at
  a time in the skip-loop; GNU's equivalent uses SSE 4.2 `pcmpestri`
  or AVX2. Closing this would probably shrink the 4-6× literal-path
  gap to 1.5-2×.
- **Context lines (-A/-B/-C)** — `oldgrep.ailang` had a ring-buffer
  implementation; not ported yet. Feature, not speed.

---

## Summary table

| Change | Wall time savings | Effort | Keep? |
|--------|--------------------|--------|-------|
| Pool parser-node allocator           | 12 GB RSS → 256 KB    | 1 day    | ✅ non-negotiable |
| Regex prefix + BM pre-filter          | 60 s → 1.24 s         | 1 day    | ✅ biggest wall win |
| Lazy DFA                              | 60 s → 2.62 s         | 1 day    | ✅ required to beat GNU on hard cases |
| Zero-copy DFA path                    | 59 s → 3.7 s          | 1 hour   | ✅ trivial once noticed |
| Inlined DFA transition lookup         | 3.34 s → 2.62 s       | 15 min   | ✅ free |
| Boyer-Moore for literals              | 6.9 s → 1.0 s         | 1 hour   | ✅ classic win |
| 1 MB read buffer                      | small, positive       | 1 line   | ✅ free |
| MemChr for newlines                   | small                 | 30 min   | ✅ free |
| MemCompare case-sensitive literal     | small                 | 10 min   | ✅ free |
| Single-pass `Regex_Search`            | ~6 %                  | 1 hour   | ✅ enables DFA fallback |
| 1 MB output buffer                    | **zero**              | 1 line   | ❌ reverted |
| `Branch` dispatch in ProcessState     | **negative (3.5× regression)** | 1 hour | ❌ reverted, compiler rough edge |
| Auto-lift nested expressions          | untested              | compiler pass | ❌ verifiability cost > payoff |

**Bottom line:** RSS went from 12 GB → 256 KB (mandatory, first), and wall
time on the hardest regex went from 60 s → 2.62 s (competitive, done last).
Total session effort ≈ two working sessions. Every win on the list cost
less than a day; the rejected items cost less than an afternoon to
discover and back out. Measure first, commit second.
