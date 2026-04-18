# AiLang — Compiler, Code Structure, and Triage Notes

Living document. New findings get appended to §5 as we work through the
CoreUtils fix-up.

---

## 1. The compiler

Canonical compiler: **`./ailang6.x`** (statically linked x86-64 ELF, at
the root of `AILangSH/`). Earlier `ailang1.x`..`ailang5.x` are kept
alongside for bisect / regression comparison — treat `ailang6.x` as the
source of truth unless you're specifically bisecting.

### Usage

```
./ailang6.x [-P] [-D1-4] <source_file> [output_file]
```

| Flag        | Meaning                                                       |
|-------------|---------------------------------------------------------------|
| `-P`        | Parse-only / front-end pass (no codegen).                     |
| `-D1`…`-D4` | Debug verbosity 1→4. Raise when the build fails silently.     |

Output is a fully static ELF — runs with no loader or libc dependency.

### Examples

```bash
# Plain program
./ailang6.x hello.ailang hello.x

# One CoreUtil into the layout build_all_utils.sh expects
./ailang6.x AiLang_CoreUtils/dist/head_util/head.ailang \
            AiLang_CoreUtils/dist/head_util/head_exec
```

---

## 2. Code structure

### Source / binary conventions

| Extension | Meaning                                                      |
|-----------|--------------------------------------------------------------|
| `.ailang` | Source.                                                      |
| `.x`      | Default naming for compiled AiLang ELF binaries.             |
| `_exec`   | Per-util binary inside `AiLang_CoreUtils/dist/<util>_util/`. |

### Imports (Python-like)

Libraries live in `AILangSH/Librarys/` as files named
`Library.<Name>.ailang`. A source file pulls one in with a top-level
declaration:

```
LibraryImport.Arena
LibraryImport.StringUtils
LibraryImport.JSON
```

### Runtime libraries worth knowing

| Library             | Provides                                                        |
|---------------------|-----------------------------------------------------------------|
| `Library.Arena`     | `Allocate` / `Deallocate` (slab allocator, 4 MB chunks per size class).  **Required for any util that calls `Allocate`.** |
| `Library.StringUtils` | String helpers.                                              |
| `Library.JSON`      | JSON parse/emit.                                                |
| `Library.XArrays`   | Dynamic arrays.                                                 |
| `Library.HashMap`   | Hash maps.                                                      |
| `Library.Socket`    | BSD sockets.                                                    |
| `Library.Analyzer`  | Static-analysis library used by the analyzer binary.            |

### Syscalls

AiLang calls **Linux syscalls directly** via `SystemCall(nr, …)` — no
libc. The syscall number table lives deep in the compiler sources under
`Librarys/Compiler/`. Common numbers used in CoreUtils:

| Nr   | Call    |
|------|---------|
| 0    | read    |
| 1    | write   |
| 2    | open    |
| 3    | close   |
| 60   | exit    |

Idiomatic source pattern wraps these in per-util helpers:

```
Function.SysWrite {
    Input: fd: Integer
    Input: buffer: Address
    Input: count: Integer
    Body: { SystemCall(1, fd, buffer, count) }
}
```

---

## 3. Static analyzer

Binary: **`./ailang_analyzer.x`** (same dir as the compiler).

```
./ailang_analyzer.x <filename.ailang> [function_filter]
```

Four passes:

| Pass   | Tag   | Catches                                                 |
|--------|-------|---------------------------------------------------------|
| Memory | [MEM] | leaks, unused vars, missing returns                      |
| CFG    | [CFG] | unreachable code, infinite loops, null deref            |
| Data   | [DFA] | uninit vars, double dealloc, call graph                 |
| Pool   | [PTF] | address safety, field validation, type conflicts        |

Summary is printed at the bottom (`N errors, M warnings, P hints`). Run
it before and after any fix; a warning that disappears is a good sign,
and a new one is a regression.

---

## 4. Building the CoreUtils

The orchestration script is `AiLang_CoreUtils/build_all_utils.sh`. It
is currently **stale** — still calls `python3 main.py`. Workaround loop
until it's rewritten:

```bash
# From AILangSH/
for u in echo cat ls wc grep head tail ...; do
  src="AiLang_CoreUtils/dist/${u}_util/${u}.ailang"
  out="AiLang_CoreUtils/dist/${u}_util/${u}_exec"
  [[ -f "$src" ]] && ./ailang6.x "$src" "$out"
done
```

Install/repair: `AiLang_CoreUtils/install_ailang_utils.sh` copies each
`_exec` to `~/.local/bin/ailang/<util>_ailang` and symlinks
`~/.local/bin/<util>` onto it. It's safe to re-run for individual
utilities — it rebuilds the symlink each time.

---

## 5. Triage log

