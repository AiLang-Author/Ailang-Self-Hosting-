# C64 BASIC (Gtk)

Ailang BASIC kernel in a Gtk3 window, same pattern as CAD, Paint, ECU,
and HalCodeGTK: the kernel owns the 80×24 cell buffer; the host only
blits and sends keys.

Language target is **NBS / ECMA-55 Minimal BASIC**, full suite, nothing
skipped. Last run: **208/208**, **114 PASS / 25 FAIL / 63 ERROR / 6
TIMEOUT**. See [NBS_RESULTS.md](NBS_RESULTS.md).

Lives in [Ailang-Self-Hosting-](https://github.com/AiLang-Author/Ailang-Self-Hosting-)
(`C-64 basic gtk/`). Compile with `./ailang.x` from that tree
(`Library.BasicNum` and the C64 math/string/file libs).

```
./C-64\ basic\ gtk/scripts/run_c64_gtk.sh
```

Headless NBS:

```
python3 "C-64 basic gtk/tests/run_nbs.py"
```

State dir `/tmp/c64_basic`:

| File | Role |
|------|------|
| `screen.bin` | 80×24 ASCII cells from the kernel |
| `gen.txt` | redraw generation |
| `keys.txt` | host writes decimal key (13 enter, 8 backspace, 27 esc) |

Fonts: Cairo `DejaVu Sans Mono` for now. Next: VIF/TVG like
`HalCodeGTK/fonts` and ECU `.vif` so layout and typeface are not
terminal-cell limited.

TUI remains in `C-64 basic intepreter/`.
