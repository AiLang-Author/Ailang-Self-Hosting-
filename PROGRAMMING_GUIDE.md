# AILang OS Programming Guide

This guide covers how to build applications for AILang OS — from standalone programs to full IPC windowed apps that run inside the display server.

---

## Table of Contents

1. [Language Basics](#1-language-basics)
2. [Memory Management](#2-memory-management)
3. [System Calls](#3-system-calls)
4. [Building an IPC Application](#4-building-an-ipc-application)
5. [Window UI Design](#5-window-ui-design)
6. [Widget Reference](#6-widget-reference)
7. [IPC Message Reference](#7-ipc-message-reference)
8. [Database Integration](#8-database-integration)
9. [Fork/Exec Pattern](#9-forkexec-pattern)
10. [Vector Graphics](#10-vector-graphics)
11. [Library Reference](#11-library-reference)
12. [Compiling and Deploying](#12-compiling-and-deploying)

---

## 1. Language Basics

AILang compiles directly to x86-64 ELF binaries. There is no runtime, no garbage collector, and no libc. All OS interaction happens through raw Linux syscalls.

### Functions

```ailang
Function.Add {
    Input: a: Integer
    Input: b: Integer
    Output: Integer
    Body: {
        result = Add(a, b)
        ReturnValue(result)
    }
}
```

Functions declare their inputs with types (`Integer`, `Address`) and an optional `Output` type. The entry point for any program is `SubRoutine.Main`.

### Entry Point

```ailang
SubRoutine.Main {
    PrintMessage("Hello from AILang OS\n")
    RunTask(Main)
}
```

### Control Flow

```ailang
// Conditional
IfCondition EqualTo(x, 0) ThenBlock: {
    PrintMessage("zero\n")
} ElseBlock: {
    PrintMessage("nonzero\n")
}

// Loop
WhileLoop LessThan(i, 10) {
    PrintNumber(i)
    PrintMessage("\n")
    i = Add(i, 1)
}
```

### Comparison Operators

| Function | Meaning |
|----------|---------|
| `EqualTo(a, b)` | a == b |
| `NotEqual(a, b)` | a != b |
| `LessThan(a, b)` | a < b |
| `GreaterThan(a, b)` | a > b |
| `GreaterEqual(a, b)` | a >= b |

### Arithmetic and Bitwise

| Function | Operation |
|----------|-----------|
| `Add(a, b)` | a + b |
| `Subtract(a, b)` | a - b |
| `Multiply(a, b)` | a * b |
| `Divide(a, b)` | a / b |
| `Modulo(a, b)` | a % b |
| `BitwiseAnd(a, b)` | a & b |
| `BitwiseOr(a, b)` | a \| b |
| `LeftShift(a, n)` | a << n |
| `RightShift(a, n)` | a >> n |

### Imports

```ailang
// Import a library (from Librarys/ directory)
LibraryImport.Arena
LibraryImport.Socket
LibraryImport.StringUtils

// Import an OS module (from OS/ directory)
Import.OS.Schema
```

### FixedPool — Global State

FixedPools are pre-allocated global variables. They are the primary mechanism for application state:

```ailang
FixedPool.AppState {
    "running":   Initialize=1, CanChange=True
    "win_id":    Initialize=0, CanChange=True
    "sock":      Initialize=0
    "count":     Initialize=0, CanChange=True
}
```

Access fields with dot notation: `AppState.running = 0`

Use `CanChange=True` for fields that will be modified at runtime. Fields without this flag are compile-time constants.

---

## 2. Memory Management

AILang uses explicit memory management through the Arena allocator.

```ailang
LibraryImport.Arena

// Allocate N bytes
buf = Allocate(256)

// Write data
StoreValue(buf, 42)                    // Write 8-byte integer at offset 0
StoreValue(Add(buf, 8), 100)           // Write at offset 8
SetByte(buf, 0, 65)                    // Write single byte ('A')

// Read data
val = Dereference(buf)                 // Read 8-byte integer at buf
b = GetByte(buf, 3)                    // Read single byte at offset 3

// Memory operations
MemoryCopy(dst, src, count)            // Copy bytes
MemorySet(buf, 0, 256)                 // Fill with zeros
MemChr(buf, 10, len)                   // Find byte (like memchr)

// Free
Deallocate(buf, 256)
```

### Strings

Strings in AILang are null-terminated byte sequences:

```ailang
msg = "Hello World"
len = StringLength(msg)                // Returns 11
cmp = StringCompare(s1, s2)            // Returns 0 if equal

// Build strings in buffers
buf = Allocate(128)
SetByte(buf, 0, 72)                    // 'H'
SetByte(buf, 1, 105)                   // 'i'
SetByte(buf, 2, 0)                     // null terminator
```

---

## 3. System Calls

Direct Linux syscalls are made with `SystemCall()`:

```ailang
// SystemCall(number, arg1, arg2, arg3, arg4, arg5)
fd = SystemCall(2, "/tmp/test.txt", 0, 0)         // SYS_OPEN
bytes = SystemCall(0, fd, buf, 256)                // SYS_READ
SystemCall(1, fd, buf, bytes)                      // SYS_WRITE
SystemCall(3, fd)                                  // SYS_CLOSE
```

### Common Syscall Numbers

| Number | Name | Arguments |
|--------|------|-----------|
| 0 | SYS_READ | fd, buf, count |
| 1 | SYS_WRITE | fd, buf, count |
| 2 | SYS_OPEN | path, flags, mode |
| 3 | SYS_CLOSE | fd |
| 35 | SYS_NANOSLEEP | timespec_ptr, 0 |
| 41 | SYS_SOCKET | domain, type, protocol |
| 42 | SYS_CONNECT | fd, addr, addrlen |
| 57 | SYS_FORK | — |
| 59 | SYS_EXECVE | path, argv, envp |
| 60 | SYS_EXIT | code |
| 61 | SYS_WAIT4 | pid, status, options, rusage |
| 83 | SYS_MKDIR | path, mode |
| 165 | SYS_MOUNT | source, target, fstype, flags, data |

It is common practice to define syscall numbers in a FixedPool for readability:

```ailang
FixedPool.Sys {
    "SYS_READ":  Initialize=0
    "SYS_WRITE": Initialize=1
    "SYS_OPEN":  Initialize=2
    "SYS_CLOSE": Initialize=3
    "SYS_FORK":  Initialize=57
    "SYS_EXECVE":Initialize=59
}
```

---

## 4. Building an IPC Application

All graphical applications in AILang OS are IPC clients. They connect to the display server's Unix socket, create a window, and handle events. Here is the complete pattern:

### Step 1: Imports and State

```ailang
LibraryImport.Arena
LibraryImport.Socket
LibraryImport.StringUtils
LibraryImport.JSON
LibraryImport.Arrays
LibraryImport.Hash

FixedPool.AppState {
    "running":   Initialize=1, CanChange=True
    "win_id":    Initialize=0, CanChange=True
    "msg_count": Initialize=0, CanChange=True
    "sock":      Initialize=0, CanChange=True
}
```

### Step 2: Connect and Register

```ailang
SubRoutine.Main {
    Arena_Init()

    // Connect to the display server
    sock = Socket.Create(1, 1)          // AF_UNIX, SOCK_STREAM
    cres = Socket.ConnectUnix(sock, "/tmp/ailang_display.sock")
    IfCondition LessThan(cres, 0) ThenBlock: {
        PrintMessage("Cannot connect to display server\n")
        SystemCall(60, 1)               // exit(1)
    }
    AppState.sock = sock

    // Register this application
    Socket.SendMsg(sock, "{\"method\":\"register\",\"service\":\"myapp\"}")

    // ... continued in next step
}
```

### Step 3: Create Window

```ailang
    // Create a window using an HTML config file
    Socket.SendMsg(sock,
        "{\"method\":\"window.create\",\"title\":\"My App\",\"w\":640,\"h\":480,\"html\":\"config/myapp.html\"}")

    // Receive the window ID
    resp = Socket.RecvMsg(sock)
    IfCondition NotEqual(resp, 0) ThenBlock: {
        parsed = ParseJSON(resp)
        pobj = JSON.AsObject(parsed)
        wid = JSON.GetNumber(pobj, "win_id")
        AppState.win_id = wid
        JSON.Free(parsed)
    }
```

### Step 4: Event Loop

```ailang
    // Main event loop
    WhileLoop EqualTo(AppState.running, 1) {
        msg = Socket.RecvMsg(sock)
        IfCondition EqualTo(msg, 0) ThenBlock: {
            AppState.running = 0
        } ElseBlock: {
            pmsg = ParseJSON(msg)
            mobj = JSON.AsObject(pmsg)
            method = JSON.GetString(mobj, "method")

            // Window closed
            cmp = StringCompare(method, "window.closed")
            IfCondition EqualTo(cmp, 0) ThenBlock: {
                AppState.running = 0
            }

            // Button click
            cmp2 = StringCompare(method, "input.action")
            IfCondition EqualTo(cmp2, 0) ThenBlock: {
                action = JSON.GetString(mobj, "action")
                HandleAction(sock, action)
            }

            // Keyboard input
            cmp3 = StringCompare(method, "input.key")
            IfCondition EqualTo(cmp3, 0) ThenBlock: {
                keycode = JSON.GetNumber(mobj, "keycode")
                ch = JSON.GetNumber(mobj, "char")
                HandleKey(sock, keycode, ch)
            }

            JSON.Free(pmsg)
        }
    }

    Socket.Close(sock)
    SystemCall(60, 0)                   // exit(0)
    RunTask(Main)
}
```

### Step 5: Send UI Updates

```ailang
// Update a label widget
Function.SendSetLabel {
    Input: sock: Integer
    Input: widget_id: Address
    Input: text: Address
    Body: {
        req = JSON.NewObject()
        JSON.SetString(req, "method", "window.setlabel")
        JSON.SetNumber(req, "win_id", AppState.win_id)
        JSON.SetString(req, "id", widget_id)
        JSON.SetString(req, "text", text)
        msg = JSON.SerializeObject(req)
        Socket.SendMsg(sock, msg)
        JSON.Free(req)
    }
}

// Add a line to a panel widget
Function.SendAddLine {
    Input: sock: Integer
    Input: text: Address
    Input: color: Integer
    Body: {
        req = JSON.NewObject()
        JSON.SetString(req, "method", "window.addline")
        JSON.SetNumber(req, "win_id", AppState.win_id)
        JSON.SetString(req, "text", text)
        JSON.SetString(req, "target", "results")
        IfCondition NotEqual(color, 0) ThenBlock: {
            JSON.SetNumber(req, "color", color)
        }
        msg = JSON.SerializeObject(req)
        Socket.SendMsg(sock, msg)
        JSON.Free(req)
    }
}

// Clear a panel
Function.SendClear {
    Input: sock: Integer
    Input: panel_id: Address
    Body: {
        req = JSON.NewObject()
        JSON.SetString(req, "method", "window.clear")
        JSON.SetNumber(req, "win_id", AppState.win_id)
        JSON.SetString(req, "target", panel_id)
        msg = JSON.SerializeObject(req)
        Socket.SendMsg(sock, msg)
        JSON.Free(req)
    }
}
```

---

## 5. Window UI Design

Window layouts are defined in HTML/XML config files under `config/`. The display server parses these using the Auckland layout engine.

### Basic Structure

```html
<window title="My App" design-w="640" design-h="480" toolbar="about">
  <group layout="vbox" gap="4" padding="6" bg="#2D2D44">

    <!-- Status bar -->
    <group layout="hbox" gap="4" height="24">
      <label text="Ready" fg="#00FF88" text-align="left" grow="1" height="20" id="status"/>
    </group>

    <separator height="1" fg="#444444"/>

    <!-- Buttons -->
    <group layout="hbox" gap="4" height="28">
      <button label="Run"   action="app.run"  width="80" height="24" bg="#00CC66" fg="#FFFFFF"/>
      <button label="Clear" action="app.clr"  width="80" height="24" bg="#3D3D50" fg="#E0E0E0"/>
    </group>

    <separator height="1" fg="#444444"/>

    <!-- Results panel (scrollable, targetable) -->
    <panel layout="vbox" gap="1" grow="1" bg="#1C1C2E" border="1" padding="2" id="results"/>

  </group>
</window>
```

### Layout Model

The layout uses a **flex model** with two container types:

- `layout="hbox"` — Children arranged horizontally (left to right)
- `layout="vbox"` — Children arranged vertically (top to bottom)

**Sizing rules:**
- `width="N"` / `height="N"` — Fixed size in pixels
- `grow="1"` — Expand to fill remaining space (like CSS `flex-grow`)
- `gap="N"` — Space between children
- `padding="N"` — Internal padding

### Colors

Colors use hex notation with optional alpha:

```html
bg="#2D2D44"      <!-- Background (RGB) -->
fg="#00FF88"      <!-- Foreground / text (RGB) -->
bg="#801C1C2E"    <!-- Semi-transparent (ARGB) -->
```

### Widget IDs and Actions

- `id="status"` — Makes a widget targetable by `window.setlabel` messages
- `action="app.run"` — When clicked, sends an `input.action` event with this string

Convention: use a short prefix for your app's actions (e.g., `g.` for grep, `wf.` for wifi, `pkg.` for package manager).

---

## 6. Widget Reference

### `<window>`

Top-level container. Required attributes:

```html
<window title="App Name" design-w="640" design-h="480" toolbar="about">
```

| Attribute | Description |
|-----------|-------------|
| `title` | Window title bar text |
| `design-w` | Design width in pixels |
| `design-h` | Design height in pixels |
| `toolbar` | Toolbar mode: `about`, `file`, `browser` |
| `addressbar` | Show address bar: `true` (browser mode) |

### `<group>`

Layout container. Does not scroll.

```html
<group layout="hbox" gap="4" padding="6" bg="#2D2D44" height="28">
```

### `<panel>`

Scrollable container. Can be targeted by `window.addline` and `window.clear`.

```html
<panel layout="vbox" gap="1" grow="1" bg="#1C1C2E" border="1" padding="2" id="results"/>
```

### `<button>`

Clickable button. Sends `input.action` when clicked.

```html
<button label="Search" action="g.run" width="80" height="24" bg="#00CC66" fg="#FFFFFF"/>
```

### `<label>`

Static or dynamic text. Targetable by ID for updates.

```html
<label text="Ready" fg="#C0C0C0" text-align="left" grow="1" height="20" id="status"/>
```

| `text-align` | `left`, `center`, `right` |

### `<textfield>`

Text input. Keyboard events are sent to the app as `input.key` messages.

```html
<textfield grow="1" height="20" bg="#1C1C2E" fg="#00FF88" border-color="#444444" padding="2"/>
```

### `<checkbox>`

Toggle checkbox. Sends `input.action` when toggled.

```html
<checkbox label="Case insensitive" action="g.ci" height="18" fg="#E0E0E0"/>
```

### `<separator>`

Horizontal divider line.

```html
<separator height="1" fg="#444444"/>
```

### `<canvas>`

Drawing surface for custom rendering (TinyVG, SVG, or direct pixel operations).

```html
<canvas grow="1" bg="#000000" id="canvas0"/>
```

### `<slider>`

Value slider control.

```html
<slider min="0" max="100" value="50" action="vol.change" grow="1" height="20"/>
```

### `<progress>`

Progress bar.

```html
<progress value="75" max="100" grow="1" height="16" fg="#00CC66" bg="#1C1C2E"/>
```

### `<image>`

Image display widget.

```html
<image src="icon.tvg" width="32" height="32"/>
```

### `<tabs>` / `<tab>`

Tabbed container.

```html
<tabs grow="1">
  <tab label="Files">
    <panel layout="vbox" grow="1" id="filelist"/>
  </tab>
  <tab label="Search">
    <panel layout="vbox" grow="1" id="searchresults"/>
  </tab>
</tabs>
```

---

## 7. IPC Message Reference

### Client to Server

**Register:**
```json
{"method": "register", "service": "myapp"}
```

**Create Window:**
```json
{
  "method": "window.create",
  "title": "My App",
  "w": 640,
  "h": 480,
  "html": "config/myapp.html"
}
```

**Set Label (update text of a widget by ID):**
```json
{
  "method": "window.setlabel",
  "win_id": 1,
  "id": "status",
  "text": "Connected"
}
```

**Add Line (append text to a panel):**
```json
{
  "method": "window.addline",
  "win_id": 1,
  "target": "results",
  "text": "Found: main.ailang",
  "color": 65416
}
```
Color is an integer: `0x00FF88` = 65416 (green).

**Clear Panel:**
```json
{
  "method": "window.clear",
  "win_id": 1,
  "target": "results"
}
```

### Server to Client

**Window Created:**
```json
{"method": "window.created", "win_id": 1}
```

**Window Closed (user clicked X):**
```json
{"method": "window.closed", "win_id": 1}
```

**Button Click:**
```json
{
  "method": "input.action",
  "action": "g.run",
  "action_len": 5
}
```

**Keyboard Input:**
```json
{
  "method": "input.key",
  "keycode": 28,
  "char": 13,
  "shift": 0
}
```

Common keycodes:
| Keycode | Key |
|---------|-----|
| 14 | Backspace |
| 28 | Enter |
| 1 | Escape |
| 15 | Tab |
| 57 | Space |
| 103 | Arrow Up |
| 108 | Arrow Down |
| 105 | Arrow Left |
| 106 | Arrow Right |

`char` contains the ASCII value for printable characters (32-126).

---

## 8. Database Integration

Applications can connect to PostgreSQL directly for persistent storage.

### Connect

```ailang
LibraryImport.PostgreSQL_Complete

conn = PG_Connect("127.0.0.1", 5432, "ailang_system", "bob", "")
IfCondition EqualTo(conn, 0) ThenBlock: {
    PrintMessage("Cannot connect to PostgreSQL\n")
    ReturnValue(0)
}
```

### Query

```ailang
result = PG_Query(conn, "SELECT name, display_name FROM services WHERE enabled = true")
IfCondition NotEqual(result, 0) ThenBlock: {
    count = Array.Size(result)
    i = 0
    WhileLoop LessThan(i, count) {
        row = Array.Get(result, i)
        name = Hash.Get(row, "name")
        display = Hash.Get(row, "display_name")
        PrintMessage(name)
        PrintMessage(" - ")
        PrintMessage(display)
        PrintMessage("\n")
        i = Add(i, 1)
    }
    PG_DestroyResult(result)
}
```

### Insert/Update

```ailang
r = PG_Query(conn, "INSERT INTO settings (app_id, key, value) VALUES ('myapp', 'theme', 'dark') ON CONFLICT (app_id, key) DO UPDATE SET value = 'dark'")
IfCondition NotEqual(r, 0) ThenBlock: {
    PG_DestroyResult(r)
}
```

### Schema Tables Available

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `services` | Service registry | name, binary_path, enabled, priority, autostart |
| `service_status` | Runtime state | service_name, pid, state |
| `users` | Accounts | username, password_hash, is_admin |
| `sessions` | Login tracking | user_id, active, tty |
| `files` | Virtual filesystem | name, parent_id, type, blob_uuid |
| `settings` | App config | app_id, key, value |
| `packages` | Package registry | name, binary_name, has_binary, installed |

### Disconnect

```ailang
PG_Disconnect(conn)
```

---

## 9. Fork/Exec Pattern

To launch external processes from within an AILang application:

```ailang
Function.RunCommand {
    Input: cmd_path: Address
    Input: argv: Address
    Output: Integer
    Body: {
        pid = SystemCall(57, 0, 0, 0, 0, 0)   // SYS_FORK

        IfCondition EqualTo(pid, 0) ThenBlock: {
            // Child process — close inherited file descriptors
            fd_close = 3
            WhileLoop LessThan(fd_close, 64) {
                SystemCall(3, fd_close)         // SYS_CLOSE
                fd_close = Add(fd_close, 1)
            }

            // Build minimal environment
            envp = Allocate(8)
            StoreValue(envp, 0)

            // Replace process with target binary
            SystemCall(59, cmd_path, argv, envp, 0, 0)  // SYS_EXECVE
            SystemCall(60, 127)                          // exit if execve fails
        }

        // Parent process — wait for child
        status_buf = Allocate(8)
        StoreValue(status_buf, 0)
        SystemCall(61, pid, status_buf, 0, 0, 0)   // SYS_WAIT4
        wstatus = Dereference(status_buf)
        exit_code = BitwiseAnd(Divide(wstatus, 256), 255)
        Deallocate(status_buf, 8)
        ReturnValue(exit_code)
    }
}
```

### Building argv

```ailang
// Example: ls -la /tmp
argv = Allocate(32)                    // 4 pointers x 8 bytes
StoreValue(Add(argv, 0),  "/bin/ls")
StoreValue(Add(argv, 8),  "-la")
StoreValue(Add(argv, 16), "/tmp")
StoreValue(Add(argv, 24), 0)          // NULL terminator
rc = RunCommand("/bin/ls", argv)
Deallocate(argv, 32)
```

### Background Daemon (no wait)

```ailang
Function.StartDaemon {
    Input: cmd_path: Address
    Input: argv: Address
    Output: Integer
    Body: {
        pid = SystemCall(57, 0, 0, 0, 0, 0)
        IfCondition EqualTo(pid, 0) ThenBlock: {
            // Child: close FDs, setsid, execve
            fd_close = 3
            WhileLoop LessThan(fd_close, 64) {
                SystemCall(3, fd_close)
                fd_close = Add(fd_close, 1)
            }
            SystemCall(112)                     // SYS_SETSID
            envp = Allocate(8)
            StoreValue(envp, 0)
            SystemCall(59, cmd_path, argv, envp, 0, 0)
            SystemCall(60, 127)
        }
        ReturnValue(pid)                        // Return PID to parent
    }
}
```

---

## 10. Vector Graphics

AILang OS supports two vector graphics formats.

### SVG

The `Library.SVG.ailang` module provides a full SVG parser and software rasterizer:

- Path elements (`<path d="M 10 10 L 90 90"/>`)
- Basic shapes (rect, circle, ellipse, line, polygon, polyline)
- Gradients (linear and radial)
- Transforms (translate, rotate, scale, matrix)
- Named colors and hex color codes
- Stroke and fill with opacity

SVG content can be rendered to surfaces which are then composited into windows by the display server.

### TinyVG (VIF)

The `Library.VIF.ailang` module handles the binary TinyVG vector format, which is more compact than SVG. TinyVG images can be used for icons and UI elements through the `<image>` widget.

Both formats integrate with the display server's compositing pipeline and are rasterized at the target resolution.

---

## 11. Library Reference

### Core Libraries

| Library | Import | Description |
|---------|--------|-------------|
| Arena | `LibraryImport.Arena` | Memory allocation (`Allocate`, `Deallocate`) |
| Socket | `LibraryImport.Socket` | Unix/TCP sockets, `SendMsg`/`RecvMsg` with length prefix |
| StringUtils | `LibraryImport.StringUtils` | String operations |
| JSON | `LibraryImport.JSON` | JSON parse/build (`NewObject`, `SetString`, `SetNumber`, `SerializeObject`) |
| Arrays | `LibraryImport.Arrays` | Dynamic arrays (`Array.New`, `Array.Push`, `Array.Get`, `Array.Size`) |
| Hash | `LibraryImport.Hash` | Hash maps (`Hash.New`, `Hash.Set`, `Hash.Get`) |
| PostgreSQL_Complete | `LibraryImport.PostgreSQL_Complete` | Full PG wire protocol driver |
| HTTP | `LibraryImport.HTTP` | HTTP client |
| Regex_Thompson | `LibraryImport.Regex_Thompson` | NFA-based regex engine |
| CSV | `LibraryImport.CSV` | CSV parsing |
| RESP | `LibraryImport.RESP` | Redis protocol |
| Math | `LibraryImport.Math` | Basic math functions |
| LinearAlgebra | `LibraryImport.LinearAlgebra` | Matrix and vector operations |
| FixedPointTrig | `LibraryImport.FixedPointTrig` | Trigonometry without floating point |
| TimeDate | `LibraryImport.TimeDate` | Date/time formatting and arithmetic |
| TextBuffer | `LibraryImport.TextBuffer` | Gap buffer for text editing |
| MessagePort | `LibraryImport.MessagePort` | Inter-process message passing |
| OAuth | `LibraryImport.OAuth` | OAuth 2.0 authentication flows |

### Display Libraries (used by display server)

| Library | Description |
|---------|-------------|
| Display.Render.Framebuffer | Framebuffer I/O |
| Display.Render.DRenderFB | Frame rendering pipeline |
| Display.UI.Auckland | Layout solver (hbox/vbox flex) |
| Display.UI.AucklandBind | HTML-to-layout binding |
| Display.Content.HTMLParse | HTML/XML parser |
| Display.Content.SVG | SVG rasterizer |
| Display.Window.WinManager | Window lifecycle |
| Display.IPC.IPCBroker | IPC message routing |
| Display.Input.DInputEvdev | evdev input discovery |

---

## 12. Compiling and Deploying

### Compile

```bash
# Compile an application
./ailang.x Applications/myapp_ipc.ailang -o myapp.x

# Compile an OS module
./ailang.x OS/Init.ailang -o ailang_init.x
```

The compiler resolves imports automatically, handles namespace conflicts, and produces a standalone ELF binary.

### Deploy to the OS

Copy the binary to the system directory:

```bash
cp myapp.x /system/bin/myapp.x
```

Copy the HTML config:

```bash
cp config/myapp.html /config/myapp.html
cp config/myapp.html /system/config/myapp.html
```

### Register as a Service

Add your app to the `services` table so it appears in the Start Menu:

```sql
INSERT INTO services (name, display_name, binary_path, enabled, priority)
VALUES ('myapp', 'My App', '/system/bin/myapp.x', true, 50)
ON CONFLICT (name) DO UPDATE SET binary_path='/system/bin/myapp.x';
```

Or add it to `OS/Installer.ailang` in the `Inst_SeedAllServices` function for automatic registration on first boot.

### Register as a Package

Add your app to the `packages` table for the package manager:

```sql
INSERT INTO packages (name, display_name, category, binary_name, binary_path, html_config, priority, depends_on)
VALUES ('myapp', 'My App', 'app', 'myapp.x', '/system/bin/myapp.x', 'myapp.html', 50, 'display_server')
ON CONFLICT (name) DO UPDATE SET display_name='My App';
```

### Complete Example: Minimal Counter App

**config/counter.html:**
```html
<window title="Counter" design-w="300" design-h="200" toolbar="about">
  <group layout="vbox" gap="4" padding="8" bg="#2D2D44">
    <label text="0" fg="#00FF88" text-align="center" grow="1" font-size="48" id="count"/>
    <separator height="1" fg="#444444"/>
    <group layout="hbox" gap="4" height="32">
      <button label="-" action="c.dec" grow="1" height="28" bg="#FF5555" fg="#FFFFFF"/>
      <button label="Reset" action="c.rst" grow="1" height="28" bg="#3D3D50" fg="#E0E0E0"/>
      <button label="+" action="c.inc" grow="1" height="28" bg="#00CC66" fg="#FFFFFF"/>
    </group>
  </group>
</window>
```

**Applications/counter_ipc.ailang:**
```ailang
LibraryImport.Arena
LibraryImport.Socket
LibraryImport.StringUtils
LibraryImport.JSON
LibraryImport.Arrays
LibraryImport.Hash

FixedPool.CtrState {
    "running": Initialize=1, CanChange=True
    "win_id":  Initialize=0, CanChange=True
    "sock":    Initialize=0, CanChange=True
    "count":   Initialize=0, CanChange=True
}

Function.Ctr_UpdateDisplay {
    Input: sock: Integer
    Body: {
        // Convert count to string
        buf = Allocate(16)
        // ... number-to-string conversion ...
        req = JSON.NewObject()
        JSON.SetString(req, "method", "window.setlabel")
        JSON.SetNumber(req, "win_id", CtrState.win_id)
        JSON.SetString(req, "id", "count")
        JSON.SetString(req, "text", buf)
        msg = JSON.SerializeObject(req)
        Socket.SendMsg(sock, msg)
        JSON.Free(req)
        Deallocate(buf, 16)
    }
}

SubRoutine.Main {
    Arena_Init()
    sock = Socket.Create(1, 1)
    Socket.ConnectUnix(sock, "/tmp/ailang_display.sock")
    CtrState.sock = sock

    Socket.SendMsg(sock, "{\"method\":\"register\",\"service\":\"counter\"}")
    Socket.SendMsg(sock, "{\"method\":\"window.create\",\"title\":\"Counter\",\"w\":300,\"h\":200,\"html\":\"config/counter.html\"}")

    resp = Socket.RecvMsg(sock)
    parsed = ParseJSON(resp)
    pobj = JSON.AsObject(parsed)
    CtrState.win_id = JSON.GetNumber(pobj, "win_id")
    JSON.Free(parsed)

    WhileLoop EqualTo(CtrState.running, 1) {
        msg = Socket.RecvMsg(sock)
        IfCondition EqualTo(msg, 0) ThenBlock: {
            CtrState.running = 0
        } ElseBlock: {
            pmsg = ParseJSON(msg)
            mobj = JSON.AsObject(pmsg)
            method = JSON.GetString(mobj, "method")

            cmp = StringCompare(method, "window.closed")
            IfCondition EqualTo(cmp, 0) ThenBlock: { CtrState.running = 0 }

            cmp2 = StringCompare(method, "input.action")
            IfCondition EqualTo(cmp2, 0) ThenBlock: {
                action = JSON.GetString(mobj, "action")

                ac = StringCompare(action, "c.inc")
                IfCondition EqualTo(ac, 0) ThenBlock: {
                    CtrState.count = Add(CtrState.count, 1)
                    Ctr_UpdateDisplay(sock)
                }

                ac2 = StringCompare(action, "c.dec")
                IfCondition EqualTo(ac2, 0) ThenBlock: {
                    CtrState.count = Subtract(CtrState.count, 1)
                    Ctr_UpdateDisplay(sock)
                }

                ac3 = StringCompare(action, "c.rst")
                IfCondition EqualTo(ac3, 0) ThenBlock: {
                    CtrState.count = 0
                    Ctr_UpdateDisplay(sock)
                }
            }

            JSON.Free(pmsg)
        }
    }

    Socket.Close(sock)
    SystemCall(60, 0)
    RunTask(Main)
}
```

**Build and deploy:**
```bash
./ailang.x Applications/counter_ipc.ailang -o counter.x
cp counter.x /system/bin/
cp config/counter.html /config/
```

---

## License

Copyright 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved. SCSL.
