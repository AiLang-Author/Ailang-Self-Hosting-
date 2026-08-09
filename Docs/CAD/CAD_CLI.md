# CAD CLI contract (frozen surface)

**Status:** v1 — host Linux tools, no AOS required.  
**Binaries:** `cad_load.x`, `cad_view.x` (build from `CAD/*.ailang`).

This is the **public API** for scripts and (later) AIMacro: load a profile, make a solid, export STEP and/or a BMP look-at.

---

## Build

```bash
./ailang.x CAD/cad_load.ailang -o cad_load.x
./ailang.x CAD/cad_view.ailang -o cad_view.x
```

---

## `cad_load` — DXF → solid → STEP

```bash
./cad_load.x --in profile.dxf --out solid.stp [--height 10]
./cad_load.x --in plate.dxf --hole hole.dxf --out esc.stp -H 4
cat profile.dxf | ./cad_load.x -H 10 > solid.stp          # pipe
./cad_load.x -H 8 < profile.dxf > solid.stp
```

| Flag | Default | Meaning |
|------|---------|---------|
| `-i` / `--in` | `-` | Input DXF path, or `-` = stdin |
| `-o` / `--out` | `-` | Output STEP path, or `-` = stdout |
| `-H` / `--height` | `10` | Extrude / plate thickness (mm, integer) |
| `-k` / `--hole` | — | Through poly hole DXF (plate mode; needs file `--in`) |

**Library equivalents**

| CLI | Library |
|-----|---------|
| extrude profile | `CAD_IO.LoadDXFExtrude` / `LoadDXFExtrudeFd` |
| plate + hole | `CAD_IO.LoadDXFPlateHole` |
| STEP out | `CAD_IO.ExportSTEP` / `ExportSTEPFd` |

**Supported DXF entities (2D, z≈0):** `LINE`, `CIRCLE`, `ARC`.

---

## `cad_view` — DXF → solid → BMP (software viewport)

```bash
./cad_view.x --in profile.dxf --shot out.bmp -H 10
./cad_view.x -i keyhole.dxf -o k.bmp -H 8 --view 0 --wire 0
./cad_view.x -i plate.dxf -k hole.dxf -o esc.bmp -H 4 --view 1
cat profile.dxf | ./cad_view.x --shot out.bmp -H 8
./cad_view.x -i part.dxf -o part.bmp -H 10 --show   # host eog window
```

| Flag | Default | Meaning |
|------|---------|---------|
| `-i` / `--in` | `-` | DXF or stdin |
| `-o` / `--shot` | `test-stl/cad_view.bmp` | Output BMP |
| `-H` / `--height` | `10` | Thickness mm |
| `-k` / `--hole` | — | Plate hole DXF |
| `-W` / `--width` | `800` | Image width |
| `--imgh` | `600` | Image height |
| `--view` | `0` | `0`=iso `1`=top `2`=front |
| `--wire` | `0` | `1`=tri edges `0`=shaded only |
| `--defl` | `2` | Mesh deflection in **0.01 mm** (2 → 0.02 mm) |
| `--show` | off | Open host viewer on BMP |

**Library equivalents**

| CLI | Library |
|-----|---------|
| options | `CAD_View.SetViewMode` / `SetWire` / `SetDefl` |
| render | `CAD_View.RenderSolidToBMP` |
| host window | `CAD_View.OpenHostViewer` |

---

## Example scripts

```bash
CAD/scripts/load_profile.sh path.dxf out.stp [height]
CAD/scripts/view_profile.sh path.dxf out.bmp [height]
./CAD/smoke_view.sh
```

---

## Intentionally out of contract (v1)

- STEP **import** (export only)
- Interactive orbit (re-run with `--view`)
- AOS / Vulkan workbench
- General boolean cut of arbitrary solids
- AIMacro (next consumer of this CLI, not a replacement)

---

## Roadmap after v1 freeze

1. ~~Authoring: ARC~~ done  
2. ~~View: wire/defl/presets~~ done; host window + interactive dogbone pad **done** (2026-08-08)  
3. **Next:** revolve surface in `cad_app` (kernel recipes already green)  
4. **This doc** = script/AIMacro surface  
5. AIMacro / thin GUI **only** via these commands/APIs
