# Library.Regex_Thompson(ailang)

## NAME

`Library.Regex_Thompson` — Thompson NFA regular expression engine

## SYNOPSIS

```
LibraryImport.Regex_Thompson
```

> Requires: `LibraryImport.Arena` (pulled in automatically)

---

## DESCRIPTION

`Library.Regex_Thompson` is a full regular expression engine built on
the Thompson NFA construction algorithm. It compiles a pattern string
into an NFA handle and provides three search strategies of increasing
speed: anchored match at a position, unanchored single-pass NFA search,
and a lazy DFA that caches NFA state sets for O(1) per-byte dispatch.

The engine is the backbone of AILang's `grep` implementation and is
designed for high-throughput line-at-a-time scanning.

### Supported Syntax

| Syntax | Meaning |
|--------|---------|
| `.` | Any byte except `\n` |
| `*` | Zero or more (greedy) |
| `+` | One or more (greedy) |
| `?` | Zero or one |
| `^` | Start of string assertion |
| `$` | End of string assertion |
| `[abc]` | Character class |
| `[a-z]` | Character range |
| `[^abc]` | Negated class |
| `\|` | Alternation |
| `(expr)` | Grouping |
| `\n` `\r` `\t` | Escape sequences |

### Known Limitations

- No `\( \)` grouping with backreferences
- No `\{m,n\}` counted repetition
- No `--color` highlighting support
- Case-insensitive matching (`-i`) is emulated by lowercasing the
  pattern and the input — the `CASE_INSENSITIVE` flag slot exists but
  is not implemented inside the engine itself

---

## FUNCTIONS

---

### `Regex_Compile`

```
Function.Regex_Compile
    Input:  pattern: Address   // NUL-terminated pattern string
    Input:  flags:   Integer   // reserved — pass 0
    Output: Address            // opaque handle, or 0 on error
```

Compiles `pattern` into an NFA and returns an opaque handle. The handle
is valid until `Regex_Free` is called. Returns `0` if the pattern is
`null`, the pattern contains a syntax error, or allocation fails.

The `flags` argument is reserved for future use. Pass `0`.

**Memory:** Each compiled regex allocates one block of
`MAX_STATES × STATE_SIZE` bytes (4096 × 40 = 163 840 bytes) for the
NFA state table, plus a 32-byte handle header. Free with `Regex_Free`
when done.

**Examples:**
```
h = Regex_Compile("foo.*bar", 0)    // matches "foo" ... "bar"
h = Regex_Compile("^hello$", 0)     // exact line match
h = Regex_Compile("[0-9]+", 0)      // one or more digits
h = Regex_Compile("cat|dog", 0)     // alternation
```

---

### `Regex_Match`

```
Function.Regex_Match
    Input:  regex:     Address   // handle from Regex_Compile
    Input:  text:      Address   // NUL-terminated string to match
    Input:  start_pos: Integer   // byte offset to begin matching
    Output: Integer              // match length in bytes, or -1
```

Anchored match: attempts to match the pattern starting at exactly
`start_pos` in `text`. Returns the number of bytes consumed by the
match (≥ 0), or `-1` if no match at that position.

To find a match anywhere in a string, loop `start_pos` from `0` to
`StringLength(text)` calling `Regex_Match` at each position, or use
`Regex_Search` which does this in a single pass.

**Note:** `text` must be NUL-terminated. `start_pos` must be ≤
`StringLength(text)`.

**Examples:**
```
h = Regex_Compile("foo", 0)
n = Regex_Match(h, "foobar", 0)    // → 3  (matched "foo")
n = Regex_Match(h, "foobar", 1)    // → -1 (no match at offset 1)
n = Regex_Match(h, "barfoo", 3)    // → 3  (matched "foo" at offset 3)
```

---

### `Regex_Search`

```
Function.Regex_Search
    Input:  regex:    Address   // handle from Regex_Compile
    Input:  text:     Address   // bytes to search (need not be NUL-terminated)
    Input:  text_len: Integer   // number of bytes to scan
    Output: Integer             // 1 if match found anywhere, 0 otherwise
```

Unanchored single-pass search. Keeps the NFA start state active at
every position so any position can be a fresh match start. Cost is
O(`text_len` × active NFA states) — much cheaper than calling
`Regex_Match` in a loop for each position.

`text_len` is passed explicitly so the caller does not need a NUL
terminator at `text[text_len]`. This is the function used by `grep`'s
per-line dispatch.

**Examples:**
```
h = Regex_Compile("foo", 0)
found = Regex_Search(h, "hello foobar world", 18)   // → 1
found = Regex_Search(h, "hello world", 11)           // → 0
```

---

### `Regex_DFAInit`

```
Function.Regex_DFAInit
    Input:  regex: Address   // handle from Regex_Compile
    Output: Integer          // 1 if DFA ready, 0 if not applicable
```

Initializes a lazy DFA for the compiled regex. The DFA caches NFA
state sets as DFA states with 256-entry transition tables, enabling
O(1) per-byte dispatch instead of per-byte NFA simulation.

