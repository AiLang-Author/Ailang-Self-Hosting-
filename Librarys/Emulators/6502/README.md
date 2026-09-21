# Emulators / 6502

Not generic libraries. Import with a regular `Import`, no `Library.` filename:

```
Import.Librarys.Emulators.6502.C64
Import.Librarys.Emulators.6502.CPU
```

Resolves to `Librarys/Emulators/6502/CPU.ailang` (and friends).

| File | Chip / role |
|---|---|
| CPU.ailang | NMOS 6502/6510 core |
| Bus.ailang | 64K page bus |
| Board.ailang | JSON motherboard loader |
| C64.ailang | C64 pack + KERNAL stubs |
| MOS6526.ailang | CIA |
| MOS6569.ailang | VIC-II |
| MOS6581.ailang | SID |
| legacy/ | old C64Memory/VIC/CIA skeletons |

Public repo: https://github.com/AiLang-Author/6502-Board
