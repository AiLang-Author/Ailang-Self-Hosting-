# Full suite M31c baseline (2026-07-17)
- **Total:** 49998 tests, wall **2017s** (~33.6 min)
- **Pass:** **19129 / 49998 (38.3%)**  T/O 61, error 47
- **Prior M29h:** 21783 / 49998 (43.6%)  Δ **-2654** passes

## Scope
- **language:** 14446/23899 (60.4%)  was 16310/23899 (68.2%)  Δ -1864
- **built-ins:** 4087/23521 (17.4%)  was 4848/23521 (20.6%)  Δ -761
- **annexB:** 406/1086 (37.4%)  was 443/1086 (40.8%)  Δ -37

## Highlights
- **RegExp built-ins:** 518/1879 (27.8%) — property-escapes / unicodeSets motion vs M29
- **String:** 336/1223 (27.5%)
- **Object:** 1246/3411 (36.6%) — regression vs M29 defineProperty/create
- **Array:** 1337/3081 (43.7%)
- **Promise:** 152/677 (22.5%)

## Regression note (post-UTF-16)
Net **−2654** vs M29h. Largest pass→fail: language class (~1171), Object.defineProperty/create (~580), Array.prototype (~156).
Root cause cluster: **property keys as UTF-16** vs C-byte name checks (gOPD name/length, FuncPropGet).
Hotfix for name/length gOPD + FuncPropGet StrEq applied after suite (not in this JSON).

Artifacts: `/tmp/test262_full_m31c.json`, `results/test262_full_m31c.json`
