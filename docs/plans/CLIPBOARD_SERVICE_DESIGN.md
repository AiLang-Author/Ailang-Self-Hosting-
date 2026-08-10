# System Clipboard Service — Design

_Status: draft · 2026-07-05 · owner: Sean_

## 1. Context & motivation

Copy/paste in AOS today works, but only for **native Auckland text widgets**
managed inside the display server. The clipboard itself is a single global
`FixedPool.Clipboard` buried in `Library.TextBuffer.ailang`, poked directly by
two call sites:

- `Library.AucklandEvent.ailang` — keyboard `Ctrl+C/X/V/A` (`AK_EventKeyCtrl`,
  `AK_CopySelection`).
- `Library.Menu/Library.ContextMenu.ailang` — right-click Cut/Copy/Paste/Select
  All (`ContextMenu_FireAction`).

Two facts from the July 2026 investigation frame this design:

1. **It is already a display-server capability, not an app one.** No IPC app
   binary imports `TextBuffer`/`Clipboard`. Editing, selection, and clipboard all
   run in the display-server process on display-server-owned `TextBuffer`s. So
   "copy/paste shouldn't live in application binaries" is already true for native
   widgets — good foundation.
2. **It does not generalize.** Apps that render their own content into a shared
   canvas over IPC (Chrome, terminal, Ladybird, future image/doc viewers) have no
   display-server `TextBuffer`, and there is **no clipboard IPC method** today.
   They cannot copy or paste at all. There is also no owner/permission model.

Goal: promote the clipboard from a buried pool to a **first-class system service**
that (a) works across any surface — native textfield, canvas document, IPC app —
(b) carries typed content (text now; images, file refs, rich later), and
(c) is eventually **capability-scoped by the logged-in user** so clipboard flow
respects privilege boundaries.

Groundwork already present: `FixedPool.ClipType` (`TEXT` type tag) and a
`ClipHistory` ring with a per-entry `TYPE` field in `Library.TextBuffer.ailang`.

## 2. Goals / non-goals

**Goals**
- One authoritative clipboard, owned by the display server, no per-app copies.
- Typed entries; text first, image (via shm) next, file-ref and rich later.
- IPC protocol so shm-canvas apps participate in copy/paste.
- Keep the fast in-process path for native Auckland textfields.
- Phased path to user/capability scoping backed by Postgres.

**Non-goals (for now)**
- Cross-machine / network clipboard.
- Rich-text/HTML fidelity (tracked as a later type).
- Capability scoping in v1 (added in v2 — see §6). Per decision 2026-07-05,
  v1 ships an unscoped system-wide clipboard; scoping is layered on once it works
  ("Postgres makes that easy").

## 3. Architecture

**Host:** the **display server** (`Main.ailang` process). It already owns the
clipboard pool, the window→owner mapping (`WinView`), and the IPC broker
(`Library.IPCBroker.ailang`). A standalone `svc_daemon` clipboard service is
possible later but adds process/plumbing cost for no near-term benefit.

**Core object — `ClipboardService`** (promote the current pool):
- Current entry: `{ type, data_ptr, data_len, owner_session, seq }`.
- History ring: reuse/extend `ClipHistory` (already typed).
- For large/binary payloads (images), store a **shm handle** instead of an inline
  buffer, mirroring the existing `canvas.attach`/`ShmCanvas` mechanism rather than
  copying megabytes through the socket.

**Two access paths:**
- **In-process (native Auckland widgets):** `AK_CopySelection` / paste call
  `Clipboard_Set`/`Clipboard_Get` directly — unchanged hot path, just retargeted
  at the service API.
- **IPC (shm-canvas apps):** new `clipboard.*` methods (see §4). App-rendered
  surfaces copy/paste by messaging the service.

## 4. IPC protocol (new `clipboard.*` methods in IPCBroker)

Added to the method dispatch in `Library.IPCBroker.ailang` (~line 310), alongside
`window.create`, `canvas.attach`, etc. JSON over the existing Unix socket.

```
// App -> Server
{ "method":"clipboard.set", "win_id":N, "type":"text", "data":"..." }
{ "method":"clipboard.set", "win_id":N, "type":"image", "shm_path":"/...","w":W,"h":H,"fmt":"rgba" }
{ "method":"clipboard.get", "win_id":N, "accept":["image","text"] }   // preference order

// Server -> App (response to get)
{ "method":"clipboard.data", "type":"text", "data":"..." }
{ "method":"clipboard.data", "type":"image", "shm_path":"/...","w":W,"h":H,"fmt":"rgba" }
{ "method":"clipboard.data", "type":"empty" }
```

