# Welcome to AILang OS

## What You're Looking At

This repository contains an operating system written from scratch in its own programming language. The language is called AILang. The compiler is self-hosted — it compiles itself. Everything you see here, from the boot process to the windowed desktop, is AILang code that compiles to native x86-64 Linux binaries through direct syscalls. No C standard library. No runtime. No external dependencies beyond the Linux kernel.

## Why

Most operating systems are built in C, with a toolchain that has decades of accumulated complexity. AILang OS asks a different question: what happens when you design a language and an OS together, from the ground up, with no inherited baggage?

The result is a system where:
- A complete graphical application is 30-90 KB
- The entire OS footprint is under 3 MB of AILang binaries
- Every application compiles in under a second
- You can read the full source of any system component — there are no opaque layers

## What It Does

AILang OS boots to a graphical desktop with:

- **A compositing window manager** — Overlapping windows, mouse-driven, rendered directly to the Linux framebuffer. No X11 or Wayland.
- **A start menu and taskbar** — Click to launch applications, see running windows.
- **A terminal emulator** — Full PTY-based terminal with shell access.
- **A text editor** — Notepad for basic text editing.
- **A calculator** — Expression-based calculator.
- **A file search tool** — Regex-powered grep with multiple file targets.
- **A code editor** — VS Code-style editor for AILang source.
- **Web browsers** — Chrome and Ladybird browser shells (work in progress).
- **An AI assistant** — Claude Code integration.
- **A WiFi manager** — Scan, connect, and manage wireless networks.
- **A package manager** — Track, install, and repair system packages.
- **A video player** — Media playback.

All of these are separate processes that communicate with the display server over a Unix socket using a JSON-based IPC protocol.

## How It Works

### The Language

AILang uses explicit function-call syntax for everything. There are no operators with precedence rules — `Add(a, b)` instead of `a + b`, `EqualTo(x, 0)` instead of `x == 0`. This makes parsing unambiguous and the compiler small.

State is managed through FixedPools (global named constants and mutable variables) and explicit memory allocation through an Arena allocator. There is no garbage collector.

### The Display Server

The display server is built from ~60 library modules and handles everything: parsing HTML widget definitions, solving flex layouts, rendering text and shapes, compositing overlapping windows, routing keyboard and mouse input to focused applications, and managing the desktop shell.

Applications don't link against the display server. They run as separate processes and connect to it over `/tmp/ailang_display.sock`. The protocol is simple: 4 bytes of big-endian message length, followed by a JSON object. Applications send requests (`create window`, `update label`, `add line to panel`). The server sends events (`button clicked`, `key pressed`, `window closed`).

### The Database

PostgreSQL runs as a system service. It stores the service registry, user accounts, file metadata, application settings, and package state. All schema DDL is idempotent — the system can re-bootstrap safely at any time.

### The Widget Toolkit

Window layouts are declared in HTML/XML config files:

```html
<window title="My App" design-w="640" design-h="480">
  <group layout="vbox" gap="4" padding="6" bg="#2D2D44">
    <label text="Hello" fg="#00FF88" id="greeting"/>
    <button label="Click Me" action="app.click" bg="#00CC66" fg="#FFFFFF"/>
    <panel grow="1" bg="#1C1C2E" id="output"/>
  </group>
</window>
```

The Auckland layout engine processes these into a rendered UI. Available widgets include buttons, labels, text fields, checkboxes, sliders, progress bars, panels (scrollable lists), tabs, canvases, and separators. Layouts use a flex model with `hbox`/`vbox` containers and `grow` factors.

### Vector Graphics

The system includes both SVG and TinyVG (VIF) parsers and software rasterizers. SVG supports paths, shapes, gradients, and transforms. These can be used for application icons, UI elements, and custom drawing.

## Getting Started

### Reading the Code

Start with these files to understand the system:

| File | What It Does |
|------|-------------|
| `OS/Init.ailang` | PID 1 — the entire boot sequence |
| `OS/Schema.ailang` | Database table definitions |
| `OS/ServiceDaemon.ailang` | Reads the service table, launches applications |
| `Applications/grep_ipc.ailang` | Clean example of a complete IPC application |
| `config/grep.html` | Example window layout definition |
| `Librarys/Library.Socket.ailang` | The IPC transport layer |
| `Librarys/Library.JSON.ailang` | JSON parser used by all IPC messages |

### Building an Application

See [PROGRAMMING_GUIDE.md](PROGRAMMING_GUIDE.md) for the full API reference. The short version:

1. Create a config HTML file defining your window layout
2. Write an AILang source file that connects to the display socket
3. Register, create a window, enter an event loop
4. Handle `input.action` (button clicks) and `input.key` (keyboard) events
5. Send `window.setlabel`, `window.addline`, and `window.clear` to update the UI
6. Compile with `./ailang.x YourApp.ailang -o yourapp.x`
7. Copy the binary to `/system/bin/` and the config to `/config/`

### Running

AILang OS boots from a UEFI-compatible disk image. It has been tested in QEMU/KVM and on bare metal x86-64 hardware. The kernel includes built-in drivers for 44 WiFi chipsets and ships firmware for Intel, Atheros, Broadcom, Realtek, and MediaTek wireless adapters.

## Project Structure

```
OS/                    System modules (init, schema, services, login, installer)
Applications/          IPC client applications (terminal, editor, browser, tools)
Librarys/              Library modules (~80 total)
  Display/             Display server stack (60 modules)
config/                Window UI definitions (HTML/XML)
Programs/              Standalone demo programs
ailang.x               The self-hosted compiler
```

## Documentation

- [INTRODUCTION.md](INTRODUCTION.md) — Architecture overview and technical details
- [PROGRAMMING_GUIDE.md](PROGRAMMING_GUIDE.md) — API reference and app development tutorial

## License

Copyright 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved. SCSL.