Returns `0` (DFA not available) if the pattern contains `^` or `$`
assertions — positional semantics cannot be DFA'd without per-position
specialization. Caller falls back to `Regex_Search`.

Only useful for single-pattern grep. Multi-pattern use cannot share
a single DFA buffer. Call once after `Regex_Compile`; the DFA state
persists for the lifetime of the handle.

---

### `Regex_DFASearch`

```
Function.Regex_DFASearch
    Input:  text:     Address   // bytes to search
    Input:  text_len: Integer   // number of bytes
    Output: Integer             // 1 = match, 0 = no match, -1 = overflow
```

Unanchored search via the lazy DFA. Per-byte cost is one table lookup
(address arithmetic + `Dereference`). On DFA state overflow (more than
`DFA.cap` = 1024 distinct NFA state sets encountered) returns `-1` —
caller should fall back to `Regex_Search` for the remainder of the
input.

`Regex_DFAInit` must have been called successfully before using this
function.

---

### `Regex_GetPrefix`

```
Function.Regex_GetPrefix
    Input:  regex:   Address   // handle from Regex_Compile
    Input:  out_buf: Address   // caller-supplied buffer
    Input:  max_len: Integer   // capacity of out_buf
    Output: Integer            // number of bytes written
```

Extracts the longest literal prefix from the compiled regex — a
consecutive run of `CHAR` states from the start, with no branching.
Writes up to `max_len` bytes into `out_buf`. Returns the actual count
written.

A leading `^` anchor is transparently skipped so `"^foo.*"` returns
`"foo"` (length 3).

Returns `0` if the pattern starts with a branch or quantifier (e.g.
`.*`, `[abc]`, `a|b`).

**Use case:** Pre-filter candidate match positions with Boyer-Moore
before calling `Regex_Match`. Effective when `prefix_len >= 2`. Used
internally by grep's `REGEX_PREFIX_BM` strategy.

---

### `Regex_Free`

```
Function.Regex_Free
    Input:  regex: Address   // handle from Regex_Compile
    Output: Integer          // 1 on success, 0 if regex was null
```

Frees the NFA state table and handle header allocated by
`Regex_Compile`. After this call the handle is invalid.

---

### `Regex_FreeMatchState`

```
Function.Regex_FreeMatchState
    (no arguments, no return value)
```

Frees the persistent thread buffers used by `Regex_Match` and
`Regex_Search`. These buffers are allocated once on first use and
reused across calls to avoid per-line allocation overhead. Call this
when all matching is complete and you want to reclaim the memory.

Optional — process exit reclaims it automatically.

---

## TYPICAL USAGE PATTERN

```
// Compile once
h = Regex_Compile("Function\\..*", 0)
IfCondition EqualTo(h, 0) ThenBlock: {
    // pattern error
}

// Optional: init DFA for single-pattern hot path
dfa_ok = Regex_DFAInit(h)

// Per-line search
IfCondition EqualTo(dfa_ok, 1) ThenBlock: {
    result = Regex_DFASearch(line, line_len)
    IfCondition LessThan(result, 0) ThenBlock: {
        // DFA overflow — fall back
        result = Regex_Search(h, line, line_len)
    }
} ElseBlock: {
    result = Regex_Search(h, line, line_len)
}

// Cleanup
Regex_Free(h)
Regex_FreeMatchState()
```

---

## PERFORMANCE TIERS

From fastest to slowest per line:

| Strategy | When | Cost |
|----------|------|------|
| Lazy DFA | Single pattern, no assertions, DFA not overflowed | O(1) per byte |
| Regex prefix + BM | Pattern has ≥ 2-byte literal prefix | Skip most positions |
| `Regex_Search` NFA | General case | O(len × active states) |
| `Regex_Match` loop | Anchored scan, external caller loop | O(len × depth) |

The `grep` dispatcher selects the strategy once at compile time
(`CompileAllPatterns`) and dispatches via a `Branch` table per line —
no flag checks in the hot path.

---

## CONSTANTS

```
RegexConstants.MAX_STATES    // 4096 — max NFA states per pattern
RegexConstants.MAX_THREADS   // 1024 — max concurrent NFA threads
RegexConstants.STATE_SIZE    // 40   — bytes per NFA state (8-byte aligned)
DFA.cap                      // 1024 — max lazy DFA states before overflow
```

---

## SEE ALSO

`Library.Arena`,
`grep.ailang` (consumer of this library),
`Library.StringUtils`

---

## VERSION

April 2026 rewrite. Key fixes over prior version:
- State structure corrected to 40-byte alignment (was 24 — caused OOB writes)
- List node layout fixed: `is_out2` moved to offset 16 (was offset 12, clobbered `next` pointer)
- Thread buffers made persistent across calls (eliminated 30M+ allocations per grep run)
- `Regex_Search` single-pass unanchored driver added (replaces per-position `Regex_Match` loop)
- Lazy DFA added for single-pattern O(1)-per-byte hot path
- Pool-based AST node allocators replace per-node `Allocate` calls

## COPYRIGHT

Copyright (c) 2025–2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
