# C and C++ versus AILANG

Same shape-area program, two languages. `shapes.ailang` and `shapes.cpp` in this directory are the sources. `run.sh` rebuilds both, pins one core, and checks that paired results carry the same f64 bits. `shapes-fixedpool.ailang` and `shapes-linkage.ailang` are the same kernels with the clock and the records stored differently. The case studies at the bottom time those two files against `shapes.ailang`.

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

## Where the footprint starts to matter

Arena's slab chunk is `ArenaConst.CHUNK_SIZE`, 4 MB unless a program changes it. `shapes.ailang` does not. The hot loop never reads that slab. The 4,096 records are 98,304 bytes inside the 256 KB fixed-pool mapping, and the 32 MB scrub is a separate mapping taken after the hot runs.

A one-core sweep lowered the slab from 4 MB to 4 KB. Each step mapped exactly the requested size. One pass left the 4 MB slab untouched. The other passes stored through every cache line of the slab before timing, so the memory was resident. At N = 4096 and 200 repetitions, `loop-fadd` stayed between 5.4 and 6.8 cycles per shape, `area-branch` between 32 and 36, and `corner-one` between 38 and 41. The 4 KB slab and the 4 MB slab are the same result inside the noise of a single run. Lowering Arena's slab does not find a performance knee for this benchmark. Four megabytes also still fits beside the record table in the 8 MB level-3 cache, and 200 repetitions hide a cold first pass.

The curve that does move is the record stream itself. Total visits were held near 819,200, so a shorter table is repeated more often. Cycles per shape, one run:

| Records | Bytes | loop-fadd | area-branch | corner-one |
|---:|---:|---:|---:|---:|
| 64 | 1,536 | 6.0 | 17.1 | 19.9 |
| 256 | 6,144 | 5.1 | 26.1 | 28.7 |
| 512 | 12,288 | 5.2 | 30.0 | 36.0 |
| 768 | 18,432 | 5.4 | 30.5 | 35.9 |
| 4,096 | 98,304 | 6.3 | 34.0 | 37.4 |
| 8,192 | 196,608 | 5.9 | 34.2 | 38.5 |

`loop-fadd` has no per-record branch, and it stays near 5 to 6 cycles from 1.5 KB through 192 KB. That range crosses the 16 KB level-1 data cache and stays inside the 2 MB level-2 cache. `area-branch` and `corner-one` climb from about 17 and 20 cycles up to about 30 and 36 by 12 KB of records, then sit on that plateau through the published 4,096-record run. The same split showed up on a second run of the short tables. The branch kernels are the ones that get cheaper as the stream gets shorter. The published hot row is already on the plateau, not on the steep part. This is the cycle curve, not a miss counter.

## Case study: allocating the clock was the wrong tool

`shapes.ailang` calls `Allocate(16)` for the clock and `Allocate` of 32 MB for the scrub. `Allocate` is Arena, so the program imports `Library.Arena.ailang`, 2,128 lines. The 16-byte clock comes out of the 24-byte slab, and the first use of that slab maps a 4 MB chunk. The scrub is past every slab class, so Arena maps 32 MB directly anyway. The hot loops never call `Allocate`.

`shapes-fixedpool.ailang` drops the import. The clock is two words in the pool the shape table already required:

```ailang
FixedPool.Clock {
    "sec": Initialize=0, CanChange=True
    "nsec": Initialize=0, CanChange=True
}
```

`CanChange` records that those words are writable. The compiler stores the flag and does not emit different instructions for it. Without Arena the pool has 22 named slots. The clock is bytes 160..175. The records start at byte 176. The scrub is still a 32 MB wipe, done with one `mmap` of that size, because that is a buffer used once and it does not fit in the 256 KB pool.

Three pinned runs, same core, hot N = 4096. Every f64 bit matched the Arena build, including corner `4724367508723648189`. Median cycles per shape:

| Kernel | With Arena | Fixed pool |
|---|---:|---:|
| loop-int | 4.2 | 3.7 |
| loop-fadd | 5.7 | 5.7 |
| loop-fmul | 5.9 | 5.1 |
| area-branch | 34.4 | 34.4 |
| area-table | 7.7 | 7.9 |
| corner-one | 39.1 | 39.4 |
| corner-two | 46.5 | 44.0 |
| corner-call | 45.2 | 44.8 |

`loop-fmul` was 5.9, 6.1, 5.9 with Arena and 5.1 on every fixed-pool run. `corner-one` overlapped. The branch plateau did not move. The multiply loop's source is the same function. What changed around it is the program: the record base moved from byte 1112 to byte 176, and the code section shrank from 50,450 bytes to 16,585.

