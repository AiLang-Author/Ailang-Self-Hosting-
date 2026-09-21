# Motherboard: JSON description, LinkagePool runtime

JSON is the **board file** (what a schematic would be). It is not how chips
talk at runtime.

Runtime pointers are **LinkagePool** (`@`, `PointerTo=`). Method plug is
**`AddressOf` + `CallIndirect`** — same pair OOP and HAL pin monitor already
use. The old C64 `C64IO.vic_read = 0` slots were integers with nothing behind
them; that was the mistake, not “Ailang has no pointers.”

```
  c64.board.json                 (description — human / git / diagram)
           |
           |  loader (later)
           v
  LinkagePool.Board              chips linked list, nets linked list
           |
           |  chip@read = AddressOf(C64VIC_Read)
           v
  CallIndirect(chip@read, chip, addr)
```

## Three layers

| Layer | What | Analog |
|---|---|---|
| JSON | sockets, address decode, net names | Gerber / netlist |
| LinkagePool | live chip instances, `PointerTo` chains | parts on the PCB |
| AddressOf / CallIndirect | read/write/tick/pin | the silicon |

FixedPool is the wrong shape for chips: one global VIC. LinkagePool is many
instances (two CIAs, a second 6502 for a 1541, a homebrew UART).

## Chip record

See `Librarys/Library.Board6502.ailang`.

```
LinkagePool.Chip {
    "name":  Initialize=""
    "devid": Initialize=0
    "lo":    Initialize=0
    "hi":    Initialize=0
    "state": Initialize=0          // chip's own regs (typed per model)
    "read":  Initialize=0          // AddressOf(Model_Read)
    "write": Initialize=0
    "tick":  Initialize=0
    "pin":   Initialize=0
    "next":  Initialize=0, PointerTo=LinkagePool.Chip
}
```

`state` is an address of another pool (`LinkagePool.VICRegs`,
`LinkagePool.UARTRegs`, …). The bus does not need that type; the chip
functions do.

Bus read:

```
chip = Board_ChipFor(addr)          // walk maps / devid
fn   = chip@read
val  = CallIndirect(fn, chip, addr)
```

A custom ASIC is: new library + `Board_RegisterModel("MY_UART", AddressOf(UART_Read), …)` + a JSON `chips[]` row. No CPU fork.

Model registry is the one compile-time table: string name → four addresses.
JSON cannot invent a function that was never linked; it can only **name** a
model the program registered.

## Nets (IRQ, PHI2, AEC)

```
LinkagePool.PinRef {
    "chip": Initialize=0, PointerTo=LinkagePool.Chip
    "pin":  Initialize=""           // "irq", "nmi", "phi2"
    "next": Initialize=0, PointerTo=LinkagePool.PinRef
}

LinkagePool.Net {
    "name":    Initialize=""
    "combine": Initialize=0         // 0=wire, 1=wired-and, 2=wired-or
    "srcs":    Initialize=0, PointerTo=LinkagePool.PinRef
    "dsts":    Initialize=0, PointerTo=LinkagePool.PinRef
    "next":    Initialize=0, PointerTo=LinkagePool.Net
}
```

Each tick: for each net, `CallIndirect(chip@pin, chip, "irq")` on sources,
combine, write destinations. Same idea as `HAL_Pin_Monitor.RegisterPin(..., AddressOf(callback))`.

## JSON (board description only)

`docs/emu/boards/c64.board.json` stays the schematic:

- `chips[]` — id, part, **model name** (looked up in the registry)
- `maps[]` — `lo`/`hi`/`devid` on a bus
- `nets[]` — named wires

Diagram: `python3 docs/emu/boards/board_dot.py …` → Graphviz.

Loader (not written yet): parse JSON with `Library.JSON`, `AllocateLinkage`
for each chip/net, fill `chip@read` from `Board_RegisterModel`.

## Prior art (has anyone done it this way?)

Yes, in spirit. Closest C grab is **[floooh/chips](https://github.com/floooh/chips)** (zlib): each MOS part is a standalone header (`m6502.h`, `m6569.h`, `m6526.h`, `m6581.h`). Chips talk through a **pin bitmask**; a machine is those chips wired like a breadboard. They still take shortcuts on address decode. That is the same idea as our JSON nets + LinkagePool chips; they did not use a JSON motherboard file.

**zinc64** (Rust) has `ChipFactory` — construct VIC/CIA/SID with shared `IrqLine`/`Pin` objects, swap implementations.

**VICE** is chip-foldered internally (`viciisc`, `cia`, `sid`) but one big C program, GPL. Do not copy it. Their `vicii-chip-model.c` is PAL/NTSC tables, not a plug bus.

**circuit-json** / tscircuit is PCB netlist JSON (Gerbers, SPICE), not a 6502 emulator.

Nobody famous ships “motherboard.json → CallIndirect chip models” in Ailang; the hardware-shaped split is old. We can **read** floooh as a pin-level reference later. We should **not** import VICE sources.

KERNAL: we stub the jump table (`$FFD2` RTS, `$FFE4` LDA#0/RTS, Palm `$FF48` IRQ). We do not ship copyrighted `kernal.bin`.

## What we will not do

- Store JSON in the hot path (every `STA $D020`).
- One giant `If devid == 1` forever — that is the bootstrap dispatcher until
  the board list is live.
- Pretend JSON can call a library that was never imported.
