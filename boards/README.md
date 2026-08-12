# AILang HDL Board Profiles

**Vendor-neutral board I/O maps** for AILang HDL.

Industry never shipped a single good “board JSON” that works across Gowin / Lattice / Xilinx / Intel.  
We keep one here: **`ailang.board/v1`**. Humans and models add boards over time. The compiler loads them at **emit time** for pin verification and constraint generation.

## Layout

```
boards/
  catalog.json                 # index of all boards
  schema/
    ailang.board.v1.schema.json
    ailang.board.bind.v1.schema.json
  tang_nano_9k/
    board.json                 # profile (device + resources)
    bind_blink.json            # example design binding
  generic_sim/
    board.json
```

## Use with the compiler

```bash
./ailang_hdl.x -hdl \
  -board boards/tang_nano_9k/board.json \
  -bind  boards/tang_nano_9k/bind_blink.json \
  dev/hdl_tang_blink.ailang out/blink

# list catalog
./ailang_hdl.x -hdl --list-boards

# env default
export AILANG_BOARD=boards/tang_nano_9k/board.json
```

Without `-board`, the HDL path prints the catalog and continues with **UNASSIGNED** pins (Yosys sim still works).

## Authoring (humans & models)

1. Copy `tang_nano_9k/board.json` or run:
   ```bash
   python3 tools/board_profile_scaffold.py --name my_board --vendor gowin --part PART
   ```
2. Fill `clocks` / `resources` from the schematic or manufacturer pinout.
3. Add an entry to `catalog.json`.
4. Add a `bind_*.json` for each dogfood design.

**Models:** read `schema/ailang.board.v1.schema.json`, emit valid JSON only — no Verilog required.

## Related

- Design doc: `docs/compiler/14_HDL_BOARD_PROFILE.md`
- Tang Nano flow: `docs/compiler/13_HDL_TANG_NANO_9K.md`
- LSP / VS Code: board diagnostics + “Select board” (see design doc § IDE)
