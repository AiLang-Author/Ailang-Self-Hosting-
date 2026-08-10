# AILang CAD dogfood kit (design feedback)

**This is not a product release.** It is an early, internal-style CAD shell built entirely on the AILang stack so we can get design feedback from people who care about real CAD UX.

## Source of truth

**GitHub (clone / issues / PRs):**  
https://github.com/AiLang-Author/Ailang-Self-Hosting-

License: **SCSL v1.0** (see `LICENSE` in the package and repo root). Personal/academic use free; commercial use needs a license. Forking/redistribution of the full codebase is restricted — please send design notes and patches upstream.

Contact: smc.collins1977@gmail.com

## What you can try (Linux + X11 / XWayland)

This kit includes a **prebuilt Linux x86_64** CAD kernel + X11 presenters so you can poke at viewport UX without building the whole monorepo first.

```bash
# from this folder
chmod +x bin/* scripts/*.sh
export DISPLAY=:0   # or your XWayland display
./scripts/run_dogfood.sh
```

**Controls (summary)**

| Area | Action |
|------|--------|
| 3D | LMB drag = orbit, scroll = zoom, short click = pick |
| Sketch | LMB place, hold ~1s + drag = pan, RMB = cancel |
| Pad height | Feature → Pad… (dialog) or `height N` then pad |
| Mirror | Sketch → Mirror X / Y (or panel MirX / MirY) |
| Live angle | Line tool: second point shows `ang=` + length on rubber-band |

Agent / script drive:

```bash
./scripts/cad_cmd.sh tool_line --wait
./scripts/cad_cmd.sh "click 200 200" --wait
./scripts/cad_shot.sh /tmp/view.png
```

## What we want feedback on

Please tell us (Telegram thread or GitHub issue) what felt **wrong, slow, or free-form-CAD-like** vs FreeCAD/SolidWorks:

1. **Sketch in 3D** — planes + solids together; is that enough or do you need a pure 2D pad?
2. **Pad height** — dialog vs always-on spinner vs drag arrow
3. **Mirror** — whole-sketch only today; do you need selection + custom axis first?
4. **Live angle** — relative to shared vertex / origin; what else (length lock, polar coord)?
5. **Menus vs panel** — FLTK menus (if you build FLTK) vs X11 tool panel
6. **File open/save** — DXF import path + Postgres part list; what would you open first day?

## Full repo / rebuild

The monorepo has the compiler (`ailang.x`), `Librarys/Cad/*`, and the FLTK shell:

```bash
git clone https://github.com/AiLang-Author/Ailang-Self-Hosting-.git
cd Ailang-Self-Hosting-
# optional: build FLTK under third_party (see CAD/host/BUILD_FLTK.md)
./CAD/scripts/run_cad_app.sh
```

## Disclaimer

Expect crashes, ugly pixels, and incomplete feature trees. That is intentional dogfood.  
**Do not use this for production parts.**

Thanks — Sean / 2 Paws Machine and Engineering
