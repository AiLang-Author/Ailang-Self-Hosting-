# AILang HDL — Board Profile System (`ailang.board/v1`)

**Status:** v1 (JSON load at emit time)  
**Catalog:** [`boards/`](../../boards/)  
**Schemas:** [`boards/schema/`](../../boards/schema/)

---

## Why

There is **no industry-wide board I/O JSON**. Vendors ship CST / PCF / XDC / QSF — all different, all emit-only dialects.

AILang owns a **neutral profile**:

1. **Humans and models** author `board.json` once per board  
2. **Compiler** loads it at **HDL emit time**  
3. **Verify** design ports against resources  
4. **Emit** vendor constraints (`.cst` first; PCF/XDC next)

This is the pin equivalent of netlist IR: **data first, vendor text second**.

---

## Files

| Path | Role |
|---|---|
| `boards/catalog.json` | Index of all boards |
| `boards/<name>/board.json` | Profile (`ailang.board/v1`) |
| `boards/<name>/bind_*.json` | Design binding (`ailang.board.bind/v1`) |
| `Librarys/.../BoardProfileHDL.ailang` | Loader / verify / CST emit |
| `tools/board_profile_scaffold.py` | Scaffold for models/humans |

---

## CLI

```bash
# List catalog (prompt surface for humans & IDE)
./ailang_hdl.x -hdl --list-boards

# Compile with board + bind
./ailang_hdl.x -hdl \
  -board boards/tang_nano_9k/board.json \
  -bind  boards/tang_nano_9k/bind_blink.json \
  -period 37 \
  dev/hdl_tang_blink.ailang out/blink

# Artifacts include out/blink.cst when profile is gowin
```

Without `-board`, emit still succeeds; pin maps stay `UNASSIGNED` and the catalog is printed as a **prompt**.

Env (optional later): `AILANG_BOARD=boards/tang_nano_9k/board.json`

---

## Emit-time flow

```
Parse → Netlist IR
      → Write .v .nl.json .sdc .ys .pins
      → BoardProf_ApplyAtEmit(base)
            ├─ if no profile: ListCatalog (prompt)
            ├─ Verify ports vs bind/defaults
            └─ Emit .cst (gowin) from resources
```

---

## IDE / LSP / Analyzer

### Good insertion points

| Layer | Hook | What to do |
|---|---|---|
| **`ailang_lsp.x`** | After parse diagnostics | If workspace has `boards/` or `.ailang-board` pointer, load profile; emit diagnostics for unbound `FixedPool` fields used as top ports |
| **VS Code extension** | Command `ailang.selectBoard` | QuickPick from `catalog.json` → write `.vscode/ailang-board.json` or workspace setting; pass `-board` on HDL tasks |
| **Analyzer** | Optional HDL mode pass | Same verify rules as emit (width, missing bind) — edit-time, not only build-time |
| **vscode_ipc / IDE** | Project settings | Board id dropdown next to “Build HDL” |

### Recommended workspace pointer

```json
// .vscode/settings.json or .ailang/project.json
{
  "ailang.hdl.board": "boards/tang_nano_9k/board.json",
  "ailang.hdl.bind": "boards/tang_nano_9k/bind_blink.json"
}
```

Extension runs:

```text
ailang_hdl.x -hdl -board <board> -bind <bind> ${file} ${out}
```

LSP can re-run a **light** `BoardProf_Verify` over AST pool names without full netlist (name match only), then full verify on build.

### Why not only LSP?

Pin verification needs **top ports after HDL lower** for truth. LSP gives early UX; **emit-time load is authoritative**.

---

## Schema sketch (board)

```json
{
  "schema": "ailang.board/v1",
  "name": "tang_nano_9k",
  "vendor": "gowin",
  "device": { "part": "...", "family": "...", "loader_board": "tangnano9k" },
  "clocks": { "clk27": { "hz": 27000000, "pin": "52" } },
  "resources": {
    "led": { "dir": "out", "width": 6, "pins": ["10","11","13","14","15","16"], "invert": true }
  },
  "defaults": { "clk": "clk27", "rst": { "tie": 0 } }
}
```

## Schema sketch (bind)

```json
{
  "schema": "ailang.board.bind/v1",
  "board": "tang_nano_9k",
  "bind": {
    "clk": "clk27",
    "Board_led": { "resource": "led", "bits": "5:0" },
    "Board_div": null
  }
}
```

Port names use **Verilog-safe** ids (`Board_led`), matching ModulesHDL emit.

---

## Models

1. Read `boards/schema/ailang.board.v1.schema.json`  
2. Read a schematic / pin table  
3. Emit `boards/<name>/board.json`  
4. Append `catalog.json`  
5. Optional: `python3 tools/board_profile_scaffold.py --name ...`

No Verilog required to add a board.

---

## Roadmap

| Done | Next |
|---|---|
| JSON schema + catalog + Tang Nano pack | PCF/XDC from same profile |
| Load / list / verify / CST emit | Auto-period from `clocks.hz` into SDC |
| CLI `-board` `-bind` `--list-boards` | VS Code QuickPick + LSP diagnostics |
| | Invert-aware top_wrap generator |
| | Strict policy: unbound_out=error fails compile |

---

## Philosophy

Same as TechBlock and netlist IR:

> **Own the intermediate. Dump vendor formats. Don’t make the user learn five pin dialects.**
