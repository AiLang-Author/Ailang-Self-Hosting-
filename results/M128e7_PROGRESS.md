# M128e7 progress — class field_init free-var

**Date:** 2026-07-29  
**Branch:** `master`

---

## This commit

| Area | Change |
|------|--------|
| `JSCompState.in_field_init` | Flag while compiling `__field_init__` body |
| `JSComp__EmitVarGet/Set` | Force free-var (slot=-1 → GET_FREE/SET_FREE) when in_field_init — field_init only has local 0 = `this` |
| CONSTRUCT base path | On field-init throw: rethrow pending + pop construct frame if still live |

## Measured

| Suite | Score | Notes |
|-------|------:|-------|
| **statements/class/elements** | **1351 pass / 107 fail / 8 t/o / 68 err** | runner pass% **92.7%** (pass/(pass+fail)); base was 1326 pass |
| elements delta vs base | **+25 fixed, 0 regressed** | free-var + abrupt instance fields |
| **statements/with** | **181/181 (100%)** | regression OK |
| **class/dstr** | 1860 pass + 60 batch `harness_eof` | sample 20/20 no-batch green; batch flake not real fail |
| free-var probe `f = x + 1` | pass | |

### Notable fixes (base → e7)

- literal-names family (after-same-line / multiple-definitions / …)
- `init-value-defined-after-class`, `init-value-incremental`, `init-err-evaluation`
- `fielddefinition-initializer-abrupt-completion` (+ super variant)
- several former timeouts → pass

### Residual (elements)

- private* bulk (~122)
- static computed propname constructor/prototype
- proxy field define observability
- eval/supercall-in-field edges
- `abrupt-completition-on-field-initializer` (static half of combined test)

## Next

L-B residual: static fields, private, then L-C subclass/super.

## M128e7al–am (2026-07-31)

- **e7al**: `delete` removes `__get_`/`__set_`; `UPDATE_ELEM` for `base[key]++` (single key eval, null base TypeError first). postfix/prefix ++/-- **100%**.
- **e7am**: `%` IEEE remainder edges + object ToNumeric — modulus **100%**.
- Prior: full BigInt (ops, relational, updates), sticky `__pend_exc__` fix.

## M128e7an (2026-07-31) — string const NUL + relational 100%

| Area | Change |
|------|--------|
| `JSComp__AddStringRaw` | Type **5** pool entry: `[len:8][bytes...][0]`; embedded `\u0000` preserved |
| `JSVM__LoadConst` type 5 | `JSRT_CreateStringUTF8Len` (UTF-8→UTF-16 + length; not Latin-1) |
| `JSRT_CreateString` | Thin wrapper over UTF8Len via `StringLength` |
| `JSRT_GreaterThan` | ToPrimitive L→R then `b < a` |
| `JSRT_LessEqual` / `GreaterEqual` | ToPrimitive L→R; **string** path via `StrCmp` (equal strings no longer fall through ToNumeric→NaN) |

### Measured (batch harness)

| Category | Score |
|----------|------:|
| less-than | **45/45 (100%)** |
| greater-than | **49/49 (100%)** |
| less-than-or-equal | **47/47 (100%)** |
| greater-than-or-equal | **43/43 (100%)** |
| modulus | **39/40 pass** (+1 harness_eof flake) |

Tip: string-const type5 + relational order/string-eq.

## M128e7ao (2026-07-31) — ** ToNumeric, escapes, Date(), MAX_VALUE parse

| Area | Change |
|------|--------|
| `JSRT_Exp` | ToNumeric for non-NUMBER (bool/null/…); no NumericBin stub → was ** undefined |
| Lexer string | `\b` `\f` `\v` single escapes |
| `DATE_CTOR` | `Date()` without new → string (`__new_target__` undefined); `new Date()` → object |
| `JSRT__ParseNumberStr` | scale `10^n` via float *10; apply exp as one mul (MAX_VALUE `1.797…e+308` finite) |

### Measured

| Category | Score |
|----------|------:|
| exponentiation | **44/44 (100%)** |
| addition / mul / div / sub / delete / updates | **100%** (prior rescore) |
| typeof | 13/16 (Date() string fixed; proxy/symbol/native-call residual) |
| literals/string | 67/73 |

Next: typeof residuals, string line-continuation/legacy-octal, numeric legacy octal.

## M128e7ap (2026-07-31) — typeof 100%

| Area | Change |
|------|--------|
| Object global | native `OBJ_CTOR` function (was plain object) |
| `Object(Symbol)` | box primitive Symbol → typeof `"object"` |
| Proxy | `__proxy_callable__` flag; `Proxy.revocable` + revoke |
| `typeof` Proxy | uses callable flag (survives revoke) |

### Measured

| Category | Score |
|----------|------:|
| typeof | **16/16 (100%)** |
| exponentiation | 100% |


## M128e7aq (2026-07-31) — legacy octal string escapes

Lexer: full LegacyOctalEscapeSequence `\0`-`\377` + NonOctalDecimal `\8`/`\9`.
literals/string **68/73** (was 67).

Residual: line-continuation CR/LS/PS, a few harness_eof / hex edge.

## M128e7ar (2026-07-31) — string LineContinuation LS/PS

Lexer LineContinuation: `\\` + LF/CR/CRLF/**LS/PS** (UTF-8 E2 80 A8/A9) → empty SV.
literals/string **70/73** (line-continuation double/single green).
Residual 3: batch `harness_eof` / sticky fail — **pass alone** on single+batch harness.
Updates postfix/prefix still **100%** (tip).

## M128e7as (2026-07-31) — numeric 100%

| Area | Change |
|------|--------|
| ParseNumberStr | Annex B legacy octal `0[0-7]+` base-8; `08`/`080` stay decimal |
| ParseNumberStr | unified significand for ≤15 digits (`1.1e-1 === 0.11`) |
| Parse NUMBER_LIT | strict mode rejects LegacyOctalIntegerLiteral |

### Measured

| Category | Score |
|----------|------:|
| literals/numeric | **157/157 (100%)** |
| exponentiation | still 100% |
