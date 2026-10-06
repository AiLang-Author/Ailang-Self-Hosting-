# C and C++ versus AILANG

Same shape-area program, two languages. `shapes.ailang` and `shapes.cpp` in this directory are the sources. `run.sh` rebuilds both, pins one core, and checks that paired results carry the same f64 bits.

The example is Casey Muratori's timing rewrite of the Clean Code shapes chapter, "Clean Code, Horrible Performance" (28 February 2023). Square, rectangle, triangle, and circle. Area is `w*w`, `w*h`, `0.5*w*h`, or `pi*w*w`. The f64 kernels are the paired comparison. The f32 kernels in `shapes.cpp` are the virtual-call listings from that article. AILANG has no vtable, so those rows are C++ only.

## Why use AILANG

`run.sh` does not pass `-TS`. The compiler reads both files and parsed 142 declarations, and the unshaken executable contains the benchmark and the whole Arena library, including slab sizes this program never asks for. A second build, `shapes_ts.x`, passes `-TS` and keeps 82 of those 121 functions. Tree-shaking changes the binary, not the two files a person reads.

That is the comparison to show when someone asks why the language exists. The state of the AILANG program is one 1,005-line file and one 2,128-line library. A person can read both, and then they have seen every name the program can reach. `shapes.cpp` is 607 lines, and the other 12,805 lines are headers the programmer did not set out to read. Those headers are the rest of the program's state, spread across 80 files.

The kernels are a list of named steps, so the running values stay visible. `SumFadd` keeps `acc`, `psum`, `cursor`, and `rep` in order:

```ailang
WhileLoop LessThan(cursor, limit) {
    w = Dereference(Add(cursor, 8))
    psum = Float_Add(psum, w)
    cursor = Add(cursor, 24)
}
```

The C++ twin is shorter, and it hides the same walk inside a struct and a subscript:

```cpp
for (int i = 0; i < n; i++) acc = acc + g_s64[i].w;
```

`g_s64` is a `Shape64` defined earlier in `shapes.cpp`, and `f64` is a name for `double`. Both are easy to find in this one file. The words underneath them (`uint64_t`, the calling convention, `printf` for the row) are not. In the AILANG loop every operation is a word the language already defined.

## Why the AILANG program is lighter

C++17 has 84 keywords, including the alternative tokens (`and`, `or`, `bitand`, and the rest). Those words are the grammar: `if`, `while`, `class`, `template`, `new`. The jobs this benchmark actually does are not keywords. They arrive through headers.

`shapes.cpp` names seven of them:

```cpp
#include <cstdint>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <new>
```

`cstdint` supplies `uint32_t` and `uint64_t`. `cstdio` supplies `printf`. `cstdlib` supplies `malloc`. `cstring` supplies `memcpy`. `ctime` supplies `clock_gettime`. `new` supplies placement new. g++ 13.3, with `-std=c++17 -fno-exceptions -fno-rtti`, follows those seven names into 80 header files.

AILANG's keyword table registers 154 words. The list is `Kw_Init` in `Librarys/Compiler/Frontend/Lexer/Library.CLexerKeywords.ailang`. The extra words are the jobs C++ puts in a header:

| The program needs | C++ | AILANG |
|---|---|---|
| Integer widths | `uint64_t` from `<cstdint>` | `Integer`, `UInt64`, `Int64` |
| Arithmetic | `+` `*` on a `double` from the language, plus `<cstdint>` for the bit width | `Add`, `Multiply`, `Float_Add`, `Float_Mul`, `Float_Div` |
| A record array | a `static` buffer, or `malloc` | `FixedPool` |
| A clock | `clock_gettime` from `<ctime>` | `SystemCall` (228 is `clock_gettime`) |
| Print a row | `printf` from `<cstdio>` | `PrintMessage`, `PrintNumber` |
| Scratch storage | `malloc` from `<cstdlib>`, placement `new` | `Allocate` |

`Float_Add`, `PrintMessage`, `Dereference`, and `Allocate` are compiler-known names rather than entries in the 154-word table. They are still part of the base language. A program spells them. It does not include a file to get them.

`shapes.ailang` has one import, `LibraryImport.Arena`. That file is `Librarys/Library.Arena.ailang`, 2,128 lines, and it imports nothing else. It is the body of `Allocate`. On the C++ side the body of `malloc` stays in libc and is not part of the header count below.

## Line count

Physical lines, each file once.

| What the compiler reads | Lines |
|---|---:|
| `shapes.ailang` | 1,005 |
| `Library.Arena.ailang` | 2,128 |
| AILANG total | 3,133 |
| `shapes.cpp` | 607 |
| 80 headers pulled in by the seven includes | 12,805 |
| C++ total | 13,412 |

The largest headers are configuration and C library prototypes, not the shape kernels. `c++config.h` is 2,294 lines, `stdlib.h` is 1,169, `stdio.h` is 985. After the preprocessor drops comments and the `#if` branches this machine does not take, the merged C++ translation unit is 4,098 lines, 2,266 of them non-empty. The 13,412 figure is the source you read if you follow every include.

## Performance

Hot run, N = 4096 shapes, 200 repetitions, one core pinned on this FX-8320. The TSC runs at 3.7 GHz, so cycles per shape are `nanoseconds * 3.7 / 819200`. Each number is the median of three runs. The AILANG binary is the one `run.sh` builds with the installed compiler (`bdf49c48`, the `ccd857bd` master). It is byte-identical to the 6 October 2026 timing run. The C++ numbers are the three runs of this `shapes.cpp` under

