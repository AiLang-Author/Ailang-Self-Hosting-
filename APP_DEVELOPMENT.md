# Ailang Application Development Guide

## Overview

Ailang applications run as **standalone long-running binaries** that communicate with the display server over IPC (Unix socket). The display server handles all rendering, layout, and input — the app binary handles all business logic. Neither side imports or knows about the other's internals.

This model means that once a logic library exists (calculator arithmetic, video decoding, file management, etc.), building a graphical app is mostly writing an HTML layout file and a thin IPC service loop.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Display Server (SysDisplay.x)                               │
│                                                              │
│  PostgreSQL ──► Service catalog (what apps exist)            │
│  IPCBroker  ──► Unix socket listener + client routing        │
│  AppHost    ──► HTML → Auckland widget tree (layout engine)   │
│  Auckland   ──► Rendering, mouse events, action dispatch     │
│  WinManager ──► Window chrome, borders, compositing          │
│                                                              │
│  The display server imports ZERO app-specific code.          │
└──────────────────────────┬───────────────────────────────────┘
                           │  /tmp/ailang_display.sock
                           │  (4-byte BE length prefix + JSON)
┌──────────────────────────┴───────────────────────────────────┐
│  App Binary (e.g. calc_ipc.x)                                │
│                                                              │
│  IPC glue       ──► Connect, register, service loop (~50 LOC)│
│  Logic library  ──► Business logic (Calculator, FFmpeg, etc.)│
│  Action→JSON    ──► Translate UI actions to logic calls       │
│                                                              │
│  The app binary knows nothing about rendering or layout.     │
└──────────────────────────────────────────────────────────────┘
```

## App Lifecycle

### 1. Launch

The display server fork/execs the app binary when a user clicks its entry in the Start Menu. The binary path comes from the PostgreSQL `services` table.

### 2. Connect + Register

The app connects to `/tmp/ailang_display.sock` and identifies itself:

```json
{"method":"register","service":"calculator"}
```

The display server looks up the service name in its cached service table and associates the connection with a service ID.

### 3. Request a Window

The app sends a window creation request, referencing an HTML layout file:

```json
{"method":"window.create","title":"Calculator","w":280,"h":380,"html":"config/calculator.html"}
```

The display server:
- Parses the HTML file via AppHost
- Builds an Auckland widget tree (buttons, labels, layout containers)
- Creates a window with chrome, borders, and toolbar (from `toolbar=` attribute)
- Renders the initial UI
- Responds with: `{"method":"window.created","win_id":3}`

### 4. Service Loop

The app blocks on `Socket.RecvMsg`, waiting for messages from the display server. Two message types arrive:

**Button clicks** — when the user clicks a button in the app's window, the display server extracts the action string from the Auckland tree and forwards it:

```json
{"method":"input.action","win_id":3,"action":"c.5","action_len":3}
```

The app:
1. Translates the action string to a logic call (e.g., `"c.5"` → `digit(5)`)
2. Executes the logic
3. Sends a display update back:

```json
{"method":"window.update","win_id":3,"display":"25+17"}
```

The display server updates the label widget in the Auckland tree and re-renders.

**Window closed** — when the user closes the window via the toolbar X button:

```json
{"method":"window.closed","win_id":3}
```

The app cleans up and exits.

### 5. Shutdown

On receiving `window.closed`, the app closes its socket and calls `exit(0)`. The display server detects the disconnect (poll POLLHUP), removes the client from the broker table, and reaps the child process.

## IPC Protocol

All messages are length-prefixed JSON over a Unix domain socket.

### Wire Format

```
[4 bytes: big-endian message length][N bytes: JSON payload]
```

### App → Display Server

| Method | JSON | Purpose |
|--------|------|---------|
| `register` | `{"method":"register","service":"calculator"}` | Identify app to server |
| `window.create` | `{"method":"window.create","title":"Calc","w":280,"h":380,"html":"config/calculator.html"}` | Request window creation |
| `window.update` | `{"method":"window.update","win_id":N,"display":"25+17"}` | Update display label |

### Display Server → App

| Method | JSON | Purpose |
|--------|------|---------|
| `window.created` | `{"method":"window.created","win_id":N}` | Confirm window, provide ID |
| `window.closed` | `{"method":"window.closed","win_id":N}` | User closed window |
| `input.action` | `{"method":"input.action","win_id":N,"action":"c.5","action_len":3}` | Button click forwarded |

## HTML Layout Files

The display server uses HTML-like config files to define window layout. These are parsed by `AppHost` and converted to an Auckland widget tree.

### Window Root Tag

The `<window>` tag defines the window and its toolbar:

```html
<window title="Calculator" design-w="280" design-h="380" toolbar="about">
```

| Attribute | Required | Description |
|-----------|----------|-------------|
| `title` | Yes | Window title, shown in toolbar and deskbar |
| `design-w` | Yes | Design width in logical pixels |
| `design-h` | Yes | Design height in logical pixels |
| `toolbar` | No | Toolbar preset (default: `about`) |

### Toolbar Presets

The `toolbar=` attribute controls which buttons appear in the window toolbar:

| Value | Buttons | Use Case |
|-------|---------|----------|
| `none` | No toolbar at all | Full-screen apps, games |
| `about` | [About] [spacer] [title] [X] | Simple apps (calculator, settings) |
| `file` | [File] [About] [spacer] [title] [X] | Apps with file operations |
| `full` | [File] [Edit] [View] [About] [spacer] [title] [X] | Full document editors |

The About button is the mandatory minimum for any toolbar. The Close (X) button is always present. Toolbar actions (`win.close`, `app.about`, `menu:file`, etc.) are handled by the display server — they are never forwarded to the app process.

### Action String Namespaces

Action strings use prefixes to determine routing:

| Prefix | Handled By | Examples |
|--------|-----------|----------|
| `win.` | Display server | `win.close`, `win.new` |
| `app.` | Display server | `app.about`, `app.quit`, `app.home` |
| `menu:` | Display server | `menu:file`, `menu:edit` |
| `sys.` | Display server | `sys.screenshot` |
| `fd.` | Display server | `fd.open`, `fd.cancel` |
| Everything else | App process via IPC | `c.5`, `c.add`, `m.go` |

App-specific actions should use a short prefix unique to the app (e.g., `c.` for calculator, `m.` for a custom app).

### Layout Example: `config/calculator.html`

```html
<window title="Calculator" design-w="280" design-h="380" toolbar="about">
  <group layout="vbox" gap="4" padding="8" bg="#1C1C2E">
    <panel height="56" bg="#0D1117" padding="8">
      <label text="0" fg="#00FF88" text-align="right" height="40"
             font-size="24" id="display"/>
    </panel>
    <group layout="hbox" gap="4">
      <button label="C"   action="c.clr" grow="1" height="52"
              bg="#3D3D50" fg="#E0E0E0"/>
      <button label="+/-" action="c.neg" grow="1" height="52"
              bg="#3D3D50" fg="#E0E0E0"/>
      <button label="%"   action="c.pct" grow="1" height="52"
              bg="#3D3D50" fg="#E0E0E0"/>
      <button label="/"   action="c.div" grow="1" height="52"
              bg="#FF9500" fg="#FFFFFF"/>
    </group>
    <!-- ... more rows of buttons ... -->
  </group>
