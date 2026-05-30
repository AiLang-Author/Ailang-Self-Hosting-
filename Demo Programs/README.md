# AILang Demo Programs

This directory contains the **official progressive teaching examples** for the AILang programming language.

- 132 focused, self-contained `.ailang` programs
- Designed as cumulative teaching aids (from absolute beginner to advanced language features)
- See the full curated curriculum and teaching notes here:

**→ [DEMO_PROGRAMS_TEACHING_INDEX.md](./DEMO_PROGRAMS_TEACHING_INDEX.md)**

## Quick Start — Compile & Run Any Demo

```bash
# From the project root
./ailang.x "Demo Programs/programs/001_hello_world.ailang"  /tmp/hello.x
/tmp/hello.x
```

Some compiler builds also accept the `-o` form:

```bash
./ailang.x "Demo Programs/programs/015_multiplication_table.ailang" -o /tmp/table.x
/tmp/table.x
```

The resulting `.x` file is a native, standalone Linux x86-64 executable (no runtime, no GC, no dependencies).

## Structure

- `programs/` — All the actual demo source files (currently numbered with some gaps for historical reasons)
- `DEMO_PROGRAMS_TEACHING_INDEX.md` — The master teaching curriculum document with:
  - Recommended clean sequential numbering
  - Logical grouping (Basics → Types → Operators → Control Flow → Loops → Functions → Error Handling → Algorithms → Advanced Idioms)
  - Notes on AILang-specific features (Fork/Branch, explicit everything, pool-based multi-return, etc.)
  - The two important unnumbered advanced control-flow companions (`fork_not_switch.ailang` and the large combinatorial `fork_branch_combinatorial.ailang`)

These programs are the best way to learn both general programming and AILang's explicit, unambiguous philosophy by example.

---

**Compiler binary** is typically `ailang.x` (or `Main.x` / `ailang_new.x` during development) in the project root.

Enjoy the journey from hello world to combinatorial Fork + Branch decision trees!