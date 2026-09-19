# AIMacro vs CPython tests (test262 analog)

JS has `test262` + `tools/test262_runner.py` + `JS-tests/test262_harness.ailang`.
AIMacro’s counterpart is **not** a full CPython `Lib/test` run (unittest, C API,
importlib). It is the same *shape*: preprocess → execute → compare → JSON.

## Pieces

| JS (test262) | AIMacro |
|--------------|---------|
| test262 checkout | optional CPython tree (`--cpython`) |
| throw/async preprocessor | `tools/py2aim.py` (indent → `{ }`) |
| `test262_harness.x` | `./aimacro.x` + `./ailang.x` |
| `tools/test262_runner.py` | `tools/aimacro_cpython_runner.py` |
| curated midgate paths | `tests/python/curated/*.py` |

## Convert indent Python to AIMacro

```bash
python3 tools/py2aim.py tests/python/curated/if_while.py /tmp/if_while.aim
./aimacro.x /tmp/if_while.aim /tmp/if_while.ailang
./ailang.x /tmp/if_while.ailang /tmp/if_while
/tmp/if_while
```

## Run the lite suite (compare stdout to CPython)

```bash
python3 tools/aimacro_cpython_runner.py --verbose
python3 tools/aimacro_cpython_runner.py --output-json results/aimacro_cpython.json
```

`--corpus all` is the mountain: curated (stdout vs python3) plus CPython
stdlib transpile plus `Lib/test` transpile. `Lib/test` is unittest — those
files are syntax probes, not a unittest runner. See [CONFORMANCE.md](CONFORMANCE.md).

```bash
./AIMacro/scripts/run_conformance.sh
```

## Deep run (2026-09-18)

**25/25** curated files pass stdout vs CPython after Wave 16 (`print_range_list.py`). See [AUDIT_2026-09-18.md](AUDIT_2026-09-18.md).

Mountain (CPython Lib + Lib/test) is a separate scorecard, not a unittest run:

```bash
./AIMacro/scripts/run_conformance.sh
# or:
python3 tools/aimacro_cpython_runner.py --corpus all \
    --output-json results/aimacro_conformance.json \
    --output-md AIMacro/CONFORMANCE.md
```

```bash
python3 tools/aimacro_cpython_runner.py --verbose --output-json results/aimacro_cpython_deep.json
```

## Wave 16

`print(sep=, end=)`, `list(range(5, 0, -1))`, `list("ab")`. Curated: `print_range_list.py`.

## Wave 15

`f(b=2, a=1)` and defaults via keywords. Curated: `kwargs_user.py`.

## Wave 14

`input()` vs CPython with a sibling `.stdin` file. Curated: `input_fn.py`.

## Wave 13

`sorted(xs, key=lambda n: 0-n)` and `reverse=True`. Curated: `sorted_key.py`.

## Wave 12

`1 if 1 else 0`, nested ternary, `lambda v: 1 if v else 0`. Curated: `ternary.py`.

## Wave 11

`f = lambda x: x+1; print(f(3))` and `(lambda a, b: a*b)(3, 4)`. No closures.
Curated: `lambda_fn.py`.

## Wave 10

`print({"z": 1, "a": 2})` is `{'z': 1, 'a': 2}`. Curated: `dict_order.py`.

## Wave 9

`0 and boom()` / `1 or boom()` / `5 < 3 < boom()` do not call `boom`.
Curated: `short_circuit.py`.

## Wave 8

`print(1 == 1)` is `True`; `1 and 2` is `2`; `in`/`is`/`not`/`isinstance`/`any`/`all`
match CPython. Curated: `compare_bool.py`.

## Wave 7

`print(True)`, `print([1, 2])`, `print({"a": 1})`, `repr(x)`, and
`json.dumps({"k": "v"})` match CPython stdout. Curated: `print_repr.py`.

Grow `tests/python/curated/` the way JS grew midgate, then slice CPython
`Lib/test/test_grammar.py`-style files — not 50k tests on day one.
