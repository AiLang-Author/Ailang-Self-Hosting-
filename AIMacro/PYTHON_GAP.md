# AIMacro vs Python — gap to close

Target is **not** CPython. Target is the 95th percentile of scripts people actually
write: CLI tools, file munging, small games, glue, OOP-ish classes, dict/list
wrangling. Syntax is Python-shaped with C-style `{ }` blocks.

Matrix as of 2026-09-18: **62 tests, 62 run**. Waves 1–16 shipped. CPython-lite harness: `tools/py2aim.py` + `tools/aimacro_cpython_runner.py`. Mountain scorecard: `--corpus all` → [CONFORMANCE.md](CONFORMANCE.md).

---

## Already in (verified by tests)

| Area | Notes |
|------|--------|
| Functions, nested `def` (hoisted) | No closures |
| `if` / `elif` / `else` / `while` / `for` | Braces, not indent |
| `break` / `continue` / `return` / `pass` | |
| ints, `+ - * % ** //`, augassign | `/` is true division (Wave 4) |
| strings, concat, index, slice, methods | strip/upper/lower/find/split/replace/join/starts/ends |
| lists, index, slice, append/pop/insert | |
| dicts, `d[k]`, keys/values/items/get | |
| classes, `__init__`, methods, `self`, inheritance, `super` | |
| `isinstance(obj, Class)` and `isinstance(x, int/str/list)` | `isinstance(x, None)` is **not** Python and currently returns 0 |
| `print`, `len`, `str`, `repr`, `int`, `range`, `min`/`max`, `sorted` | `print(True)`/`print([1, 2])`/`print({"a": 1})` match CPython |
| `enumerate`, `zip` | |
| `type(x)` | Returns TypeID integer, not a type object |

---

## Semantic mismatches (Python programmers will hit these)

These are not missing features so much as **wrong Python**:

1. **`/` is true division** (Wave 4). `//` is integer. Mixed `int`/`float` arithmetic promotes. `int/float ==` is numeric.
2. **`None` is a sentinel** (Wave 1) — `Types.GetNone()`. `None is 0` is false. (Old text said `None` was `0`.)
3. **`type()` returns a TypeID integer**, not `int`/`str`/`list` objects. `type(x) is int` cannot work.
4. **`isinstance(x, None)`** is invalid Python. Use `x is None` or `isinstance(x, type(None))` once types exist.
5. **Truthiness of `[]` / `""` / `{}`** is false (Wave 1, `SmartBool`).
6. **Nested functions share no cell.** Hoisted to file scope; cannot close over locals.
7. **`import m` emits `Import.m`** for unknown modules. `sys`/`os`/`json`/`math`/`time` are shims (Wave 3), not module objects.

---

## Close-the-spec order (recommended)

### Wave 1 — make daily scripts not lie — **shipped 2026-09-18**

| Item | Status |
|------|--------|
| Distinct `None` sentinel | Done — `Types.GetNone()`, `is` / `is not` |
| Container/string truthiness | Done — `AIMacro.SmartBool` on if/while/not/and/or |
| `/` integer-only | Documented; floats deferred to FPU |
| `for x in list/str/dict` | Done — `IterLen` / `IterGet` |
| `x in list/dict/str` | Done |
| `open`/`read`/`write`/`close` | Done — real syscalls |
| `sys.argv` / `argv()` | Done — `/proc/self/cmdline` |

### Wave 2 — 95th-percentile syntax — **shipped 2026-09-18**

| Item | Status |
|------|--------|
| f-strings `f"hi {name}"` | Done — `{ident}`, `{obj.attr}`, `{func(n)}`; `{{`/`}}` escapes |
| Default args `def f(x=1)` | Done — omitted args filled at the call site |
| Tuple unpack `a, b = pair` | Done (was in parser; now tested) |
| Chained compare `1 < x < 10` | Done |
| `with open(...) as f { ... }` | Done — body then `FileClose` |
| List comps `[x for x in xs if p]` | Done |
| `*args` | Done in Wave 3 — extras packed into an array Input |
| `try/except` | Done in Wave 5 |

### Wave 3 — stdlib shims (not CPython modules) — **shipped 2026-09-18**

Implemented as `AIMacro` builtins + `import` mapping, not a pip universe.
`import os` / `json` / `math` / `time` / `sys` emit nothing (runtime already linked).

| Shim | Status |
|------|--------|
| `sys.argv`, `sys.exit`, `sys.stdin`/`stdout` | Done — argv via `/proc/self/cmdline`; stdin/stdout are fd 0/1 file handles |
| `os.path.join/exists/basename/dirname`, `os.listdir` | Done — join nests; listdir is `getdents64` |
| `json.loads` / `json.dumps` | Done — JSON tagged values converted to Hash/Array |
| `math.sqrt/sin/cos/pi` | Done — integer `Math.ISqrt` / `Trig.*`; `pi` is 31416 |
| `time.time` / `time.sleep` | Done — `clock_gettime` / `nanosleep` (integer seconds) |
| `*args` | Done — named Inputs plus last `Address` pack array |

### Wave 4 — IEEE floats — **shipped 2026-09-18**

