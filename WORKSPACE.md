# Workspace map

This monorepo is a **language + libraries** workspace. Apps exist to:

1. Prove the language and base libraries are approachable for real software
2. Give AOS (AILang OS / desktop stack) things users and developers can run
3. Produce concrete patterns useful as training data for humans and AI systems

CAD, the browser, games, CNC demos, etc. are **application proofs**, not the core product.
Shipping any one of them is optional; keeping the path from “hello world” → real app clear is not.

## Layout (target)

```
.
├── WORKSPACE.md              # this file — how to think about the tree
├── README.md                 # language overview, install, quick start
├── BUILD.md, CONTRIBUTING.md, LICENSE
│
├── ailang.x / analyzer.x     # shipped toolchain binaries (root)
├── Main.ailang, ailang_*.ailang, aimacro_*.ailang
│
├── Librarys/                 # THE product — stdlib + domain libraries
│   ├── Compiler/ Display/ Browser/ Cad/ Drivers/ Accel/ …
│   └── (import paths resolve from here — do not rename lightly)
│
├── docs/                     # ALL documentation (single tree)
│   ├── language/             # warts, guides, language-level notes
│   ├── compiler/             # compiler architecture
│   ├── display/              # Auckland / window system
│   ├── design/               # design notes and specs
│   ├── browser/              # JS engine plans and status
│   ├── cad/                  # CAD design (app work may live under CAD/)
│   ├── aos/                  # OS install, secure boot, emergency
│   ├── apps/                 # other app design notes
│   ├── plans/                # cross-cutting plans
│   └── archive/              # historical / sandbox / old prompts
│
├── dev/                      # developer tooling (not end-user product)
│   ├── compiler-regression/  # known-good programs for compiler debug (was TestCode/)
│   └── amdgpu/               # AMD GCN / SI driver bring-up kit
│       ├── tools/            # Python/shell probes, mmiotrace helpers
│       ├── notes/            # session handoffs, crash postmortems
│       ├── reference/        # ISA notes, scraped kernel docs
│       ├── fw_trace/         # firmware / init sequence extractors
│       └── traces/           # local dumps only (gitignored)
│
├── CAD/                      # CAD application sources (active app work)
├── Applications/             # desktop apps (IPC clients, tools)
├── OS/                       # AOS userspace (init, login, schema, …)
├── AiLang_CoreUtils/         # POSIX-style utilities in AILang
├── Demo Programs/            # language demos / teaching corpus
├── Programming_Manual/       # learning manuals (paths stable for now)
├── tools/                    # general repo tools (test runners, encoders)
├── tests/                    # conformance / integration suites
└── results/                  # large run outputs (should not be in git)
```

## Zones of work

| Goal | Touch | Put scratch in |
|------|--------|----------------|
| Language / stdlib | `Librarys/` (non-app), manuals, demos | `docs/language/`, temp only |
| App proof (e.g. CAD) | `CAD/` + its `Librarys/Cad/` + `docs/cad/` | app-local `build/`, screenshots — not repo root |
| AOS / desktop | `OS/`, `Main.ailang`, `Librarys/Display/`, `Applications/` | `docs/aos/` |
| Browser / JS | `Librarys/Browser/`, `docs/browser/`, `tools/*test262*` | `results/` (ignored) |
| Compiler debug / golden programs | `dev/compiler-regression/` (was `TestCode/`) | local `/tmp` binaries only |
| AMD GPU drivers | `Librarys/Accel/`, `Librarys/Drivers/AMDGPU/`, `dev/amdgpu/` | `dev/amdgpu/traces/` |

## What not to dump at repo root

- Compiled `*.x` (except intentional `ailang.x` / `analyzer.x`)
- Screenshots, mesh dumps, MMIO traces, VBIOS blobs
- One-off GPU probe scripts (use `dev/amdgpu/tools/`)
- Session handoff markdown (use `docs/…` or `dev/amdgpu/notes/`)

## Side projects as language proofing

C64, DnD, CNC, MediaCenter, LLM demos, etc. are welcome as long as they:

- Exercise libraries someone else might use
- Stay in their own folder (or under `Applications/` / `docs/apps/`)
- Do not spray build artifacts across the root

They are part of the **approachability + training-data** mission, not clutter by default.

## Related docs

- `docs/README.md` — documentation index
- `dev/amdgpu/README.md` — driver bring-up kit
- `README.md` — public language overview
