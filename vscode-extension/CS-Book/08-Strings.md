# Chapter 8: Strings

**What you'll learn:** What a string actually is at the machine level (a pointer to a null-terminated sequence of bytes). How AILang treats string operations as first-class compiler builtins with ~20-26 specialized primitives, many of which are accelerated with SSE2 SIMD and REP-string instructions on x86-64. Why this combination gives you both radical explicitness and real performance.

---

## The Simplest Possible String

When you write:

```ailang
greeting = "Hello"
```

what actually exists in memory?

At the lowest level, a string in AILang is a classic C-style representation:

- An `Address` (pointer) to the first byte of a sequence.
- The sequence is terminated by a zero byte (`\0`).

The literal `"Hello"` lives in memory as the six bytes `48 65 6C 6C 6F 00`. The variable holds only the pointer.

This is deliberate. AILang does not hide the representation behind a high-level object.

However, **all string operations are compiler builtins**, not ordinary function calls. The compiler knows roughly two dozen specialized string primitives and lowers them directly to highly optimized x86-64 code, including:

- Classic `REP MOVSB` / `REPE CMPSB` / `REPNE SCASB` instructions for bulk work.
- SSE2 SIMD paths (16-byte parallel compares, searches, copies, etc.) with scalar fallbacks.

This is why string operations in AILang feel high-level and safe while still delivering performance that approaches hand-written assembly in hot paths.

---

## Strings Are Not Values — They Are Locations

In high-level languages, strings often behave like values:
- You can assign them.
- You can pass them around.
- They seem to have a size and a content that travels with them.

In reality (and in AILang), a string variable is just a pointer. The actual characters live somewhere else in memory.

This means:

- Copying a string variable copies the pointer, not the characters.
- Two variables can point to the same string data.
- If you modify the data through one pointer, the change is visible through the other.
- If the memory is freed while other pointers still point to it, you have a use-after-free.

AILang makes the pointer nature visible through a rich set of explicit, compiler-builtin operations (documented in the String Operations manual). Some of the core ones:

- `StringLength`, `StringConcat`, `StringCompare`, `StringEquals`
- `StringCharAt`, `StringIndexOf`, `StringContains`
- `StringSubstring`, `StringExtract`, `StringTrim`, `StringReplace`
- `StringToUpper`, `StringToLower`
- `NumberToString`, `StringToNumber`
- Memory-level primitives (`MemoryCopy`, `MemorySet`, `MemCompare`) that are heavily SSE2-accelerated

All of these are lowered by the compiler with architecture-specific fast paths. You still see exactly which operation you are performing.

---

## Real Literal Syntax (Verified Demos)

String literals support standard escapes and Unicode. The compiler handles the encoding; the result is still a plain arena-allocated, null-terminated byte sequence.

**Demo 004 — Escape sequences**

```ailang
PrintMessage("tab\there\n")
PrintMessage("quote\"inside\n")
PrintMessage("backslash\\once\n")
PrintMessage("two lines\nin one string\n")
```

**Demo 005 — Unicode (UTF-8 bytes under the hood)**

```ailang
PrintMessage("Greek:   Γειά σου\n")
PrintMessage("Japanese: こんにちは\n")
PrintMessage("Emoji:   🚀 🌍 ✨\n")
```

These are real, working examples from the teaching suite. The data is bytes. The operations that act on them are compiler builtins with heavy optimization.

---

## Hardware Connection

At the lowest level, strings are addresses + byte walks.

The compiler, however, does not emit naive byte-by-byte loops for everything. For performance-critical operations it generates:

- `REP MOVSB` / `REPE CMPSB` / `REPNE SCASB` (highly optimized microcoded string instructions on modern x86).
- SSE2 SIMD code paths (XMM registers, 16 bytes at a time) for length, compare, search, copy, and memory primitives, with scalar fallbacks for remainders.

This is exactly what the user and the official String Operations manual describe: roughly two dozen string primitives that are first-class compiler builtins, many of them SSE2-accelerated on x86-64 targets.

The explicit named operations in source give you the safety and clarity. The compiler gives you the speed that would normally require writing assembly by hand.

---

## Key Concepts

- Representation: `Address` pointing to null-terminated bytes (arena allocated, UTF-8 compatible at the byte level).
- Operations: ~20-26 compiler-builtin primitives (not library functions).
- Performance: On x86-64, critical paths use REP-string instructions and SSE2 SIMD.
- Explicitness: You always name the operation you want (`StringCompare`, `StringIndexOf`, `MemoryCopy`, etc.).
- The combination of simple representation + rich optimized builtins is what makes AILang strings both understandable and fast in practice.

---

*Next: We look at arrays — the most fundamental ordered collection, and how index arithmetic works at the hardware level.*