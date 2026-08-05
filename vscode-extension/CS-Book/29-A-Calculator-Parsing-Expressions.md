# Chapter 29: A Calculator — Parsing Expressions

**What you'll learn:** How to turn a stream of characters into a structured representation (tokenizing and parsing). How to build and evaluate an Abstract Syntax Tree. The relationship between this small project and what a real compiler does.

---

## A "Real" Program at Last

Up to this point, most of the code you have written has been small examples designed to illustrate a single concept.

Now we will build something more substantial: a program that can read mathematical expressions typed by the user, parse them according to the normal rules of arithmetic, and compute the result.

Examples of what the program should handle:

```
2 + 3 * 4          → 14   (not 20)
(2 + 3) * 4        → 20
10 - 3 - 2         → 5    (left-associative)
-5 + 3             → -2
2 ^ 3 ^ 2          → 512  (or 64, depending on associativity rules you choose)
```

This is a classic "compiler" project in miniature.

---

## The Phases (Again)

A real compiler has phases: lexing, parsing, semantic analysis, optimization, code generation.

Our calculator will have a simplified version of the first few:

1. **Lexing (Tokenization)** — Turn the raw input string into a sequence of tokens:
   - Numbers (`123`, `3.14`)
   - Operators (`+`, `-`, `*`, `/`, `^`, unary `-`)
   - Parentheses
   - End of input

2. **Parsing** — Turn the flat token stream into a tree that respects operator precedence and associativity. This tree is an Abstract Syntax Tree (AST) for the expression.

3. **Evaluation** — Walk the tree and compute the numeric result.

We will not generate machine code (though we could — that would turn the calculator into a tiny JIT compiler).

---

## Lexing by Hand

The lexer is usually the simplest phase.

You walk through the characters one by one:

- When you see a digit, collect the whole number (and maybe a decimal point).
- When you see `+`, `-`, `*`, `/`, or `^`, emit an operator token.
- When you see `( ` or `)`, emit a parenthesis token.
- Skip whitespace.
- When you run out of characters, emit an "end of input" token.

Error handling here is straightforward: if you see a character you don't recognize (like `@`), report a "bad character" error with its position.

---

## Parsing with Precedence

The interesting part is parsing expressions with different operator precedences.

You want `2 + 3 * 4` to be parsed as `2 + (3 * 4)`, not `(2 + 3) * 4`.

There are several well-known techniques for this:

- **Recursive descent with precedence climbing** (relatively simple to implement by hand)
- **Shunting-yard algorithm** (Dijkstra's classic algorithm that uses two stacks)
- **Parser generators** (tools that take a grammar and produce a parser)

For a teaching calculator, recursive descent with precedence climbing is an excellent choice because the code stays relatively close to the grammar you would write on paper.

A simplified grammar might look like:

```
expression   → term ( ('+' | '-') term )*
term         → factor ( ('*' | '/') factor )*
factor       → power ( '^' power )*
power        → atom | '-' power
atom         → NUMBER | '(' expression ')'
```

Each non-terminal becomes a function. The functions call each other according to the grammar, and they build tree nodes as they go.

---

## Building the AST

As the parser recognizes structure, it creates nodes:

```ailang
LinkagePool.Expr {
    "kind":  Initialize=0, CanChange=True   // 1=number, 2=add, 3=sub, 4=mul, ...
    "left":  Initialize=0, CanChange=True
    "right": Initialize=0, CanChange=True
    "value": Initialize=0, CanChange=True   // for number literals
}
```

A node for `2 + 3 * 4` would end up as:

```
Add
├── Number(2)
└── Mul
    ├── Number(3)
    └── Number(4)
```

The tree makes the intended order of operations explicit.

---

## Evaluating the Tree

Once you have the tree, evaluation is usually a simple recursive walk:

```ailang
Function.Eval {
    Input: node: Address
    Output: Integer
    Body: {
        kind = LinkageField(node, Expr, kind)
        IfCondition EqualTo(kind, EXPR_NUMBER) ThenBlock: {
            ReturnValue(LinkageField(node, Expr, value))
        }
        // ... handle Add, Sub, Mul, etc. by recursing on children ...
    }
}
```

This is the same basic pattern a real interpreter uses, and it is also the pattern a compiler's code generator follows — except instead of computing the value immediately, it emits instructions that will compute the value later.

---

## Why This Project Matters

This calculator is small enough to be written by a student in a reasonable amount of time, yet it exercises almost every concept from the first half of the book:

- Memory management (allocating AST nodes)
- Structured data (`LinkagePool`)
- Control flow and recursion
- Error handling (syntax errors, runtime errors like division by zero)
- Explicit contracts between functions

More importantly, it gives the student a visceral understanding of what compilers actually do. When they later look at the real AILang compiler, they will recognize the same patterns at a larger scale.

---

## Possible Extensions

Once the basic calculator works, natural next steps include:

- Adding variables (`let x = 5; x + 3`)
- Adding functions (`sqrt(2) + sin(3)`)
- Generating actual machine code instead of interpreting the tree (a tiny JIT)
- Adding a REPL with history and better error recovery

Each of these extensions forces the student to confront new design decisions while staying grounded in the explicit model of computation they have been building all along.

---

## Key Concepts

- Lexing: characters → tokens
- Parsing: tokens → tree (respecting precedence and associativity)
- Evaluation (or code generation): tree → result (or instructions)
- The same high-level structure appears in every compiler and interpreter

---

*Next: We build something even more interactive — a simple text editor that runs in the terminal.*