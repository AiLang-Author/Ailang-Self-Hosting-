# AIMacro Status Scorecard

Living document. Re-run audit scripts and update counts after substantive changes.

**Last updated:** 2026-06-09 (M0 bootstrap — docs + branch; audit pending)

## Build artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Transpiler CLI | `aimacro.x` | Present (~297 KB) |
| AILang runtime | `ailang.x` | Assumed present at repo root |
| Sources | `aimacro_cli.ailang`, `aimacro_console.ailang` | Present |

## Phase gate

| Gate | Target | Current |
|------|--------|---------|
| M0 — Project docs + branch | Complete | In progress |
| M1 — P0 transpile | 100% | Not audited |
| M2 — P0 compile + run | ≥95% | Not audited |
| M3 — P1 coverage | Roadmap | Not started |
| M4 — AIMacroVM design lock | SPEC §VM | Draft in SPECIFICATION.md |
| M5 — VM prototype | JSVM parity sketch | Not started |
| M6 — Dual-mode (AOT + VM) | Optional | Not started |

## P0 test matrix (fill after audit)

| Category | Total | Transpile OK | Compile OK | Run OK |
|----------|-------|--------------|------------|--------|
| Core (listed in TEST_MATRIX P0) | ~28 | — | — | — |
| P1 | ~18 | — | — | — |
| P2 | ~4+ | — | — | — |

## Known gaps (from prior investigation)

- Scrollbar / UI: unrelated to AIMacro; see Auckland WIP on `master`.
- `aimacro.ailang` does not exist; entry is `aimacro_cli.ailang`.
- HalCode9000 MCP: separate project under `Applications/HalCode9000/`.
- Runtime `open()` and some stdlib modules may be partial — verify per `aimacro_feature_probe.aim`.

## Next audit

```bash
./AIMacro/scripts/run_transpile_all.sh 2>&1 | tee AIMacro/artifacts/transpile_audit.log
```

Create `AIMacro/artifacts/` if missing; add `*.log` to local gitignore only if user requests.

## Decision log

| Date | Decision |
|------|----------|
| 2026-06-09 | Branch `aimacro/runtime-roadmap`; docs under `AIMacro/`; VM modeled on `Library.JSVM.ailang`. |