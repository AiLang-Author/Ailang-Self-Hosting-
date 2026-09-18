# Library.Math(ailang)

## NAME

`Library.Math` — composed float helpers on top of compiler `Float_*` builtins

## ADVERTISING

This is **not** C `math.h`.

| Kind | How you get it | Examples |
|------|----------------|----------|
| Compiler primitive | no import | `Add`, `Float_Sin`, `Float_Sqrt`, `Float_Pow`, `Float_Mod` |
| This library | `LibraryImport.Math` | `Math.Hypot`, `Math.Asin`, `Math.Log2` |

Primitives are the language. The library is optional sugar for identities
(`hypot = sqrt(x²+y²)`, `log2 = ln(x)/ln(2)`). It is **not** auto-imported.
`LibraryImport.Arena` is the only “just there” memory helper; math stays
explicit so a tiny program does not pull CAD-sized numerics.

`Librarys/TF/Library.Math.ailang` is TensorFlow config, not this file.

## SYNOPSIS

```
LibraryImport.Math

h = Math.Hypot(x, y)
a = Math.Atan(x)
s = Math.Asin(x)
c = Math.Acos(x)
lg = Math.Log2(x)
l10 = Math.Log10(x)
e2 = Math.Exp2(x)
```

Arguments and results are IEEE-754 binary64 **bit patterns in `Integer`**,
same as `Float_*`.

## SEE ALSO

`docs/compiler/MATH_PRIMITIVES.md`, `Programming_Manual/AILANG Arithmetic and Mathematical Ope.md`
