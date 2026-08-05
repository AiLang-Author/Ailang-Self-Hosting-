# AIMacro Project

AIMacro is a Python-like surface syntax (`def` / `end` blocks) that transpiles to
AILang, backed by a dedicated runtime library. The long-term goal is dual execution:

1. **AOT (today):** `.aim` → `.ailang` → `ailang.x` → static native binary
2. **VM (target):** `.aim` → bytecode → `AIMacroVM` (modeled on `Library.JSVM`)

This directory is the **project hub** for specifications, objectives, test matrix,
and automation scripts. Implementation lives in `Librarys/AIMacro/` and
`AIMacro_Tests/`.

## Entry points (repo root)

| Binary / source | Role |
|-----------------|------|
| `aimacro.x` | Compiled CLI transpiler (~297 KB) |
| `aimacro_cli.ailang` | CLI: `./aimacro.x input.aim [output.ailang]` |
| `aimacro_console.ailang` | Interactive TUI console (lex/parse/codegen debug) |

There is no `aimacro.ailang` at repo root; use `aimacro_cli.ailang`.

## Documentation map

| Document | Contents |
|----------|----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full pipeline, library inventory, JSVM parallel |
| [SPECIFICATION.md](SPECIFICATION.md) | Language surface, builtins, codegen contracts |
| [OBJECTIVES.md](OBJECTIVES.md) | Phases, milestones, acceptance criteria |
| [TEST_MATRIX.md](TEST_MATRIX.md) | All 42 `.aim` tests by tier and status |
| [STATUS.md](STATUS.md) | Living scorecard (transpile / compile / run) |

## Quick commands

```bash
# Transpile one file
./aimacro.x AIMacro_Tests/aimacro_full_test.aim /tmp/out.ailang

# Transpile all tests (report only)
./AIMacro/scripts/run_transpile_all.sh

# Full pipeline for one test (transpile → compile → run)
./AIMacro/scripts/run_pipeline.sh AIMacro_Tests/test_harness.aim
```

## Branch

Active development for this initiative: **`aimacro/runtime-roadmap`**

## Related code

- `Librarys/AIMacro/` — lexer, parser, codegen, runtime builtins
- `AIMacro_Tests/` — 42 `.aim` regression and feature tests
- `Librarys/Browser/Library.JSVM.ailang` — reference VM architecture