# AILang Demo Programs — Teaching Index & Curriculum

**These 130+ programs are the official progressive teaching examples for AILang.**

They start at absolute zero (`hello world`) and advance through types, operators, control flow (including AILang's unique `Fork`/`Branch` constructs), loops, functions, recursion, error handling, classic algorithms, and advanced language idioms.

They are designed as **programming teaching aids** — short, focused, self-contained, and cumulatively building knowledge of both general programming concepts and AILang's distinctive explicit style.

---

## How to Compile and Run a Demo

The self-hosting AILang compiler is the binary `ailang.x` (or `Main.x` / `ailang_new.x` in some trees).

**Standard invocation (as used in this project):**

```bash
./ailang.x path/to/source.ailang  path/to/output.x
```

Example:

```bash
./ailang.x "Demo Programs/programs/001_hello_world.ailang"  /tmp/hello.x
/tmp/hello.x
```

Alternative form seen in build scripts and notes (some versions support `-o`):

```bash
./ailang.x TestCode/some_test.ailang -o /tmp/some_test.x
/tmp/some_test.x
```

After building, the `.x` file is a native Linux x86-64 ELF executable. Run it directly.

**Tip:** Many demos produce output to stdout. Some demonstrate stderr, environment variables, command-line args, etc.

---

## Current State of the Collection (as of 2026)

- **Total files:** 132 `.ailang` files in `Demo Programs/programs/`
- **Numbering:** Mostly sequential with intentional gaps (e.g. 034, 079, 107–113, 120, 126–270, etc.). Later topics jump to the 27x and 43x ranges.
- **Duplicates / siblings:** 062 appears twice (branch vs switch variants).
- **Unnumbered advanced companions:**
  - `fork_not_switch.ailang`
  - `fork_branch_combinatorial.ailang` (large, 10k+ lines — the "aha!" combinatorial example)
- These are **not** random examples. They form a deliberate curriculum covering every major language feature in teaching order.

**The two high-numbered "fork" files are deliberate off-list companions** to the 062 control-flow lessons. They demonstrate why AILang has both `Fork` (binary "is this true?") and `Branch` (multi-way "which value?") instead of a single overloaded `switch`/`if`.

---

## Recommended Teaching Curriculum (Clean Numbering Proposal)

Below is a **suggested clean, gap-free renumbering** for a polished "v1 Teaching Set". 

Current numbers are preserved in the table for reference. If you approve, we can physically rename the files (and update the two `fork_*` internal comments that reference 062 numbers).

### 1. Getting Started — Hello & Basic Output (001–015)

| New # | Current Filename                    | Topic                              | Notes                  |
|-------|-------------------------------------|------------------------------------|------------------------|
| 001   | 001_hello_world.ailang             | Hello World                        | Core                   |
| 002   | 002_hello_styles.ailang            | Styled / multiple output styles    | Core                   |
| 003   | 003_multiple_lines.ailang          | Multiple lines & basic formatting  | Core                   |
| 004   | 004_escape_sequences.ailang        | Escape sequences                   | Core                   |
| 005   | 005_unicode.ailang                 | Unicode support                    | Core                   |
| 006   | 006_padded_output.ailang           | Padded / formatted output          | Core                   |
| 007   | 007_stderr.ailang                  | Writing to stderr                  | Core                   |
| 008   | 008_no_newline.ailang              | Output without trailing newline    | Core                   |
| 009   | 009_ansi_color.ailang              | ANSI colors & terminal control     | Core                   |
| 010   | 010_date_and_time.ailang           | Date/time basics                   | Core                   |
| 011   | 011_env_variables.ailang           | Environment variables              | Core                   |
| 012   | 012_command_line_args.ailang       | Command-line arguments             | Core                   |
| 013   | 013_name_version.ailang            | Program name & version             | Core                   |
| 014   | 014_banner.ailang                  | ASCII art banner                   | Fun / teaching         |
| 015   | 015_multiplication_table.ailang    | Simple table generation (first "real" program) | Core |

### 2. Variables, Types, Literals & Conversions (016–040)

| New # | Current Filename                    | Topic                                      | Notes |
|-------|-------------------------------------|--------------------------------------------|-------|
| 016   | 016_integer_variables.ailang       | Integer variables                          | Core |
| 017   | 017_floating_point.ailang          | Floating point                             | Core |
| 018   | 018_boolean.ailang                 | Booleans                                   | Core |
| 019   | 019_character.ailang               | Characters                                 | Core |
| 020   | 020_string_variables.ailang        | Strings                                    | Core |
| 021   | 021_constants.ailang               | Constants                                  | Core |
| 022   | 022_type_inference.ailang          | Type inference                             | Core |
| 023   | 023_null.ailang                    | Null / nil                                 | Core |
| 024   | 024_multiple_assignment.ailang     | Multiple assignment                        | Core |
| 025   | 025_swap_variables.ailang          | Swap variables (classic exercise)          | Core |
| 026   | 026_int_overflow.ailang            | Integer overflow behavior                  | Important |
| 027   | 027_float_precision.ailang         | Floating point precision                   | Important |
| 028   | 028_scientific_notation.ailang     | Scientific notation                        | Core |
| 029   | 029_hex_oct_bin_literals.ailang    | Hex / Octal / Binary literals              | Core |
| 030   | 030_signed_unsigned.ailang         | Signed vs unsigned (where relevant)        | Core |
| 031   | 031_long_big_integers.ailang       | Big / long integers                        | Core |
| 032   | 032_complex_numbers.ailang         | Complex numbers                            | Core |
| 033   | 033_byte_values.ailang             | Byte values / low-level bytes              | Core |
| 034   | *(gap — available)*                | —                                          | — |
| 035   | 035_type_aliases.ailang            | Type aliases                               | Core |
| 036   | 036_string_interpolation.ailang    | String interpolation                       | Core |
| 037   | 037_multiline_strings.ailang       | Multiline strings                          | Core |
| 038   | 038_raw_strings.ailang             | Raw strings                                | Core |
| 039   | 039_string_to_number.ailang        | String → number conversion                 | Core |
| 040   | 040_number_to_string.ailang        | Number → string conversion                 | Core |

### 3. Operators & Expressions (041–060)

| New # | Current Filename                    | Topic                              | Notes |
|-------|-------------------------------------|------------------------------------|-------|
| 041   | 041_arithmetic_operators.ailang    | Arithmetic operators               | Core |
| 042   | 042_integer_division.ailang        | Integer division & remainder       | Core |
| 043   | 043_exponentiation.ailang          | Exponentiation (`^`)               | Core (note: `^` is power, not XOR) |
| 044   | 044_bitwise.ailang                 | Bitwise operations                 | Core |
| 045   | 045_bit_shift.ailang               | Bit shifts                         | Core |
| 046   | 046_logical.ailang                 | Logical operators                  | Core |
| 047   | 047_comparison.ailang              | Comparison operators               | Core |
| 048   | 048_ternary.ailang                 | Ternary / conditional expression   | Core |
| 049   | 049_compound_assignment.ailang     | Compound assignment (`+=` etc.)    | Core |
| 050   | 050_increment_decrement.ailang     | Increment / decrement (explicit)   | Core |
| 051   | 051_spaceship.ailang               | Spaceship / three-way comparison   | Core |
| 052   | 052_null_coalescing.ailang         | Null coalescing                    | Core |
| 053   | 053_safe_navigation.ailang         | Safe navigation (`?.`)             | Core |
| 054   | 054_walrus.ailang                  | Walrus operator (`:=`)             | Core |
| 055   | 055_precedence.ailang              | Operator precedence (or lack thereof — explicit parens) | Important |
| 056   | 056_operator_overloading.ailang    | Operator overloading (or explicit named forms) | Core |
| 057   | 057_string_concat.ailang           | String concatenation               | Core |
| 058   | 058_membership.ailang              | Membership / `in` tests            | Core |
| 059   | 059_identity.ailang                | Identity (`is`)                    | Core |
| 060   | 060_spread.ailang                  | Spread / splat                     | Core |

### 4. Control Flow — If, Branch, Fork, Pattern Matching (061–066 + Advanced Companions)

| New # | Current Filename                          | Topic                                              | Notes |
|-------|-------------------------------------------|----------------------------------------------------|-------|
| 061   | 061_if_elif_else.ailang                  | Classic if / elif / else                           | Core |
| 062a  | 062_branch_not_switch.ailang             | `Branch` — AILang's multi-way dispatch (not switch) | Core language feature |
| 062b  | 062_switch_case.ailang                   | Switch-like usage of Branch                        | Core |
| 063   | 063_switch_fallthrough.ailang            | Fallthrough behavior (or explicit)                 | Core |
| 064   | 064_pattern_matching.ailang              | Pattern matching                                   | Core |
| 065   | 065_guard_clauses.ailang                 | Guard clauses                                      | Core |
| 066   | 066_nested_if.ailang                     | Nested ifs (and when to use Fork/Branch instead)   | Core |
| —     | fork_not_switch.ailang (advanced)        | `Fork` — the binary "IS THIS TRUE?" construct     | **Highly recommended** companion |
| —     | fork_branch_combinatorial.ailang (advanced) | Real-world combinatorial Fork + Branch decision tree (combat resolver) | **Excellent teaching capstone** for control flow |

### 5. Loops & Iteration (067–090)

| New # | Current Filename                    | Topic                                      | Notes |
|-------|-------------------------------------|--------------------------------------------|-------|
| 067   | 067_for_loop_index.ailang          | Classic indexed for loop                   | Core |
| 068   | 068_for_each.ailang                | For-each / iterator style                  | Core |
| 069   | 069_while_loop.ailang              | While loop                                 | Core |
| 070   | 070_repeat_until.ailang            | Repeat-until / do-while                    | Core |
| 071   | 071_loop_break.ailang              | Break                                      | Core |
| 072   | 072_loop_continue.ailang           | Continue                                   | Core |
| 073   | 073_return_in_loop.ailang          | Return from inside loop                    | Core |
| 074   | 074_labeled_break.ailang           | Labeled break                              | Core |
| 075   | 075_infinite_loop.ailang           | Infinite loop (`loop {}`)                  | Core |
| 076   | 076_nested_loops.ailang            | Nested loops                               | Core |
| 077   | 077_nested_break.ailang            | Breaking out of nested loops               | Core |
| 078   | 078_loop_string_chars.ailang       | Looping over string characters             | Core |
| 079   | *(gap)*                            | —                                          | — |
| 080   | 080_loop_over_map.ailang           | Looping over maps / collections            | Core |
| 081   | 081_reverse_loop.ailang            | Reverse iteration                          | Core |
| 082   | 082_step_loop.ailang               | Stepped iteration                          | Core |
| 083   | 083_zip_loop.ailang                | Zip two sequences                          | Core |
| 084   | 084_enumerate_loop.ailang          | Enumerate (index + value)                  | Core |
| 085   | 085_loop_else.ailang               | Loop-else (no-break clause)                | Nice feature |
| 086   | 086_goto.ailang                    | Goto (yes, it exists — when you actually need it) | Important for systems |
| 087   | 087_exception_flow.ailang          | Exception flow in loops                    | Core |
| 088   | 088_short_circuit.ailang           | Short-circuit evaluation in loops/conditions | Core |
| 089   | 089_assertion.ailang               | Assertions inside loops                    | Core |
| 090   | 090_compile_vs_runtime_branch.ailang | Compile-time vs runtime branching        | Advanced / important |

### 6. Functions & Abstraction (091–119)

| New # | Current Filename                          | Topic                                      | Notes |
|-------|-------------------------------------------|--------------------------------------------|-------|
| 091   | 091_basic_function.ailang                | Basic function definition & call           | Core |
| 092   | 092_multi_params.ailang                  | Multiple parameters                        | Core |
| 093   | 093_return_value.ailang                  | Returning values                           | Core |
| 094   | 094_multi_return_via_pool.ailang         | Multiple returns via pool / out-params     | Core AILang pattern |
| 095   | 095_void_function.ailang                 | Void / SubRoutine (no return)              | Core |
| 096   | 096_default_parameters.ailang            | Default parameters                         | Core |
| 097   | 097_keyword_arguments.ailang             | Keyword arguments                          | Core |
| 098   | 098_variadic_functions.ailang            | Variadic functions                         | Core |
| 099   | 099_factorial.ailang                     | Factorial (intro recursion)                | Core |
| 100   | 100_fibonacci.ailang                     | Fibonacci                                  | Core |
| 101   | 101_tail_recursion.ailang                | Tail recursion optimization                | Important |
| 102   | 102_mutual_recursion.ailang              | Mutual recursion                           | Core |
| 103   | 103_lambdas.ailang                       | Lambdas / anonymous functions              | Core |
| 104   | 104_higher_order_functions.ailang        | Higher-order functions                     | Core |
| 105   | 105_functions_returning_functions.ailang | Functions that return functions            | Core |
| 106   | 106_closures.ailang                      | Closures                                   | Core |
| 107–113 | *(gaps)*                               | —                                          | — |
| 114   | 114_pure_function.ailang                 | Pure functions                             | Core |
| 115   | 115_side_effect_free.ailang              | Side-effect-free code                      | Core |
| 116   | 116_inline_functions.ailang              | Inline functions                           | Core |
| 117   | 117_nested_functions.ailang              | Nested functions                           | Core |
| 118   | 118_forward_declaration.ailang           | Forward declarations (or lack thereof)     | Core |
| 119   | 119_overloaded_functions.ailang          | Function overloading                       | Core |

### 7. Functional Patterns (121–125)

| New # | Current Filename                    | Topic                    | Notes |
|-------|-------------------------------------|--------------------------|-------|
| 120   | *(gap)*                             | —                        | — |
| 121   | 121_map_filter_reduce_args.ailang  | Map / Filter / Reduce (arg style) | Core |
| 122   | 122_map_pattern.ailang             | Map pattern              | Core |
| 123   | 123_filter_pattern.ailang          | Filter pattern           | Core |
| 124   | 124_reduce_pattern.ailang          | Reduce pattern           | Core |
| 125   | 125_zip_unzip.ailang               | Zip / Unzip              | Core |

### 8. Error Handling, Results, Options & Recovery (271–290)

These use higher numbers because they were added later in the curriculum.

| New # | Current Filename                    | Topic                              | Notes |
|-------|-------------------------------------|------------------------------------|-------|
| 271   | 271_throw_exception.ailang         | Throwing exceptions                | Core |
| 272   | 272_catch_exception.ailang         | Catching exceptions                | Core |
| 281   | 281_result_type.ailang             | Result / Either type               | Core modern pattern |
| 282   | 282_option_maybe.ailang            | Option / Maybe                     | Core |
| 283   | 283_panic_recover.ailang           | Panic + recover                    | Core |
| 284   | 284_error_wrapping.ailang          | Error wrapping                     | Core |
| 285   | 285_assertions.ailang              | Assertions                         | Core |
| 286   | 286_validate_inputs.ailang         | Input validation                   | Core |
| 287   | 287_graceful_recovery.ailang       | Graceful recovery patterns         | Core |
| 290   | 290_user_friendly_errors.ailang    | User-friendly error messages       | Core |

### 9. Classic Algorithms & Puzzles (434–439)

| New # | Current Filename                    | Topic                    | Notes |
|-------|-------------------------------------|--------------------------|-------|
| 434   | 434_tower_of_hanoi.ailang          | Tower of Hanoi (recursion) | Excellent capstone |
| 436   | 436_gcd_euclidean.ailang           | Euclidean GCD              | Core |
| 437   | 437_lcm.ailang                     | LCM (using GCD)            | Core |
| 439   | 439_fast_exponentiation.ailang     | Fast exponentiation (binary exp) | Core |

### 10. Advanced Language Idioms & Companions (Unnumbered → Proposed 500+ or separate "Advanced" section)

| Proposed | Current Filename                    | Topic / Purpose                                      | Recommendation |
|----------|-------------------------------------|------------------------------------------------------|----------------|
| 501      | fork_not_switch.ailang             | `Fork` vs traditional if/switch — the binary dispatch story | **Must read** after 061–066 |
| 502      | fork_branch_combinatorial.ailang   | Full multi-axis combinatorial decision tree using Fork + Branch together (text-adventure combat resolver) | **Capstone control-flow demo** — one of the best in the set |

---

## Suggested Next Steps (for you / me)

1. **Approve this index** — I can place it in `Demo Programs/` (or move to `Programming_Manual/` if preferred).
2. **Physical renumbering?** I can write a small script (or use terminal commands) to rename every file into the clean "New #" sequence above, while updating the two `fork_*` files' internal comments that hard-reference the old 062 numbers.
3. **Fill the gaps** — Some gaps (034, 079, etc.) could be filled with missing topics if you want a truly complete 001–N set.
4. **Add a top-level `README.md`** in `Demo Programs/` that points new users here + shows the compile command.
5. **Cross-link** from `Programming_Manual/Intro To Ailang Programming.md` and other manuals.

---

## Notes on AILang Philosophy Visible in These Demos

- Everything is explicit (no hidden control flow, no precedence surprises).
- `Fork` and `Branch` are intentionally distinct from each other and from `IfCondition`.
- Multiple return via pools / named out-params is the idiomatic pattern.
- `FixedPool` for shared mutable state across SubRoutines is shown in the advanced fork demo.
- Recursion, tail recursion, and higher-order functions are all first-class teaching material.

This collection is one of the best "learn the language by reading real small programs" resources in the tree.

Let me know how you'd like to proceed — renumber the files? Add more demos for the gaps? Generate a printable "student workbook" version? Or integrate this index into the Programming Manual?

**Current location of the programs:**
`Demo Programs/programs/*.ailang`

**This index file:** `Demo Programs/DEMO_PROGRAMS_TEACHING_INDEX.md` (newly created)