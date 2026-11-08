# AILang

**A self-hosting systems language designed for consistency, readable code, and AI-assisted development.**

AILang is built around a deliberate trade-off: a constrained syntax with a rich set of primitives. Rather than accumulating many special cases, language constructs follow consistent shapes—from primitive arguments to functions and subroutines. The result is code intended to be easy to scan, search with tools like `grep`, generate with AI, and understand in human–AI pair programming.

The language is not only a proposal: its compiler is written in AILang and compiles AILang programs to native code. The project is working toward **version 1.0.0, targeted for December 31, 2026**.

## Why AILang

- **Consistency over syntax variety.** Primitives, arguments, functions, and subroutines follow coherent conventions, reducing the number of forms a reader or code-generation tool needs to learn.
- **A constrained language with substantial primitives.** Keep the surface syntax deliberate while providing reusable capabilities for practical systems code.
- **Designed to be read and searched.** Clear, regular code is easier to skim, inspect, and navigate with ordinary tools—including `grep`.
- **Built for human and AI collaboration.** Predictable structure supports code generation and review without giving up human readability.
- **Systems programming with a self-hosting compiler.** AILang is statically typed and compiles to native code; the compiler itself is implemented in AILang.

## Performance

AILang's compiler and generated code are being optimized continuously. Project benchmarks show performance competitive with GCC `-O3` on a number of measured workloads, with results varying by program and workload. See the [benchmark results](docs/benchmarks/shapes) for the measurements and test details.

Performance claims should be read in the context of those specific benchmarks—not as a guarantee that every AILang program matches GCC. The goal is to keep improving generated code while retaining the language's emphasis on explicit, readable structure.

## What it can express

AILang is intended to span a broad range of programs: from a small “Hello, world!” to substantial systems software. The repository includes a self-hosted compiler, reusable libraries, command-line utilities, and larger projects such as a custom CAD kernel and an OS runtime layer running on the Linux kernel. These projects are at different stages of development; see their own documentation for current status.

## Try AILang

Compile a source file with the compiler:

```bash
./ailang.x path/to/program.ailang
```

For installation, options, and compiler commands, see [`install_compiler.sh`](install_compiler.sh) and the [compiler documentation](docs/README.md).

Start learning with the [programming manuals](Programming_Manual/) and browse the [demo programs](Demo%20Programs/). The [workspace guide](WORKSPACE.md) describes the repository layout.

## Project status

AILang is under active development. The compiler, language, libraries, and example systems are evolving; expect incomplete features and occasional regressions. The project is progressing toward its **December 31, 2026** version 1.0.0 target. Check the relevant project documentation and tests for the current state of individual components.

## License

The main project is distributed under the [Sean Collins Software License (SCSL v1.0)](License.md). Review the license before using or redistributing the project. The VS Code extension has a separate MIT license.

---

**AILang: consistent syntax, capable primitives, native systems code.**
