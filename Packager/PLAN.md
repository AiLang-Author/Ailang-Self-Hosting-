# AILang Packager — TUI Application Plan

## Goal

Build a TUI application in AILang that scans a project directory, discovers build targets, executes builds, generates install scripts, and packs everything into a distributable package (zip). Application-agnostic — works with HalCode9000, the compiler, ATTN, or any AILang project. Later phases integrate with Olympus repo and git.

## Phase 1: Folder Mode (standalone TUI)

### Workflow

```
1. Launch packager, pick a directory (or pass as argv)
2. Scan: find .ailang sources, .x binaries, build.sh, config files, subdirs
3. Present file tree in TUI sidebar — user selects what to include
4. Define build graph: which .ailang files compile to which .x binaries, in what order
5. Build: execute build commands, show live output in tool blocks
6. Generate install.sh — scaffold from discovered layout, open in embedded editor for customization
7. Pack: zip selected files + install.sh + manifest into distributable archive
```

### TUI Layout (4-pane)

```
+-------------------+------------------------------------------+
| SIDEBAR           | MAIN                                     |
| (file tree)       | (package config / build output /          |
|                   |  install script editor)                  |
|                   |                                          |
+-------------------+------------------------------------------+
| DETAIL (status bar, progress, messages)                      |
+--------------------------------------------------------------+
| PROMPT (commands: [B]uild [P]ack [E]dit install [S]can [Q])  |
+--------------------------------------------------------------+
```

- **SIDEBAR** — `TUI_Tree` widget showing project file tree. Checkboxes for include/exclude. Dirty markers for modified files.
- **MAIN** — Context-dependent: package config form (TextBuffer fields), build output (TUI_Block), or embedded editor (Editor library) for install.sh.
- **DETAIL** — Status bar with package name, version, file count, total size.
- **PROMPT** — Single-key command bar. Mode indicator.

### Manifest: Package.ailang

```ailang
FixedPool.Package {
    "name":        Initialize="HalCode9000"
    "version":     Initialize="1.0.0"
    "description": Initialize="Native AILang chat client with 24 tool workers"
    "author":      Initialize="Sean Collins"
    "license":     Initialize="SCSL"
    "entry":       Initialize="HalCode9000.x"
}

FixedPool.PackBuild {
    "compiler":    Initialize="ailang.x"
    "build_script": Initialize="build.sh"
    "build_args":  Initialize=""
}

FixedPool.PackFiles {
    // Glob patterns for what goes in the package
    "include_bin":    Initialize="*.x"
    "include_src":    Initialize="*.ailang"
    "include_config": Initialize="*.json"
    "include_docs":   Initialize="*.md"
    "include_dirs":   Initialize="cc_tools,backends,skills,providers,docs"
    "exclude":        Initialize="nohup.out,*.log,*.bak,.git"
}

FixedPool.PackInstall {
    "install_dir":    Initialize="/usr/local/lib/halcode9000"
    "bin_dir":        Initialize="/usr/local/bin"
    "symlink_entry":  Initialize="true"
    "post_install":   Initialize="setup.sh"
}
```

The packager reads this natively — it's just AILang FixedPools parsed by the compiler's own frontend. No JSON/YAML parser needed.

### Files to Create

| File | Purpose |
|------|---------|
| `Packager.ailang` | Main entry, TUI init, event loop, mode dispatch |
| `Packager/Scan.ailang` | Directory scanner: walk tree, classify files, detect build scripts |
| `Packager/Build.ailang` | Build executor: parse build graph, fork+exec, capture output |
| `Packager/Pack.ailang` | Archive creator: collect files, generate manifest, create zip |
| `Packager/Install.ailang` | Install script generator: scaffold sh from PackInstall config |
| `Packager/UI.ailang` | TUI layout, pane management, widget wiring |
| `Packager/Manifest.ailang` | Read/write Package.ailang manifest files |

### Libraries Used