### head  ✅ fixed

Symptom: in multi-file mode, `head f1 f2` printed all headers first and
all content second, with no separator newline between files — diff
against GNU head failed.

Root cause: `Main` emitted the `==> <file> <==` header via `WriteStderr`
(fd 2). GNU head writes those headers to stdout (fd 1) so they stay
ordered with the file bodies.

Fix in `AiLang_CoreUtils/dist/head_util/head.ailang`:

1. Added `LibraryImport.Arena` at the top (Allocate/Deallocate moved
   there; linking otherwise fails).
2. Added a `WriteStdoutStr` helper (twin of `WriteStderr`, fd 1).
3. Replaced the four header-emitting `WriteStderr` calls in `Main`
   with `WriteStdoutStr`.

Verification (`head_exec` vs `/usr/bin/head`):

| Case                            | Before | After |
|---------------------------------|--------|-------|
| Default (10 lines, 1 file)      | PASS   | PASS  |
| `-n N`                          | PASS   | PASS  |
| `-c N`                          | PASS   | PASS  |
| stdin                           | PASS   | PASS  |
| Multi-file headers              | **FAIL** | **PASS** |
| `-q` multi-file                 | PASS   | PASS  |
| Missing file + exit code        | PASS   | PASS  |

### tac  ✅ rewritten

Symptom: reversing a 20-line file emitted the reversed content *and*
then the file forward again (roughly 2x the expected output).

Root cause: after the reverse loop, the trailing-partial-line handler
ran unconditionally, with `line_start` still holding its last-iteration
value of `0`. That condition was always true for any non-empty input,
so it re-emitted `file_buffer[0..total_bytes]` — i.e. the whole file
forward.

Also fixed:
- Added `LibraryImport.Arena`.
- Added multi-file support and `-` as stdin.
- Correct handling of trailing partial line (no appended `\n` — GNU
  tac concatenates the trailing bytes onto the front of the next
  reversed record, so input `x\ny\nz` becomes output `zy\nx\n`).

7/7 GNU conformance (simple reverse, stdin, no trailing newline,
single line, two files, empty stdin, file then `-`).

### tr  ✅ rewritten

Symptom: `tr a-z A-Z` returned input unchanged.

Root causes:
1. Missing `LibraryImport.Arena`.
2. SET1/SET2 never expanded — `a-z` was treated as three literal
   characters `a`, `-`, `z`. GNU tr expands ranges (and `\n`, `\t`,
   `\\` etc. escapes) before table building.
3. `-s` (squeeze repeats) was unimplemented.
4. My initial rewrite used `;` as a statement separator and ` → ` in
   a comment; both tripped the parser (`PARSE ERROR: Unexpected token
   in statement`). Lesson: AiLang is newline-separated and
   ASCII-only — added both to `AILANG_STDLIB_INDEX.md`.

Result: 8/8 GNU conformance on translate / delete / squeeze /
ranges / escapes.

### cut  ✅ rewritten

Symptom (old binary): "cut: cannot open file" on any invocation; new
compile broke with `Unknown function: MemCopy`.

Root causes:

1. `MemCopy(...)` intrinsic was renamed to `MemoryCopy(...)` (compiler
   FPU SSE2 dispatcher — see
   `Librarys/Compiler/Compile/FPU/X86/Library.FPUCompileX86MemOps.ailang`).
   Same argument order: `(dest, src, count)`. Same applies to
   `MemSet` → `MemorySet`.
2. Missing `LibraryImport.Arena` (everywhere `Allocate` is used).
3. Arg parser only recognised `-f`; unknown flags fell through into the
   filename slot, so `-d,` was opened as a file.
4. `-f` accepted only a single integer, not the POSIX LIST grammar
   (`N | N-M | -M | N- | A,B`).
5. `-d`, `-c`, `-b`, `-s` were entirely missing.
6. In the rewrite, an initial double-emission bug appeared when a line
   had no delimiter: the field-loop still emitted field 1 (= whole line)
   AND the passthrough block emitted it again. Fix: scan the line first
   for the delim, take the passthrough OR the field-selection branch,
   never both.

Result: full GNU-equivalent cut. 13/13 GNU diff tests pass covering
`-d`, `-f LIST` with ranges/open/prefix, `-c`, `-s`, no-delim
passthrough, stdin fallback, and missing-file exit codes.

### logname  ✅ rewritten (POSIX semantics)

Symptom: `logname` printed `sean` on WSL, where GNU logname correctly
errors with "no login name".

Root cause: the old implementation used `id -un` semantics — `getuid()`
+ /etc/passwd lookup — which returns the effective user regardless of
login context. POSIX `logname` is defined in terms of `getlogin(3)`,
which returns the LOGIN name (empty when no controlling login session
exists).

