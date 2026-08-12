# AILang Compiler — 10: HDL / Netlist Backend

**Status:** Active development (ModulesHDL)  
**CLI:** `./ailang.x -hdl <source.ailang> [base_path]`  
**Artifacts:** `<base>.v` (structural Verilog), `<base>.nl.json` (graph dump)  
**Consumers:** Yosys, vendor flows that accept structural Verilog / gate netlists  
**User guide (errata / how to write sources):** [`Programming_Manual/AILANG HDL Programming Guide.md`](../../Programming_Manual/AILANG%20HDL%20Programming%20Guide.md)

---

## 1. Purpose

Compile **regular AILang** into a **circuit description** (netlist), not machine code.

| Target family | Object code | Modules |
|---|---|---|
| x86 / future ISA | Bytes + ELF | `Compile/Modules`, `CodeEmit` |
| **HDL / netlist** | Cells, nets, memories, LUTs | **`Compile/ModulesHDL` only** |

There is **no separate HDL dialect**. Same lexer, parser, AST. Different generators after the frontend. HDLs that restate algorithms as wires and sensitivity lists are rejected as a product shape.

### Product slogan

> AILang does not grow memory. It places memory.  
> Hardware is the target where that stops being a metaphor.

---

## 2. Design principles

1. **Same source language** — FixedPool, Function, SubRoutine, Branch, arithmetic calls, etc.
2. **Fork at compile modules** — Never dual-personality the x86 modules with `if hdl`.
3. **Netlist is object code** — Verilog/JSON are serializers of an IR graph.
4. **Bounded resources** — FixedPool is legal; unbounded DynamicPool is illegal.
5. **Tables over if-chains** — Multi-way decisions prefer **LUT / matrix / case ROM** over deep nested conditionals (area, timing, and human sanity).
6. **Grow the subset** — Hard error or explicit skip for unsupported constructs; do not silently invent semantics.
7. **Do not break the main compiler** — All generation lives under `ModulesHDL/`.

---

## 3. Pipeline

```
Source.ailang
      │
      ▼
  Frontend (shared)
  Lex → Parse → AST  [optional Sem]
      │
      ▼  -hdl branch in ailang_cli (after semantics)
  CompileHDL_Program
      │
      ├─ Pass 1: Discover Function / SubRoutine shells
      ├─ Pass 2: Generate
      │     FixedPool  → memories + top ports
      │     Function   → comb module + body lower
      │     SubRoutine → module; Main body → ailang_top (seq)
      │     RunTask    → clocked region note / task shell
      │     Branch     → LUT table when pattern matches
      └─ Pass 3: Serialize
            EmitVerilogHDL  → .v
            EmitJsonHDL     → .nl.json
      │
      ▼
  Yosys / Libero / …  (place, route, bitstream)
```

x86 path is untouched when `-hdl` is set: no `Emit_Init`, no ELF.

---

## 4. File map

```
Librarys/Compiler/Compile/ModulesHDL/
├── Library.CCompileMainHDL.ailang   — dispatcher, CLI entry API
├── Library.NetlistIRHDL.ailang      — IR: modules, cells, nets, memories, LUTs, assigns
├── Library.CCompilePoolHDL.ailang   — FixedPool → reg/mem + top output ports
├── Library.CCompileExprHDL.ailang   — expr → nets / binop cells
├── Library.CCompileStmtHDL.ailang   — stmt → assigns; Branch → LUT
├── Library.CCompileFuncHDL.ailang   — Function / SubRoutine / RunTask
├── Library.EmitVerilogHDL.ailang    — structural Verilog
└── Library.EmitJsonHDL.ailang       — JSON graph (Library.JSON)

docs/compiler/10_HDL_BACKEND.md      — this document
dev/hdl_smoke.ailang                 — dogfood smoke source
```

Import path: `LibraryImport.Compiler.Compile.ModulesHDL.CCompileMainHDL`

---

## 5. Netlist IR (object code)

### 5.1 Module

| Field | Role |
|---|---|
| name, kind | top / func / sub / task |
| ports | clk, rst, params, pool outs, result |
| cells | const, add/sub/mul, dff stub, instance, … |
| nets | named wires |
| memories | FixedPool fields |
| assigns | comb `assign` or seq `<=` |
| **luts** | **solution tables (preferred multi-way)** |

### 5.2 Storage mapping

| AILang | Hardware |
|---|---|
| `FixedPool.P { "f": Initialize=N }` | `reg` / `output reg` on `ailang_top` |
| `FixedPool` array `MaximumLength-K` | memory array / ROM candidate |
| `DynamicPool` | **illegal** (cannot grow on silicon) |
| Function params | `input` ports |
| `Output: Integer` | `output` `result` (comb assign) |

### 5.3 Control mapping

| AILang | Hardware |
|---|---|
| Pure `Function` body | Combinational cloud in its module |
| `SubRoutine.Main` body | Sequential region on **`ailang_top`** (shares pool regs) |
| `RunTask` | Clocked process anchor (task shell; body may live on top) |
| `Add` / `Subtract` / … | Binop cells → `assign w = a + b` |
| **`Branch` (const table pattern)** | **LUT / `case` ROM** |
| Free-form `IfCondition` | Seq if markers (avoid for dense multi-way) |

### 5.4 LUT / matrix philosophy

Complex decision logic should be:

