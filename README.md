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

AILang grep beats GNU grep 3.11 in 13 out of 14 tests. Here's the scorecard:

| Test | AILang | GNU grep 3.11 | Winner |
|---|---:|---:|---|
| `'kernel'` | 208 ms | 311 ms | AILang — 1.49× |
| `-F 'kernel'` | 212 ms | 310 ms | AILang — 1.46× |
| `-i 'kernel'` | 251 ms | 358 ms | AILang — 1.42× |
| `-c 'kernel'` | 168 ms | 190 ms | AILang — 1.13× |
| `-n 'kernel'` | 315 ms | 428 ms | AILang — 1.35× |
| `-v 'kernel'` | 352 ms | 472 ms | AILang — 1.34× |
| `-w 'kernel'` | 222 ms | 615 ms | AILang — 2.77× |
| `-ic 'kernel'` | 195 ms | 234 ms | AILang — 1.20× |
| `-wc 'kernel'` | 179 ms | 415 ms | AILang — 2.31× |
| `-Fc 'kernel'` | 169 ms | 193 ms | AILang — 1.14× |
| `'UNIQUE_MARKER_XYZ'` | 49 ms | 79 ms | AILang — 1.61× |
| `-c 'UNIQUE_MARKER'` | 47 ms | 78 ms | AILang — 1.65× |
| `-F 'error_handler'` | 272 ms | 288 ms | AILang — 1.05× |
| `-Fc 'error_handler'` | 223 ms | 163 ms | GNU — 1.36× |

**Highlights:**

- Word match (`-w`) is 2.77× faster than GNU grep.
- Rare-pattern search is 1.65× faster — MemMem's scan-and-skip is very efficient.
- Case-insensitive search is 1.42× faster — MemMemFold pays off.
- The only loss is long fixed-pattern count (`-Fc error_handler`), where GNU's Boyer–Moore–Horspool skip table gives it an edge on 13-character patterns.
- The AILang binary is 118 KB vs. GNU's 1.7 MB — 14× smaller.
- 100% correctness — every test matches GNU grep output exactly.

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
