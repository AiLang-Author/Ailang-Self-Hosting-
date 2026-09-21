# 6502 family emulator — modular, full CPU spec, C64 first

Date: 2026-09-18

Decisions locked in chat:

1. **First machine pack is the C64** (VIC, CIA1/2, 6510 port, SID later).
2. **CPU is full spec now; video later.** VIC stays a register file until Klaus / Lorenz say the core is honest.

## What already exists (skeleton)

| File | What it is | What is wrong |
|---|---|---|
| `Library.CPU6502.ailang` | Documented opcode table, addressing modes, BCD ADC/SBC, IRQ/NMI flags | `LibraryImport.C64Memory` — not a core. `CPU.SP`/`CPU.PC` in the pool, but the body writes `CPU.SecurityPool` / `CPU.PrintChar` (rename wreckage). Cycle counts are constants, no page-cross. |
| `Library.Bus6502.ailang` | 256-page table, RAM map, device-id IO slots | `Bus6502_IORead`/`Write` are open-bus stubs. CPU does not use it yet. |
| `Library.C64Memory.ailang` | 64K RAM, 6510 port, BASIC/KERNAL/CHAR slots, banking | I/O “function pointers” (`C64IO.vic_read` = 0) are never called. This is a **C64 pack**, not the CPU bus. |
| `Library.C64VIC.ailang` | Register file + frame renderer (text/bitmap/sprites) | Explicitly **not** cycle-accurate (no badlines, raster IRQ, sprite steal). Parked until CPU is proven. |
| `Library.C64CIA.ailang` | CIA1 keyboard/joystick, CIA2 VIC bank, timers | Fine as a C64 device. Must not be imported by the CPU. |
| SID | none | C64 pack later. |

Pointers: **LinkagePool** (`@`, `PointerTo=`) for chip instances and nets.
Method plug: **`AddressOf` + `CallIndirect`** on `chip@read` / `@write` / `@tick`.
JSON is only the board description. See `docs/emu/BOARD.md`.

## Layers

```
                    ┌─────────────────────────┐
                    │  C64 machine (app)      │
                    │  ROMs, tick, Gtk blit   │
                    └───────────┬─────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
   CPU6502                 Bus6502                 C64 devices
   (opcodes only)          (pages + devid)         VIC CIA SID 6510
         │                      ▲
         └────── Read/Write ────┘
```

- **CPU6502** imports **only** `Bus6502`. Never `C64Memory`.
- **Bus6502** is 64K of pages. `io_id[page] == 0` → `GetByte`/`SetByte`. Else `Bus6502_IORead(devid, addr)`.
- **C64 pack** registers models (`Board_RegisterModel("C64VIC", AddressOf(C64VIC_Read), …)`), then JSON/`Board_AddChip` hangs instances on the bus. `Bus6502_IORead` becomes `Board_DevRead` (CallIndirect on the chip).
- **NES / Apple / PET** later: same CPU + bus, different pack, different device-id range.

Device ids (C64 range 1–15):

| id | device |
|---|---|
| 0 | RAM/ROM through page pointer |
| 1 | VIC-II `$D000` |
| 2 | SID `$D400` |
| 3 | CIA1 `$DC00` |
| 4 | CIA2 `$DD00` |
| 5 | 6510 port `$0000–$0001` + banking side effect |
| 6 | Color RAM `$D800` |
| 255 | open bus |

Adding a machine is a new pack file plus a few `devid` cases, not a fork of the CPU.

## Full CPU spec (this phase)

- All **documented** 6502 opcodes (skeleton already has the official set: load/store, alu, shift, branch, jmp/jsr/rts/rti, flags, BRK, NOP).
- **JMP ($xxFF)** page-wrap bug (real 6502).
- **Page-cross** extra cycle on abs,X/Y and (zp),Y.
- **RMW** extra cycles (INC/ASL/…).
- **BCD** ADC/SBC (skeleton has helpers — wire and test).
- **Undocumented** opcodes used by C64 software / Lorenz: SLO, RLA, SRE, RRA, SAX, LAX, DCP, ISC, ANC, ALR, ARR, SBX, NOP variants, and the unstable ones documented as unstable.
- **IRQ/NMI** sampled at instruction boundary first; cycle-steal later if a test demands it.
- **6510** is a C64 device (port + banking), not a CPU fork. CPU is a 6502; the pack writes `$0000/$0001`.

Not in this phase: VIC badlines, sprite DMA, SID analog, 1541 as a second 6502 (that is another CPU instance on another bus).

## Tests (CPU)

1. Smoke: poke `A9 2A 8D 00 10` (LDA #42 / STA $1000), step, read back.
2. [Klaus Dormann](https://github.com/Klaus2m5/6502_65C02_functional_tests) `6502_functional_test.bin` — trap on success address.
3. Decimal test from the same suite.
4. Unofficial smoke (`tests/emu6502/undoc_smoke.ailang`).
5. Wolfgang Lorenz C64 suite (`tests/emu6502/lorenz/`) once the C64 pack
   maps IO and KERNAL stubs (LOAD/CHROUT). Motherboard JSON:
   `docs/emu/BOARD.md` + `docs/emu/boards/c64.board.json`.

Video tests wait.

## Work order

1. Unhook CPU from `C64Memory`. Use `CPU.SP` / `CPU.PC`. All mem via `Bus6502_*`.
2. Smoke binary in `dev/compiler-regression/` or `tests/emu6502/`.
3. Klaus Dormann runner (load blob, run until PC stuck / success).
4. Undocumented opcodes + Lorenz.
5. C64 pack: dispatcher, 6510 port, CIA, VIC **registers only**, ROM load, tick loop.
6. Gtk blit of VIC framebuffer (same pattern as C64 BASIC gtk) when we turn video back on.

## What we will not do

- Cycle-accurate VIC in the same breath as the CPU rewrite.
- Function-pointer “plugins” (Ailang cannot call those `C64IO.vic_read` slots).
- One god file that is CPU+C64+NES.
