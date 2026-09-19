# AIMacro CPython conformance scorecard

Generated **2026-09-19**. Python 3.11.6. Stdlib `/home/bob/tools/oss-cad-suite/lib/python3.11`.

## Suites

| Suite | Stage | Total | Pass | Fail | In-scope pass | Seconds |
|-------|-------|------:|-----:|-----:|--------------:|--------:|
| `curated` | run vs python3 | 25 | **25** | 0 | 25/25 | 12 |
| `lib` | transpile | 585 | **182** | 403 | 168/395 | 52 |

Was 84/585 before the SIGSEGV grind, 67/585 before the parse grind. Curated still 25/25.

## The 313 “codegen fails” were a misread

Those 313 had **no `Parse Error:` text** in the JSON tail, so they looked like codegen. Re-running with `Parse_Consume` printing `expected token N got M` showed they were **silent parse failures** (`Parse.err=1` without a message).

Of those 313:

| Count | Bucket | Cause |
|------:|--------|--------|
| 144 | `from .mod import` / `from . import` | relative import; first token after `from` is `.` |
| 92 | expected `)` got STRING | implicit `"a" "b"` concat, often across newlines inside `()` |
| 21 | expected `:` got IDENT | encodings codecs / annotations |
| 13 | expected symbol after `import` | `from x import (a, b)` parentheses |
| 7 | SIGSEGV | real crash |
| 3 | empty file | empty `__init__.py` |
| rest | mixed `)`, `]`, `}` mismatches | listcomp, type params, etc. |

## What we fixed in this grind

- `Parse_Consume` now prints expected vs got (so this bucket cannot hide again)
- Relative `from . import x` / `from .mod import *`
- `from x import (a, b)` parenthesized names
- Implicit string concat `"a" "b"`
- Lexer joins newlines inside `()` and `[]` (Python implicit line joining; not inside `{ }` blocks)
- Skip emitting `Import.` for relative `.` modules (avoids `Import..`)
- `AST_GetField` covers remaining node types; OOP method-body emit is null-guarded
- Implicit `"a" "b"` BINARY_OP slots were swapped (`op` in left); encodings tables SIGSEGV
- Decorator attach no longer `ArraySet(0, …)` when the following class/def fails to parse

## Remaining lib fails (403)

**SIGSEGV pile is gone** (`rc=-11`: 103 → 0). Former crash files now transpile (98/103) or fail as parse (`Expected '}' after class body`, 5/103).

| Count | Message |
|------:|---------|
| 132 | Expected `}` after class body (enum tuple values, decorated class parse) |
| 68 | Unexpected token in expression |
| 27 | expected `)` got STRING |
| 27 | expected `}` got IDENT |
| 19 | expected `}` got STRING |
| 19 | expected `)` got `:` |
| 17 | Expected `{` to start block |
| 2 | timeout (`rc=124`, `_pydecimal.py` / `smtpd.py`) |

Next grind: class-body `}` 132, then unexpected-token 68.

## How to re-run

```bash
python3 tools/aimacro_cpython_runner.py --verbose
python3 tools/aimacro_cpython_runner.py --corpus lib --stage transpile --timeout 2 \
    --output-json results/aimacro_conformance.json
```
