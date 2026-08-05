# Desert e7dz — 2058/2931 (70.6%)

Tip after e7dy 1972/2931 (67.6%). **+86** desert passes.

## Fixes

### 1. CallFunc dual-write `arguments` onto frame env (species invocation)
`GET_GLOBAL` walks `GetCurEnv()` before GlobalHash. CALL dual-writes
`arguments` onto the frame env; CallFunc only SetGlobal. Nested species
ctors under `testWithTypedArrayFactories(TA, makeCtorArg)` resolved the
outer factory's `arguments` (argc=2, TA+factory) instead of Construct's
`«len»`. Formal `count` was correct; `arguments` object was wrong.

Mirror CALL: after CreateArguments + SetGlobal, also
`JSRT_ObjSet(frame_env, "arguments", args_obj)`.

Unlocked: map/filter/slice/subarray `speciesctor-get-species-custom-ctor-invocation`.

### 2. TypedArray default sort — CompareTypedArrayElements
Array default is ToString order; TA requires numeric compare + NaN last +
−0 before +0. ArrSort now ValidateTypedArray and branches on is_ta.

### 3. Float64 get/set via lo/hi u32 limbs
Signed `*256` / `/256` on full 64-bit patterns overflowed when the sign
bit was set (most negative f64 values). Assemble/write as two u32 limbs
with ShiftLeft/ShiftRight + BitwiseAnd. Also fixed DataView f64 paths.

## Score
| Category | Total | Pass | % |
|---|---:|---:|---:|
| ArrayBuffer | 196 | 79 | 40.3 |
| DataView | 561 | 473 | 84.3 |
| TypedArray | 1438 | 961 | 67.4 |
| TypedArrayConstructors | 736 | 545 | 74.3 |
| **TOTAL** | **2931** | **2058** | **70.6** |

Prior e7dy: 1972. Goal 95% ≈ 2784 (−726 remaining).