```text
g++ -O3 -std=c++17 -fno-exceptions -fno-rtti -fno-devirtualize
    -fno-tree-vectorize -fno-tree-slp-vectorize -fno-unroll-loops
```

Vectorization and unrolling stay off so the x4 kernels are the only unrolls. Paired f64 bits matched on every row, including corner `4724367508723648189`. `area-table-x4` is `4726534476088133271` on both, three ulps away from the serial sum, and the two compilers agree with each other.

| Kernel | AILANG | C++ | C++ name |
|---|---:|---:|---|
| loop-int | 4.1 | 3.7 | loop-int |
| loop-fadd | 5.7 | 5.1 | loop-fadd |
| loop-fmul | 5.9 | 5.1 | loop-fmul |
| area-if | 33.0 | 26.3 | area-if |
| area-if-call | 34.3 | 31.6 | area-if-call |
| area-fork | 31.3 |  | no C++ twin |
| area-fork-call | 33.7 |  | no C++ twin |
| area-branch | 33.0 | 29.1 | area-switch |
| area-branch-call | 34.9 | 32.3 | area-switch-call |
| area-table | 7.2 | 5.1 | area-table |
| area-table-call | 11.1 | 6.3 | area-table-call |
| area-table-x4 | 7.4 | 3.7 | area-table-x4 |
| corner-one | 38.2 | 27.0 | corner-one |
| corner-two | 45.0 | 33.8 | corner-two |
| corner-call | 42.9 | 58.7 | corner-call |
| corner-table | 7.1 | 5.1 | corner-table |

The f32 virtual-call rows are C++ only. Same machine, same flags, same median:

| Kernel | Cycles per shape |
|---|---:|
| f32-vtbl | 38.8 |
| f32-vtbl4 | 35.3 |
| f32-switch | 23.4 |
| f32-switch4 | 20.2 |
| f32-table | 5.1 |
| f32-table4 | 3.3 |
| f32-corner-vtbl | 74.1 |
| f32-corner-switch | 26.2 |
| f32-corner-table | 5.1 |

`SumCornerOne` in `shapes.ailang` still writes the divide after the branch (`1 / (corners + 1)`). Each arm's corner count is a constant, and both compilers fold that divide. The remaining corner-one gap is 38 cycles against 27.

## Binary size

Built from these sources on 6 October 2026. `shapes.x` is the unshaken file, 55,174 bytes, sha256 `025da4ba91b548df7297c62a16f33f139a0787e457ac3b7588bd30e87a40d74b`. It is a static executable with no section headers: 50,450 bytes of code and 1,905 bytes of data. `strip` has nothing to remove. The code section holds the benchmark and the Arena library together.

`shapes_ts.x` is the same source with `-TS`. The compiler kept 82 of 121 functions. The file is 33,454 bytes, sha256 `45c9c6e7670cb4cf6d0ef93ce046624af66019e65b0abaae51aa3c5317ddfadc`: 28,953 bytes of code and 665 bytes of data. That is 21,720 bytes under the unshaken file. It printed the same 48 rows, the same f64 bits, and the same exit 62.

| Binary | On disk | Stripped | How it links |
|---|---:|---:|---|
| `shapes.x` | 55,174 | 55,174 | Static. No libc. Whole Arena library. |
| `shapes_ts.x` | 33,454 | 33,454 | Static. No libc. `-TS`, 82 of 121 functions. |
| `shapes_cpp` | 22,728 | 18,656 | Dynamic PIE. Needs `libc.so.6` (2,125,328 bytes on this machine, shared with everything else). |
| `shapes_cpp_static` | 791,832 | 710,672 | Same g++ flags plus `-static`. libc is inside the file. |

The dynamic C++ file is the smaller file, because `printf` and `malloc` stay in the shared library. Its `.text` is 9,367 bytes. Link C++ the way AILANG always links, one static executable, and the stripped file is 710,672 bytes against 33,454 for the tree-shaken AILANG program.

The 18,656-byte file is not the cost of running `shapes.cpp`. The loader maps `libc.so.6` at start. The static link is that same program with the library in the file.

Both programs also allocate a 32 MB scrub buffer, and that buffer is most of the resident set. One run on this FX-8320, peak resident set from `getrusage`:

| Binary | Peak resident |
|---|---:|
| `shapes_ts.x` | 32,768 KB |
| `shapes.x` | 32,768 KB |
| `shapes_cpp_static` | 33,640 KB |
| `shapes_cpp` | 34,720 KB |

Above the scrub, the static C++ process kept 872 KB more than the tree-shaken AILANG process, in line with its 792 KB file. The dynamic C++ process kept 1,952 KB more. The running cost of the dynamic build is the pages of libc it actually touched, plus the loader and 304 KB of zeroed static data, not the 18 KB file.

Each core here has 16 KB of level-1 data cache. A pair of cores shares 64 KB of level-1 instruction cache. The tree-shaken AILANG code is 28,953 bytes, so the whole code section fits in that instruction cache. The 710 KB static C++ image does not. The inner shape loop is a few instructions in both languages and fits either way. The code that does not fit is the library around the loop: printing a row, allocating the scrub, and reading the clock. That is a size comparison against the cache, not a miss counter.

`run.sh` rebuilds `shapes.x` and `shapes_cpp` here. `shapes_ts.x` is the `-TS` build of the same `shapes.ailang`. Those outputs, the static C++ binary, and the row logs are gitignored.
