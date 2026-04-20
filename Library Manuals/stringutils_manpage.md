# Library.StringUtils(ailang)

## NAME

`Library.StringUtils` — string combination utilities for AILang

## SYNOPSIS

```
LibraryImport.StringUtils
```

> Requires: `LibraryImport.Arena` (pulled in automatically)

---

## DESCRIPTION

`StringUtils` provides higher-level string operations built from AILang's
core primitives (`GetByte`, `SetByte`, `Allocate`, `StringLength`,
`StringConcat`). It covers the patterns users reach for most: parsing,
prefix/suffix testing, search, padding, trimming, and repetition.

**This library handles combinations — not primitives.**
Operations like `StringLength` and `StringConcat` are compiler built-ins
and are not part of this library. `StringUtils` composes those primitives
into the functions that would otherwise be reimplemented repeatedly in
user code.

### Conventions

- All functions accept null-terminated byte string `Address` arguments.
- Return type is either `Integer` (predicates, positions, counts) or
  `Address` (a newly allocated string).
- Allocated results are Arena-backed. Caller does not free them.
- Empty string inputs are handled gracefully — see individual entries.

---

## FUNCTIONS

---

### PARSING

---

#### `StringToInt`

```
Function.StringToInt
    Input:  s: Address
    Output: Integer
```

Parses a decimal digit string into an integer. Scanning stops at the
first non-digit byte (whitespace, punctuation, null terminator).
Returns `0` on empty input.

**Note:** Does not handle a leading `-` sign. Wrap in user code when
negative parsing is needed.

**Examples:**
```
n = StringToInt("42")       // → 42
n = StringToInt("100abc")   // → 100  (stops at 'a')
n = StringToInt("")         // → 0
```

---

### PREFIX / SUFFIX TESTS

---

#### `StringStartsWith`

```
Function.StringStartsWith
    Input:  s:      Address
    Input:  prefix: Address
    Output: Integer          // 1 = match, 0 = no match
```

Returns `1` if `s` begins with `prefix`, `0` otherwise.
An empty `prefix` always returns `1`.

**Examples:**
```
StringStartsWith("hello world", "hello")   // → 1
StringStartsWith("hello world", "world")   // → 0
StringStartsWith("hello world", "")        // → 1
```

---

#### `StringEndsWith`

```
Function.StringEndsWith
    Input:  s:      Address
    Input:  suffix: Address
    Output: Integer          // 1 = match, 0 = no match
```

Returns `1` if `s` ends with `suffix`, `0` otherwise.
An empty `suffix` always returns `1`.
Returns `0` if `suffix` is longer than `s`.

**Examples:**
```
StringEndsWith("hello world", "world")   // → 1
StringEndsWith("hello world", "hello")   // → 0
StringEndsWith("hello world", "")        // → 1
```

---

### SEARCH

---

#### `StringIndexOf`

```
Function.StringIndexOf
    Input:  haystack: Address
    Input:  needle:   Address
    Output: Integer          // byte offset, or -1 if not found
```

Returns the zero-based byte offset of the first occurrence of `needle`
in `haystack`, or `-1` if absent.

An empty `needle` always returns `0` (matches at the start).
Returns `-1` if `needle` is longer than `haystack`.

**Examples:**
```
StringIndexOf("hello world", "world")   // → 6
StringIndexOf("hello world", "xyz")     // → -1
StringIndexOf("hello world", "")        // → 0
```

---

#### `StringContains`

```
Function.StringContains
    Input:  haystack: Address
    Input:  needle:   Address
    Output: Integer          // 1 = found, 0 = not found
```

Returns `1` if `needle` appears anywhere in `haystack`, `0` otherwise.
Thin wrapper over `StringIndexOf` — use this when you only need
presence/absence and not the position.

**Examples:**
```
StringContains("hello world", "world")   // → 1
StringContains("hello world", "xyz")     // → 0
```

---

### PADDING

---

