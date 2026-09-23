# 6502 tests

## Smoke

```
Import.Librarys.Emulators.6502.CPU
./ailang.x tests/emu6502/smoke.ailang /tmp/emu6502_smoke.x
/tmp/emu6502_smoke.x
```

LDA #$2A / STA $1000 on a bare 64K bus.

## Klaus Dormann functional blob

Klaus Dormann’s NMOS 6502 test
https://github.com/Klaus2m5/6502_65C02_functional_tests

`6502_functional_test.bin` is a **full 64K RAM image** (load at `$0000`).
Start PC at `$0400`. The program walks every documented opcode (binary and
valid BCD). Failures and success are **traps**: `JMP *` so the PC stops
changing.

This copy’s success trap is `$3469` (listing: `3469 : 4c6934 jmp * ;test passed`).
Any other stuck PC is the failing test; look that address up in
`bin_files/6502_functional_test.lst`.

About **30 million** instructions. Not a 65C02 test (that is a separate blob).

```
./ailang.x tests/emu6502/klaus.ailang /tmp/emu6502_klaus.x
/tmp/emu6502_klaus.x
```

## Unofficial / Lorenz

NMOS unofficial opcodes (SLO/ASO, RLA, SRE/LSE, RRA, SAX, LAX, DCP/DCM,
ISC/INS, ANC, ALR, ARR, SBX, NOP variants, JAM) live in `CPU_ExecuteUndoc`.

```
./ailang.x tests/emu6502/undoc_smoke.ailang /tmp/emu6502_undoc.x
/tmp/emu6502_undoc.x
```

Wolfgang Lorenz 2.15 is in `tests/emu6502/lorenz/` (265 PRGs). Full run
needs a C64 pack: 6510 port, KERNAL LOAD/CHROUT stubs. Motherboard JSON
for that pack: `docs/emu/BOARD.md`.

JSON board loader smoke — parse `smoke.board.json`, plug `ProbeASIC` at
`$DE00` via LinkagePool + `CallIndirect`, CPU `LDA $DE00 / STA $1000`:

```
./ailang.x tests/emu6502/board_smoke.ailang /tmp/board_smoke.x
/tmp/board_smoke.x
```

CIA timer underflow + VIC `$D012` raster (65 cyc/line NTSC):

```
./ailang.x tests/emu6502/cia_vic_smoke.ailang /tmp/cia_vic_smoke.x
/tmp/cia_vic_smoke.x
```

PLA `$01` banking, `$01` fetch, CIA2 NMI edge, timer B delay / cascade / IMR:

```
./ailang.x tests/emu6502/pla_smoke.ailang /tmp/pla_smoke.x && /tmp/pla_smoke.x
./ailang.x tests/emu6502/mmufetch_smoke.ailang /tmp/mmufetch_smoke.x && /tmp/mmufetch_smoke.x
./ailang.x tests/emu6502/nmi_smoke.ailang /tmp/nmi_smoke.x && /tmp/nmi_smoke.x
./ailang.x tests/emu6502/cia_tb_smoke.ailang /tmp/cia_tb_smoke.x && /tmp/cia_tb_smoke.x
./ailang.x tests/emu6502/nmi_lorenz_smoke.ailang /tmp/nmi_lorenz_smoke.x && /tmp/nmi_lorenz_smoke.x
```

Full Lorenz 2.15 (`tests/emu6502/lorenz.ailang`): last run through `nmi` / CIA TAB / `imr` / `flipos`, then **TIMEOUT** on `oneshot` (CRA still `$09` when ICR should be `$01` in the 4-cycle `STA $DC0E` / `LDA $DC0E` window). Next name after `oneshot` is `cntdef`.

C64 JSON board + KERNAL stubs (`JSR $FFD2`, VIC `$D020`, 6510 `$01`):

```
./ailang.x tests/emu6502/c64_stub_smoke.ailang /tmp/c64_stub_smoke.x
/tmp/c64_stub_smoke.x
```
