# 05 — Input System: Evdev, Cursor, IPCBroker, Device Discovery

> **Copyright © 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved. SCSL.**

---

## 1. Overview

The Input System bridges the Linux kernel's evdev interface to the display server. It discovers input devices, reads raw events, routes them through the appropriate channels (local dispatch or IPC forwarding), and renders a software cursor. It also provides the IPC broker for communication with external application processes.

### Components

| Component | Source File | Lines | Role |
|-----------|------------|-------|------|
| **DInputTypes** | `Library.DInputTypes.ailang` | ~250 | Linux evdev structs, key codes, mouse state |
| **DInputEvdev** | `Library.DInputEvdev.ailang` | ~350 | Evdev read/poll, key/mouse event processing |
| **DInputDiscover** | `Library.DInputDiscover.ailang` | ~400 | Device discovery (by-id + /proc fallback) |
| **Cursor** | `Library.Cursor.ailang` | ~350 | Cursor save/restore/draw, shape switching |
| **CursorBitmap** | `Library.CursorBitmap.ailang` | ~350 | Bitmap cursor masks (4 shapes) |
| **InputRouter** | `Librarys/deprecated/Library.InputRouter.ailang` | ~200 | ☠️ DEAD/VESTIGIAL — Ring1 drain; functionally replaced by EventRouter |
| **IPCBroker** | `Library.IPCBroker.ailang` | ~1000 | Inter-process communication broker |

---

## 2. DInputTypes — Kernel Structures

### 2.1 Evdev Event Structure

Mirrors the Linux kernel's `struct input_event`:

```
InputEvent (16 bytes):
    [0-3]  tv_sec    — Seconds (struct timeval)
    [4-7]  tv_usec   — Microseconds
    [8-9]  type      — Event type (EV_KEY=1, EV_REL=2, EV_ABS=3, etc.)
    [10-11] code     — Event code (key/button/axis code)
    [12-15] value    — Event value (0=release, 1=press, 2=repeat for keys)
```

### 2.2 Event Types

```
EV_SYN = 0x00    — Sync/separator event
EV_KEY = 0x01    — Key/button state change
EV_REL = 0x02    — Relative axis change (mouse movement)
EV_ABS = 0x03    — Absolute axis (touchscreen, tablet)
EV_MSC = 0x04    — Miscellaneous
```

### 2.3 Mouse State

```
MouseState:
    x, y          — Current cursor position (absolute screen coords)
    btn_left      — Left button state (0=up, 1=down)
    btn_right     — Right button state
    btn_middle    — Middle button state
    wheel_delta   — Accumulated wheel delta
```

### 2.4 Key Map

Key codes from the Linux input layer are mapped to ASCII characters via the `KeyMap` library. Special keys (Alt, Ctrl, Shift, F-keys, ESC) are handled as modifiers or hotkeys.

---

## 3. DInputEvdev — Event Reading

### 3.1 Device Open (`Evdev_OpenDevice`)

Opens a Linux evdev device node in non-blocking mode:

```
Evdev_OpenDevice(path):
    fd = open(path, O_RDONLY | O_NONBLOCK)
    if fd < 0: return -1
    ioctl(fd, EVIOCGRAB, 1)    — Grab exclusive access
    Store fd in device table
    Return fd
```

Device grab prevents other processes (like the Linux console) from receiving the same input events.

### 3.2 Event Poll (`Evdev_Poll`)

Called once per frame from the main loop:

```
Evdev_Poll():
    For each open device:
        bytes = read(fd, event_buffer, sizeof(InputEvent) * MAX_EVENTS)
        For each complete InputEvent in buffer:
            Evdev_ProcessEvent(device_idx, &event)
```

### 3.3 Event Processing (`Evdev_ProcessEvent`)

```
Evdev_ProcessEvent(dev_idx, event):
    switch event.type:
        EV_KEY:
            if event.code == BTN_LEFT/MIDDLE/RIGHT:
                Update MouseState buttons
                if press: push Ring1Event.MOUSE_DOWN to Ring1
                if release: push Ring1Event.MOUSE_UP to Ring1
            else:
                Evdev_HandleKey(dev_idx, event.code, event.value)
        EV_REL:
            if REL_X or REL_Y:
                Evdev_HandleRel(dev_idx, event.code, event.value)
        EV_SYN:
            if accumulated motion: push Ring1Event.MOUSE_MOVE to Ring1
            if accumulated wheel: push Ring1Event.MOUSE_WHEEL to Ring1
```

### 3.4 Key Handling (`Evdev_HandleKey`)

