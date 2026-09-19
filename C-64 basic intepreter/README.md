# C64 BASIC interpreter (TUI)

Classic light-blue-on-blue screen in the **terminal** (`Library.TUI`).

Do not use `python3 main.py`. Build with the self-hosting compiler:

```bash
./ailang.x "C-64 basic intepreter/c64_basic_interpreter.ailang" "C-64 basic intepreter/c64_basic.x"
./C-64\ basic\ intepreter/c64_basic.x
```

Type BASIC, then `READY.` `QUIT` or ESC to leave.

`LibraryImport.TuiWidget` was removed so this no longer depends on Packager’s `UILayout` chat panes.

## Later: GTK / Haiku

Keep this TUI tree. Fork a new folder (e.g. `C-64 basic gtk/`) for a Gtk3 host like CAD (`CAD/host/cad_shell_gtk`) and HalCode (kernel + chrome, not ANSI in-process). Haiku GUI is a third surface, same kernel if we split I/O behind `C64_Print` / `C64_ReadLine`.