</window>
```

**Key points:**
- `action="c.5"` — the action string sent to the app when this button is clicked
- Action strings are app-defined. The display server treats them as opaque bytes.
- Layout uses `vbox`, `hbox` containers via `<group layout="...">`. Auckland handles measurement and positioning.
- Colors are per-widget. The display server renders them — the app never touches pixels.
- `grow="1"` makes buttons share available space equally within their row.
- `id="display"` marks the label that `window.update` targets.

## Building a New App: Step by Step

### Step 1: Create the Logic Library

Write pure business logic with no UI or IPC code. Expose a JSON-based handler.

```
// Librarys/Library.MyApp.ailang

Function.MyApp_JsonHandle {
    Input: json_str: Address
    Input: json_len: Integer
    Output: Address          // returns JSON response string
    Body: {
        parsed = ParseJSON(json_str)
        method = JSON.GetString(parsed, "method")
        // ... dispatch to logic functions ...
        // ... build response JSON ...
        ReturnValue(response)
    }
}
```

Test the logic independently with a standalone test binary before adding IPC.

### Step 2: Create the HTML Layout

Define the window UI in an HTML config file under `config/`.

```html
<window title="My App" design-w="400" design-h="300" toolbar="about">
  <group layout="vbox" gap="4" padding="8" bg="#2A2A3C">
    <label id="status" text="Ready" height="32" fg="#E0E0E0"/>
    <group layout="hbox" gap="4">
      <button label="Go"    action="m.go"   grow="1" height="40"
              bg="#2D5F2D" fg="#FFFFFF"/>
      <button label="Stop"  action="m.stop" grow="1" height="40"
              bg="#5F2D2D" fg="#FFFFFF"/>
    </group>
  </group>
</window>
```

### Step 3: Create the IPC Service Binary

The service binary has three parts:

**A. Boilerplate** (same for every app, ~50 lines):
- Connect to `/tmp/ailang_display.sock`
- Send `register` message
- Send `window.create` with your HTML file
- Receive `window.created` response
- Enter service loop: recv → dispatch → send response
- Exit on `window.closed`

**B. Action translation** (app-specific):
- Convert action strings from the HTML buttons to JSON for your logic library
- e.g., `"m.go"` → `{"method":"start"}` or `"c.5"` → `{"method":"digit","value":5}`

**C. Logic library import**:
- `LibraryImport.MyApp`
- Call `MyApp_JsonHandle(json, len)` on each `input.action`

### Step 4: Register in PostgreSQL

Add a row to the `services` table. The display server seeds defaults on startup:

```sql
INSERT INTO services (name, display_name, binary_path, enabled, priority)
VALUES ('myapp', 'My App', './myapp.x', true, 20)
ON CONFLICT (name) DO UPDATE SET binary_path = './myapp.x';
```

- `binary_path` is the path to the compiled binary (fork/exec'd by the display server)
- `display_name` appears in the Start Menu
- `priority` controls sort order in the Start Menu (lower = higher)

### Step 5: Build and Run

```bash
# Build the app binary
./ailang.x Testcode/myapp_ipc.ailang myapp.x