Notes:
- `accept` lets the requester pick the best type it understands (e.g. an image
  viewer prefers `image`, a text field falls back to `text`).
- Large payloads use `shm_path` (allocate → present → detach), never inline bytes.
- `win_id` identifies the requesting surface; it is the anchor for scoping in v2.
- Native right-click menu over an IPC-app window: the menu still runs in the
  display server, but Copy/Paste on an app-owned surface routes through
  `clipboard.set/get` to that app instead of a local `TextBuffer`.

## 5. Type system

| Type      | v1 | Representation                              |
|-----------|----|---------------------------------------------|
| `text`    | ✅ | inline UTF-8 (`data`)                        |
| `image`   | v3 | shm handle + `{w,h,fmt}` (rgba/bgra)         |
| `file_ref`| v3 | list of absolute paths / UUIDs              |
| `rich`    | later | typed blob + fallback `text`             |

`ClipType` (already in `TextBuffer.ailang`) is the enum; extend with `IMAGE`,
`FILE_REF`, `RICH`. Every entry keeps a `text` fallback where meaningful so
text-only sinks always get *something*.

## 6. Capability scoping (v2+, Postgres-backed)

Deferred out of v1 by decision, but the design reserves for it now so it drops in
cleanly.

- Every clipboard entry is stamped with the **owning login session** (from
  `OS/Login.ailang` / `OS/UUIDStore.ailang`). Every window already maps to an
  owner via `WinView`.
- On `clipboard.get`, the service checks the requester's session/label against the
  entry's before releasing content:
  - **v2 (session scope):** same-session only; deny cross-session paste.
  - **v3 (privilege labels):** per-surface privilege level; release only if the
    requester's label **dominates or matches** the entry's (Bell-LaPadula-style
    flow control). Closes the clipboard confused-deputy / exfil path — a
    privileged copy can't be pasted into a less-privileged or foreign surface.
- Postgres makes this cheap: entries + history + session/privilege live in the
  existing PG-backed registry; scope checks are a query, and history/audit come
  free.

Proposed tables (v2):
```
clipboard_entry(id, seq, type, data|shm_ref, owner_session, privilege_label, created_at)
clipboard_history(... same, retained N ...)
session(id, user_id, privilege_label, ...)   -- may already exist via Login
```

## 7. Phasing

- **v1 — system-wide clipboard, unscoped.** Promote pool → service; add
  `clipboard.set/get` (text); wire one IPC app (terminal or Chrome) as the pilot
  producer/consumer. Native textfield path unchanged. _This is the first buildable
  slice._
- **v2 — session scoping.** Stamp `owner_session`; deny cross-session; PG-backed
  entry/history.
- **v3 — types + labels.** Image (shm) + file_ref types; privilege-label dominance
  checks; clipboard-history UI (the `ClipHistory` ring surfaced to the user).

## 8. Integration points / files

- `Library.TextBuffer.ailang` — promote `Clipboard`/`ClipType`/`ClipHistory` into
  the service API surface (`Clipboard_Set/Get` stay the in-process entry points).
- `Library.IPCBroker.ailang` — add `clipboard.*` methods to the dispatch (~310);
  reuse `canvas.attach` shm plumbing for image payloads.
- `Library.AucklandEvent.ailang` / `Library.ContextMenu.ailang` — when the target
  surface is IPC-owned, route Copy/Paste via the service→app instead of a local
  `TextBuffer`.
- `OS/Login.ailang`, `OS/UUIDStore.ailang` — session identity for v2 scoping.
- PG schema (`system/schema.sql`) — v2 tables.

## 9. Open questions

1. **Authoritative session identity per window** — is it the `Login` session id,
   or the IPC `job`/owner recorded on `WinView`? This is the key that v2 scoping
   hangs on; confirm before building v2.
2. **Selection ownership for IPC apps** — does the app hold the selection and only
   serialize on `clipboard.set` (X11-style lazy), or does it push eagerly on
   selection change? Lazy is cheaper for large content; pick when wiring the pilot.
3. **Right-click over an IPC-app surface** — confirm the display server can tell an
   app-owned canvas region from a native widget region to choose local-`TextBuffer`
   vs `clipboard.get` routing.

## 10. Verification (per phase)

- **v1:** headless harness like `TestCode/Test.CopyPaste.ailang`, extended to drive
  `clipboard.set`/`clipboard.get` between two contexts; plus a live tty2 test with
  the pilot IPC app (copy in terminal → paste in notepad).
- **v2/v3:** add cross-session deny tests and image round-trip (shm) tests.
```
```
