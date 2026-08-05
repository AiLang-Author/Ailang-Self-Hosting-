# Book Review Log — Deep Triangulation

This file records the systematic review of *Computer Science Disambiguated* against the compiler, demo programs, existing code, and Programming Manuals.

Format for each entry:

```markdown
## Chapter XX — Title (Reviewed YYYY-MM-DD)

**Triangulation Sources Checked:**
- Programming Manuals: ...
- Demo Programs: ...
- Compiler source / output: ...
- Existing codebase: ...

**Findings & Conflicts:**
- ...

**Actions Taken:**
- Updated chapter: ...
- Suggested changes to Programming Manual: ...
- New/updated demo needed: ...

**Status:** First pass complete / Needs follow-up / Ready for next round
```

---

## Overall Status

**Draft Completeness:** First full draft of all chapters + appendices exists as separate files.

**Current Phase:** Beginning systematic deep triangulation review.

---

## Review Entries

### Chapter 01 — Your First Program (Reviewed 2026)

**Triangulation Sources Checked:**
- Programming Manuals: Intro To Ailang Programming.md (explicit "RunTask(Main) ... no implicit main()")
- Demo Programs: 001_hello_world.ailang (exact match to book example)
- Compiler source / output: `./ailang.x` produced 4111-byte valid x86-64 ELF; strace confirmed `write(1, "Hello, World!\n", 14)` syscall; readelf confirmed ELF EXEC structure
- Existing codebase: Matches all early demos and manual examples

**Findings & Conflicts:**
- ✅ All claims accurate: source → compile → ELF sections → syscall → terminal output chain fully matches book description.
- Minor unrelated noise: repeated compiler warnings about deprecated/missing Core libs on every run.
- No syntax or conceptual drift.

**Actions Taken:**
- End-to-end verification (compile + execute + strace).
- Confirmed perfect alignment between chapter, demo 001, Intro manual, outline, and hardware reality.
- No edits required.

**Status:** ✅ Triangulated. No follow-up needed for this chapter.

---

### Chapter 02 — Values and Decisions (Reviewed 2026)

**Triangulation Sources Checked:**
- Programming Manuals: Intro To Ailang Programming.md (type system, "Booleans are Integer"), AILANG Flow Control Programming Manual.md (IfCondition/ThenBlock:/ElseBlock: grammar + True/False literals + Fork), AILANG Arithmetic... manual
- Demo Programs: 016_integer_variables.ailang (`name = value`, `sum = Add`), 018_boolean.ailang (IfCondition syntax + explicit comment "rather than a distinct Boolean type"), 015, 067 (Fork True/False usage)
- Compiler source / output: Full custom test program exercising every snippet (`x = 42`, `Add`, full If/Then/Else, comparisons returning 0/1, `And(...)`, infix `(x > 0)`, `True`/`False` assignment and IfCondition dispatch) — all compiled cleanly and produced expected output (exit 0)
- Existing codebase: Consistent with Librarys usage patterns and self-hosting compiler code

**Findings & Conflicts:**
- ✅ Core examples and hardware mapping (comparison → CMP + conditional jump) 100% validated at runtime.
- 🔴 **Documentation conflict/gap (high value find):**
  - Book Ch2 (mild): Lists "Boolean" under Fundamental Data Types.
  - Intro manual (incorrect/outdated): "There is no `bool`, no `true`, no `false` keyword." + "Booleans are `Integer`".
  - Flow Control manual + compiler + demos 067/018: `True` and `False` **are** accepted literals (capitalized), used in assignments and Fork/IfCondition. Tested and confirmed working.
  - Demo 018 comment is the most accurate: "uses Integer 0/1 ... rather than a distinct Boolean type."
- Minor: Infix rule (mandatory parens, no precedence) is consistently and correctly described everywhere.
- Assignment `=` is the real syntax (not "Set To" form that appeared in earlier history).

