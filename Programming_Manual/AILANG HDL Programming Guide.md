# AILANG HDL Programming Guide

**Audience:** engineers writing AILang that compiles to netlist / chip  
**Backend design:** `docs/compiler/10_HDL_BACKEND.md`  
**Living doc** — update when the subset or errata change.

**Status:** 2026-08-11 · ModulesHDL v1 (skid template + multi-driver coalesce)

---

## 1. What you are writing

Regular **AILang**. No Verilog dialect, no `always`, no wires in source.

```bash
./ailang.x ailang_cli.ailang ailang_hdl.x          # rebuild CLI once
./ailang_hdl.x -hdl mychip.ailang out/mychip
# → out/mychip.v .nl.json .sdc .ys .pins
#    out/mychip.blif is written when you run: yosys -s out/mychip.ys
yosys -s out/mychip.ys
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
    "table": ElementType-Integer, MaximumLength-4, Initialize=7
}
```

- Scalars → `output reg [63:0] App_count` on `ailang_top`.
- Arrays → internal `reg [W-1:0] App_table [0:N-1]`, filled with `Initialize` (ROM default).
- Const read: `App.limit = App.table[2]`
- Dash or equals attrs: `MaximumLength-4` or `MaximumLength=4`

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

### Streams (ready/valid naming)

```ailang
FixedPool.Stream {
    "in_data": Initialize=0
    "in_valid": Initialize=0
    "in_ready": Initialize=1
    "out_data": Initialize=0
    "out_valid": Initialize=0
    "out_ready": Initialize=0
}
```

| Field | Direction |
|---|---|
| `in_data`, `in_valid` | input (host → chip) |
| `in_ready` | **output** (we accept) |
| `out_data`, `out_valid` | output (chip → host) |
| `out_ready` | **input** (sink accepts) |

**Fire condition** (one beat per clock when both sides ready):

```ailang
Stream.in_ready = 1
IfCondition EqualTo(And(Stream.in_valid, Stream.in_ready), 1) ThenBlock: {
    Stream.out_data = Stream.in_data
    Stream.out_valid = 1
} ElseBlock: {
    Stream.out_valid = 0
}
```

**Skid (1-deep hold)** — copy `dev/hdl_templates/stream_skid_1deep.ailang`  
(or the Stream/Skid section of `dev/hdl_smoke.ailang`).

Rules of thumb:
- `in_ready` low when skid full and sink not ready  
- `out_valid` / `out_data` mirror skid  
- Load skid on `in_valid && in_ready`; clear on `out_valid && out_ready`

### Artifacts

| File | Role |
|---|---|
| `.v` | structural Verilog |
| `.nl.json` | netlist graph dump |
| `.sdc` | clock / I/O delay stubs |
| `.ys` | Yosys script (check + `write_blif`) |
| `.pins` | port list for board pin binding |
| `.blif` | produced by `yosys -s *.ys` |

### Variable array index

```ailang
App.limit = App.table[App.mode]
```

### If both arms are constants → 2-entry LUT

```ailang
IfCondition EqualTo(App.mode, 0) ThenBlock: {
    App.count = 100
} ElseBlock: {
    App.count = 200
}
```

---

## 4. Errata & “software vs `-hdl`” differences

| Topic | Software | `-hdl` today |
|---|---|---|
| **DynamicPool** | Grows (with limits) | **Hard error** |
| **MaximumLength / ElementType** | Array constraints | **Supported** (dash or `=`): `MaximumLength-N`, `ElementType-Integer\|Byte\|Address`. Cap 4096. Becomes `reg [W-1:0] name [0:N-1]` ROM-style fill from `Initialize`. |
| **Index `pool[i]`** | Runtime index | **Const or variable**: `App.table[2]`, `App.table[App.mode]` (async read) |
| **Stream ports** | sockets/files | Name convention: `in_data`/`in_valid` → inputs; `in_ready` → output; `out_data`/`out_valid` → outputs; `out_ready` → input |
| **LinkagePool attrs** | Full attr children | Not in HDL subset |
| **String `Initialize`** | OK | **Error** (no string heap on chip) |
| **PrintMessage / PrintNumber** | stdout | **No-ops** (ignored) |
| **User function calls** | Normal | **Instance hierarchy** — callee must appear **before** call site in the file; arity must match `Input:` ports; result via `result` port |
| **`Output: Integer`** | Type only | Becomes port **`result`** (fixed name) |
| **`IfCondition`** | Full control | Seq if markers; **do not** use for dense multi-way — use **`Branch`** |
| **While** | Spin in process | **1 iteration/clock** while cond; avoid unbounded true |
| **Syscalls / files / sockets** | OK | **Illegal** without IO binding (none yet) |
| **Main location** | Process entry | Sequential **netlist top**, not a software main |
| **Multi-write same reg** | Last store wins in SW too | Uncond seq multi-driver: **warn + keep last**; exclusive updates under `If`/`Branch` |

Update this table whenever ModulesHDL gains a feature.

---

## 5. What to avoid

- Growing memory or pointer graphs with unbounded life  
- Long if/else ladders for decode → use **`Branch` + constants**  
- **Multiple unconditional writes to the same reg in Main** — you'll see `[HDL] warn: multi-driver seq`  
- Calling a Function before it is defined in the source file  
- Mixing `-hdl` with OS-facing libraries  

---

## 6. Smoke / dogfood

| File | Role |
|---|---|
| `dev/hdl_smoke.ailang` | Dogfood: Inc, ROM index, if-LUT, skid stream |
| `dev/hdl_templates/` | Copy-paste chips (skid stream) |
| `docs/compiler/10_HDL_BACKEND.md` | Compiler architecture |
| `claude-memory/project_ailang_hdl.md` | Agent notes / grind priorities |

---

## 7. Changelog (user-facing)

| Date | Note |
|---|---|
| 2026-08-11 | Initial guide. FixedPool scalars, Function comb, Main seq, Branch→LUT. Errata: MaximumLength/arrays. |
| 2026-08-11 | User Function calls → module instances (define before use). |
| 2026-08-11 | WhileLoop → multi-cycle (one body iter per clock). |
| 2026-08-11 | MaximumLength/ElementType parse; array ROM fabric; const index `pool[i]`. |
| 2026-08-11 | Variable index; stream in_/out_ ports; If const-arms → 2-entry LUT. |
| 2026-08-11 | Sidecars `.sdc` + `.ys`; skip empty modules; stream fire = valid∧ready. |
| 2026-08-11 | `.pins` pin map; `.ys` writes `.blif`; skid+FSM stream smoke. |
| 2026-08-11 | Multi-driver seq coalesce+warn; `dev/hdl_templates/stream_skid_1deep`. |

*When you change the subset, append a row here and fix §3–§4.*
