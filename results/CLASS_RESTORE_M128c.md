# Class restore — M128c

**Date:** 2026-07-26  
**Slice:** `language/statements/class`  
**JSON:** `results/test262_class_m128c.json`

| Metric | M128ba (broken) | M128c | M110 baseline |
|--------|----------------:|------:|--------------:|
| Pass   | ~897 (20.5%)    | **3962 / 4367 (91.4%)** | ~3936 (~90%) |

## Root cause (stupid, as predicted)

1. **CLASS_DECL TDZ double-slot:** Program TDZ pre-scan called `AddLocal("C")` (slot 0, `tdz_map[0]=1`). CLASS_DECL called `AddLocal` again which **always appends** → slot 1. Clear/SET_LOCAL hit slot 1; `FindLocal` still saw slot 0 in TDZ → bare `C` after `class C {}` always `ReferenceError`.
   - **Fix:** `FindLocalInScope` before `AddLocal` in CLASS_DECL (same pattern as let/const).

2. **`extends Object` / SuperCall bag:** Global `Object` is an OBJECT bag with `__ctor__`. CHECK_CTOR rejected non-FUNCTION; CALL unwrapped bag before SuperCall identity match; CALL Bridge path skipped this-init for OBJ_CTOR (88).
   - **Fix:** unwrap `__ctor__` in CHECK_CTOR; match bag/ctor in CALL+CALL_SPREAD SuperCall; this-init after Bridge SuperCall.

## Gates

```bash
python3 tools/test262_runner.py --paths language/statements/class -j8 --timeout 10
# expect ≥85–90%
```