```
Evdev_HandleKey(dev_idx, code, value):
    if value == 1 (press):
        push Ring1Event.KEY_DOWN to Ring1
    else if value == 0 (release):
        push Ring1Event.KEY_UP to Ring1
    // value == 2 (repeat) is handled by the host, not forwarded
```

### 3.5 Relative Motion (`Evdev_HandleRel`)

```
Evdev_HandleRel(dev_idx, code, value):
    if code == REL_X: MouseState.x += value * accel_factor
    if code == REL_Y: MouseState.y += value * accel_factor
    if code == REL_WHEEL: MouseState.wheel_delta += value

    // Clamp to screen bounds
    MouseState.x = clamp(MouseState.x, 0, screen_w - 1)
    MouseState.y = clamp(MouseState.y, 0, screen_h - 1)
```

### 3.6 Mouse Bounds

`Evdev_SetMouseBounds(w, h)` updates the clamping bounds when the screen resolution changes.

---

## 4. DInputDiscover — Device Discovery

### 4.1 Discovery Strategy

Two-tier discovery:

**Tier 1 — by-id (preferred):**
```
Discover_FindDevices():
    1. List /dev/input/by-id/ directory
    2. Filter for *-kbd (keyboard) and *-mouse entries
    3. Read symlink targets to get /dev/input/eventN paths
    4. Return list of device paths
```

**Tier 2 — /proc fallback:**
```
Discover_FindDevicesFallback():
    1. Read /proc/bus/input/devices
    2. Parse "H: Handlers=" lines for eventN
    3. Parse "B: EV=" for capability bits
    4. Match keyboards (EV=120013) and mice
    5. Build /dev/input/eventN paths
```

### 4.2 Path Building

```
Disc_BuildByIdPath(name):
    return "/dev/input/by-id/" + name

Disc_ReadLink(path):
    readlink(path) → get target eventN path
```

### 4.3 Open All (`Discover_OpenAll`)

Calls `Evdev_OpenDevice` for each discovered device. Falls back to hardcoded `/dev/input/event0` through `/dev/input/event5` if discovery yields nothing.

---

## 5. Cursor — Software Cursor

### 5.1 Design

The display system uses a **software cursor** — no hardware cursor support. The cursor is rendered by saving the pixels under the cursor position, drawing the cursor shape, and restoring the saved pixels when the cursor moves. This approach works on any framebuffer, regardless of hardware cursor capabilities.

### 5.2 Cursor Shapes

Four bitmap shapes from `CursorBitmap`:

| Shape | Index | Description |
|-------|-------|-------------|
| Arrow | 0 | Standard pointer (default) |
| I-Beam | 1 | Text input cursor |
| Resize | 2 | Diagonal resize arrows |
| Hand | 3 | Link/click hand pointer |

Each shape is a 32×32 monochrome bitmap with a 32×32 alpha mask. Black pixels in the mask are transparent; white pixels are opaque.

### 5.3 Cursor State Machine

```
CursorState:
    x, y           — Current cursor position
    shape          — Current shape index
    saved[]        — Saved pixel buffer (32×32 BGRA)
    saved_x        — X position of saved pixels
    saved_y        — Y position of saved pixels
    visible        — Cursor visibility flag
```

### 5.4 Key Functions

| Function | Description |
|----------|-------------|
| `Cursor_Init()` | Allocate save buffer, set default shape |
| `Cursor_SetPos(x, y)` | Update cursor position |
| `Cursor_SetShape(shape)` | Switch cursor shape |
| `Cursor_Save(x, y)` | Save 32×32 pixels under cursor |
| `Cursor_Restore()` | Restore saved pixels to framebuffer |
| `Cursor_Draw()` | Restore old, save new, draw cursor at current pos |
| `Cursor_BlitMask(surf, dx, dy)` | Blit cursor bitmap with alpha mask |

### 5.5 Draw Cycle

Called at the end of each frame's composition:

```
Cursor_Draw():
    1. Cursor_Restore()            — Put back pixels from last position
    2. Cursor_Save(x, y)           — Save pixels at new position
    3. Cursor_BlitMask(fb, x, y)   — Draw cursor shape with alpha mask
```

The save buffer is 32×32 pixels × 4 bytes = 4096 bytes.

---

## 6. InputRouter — ☠️ DEAD/VESTIGIAL

> **⚠️ InputRouter is functionally dead.** Its former role (draining Ring1 and dispatching key/mouse events) has been absorbed by `EventRouter` and `SysDisplay_DrainInput`. The file remains at `Librarys/deprecated/Library.InputRouter.ailang` for reference but is not imported by the current display server.

### 6.1 Original Design (preserved for archaeology)

