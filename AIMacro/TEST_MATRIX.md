# AIMacro Test Matrix

**42** tests under `AIMacro_Tests/` (flat directory, all `.aim`).

## How to run one test

```bash
./aimacro.x AIMacro_Tests/<file>.aim AIMacro_Tests/<file>.ailang
./ailang.x AIMacro_Tests/<file>.ailang
```

Or use `./AIMacro/scripts/run_pipeline.sh AIMacro_Tests/<file>.aim`.

## Priority tiers

| Tier | Meaning |
|------|---------|
| **P0** | Must pass for Phase 1 exit (Tier A + core integration) |
| **P1** | Required for 95th-percentile claim (Tier B) |
| **P2** | Debug, isolate, stress, or regression |

## P0 — Core integration (8)

| Test | Focus |
|------|-------|
| `aimacro_feature_probe.aim` | Broad builtin + syntax smoke |
| `aimacro_full_test.aim` | Large integration |
| `test_harness.aim` | Harness self-check |
| `test_minimal.aim` | Minimal defs + calls |
| `control_flow_test.aim` | if / while / for |
| `dict_test_comprehensive.aim` | Dict literals, access, edge cases |
| `test_oop_complete.aim` | OOP integration |
| `comprehensive_test.aim` | Multi-feature sweep |

## P1 — Extended surface (18)

| Test | Focus |
|------|-------|
| `test_string_methods.aim` | str methods |
| `string_features_test.aim` | String features |
| `string_test.aim` | String basics |
| `string_concat_test.aim` | Concatenation |
| `string_equality_test.aim` | Equality / comparison |
| `test_enumerate_zip.aim` | enumerate, zip |
| `test_isinstance.aim` | isinstance |
| `test_types.aim` | Type checks |
| `test_aimacro_types.aim` | AIMacro type layer |
| `test_oop_transpile.aim` | OOP codegen |
| `test_oop_parser.aim` | OOP parse |
| `super_test.aim` | super() |
| `test_full_features.aim` | Feature bundle |
| `test_quick_wins.aim` | Quick feature wins |
| `practical_test.aim` | Practical script patterns |
| `fizzbuzz.aim` | Classic algorithm |
| `dungeon_escape.aim` | Game-style control flow |
| `complex_test.aim` | Complex expressions |
| `complex_test_2.aim` | Complex expressions (variant) |

## P2 — Debug / isolate / stress (16)

| Test | Focus |
|------|-------|
| `test.aim` | Generic scratch |
| `test_int.aim` | int builtin |
| `test_min.aim` | min builtin |
| `test_sorted_minimal.aim` | sorted minimal |
| `test_input.aim` | input() |
| `len_debug.aim` | len debugging |
| `array_debug.aim` | Array debugging |
| `not_debug.aim` | Boolean not |
| `aimacro_param_debug.aim` | Parameter passing |
| `aimacro_list_isolate.aim` | List isolate |
| `aimarco_bug_iso.aim` | Bug isolation (typo in name) |
| `aimacro_edge_cases.aim` | Edge cases |
| `aimacro_stress_test.aim` | Size / stress |
| `comprehensive_floor_test.aim` | floor() regression |
| `comprehensive_floor_test_2.aim` | floor() regression v2 |

## Full inventory (alphabetical)

```
aimacro_edge_cases.aim
aimacro_feature_probe.aim
aimacro_full_test.aim
aimacro_list_isolate.aim
aimacro_param_debug.aim
aimacro_stress_test.aim
aimarco_bug_iso.aim
array_debug.aim
complex_test.aim
complex_test_2.aim
comprehensive_floor_test.aim
comprehensive_floor_test_2.aim
comprehensive_test.aim
control_flow_test.aim
dict_test_comprehensive.aim
dungeon_escape.aim
fizzbuzz.aim
len_debug.aim
not_debug.aim
practical_test.aim
string_concat_test.aim
string_equality_test.aim
string_features_test.aim
string_test.aim
super_test.aim
test.aim
test_aimacro_types.aim
test_enumerate_zip.aim
test_full_features.aim
test_harness.aim
test_input.aim
test_int.aim
test_isinstance.aim
test_min.aim
test_minimal.aim
test_oop_complete.aim
test_oop_parser.aim
test_oop_transpile.aim
test_quick_wins.aim
test_sorted_minimal.aim
test_string_methods.aim
test_types.aim
```

## Mapping tests → libraries

| Area | Primary library |
|------|-----------------|
| Lex | `Librarys/AIMacro/Library.AIMacroLexer.ailang` |
| Parse | `Library.AIMacroParserCore.ailang`, `Library.AIMacroParserOOP.ailang` |
| Codegen | `Library.AIMacroCodeGen4.ailang` (+ CodeGen1–3, OOP, Dict) |
| Runtime | `Librarys/AIMacro/Library.AIMacro.ailang` |
| Types | `Library.AIMacroTypes.ailang`, `Library.AIMacroTypeAnnotations.ailang` |

Update `STATUS.md` after each audit with pass/fail counts per tier.