Wraps compiler `Float_*` primitives (binary64 in GPR, SSE2). Values are boxed so they are distinct from ints.

| Item | Status |
|------|--------|
| `/` true division | Done — `AIMacro.TrueDiv` → `Float_Div` |
| `//` integer | Done — `AIMacro.FloorDiv` (truncates float operands to int) |
| Literals `1.5`, `.5` | Done — `AIMacro.FloatParse` |
| `float()` / `int()` / `str()` / `print` | Done |
| `+ - *` promote if either side is float | Done — `NumAdd`/`NumSub`/`NumMul` |
| `== != < <= > >=` numeric with floats | Done |
| `math.sqrt/sin/cos/pi` | Done — `Float_Sqrt`/`Sin`/`Cos`; pi is IEEE 3.14159… |
| `isinstance(x, float)` | Done — `TypeID.FLOAT` |

Integer algorithms that used `/` as truncating div were switched to `//` in the test corpus.

### Wave 5 — catchable errors — **shipped 2026-09-18**

AILang `TryBlock` is structured flow only (catch never runs). Wave 5 desugars to a pending flag, `Fork` for catch, `Branch` for typed `except`, and a Plex node for the exception object.

| Item | Status |
|------|--------|
| `try { } except { }` | Done — remaining try stmts skipped via `Fork` |
| `except ValueError as e` | Done — `Branch` on kind; `e` is a Plex node |
| `raise ValueError("msg")` | Done — uncaught `ProcessExit(1)` |
| `finally` | Done — always runs after try/except |
| `open` missing file | Done — `FileNotFoundError` (kind 4) |
| `json.loads` failure | Done — `ValueError` |
| `with` body | Skips remaining body if pending; still `FileClose` |

Not stack-unwind: `raise` in a callee is seen after that call statement returns. Deep frames that ignore the pending flag will keep running until the `try` checks again.

### Wave 6 — data/error honesty — **shipped 2026-09-18**

| Item | Status |
|------|--------|
| `json.dumps("hello")` | Done — `LooksLikeString` (not `>= 4e6`) |
| `print(e)` / `str(e)` | Done — Plex exception prints message |
| Traceback ring | Done — ring 0 links successive raises |
| Scientific literals `1e-3` | Done — lexer + `FloatParse` exponent |
| `**` on floats | Done — `NumPow` loop-mul (int exp); ints still `Math.Power` |

Indent Python → braces: `tools/py2aim.py`. Compare to CPython: `tools/aimacro_cpython_runner.py` (see [PYTHON_TESTS.md](PYTHON_TESTS.md)).

### Wave 7 — print/repr honesty — **shipped 2026-09-18**

`True`/`False` are boxed (`TypeMagic.BOOL`) so they print as themselves while still comparing equal to `1`/`0`. List/dict `str`/`print` use Python-style `repr`. `json.dumps` walks native Hash/Array and matches CPython spacing (`", "`, `": "`).

| Item | Status |
|------|--------|
| `print(True)` / `print(False)` vs `print(1)` | Done — `TrueVal`/`FalseVal` boxes |
| `print([1, 2])` / `print({"a": 1})` | Done — `Repr`; inline lits flatten to temps |
| `repr(x)` | Done — `AIMacro.Repr` (`'str'` single quotes) |
| `json.dumps({"k": "v"})` | Done — `JsonDumpNative`; string values quoted |
| `json.dumps(True)` / `None` | Done — `true` / `null` |
| `True == 1` / `True + 1` | Done — `BoolVal` unbox in `Num*` |

### Wave 8 — comparisons print True/False — **shipped 2026-09-18**

Comparisons, `is`/`in`/`not`, `isinstance`, `any`/`all` return boxed bools. `and`/`or` return the operand (Python), not `0`/`1`. Not short-circuit: both sides of `and`/`or` are evaluated.

| Item | Status |
|------|--------|
| `print(1 == 1)` is `True` | Done — `NumEq`/`Ne`/`Lt`/`Le`/`Gt`/`Ge` box |
| `is` / `is not` | Done — `AIMacro.Is` |
| `in` / `not in` | Done — `Bool(Contains)`; list uses `NumEq` so `True in [1]` |
| `not` | Done — `AIMacro.NotVal` |
| `and` / `or` | Done Wave 8 operands; Wave 9 short-circuit |
| chained `1 < x < 9` | Done Wave 8 box; Wave 9 short-circuit later links |
| `isinstance` / `any` / `all` | Done — boxed; `all([])` is `True` |

### Wave 9 — short-circuit — **shipped 2026-09-18**