InputRouter drained Ring1 (the input event ring buffer) and forwarded events:

```
InputRouter_Drain():
    While Ring1 has entries:
        event = Ring1_Pop()
        if event.type == KEY_DOWN:
            if focused_window has IPC binding:
                IPCBroker_SendKey(focused, keycode)
            else:
                Win_KeyDown(focused, keycode)
        if event.type == MOUSE_MOVE:
            Cursor_SetPos(x, y)
            Post to SysDisplay drain queue
```

Global hotkeys intercepted before per-window routing:
- **F12** → Toggle DebugLog overlay
- **F11** → Toggle fullscreen
- **Alt+V** → Create new window
- **ESC** → Close menus / quit

---

## 7. IPCBroker — Inter-Process Communication

### 7.1 Architecture

IPCBroker manages Unix domain socket connections to external application processes. Each app runs as a separate process and communicates with the display server via a simple message protocol over a socket pair.

### 7.2 Client Management

```
IPCBroker:
    listen_fd           — Server socket fd
    clients[16]         — Connected client slots
    client_count        — Active client count

IPCClient (per connection):
    fd                  — Client socket fd
    win_idx             — Bound window index (-1 = unbound)
    job_ptr             — Job handle
    service_id          — Database service ID
    recv_buffer         — Partial message buffer
    recv_len            — Bytes in buffer
```

### 7.3 Message Protocol

Messages are length-prefixed binary packets:

```
[0-3]   msg_type     — Message type identifier
[4-7]   payload_len  — Length of payload (N)
[8-N+7] payload      — Type-specific data
```

### 7.4 Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `WINDOW_CREATE` | App→Host | Request new window with title+size |
| `WINDOW_UPDATE` | App→Host | Update window title, geometry |
| `WINDOW_CLOSE` | Host→App | Notify window was closed |
| `WINDOW_RESIZED` | Host→App | Notify window was resized |
| `CANVAS_ATTACH` | App→Host | Attach IPC canvas to window |
| `CANVAS_DETACH` | App→Host | Detach IPC canvas |
| `ADD_LINE` | App→Host | Append text line to canvas |
| `CLEAR_LINES` | App→Host | Clear canvas lines |
| `SET_LABEL` | App→Host | Set status label |
| `ACTION` | Host→App | Forward user action to app |
| `KEY` | Host→App | Forward key event |
| `MOUSE` | Host→App | Forward mouse event |
| `ADDR_GO` | Host→App | Address bar navigation |

### 7.5 Poll Cycle (`IPCBroker_Poll`)

Called once per frame:

```
IPCBroker_Poll():
    1. accept() new connections on listen_fd
    2. For each connected client:
        bytes = recv(fd, buffer, ...)
        if bytes > 0:
            append to recv_buffer
            while complete message in buffer:
                IPCBroker_HandleMsg(client, msg_type, payload)
                remove message from buffer
        if bytes == 0:
            IPCBroker_RemoveClient(client)
```

### 7.6 Action Relaying

`IPCBroker_RouteAction(job, action_ptr, action_len, source_win)`:
Finds the client bound to `source_win` and sends an ACTION message. This is how toolbar button clicks, menu selections, and other UI actions reach external app processes.

### 7.7 Window Lifecycle IPC

When an IPC app creates a window:
1. App sends `WINDOW_CREATE` → Host calls `Win_Create` with app-provided title and size
2. Host sends back window index
3. App optionally sends `CANVAS_ATTACH` to bind its rendering surface
4. User interacts → Host sends `KEY`/`MOUSE`/`ACTION` messages
5. User closes window → Host sends `WINDOW_CLOSE`, removes client binding
6. App exits → socket closes, Host cleans up client and windows

### 7.8 Canvas IPC

For apps that render their own content (e.g., terminal emulators, browsers), the IPC canvas protocol provides:
- `CANVAS_ATTACH` — Bind app's rendering to a window's content surface
- `ADD_LINE` — Append a line of text to the canvas
- `CLEAR_LINES` — Clear all content
- `SET_LABEL` — Set a status label
- Shared memory path: `shm_ptr` for direct pixel access (future enhancement)

---

## 8. Dependencies

```
DInputTypes → (none — pure data structures)
DInputEvdev → DInputTypes, DInputDiscover, DRingTypes, DRing1, KeyMap
DInputDiscover → (Linux /dev/input and /proc filesystem)
Cursor → CursorBitmap, Framebuffer
CursorBitmap → DSurface
InputRouter → DEAD — not imported; functionally replaced by EventRouter
IPCBroker → WinManager, SysDisplay (for dirty flag), Socket
```
