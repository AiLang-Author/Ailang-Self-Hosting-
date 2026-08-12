# AILang HDL — Language coverage matrix

**Status:** living document (ModulesHDL)  
**Companion:** [10_HDL_BACKEND.md](10_HDL_BACKEND.md)

## Practical limit (the real answer)

AILang’s full surface is large (~250 AST kinds, host I/O, actors).  
**HDL core is intentionally smaller** — whatever has *finite, placeable* meaning.

| Band | Approx size | Contents |
|---|---|---|
| **Core (aim to finish)** | **~40–55 constructs** | Pools, functions, control, arith/bit, arrays, print, streams |
| **Solid extensions** | **+10–20** | ForEvery, bit helpers, power/rotate, board sidecars |
| **Stretch** | **+handful** | Tech-block libraries, DSP escapes, interleaved print |
| **Never / rare black box** | rest | Dynamic growth, files, sockets, GC strings, OS |

**Rule:** finite state or pure logic → chip. Grow / block / heap → software.

You do **not** need “all keywords.” You need the **core band** complete and greppable.  
That is the practical limit — and it is already most of what a soft-CPU-free datapath needs.

---

## Matrix (ModulesHDL)

### Legend

| Symbol | Meaning |
|---|---|
| **Y** | Supported |
| **P** | Partial |
| **N** | Rejected / not silicon |
| **—** | Software-only |

### Declarations

| Construct | HDL | Notes |
|---|---|---|
| `FixedPool` | **Y** | Scalars + arrays |
| `DynamicPool` | **N** | Illegal |
| Other pools | **N** | Rejected |
| `Function` | **Y** | Comb + `result` |
| `SubRoutine` / `Main` | **Y** | Seq top |
| `RunTask` | **Y** | Clock domain |
| Inline / lambda | **N** | |

### Statements

| Construct | HDL | Notes |
|---|---|---|
| Assignment | **Y** | |
| `pool[i] = expr` | **Y** | |
| `ReturnValue` | **Y** | |
| `IfCondition` / `Fork` | **Y** | LUT / mux / seq |
| `Branch` | **Y** | LUT table |
| `WhileLoop` | **Y** | 1 iter/clock |
| `UntilCondition` | **Y** | inverted while |
| `ForEvery` | **Y** | Unroll ≤32 + shadow reduce |
| `ExitLoop` / `ContinueLoop` | **P** | noted no-ops |
| `PrintMessage` / `PrintNumber` | **Y** | ROM + multi-job itoa |
| `Halt` | **P** | ignored on silicon |
| Try/Catch | **N** | |

### Expressions / builtins (core)

| Family | Names | HDL |
|---|---|---|
| Literals | number, bool, null | **Y** |
| Names | idents, pool fields, `pool[i]` | **Y** |
| Arith | Add Sub Mul Div Modulo Negate Increment Decrement | **Y** |
| Power | Power / OP_POWER | **Y** const exp 0..8 only |
| Bitwise | BitwiseAnd/Or/Xor/Not, Xor, shifts | **Y** |
| Rotate | RotateLeft/Right | **Y** const dist 0..63 |
| Bits | BitTest BitSet BitClear LowBits | **Y** const bit/width |
| Predicates | IsZero IsNonZero | **Y** |
| Compare | EqualTo NotEqual Less* Greater* | **Y** |
| Logic | And Or Not | **Y** `$logic_*` |
| Structure | AbsoluteValue Min Max Clamp Select | **Y** mux |
| Calls | user Function | **Y** instance |
| AST binary ops | + − * / % & \| ^ << >> && \|\| | **Y** |
| Strings / files / net | — | **N** / **—** |

### Tooling

| Artifact | Status |
|---|---|
| `.v` `.nl.json` `.sdc` `.ys` | **Y** |
| `.pins` `.pcf` `.xdc` | **Y** |
| synth_ice40/ecp5/xilinx | **Y** |
| `dev/hdl_test_yosys.sh` | **Y** |

---

## Dogfood + stress

```bash
./dev/hdl_test_yosys.sh
./dev/hdl_test_yosys.sh stress
./dev/hdl_test_yosys.sh core logic
```

| Suite | What it stresses |
|---|---|
| `core` / `logic` | Core syntax without host I/O noise |
| `stress_bits` | BitSet/Clear/Test, rotate, Power, fat exprs |
| `stress_array` | ForEvery depth 32, var index R/W |
| `stress_nested` | Nested ForEvery, F1→F2→F3, nested If, Branch |
| `stress_branch` | Dense Branch table, While/Until, multi-stmt If |

**Semantics note:** straight-line pool updates use a **comb shadow chain** so  
`x = BitSet(x,0); x = BitSet(x,1)` accumulates (not NBA last-wins).

---

## Still outside core (by design for now)

1. **Technology block `LibraryImport`** — vendor cells as libraries (not today)  
2. Interleaved print events (ROM mid-stream with itoa)  
3. ForEvery depth > 32 (use index While)  
4. Runtime-variable Power / Rotate distance  
5. DSP black-box policy  

**Core is “done enough” when** the matrix **Y** rows cover the table above and Yosys harness stays green on non-print suites.