# Build the display server (if service seed SQL changed)
./ailang.x Main.ailang SysDisplay.x

# Run on TTY
sudo ./SysDisplay.x
# Click "Home" → "My App" in the Start Menu
```

## Display State: Expression Buffers

Apps that build up state incrementally (like a calculator expression) should maintain a display buffer and return the full expression string in `window.update`, not just the current value.

**Pattern:**
1. Allocate a buffer (e.g., 64 bytes) at init time
2. Append characters as the user enters them (digits, operators)
3. On `=` (evaluate), replace the buffer with the result
4. On `C` (clear), reset to `"0"`
5. Return the buffer contents as the `"display"` field in `window.update`

**Example flow:**
```
User clicks: 2, 5, +, 1, 7, =
Display shows: "2" → "25" → "25+" → "25+1" → "25+17" → "42"
```

The display server renders whatever string the app sends — it does not interpret it.

## Headless Testing

Apps and the display server can be tested without a real framebuffer using `FB_InitHeadless`:

```
// In your test binary, override RenderFB_InitDouble:
Function.RenderFB_InitDouble {
    Output: Integer
    Body: {
        FB_InitHeadless(1920, 1080)
        ReturnValue(1)
    }
}
```

This allocates an anonymous mmap buffer instead of opening `/dev/fb0`. The real framebuffer is the default path — test binaries opt into headless mode by overriding `RenderFB_InitDouble`. No comment-swapping or config changes needed.

**Example:** `TestCode/test_main.ailang` uses this pattern for automated resize, debug overlay, Start Menu, and IPC integration tests (34 test steps).

## What Goes Where

| Concern | Owner | Example |
|---------|-------|---------|
| Window layout, buttons, colors | HTML config file | `config/calculator.html` |
| Toolbar preset declaration | HTML `toolbar=` attribute | `toolbar="about"` |
| Toolbar rendering + system actions | Display server (WinToolbar) | `Library.WinToolbar.ailang` |
| Widget rendering, font raster | Display server (Auckland) | `Library.Auckland.ailang` |
| Mouse/keyboard to action string | Display server (AK_EventMouse) | `Library.AucklandEvent.ailang` |
| System action handling | Display server (EventRouter) | `win.close`, `app.about` |
| App action relay to process | Display server (IPCBroker) | `Library.IPCBroker.ailang` |
| Action string → logic call | App binary | `calc_ipc.ailang:CalcIPC_ActionToJSON` |
| Business logic | Logic library | `Library.Calculator.ailang` |
| Display update text | App binary → IPC → display server | `window.update` message |
| Service catalog | PostgreSQL | `services` table |
| Process launch | Display server (fork/exec) | `Library.Deskbar.ailang` |

## Reference Implementation

The calculator is the complete reference for the app development model:

| Component | File | Purpose |
|-----------|------|---------|
| Logic library | `Librarys/Library.Calculator.ailang` | Pure arithmetic engine with expression buffer. 10/10 standalone tests. |
| HTML layout | `config/calculator.html` | 4x5 button grid + display label, `toolbar="about"` |
| IPC service | `Testcode/calc_ipc.ailang` | Full IPC lifecycle. Connect, register, window, service loop. |
| Standalone tests | `Calc.ailang` | Tests logic library independently (no IPC, no display server). |
| DB seed | `Library.SysDisplay.ailang` | `binary_path = './calc_ipc.x'` |
| Headless tests | `TestCode/test_main.ailang` | IPC integration tests with `FB_InitHeadless` |

## Design Principles

1. **Display server imports zero app code.** Ever. Apps are standalone binaries.
2. **Apps know nothing about rendering.** No pixel manipulation, no surface allocation, no font calls.
3. **PostgreSQL is for service discovery only.** What apps exist, how to launch them. All runtime data flows through IPC.
4. **HTML defines layout, not behavior.** Action strings are opaque to the display server.
5. **Toolbar actions are display-server commands.** `win.close`, `app.about`, `menu:file` are never forwarded to app processes.
6. **Logic libraries are testable independently.** Build a standalone test binary (e.g., `Calc.x`) before adding IPC.
7. **IPC boilerplate is minimal.** The connect/register/loop pattern is ~50 lines. App-specific code is the action-to-JSON translation.
8. **Test without hardware.** Use `FB_InitHeadless` in test binaries to run the full display pipeline against an anonymous memory buffer.