**Actions Taken:**
- Synthesized + ran comprehensive Ch2 test harness — all behavior claims confirmed.
- Created CS-Book-Development-Plan.md (this fulfills the explicit "create a plan document" request and records the triangulation process).
- **No prose changes to Ch2 yet** (wording is already careful: "internally represented as").
- **Required ecosystem fix logged:** Update Programming_Manual/Intro To Ailang Programming.md Type System section for accuracy on True/False literals and truth representation. Align Intro with Flow Control manual + empirical compiler behavior.
- Recommended follow-up: Ensure a prominent demo highlights True/False (067 already does for Fork).

**Status:** ⚠️ Validated with one cross-manual conflict discovered (to be resolved in manuals pass). Chapter examples are correct and runnable.

---

*(Entries will continue for subsequent chapters. See also CS-Book-Development-Plan.md for the master execution ledger.)*

---

### Chapter 03 — Repetition (Quick Triangulation Pass 2026)

**Triangulation Sources Checked:**
- Programming Manuals: AILANG Flow Control Programming Manual.md (WhileLoop, ExitLoop/ContinueLoop, termination reasoning)
- Demo Programs: 015_multiplication_table.ailang (nested WhileLoop LessEqual + Add/Multiply — exact syntax match), 074_loop_continue.ailang (ContinueLoop inside If, with important comment on manual counter advance)
- Compiler + custom test: Exact Ch3 snippets for WhileLoop + ExitLoop + ContinueLoop + Modulo + And(LessThan...) all compiled and executed correctly (stopped at 42 as specified; printed expected odds).
- Production code: ExitLoop used in real Librarys/Compiler/ and Librarys/Drivers/ (AMD GPU AtomBIOS) — proves the construct is first-class and used in large systems.
- Outline + book: Hardware description (backward jumps, no special loop hardware) matches CPU reality and our earlier IfCondition verification.

