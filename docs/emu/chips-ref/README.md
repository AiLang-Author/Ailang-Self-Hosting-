# Chip reference (not linked into the emulator)

zlib headers from https://github.com/floooh/chips — pin-bitmask C models.
We **translate** these into Ailang libraries; we do not compile the C.

| Header | Ailang library |
|---|---|
| m6502.h | `Library.CPU6502` (already) |
| m6526.h | `Library.MOS6526` |
| m6569.h | `Library.MOS6569` (next) |
| m6581.h | `Library.MOS6581` (next) |

Full clone lives in `chips/` (gitignored). VICE C is GPL — do not copy it here.
