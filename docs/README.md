# Documentation index

Single home for written material. Prefer new docs under the folders below
instead of the repository root.

See also `WORKSPACE.md` at the repo root for the monorepo philosophy.

## Map

| Path | Contents |
|------|----------|
| `language/` | Language warts, programming guide notes, oddities |
| `compiler/` | Compiler architecture (frontend → emit → x86) |
| `display/` | Auckland UI / window system / input |
| `design/` | Design specs, compiler/display design history |
| `browser/` | JS engine master plan, conformance, usability plans |
| `cad/` | CAD kernel and app design (do not fight active CAD work) |
| `aos/` | OS install, LUKS/secure boot, sandbox/jail, firmware-on-disk, device UI, foreign-app porting |
| `apps/` | Other application design (MediaCenter, etc.) |
| `plans/` | Active cross-cutting work only (landed clipboard design is `display/CLIPBOARD_SERVICE.md`) |
| `archive/` | Historical sandboxes, old prompts, retired experiments |

## Still outside this tree (stable paths for now)

These learning/reference trees keep their historical names until a later rename pass:

- `Programming_Manual/` — step-by-step manuals
- `Library Manuals/` — per-library manpage-style docs
- `Language Docs BNF grammar etc/` — language spec / BNF / keywords
- `Demo Programs/` — runnable examples (training corpus)
- `Design-Language- Refrence/` — UI mockup PNGs

## Conventions

1. **Product docs** live under the matching product folder (`browser/`, `cad/`, …).
2. **Session handoffs** for GPU driver work go to `dev/amdgpu/notes/`, not here.
3. **Do not** leave new `*.md` plans at the repository root.
4. Prefer ASCII filenames without leading `#` when creating new files (legacy design notes still use messy names).
