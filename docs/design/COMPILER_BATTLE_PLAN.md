# AILANG Compiler — Battle Plan

Drafted 2026-04-18 after the grep perf pass. Four compiler issues
surfaced during the session; they're listed here with concrete repro,
diagnosis, and fix plan so the next session can pick up without
re-deriving anything.

**Suggested order:**
1. Problem 3 — FixedPool string-literal `Initialize="…"`    (½-1 day)
2. Problem 2 — `Branch`/`Case` codegen                      (2-3 days)
3. Problem 1 — SIMD substring-compare intrinsic             (1-2 days)
4. Problem 4 — Nested-call-arg codegen / explicit hoist     (discussion first)

Problems 1-3 are scoped and independent. Problem 4 is more of a
language-design conversation than a coding task.

Core files to know:
- `ailang6.x` — canonical self-hosted compiler (AiLangSH root)
- `ailang_analyzer.x` / `analyzer.x` — static analyzer
- Parser statements: `Librarys/Compiler/Frontend/Parser/Library.CParserStatements.ailang`
- Statement codegen: `Librarys/Compiler/Compile/Modules/Library.CCompileStmt.ailang`
- Pool codegen:      `Librarys/Compiler/Compile/Modules/Library.CCompilePool.ailang`
- FPU/SIMD memops:   `Librarys/Compiler/Compile/FPU/X86/Library.FPUCompileX86MemOps.ailang`
- Existing memops list: `MemorySet`, `MemoryCopy`, `MemCompare`, `MemChr`
  (dispatch at `FPUCompileX86MemOps.ailang:32-49`)

---

## Problem 3 — FixedPool string-literal initializer silently miscompiles

### Symptom

```
FixedPool.Spaces {
    "pad7": Initialize="       "
}
```

compiles without error or analyzer warning. At runtime `Spaces.pad7`
reads as **0** (NULL). Any `WriteBuffered(Spaces.pad7, n)` or
`GetByte(Spaces.pad7, i)` segfaults on first dereference.

### Evidence

`wc_util/wc.ailang`'s `PrintFormattedNumber` used the pattern above
for right-padding its output. `wc_exec` segfaulted on every
invocation (file, stdin, `-l`, etc.). Instrumenting with
`PrintNumber(Spaces.pad7)` emitted `0`. Fixed in `wc` by inlining the
padding (`WhileLoop ... WriteByteBuffered(32)`), commit `06e4c053`.
Documented in `COMPILER.md` §6.

### Diagnosis

The parser accepts `Initialize="<str>"` and attaches the string literal
to the pool-member node (the `[POOL]` trace during compile of a test
case shows `init_str=<the literal>`). But the pool-init codegen path in
`CCompilePool.ailang` writes `0` for non-integer initializers — string
storage isn't emitted and the field isn't populated.

Integer `Initialize=N` works today because numeric literals flow cleanly
through the pool-member emit path: allocate the field, store `N` as its
initial value. String literals need a two-step lowering that the current
codegen doesn't do.

### Plan

1. **Emit** the string as a read-only data blob (in `.rodata` if the
   compiler has section tables; otherwise alongside other static
   strings the compiler already emits for `PrintMessage("foo")` etc.).
   The existing `PrintMessage` / `SystemCall(1, 1, "text", len)` path
   already emits static strings — reuse that machinery.