Fix:

1. Read `/proc/self/loginuid` — the Linux audit subsystem's login UID.
2. If the file is missing, unreadable, or contains `-1` /
   `4294967295` (unset), write `logname: no login name\n` to stderr
   and exit 1.
3. Otherwise look up that UID in `/etc/passwd` and print the matching
   username to stdout.

On WSL (no pam_loginuid), this now matches GNU: `no login name` + exit 1.
On a real login session it prints the login user.

### Regex engine (`Library.Regex_Thompson`) — two bugs fixed

While wiring the regex library into grep, a standalone test
(`AILangSH/regextest.ailang`) surfaced two bugs. Both fixed:

1. **`CreateList` 4-byte OOB write.** The list node was allocated at
   16 bytes but the `is_out2` flag was stored at offset 12 with
   `StoreValue` — which writes 8 bytes, overrunning to byte 19. This
   corrupted Arena's next-slab header and segfaulted `Regex_Compile`
   on simple patterns like `a*`. Fix: expanded the list node to
   24 bytes, moved `is_out2` to offset 16. Also updated `SetListNext`
   and `PatchList` to match. Library file:
   `Librarys/Library.Regex_Thompson.ailang`.
2. **`ParseClass` never implemented ranges.** The inner class-parse
   loop just `SetBit`'d every character it saw, so `[0-9]` set bits
   for `0`, `-`, `9` — three chars, not ten. Fix: peek after every
   class member for `-<end>` and fill `[start..end]` inclusive. Same
   file.

Also added `LibraryImport.Arena` to the regex library itself so it's
self-contained (compiler dedups duplicate imports when callers also
import Arena).

Standalone regex conformance (`AILangSH/regextest.ailang`): **24/24
PASS** covering literals, `.`, `*`, `+`, `?`, `^`, `$`, `[abc]`,
`[a-c]`, `[0-9]`, `[^abc]`, `|` alternation.

### grep  ✅ rewritten (with regex)

Old grep was parked because performance work regressed correctness and
it depended on the defunct `Library.Grep_Extended`.

Rewrite now includes regex via `Library.Regex_Thompson` (defaults to
regex; `-F` opts into literal). Covers the flags that actually get
used in pipelines and scripts:

| Flag | Effect                                          |
|------|-------------------------------------------------|
| `-i` | case-insensitive                                |
| `-v` | invert                                          |
| `-n` | prefix with 1-based line number                 |
| `-c` | count-only per file                             |
| `-l` | list files with matches                         |
| `-L` | list files without matches (GNU ext)            |
| `-q` | silent; exit code only                          |
| `-s` | suppress file-error diagnostics                 |
| `-H` | always prefix filename                          |
| `-h` | never prefix filename                           |
| `-F` | fixed string (accepted; already default here)   |
| `-x` | whole-line match                                |
| `-w` | whole-word match                                |
| `-e` | explicit pattern (repeatable)                   |
| `-`  | read stdin                                      |
| `--` | end of options                                  |

Exit codes: 0 = any match, 1 = no match, 2 = file error.

Conformance (vs `/usr/bin/grep -F`): **12/12 PASS** — literal, no
match exit, -i, -v, -n, -c, -l, -q, stdin, -x, -w, multiple -e.

### Known gaps vs GNU grep

1. **No regex engine.** `Library.Regex_Thompson.ailang` exists and
   builds against `ailang6.x`, but a 13-case standalone smoke test
   segfaults on the 4th case (`he*l` vs `heeeeeel`). The first
   three (literal, literal no-match, `.` dot) pass. Filed for a
   later dedicated fix — parked for now. Pattern metachars (`.`,
   `*`, `^`, `$`, `[...]`, `|`, `+`, `?`, `\( \)`) are all
   untreated; they match literally.
2. No `-r` / `-R` recursive directory search.
3. No `-A` / `-B` / `-C` context lines.
4. No `--include` / `--exclude`.
5. No `--color`.

### Bulk compiler port (April 2026)

All 57 coreutils sources were ported to `ailang6.x` in one pass:

- Added `LibraryImport.Arena` to 49 files that used `Allocate` without
  it. 8 files already had the import.
- Renamed all `MemCopy(` → `MemoryCopy(` and `MemSet(` → `MemorySet(`
  (26 occurrences across 11 files).
- Replaced `ReturnVoid` (no longer a primitive) with `ReturnValue(0)`
  in dd, df, split.
- Split multi-line string literals in paste and wc into per-line
  emit calls (AiLang lexer rejects embedded newlines in `"..."`).
- Stubbed `FixedPool.ExtendedConfig` inline in grep.ailang because
  `Library.Grep_Extended.ailang` no longer exists in the tree.

