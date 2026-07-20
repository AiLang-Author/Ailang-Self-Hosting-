# JS Engine Handoff — M48

**Branch:** `gpu-45-may-baseline-restore`  
**Hard goal:** **90% full test262 / working JS engine, all features.**

## What landed

1. **Plan rewrite** — `JS-DEPENDENCY-PLAN.md` / `BROWSER_CONFORMANCE.md`: destination is **90% full**, not OA/S-only theater. Language first → OA/S 90% each → full 90%.
2. **SetFunctionName complete** (compiler):
   - Param default `fn = function(){}` / arrow
   - Array/obj dstr local **and** global bindings
   - Object literal `{ bar: function(){} }` (stack-safe: leave `[obj,fn]` for prop SET_PROP)
   - VM path already: FUNCTION + `"name"` → `JSRT_FuncPropSet` (M48 first commit)
3. Midgate e2e+core **PASS**.

## Language slice (vs full M47 same paths)

| Area | M47 | **M48** | Δ pass |
|------|----:|--------:|-------:|
| statements/class | 70.5% | **76.4%** | **+249** |
| expressions/class | 71.4% | **77.6%** | **+248** |
| expressions/object | 67.7% | **73.6%** | **+67** |
| for-of | 71.1% | **78.3%** | **+46** |
| arrow-function | 84.8% | **91.8%** | **+24** |
| function | 82.6% | **90.5%** | **+21** |
| **slice total** | — | **77.5%** (8455/10945) | **+655 fixed / −5 regressed** |

**fn-name-ish fixed: ~625** of the +655 (confirms M37→M47 language regression cause).

JSON: `results/test262_lang_m48.json`

## Why language regressed while grinding built-ins

M38–M47 built-in moles shared VM/property paths. Biggest: `function.name` is `!W` `C` — ordinary assign failed `CanAssign` → empty names → class/dstr cascade (~492+ of −740 language regressions). Built-ins +759, language −591, full only +174. See plan.

## Next bugs (knock order)

1. Remaining class residual (private, static, heritage) — still ~2k fails on class
2. object literal residual (~306 fails)
3. for-of residual (~160)
4. arguments-object
5. async / modules (for-await, dynamic-import)
6. Then OA/S to 90% each without language regressions

```bash
python3 tools/js_midgate.py --rebuild --quick
python3 tools/test262_runner.py --paths 'language/statements/class,language/expressions/class' -j 8
```