2. **At pool setup** (the same point where integer `Initialize=N`
   values get stored into the pool's field slot), store the **address**
   of the emitted string blob instead of `0`.
3. **Length question:** FixedPool fields are 8-byte int/address slots
   today. A string `Initialize` naturally lands in that slot as a
   pointer. That matches how `Scratch.rx = Allocate(N)` stores an
   address in the same kind of slot — no new infrastructure.
4. **Analyzer bonus:** add a `[MEM]` warning "`FixedPool.X.Y` has
   string `Initialize` — compiler support is limited; field will be
   NULL at runtime." This should be removed once the codegen lands,
   but it bridges the gap and catches the exact trap `wc` fell into.

### Where to look

- `Librarys/Compiler/Compile/Modules/Library.CCompilePool.ailang` —
  pool field initialization codegen. Search for the branch that handles
  `Initialize=<int>` and add the string-literal sibling.
- `Librarys/Compiler/Compile/Modules/Library.CCompileStringCore.ailang`
  (or the builtins path that handles string-literal arguments to
  `PrintMessage`) — existing static-string emit is reusable here.

### Test

```ailang
LibraryImport.Arena

FixedPool.Strings {
    "short":  Initialize="hi"
    "medium": Initialize="hello world"
    "empty":  Initialize=""
}

SubRoutine.Main {
    SystemCall(1, 1, "short=",  6) SystemCall(1, 1, Strings.short,  StringLength(Strings.short))
    SystemCall(1, 1, "\nmed=",  5) SystemCall(1, 1, Strings.medium, StringLength(Strings.medium))
    SystemCall(1, 1, "\n", 1)
    SystemCall(60, 0)
}
RunTask(Main)
```

Expected: `short=hi\nmed=hello world`. Currently: segfault on first
`StringLength` or garbled output.

### Risk

Low. Additive change — existing integer-Initialize and
`Initialize=0`-then-`.buf = Allocate(...)` patterns keep working.
Only affects users who write `Initialize="…"`, which is currently
broken anyway.

### Effort

½-1 day: reuse existing static-string emit + add one case in pool
init, plus the analyzer warning and a handful of tests.

---

## Problem 2 — `Branch`/`Case` codegen

### Symptom

Two distinct bugs under the same feature:

**Bug A — silent `ReturnValue` swallow inside `Case`:**
```ailang
Function.F {
    Output: Integer
    Body: {
        Branch x {
            Case 1: { ReturnValue(100) }
            Case 2: { ReturnValue(200) }
        }
        ReturnValue(0)   // falls here on any match instead of returning 100/200
    }
}
```
`ReturnValue` inside a `Case` exits the case, not the function.

**Bug B — performance regression:**
Replacing the `IfCondition EqualTo(type, N)` chain in regex
`ProcessState` with an equivalent `Branch type { Case 0: … Case 1: … }`
made prefix-pattern grep 3.5× **slower** (1.24 s → 4.44 s on 536 MB
corpus) and silently broke the `regextest.x` suite (dropped from 24/24
to 0/24 passing — test harness printed nothing because the
MATCH-state `Case` never returned).

### Evidence

- Live experience documented in `GREP_PERF_NOTES.md` (§ "Branch-based
  dispatch in `ProcessState`") and `COMPILER.md` §6.
- Both the reverted commit and the replacement test are in the session
  history under the partial DFA work.
- `regextest.x`: full regression to 0 passes when `Branch` was live;
  24/24 returned immediately after reverting to `IfCondition` chain.

### Diagnosis

**Bug A** — the codegen for `Case` blocks likely treats them as a
lexical scope whose exit target is the end-of-`Branch` label, not the
function's epilogue. `ReturnValue` inside the case emits a jump to
that end-of-`Branch` label instead of a function return. The fix is to
route `ReturnValue` through the enclosing-function's epilogue regardless
of intermediate scope (same rule as `ReturnValue` inside `WhileLoop`,
`IfCondition`, `Fork`, which all work correctly today).

**Bug B** — haven't disassembled yet, but the likely suspects:
- Per-case full function-style framing (prologue/epilogue for each
  case body) instead of plain local jumps
- Missing jump-table optimization — for dense integer cases
  (`Case 0 … Case 8`), it should emit `jmp *table(,value,8)`. For
  sparse integer cases, fall through to if-else chain is acceptable.
- If `Branch` always emits the chain AND adds per-case framing,
  it's strictly worse than the manual `IfCondition` chain on every
  axis, which matches what we measured.

### Where to look

- Parser: `Librarys/Compiler/Frontend/Parser/Library.CParserStatements.ailang:372-429`
  (`Parse_Branch`). Syntax itself parses correctly; this is not a
  parser bug.
- Codegen: `Librarys/Compiler/Compile/Modules/Library.CCompileStmt.ailang:429`
  — the comment reading
  `// Branch expr { Case val: { ... } Case val: { ... } Default: { ... } }`
  is at the top of the `Branch` lowering. That's the right entry point.
- Confirm via disassembly: compile a minimal `Branch` test, run
  `objdump -d` or the compiler's `-D4` flag, compare to the
  equivalent `IfCondition` chain.

### Plan

1. **Fix Bug A first** (the silent-return swallow). One-line fix in the
   statement lowering: when the body of a `Case` lowers a
   `ReturnValue`, it must emit the function-return sequence (= jump to
   epilogue label), not the `Branch`-end label.
2. **Land a `test_branch_semantics.ailang`** covering:
   - `Case` + `ReturnValue` — must exit the function.
   - `Case` + `BreakLoop` inside a loop inside a Case — must exit the
     loop, not the Case.
   - `Case` + `ContinueLoop` inside a loop inside a Case — continue
     the loop.
   - Nested `Branch` with `ReturnValue` in inner case — exits to
     function.
   - `Branch` without `Default`, value doesn't match any `Case` — no-op
     (fall through).
   - `Branch` with `Default` — fallback runs.
3. **Then tackle Bug B**: compare generated code for a 5-case `Branch`
   vs equivalent `IfCondition` chain. Adjust to match the chain's
   code size at minimum. Add dense-case jump-table emit if the
   compiler architecture allows it cheaply.
4. **Re-run the `ProcessState` conversion** after fixes land. Expected
   outcome: no regression vs `IfCondition` chain, and ideally a small
   win on sparse dispatch.

### Risk

Medium. Touches codegen, needs careful IR-level testing. Bug A fix
should be small and safe. Bug B optimizations could be deferred if
complex — the important thing for callers is "Branch isn't a speed
regression trap."

### Effort

2-3 days including tests and cross-checks. Bug A fix alone is ~half a
day. Bug B diagnosis is another day; optimization on top of that.

---

## Problem 1 — SIMD substring-compare intrinsic

### Symptom

Boyer-Moore loop in AILANG runs at ~2 ns/byte; GNU grep runs at
~0.5 ns/byte. **4-5× gap** on every literal/prefix-anchored
workload — the bulk of everyday grep usage.

### Evidence

Bench from `GREP_PERF_NOTES.md`, 536 MB corpus:

| Pattern | AILANG | GNU | Ratio |
|---|---|---|---|
| `-F Function` (fixed-string) | 1.02 s | 0.27 s | 3.8× |
| `Function` regex literal | 1.13 s | 0.27 s | 4.2× |
| `LibraryImport` | 0.90 s | 0.18 s | 5.0× |
| `FragAlloc\(\)` | 0.93 s | 0.17 s | 5.4× |

The gap scales linearly with input size (per-byte cost). Tried a
MemChr-anchored substring search variant — faster for rare-last-byte
patterns, 10-40% **worse** for common-last-byte patterns (which
dominate real text). Reverted.

### Diagnosis

GNU's win is SSE 4.2 `pcmpestri` / `pcmpestrm` with the
`_SIDD_CMP_EQUAL_ORDERED` immediate: compares 16-byte text chunks
against a pattern up to 16 bytes in a single instruction, returns the
offset of the first match. Closes most of the literal-path gap in a
single instrinsic.

We already have `MemChr` and `MemCompare` emitted with SSE2 — the
codegen path and cpuid detection plumbing are in place. Adding one
more SIMD primitive is additive.

### Plan

1. **Intrinsic name & signature:**
   ```
   MemFindSubstring(haystack: Address, haylen: Integer,
                    needle: Address,   needlen: Integer)
       → Integer       // offset of first match, or -1 if none
   ```
   Same signature shape as `MemChr` but for multi-byte needle.

2. **Codegen plan:**
   - Add dispatch in `FPUCompileX86MemOps.ailang:32-49` alongside
     `MemorySet`/`MemoryCopy`/`MemCompare`/`MemChr`.
   - Emit `pcmpestri` loop for needle lengths ≤ 16:
     ```
     ; rdi = haystack, rsi = needle, rcx = hay_remaining,
     ; rdx = needle_len, rax = pattern-relative offset
     pcmpestri xmm0, [rdi], _SIDD_CMP_EQUAL_ORDERED
     ```
     `ECX` receives the match offset in [0, 16) on match, 16 on
     no-match-this-chunk. Advance haystack by 16, repeat. On match,
     return `total_advance + ECX`.
   - For needle length > 16: fall back to a MemChr-anchored-on-first-byte
     loop with a MemCompare verify (same as today's
     `SearchBoyerMoore(plen=1)` shortcut but for the first byte
     instead of last).
   - For SSE 4.2-absent CPUs: scalar loop (memchr + memcmp). Feature
     detect via CPUID at program startup; store flag in a global.
     We already do similar for any SSE2 fallback, so the skeleton
     exists.

3. **Caller changes:**
   - `AiLang_CoreUtils/dist/grep_util/grep.ailang`: replace
     `SearchBoyerMoore`'s body with a one-liner call to
     `MemFindSubstring` for needle length ≤ 16. Keep BM fallback for
     longer needles (rare).

4. **Test:**
   - Bit-level unit test: needle in every position, needle absent,
     needle at end, needle length 1/2/4/8/16/17/32.
   - Perf: bench vs GNU on `-F Function` / `-F LibraryImport` / etc.
     Target: within 1.5× of GNU or better.

### Where to look

- `Librarys/Compiler/Compile/FPU/X86/Library.FPUCompileX86MemOps.ailang`
  — add a `Function.FPUCompileX86_MemFindSubstring` modeled on
  `FPUCompileX86_MemChr`.
- CPU feature detection: search the compiler tree for `cpuid` / SSE2
  flag bits; reuse that path.

### Risk

Low-to-medium. SSE 4.2 is on every x86-64 CPU from ~2008+, and
`pcmpestri` has no alignment requirements for the common mode we'd
use. The risk is in edge cases (crossing page boundaries near
unmapped pages at end-of-input). Canonical defense: stop the SIMD
loop `haylen - 16` bytes before the end and scalar-scan the tail.

### Effort

1-2 days. Intrinsic codegen (half day) + CPU feature detection (a
few hours if not already there) + caller integration (half day) +
correctness + perf tests (half day).

### Expected payoff

Closes the 4-5× literal-path gap to GNU. Prefix regex gap (currently
1.4×) shrinks to ~1.1× (prefix BM path is dominated by the same
scalar compare). Net: AILANG grep becomes a credible general
replacement, not just a "wins on weird regex" niche tool.

---

## Problem 4 — Nested-call-arg codegen / explicit hoist syntax

### Symptom

```
Deallocate(ptr, Multiply(Pool.CONST, 8))
```

— a function call whose **argument** is itself a non-trivial computed
expression — can trip the compiler's register allocation. Observed
firsthand fixing `wc`: the above needed to be rewritten as

```
size = Multiply(Pool.CONST, 8)
Deallocate(ptr, size)
```

to compile reliably.

### Why this is its own category

Unlike problems 1-3, this one isn't a simple bug fix. It's an
architectural tension:

**Option A: auto-lift in a lowering pass.** Compiler silently rewrites
`f(a, g(b, c))` → `t = g(b, c); f(a, t)`. Common in optimizing
compilers. Clean user ergonomics. **Rejected by user** on DO-178C
grounds: source-to-object traceability needs to be 1:1, and a
silent source→IR transform breaks that.

**Option B: `CB:` / `CodeBlock` prefix.** User annotates long
statements that need special handling. Explicit, but noisy and
forgettable. Pushes the compiler's limitations onto every caller.

**Option C: keep manual hoisting as discipline.** Don't change the
compiler. Add a lint in the analyzer that flags nested-call-args,
nudging users to hoist. Safe but puts the burden entirely on
reviewers.

**Option D: fix register allocation.** Tackle root cause — make
the codegen spill/reload correctly around nested calls. This is the
"proper" fix but risks a large churn in a load-bearing module.
The existing hoist module is already reportedly making code worse,
so it needs refinement anyway.

### Evidence

- User's report while fixing `wc`: "deeply nested calls create a
  fucking nightmare with code hoisting versus flattening."
- Existing hoist module "made the code run worse, likely needed more
  refinement."
- `wc.ailang:597` pre-fix was the exact case that motivated adding the
  local temporary; the new form (hoisted `Multiply` into `fp_size`) works.

### What to decide first

Before writing code, answer these:

1. **Does the existing hoist module already attempt this transform?**
   (Grep compiler source for "hoist" — confirm current behavior and
   why it regresses code.)
2. **Where exactly does codegen fall over?** A minimal repro:
   - `F(Multiply(A, B))` — does the multiply result land in the
     argument register for `F`, or does an intermediate register
     spill clobber something?
   - Inspect with `-D4` and compare to the hoisted form's assembly.
3. **Is this actually a correctness bug or a quality-of-generated-code
   bug?** (Unclear from current info — the wc fix worked with the
   nested form once `MAX_FILES` was the only nested call. Maybe the
   trigger is deeper nesting, not any nesting.)
4. **If we pick Option D (fix register allocation), what's the
   minimum-impact intervention?** E.g. spilling the left argument to
   the stack before evaluating the right. Inelegant but correct.

### Tentative plan (pending the above investigation)

- **Phase 1: document.** Reproduce the bug reliably, file a minimum
  test case. Don't ship a fix yet.
- **Phase 2: audit existing hoist module.** Read it, understand why
  it regresses, decide if refinement is cheap or if removal is saner.
- **Phase 3: pick Option C or D based on what Phase 2 finds.** If the
  hoist module's existing logic is salvageable, refine it (Option D
  disguised as a better Option A, without breaking traceability — the
  trick is making the transform visible in debug output). If not, add
  the analyzer lint (Option C) and keep manual hoisting.
- **Phase 4 (stretch): `CodeBlock` syntax.** Only if C/D prove
  insufficient. `CodeBlock { a = g(b, c); f(x, a) }` as a first-class
  construct that's a semicolon-less alternative to manual hoisting.
  Resist if possible — more syntax for the same effect as C.

### Effort

Phase 1-2: 1 day of investigation (no code changes). Phase 3:
depends on what Phase 2 finds — anywhere from a half day (lint) to
a week (rewrite hoist module). Phase 4: avoid unless forced.

---

## What the next session should do first

1. **Start with Problem 3** (FixedPool string init). It's the smallest
   blast radius, unblocks idiomatic stringpool use across the stdlib,
   and the fix reuses machinery that already exists. Half to one day.
2. **Write `test_compiler_regressions.ailang`** as we go. Each of
   these four problems should have a minimal repro committed, so we
   never lose a bug fix to a later regression without noticing.
3. **Don't ship Problem 2's perf optimization without the Bug A
   semantics fix.** The semantic bug is a silent correctness trap;
   speed is secondary to not-miscompiling.
4. **Park Problem 4 until Problems 1-3 ship.** Having a cleaner
   compiler to reason about will make the architectural decision
   easier.

---

## Session artifacts to reference

- `COMPILER.md` §6 — all rough edges found 2026-04-18, with minimal
  repros.
- `GREP_PERF_NOTES.md` — "What does and doesn't make a fast grep,"
  ranked by measured impact. Frames expected payoff for Problem 1.
- `test_regex_prefix.ailang`, `test_regex_dfa.ailang` — regression
  suites for the regex library, still useful after compiler work.
- Git log range `adf1fb5c..HEAD` — the commits that caused or
  mitigated each of the four issues described here.
