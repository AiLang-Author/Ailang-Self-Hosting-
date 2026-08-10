# AILang Language Design Notes

---

## Operator Philosophy

**Core principle: No ambiguous operators. Ever.**

AILang deliberately excludes operators that have caused real-world bugs in C, C++, and other languages due to ambiguity, undefined behavior, or implicit side effects.

### No `++` / `--` operators

C/C++ `++` and `--` are excluded because:
- Pre vs post increment semantics are a common source of bugs
- `i++ + ++i` is undefined behavior in C
- Increment inside array index expressions is a footgun
- Silent mutation makes code harder to reason about

**Current explicit form:**
```
n = Increment(n)   // clear, unambiguous, intentional
n = Decrement(n)
i = Add(i, 1)      // used throughout hot loops — verbose but readable
```

---

## Proposed: Compound Assignment Operators

Add `+=` `-=` `*=` `/=` as syntactic sugar for the common reassignment pattern.
No new semantics — purely ergonomic. No ambiguity introduced.

**Motivation:** The grep source alone has `i = Add(i, 1)` 50+ times in hot loops.
Compound assignment cleans this up considerably without adding any semantic risk.

**Proposed syntax:**
```
i += 1        // equivalent to: i = Add(i, 1)
i -= 1        // equivalent to: i = Subtract(i, 1)
i *= 2        // equivalent to: i = Multiply(i, 2)
i /= 2        // equivalent to: i = Divide(i, 2)
i /=/ 8       // equivalent to: i = Modulo(i, 8)
```

**Rules:**
- Left side must be a simple variable (no chained assignment)
- Right side is a full expression
- No combined increment: `i += j += 1` is NOT allowed
- These are statements, not expressions — cannot be used inside conditions

**This preserves the no-ambiguity guarantee** — compound assignment is
always a statement with one clear meaning. It cannot appear mid-expression.

---

## Operators Intentionally Excluded

| Operator | Reason excluded |
|----------|----------------|
| `++` / `--` | Pre/post ambiguity, UB in expressions |
| `?:` ternary | Encourages nesting, readable `IfCondition` preferred |
| Bitwise `~` not | Use `BitwiseNot()` — explicit |
| `<<` `>>` as shift | Use `LeftShift()` `RightShift()` — no confusion with streams |
| `&&` `\|\|` short-circuit as operators | Use `And()` `Or()` — explicit evaluation model |

---

## Notes

- `Increment(n)` and `Decrement(n)` remain valid primitives — useful in
  educational/demonstration code (the 500 programs) where explicitness aids clarity
- Compound assignment is a **parser-level desugaring** — codegen sees
  the expanded form, no new IR nodes needed
- Priority: implement after current SSE / compiler optimization pass

---
*Last updated: April 2026*
