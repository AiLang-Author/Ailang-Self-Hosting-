# Chapter 26: Error Handling

**What you'll learn:** The difference between expected problems (file not found, invalid input, network timeout) and unexpected bugs (null pointer, out-of-bounds access, assertion failure). How AILang's `TryBlock` / `CatchError` / `FinallyBlock` mechanism separates these cases. How to write error messages that actually help the user.

---

## Two Very Different Kinds of "Error"

When something goes wrong in a program, it is useful to distinguish between two fundamentally different situations:

1. **Expected problems** — Things the program can reasonably anticipate and should handle gracefully:
   - File not found
   - Network connection refused or timed out
   - Invalid user input
   - Out of disk space
   - Permission denied

2. **Unexpected bugs** — Things that represent programming mistakes or violations of assumptions the code was written under:
   - Dereferencing a null pointer
   - Array index out of bounds

AILang provides `TryBlock` / `CatchError` / `FinallyBlock` for the first category. A verified example (demo 088):

```ailang
TryBlock {
    PrintMessage("try: doing work\n")
    // ... code that might produce expected errors ...
} CatchError e {
    PrintMessage("caught expected error: ")
    PrintNumber(e)
    PrintMessage("\n")
} FinallyBlock {
    PrintMessage("finally: always runs\n")
}
```

This separates expected, recoverable problems from true bugs (which should typically be caught by assertions or crash loudly).
   - Assertion failure
   - Division by zero when the code was supposed to have validated the divisor earlier

These two categories require completely different responses.

For expected problems, the program should generally try to recover, report the situation to the user or caller in a useful way, and continue (or exit cleanly).

For unexpected bugs, the program has reached a state the author explicitly believed was impossible. Continuing is often more dangerous than stopping.

---

## AILang's Structured Error Handling

AILang provides a structured way to separate these cases:

```ailang
TryBlock: {
    content = ReadTextFile("config.txt")
}
CatchError.FileNotFound {
    PrintMessage("Config file missing, using built-in defaults\n")
    content = default_config_text
}
FinallyBlock: {
    PrintMessage("Config loading attempt complete\n")
}
```

- `TryBlock` contains the code that might fail in an expected way.
- `CatchError.*` handlers catch specific expected error conditions.
- `FinallyBlock` runs no matter what happened (success, caught error, or unexpected bug).

This is similar in spirit to exception handling in other languages, but with a few important differences in philosophy:

- AILang encourages you to treat only *expected* problems as catchable errors.
- Unexpected bugs are still expected to be caught by assertions, bounds checking, and other defensive mechanisms, which typically abort rather than being caught by normal error handlers.
- The `FinallyBlock` is a good place for cleanup that must happen regardless of success or failure.

---

## Writing Error Messages That Help

One of the most common failures in error handling is writing useless error messages.

A good error message answers three questions:

1. **What happened?** ("Could not open configuration file")
2. **Where did it happen?** (file name, line number, or at least the operation that was attempted)
3. **What can the user or caller do about it?** ("Check that the file exists and is readable", "Provide a different path using --config", "The program will continue with default settings")

Bad error messages tend to be vague ("Error"), internal ("Assertion failed at line 472 in file foo.c"), or unhelpful ("Operation failed").

AILang's error handling does not magically produce good messages — that is still the programmer's responsibility. But the structure makes it easier to attach context at the point where the error is detected and to propagate it outward.

---

## Hardware Connection

At the machine level, there is no distinction between "expected error" and "unexpected bug." The CPU will execute whatever instructions it is given.

All of the distinction lives in the software conventions we layer on top:

- Expected errors are represented as ordinary return values or explicit error objects that the calling code is expected to check.
- Unexpected bugs are turned into traps, signals, or deliberate crashes (via assertions or bounds checks) that are not intended to be caught by normal error handling.

The operating system and hardware provide mechanisms (signals, exceptions, page faults, etc.) that can be used for both purposes, but it is the program's responsibility to decide which situations belong in which category.

---

## Key Concepts

- Expected problems vs. unexpected bugs require different responses.
- `TryBlock` / `CatchError` / `FinallyBlock` provide structured handling for expected errors.
- Good error messages answer what, where, and what to do.
- The hardware does not distinguish these cases — the distinction is a software convention.

---

*Next: We look at building data structures from first principles — linked lists, stacks, queues, trees, and hash maps — each implemented using only the memory and pointer primitives we have already discussed.*