| Binary | Bytes | Code | What it contains |
|---|---:|---:|---|
| `shapes.x` | 55,174 | 50,450 | Benchmark plus the whole Arena library |
| `shapes_ts.x` | 33,454 | 28,953 | Same source, `-TS`, 82 of 121 functions |
| `shapes_fixedpool.x` | 20,731 | 16,585 | No Arena. 38 declarations, 3,230 nodes |

`-TS` on the fixed-pool source keeps 33 of 33 functions. The file is byte-identical to the unshaken one, sha256 `30b49c0c76e896a9830f5caa26bebb0151adc3b0c93efb1168f5258ca8b6be9e`. There is nothing left to shake out.

A general allocator is the wrong tool when the size and the lifetime are already known. Two pool slots hold a clock that lives as long as the process. One direct map holds a 32 MB wipe that is used once. The slab's 4 MB chunk, and the 2,128 lines that come with it, were not part of the shape loop.

## Case study: a LinkagePool pointer per record

`shapes-linkage.ailang` is 1,053 lines. The source spells a record as a pointer and a field name. The installed compiler lowers that spelling, on the hot path, to the same load the raw file writes by hand as `Dereference(Add(cursor, offset))`.

### The pattern

Declare the three words. Each field is 8 bytes, in the same order as the raw record:

```ailang
LinkagePool.Shape {
    "kind": Initialize=0
    "w": Initialize=0
    "h": Initialize=0
}
```

Stamp one pointer above the timed loop. `AllocateLinkage(LinkagePool.Shape)` calls `Arena_Alloc` with the pool size, 24 bytes, and that assignment is what marks the name as this pool. A later assignment leaves the mark in place, so the inner loop can copy a new address into the same name and still use `@`. Copy the cursor, then read the fields by name, then step 24 bytes:

```ailang
rec = AllocateLinkage(LinkagePool.Shape)
WhileLoop LessThan(rep, reps) {
    cursor = base
    WhileLoop LessThan(cursor, limit) {
        rec = cursor
        typ = rec@kind
        w = rec@w
        h = rec@h
        cursor = Add(cursor, 24)
    }
}
```

`SumFadd` in the file is that loop with only the width: `rec = cursor`, `w = rec@w`, `psum = Float_Add(psum, w)`, `cursor = Add(cursor, 24)`. The allocation sits above the repetition loop. The inner loop does not allocate. `LibraryImport.Arena` stays, because `AllocateLinkage` is an Arena allocation.

`@` is legal only on a name that already carries the pool mark. `cursor@w`, with `cursor` never assigned from `AllocateLinkage`, is a compile error: the variable is not a LinkagePool pointer. The fix in the hot loops is the copy above, `rec = cursor`, into a name that was stamped once. Writing `cursor = AllocateLinkage(...)` and then `cursor = base` also works, because the mark survives the second assignment. The first binary that compiled `cursor@kind` without that copy read a stale stack slot, still holding the first pointer, and `loop-int` printed 2457600: one type-3 record, counted 4,096 × 200 times.

`Fill` uses the same names, one allocation per record, outside the timed kernels:

```ailang
rec = AllocateLinkage(LinkagePool.Shape)
rec@kind = typ
rec@w = Float_FromInt(wint)
rec@h = Float_FromInt(hint)
```

Those 4,096 blocks come from the 24-byte slab, which bumps by 24. They land in one contiguous run, so `cursor = Add(cursor, 24)` still steps from one record to the next. The paired f64 bits are the check that the step landed on the same words as the raw table. The eight coefficients stay in the fixed pool. `CoeffAddr` is still `mov rax, r15; add rax, 1048`.

The clock is the same construct, two words instead of three:

```ailang
LinkagePool.Clock {
    "sec": Initialize=0
    "nsec": Initialize=0
}
clock = AllocateLinkage(LinkagePool.Clock)
```

`Stamp` still reads those two words with `Dereference`. The syscall writes the bytes, and the parameter it receives is a bare integer.

### What the compiler does with it

On the compiler that first timed this file, `rec@w` reloaded the pointer from the variable's stack slot, tested it for zero, and then loaded `[pointer + offset]`. A zero pointer yields 0. The hot loops already keep the cursor in a register. That register was invisible to the field load, so each record stored the cursor into the typed local first. That store stays in the source. On the folded path it is extra. On every other pointer it is the address the field load reads.

The installed compiler treats a field whose base is the homed loop cursor, or a local this loop assigned straight from that cursor (`rec = cursor`, or `rec = Add(cursor, imm)` with a nonnegative immediate), as one load from that register plus the field displacement. `w = rec@w` stays the qword at that address, the same way `w = Dereference(Add(cursor, 8))` already did. A store through the same base writes `[r13 + disp]`. Every other pointer still reloads from its stack slot and still null-tests. A null still yields 0. Nested records and a `PointerTo` field stay on that slower path, so their pool type is still recorded.