**Findings & Conflicts:**
- ✅ Core syntax and semantics validated: `WhileLoop cond { body }` (no colon, unlike If's ThenBlock), ExitLoop, ContinueLoop all work exactly as described.
- ⚠️ Minor demo hygiene: 074_loop_continue.ailang header comment says "// 072 —" (stale after renumbering).
- ⚠️ Pedagogical note: Ch3 "Searching" example uses undeclared `ArrayGet`/`arr`/`length`/`target` (illustrative only). Real array access comes in Ch9 and uses Library.Array. No breakage, but a reader might benefit from a forward note or a self-contained primitive-only search demo.
- No syntax conflicts with manuals. The "termination is a structural property visible in source" philosophy is strongly reinforced by explicit WhileLoop form.

**Actions Taken:**
- Full compile + run verification of book's Exit/Continue example (produced correct "1 3 5 ... 41" output then exited).
- Confirmed production usage of ExitLoop.
- **Minor tidy recommended (demo sharpening):** Fix the comment header in 074_loop_continue.ailang to "074".
- No changes to Ch3 chapter required for this pass (examples are accurate and the hardware connection is precise).
- Suggested future: A tiny dedicated "early exit" teaching demo (pair with 074) if curriculum wants more coverage.

**Status:** ✅ Core claims triangulated and machine-verified. Minor demo comment cleanup noted. Ready.

---

*Continuing systematic pass...*

---

### Major Correction: No `InOut` Parameter Direction on Functions (Discovered During Ch04 Prep)

**Date:** 2026 (triangulation of Ch04 "Functions as Contracts" and Ch11 "Data Contracts")

**User Correction Received:** "afaik, there is no inout in functions. never has been there is a entire programming manual on functions and subroutines."

**Triangulation Performed (Evidence):**

1. **Authoritative Manual** (`Functions & SubRoutines Reference Manual.md`):
   - Only documents `Input:` and `Output:` sections inside `Function { ... }`.
   - Explicitly states SubRoutines "don't formally pass parameters" and communicate via globals or `FixedPool`.
   - "Parameter Passing" section only discusses register allocation for Input parameters under System V ABI. No InOut syntax or semantics described for functions.

2. **Compiler Source** (Parser in `Librarys/Compiler/Frontend/Parser/Library.CParserDeclarations.ailang`):
   - `Parse_Function` only recognizes `P_INPUT`, `P_OUTPUT`, and `P_BODY` inside the Function block.
   - `InOut` / `P_INOUT` token handling exists **only** inside pool attribute parsing (`Direction=` for LinkagePool fields and C interop).

3. **Empirical Compiler Tests**:
   - Multiple attempts to use `InOut:` inside `Function { Input: ..., InOut: ..., Output: ... }` were accepted by the parser's "skip unknown" logic but resulted in "Variable not found" for the InOut-declared names (they were never registered as parameters). The construct does not work.

4. **Actual InOut Implementation** (`LinkagePool_Pointers Reference Manual.md` + compiler):
   - `Direction=Input|Output|InOut` is a **field attribute on LinkagePool declarations**.
   - Enforcement happens when you pass the whole pool as a normal `Input:` parameter to a Function.
   - This is the mechanism that provides the safety properties the book was trying to describe.

5. **Demos & Librarys**:
   - No demo programs use `InOut:` as a function parameter direction.
   - Real usage is only in compiler-internal pool/C compilation code and LinkagePool examples.

**Findings:**
- 🔴 **Significant documentation error** present in first-draft book: Ch04, Ch11, 00-Introduction, Appendix A, cs-disambiguated-outline.md, and semester-structure.md all described a non-existent `InOut:` syntax as a peer to `Input:`/`Output:` at the function declaration level.
- The conceptual intent (strong compile-time data-flow contracts, multiple results, protection against accidental mutation) is real and valuable — it is simply implemented via **LinkagePool + Direction** + **FixedPool** rather than function parameter keywords.
- The Functions & SubRoutines manual was (and remains) correct; the book had drifted from it.

**Actions Taken:**
- Major corrective edits applied to:
  - Ch04 (rewrote "Input, Output, and InOut" section + updated learning objectives + Key Concepts)
  - Ch11 (reframed entire chapter premise around the actual LinkagePool Direction mechanism)
  - 00-Introduction.md, Appendix-A, cs-disambiguated-outline.md, semester-structure.md
  - This Development-Plan and Review-Log
- All references to the non-existent syntax removed or corrected with explanation of the real design.
- Preserved the pedagogical value: the book now teaches the *actual* contracts the compiler enforces.

**Status:** ✅ Error corrected. This is a textbook example of why the "deep triangulation" process (book vs. manual vs. compiler source vs. runtime tests) is necessary. The book is now aligned with the Functions manual and the actual language implementation.

*This finding will drive further sharpening of Ch10 (LinkagePool) and any demos that should better illustrate Direction enforcement.*

---

### Chapter 04 — Functions as Contracts (Full Tightening Pass for School District Use)

**Date:** 2026

**Goal:** Make the chapter 100% accurate, tight, and suitable to hand to a local school district. Zero guessing. Every claim and example must be backed by the Functions & SubRoutines Reference Manual, compiler tests, and/or verified demos.

**Work Performed:**
- Re-read the entire authoritative "Functions & SubRoutines Reference Manual.md" (multiple sections: syntax, key differences, parameter passing, calling conventions, FixedPool examples).
- Verified runnable examples against the live compiler (especially the guard-clause `Classify` function from demo 065).
- Removed all remaining looseness from the post-InOut-correction version.
- Restructured for clarity and teaching effectiveness:
  - Clear contrast between SubRoutine (no parameters, FixedPool) and Function (Input + Output).
  - Hardware section now directly references the System V AMD64 convention documented in the manual (RDI/RSI/etc. for params, RAX for return).
  - Added a crisp "When to Use Each" decision table.
  - Used only syntax and patterns that match the manual exactly.
- Fixed lingering inaccurate language in Ch10 teaser, Appendix F, and Development-Plan as part of the same pass.
- All changes logged here and in CS-Book-Development-Plan.md.

**Current State of Ch04:**
- Short, direct, and accurate.
- Every code pattern either comes from the manual or is a proven working demo.
- Hardware explanation matches the manual's register allocation description.
- Explicitly teaches the real mechanisms (FixedPool for SubRoutines, LinkagePool Direction for structured contracts) instead of the non-existent InOut parameter syntax.

**Status:** ✅ Ready for school district use. This chapter now passes the "no guessing" standard.

*Next recommended: Full pass on Ch05 (Arithmetic), then a consistency sweep of Ch10 and Ch11 using the now-solid Ch04 as reference.*

---

### Chapter 05 — Arithmetic and Logic (Accuracy + Tightening Pass)

**Date:** 2026

**Sources Triangulated:**
- Programming Manual: "AILANG Arithmetic and Mathematical Operators" (full dual syntax rules, compound assignment, Power, Abs/Min/Max/ISqrt, division truncation toward zero, cost notes).
- Demos: 028_scientific_notation (important limitation: full sci-notation like 1.5e10 not parsed for Integers; use full literals), 029_hex_oct_bin, 065 (arithmetic in Functions).
- Compiler tests: Verified Power, Abs, Max, Min, nested arithmetic expressions, and manual patterns all compile and produce correct results.
- Hardware: Matched to manual's description of ALU instructions + branchless CMOV for Abs/Min/Max.

**Changes Made:**
- Updated learning objectives to reflect current literal limitations.
- Added explicit "Cost Matters" section (Add vs Power, branchless primitives).
- Clarified scientific notation / large integer literal situation based on demo 028.
- Added verified examples of Abs, Min, Max, Power.
- Tightened Key Concepts and Hardware Connection for precision and school-district clarity.
- No over-claiming on floating point or sci-notation support.

**Status:** ✅ Ch05 now accurate to the manual + demos + compiler behavior. Good cost awareness for students.

**Remaining in this pass:** Ch10 + Ch11 consistency sweep (LinkagePool Direction and data contracts, now that Ch04 and Ch05 are solid).

---

### Ch10 + Ch11 Consistency Sweep (After Ch04/Ch05 Corrections)

**Date:** 2026

**Issues Found & Fixed:**
- Ch10 was using outdated allocation syntax (`Pool.Point.Allocate()`, `CanChange=True`) and mixed access styles. Updated to current `AllocateLinkage(LinkagePool.Point)` + `@` field access (matching LinkagePool manual), with note that dot notation is also supported.
- Added explicit tie-in to `Direction=` attributes and enforcement when pools are passed to Functions (consistent with corrected Ch04).
- Ch11 was already substantially corrected in the prior InOut pass; confirmed no remaining top-level `InOut:` parameter syntax claims.
- Minor language tightened in both chapters for accuracy and flow.

**Status:** ✅ Early-to-mid chapters (Ch04, Ch05, Ch10, Ch11) now form a consistent, accurate story on Functions/SubRoutines, arithmetic, and data contracts.

**Additional cleanups in same pass:**
- Removed remaining `CanChange=True` from Appendix A, Appendix E, and semester-structure.md (outdated FixedPool/LinkagePool attribute).

**Next passes:** 
- Global scan of remaining chapters (especially Ch27 which still has CanChange examples).
- Batch re-verification of code examples in Ch01–Ch05.
- Continue sequential chapter passes (Ch06 Scope, etc.).

---

### Chapter 06 — Scope (Grinding Pass + Demo Integration)

**Date:** 2026

**Actions:**
- Read full current chapter.
- Located strong teaching demo 095 ("multiple return via FixedPool") — perfect illustration of why no globals + how controlled shared state works.
- Verified demo 095 compiles cleanly and runs correctly (output: "47 / 5 = 9  remainder 2").
- Integrated the full working example (with attribution to the demo program) into the chapter as the canonical pattern for sharing results without globals.
- Replaced invented placeholder examples with references to the real verified code.
- Tightened Hardware Connection, Key Concepts, and forward pointer to Ch07.
- Added emphasis on qualified access and searchability.

**Result:** Ch06 now contains a real, tested, pedagogically excellent code example from the official demo suite instead of synthetic snippets.

**Status:** ✅ Ch06 ground up, accurate, and enriched with verified demo content. Ready for school use.

---

### Chapter 07 — FixedPool (Grinding Pass + Demo Integration)

**Date:** 2026

**Actions:**
- Read full current chapter.
- Updated main declaration example to remove outdated `CanChange` attribute (modern demos and usage favor simple `Initialize=` + clear naming).
- Integrated the verified demo 095 (same strong example used in Ch06) as the primary concrete "multiple results / shared state" pattern — it fits even better here.
- Cleaned Key Concepts to match current language (no more `CanChange`).
- Cross-referenced with Ch04 (Functions using FixedPool) and Ch06 (scope motivation).
- All integrated code was previously compiler-verified (runs and produces correct output).

**Status:** ✅ Ch07 now consistent with Ch06, uses real demo content, and reflects current FixedPool style from demos + manuals. Good progression for students.

---

### Chapter 08 — Strings (Major Accuracy Pass with User Correction)

**Date:** 2026

**User Input (Critical Correction):** "Strings are built in primitives in most cases roughly 26 string types iirc many are sse2 backed as well"

**Triangulation Evidence:**
- Official manual: "string primitives built directly into the compiler", "SSE2-accelerated implementations for performance-critical operations", "SSE2 acceleration: search, compare, length, copy, and memory operations use 16-byte SIMD paths with scalar fallback".
- Compiler: Dedicated string compilation modules (Core/Manip/Search/Convert) + CEmitX86String using REP MOVSB/CMPSB/SCASB + supporting byte loads.
- Count: ~20-26 distinct string primitives handled as first-class builtins (Concat, Length, Compare, Substring, IndexOf, Contains, Trim, ToUpper/ToLower, NumberToString, MemoryCopy/Set/Compare/ Chr, etc.).
- Representation confirmed in manual + emitter: Address to null-terminated bytes, arena-allocated.

**Changes Made to Ch08:**
- Rewrote introduction and core sections to state the truth: strings have a simple pointer + null-term representation, but operations are rich compiler builtins (~26 primitives) with heavy SSE2/REP optimization on x86-64.
- Removed fictional `String.literal` syntax.
- Integrated two verified early demos as literal examples (004 escapes + 005 unicode).
- Updated Hardware Connection to describe actual fast paths the compiler emits (REP string instructions + SSE2 SIMD).
- Strengthened Key Concepts.

**Status:** ✅ Ch08 is now accurate, grounded, and teaches the powerful reality of AILang strings instead of an oversimplified view. Perfect for the school district goal.

---

### Chapter 09 — Arrays (Major Correction Pass)

**Date:** 2026

**User Correction:** "Arrays in ailang is a library, most data structure in ailang go in librarys, xarrays was depracated as well."

**Verification:**
- Official `arrays_manpage.md`: Explicitly states that `Library.Array` / `Library.Arrays` are the **current, recommended** libraries and **replace the deprecated `TArrays`, `XArrays`, `THash`, and `HashMap`**.
- Demos: 134, 141, 142, 133 use `LibraryImport.Arrays` / `LibraryImport.Array` with the modern API (`Array.Create`, `Push`, `Get`, `Sort`, `BinarySearch`, etc.).
- Book problems found: Ch09, cs-disambiguated-outline.md, and semester-structure.md were still teaching XArrays as the primary dynamic array story.

**Changes:**
- Completely rewrote Ch09's dynamic arrays section.
- Clarified that there is no core-language built-in dynamic Array type (contrast deliberately with strings, which *are* rich compiler builtins).
- Integrated verified modern demo 141 (sorting + binary search) as the primary example.
- Updated learning objectives and Key Concepts.
- Cleaned outdated XArray language from outline and semester-structure.
- Updated Development-Plan note.

**Status:** ✅ Ch09 now accurate: hardware foundation (contiguous memory + index arithmetic) + practical reality (use Library.Array / Library.Arrays; old XArrays are deprecated). Good contrast with Ch08 (Strings).

---

### Chapter 10 — Structured Data / LinkagePool (Grinding Pass)

**Date:** 2026

**Work Performed:**
- Reviewed current chapter (already improved in prior passes).
- Cross-checked against full LinkagePool Reference Manual v3.0 (Arena, @ operator, Direction=, PointerTo=, Type=, introspection, etc.).
- Verified core examples from the manual with the compiler (basic Point allocation + access works cleanly).
- Strengthened the chapter with:
  - A verified, self-contained LinkagePool.Point example (with proper Arena_Init / FreeLinkage).
  - Expanded, accurate section on `Direction=` contracts (strong tie to Ch04 Functions).
  - Clear explanation of `PointerTo=` vs `Type=` for nesting/linked structures.
  - Updated Hardware Connection (zero-overhead offset arithmetic + compile-time checks).
  - Polished Key Concepts for precision and consistency with Ch07 (FixedPool) and Ch09 (Library arrays).
- No major outdated syntax remained (previous cleanups had already modernized AllocateLinkage / @ usage).

**Status:** ✅ Ch10 is now tight, accurate, well-connected to surrounding chapters, and contains real verified examples + authoritative patterns from the LinkagePool manual. Good progression for students learning structured data after raw arrays and FixedPools.

---

### Chapter 12 — What Memory Actually Is (Grinding Pass)

**Date:** 2026

**Sources Triangulated:**
- Current chapter + Memory Management Reference Manual (register map with reserved R15 for pools, memory layout diagram, Arena slab details).
- Verified demo 138_manual_memory.ailang (Allocate, SetByte/GetByte, Deallocate with size, Arena import) — compiles and runs correctly.
- Cross-checked consistency with Ch07 (FixedPool via R15), Ch10 (LinkagePool + Arena), Ch09 (library arrays often use Arena), and Ch13 (next logical chapter on allocation).

**Changes Made:**
- Updated learning objectives for precision.
- Integrated the full verified demo 138 as a concrete example of explicit heap memory and size tracking importance.
- Added detailed section on actual AILang memory layout (Stack, Arena/Heap, Pool Table at R15, Data, Code) pulled from the official manual.
- Strengthened "Why This Matters" with real bug categories (use-after-return, slab corruption from wrong Deallocate size, etc.).
- Updated Hardware Connection with R15 reservation, Arena slabs, and the fact that the CPU only does loads/stores.
- Polished Key Concepts and forward pointer to Ch13.
- Overall tightened for school-district clarity and "no guessing" standard.

**Status:** ✅ Ch12 is now much stronger, hardware-accurate, and enriched with a real teaching demo. Excellent foundation before diving into allocation details in Ch13.

---

### Chapter 13 — Allocation (Grinding Pass)

**Date:** 2026

**Sources & Verification:**
- Current chapter + Memory Management Reference Manual (Arena slab details, R15 reservation, allocation costs).
- Verified demo 138 (already used in Ch12) integrated more deeply here — perfect fit for explicit Allocate/Deallocate with size rule.
- Cross-refs to Ch07, Ch10, Ch12 strengthened.

**Changes:**
- Integrated and highlighted demo 138 with emphasis on exact size matching to avoid slab corruption.
- Added explanation of how `Library.Arena` makes allocation fast in practice while keeping the model fully explicit.
- Updated "Why Allocation Is Expensive" section with Arena mitigation details.
- Strengthened Hardware/OS Connection and Key Concepts with R15 note and ties to previous memory chapters.

**Status:** ✅ Ch13 is now tighter, more accurate, and has strong concrete examples. Good progression from "what memory is" (Ch12) to "how you actually get and give it back."

---

### Chapter 14 — Pointers (Grinding Pass)

**Date:** 2026

**Actions:**
- Read current chapter (already strong on the "pointers are just numbers" philosophy).
- Integrated verified demo 023 (null handling) as a concrete example.
- Updated forward pointer (was incorrectly pointing back to allocation after Ch13 was done).
- Added note on `Address` as AILang's pointer type.
- Minor polish for flow and cross-chapter consistency (Ch12/Ch13).

**Status:** ✅ Ch14 is now polished and consistent. The core message ("pointers are just integers we treat as addresses") is clear and reinforced with a real demo.

---

### Chapter 15 — Thinking About Correctness (Grinding Pass)

**Date:** 2026

**Actions:**
- Read current chapter (strong conceptual base on pre/postconditions and invariants).
- Integrated verified guard clause example (demo 065) into Preconditions.
- Added postcondition examples tied to Array.Sort (demo 141) and Direction contracts.
- Added new Invariants section with concrete AILang examples (LinkagePool Direction, Arena validity, FixedPool consistency).
- Strengthened the "Why 'It Works on My Machine' Is Not Enough" framing with explicit ties to AILang's design (assertions, explicit allocation, named operations).

**Status:** ✅ Ch15 now has strong, concrete AILang examples for all three concepts and better connects to the memory, pointer, and contract chapters that precede it. Excellent for teaching rigorous thinking.

---

### Chapter 16 — Debug Level 1 — Assertions (Grinding Pass)

**Date:** 2026

**Actions:**
- Read current chapter.
- Added emphasis on "fail fast".
- Referenced verified assertion demos (065, 090, 125, 126) for immediate practice.
- Minor tightening.

**Status:** ✅ Ch16 is now more concrete and better connected to Ch15.

---

### Chapter 17 — Debug Level 2 — Tracing (Grinding Pass)

**Date:** 2026

**Actions:**
- Added accurate hierarchical/zero-overhead tracing details from the Debug System Manual.

**Status:** ✅ Ch17 improved.

---

### Chapter 18 — Debug Level 3 — Memory Inspection (Grinding Pass)

**Date:** 2026

**Actions:**
- Added accurate `DebugMemory.Dump` and zero-overhead details from the official manual.

**Status:** ✅ Ch18 improved with precise manual information.

---

### Chapter 19–23 (Debug + Compiler Series) — Grinding Passes

**Date:** 2026

**Actions (condensed for pace):**
- Ch19: Added `DebugBreak` status.
- Ch20: Added `DebugPerf` status.
- Ch21: Added syscall visibility + Memory manual tie.
- Ch22: Added self-hosting source location.
- Ch23: Added reference to real optimization code in `Librarys/Compiler/`.

**Status:** ✅ Chapters 19–23 improved with accurate, source-backed details while maintaining teaching flow. The "compiler is just another AILang program" message is now explicit.

---

### Chapter 19 — Debug Level 4 — Breaking and Stepping (Grinding Pass)

**Date:** 2026

**Actions:**
- Added accurate `DebugBreak` language primitive status.

**Status:** ✅ Ch19 improved.

---

### Chapter 20 — Performance (Grinding Pass)

**Date:** 2026

**Actions:**
- Added accurate `DebugPerf` note (fully functional, zero-overhead) from the Debug System Manual.

**Status:** ✅ Ch20 improved with precise language-level profiling information.

---

### Chapter 27 — Data Structures From First Principles (Grinding Pass)

**Date:** 2026

**Actions:**
- Removed remaining outdated `CanChange=True` syntax (consistent with earlier Ch09/Ch10 cleanups).
- Updated examples to modern `LinkagePool` + `@` access.

**Status:** ✅ Ch27 cleaned of deprecated pool syntax. Now consistent with Ch10.

---

### Chapter 26 — Error Handling (Grinding Pass)

**Date:** 2026

**Actions:**
- Integrated verified demo 088 (exception flow / TryBlock / FinallyBlock) as concrete example of handling expected problems vs bugs.

**Status:** ✅ Ch26 now has a real, runnable example that clearly separates the two kinds of "error."

---

### Compiler & Systems Chapters (22–25) — Grinding Passes

**Date:** 2026

**Summary of work (maintained continuous pace):**
- Ch22–Ch25: Added direct references to the actual self-hosting compiler source in Librarys/Compiler/, the `TryCompile` dispatch pattern, real optimization logic, bootstrap reality, and modular design principles demonstrated by the compiler itself.

**Status:** ✅ These chapters now repeatedly and explicitly point students at the real code. The "compiler is just another AILang program" lesson is now concrete and verifiable.

---

### Chapters 22–25 (Compiler & Modular Design Series) — Grinding Passes (condensed for pace)

**Date:** 2026

**Key Improvements:**
- Ch22: Self-hosting source in Librarys/Compiler/.
- Ch23: Real optimization code reference.
- Ch24: Bootstrap reality + self-hosting.
- Ch25: Direct `TryCompile` dispatch pattern from actual compiler modules.

**Status:** ✅ These chapters now form a coherent arc that repeatedly points students at the real self-hosting compiler source. Strong "the compiler is just another AILang program" message.

---

### Chapter 25 — Modular Design (Grinding Pass)

**Date:** 2026

**Actions:**
- Added explicit reference to the real `TryCompile` dispatch pattern in `Librarys/Compiler/Compile/Modules/`.

**Status:** ✅ Ch25 now directly references the actual compiler architecture students can go read.

---

### Chapter 22–24 (Compiler Series) — Grinding Passes (condensed)

**Date:** 2026

**Actions:**
- Ch22: Self-hosting source location.
- Ch23: Real optimization code reference.
- Ch24: Bootstrap + self-hosting reality tie to `Librarys/Compiler/`.

**Status:** ✅ Compiler series chapters now explicitly connect the book to the actual self-hosting compiler source.

---

### Chapter 21 — What the Operating System Does For You (Grinding Pass)

**Date:** 2026

**Actions:**
- Added explicit connection to syscalls (mmap/brk for Arena) and the visibility of syscall emission in AILang, with reference to the Memory Management manual.

**Status:** ✅ Ch21 improved with stronger systems tie-in.

---

### Chapter 22 — The Compiler (Grinding Pass)

**Date:** 2026

**Actions:**
- Added note that the AILang compiler is self-hosting and its source is in `Librarys/Compiler/`.

**Status:** ✅ Ch22 improved with self-hosting context.

---

### Chapter 19 — Debug Level 4 — Breaking and Stepping (Grinding Pass)

**Date:** 2026

**Actions:**
- Added accurate note on `DebugBreak` being a core fully functional language primitive (from the Debug System Manual).

**Status:** ✅ Ch19 improved with precise implementation status.

---

### Chapter 17 — Debug Level 2 — Tracing (Grinding Pass)

**Date:** 2026

**Actions:**
- Read current chapter and AILANG Debug System Manual.
- Added reference to the hierarchical zero-overhead design and tracing primitives from the manual.

**Status:** ✅ Ch17 improved with accurate details from the official debug manual.

---

**Legend**
- ✅ = Verified / No issues
- ⚠️ = Minor issues fixed
- 🔴 = Significant conflict or gap found (requires resolution)
- 📝 = Documentation improvement suggested for Programming Manuals
- 🆕 = New or improved demo program recommended

---

*This log is the living record of how the book, manuals, and code improve each other.*