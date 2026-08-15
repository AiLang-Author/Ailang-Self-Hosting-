# CAD/App — local cad_app modules

App glue for the interactive CAD runner. **Not** `Librarys/` (those are guarded kernel libs).

## Import style

```ailang
// Portable kernel / viewport (baked libraries)
LibraryImport.Cad.CAD_Sketch
LibraryImport.Cad.CAD_View

// This app (local tree under CAD/App/)
Import.CAD.App.State
Import.CAD.App.Draw
```

Resolution: `Import.CAD.App.State` → `CAD/App/State.ailang` (same pattern as `Import.Attn.Train` → `Attn/Train.ailang`).

## Modules

| Module | Role |
|--------|------|
| `State.ailang` | `FixedPool.CadApp`, logging helpers |
| `Draw.ailang` | Sketch/3D FB draw, camera, `CA_PublishFrame` |
| `Solid.ailang` | Pad / cut / revolve / DXF → solid |
| `Plane.ailang` | Construction planes, sketch-on-face |
| `Doc.ailang` | Repo, open/new/list |
| `Profile.ailang` | Project closed profiles, pick |
| `Tools.ailang` | Click/hover, trim UI, constraints |
| `Ipc.ailang` | `cmd.txt` poll, CLI schema |

## Portable vs local

| Portable → `Librarys/Cad/` | Local → `CAD/App/` or `CAD/host/` |
|----------------------------|-----------------------------------|
| Sketch geometry, topo, tess, view mesh | CadApp state, click/hover glue, IPC |
| `CAD_UI` tool ids, cmd parse, tools.json, constructions | Host chrome (`CAD/host/`) only blits + sends cmds |
| `CAD_View` software raster | compiled Gtk (`CAD/host/cad_shell_gtk`) |

## Entry

```text
CAD/cad_app.ailang   # thin Main + imports only (~270 lines)
./ailang.x CAD/cad_app.ailang -o cad_app.x
```
