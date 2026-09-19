# AIMacro CPython conformance scorecard

Generated **2026-09-19**. Remeasured on this box with **Python 3.13.5** stdlib `/usr/lib/python3.13` (531 `.py` files after excludes). Prior Waves 1–16 scorecard used Python 3.11.6 / 585 files.

## Suites (this box, after class-body construct grind)

| Suite | Stage | Total | Pass | Fail | In-scope pass | Seconds |
|-------|-------|------:|-----:|-----:|--------------:|--------:|
| `curated` | run vs python3 | 25 | **25** | 0 | 25/25 | ~5 |
| `lib` | transpile | 531 | **226** | 305 | 180/339 | ~25 |

**VM baseline before class-body grind:** lib **148/531**. After this session: **226/531** (+78 from 148; +56 from post-hygiene 170). Matrix **62/62/62**. SIGSEGV **0**. Fizzbuzz ELF **211054**.

Hygiene: rebuilt `aimacro.x` from branch `aimacro/class-body-parse-fixes` (no pre-grind binary). Curated **25/25** after Hash order fix.

## Class-body grind (this VM)

| Metric (3.13 corpus) | Pre-grind | After hygiene/grind start | After this session |
|----------------------|----------:|--------------------------:|-------------------:|
| Lib transpile OK | 148 | 170 | **226** |
| Files with class-body `}` error | 119 | 108 | **97** |
| `Expected '}' after class body` msgs | 121 | 110 | **99** |

Stop condition met: **lib ≥ 210** (226). Class-body bucket still 97 (not yet <60).

## Constructs fixed this session (prove with `/tmp/cb_repro/*.aim` before patch)

| Construct | Repro | Effect |
|-----------|-------|--------|
| genexp / dictcomp / setcomp / bare genexp arg | `genexp.aim`, `dictcomp.aim`, `setcomp.aim` | listcomp already OK; comps parse as LIST_COMP |
| star LHS `*rest, last = …` | `star_lhs.aim` | class-body unpack |
| bytes/string prefix `b"…"`, `r"…"`, `u"…"`, `br`/`rb` in calls/lists/parens | `call_bytes.aim`, `endswith_b.aim`, `exact_if.aim` | was IDENT+STRING → `expected ) got STRING` |
| `except (A, B)`, dotted `except pkg.E`, `as e` | `except_tuple.aim`, `except_dotted.aim` | was `{` got `(` |
| `try`/`except`/`else` | `try_else.aim` | else body stored AST field 6 |
| `for a, b, c in` and `for (a, b) in` | `for_three.aim`, `for_paren.aim` | multi/paren unpack |

Left alone: nested def, `__new__`, `@_simple_enum` (already parsing). No decorator evaluation.

## Remaining class-body-ish primaries (97 files)

| Count | First non-`} ` Parse Error |
|------:|----------------------------|
| 30 | Unexpected token in expression |
| 7 | expected token 17 got 86 (`in` vs `,`) |
| 6 | expected token 87 got 85 / 84 got 87 |
| rest | `)` vs IDENT, `{` mismatches, etc. |

## What we fixed (cumulative on this branch)

- Bare tuple RHS / chained assign / annotated attr assign
- Method/func generic+union annotations skipped for parse coverage
- `raise X from Y` skip; `Parse_EnterBlock` accepts leftover `:`
- `py2aim` multiline suite headers
- **Hash insertion order** (header+32 order Array) — curated dict_order
- Genexp/dictcomp/setcomp; star LHS; `b"`/`r"`/`u"` prefixes; except tuples/dotted; try-else; for multi/paren unpack

Rebuild: `./ailang.x aimacro_cli.ailang aimacro && mv -f aimacro aimacro.x`

## How to re-run

```bash
python3 tools/aimacro_cpython_runner.py --verbose --timeout 8
python3 tools/aimacro_cpython_runner.py --corpus lib --stage transpile --timeout 2 \
    --output-json results/aimacro_conformance.json
./AIMacro/scripts/run_matrix.sh
```
