# Compiler regression suite

Formerly `TestCode/` — moved under `dev/` because these programs are **developer tooling**, not end-user product.

## Purpose

Known-good AILang programs used as **regression tests when debugging the compiler**.  
If a change breaks compile or run of these, treat it as a regression.

Sean’s note: these are programs that are expected to build and run; use them as a safety net after compiler work.

## Run a smoke pass

From the monorepo root:

```bash
./dev/compiler-regression/run_smoke.sh
# or a single file:
./ailang.x dev/compiler-regression/fizzbuzz.ailang -o /tmp/fizzbuzz.x && /tmp/fizzbuzz.x
```

`run_smoke.sh` compiles every `*.ailang` in this directory (not subdirs like `scratch code/` unless you pass `--all`). Failures print and continue; exit code is non-zero if any failed.

## Layout notes

| Path | Role |
|------|------|
| `*.ailang` (top level) | Primary regression corpus |
| `scratch code/` | Scratch / experimental — skipped by default smoke |

## Related

- `Demo Programs/` — teaching demos for people learning the language  
- `tests/` — large conformance (test262, WPT, …)  
- `dev/amdgpu/` — GPU driver bring-up kit  