#### `StringPadLeft`

```
Function.StringPadLeft
    Input:  s:        Address
    Input:  width:    Integer
    Input:  pad_char: Integer   // ASCII byte value of padding character
    Output: Address             // new allocated string
```

Right-aligns `s` in a field of `width` bytes by prepending `pad_char`
on the left. If `s` is already `>= width` bytes, returns a copy of `s`
unmodified. Result is a new Arena-backed buffer.

**Examples:**
```
StringPadLeft("42",    6, 32)   // → "    42"   (space-padded)
StringPadLeft("42",    6, 48)   // → "000042"   (zero-padded, '0' = 48)
StringPadLeft("hello", 3, 32)   // → "hello"    (longer than width)
```

---

#### `StringPadRight`

```
Function.StringPadRight
    Input:  s:        Address
    Input:  width:    Integer
    Input:  pad_char: Integer   // ASCII byte value of padding character
    Output: Address             // new allocated string
```

Left-aligns `s` in a field of `width` bytes by appending `pad_char`
on the right. If `s` is already `>= width` bytes, returns a copy of `s`
unmodified. Result is a new Arena-backed buffer.

**Examples:**
```
StringPadRight("hi",    6, 32)   // → "hi    "
StringPadRight("hello", 3, 32)   // → "hello"   (longer than width)
```

---

### TRIMMING

---

#### `StringTrim`

```
Function.StringTrim
    Input:  s: Address
    Output: Address   // new allocated string
```

Returns a new string with leading and trailing ASCII whitespace removed.

Whitespace characters recognized:
| Value | Character |
|-------|-----------|
| 32    | space     |
| 9     | tab       |
| 10    | newline   |
| 13    | carriage return |

An all-whitespace or empty input returns an empty string `""`.
Result is a new Arena-backed buffer.

**Examples:**
```
StringTrim("  hello  ")     // → "hello"
StringTrim("\t hello \n")   // → "hello"
StringTrim("   ")           // → ""
StringTrim("hello")         // → "hello"
```

---

### REPEAT

---

#### `StringRepeat`

```
Function.StringRepeat
    Input:  s:     Address
    Input:  count: Integer
    Output: Address          // new allocated string
```

Returns a new string that is `s` repeated `count` times consecutively.
`count <= 0` returns an empty string. Result is Arena-backed.

**Examples:**
```
StringRepeat("ab", 3)    // → "ababab"
StringRepeat("-",  10)   // → "----------"
StringRepeat("x",  0)    // → ""
```

---

## FUNCTION SUMMARY

| Function | Input | Output | Description |
|----------|-------|--------|-------------|
| `StringToInt` | `s` | `Integer` | Parse decimal string to integer |
| `StringStartsWith` | `s`, `prefix` | `Integer` | Prefix test |
| `StringEndsWith` | `s`, `suffix` | `Integer` | Suffix test |
| `StringIndexOf` | `haystack`, `needle` | `Integer` | First occurrence offset or -1 |
| `StringContains` | `haystack`, `needle` | `Integer` | Presence test |
| `StringPadLeft` | `s`, `width`, `pad_char` | `Address` | Right-align with padding |
| `StringPadRight` | `s`, `width`, `pad_char` | `Address` | Left-align with padding |
| `StringTrim` | `s` | `Address` | Strip leading/trailing whitespace |
| `StringRepeat` | `s`, `count` | `Address` | Repeat string N times |

---

## MEMORY

All functions returning `Address` allocate from the Arena. Results are
valid for the lifetime of the Arena and do not need to be freed by the
caller. Input strings are never modified.

---

## SEE ALSO

`StringLength` (compiler primitive),
`StringConcat` (compiler primitive),
`StringCompare` (compiler primitive),
`Library.Arena`

---

## VERSION

Added: April 2026 — replacement for retired StringUtils (deprecated
two-arg `Dereference` form). Written against current core primitives.

## COPYRIGHT

Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
