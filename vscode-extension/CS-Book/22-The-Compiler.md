# Chapter 22: The Compiler — How Your Code Becomes a Binary

**What you'll learn:** The three classic phases of compilation (lexing, parsing, code generation). How the AILang compiler is organized. What the output of each phase looks like. Why seeing the compiler as "just another program" is important.

---

## From Source Text to Machine Instructions

When you write a program in AILang (or any language), the computer does not execute your source code directly. The source is just text — a description of what you want the machine to do.

The compiler's job is to turn that description into actual machine instructions (and data) that the CPU can execute.

This process is traditionally divided into three major phases:

1. **Lexing** (tokenization)
2. **Parsing**
3. **Code generation**

The AILang compiler itself is written in AILang (self-hosting). Its source lives in `Librarys/Compiler/`. Seeing the compiler as "just another AILang program" that happens to consume AILang source and produce x86-64 binaries is one of the most powerful mental models you can have.

Let's look at the three phases, using a tiny example.

---

## Phase 1: Lexing — Characters Become Tokens

The lexer reads the raw characters of the source file one by one and groups them into **tokens** — the smallest meaningful units of the language.

For this source:

```ailang
SubRoutine.Main {
    PrintMessage("Hello\n")
}
```

The lexer produces something like:

- `KEYWORD:SubRoutine`
- `DOT`
- `IDENTIFIER:Main`
- `LBRACE`
- `IDENTIFIER:PrintMessage`
- `LPAREN`
- `STRING:"Hello\n"`
- `RPAREN`
- `RBRACE`

Whitespace and comments are usually discarded at this stage (unless they are significant, which they are not in AILang).

The lexer does **not** understand the meaning of the program. It only knows the rules for what constitutes a valid token. It does not know that `SubRoutine.Main` is a declaration or that `PrintMessage` is a call — it just knows it saw an identifier, a dot, another identifier, etc.

---

## Phase 2: Parsing — Tokens Become a Tree

The parser takes the stream of tokens and tries to arrange them into a structure that reflects the grammatical rules of the language. The output is usually an **Abstract Syntax Tree** (AST).

For our example, the parser would produce a tree whose root is something like "SubRoutine Declaration" with children:
- Name: "Main"
- Body: a block containing one statement
  - Statement: Call to "PrintMessage"
    - Argument: String literal "Hello\n"

The parser enforces syntax rules. If the tokens cannot be arranged into a valid tree according to the language grammar, the parser reports a syntax error.

At this point the compiler still does not know whether the program is *semantically* valid (does `PrintMessage` exist? Is it being called with the right number and types of arguments?). That comes in later phases (type checking, semantic analysis).

---

## Phase 3: Code Generation — Tree Becomes Machine Code

The code generator walks the AST and emits actual machine instructions (and data) that implement the meaning of the program.

For our tiny "Hello" program, this eventually produces:
- A small ELF executable containing:
  - Machine code that sets up arguments and executes a `write` system call with the string "Hello\n".
  - The actual bytes of the string in a data section.
  - ELF headers telling the operating system how to load and start the program.

The code generator is where the rubber meets the road. It has to make all the decisions about:
- How to represent values (where do local variables live? In registers? On the stack?)
- How to implement control flow (`IfCondition` becomes comparisons and conditional jumps)
- How to call functions (following the calling convention)
- How to allocate and access `FixedPool` and `LinkagePool` fields
- And hundreds of other details

---

## The AILang Compiler's Organization

The AILang compiler is deliberately organized as a chain of relatively independent modules.

Each module is responsible for one category of operations (arithmetic, memory, control flow, I/O, etc.). The main dispatcher walks the AST and, for each node, asks each module in turn: "Can you handle this?"

The first module that says "yes" emits the code for that node. This is the `TryCompile` pattern.

This design has several nice properties:
- Adding support for a new operation usually means writing a new small module and adding one line to the dispatch list.
- Existing modules do not have to change.
- The architecture is "additive" rather than "intrusive."

This is the same pattern the book encourages for user programs: organize around clear boundaries where new features can be added without modifying old code.

---

## What the Compiler Proves

By the time you reach this chapter, you will have seen almost everything the compiler does, piece by piece, in earlier chapters.

Seeing the compiler itself as "just another AILang program" that performs transformations you already understand is one of the most powerful moments in the course.

It closes the loop: the language is powerful enough to describe its own implementation. The explicit, low-magic nature of AILang makes the path from source text to running binary unusually short and visible.

---

## Key Concepts

- Lexing: characters → tokens
- Parsing: tokens → Abstract Syntax Tree
- Code generation: AST → machine instructions + data
- The `TryCompile` dispatch pattern as an example of additive architecture
- The compiler as a concrete example of the ideas in the rest of the book

---

*Next: We look at what the optimizer does (and why even a simple optimizer can make a big difference).*