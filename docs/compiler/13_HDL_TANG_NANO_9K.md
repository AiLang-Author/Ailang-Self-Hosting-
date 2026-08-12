# AILang HDL — Tang Nano 9K (real silicon)

**Board:** Sipeed Tang Nano 9K · Gowin **GW1NR-9** (GW1NR-LV9QN88PC6/I5)  
**Clock:** 27 MHz (pin 52)  
**LEDs:** 6× on-board, pins 10/11/13/14/15/16, **active-low**  
**Flow:** AILang → structural `.v` → **Yosys `synth_gowin`** → **nextpnr-himbaechel** → **gowin_pack** → **openFPGALoader**

This is the first **board-backed** dogfood path. Same language, same ModulesHDL core — only a thin pin wrapper + CST at the edge.

---

## Why this shape

| Layer | Owner |
|---|---|
| Algorithm / soft-IP | **AILang** (`FixedPool`, `Function`, `Branch`, …) |
| Netlist object code | ModulesHDL → `ailang_top` |
| Package pins | `dev/boards/tang_nano_9k/` (CST + 10-line wrapper) |
| Silicon | Yosys / nextpnr / Apicula — not a second HDL |

No Verilog dialect. The wrapper only renames ports and inverts active-low LEDs.

---

## One-shot build

```bash
# toolchain on PATH (oss-cad-suite)
export PATH="$HOME/tools/oss-cad-suite/bin:$PATH"

# compile + P&R + bitstream
./dev/hdl_build_tang9k.sh

# with board plugged in:
FLASH=1 ./dev/hdl_build_tang9k.sh
# or:
openFPGALoader -b tangnano9k dev/boards/tang_nano_9k/out/blink.fs
```

Source: `dev/hdl_tang_blink.ailang` — half-second binary count on the six LEDs.

---

## Files

| Path | Role |
|---|---|
| `dev/hdl_tang_blink.ailang` | Blink / LED counter in pure AILang |
| `dev/boards/tang_nano_9k/top_wrap.v` | `top` → `ailang_top` + LED invert |
| `dev/boards/tang_nano_9k/tangnano9k.cst` | Pin locations |
| `dev/hdl_build_tang9k.sh` | Full FOSS build script |
| `out/blink.fs` | Bitstream (after build) |

---

## Mapping notes

- AILang always emits `clk` / `rst` on `ailang_top`. Wrapper ties `rst = 0` and uses pool `Initialize` / `initial` for cold start.
- Pool field `Board.led` is 64-bit in the netlist; only `[5:0]` hit the package.
- **Active-low LEDs:** `assign led = ~Board_led[5:0];` lives in the wrapper so soft-IP can think “1 = lit”.
- Period hint: `./ailang_hdl.x -hdl -period 37 …` (~27 MHz) for SDC comments; not a PLL yet.

### NBA / if-else pitfall (real bug we hit)

```ailang
// BAD — Else hold undoes the Increment (last nonblocking assign wins)
Board.div = Increment(Board.div)
IfCondition GreaterEqual(Board.div, N) ThenBlock: {
    Board.div = 0
} ElseBlock: {
    Board.div = Board.div   // cancels the increment!
}

// GOOD — no Else; leave the incremented value
Board.div = Increment(Board.div)
IfCondition GreaterEqual(Board.div, N) ThenBlock: {
    Board.div = 0
    Board.led = LowBits(Increment(Board.led), 6)
}
```

Verified post-fix bitstream util on GW1NR-9: **~143 LUT4 / ~70 DFF** for the blink counter (not zero — dead logic was the NBA bug).

---

## Next on-board targets

1. UART TX from print channel → USB-UART (pins 17/18)  
2. Button → debounce soft-IP → LED  
3. PWM soft-IP on a GPIO  
4. Optional TechBlock only if a Gowin hard IP is forced  

Still: **core AILang first; TechBlock = InlineAsm for gates.**