`and`/`or` emit `IfCondition` so the skipped operand is not evaluated. Chained compare evals the first two operands, then each later link only if the previous is true (middle value reused, not re-eval'd).

| Item | Status |
|------|--------|
| `0 and boom()` does not call `boom` | Done — `Gen_ShortCircuit` |
| `1 or boom()` does not call `boom` | Done |
| `x or "d"` | Done — still returns the operand |
| `5 < 3 < boom()` does not call `boom` | Done — `Gen_FlattenChainCompare` |
| `if 0 and boom()` | Done — `Gen_If` flattens the condition |

### Wave 10 — dict insertion order — **shipped 2026-09-18**

`Hash` keeps an insertion-order array on the header. `keys`/`values`/`items`, `print`/`repr`, `json.dumps`, and `for k in d` follow CPython 3.7+ order. `pop`/`delete` drop that key and leave the rest.

| Item | Status |
|------|--------|
| `print({"z": 1, "a": 2})` is `{'z': 1, 'a': 2}` | Done |
| `d.keys()` / `for k in d` insertion order | Done |
| `json.dumps({"z": 1, "a": 2})` | Done |
| update existing key keeps position | Done (Set update does not re-push) |

### Wave 11 — lambda as hoisted def — **shipped 2026-09-18**

`lambda args: expr` becomes `Function.__lam_N` plus `AddressOf` / `CallIndirect`. No closures (same as nested `def`). No `key=` on `sorted` yet.

| Item | Status |
|------|--------|
| `f = lambda x: x+1; f(3)` | Done — `AddressOf` + `CallIndirect` |
| `(lambda a, b: a*b)(3, 4)` | Done — `INDIRECT_CALL` |
| `lambda: 7` | Done — zero-arg `CallIndirect` |
| closures `lambda x: x+n` | Not in scope — outer locals are not cells |

### Wave 12 — ternary `x if c else y` — **shipped 2026-09-18**

Conditional expressions short-circuit like `and`/`or`. Only the taken branch is evaluated. Nested `a if b else c if d else e` is right-associative. List-comp `if` filters stay filters (iterable is `or`-expr, not full ternary).

| Item | Status |
|------|--------|
| `print(1 if 1 else 0)` | Done |
| `1 if 1 else boom()` does not call `boom` | Done |
| `n if n else "d"` | Done |
| `lambda v: 1 if v else 0` | Done |
| `[x for x in xs if p]` still a filter | Done |

### Wave 13 — keyword args on builtins — **shipped 2026-09-18**

`name=value` in call lists is `Node.KW_ARG`. `sorted` honors `key=` (CallIndirect) and `reverse=`. `open` honors `mode=` / `file=`.

| Item | Status |
|------|--------|
| `sorted(xs, reverse=True)` | Done |
| `sorted(xs, key=lambda n: 0-n)` | Done — `TypedSortedKey` |
| `open(path, mode="w")` | Done |
| user `f(x=1)` generic kwargs | Not yet — builtins only |

### Wave 14 — input() is live — **shipped 2026-09-18**

No language gap. `AIMacro.Input` already `read(0)`. The scoreboard skipped `dungeon_escape` and `test_input` instead of piping stdin. `.stdin` files + `run_matrix.sh` run them. CPython-lite uses sibling `.stdin` for both python3 and the binary.

| Item | Status |
|------|--------|
| `input()` / `input("")` | Done — already worked |
| `test_input.aim` | Done — `Alice` / `21` |
| `dungeon_escape.aim` | Done — win path, VICTORY |
| curated `input_fn.py` | Done |

### Wave 15 — user-function keyword args — **shipped 2026-09-18**

Call-site `name=value` binds to `def` parameter names (plus defaults). `f(b=2, a=1)` emits `f(1, 2)`.

| Item | Status |
|------|--------|
| `f(a=1, b=2)` / `f(b=2, a=1)` | Done |
| mixed `f(1, b=2)` | Done |
| defaults `g(x=3)` with `y=5` | Done |
| `**kwargs` | Still later |

### Wave 16 — print/range/list as scripts use them — **shipped 2026-09-18**

| Item | Status |
|------|--------|
| `print(1, 2, sep=",")` / `end=` | Done — `Gen_PrintCall` skips KW_ARG |
| `range(5, 0, -1)` as a value | Done — negative step no longer forced to 1 |
| `list(range(3))` / `list("ab")` / `list()` | Done — `AIMacro.ListFrom` |

`for n in range(...)` still uses `Gen_ForRange` (does not materialize the list).

Parser/lexer work for the CPython mountain (same day): fail-fast; relative `from .`; parenthesized `from x import (a, b)`; implicit `"a" "b"`; lexer line-joining in `()`/`[]`; class annotations; `@decorators`; `async`/`await`; `*args` at calls. Lib transpile **84/585**. The 313 “codegen” misses were silent `Parse_Consume` failures. See [CONFORMANCE.md](CONFORMANCE.md).

### Explicitly later / never

- `async`/`await`, generators, `yield`
- decorators, metaclasses, descriptors
- `match`/`case`
- `set`, `bytes`, `bytearray` (add when a test needs them)
- `*args/**kwargs` mixing, keyword-only params
- packaging, venv, pip
- full CPython object model (`type` as first-class, MRO edge cases)

---

## Suggested next patches

1. Grow `tests/python/curated/` from CONFORMANCE fail stages (dict constructor, `assert`, call-site `*args`).
2. `input()` EOF → `EOFError` if a script needs it.
3. Re-run `./AIMacro/scripts/run_conformance.sh` after each wave; chase in-scope lib transpile fails.

Bytecode/VM is a later conversion of the existing emit engine. Do not start it until AOT stays green; AOT is the production path.