```
address = f(conditions)     // pack X, Y, mode bits
solution = TABLE[address]   // flat or 2D-row-major
```

not:

```
if c0 then if c1 then if c2 …   // wasteful, hard to verify
```

IR API (NetlistIRHDL):

- `NL_CreateLut(mod, name, addr_bits, data_bits)`
- `NL_LutSetEntry(lut, index, value)`
- `NL_LutBindAddr(lut, addr_net)` → out net
- `NL_CreateMatrixLut(mod, name, rows, cols, data_bits, values)` — 2D flatten

Emit: `always @(*) case (addr) … endcase` (Yosys → `$pmux` / ROM / LUT fabric).

**Branch → LUT** when every case is `target = constant` to the **same** target (optional Default). Otherwise error (do not silently emit a 400-deep if chain).

---

## 6. ABI / implementation notes

- **Call arity:** Prefer ≤6 formal inputs per function (register ABI). Extra fields via setters (`NL_MemorySetMeta`, `NL_CellSetOps`).
- **Dotted names:** Lexer may emit `App.count` as one `IDENTIFIER` (dotted ident), not always `MEMBER_ACCESS`.
- **Const extract:** Success is not the integer value (0 is valid). Use `NL.extract_val` + return 1/0.
- **Pool visibility:** FixedPool scalars are **`output reg`** on `ailang_top` so synth keeps them under DCE.

---

## 7. CLI

```bash
# Build compiler with ModulesHDL linked (once)
./ailang.x ailang_cli.ailang ailang_hdl.x

# Emit netlist
./ailang_hdl.x -hdl prog.ailang out/chip
# → out/chip.v , out/chip.nl.json

# Open tool loop
yosys -p 'read_verilog out/chip.v; hierarchy -top ailang_top; proc; stat; check'
```

Flags: `-hdl` / `--hdl`. Mutually exclusive with `-kmod`. Default base path: `a.nl`.

---

## 8. Legal subset (current)

### Supported

- FixedPool scalars (+ top ports)
- Function / SubRoutine / RunTask
- Numbers, idents, pool fields
- Calls: `Add`, `Subtract`, `Multiply`, `Divide`, compares, `And`/`Or`/`Not`
- Assignment, `ReturnValue`, simple `If`/`Fork` markers
- **Branch → LUT** (const table pattern)
- **User Function calls** → hierarchical instance (define before use; arity match)
- **WhileLoop** → one body iteration per clock while condition holds
- **MaximumLength / ElementType** on FixedPool members (array ROM fabric)
- Const index `pool[N]` into arrays
- Ignore: `PrintMessage` / `PrintNumber` (no console on chip)

### Not yet / rejected

- DynamicPool and growth
- Recursive / mutual calls; multi-output Functions
- Unbounded while-true busy loops (legal syntax, bad design)
- String pool inits
- Non-const array indices
- Full behavioral scheduling / multi-cycle FSM inference beyond 1-iter while
- Vendor primitive black boxes (BRAM/DSP) — planned escape hatch

---

## 9. Growth roadmap

| Phase | Goal |
|---|---|
| **Done** | ModulesHDL seam, FixedPool, body lower, Branch LUT, Yosys smoke |
| **Done** | Empty `task_Main` noise removed; pool scalars as top `output reg` |
| **Done** | User Function call → module instance |
| **Done** | WhileLoop multi-cycle (1 iter/clock) |
| **Done** | MaximumLength/ElementType → array/ROM; const index |
| **Next** | 2D matrix dogfood; ready/valid IO; non-const index (registered) |
| **Then** | richer FSM; techmap / SDC / BLIF |

Always: **table-shaped control first**, free-form control only when necessary.

---

## 10. Relationship to synthesis / P&R

```
AILang  ──►  netlist IR  ──►  structural Verilog
                                  │
                                  ▼
                         Yosys / vendor synth
                                  │
                                  ▼
                              gate netlist
                                  │
                                  ▼
                         nextpnr / Libero P&R / …
```

Netlist is the **semantic** bottom tier before physics. Structural Verilog is the **interop** coin. We may later emit BLIF or mapped cells; IR stays stable.

---

## 11. Testing

| Smoke | Path |
|---|---|
| Source | `dev/hdl_smoke.ailang` |
| Rebuild CLI | `./ailang.x ailang_cli.ailang ailang_hdl.x` |
| Emit | `./ailang_hdl.x -hdl dev/hdl_smoke.ailang dev/hdl_smoke_out` |
| Yosys | `hierarchy -top ailang_top; proc; stat; check` |

Expect: `$add`, `$dff`, `$pmux` (from LUT case), **0 problems**.

---

## 12. Non-goals

- Competing Verilog/VHDL syntax
- Editing x86 `Compile/Modules/*` for hardware
- Full HLS fantasy (auto-pipeline everything) in v1
- OS syscalls on silicon without explicit IO binding

---

## 13. Entry API (for drivers)

```
CompileHDL_Init()
CompileHDL_Program(ast) → Integer
CompileHDL_WriteVerilog(path)
CompileHDL_WriteJson(path)
CompileHDL_ProgramToFiles(ast, base_path)
CompileHDL_PrintStats()
CompileHDL_Free()
```

---

*AILang HDL backend — netlist as native output, tables as preferred logic, FixedPool as placed memory.*
