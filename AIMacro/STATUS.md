# AIMacro Status Scorecard

Living document. Re-run audit scripts and update counts after substantive changes.

**Last updated:** 2026-09-19 (hygiene: curated 25/25 after Hash order restore; class-body lib 148→170/531; matrix 62/62/62; SIGSEGV 0)

## Build artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Transpiler CLI | `aimacro.x` | Rebuilt 2026-09-19 (~393 KB ELF) from `aimacro_cli.ailang` |
| AILang runtime | `ailang.x` | Present at repo root |
| Sources | `aimacro_cli.ailang`, `aimacro_console.ailang` | Present |

## Phase gate

| Gate | Target | Current |
|------|--------|---------|
| M0 — Project docs + branch | Complete | Docs present (on `master`) |
| M1 — P0 transpile | 100% | **42/42 transpile OK** |
| M2 — P0 compile + run | ≥95% | **42/42 compile, 42/42 run** |
| M3 — P1 coverage | Roadmap | Tests in matrix run; feature gaps still in SPEC |
| M4 — AIMacroVM design lock | SPEC §VM | Draft in SPECIFICATION.md |
| M5 — VM prototype | JSVM parity sketch | Not started |
| M6 — Dual-mode (AOT + VM) | Optional | Not started |

## Full matrix (2026-09-18)

| Category | Total | Transpile OK | Compile OK | Run OK |
|----------|-------|--------------|------------|--------|
| All `AIMacro_Tests/*.aim` | 62 | 62 | 62 | **62** |
| P0 | 8 | 8 | 8 | 8 |
| P1 | 18 | 18 | 18 | 18 |
| P2 | 16 | 16 | 16 | 16 |
| Wave extras | 20 | 20 | 20 | 20 |

`dungeon_escape.aim` and `test_input.aim` take stdin from sibling `.stdin` files. `./AIMacro/scripts/run_matrix.sh` pipes them. No skips.

CPython-lite curated: **25/25** (Hash insertion order restored on this branch). Lib transpile **170/531** (py3.13; was 148 before class-body grind). SIGSEGV **0**. See [CONFORMANCE.md](CONFORMANCE.md).


## Class-body grind (2026-09-19)

- Bare tuple RHS, chained assign, annotated `self.x: T = …`
- Method/func generic/union annotations skipped for parse coverage
- `py2aim` multiline `def`/`class` headers; `raise X from Y` skip
- Lib 148→170/531 (py3.13); class-body error files 119→108
- Matrix 62/62/62; fizzbuzz ELF ~211 KB; SIGSEGV 0
- Hygiene: `Library.Hash` order array at header+32 → curated **25/25**

## Wave 16 (this round)

- `print(..., sep=, end=)`; keyword args are not printed as values
- `range(n)` / `range(a,b)` / `range(a,b,step)` as a value, including negative step
- `list()` / `list(iterable)` / `list("ab")`
- Tests: `wave16_print_range.aim`, `tests/python/curated/print_range_list.py`

## Wave 15

- User `def` keyword args: `f(b=2, a=1)` binds by parameter name; defaults still fill holes
- Tests: `wave15_user_kwargs.aim`, `tests/python/curated/kwargs_user.py`

## Wave 14

- `input()` was never broken (syscall `read(0)`). The matrix skipped two tests rather than piping stdin.
- `.stdin` fixtures: `dungeon_escape` win path `1 1 3 2 2`; `test_input` `Alice` / `21`
- Matrix **60/60 run**. Curated: `input_fn.py` + `input_fn.stdin`

## Wave 13

- Keyword args `name=value` in calls (`Node.KW_ARG`)
- `sorted(..., key=lambda ..., reverse=True)`; `open(..., mode="w")`
- Tests: `wave13_kwargs.aim`, `tests/python/curated/sorted_key.py`

## Wave 12

- Ternary `x if c else y` with short-circuit (only the taken branch runs)
- List-comp `if` remains a filter
- Tests: `wave12_ternary.aim`, `tests/python/curated/ternary.py`

## Wave 11

