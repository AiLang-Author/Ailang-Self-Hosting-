# AILang HDL — Language coverage matrix

**Status:** living document (ModulesHDL)  
**Companion:** [10_HDL_BACKEND.md](10_HDL_BACKEND.md)

## How much can we support?

AILang is **not** Verilog. The bet is: **structured keywords + clean AST → boring lowerings**.  
Coverage is not “every string the lexer knows”; it is every construct that has **placeable hardware meaning**.

Rough size of the full language surface (frontend today):

| Layer | Count (approx) | Notes |
|---|---|---|
| Lexer keywords | ~50–80 (shorthand VS Code set is the ergonomic 50) | Control, pools, types, loops |
| AST node kinds | ~250+ constants | Many are types/ops/OS I/O, not “syntax forms” |
| Builtin call names (x86 modules) | ~100+ | Arith, string, file, socket, … |

**Ultimately on HDL**, a realistic ceiling:

| Tier | Share of *useful chip programs* | What fits |
|---|---|---|
| **A — Core** | ~80% | FixedPool, Function, Main, arith/bitwise/compare, If/Branch/While/Until, print channel, streams |
| **B — Solid** | +15% | Arrays R/W, Min/Max/Clamp/Abs, LUTs, hierarchy, multi-job I/O, board sidecars |
| **C — Stretch** | +5% | Bounded ForEvery, soft FSMs, vendor BRAM/DSP escapes |
| **Never (or rare black box)** | — | DynamicPool growth, sockets, files, GC strings, unbounded actors, OS syscalls |

So: **dozens of keywords + a few dozen builtins**, not hundreds of OS APIs.  
The long tail of AST ops (file/hash/socket) stays software-only; that is a feature, not a bug.

### Rule of thumb

> If the construct **places finite state or pure logic**, it belongs on the chip.  
> If it **grows, blocks on the OS, or needs a heap**, it does not.

---

## Matrix (ModulesHDL)

### Legend

| Symbol | Meaning |
|---|---|
| **Y** | Supported (lowers to netlist) |
| **P** | Partial / best-effort |
| **N** | Rejected or illegal for silicon |
| **—** | N/A / software-only |

### Declarations

| Construct | HDL | Notes |
|---|---|---|
| `FixedPool` | **Y** | Scalars + `MaximumLength` arrays |
| `DynamicPool` | **N** | Cannot grow on die |
| Other pool kinds | **N** | Temporal/Neural/… rejected |
| `Function` | **Y** | Comb module + `result` |
| `SubRoutine` / `Main` | **Y** | Seq region on top |
| `RunTask` | **Y** | Clock domain anchor |
| `Inline` / lambda / curry | **N** | Not yet |

### Statements

| Construct | HDL | Notes |
|---|---|---|
| Assignment | **Y** | Comb or seq |
| `pool[i] = expr` | **Y** | INDEX_ASSIGN → seq mem write |
| `ReturnValue` | **Y** | Comb `result` |
| `IfCondition` / `Fork` | **Y** | LUT / mux / seq if |
| `Branch` / case table | **Y** | LUT preferred |
| `WhileLoop` | **Y** | 1 body iter / clock |
| `UntilCondition` | **Y** | While Not(C) |
| `ExitLoop` / `ContinueLoop` | **P** | Noted; prefer bounded loops |
| `ForEvery` | **N** | Next: bounded FixedPool only |
| `PrintMessage` / `PrintNumber` | **Y** | ROM + multi-job itoa |
| Try/Catch/Throw | **N** | No exception fabric v1 |

### Expressions / builtins

| Construct | HDL | Yosys meet |
|---|---|---|
| Number / Bool / Null | **Y** | const |
| Idents / pool fields | **Y** | wires / regs |
| `pool[i]` read | **Y** | mem read |
| Add/Sub/Mul/Div/Modulo | **Y** | `$add`… |
| Bitwise* / Shift* | **Y** | `$and` `$xor` `$shl`… |
| Compares | **Y** | `$eq` `$lt`… |
| And/Or/Not (logic) | **Y** | `$logic_*` |
| Increment / Decrement | **Y** | ±1 |
| AbsoluteValue / Min / Max / Clamp | **Y** | mux structure |
| User Function call | **Y** | instance |
| Strings (runtime) | **N** | Only print literals → ROM |
| File/socket/hash/… | **—** | Host software |

### Tooling

| Artifact | Status |
|---|---|
| `.v` `.nl.json` | **Y** |
| `.sdc` `-period` | **Y** |
| `.pins` `.pcf` `.xdc` | **Y** |
| `.ys` + `synth_ice40/ecp5/xilinx` | **Y** |
| BLIF via yosys | **Y** |

---

## Growth order (product)

1. Finish **B**: ForEvery over FixedPool, cleaner multi-driver under deep If  
2. Interleaved print event queue (ROM + itoa mixed)  
3. Vendor DSP/`$mul` policy; true BRAM ports if Liberty/techmap needs them  
4. Keep rejecting growth/OS — that is the language selling point  

**Keywords we can “ultimately” support well:** roughly the **structured control + pool + arith** surface (~**60–100** named constructs and builtins that matter for chips).  
**Not** every AST leaf that exists for self-hosting the OS and browser.