The numbers below are that source: `rec = cursor` on every record, timed twice, once on the compiler that reloaded the pointer and once on the compiler that folds it.

### Before the fold

Three pinned runs, same core, hot N = 4096. Every f64 bit matched `shapes.x` on all 48 rows, including corner `4724367508723648189` and `area-table-x4` `4726534476088133271`. Both programs exited 62. Median cycles per shape, `nanoseconds * 3.7 / 819200`:

| Kernel | Raw offset | LinkagePool |
|---|---:|---:|
| loop-int | 4.1 | 9.3 |
| loop-fadd | 5.8 | 8.2 |
| loop-fmul | 6.0 | 15.3 |
| area-if | 33.7 | 42.4 |
| area-if-call | 34.2 | 42.1 |
| area-fork | 33.5 | 41.2 |
| area-fork-call | 33.9 | 42.7 |
| area-branch | 34.6 | 43.5 |
| area-branch-call | 34.8 | 43.3 |
| area-table | 7.6 | 27.3 |
| area-table-call | 11.1 | 32.3 |
| area-table-x4 | 7.3 | 28.1 |
| corner-one | 39.4 | 45.9 |
| corner-two | 45.7 | 50.9 |
| corner-call | 44.3 | 51.0 |
| corner-table | 7.5 | 26.5 |

`area-table-x4` on that linkage binary was 26.7, 28.1, and 32.5, so the median is 28.1. The branch rows sat inside half a cycle of their median. The table rows moved the most. Each field load on that compiler was a stack reload of a pointer the cursor register already held, a null test that never fired, and then the indirect load.

### After the fold

Three pinned runs of the installed compiler, same core, hot N = 4096, paired with `shapes.x` in the same window. Every f64 bit matched on all 48 rows, including corner `4724367508723648189` and `area-table-x4` `4726534476088133271`. Both programs exited 62. Median cycles per shape, `nanoseconds * 3.7 / 819200`:

| Kernel | Raw offset | LinkagePool |
|---|---:|---:|
| loop-int | 4.2 | 4.2 |
| loop-fadd | 5.7 | 5.7 |
| loop-fmul | 6.2 | 5.3 |
| area-if | 33.5 | 35.0 |
| area-if-call | 34.8 | 34.7 |
| area-fork | 32.3 | 34.4 |
| area-fork-call | 34.2 | 35.6 |
| area-branch | 34.8 | 37.0 |
| area-branch-call | 35.1 | 35.6 |
| area-table | 7.5 | 9.1 |
| area-table-call | 11.5 | 11.5 |
| area-table-x4 | 7.3 | 8.1 |
| corner-one | 40.4 | 40.1 |
| corner-two | 46.1 | 47.9 |
| corner-call | 45.2 | 45.5 |
| corner-table | 7.3 | 8.9 |

`loop-fmul` on the linkage binary was 5.2, 5.3, and 5.3. The raw multiply in this window was 6.2 at the median. `area-table` was 8.3, 9.1, and 9.8. `area-branch` was 37.0, 35.6, and 37.4. The table rows sit within about two cycles of the raw loads. The branch rows sit within about two cycles of theirs. `loop-int` matches the raw loop.

| Binary | Bytes | Code | What it contains |
|---|---:|---:|---|
| `shapes.x` | 55,174 | 50,450 | Records in the fixed pool. Arena for the clock and the scrub. |
| `shapes_linkage.x` | 55,174 | 51,709 | Folded field loads. One `AllocateLinkage` per record. Whole Arena library. 143 declarations. |
| `shapes_fixedpool.x` | 20,731 | 16,585 | No Arena. Records and clock are pool slots. |

`shapes_linkage.x` sha256 is `1dd71ae60d274a894e066693847844dbf7cf9966e1d30223d3ec1de346464dd4`. The file before the fold was 59,270 bytes, code 53,529, sha256 `95a0cd84920fd9f1af1158b27b4976dc0b56d7ff59734e030ce6844e7c705100`. A `-TS` linkage binary from that earlier compiler was 33,454 bytes, code 32,032, sha256 `8de996dfdc23fb816329dfd9bc8a944a2358b106f05d569144e3ac31808a6a4f`, and it was not rebuilt for the fold.

The field names are the spelling a person reads. Allocating the records still brings the Arena library back, and the fixed-pool file remains the small one. The hot loop no longer pays a pointer reload for each field.
