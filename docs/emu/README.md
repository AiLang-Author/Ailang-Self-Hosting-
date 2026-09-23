# 6502-Board (this tree)

Canonical public repo: **https://github.com/AiLang-Author/6502-Board**

Chip sources live under `Librarys/Emulators/6502/` (not the generic `Librarys/` pile).

```
Import.Librarys.Emulators.6502.C64
Import.Librarys.Emulators.6502.CPU
```

The board file is the schematic (`docs/emu/boards/c64.board.json`). Chips are Ailang libraries. Runtime pointers are LinkagePool; methods plug with `AddressOf` / `CallIndirect`.

| Piece | State |
|---|---|
| NMOS 6502 documented opcodes | Klaus Dormann **PASS** (30,646,177 steps, trap `$3469`) |
| Unofficial opcodes | Lorenz CPU chain **PASS** (ANE/LXA/SHA family) |
| JSON board loader | **PASS** (`ProbeASIC` at `$DE00`) |
| C64 pack + KERNAL stubs | **PASS** (`JSR $FFD2`, VIC `$D020`, 6510 `$01`) |
| PLA `$01` fetch map | **PASS** (`mmufetch` / `mmu` / `cpuport`) |
| CIA | timers A+B, per-CPU-cycle phi2, start delay 3, ICR/IMR, TA→TB cascade, PB6/PB7; IRQ pin one cycle after underflow |
| IRQ / NMI | CIA1 → IRQ; CIA2 edge → NMI; Lorenz `nmi` `$DD0D` **PASS** |
| VIC | NTSC raster `$D011`/`$D012` (paint later) |
| Lorenz 2.15 | through `imr` / `flipos`; **TIMEOUT** on `oneshot` (`CRA IS NOT $08 AT ICR=$01`) |

See `tests/emu6502/README.md` for how to run the smokes.
