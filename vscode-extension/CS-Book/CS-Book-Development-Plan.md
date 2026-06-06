# CS Book Development Plan — Deep Triangulation & Mutual Sharpening

**Created:** 2026 (per user request: "create a plan document, do each chapter, verify against the compiler, the demo programs, existing code and the programming manuals. think of this as a deep triangulation and anywhere we find conflict we resolve the documentation gaps. this way the book sharpens the manuals the code sharpens the book etc.")

**Primary Document Pair:**
- This plan (execution driver and conflict ledger)
- [Book-Refinement-Plan.md](./Book-Refinement-Plan.md) (detailed per-chapter review process and tracking template — the operational heart of the triangulation)

The two are complementary. This file records the actual execution status, chapter-by-chapter outcomes, and cross-ecosystem fixes applied.

---

## Core Goal (User Directive)

Perform a ground-up, no-magic review of *Computer Science Disambiguated* (the CS-Book chapters) such that:

- Every significant claim, code example, and hardware explanation is **verified** against:
  1. The live AILang compiler (`./ailang.x` + `-d` diagnostics + generated ELF behavior)
  2. The 140+ verified runnable demo programs (001–...)
  3. Production code in Librarys/, Applications/, Main.ailang, self-hosting compiler sources, etc.
  4. The Programming_Manual/*.md files (the technical reference)
- **Conflicts and gaps are resolved explicitly** — not papered over.
- Fixes flow in both directions: book ←→ manuals ←→ demos ←→ (occasionally) compiler observations.
- The result sharpens teaching clarity, removes lingering magic or outdated descriptions, and improves the entire AILang documentation ecosystem.

This is the "round-robin" quality pass after the successful first-draft chapters.

---

## Current Execution Status

**Plan Status:** Execution started. Phase 1 (Ch 01–05) underway.

**Compiler Verified:** `./ailang.x` present and functional (3MB self-hosting ELF). Supports `-d` for diagnostics. Produces correct x86-64 Linux ELFs that run with exit 0. Strace/objdump/readelf usable for hardware grounding.

**Demos:** 001– (at least 146+ in programs/ subdir) all previously verified build+run clean. Teaching index exists.

**Key References for Triangulation:**
- Programming_Manual/ (19+ files): Intro, Flow Control, Functions & SubRoutines, Memory Management, AILANG Arithmetic..., LinkagePool, etc.
- Demo Programs/programs/*.ailang + DEMO_PROGRAMS_TEACHING_INDEX.md + README.md
- Librarys/ (new Array/Hash etc. + deprecated/)
- Library Manuals/*.md (rewritten authoritative ones)
- CS-Book/*.md (the 32 chapters + 6 appendices + outlines)
- Live binaries + strace + disassembly for syscall/instruction claims

---

## Chapter-by-Chapter Triangulation Log (Execution Record)

### Chapter 01 — Your First Program (Triangulated 2026)

**Sources Checked:**
- Compiler: Compiled 001_hello_world.ailang (and book example) → 4111-byte ELF, ran successfully (exit 0).
- strace: Confirmed `write(1, "Hello, World!\n", 14)` syscall exactly as described.
- Demos: Exact match to 001_hello_world.ailang (SubRoutine.Main + PrintMessage + RunTask(Main)).
- Programming Manuals: Intro To Ailang Programming.md explicitly documents `RunTask(Main)` as the entry point with "There is no implicit `main()`." Matches book.
- Outline (cs-disambiguated-outline.md): Intent matches (4KB binary, ELF sections, write syscall path to photons).
- Hardware: readelf confirmed valid x86-64 ELF EXEC.

**Findings & Conflicts:**
- ✅ All core claims accurate.
- Minor ecosystem noise: compiler sometimes emits deprecation warnings related to old Core libs / XArrays — these are historical and unrelated to current recommended Library.Array usage.
- No syntax issues in chapter examples.

**Actions Taken:**
- Verified end-to-end (source → compile → ELF → syscall → output).
- Confirmed Ch1 + demo 001 + manual + outline + real hardware behavior are in perfect alignment.
- No edits required to chapter.

**Status:** ✅ Triangulated. Ready for any future polish pass.

---

### Chapter 02 — Values and Decisions (Triangulated 2026)

**Sources Checked:**
- Compiler + custom test harness (`/tmp/test_ch2.ailang` exercising every example): All constructs compiled and ran correctly (variables with `=`, `Add`, `GreaterThan`/`LessThan`/`EqualTo`, `IfCondition`/`ThenBlock:`/`ElseBlock:`, `And(...)`, infix with parens `(x > 0)`, truthy non-zero Integer).
- Demos: 016_integer_variables.ailang (exact `a = 10`, `sum = Add(a, b)` style), 018_boolean.ailang (IfCondition + ThenBlock: syntax + 0/1 comments), 015_multiplication_table etc.
- Programming Manuals:
  - Intro: "Booleans are `Integer` — 1 is true, 0 is false. There is no `bool`, no `true`, no `false` keyword." (see conflict below)
  - AILANG Flow Control Programming Manual.md: Full IfCondition/ThenBlock:/ElseBlock: grammar + examples. Documents `True`/`False` literals and Fork TrueBlock/FalseBlock.
  - Arithmetic manual (cross-checked for Add/GreaterThan etc.).
- Outline: Ch2 spec uses `x = 42` + IfCondition...ThenBlock: (matches reality and demos).
- Hardware grounding: Comparisons → CMP + conditional JMP (described accurately in book).

**Findings & Conflicts (Major Documentation Gaps Resolved):**

1. **Boolean representation (book vs. manuals internal conflict):**
   - Book Ch2: Lists "`Boolean` — The result of a comparison..." under "Fundamental Data Types" in parallel with Integer/Address.
   - Authoritative reality (compiler + 018 demo comment + Intro manual): No distinct Boolean *type*. Truth is carried in Integer (0=false, non-zero=true). `True`/`False` literals exist and are accepted (tested and confirmed working).
   - Flow Control manual correctly shows `True`/`False` usage and Fork TrueBlock/FalseBlock.
   - **Gap:** Intro manual's claim "no `true`, no `false` keyword" is **outdated/incorrect** (empirically falsified). Inconsistency between Intro and Flow Control manuals.

2. **Infix + parens rule:** Perfectly consistent across book, manual, compiler (mandatory parens, no precedence table). Test `(x > 0)` succeeded.

3. **Assignment syntax:** `name = value` (and `name = Add(...)`) is the documented and working form. No `Set x To` required (earlier history confusion resolved by actual demos + manual + compiler).

**Actions Taken:**
- Created and executed full Ch2 example suite → all claims about behavior verified at runtime.
- **No changes yet to Ch2 prose** (its wording is cautious enough: "internally represented as").
- **Documentation fix required (ecosystem sharpening):**
  - Update Programming_Manual/Intro To Ailang Programming.md (the "Type System" section) to acknowledge `True`/`False` literals and clarify that while the *representation* is Integer, the language provides named literals for clarity (align with Flow Control manual + compiler + demos).
  - Consider adding a small "Truth Values" note in Ch2 or a cross-ref to the corrected Intro.
- Recommended: Add or strengthen a demo that explicitly shows `True`/`False` vs raw 0/1 if not already prominent (067_fork already uses them for Fork).

**Status:** ⚠️ Minor wording tightening recommended in Ch2 for precision; **major doc conflict found and documented for fix in Intro manual**. Ch2 examples 100% validated.

---

## Phase Execution Plan (from Book-Refinement-Plan + user directive)

(See Book-Refinement-Plan.md for the full detailed checklist and per-chapter template.)

**Phase 1 (Current):** Ch 01–05 + front matter (high leverage foundations)
- [x] Ch01
- [x] Ch02 (with conflict discovery)
- [ ] Ch03 Repetition (WhileLoop, ExitLoop/ContinueLoop, labeled?)
- [x] Ch04 Functions as Contracts — fully corrected and tightened (see Review-Log for details on the InOut correction and verification)
- [ ] Ch05 Arithmetic and Logic (named ops, scientific notation, all operators)

**Phase 2:** Ch 06–14 (Scope, FixedPool deep, Strings, Arrays, LinkagePool, Memory, Allocation, Pointers)

**Phase 3:** Ch 15–28 (Correctness, Debug levels 1-4, Perf, OS, Compiler, Optimizer, Self-Hosting, Modular, Error Handling, Data Structures, Concurrency)

**Phase 4:** Ch 29–32 (Calculator, Text Editor, Database, Contributing) + full appendices A–F (these are reference and need strict manual alignment)

**Cross-cutting:**
- After every 3–5 chapters: batch update to Review-Log + any manual/demo fixes.
- Maintain runnable status of all demos.
- At end: full consistency pass on TOC, cross-refs, primer links (how-computers-compute.md), and a "Gaps Closed" summary document.

---

## How to Perform a Chapter Review (Operational Checklist)

1. Read chapter + corresponding outline section(s) + relevant Programming_Manual files.
2. Extract every code snippet + every hardware/ semantics claim.
3. Reproduce in a minimal test_XX.ailang (or reuse/extend existing demo).
4. `./ailang.x test.ailang /tmp/out.x` + execute + strace/objdump as needed.
5. Grep manuals + demos + Librarys sources for matching terminology and examples.
6. Log conflicts with exact quotes + file:line.
7. Propose + apply minimal precise fixes (book first, then manuals/demos if they were the inaccurate source).
8. Append structured entry to Review-Log.md.
9. Update this Development-Plan status.

**Tools of the Trade:**
- `-d` flag + inspection of any generated combine_source.ailang (or project-root combined_source.ailang)
- `strace -e trace=write,openat,mmap,...`
- `objdump -d -M intel`, `readelf -a`
- `grep -rn` across Programming_Manual + Demo Programs + Librarys
- Custom one-off .ailang test files in /tmp (never pollute source tree)
- Existing verify_all_demos.py / run_all_demos.py when batch checking

---

## Success Criteria (Unchanged)

- 100% of pedagogical examples in the book either (a) are directly runnable demos or (b) compile+run cleanly when extracted.
- Every hardware claim backed by observable behavior (syscall, instruction, memory layout, etc.).
- No unresolved contradictions between book / any Programming_Manual / actual compiler output / demo behavior.
- All fixes create a tighter, more accurate, more teachable AILang ecosystem.

---

## Immediate Next Steps (as of this writing)

1. Complete Ch03 (Repetition) — extract WhileLoop/Exit/Continue examples, test labeled forms if any, cross-ref Flow Control manual + relevant demos (e.g. 076?).
2. Ch04 — Functions/SubRoutines (Input:/Output: only on Functions; FixedPool for SubRoutines; LinkagePool Direction= for structured in/out contracts). Correction applied during triangulation — InOut never existed as a function parameter direction.
3. Continue through Phase 1.
4. After Phase 1: batch-fix any manual inaccuracies discovered (esp. the True/False + Boolean representation in Intro).
5. Keep this plan + Review-Log.md in sync after each chapter or logical batch.
6. When all chapters done: produce a "Triangulation Outcomes & Ecosystem Improvements" summary (what the book taught us about the manuals and vice versa).

---

**This document exists because the user asked for a deliberate, auditable, mutual-sharpening process rather than a one-way polish pass.**

**Current Phase:** Executing — multiple passes in progress.

**Completed in recent passes:**
- Ch04: Major correction + full tightening (InOut removed, aligned to Functions manual).
- Ch05: Accuracy pass (cost awareness, literal limitations from demo 028, verified primitives).
- Ch10 + Ch11: Consistency sweep (updated LinkagePool syntax and cross-refs to corrected contract model).
- Ch06: Grinding pass — integrated verified demo 095 (FixedPool multi-result pattern) as the primary concrete example.
- Ch07: Grinding pass — removed outdated CanChange syntax, integrated the same verified demo 095 as the central teaching example, cross-refs to Ch04/Ch06 improved.
- Ch08: Major accuracy pass driven by direct user correction. Strings are compiler builtins (~26 primitives, many SSE2-backed). Integrated real demos 004/005. Manual + compiler evidence confirmed.
- Ch09: Major correction pass. Arrays and most data structures are library (`Library.Array` / `Library.Arrays`), not core builtins. XArrays and old T* systems are deprecated. Integrated verified demo 141. Cleaned references across outline and semester materials.
- Ch10: Grinding pass. Strengthened with verified LinkagePool examples from the reference manual, expanded Direction= contracts section (ties to Ch04), PointerTo= vs Type= explanation, and precise hardware connection. Chapter is now consistent with Ch07 and Ch09.
- Ch12: Grinding pass. Integrated verified demo 138 (manual Allocate/Deallocate), added accurate memory layout from the Memory Management manual (R15 pool table, Arena slabs), strengthened hardware and "why it matters" sections. Good consistency with Ch07/Ch09/Ch10.
- Ch13: Grinding pass. Deepened integration of demo 138 with size-matching warning, added Arena slab performance explanation from the manual, improved cross-refs and Key Concepts. Chapter now flows cleanly from Ch12.
- Ch14: Grinding pass. Integrated verified null demo (023), cleaned forward pointer, minor polish for consistency with Ch12/Ch13.
- Ch15: Grinding pass. Integrated guard clauses (065), postcondition examples (141 + Direction), new Invariants section with AILang-specific cases. Stronger connections to prior chapters.
- Ch16: Grinding pass. Added fail-fast emphasis and direct links to verified assertion demos (065/090/125/126). Better bridge from thinking to doing.
- Ch17: Grinding pass. Added accurate hierarchical/zero-overhead tracing details from the Debug System Manual.
- Ch18: Grinding pass. Added precise `DebugMemory.Dump` and zero-overhead information from the official Debug System Manual.
- Ch19: Grinding pass. Added accurate `DebugBreak` language primitive status from the Debug System Manual.
- Ch20: Grinding pass. Added accurate `DebugPerf` (fully functional, zero-overhead) information from the Debug System Manual.
- Ch21: Grinding pass. Added explicit syscall visibility (mmap/brk for Arena) and reference to the Memory Management manual.
- Ch22: Grinding pass. Added self-hosting context (source in Librarys/Compiler/).

All changes verified against manuals + compiler where possible.

**Major Finding During Ch04 Preparation (2026):**
User directly corrected: "there is no inout in functions. never has been". Full triangulation confirmed this 100%.
- Functions manual + parser source + compiler tests + LinkagePool manual all prove: no `InOut:` (or equivalent) as a top-level section inside `Function { }` or `SubRoutine { }`.
- The feature the book described did not exist. The real mechanism is `Direction=InOut` (etc.) on **LinkagePool fields** + `FixedPool` for SubRoutines.
- Extensive corrections applied to Ch04, Ch11, Introduction, Appendix A, outline, semester-structure, and this plan.
- Logged in detail in Review-Log.md with primary evidence (parser code, manual quotes, failed compile tests).
This is the strongest validation yet of the "deep triangulation" approach the user requested.

**Key Wins So Far:**
- Created CS-Book-Development-Plan.md (direct response to "create a plan document").
- Full verification of Ch01 (hello + syscall reality via strace).
- Ch02: discovered + logged real conflict between Intro manual ("no true/false keyword") vs. Flow Control manual + compiler + demos (True/False work; truth is Integer 0/1 with literal sugar).
- Ch03: WhileLoop/ExitLoop/ContinueLoop syntax + semantics + hardware (jumps) fully validated against 015/074 demos + production Librarys code + custom compiler test. Tiny demo comment drift fixed as part of mutual sharpening.
- All tested examples from these chapters compile with ./ailang.x and run to exit 0 with correct behavior.

**Triangulation artifacts created/updated this session:**
- CS-Book-Development-Plan.md (this file)
- Review-Log.md (detailed entries for Ch 01/02/03 + conflict ledger)
- Minor source hygiene: Demo 074 header comment corrected (072 → 074)

**Next immediate:** Ch04 (Functions as Contracts) — SubRoutine vs Function, Input:/Output: only, FixedPool communication for SubRoutines, LinkagePool Direction= as the real mechanism for fine-grained contracts. (Major correction made during this session: the book previously described a non-existent `InOut:` peer to Input/Output on function declarations.)

*All changes follow the "book sharpens manuals, code sharpens book" principle.*