- `lambda args: expr` hoists to `Function.__lam_N`; value is `AddressOf`; calls use `CallIndirect`
- No closures (same as nested `def`)
- Tests: `wave11_lambda.aim`, `tests/python/curated/lambda_fn.py`

## Wave 10

- Dict insertion order on `Hash` (header order array): `print`/`repr`/`keys`/`json.dumps`/`for k in d` match CPython 3.7+
- `pop`/`delete` remove that key and keep remaining order
- Tests: `wave10_dict_order.aim`, `tests/python/curated/dict_order.py`

## Wave 9

- `and`/`or` short-circuit via `IfCondition` (`0 and boom()` does not call `boom`)
- Chained compare short-circuits later links (`5 < 3 < boom()` is safe)
- Tests: `wave9_short_circuit.aim`, `tests/python/curated/short_circuit.py`

## Wave 8

- Comparisons/`is`/`in`/`not`/`isinstance`/`any`/`all` return boxed `True`/`False`
- `and`/`or` return the operand (`1 and 2` is `2`, `0 or 5` is `5`); not short-circuit
- Chained compare boxes the combined predicate
- Tests: `wave8_compare.aim`, `tests/python/curated/compare_bool.py`

## Wave 7

- Boxed `True`/`False` (`TypeMagic.BOOL`); `print(True)` is `True`, `print(1)` is `1`; `True == 1` still holds
- `print([1, 2])` / `print({"a": 1})` via `AIMacro.Repr`; inline list/dict lits flatten
- `repr()` builtin; list/dict `str` uses repr; strings quoted with single quotes
- `json.dumps({"k": "v"})` / `True` / `None` match CPython (`JsonDumpNative`)
- Tests: `wave7_print_repr.aim`, `tests/python/curated/print_repr.py`

## Wave 6

- `json.dumps` of strings; `print(e)`/`str(e)` from Plex; traceback ring 0
- `1e-3` scientific literals; float `**` via `NumPow`
- `tools/py2aim.py` indent → `{ }`; `tools/aimacro_cpython_runner.py` vs CPython stdout
- Curated suite: `tests/python/curated/` (3/3 pass)
- Test: `wave6_json_exc.aim`

## Wave 5

- `try`/`except`/`raise`/`finally` desugar to `Fork`/`Branch` + pending flag (AILang `TryBlock` does not unwind)
- Exception object is a Plex node (type 20000+kind, slot 0 = message)
- `open` missing file raises `FileNotFoundError`; uncaught errors `ProcessExit(1)`
- Test: `wave5_try.aim`

## Wave 4

- `/` is true division via `Float_Div`; `//` stays integer
- Float literals, `float()`, boxed IEEE binary64 (`Float_*` primitives)
- `math.sqrt/sin/cos/pi` use real floats; `10 / 2 == 5` is numeric
- Test: `wave4_float.aim`. Integer-chopping tests switched to `//`

## Wave 3

- `*args`: extras packed into an array and passed as the last Input
- `import os/json/math/time/sys` skipped (no `Import.os`)
- `os.path.join/exists/basename/dirname`, `os.listdir`
- `json.loads` / `json.dumps` via AILang JSON → Hash/Array
- `math.sqrt/sin/cos/pi` (integer / fixed-point), `time.time`/`sleep`, `sys.stdin`/`stdout`
- Tests: `wave3_args.aim`, `wave3_os_json.aim`, `wave3_math_time.aim`

## Cleanup done this round

- Removed illegal `RunTask` / file-scope prints from AIMacro libraries and `Library.FixedPointTrig.ailang`
- Deduped `DictGen_SmartLen` and canonicalized `TypeID` in `AIMacroTypes`
- Deleted `Library.AIMacroCodeGen2BU.ailang`
- Stripped codegen debug `PrintMessage` noise
- Top-level `.aim` statements wrap in `SubRoutine.Main` (compiler contract)
- Parser no longer hangs on missing `end` / nested `def` / next `class`
- `print(obj.method())` and `isinstance(obj, Class)` codegen fixed

## Next

- Chase CONFORMANCE.md fail stages (decorators, `**kwargs`, `assert`, `dict()`)
- VM work (M4+) still not started — AOT emit engine is the production path; bytecode is a later conversion
