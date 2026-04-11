# AILANG String Operations Manual

## Overview

AILANG provides a comprehensive set of string primitives built directly into the compiler. String operations are not library functions — they are first-class language constructs handled by the compiler's code generation layer, with SSE2-accelerated implementations for performance-critical operations on x86-64 targets.

### String Representation

- Null-terminated byte sequences (`0x00` terminator)
- UTF-8 compatible (byte-level operations; multibyte awareness is the caller's responsibility)
- Arena-allocated: all operations that return new strings allocate via `Arena_Alloc`
- Pointer-based: strings are addresses to character data

### Core Design Principles

- Compiler primitives: string ops are lowered directly to x86-64 machine code at compile time
- SSE2 acceleration: search, compare, length, copy, and memory operations use 16-byte SIMD paths with scalar fallback for remainders
- Consistent semantics: all operations follow uniform conventions for indices, return values, and edge cases (see Semantic Conventions below)
- Arena memory model: returned strings are arena-allocated; no manual free required

### Semantic Conventions

These apply uniformly across all string primitives:

- All indices are zero-based
- `StringSubstring` takes `(str, start, length)` — the third argument is a **length**, not an end position
- Out-of-bounds or invalid input returns an empty string `""`, never NULL
- Search functions return `-1` when not found
- Boolean functions return `1` for true, `0` for false
- String equality and comparison are byte-level and case-sensitive unless otherwise noted

---

## Basic String Operations

### String Literals

```ailang
greeting = "Hello, World!"
empty_string = ""
newline_string = "Line 1\nLine 2"
tab_string = "Column 1\tColumn 2"
quote_string = "She said \"Hello\""
```

### StringFromChar

Converts an ASCII code to a single-character string.

```ailang
result = StringFromChar(ascii_code)
```

```ailang
letter_a = StringFromChar(65)    // "A"
space    = StringFromChar(32)    // " "
newline  = StringFromChar(10)    // "\n"
```

### StringLength

Returns the number of bytes in a string, not counting the null terminator. SSE2-accelerated.

```ailang
length = StringLength(string)
```

```ailang
hello_len = StringLength("Hello")   // 5
empty_len = StringLength("")         // 0
```

### StringConcat

Concatenates two strings, returning a new arena-allocated string.

```ailang
result = StringConcat(string1, string2)
```

```ailang
greeting  = StringConcat("Hello", " World")     // "Hello World"
full_name = StringConcat(first, StringConcat(" ", last))
```

### StringEquals

Returns `1` if both strings are identical (byte-level, case-sensitive), `0` otherwise. SSE2-accelerated.

```ailang
result = StringEquals(string1, string2)
```

```ailang
is_same  = StringEquals("Hello", "Hello")   // 1
is_diff  = StringEquals("Hello", "hello")   // 0
is_empty = StringEquals(input, "")          // check for empty string
```

### StringCompare

Lexicographic comparison. Returns `0` if equal, non-zero if different. SSE2-accelerated.

```ailang
result = StringCompare(string1, string2)
```

---

## String Analysis Functions

### StringCharAt

Returns the ASCII byte value at the given zero-based index. Returns `0` for NULL input or out-of-bounds access.

```ailang
char_code = StringCharAt(string, index)
```

```ailang
text       = "Hello"
first_char = StringCharAt(text, 0)   // 72  ('H')
last_char  = StringCharAt(text, 4)   // 111 ('o')
```

Note: operates on bytes. Multibyte UTF-8 codepoints occupy multiple indices.

### StringIndexOf

Finds the first occurrence of a substring or character starting at an optional position. Returns the absolute index from the start of the string, or `-1` if not found. SSE2-accelerated.

```ailang
position = StringIndexOf(haystack, needle)
position = StringIndexOf(haystack, needle, start_position)
```

```ailang
text         = "Hello World"
world_pos    = StringIndexOf(text, "World")       // 6
missing_pos  = StringIndexOf(text, "Missing")     // -1
second_apple = StringIndexOf("apple apple", "apple", 1)  // 6
```

### StringContains

Returns `1` if the needle is found anywhere in the haystack, `0` otherwise. SSE2-accelerated.

```ailang
result = StringContains(haystack, needle)
```

```ailang
is_error   = StringContains("Error: not found", "Error")    // 1
is_warning = StringContains("Error: not found", "Warning")  // 0
```

---

## String Manipulation Functions

### StringSubstring / StringExtract

Extracts a portion of a string. Both names refer to the same operation.

**Arguments: `(str, start, length)`** — `start` is a zero-based byte index, `length` is the number of bytes to extract.

Returns an empty string if `str` is NULL, `start` is negative, or `length` is zero or negative.

```ailang
result = StringSubstring(string, start, length)
result = StringExtract(string, start, length)
```

```ailang
text       = "Hello World"
first_word = StringSubstring(text, 0, 5)    // "Hello"
last_word  = StringSubstring(text, 6, 5)    // "World"

// Extract file extension
filename  = "document.pdf"
dot_pos   = StringIndexOf(filename, ".")
ext_start = Add(dot_pos, 1)
ext_len   = Subtract(StringLength(filename), ext_start)
extension = StringSubstring(filename, ext_start, ext_len)  // "pdf"
```

### StringToUpper

Returns a new string with all ASCII lowercase letters converted to uppercase. Non-ASCII bytes are passed through unchanged.

```ailang
result = StringToUpper(string)
```

```ailang
upper = StringToUpper("hello world")   // "HELLO WORLD"
```

### StringToLower

Returns a new string with all ASCII uppercase letters converted to lowercase.

```ailang
result = StringToLower(string)
```

```ailang
lower = StringToLower("HELLO")   // "hello"
```

### StringTrim

Returns a new string with leading and trailing whitespace (bytes <= 32) removed.

```ailang
result = StringTrim(string)
```

```ailang
cleaned     = StringTrim("  Hello World  ")   // "Hello World"
clean_value = StringTrim("\tSomeValue\n")      // "SomeValue"
```

### StringCopy

Copies a string. With one argument, allocates a new arena string and copies into it. With two arguments, copies `src` into `dest` and returns `dest` (no allocation). SSE2-accelerated.

```ailang
copy       = StringCopy(source)
dest_ptr   = StringCopy(dest, source)
```

### StringReplace

Replaces the first occurrence of `old` with `new` in `string`. For full replacement of all occurrences, call iteratively or build a string library function.

```ailang
result = StringReplace(string, old_substring, new_substring)
```

---

## String Conversion Operations

### NumberToString

Converts a 64-bit integer to its decimal string representation. Handles negative numbers. Returns `"0"` for zero.

```ailang
result = NumberToString(number)
```

```ailang
age_str      = NumberToString(25)        // "25"
negative_str = NumberToString(-42)       // "-42"
zero_str     = NumberToString(0)         // "0"

message = StringConcat("Error ", NumberToString(404))  // "Error 404"
```

### StringToNumber

Parses a decimal integer from a string. Skips leading whitespace, handles optional leading `+` or `-`. Stops at the first non-digit character. Returns `0` for non-numeric input. Integer only — no decimal point support.

```ailang
result = StringToNumber(string)
```

```ailang
age      = StringToNumber("25")       // 25
negative = StringToNumber("-42")      // -42
padded   = StringToNumber("  100 ")  // 100
```

---

## Memory Operations (SSE2-Accelerated)

These operate on raw memory regions rather than strings, but are available as primitives.

### MemorySet

Fills `count` bytes at `dest` with `value`. Returns `count`.

```ailang
result = MemorySet(dest, value, count)
```

### MemoryCopy

Copies `count` bytes from `src` to `dest`. Returns `count`.

```ailang
result = MemoryCopy(dest, src, count)
```

### MemCompare

Compares two memory regions of `length` bytes. Returns `0` if equal, `1` if different.

```ailang
result = MemCompare(addr1, addr2, length)
```

### MemChr

Finds the first occurrence of `byte` in `length` bytes starting at `addr`. Returns the byte offset if found, `-1` if not.

```ailang
result = MemChr(addr, byte, length)
```

---

## Advanced Text Processing

### Line-by-Line Processing

```ailang
Function.ProcessLines {
    Input: content: Address
    Output: Integer
    Body: {
        offset       = 0
        line_count   = 0
        total_length = StringLength(content)

        WhileLoop LessThan(offset, total_length) {
            newline_pos = StringIndexOf(content, "\n", offset)

            IfCondition EqualTo(newline_pos, -1) ThenBlock: {
                // Last line with no trailing newline
                line_len = Subtract(total_length, offset)
                line     = StringSubstring(content, offset, line_len)
                offset   = total_length
            } ElseBlock: {
                line_len = Subtract(newline_pos, offset)
                line     = StringSubstring(content, offset, line_len)
                offset   = Add(newline_pos, 1)
            }

            line = StringTrim(line)
            IfCondition GreaterThan(StringLength(line), 0) ThenBlock: {
                ProcessLine(line)
                line_count = Add(line_count, 1)
            }
        }

        ReturnValue(line_count)
    }
}
```

### CSV Field Extraction

```ailang
Function.ExtractCSVField {
    Input: row:        Address
    Input: field_index: Integer
    Output: Address
    Body: {
        i      = 0
        offset = 0

        WhileLoop LessThan(i, field_index) {
            next = StringIndexOf(row, ",", offset)
            IfCondition EqualTo(next, -1) ThenBlock: {
                ReturnValue("")
            }
            offset = Add(next, 1)
            i      = Add(i, 1)
        }

        next = StringIndexOf(row, ",", offset)
        IfCondition EqualTo(next, -1) ThenBlock: {
            len = Subtract(StringLength(row), offset)
        } ElseBlock: {
            len = Subtract(next, offset)
        }

        field = StringSubstring(row, offset, len)
        ReturnValue(StringTrim(field))
    }
}
```

### Key-Value Config Parsing

```ailang
Function.ParseConfigLine {
    Input: line: Address
    Output: Address   // Returns array [key, value] or empty on failure
    Body: {
        line = StringTrim(line)

        // Skip empty lines and comments (# = ASCII 35)
        IfCondition EqualTo(StringLength(line), 0) ThenBlock: { ReturnValue(0) }
        IfCondition EqualTo(StringCharAt(line, 0), 35) ThenBlock: { ReturnValue(0) }

        eq_pos = StringIndexOf(line, "=")
        IfCondition EqualTo(eq_pos, -1) ThenBlock: { ReturnValue(0) }

        key       = StringSubstring(line, 0, eq_pos)
        key       = StringTrim(key)
        val_start = Add(eq_pos, 1)
        val_len   = Subtract(StringLength(line), val_start)
        value     = StringSubstring(line, val_start, val_len)
        value     = StringTrim(value)

        pair = XArray.XCreate()
        XArray.XPush(pair, key)
        XArray.XPush(pair, value)
        ReturnValue(pair)
    }
}
```

---

## Best Practices

**Index arithmetic with StringSubstring:** always compute `length = end_pos - start_pos` explicitly. The third argument is a byte count, not a position.

**Case-insensitive comparison:** convert both strings with `StringToLower` before comparing with `StringEquals`.

**Parsing numbers from mixed text:** use `StringIndexOf` to locate the numeric region, `StringSubstring` to extract it by length, then `StringToNumber`.

**UTF-8 awareness:** `StringCharAt`, `StringSubstring`, and length operations work on bytes. Multibyte characters (non-ASCII) will have indices that do not align with visible codepoint positions. If your text is ASCII-only these are equivalent; for Unicode content, account for multi-byte sequences manually.

**More complex string operations** (e.g. regex, Levenshtein distance, formatting, multi-replace) are intentionally outside the primitive set. Build a string library for those needs as required.