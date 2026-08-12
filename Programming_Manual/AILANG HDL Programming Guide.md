# AILANG HDL Programming Guide

**Audience:** engineers writing AILang that compiles to netlist / chip  
**Backend design:** `docs/compiler/10_HDL_BACKEND.md`  
**Living doc** — update when the subset or errata change.

**Status:** 2026-08-11 · ModulesHDL v1 (+ arrays/ROM, While, user calls)

---

## 1. What you are writing

Regular **AILang**. No Verilog dialect, no `always`, no wires in source.

```bash
./ailang.x ailang_cli.ailang ailang_hdl.x          # rebuild CLI once
./ailang_hdl.x -hdl mychip.ailang out/mychip
# → out/mychip.v  +  out/mychip.nl.json
yosys -p 'read_verilog out/mychip.v; hierarchy -top ailang_top; proc; stat; check'
```

`-hdl` and `-kmod` are mutually exclusive.

---

## 2. Mental model

| Software AILang | Hardware (`-hdl`) |
|---|---|
| CPU grows / maps memory | Memory is **placed** at compile time |
| `FixedPool` | Registers / (later) ROM/BRAM |
| `DynamicPool` | **Illegal** |
| `Function` (pure) | Combinational module |
| `SubRoutine.Main` | Sequential region on **`ailang_top`** |
| `RunTask(Main)` | Clock domain on top (no empty task box) |
| `Branch` table pattern | **LUT / case ROM** (preferred) |
| Deep `IfCondition` chains | Avoid for multi-way; use `Branch` tables |
| `WhileLoop` | **One body iteration per clock** while cond true (multi-cycle) |

Slogan: **place memory, table the decisions, emit netlist.**

---

## 3. Patterns that work today

### FixedPool (state)

```ailang
FixedPool.App {
    "count": Initialize=0
    "limit": Initialize=42
    "mode":  Initialize=1
}
```

- Scalars become `output reg [63:0] App_count` (etc.) on `ailang_top`.
- Init values become reset / `initial`.
- Names are dotted idents in code: `App.count` (lexer may treat as one token).

### Combinational Function

```ailang
Function.Inc {
    Input: step: Integer
    Output: Integer
    Body: {
        ReturnValue(Add(step, 1))
    }
}
```

→ module with `assign result = step + …`.

### Sequential Main

```ailang
SubRoutine.Main {
    App.count = Add(App.count, 1)
}
RunTask(Main)
```

Body lowers into **`ailang_top`** `always @(posedge clk)` with `rst`.

### Multi-way → table (preferred)

```ailang
Branch App.mode {
    Case 0: { App.limit = 10 }
    Case 1: { App.limit = 20 }
    Case 2: { App.limit = 30 }
    Default: { App.limit = 0 }
}
```

**Rules for LUT form:**
- Each case body: **one** `target = constant`
- **Same** target in every case (and Default)
- Case keys must be **number literals**

If you need free-form multi-stmt cases, that is not table-lowered yet — restructure to a table or wait for growth.

### Arithmetic / compare (calls)

`Add`, `Subtract`, `Multiply`, `Divide`,  
`EqualTo`, `NotEqual`, `LessThan`, `GreaterThan`, `LessEqual`, `GreaterEqual`,  
`And`, `Or`, `Not`

### While (multi-cycle)

```ailang
WhileLoop LessThan(App.count, 8) {
    App.count = Inc(App.count)
}
```

- **Not** a software spin in zero time.
- Each `posedge clk`, if cond holds, body runs **once**.
- Prefer conditions that eventually go false (`LessThan(reg, K)`).
- Unbounded `WhileLoop True` will hang the machine every cycle forever — don't.

### User Function call

```ailang
App.count = Inc(App.count)
```

Define `Function.Inc` **before** the call site. Becomes a module instance.

---

## 4. Errata & “software vs `-hdl`” differences

| Topic | Software | `-hdl` today |
|---|---|---|
| **DynamicPool** | Grows (with limits) | **Hard error** |
| **MaximumLength / ElementType** | Used on FixedPool arrays | **Mostly ignored** by FixedPool member parser path — depth often stays **1**. Array→ROM not ready. Prefer scalar pools + `Branch` tables for now. |
| **LinkagePool attrs** | Full attr children | Not in HDL subset |
| **String `Initialize`** | OK | **Error** (no string heap on chip) |
| **PrintMessage / PrintNumber** | stdout | **No-ops** (ignored) |
| **User function calls** | Normal | **Instance hierarchy** — callee must appear **before** call site in the file; arity must match `Input:` ports; result via `result` port |
| **`Output: Integer`** | Type only | Becomes port **`result`** (fixed name) |
| **`IfCondition`** | Full control | Seq if markers; **do not** use for dense multi-way — use **`Branch`** |
| **While** | Spin in process | **1 iteration/clock** while cond; avoid unbounded true |
| **Syscalls / files / sockets** | OK | **Illegal** without IO binding (none yet) |
| **Main location** | Process entry | Sequential **netlist top**, not a software main |

Update this table whenever ModulesHDL gains a feature.

---

## 5. What to avoid

- Growing memory or pointer graphs with unbounded life  
- Long if/else ladders for decode → use **`Branch` + constants**  
- Expecting `MaximumLength-N` arrays to magically become BRAM today  
- Calling a Function before it is defined in the source file  
- Mixing `-hdl` with OS-facing libraries  

---

## 6. Smoke / dogfood

| File | Role |
|---|---|
| `dev/hdl_smoke.ailang` | Counter + Branch LUT + comb `Inc` |
| `docs/compiler/10_HDL_BACKEND.md` | Compiler architecture |

---

## 7. Changelog (user-facing)

| Date | Note |
|---|---|
| 2026-08-11 | Initial guide. FixedPool scalars, Function comb, Main seq, Branch→LUT. Errata: MaximumLength/arrays. |
| 2026-08-11 | User Function calls → module instances (define before use). |
| 2026-08-11 | WhileLoop → multi-cycle (one body iter per clock). Const index into pool arrays (depth>1) stub. |

*When you change the subset, append a row here and fix §3–§4.*