| Library | Usage |
|---------|-------|
| `Library.TUI` | Terminal init, raw mode, input, screen control |
| `Library.TuiWidget` | Panes, file tree, tool blocks, progress bar, status bar |
| `Library.TextBuffer` | Multi-field form editing (package name, version, etc.) |
| `Library.Editor` | Embedded editor for install.sh customization |
| `Library.Arena` | Memory management |
| `Library.StringUtils` | String ops |
| `Library.JSON` | cc_tools.json parsing, output manifest metadata |

### Scanner Logic

1. `opendir` + `readdir` via syscalls (or shell out to `find` with depth limit)
2. Classify each file:
   - `.ailang` → source (check for `SubRoutine.Main` → entry point)
   - `.x` → binary
   - `.sh` → script (check for `build` in name → build script)
   - `.json` → config
   - `.md` → docs
   - directories → recurse (respect .gitignore patterns from exclude list)
3. Build dependency detection:
   - Parse `LibraryImport` lines in .ailang files
   - Match source→binary pairs by name convention (e.g., `cc_read_ipc.ailang` → `cc_read_ipc.x`)
   - Detect build.sh and extract build commands

### Build Execution

1. If `build.sh` exists: fork+exec it, capture stdout/stderr into TUI_Block
2. If no build script: generate build commands from dependency graph
   - Compile each .ailang → .x using `ailang.x` from PATH
   - Respect ordering (libraries before consumers)
3. Show live output per-target using TUI_Block widgets (checkmark/X status icons)
4. Fail fast — stop on first error, show log path

### Install Script Generation

Scaffold `install.sh` from PackInstall config:
```sh
#!/usr/bin/env bash
set -euo pipefail
INSTALL_DIR="/usr/local/lib/halcode9000"
BIN_DIR="/usr/local/bin"
mkdir -p "$INSTALL_DIR" "$BIN_DIR"
cp -r . "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR"/*.x
ln -sf "$INSTALL_DIR/HalCode9000.x" "$BIN_DIR/halcode9000"
echo "Installed to $INSTALL_DIR"
```

Then open in the embedded Editor for the user to customize before packing.

### Pack Output

```
HalCode9000-1.0.0.zip
├── Package.ailang          (manifest)
├── install.sh              (generated + user-edited)
├── HalCode9000.x           (main binary)
├── cc_*.x                  (tool binaries)
├── cc_tools/               (tool sources)
├── backends/               (backend modules)
├── skills/                 (skill sheets)
├── providers/              (provider configs)
├── docs/                   (documentation)
├── *.ailang                (top-level sources)
├── *.json                  (config files)
└── *.md                    (docs)
```

## Phase 2: Git Integration

- Read `.git/config` for remote URL, current branch
- Read `git log` for version/changelog generation
- Detect dirty working tree — warn before packing
- Auto-tag on pack: `git tag v1.0.0`
- Generate CHANGELOG.md from commit messages between tags

## Phase 3: Olympus Integration

- Register package in Olympus repo via PostgreSQL driver
- Push artifact (zip) to Olympus blob storage (GUID flat files on disk)
- Query available packages: `SELECT name, version, description FROM packages`
- Dependency resolution: Olympus tracks which packages depend on which
- Pull + install from Olympus: download zip, run install.sh

## Design Principles

1. **Application-agnostic** — no HalCode-specific logic. Works on any project with .ailang files.
2. **Manifest is AILang** — Package.ailang is real AILang syntax. No new config format to learn.
3. **Editor-in-the-loop** — generated scripts go through the embedded editor before packing. Human always has final say.
4. **Progressive** — works standalone (Phase 1), then gains git awareness (Phase 2), then network distribution (Phase 3).
5. **Dogfoods the ecosystem** — uses TUI, TuiWidget, Editor, TextBuffer, Arena, JSON, PostgreSQL libraries. Proves the stack works for real applications.

## HalCode9000 as Test Case

First target: package HalCode9000 with this tool.
- 1 main binary (HalCode9000.x, ~500KB)
- 24 tool workers (cc_*.x, ~3.3MB total)
- 4 backend modules (backends/*.ailang)
- 24 skill sheets (skills/**/SKILL.md)
- 6 provider configs (providers/*.json)
- Build script, setup script, config files
- Total: ~3.8MB uncompressed, ~1.3MB zipped

If the packager can handle HalCode cleanly, it can handle anything in the ecosystem.
