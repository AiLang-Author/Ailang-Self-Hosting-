# AILang HDL — TechBlock (InlineAsm for gates)

**Status:** Implemented (escape hatch)  
**Philosophy:** build a **robust AILang→netlist core first**; treat vendor/technology cells like **InlineAsm** — not a second language.

---

## Why this shape

| Wrong approach | Right approach |
|---|---|
| Re-implement every FPGA primitive as AILang syntax | Core language lowers to portable prims / Yosys `$cells` |
| Dual-personality “HDL mode” dialect | Same AILang AST; rare escape when silicon needs a hard cell |
| Auto-magic Liberty import day one | Explicit `TechBlock["CELL", …]` — **you** own the contract |

Parallel to x86:

```ailang
// CPU escape
result = InlineAsm["POPCNT rax, rax"]

// Gate escape
result = TechBlock["HARD_AND2", a, b]
```

AILang will not invent timing, pin timing, or vendor semantics.  
Yosys / vendor techmap / your `.lib` owns that — same as the assembler owns opcodes.

---

## Syntax (v1)

```ailang
// Preferred — same bracket escape shape as InlineAsm
y = TechBlock["CELL_TYPE", in0, in1, ...]

// Also accepted (plain call form)
y = TechBlock("CELL_TYPE", in0, in1, ...)
```

| Piece | Rule |
|---|---|
| First arg | **String literal** cell/module type name |
| Remaining args | Input nets (max 8) |
| Result | Connected to port **`Y`** |
| Input ports | **`A`…`H`** in order |
| Core path | Prefer soft AILang (`BitwiseAnd`, `SoftAnd`, …) until silicon forces a hard cell |

Emitted Verilog:

```verilog
(* blackbox *)
module HARD_AND2 (
  input  [63:0] A, B, C, D, E, F, G, H,
  output [63:0] Y
);
endmodule

// in ailang_top:
HARD_AND2 tb_wN (
  .A(App_a),
  .B(App_b),
  .Y(wN)
);
```

Widths are 64-bit v1 (mask with `LowBits` if you need smaller).

---

## What you must provide

1. Real cell definition or Liberty / vendor techlib for P&R  
2. Correct use of ports (AILang will not rename ice40 `I0` for you in v1 — map in a thin wrapper cell or use A/B/Y wrappers)  
3. Timing constraints in `.sdc` / vendor tools  

Yosys `check` will keep blackboxes **opaque** (by design).

---

## What stays in core (do not use TechBlock for these)

Add/Sub/Mul, mux, LUT, ForEvery, Branch, LFSR/CRC soft-IP, streams, print —  
all **portable AILang**. Prefer core until a hard cell is forced by area/timing/IP.

---

## Roadmap (not day-one)

- Named port map: `TechBlock["SB_LUT4", I0=a, O=y]`  
- Width attributes per port  
- Auto-load of a `LibraryImport` tech pack that only registers blackbox names  
- Still **not** a full second HDL

---

## Dogfood

```bash
./ailang_hdl.x -hdl dev/hdl_techblock_smoke.ailang dev/hdl_tb_out
yosys -s dev/hdl_tb_out.ys
./dev/hdl_test_yosys.sh tech
```
