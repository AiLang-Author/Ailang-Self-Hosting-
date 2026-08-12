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
| Bit soft-IP | OneHot ReverseBits8 Parity8 PopCount8 Ctz8 Clz8 ByteSwap16 Hamming8 | **Y** |
| Gray / sat | GrayEncode8 GrayDecode8 SaturateU8 AddSatU8 SubSatU8 AbsDiff8 SignExtend8 | **Y** |
| Predicates | IsZero IsNonZero | **Y** |
| Compare | EqualTo NotEqual Less* Greater* | **Y** |
| Logic | And Or Not | **Y** `$logic_*` |
| Structure | AbsoluteValue Min Max Clamp Select Mux4 | **Y** mux |
| Calls | user Function | **Y** instance |
| Escape | TechBlock | **Y** blackbox (InlineAsm analogue) |
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
| `softip` | PopCount / Gray / sat / edge detect |
| `delay` | 8-tap delay line + moving average |
| `fifo` | depth-4 ring FIFO push/pop |
| `spi` | bit-serial SPI-ish master FSM |
| `arbiter` | 4-way round-robin grant |
| `debounce` | N-cycle stable filter + edges |
| `i2c` | bit-bang START/addr/data/ACK/STOP |
| `pwm` | timer wrap + duty compare |
| `crc_stream` | CRC-8 over ROM payload stream |
| `uart_rx` | start/data/stop RX + soft TX stim |
| `watchdog` | kick / timeout / sticky fault |
| `cdc` | 2FF sync + toggle→pulse handshake |
| `alu` | 8-op ALU + 4-reg file datapath |
| `stack` | depth-8 push/pop with ovf/unf |
| `barrel` | rotate/shift + nibble swap |
| `kill_verilog` | LFSR CRC UART priority + soft-IP showcase |
| `techblock` | InlineAsm-style blackbox escape |

**Semantics note:** straight-line pool updates use a **comb shadow chain** so  
`x = BitSet(x,0); x = BitSet(x,1)` accumulates (not NBA last-wins).

---

## Tech blocks = InlineAsm (escape, not core)

See **[12_HDL_TECHBLOCK.md](12_HDL_TECHBLOCK.md)**.

```ailang
y = TechBlock["HARD_AND2", a, b]   // blackbox; you own the cell lib
```

Robust AILang core first; hard cells only when forced. Not a second language.

## Still outside core (by design)

1. Named-port TechBlock / Liberty auto-import packs (thin layer on top of TechBlock)  
2. Interleaved print events  
3. ForEvery depth > 32  
4. Runtime-variable Power / Rotate  

**Core is solid when** harness stays green and kill-verilog soft-IP stays pure AILang.
