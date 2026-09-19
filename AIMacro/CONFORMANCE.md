# AIMacro CPython conformance scorecard

Generated **2026-09-19**. Remeasured on this box with **Python 3.13.5** stdlib `/usr/lib/python3.13` (531 `.py` files after excludes). Prior Waves 1–16 scorecard used Python 3.11.6 / 585 files.

## Suites (this box, after class-body grind + Hash order hygiene)

| Suite | Stage | Total | Pass | Fail | In-scope pass | Seconds |
|-------|-------|------:|-----:|-----:|--------------:|--------:|
| `curated` | run vs python3 | 25 | **25** | 0 | 25/25 | ~5 |
| `lib` | transpile | 531 | **170** | 361 | 147/339 | ~23 |

**VM baseline before class-body grind:** lib **148/531**. After grind: **170/531** (+22). Matrix **62/62/62**. SIGSEGV **0**. Fizzbuzz ELF **211054**.

Hygiene rebuilt `aimacro.x` from this branch; curated was 24/25 until `Library.Hash` gained the Wave-10 insertion-order array (header+32) — now **25/25**.

## Class-body grind

Target bucket from Waves 1–16 (3.11): **132** `Expected '}' after class body`.

| Metric (3.13 corpus) | Before | After |
|----------------------|-------:|------:|
| Lib transpile OK | 148 | **170** |
| Files with class-body error | 119 | **108** (−11) |
| `Expected '}' after class body` messages | 121 | **110** (−11) |
| `Expected '{' to start block` | 103 | **62** |
| `expected token 84 got 87` (`{` vs `:`) | 55 | **18** |
| `Unexpected token in expression` | 168 | **161** |
| `Expected ')' after parameters` | 9 | **4** |

Primary wins: enum-style bare tuple RHS, chained assigns, multiline `def`/`class` headers in `py2aim`, complex param/return annotations, annotated `self.x: T = …`, `raise X from Y` skip.

Nested `def` / `__new__` / `@_simple_enum(...)` already parsing (decorators stored, not applied).

## What we fixed

- Bare tuple RHS / chained assign / annotated attr assign
- Method/func generic+union annotations skipped for parse coverage
- `raise X from Y` skip; `Parse_EnterBlock` accepts leftover `:`
- `py2aim` multiline suite headers
- **Hash insertion order** (header+32 order Array) — curated dict_order

Rebuild: `./ailang.x aimacro_cli.ailang aimacro && mv -f aimacro aimacro.x`

## Remaining lib fails (361 on 3.13)

| Count (approx) | Message |
|------:|---------|
| 110 | Expected `}` after class body (genexp / other) |
| ~160 | Unexpected token in expression |
| ~27 | expected `)` got STRING |
| rest | `{` / `}` / `:` mismatches, timeouts |

Next: bucket remaining `}` by **construct** (genexp, implicit string concat, class-level if/try/with, …).

## How to re-run

```bash
python3 tools/aimacro_cpython_runner.py --verbose --timeout 8
python3 tools/aimacro_cpython_runner.py --corpus lib --stage transpile --timeout 2 \
    --output-json results/aimacro_conformance.json
./AIMacro/scripts/run_matrix.sh
```