Build result: **56/57 compile cleanly with `ailang6.x`.** The outlier
is grep, which also needs `CheckWordBoundary()` and other functions
that lived in the missing Grep_Extended library — parked pending a
proper rewrite.

### Compiler-wide rename alert

All CoreUtils that use `MemCopy` / `MemSet` will fail to compile against
`ailang6.x`. Ports must rewrite to `MemoryCopy` / `MemorySet`.
Affected files (by grep): basename, cut ✅, diff, dirname, grep, paste,
pwd, sort, split, uniq, wc.

### Open issues in head (not yet fixed)

Reported by `ailang_analyzer.x`:

- `[MEM]` `IsFlag` defined but never called — dead helper, safe to drop.
- `[CFG]` `HeadLines:98` possible null deref on `buffer` without null check.
- `[CFG]` `StrEquals:232` possible infinite loop (condition always true, no `BreakLoop`).
- `[CFG]` `StringToInt:253` same pattern as above.
- `[CFG]` `ParseFlags:298` and `:312` unreachable code after return/break.
- `[CFG]` `Main:396` / `:399` possible null deref on `arg`.

Also found by hand while reading:

- `--help` (lines 264-271) and `--version` (line 278) go to **stderr**;
  GNU coreutils send both to stdout.

### Compiler / toolchain issues to revisit

- `AiLang_CoreUtils/README.md` is written for the old Python compiler.
  Reads wrong against today's `ailang6.x`; needs rewrite.
- `AiLang_CoreUtils/build_all_utils.sh` still hard-codes `python3 main.py`.
  ~~Needs the loop above, or a rewrite.~~ **Rewritten 2026-04-18** to
  use `./ailang6.x` and `cd` to AILANG_ROOT so the compiler can resolve
  `Librarys/` relative to CWD (see new rough edge below).

---

## 6. Rough edges discovered 2026-04-18

### Compiler accepts but silently-miscompiles `FixedPool` string-literal initializer

```
FixedPool.Spaces {
    "pad7": Initialize="       "
}
```

Compiles clean (no warning). At runtime `Spaces.pad7` reads as **0**
(null), so any `WriteBuffered(Spaces.pad7, n)` / `GetByte(Spaces.pad7, i)`
dereferences NULL and segfaults. Found in `wc.ailang`'s
`PrintFormattedNumber` — fixed by inlining a `WhileLoop … WriteByteBuffered(32)`.

**Triggered:** any FixedPool field with `Initialize="…"`.
**Diagnosis:** `PrintNumber(Spaces.pad7)` emits `0` instead of a valid
address. The analyzer doesn't flag it.
**Workaround:** populate the field at startup via an `InitBuffers`-style
setup function, or inline the constant bytes at the call site.

### Compiler resolves `Librarys/` relative to CWD, not compiler binary

`./ailang6.x some/path/src.ailang out.x` loads `LibraryImport.X`
targets from `./Librarys/Library.X.ailang` — relative to where the
compiler was *invoked*, not where the compiler binary lives. Build
scripts therefore must `cd` to the AiLangSH root (where `Librarys/`
sits) before calling the compiler, even if they reference source
files under subdirectories.

**Symptom when violated:** `[ERROR] Arena_Alloc not found — Ensure
LibraryImport.Arena is included` even though the source has
`LibraryImport.Arena` at the top.

### Deeply nested call expressions in function-call args

User report (confirmed while fixing wc): patterns like
`Deallocate(ptr, Multiply(Pool.CONST, 8))` — a function call whose
*argument* is another non-trivial computed expression — can trip up
the compiler's codegen. Safer form:

```
size = Multiply(Pool.CONST, 8)
Deallocate(ptr, size)
```

Same for `SystemCall(nr, Add(x, Multiply(y, z)), …)` and similar.
Recommendation: precompute into a local when an argument is a
nested call/operator expression.

### CoreUtils-wide: `wc` segfault audit

`wc_exec` segfaulted on every invocation (with args, no args, stdin).
Root cause was the FixedPool string-literal bug above. Other 56 utils
built clean; spot-checked 20 behave correctly (echo, cat, head, tail,
basename, dirname, pwd, seq, uname, whoami, ls, grep, date, tr, rev,
tac, true, false, and 2 more). One-liner functional audit of the
remaining 37 is still pending.

### CoreUtils repo absorbed into AiLangSH (2026-04-18)

`AiLang_CoreUtils/` was a nested git repo (remote
`AiLang-Author/CoreUtils-`). Flattened into AiLangSH — local `.git/`
removed, tree tracked directly in parent. GitHub copy of CoreUtils-
still exists as historical reference; not synced to anymore.
Motivation: cross-cutting changes (regex library → grep) now happen
in a single commit, not two coordinated PRs across two repos.
