# 05 — Markup: HTML + WE Attributes, Regions, Actions & Triggers

> **Web 3.0 Protocol Specification — Version 1.0 (Draft)**
> **License: CC0 1.0 Universal (Public Domain Dedication)**

---

## 1. Markup Philosophy

HTML in Web 3.0 serves exactly two purposes:

1. **Structure & Text** — declare regions, document flow, complex text layouts, and semantic roles
2. **Wiring** — connect user interactions to server actions via declarative attributes
3. **Media & Fallback** — embed standard raster images (`<img>`) and media natively

HTML is never executed on the client. There is no `<script>` and no `onclick`. The client parses HTML into a DOM tree, uses it for text/flow layout, maps events to targets, and defines regions for TVG-rendered interactive chrome.

### 1.1 What HTML Elements Mean

| Element | Web 3.0 Meaning |
|---------|-----------------|
| `<region>` | Named, addressable area of the screen |
| `<div>` | Structural container (maps to TVG GROUP node) |
| `<button>` | Clickable widget (maps to TVG button render) |
| `<input>` | Text input field (maps to TVG text input render) |
| `<select>` | Dropdown selector (maps to TVG dropdown render) |
| `<textarea>` | Multi-line text input |
| `<form>` | Logical grouping of inputs for submission |
| `<ul>`, `<ol>`, `<li>` | List containers (maps to VBOX layout) |
| `<table>`, `<tr>`, `<td>` | Table (maps to GRID layout) |
| `<img>` | Raster image fallback (use sparingly) |
| `<icon>` | Named vector icon reference |
| `<h1>`–`<h6>` | Heading text with size levels |
| `<p>`, `<span>` | Inline and block text |
| `<a>` | Hyperlink (click triggers `load` action) |

---

## 2. WE Attributes (The Only Extension)

All client behavior is wired through five attributes with the `we-` prefix:

### 2.1 `we-action`

Declares the action verb sent to the server when triggered.

```
<button we-action="submit">Save</button>
<input we-action="search" placeholder="Search...">
<a we-action="load" href="/page2">Next Page</a>
```

Value: any built-in action or `custom:verb`.

### 2.2 `we-target`

Declares which region receives the server's UPDATE response.

```
<button we-action="submit" we-target="main-content">Save</button>
```

If omitted, the target is the region containing the element.

### 2.3 `we-trigger`

Declares which client-side event fires the action. Multiple triggers separated by `|`.

```
<button we-action="submit" we-trigger="click">Save</button>
<input we-action="search" we-trigger="input|change">
<div we-action="refresh" we-trigger="load">...</div>
```

Default triggers per element:
| Element | Default Trigger |
|---------|-----------------|
| `<button>`, `<a>` | `click` |
| `<input type="text">` | `change` |
| `<input type="search">` | `input` |
| `<select>` | `change` |
| `<input type="checkbox">` | `click` |
| `<form>` | `submit` |

### 2.4 `we-region`

Explicitly names a region. Alternative to the `<region>` element.

```
<div we-region="sidebar">...</div>
```

### 2.5 `we-vector`

When `"true"`, child text content is interpreted as TVG commands rather than HTML.

```
<div we-vector="true">
  <!-- inline TVG base64 or the server replaces this content with TVG binary -->
</div>
```

Server can also omit `we-vector` and send TVG commands in the UPDATE's `commands` array directly, which is the preferred approach.

---

## 3. Regions

### 3.1 Definition

A region is a named, addressable UI area. Regions are the unit of targeted updates: when the server responds to an event, it sends HTML/TVG fragments addressed to a specific region.

```
<region id="main" role="dashboard">
  <!-- content rendered here -->
</region>
```

Regions can be nested. If a child region is targeted, only that region is updated; the parent is untouched.

### 3.2 Region Roles

Roles hint at the purpose of a region for layout and accessibility:

| Role | Description |
|------|-------------|
| `dashboard` | Main content area with widgets |
| `toolbar` | Horizontal action bar |
| `sidebar` | Vertical navigation panel |
| `form` | Structured input collection |
| `list` | Scrollable item container |
| `detail` | Item detail view |
| `modal` | Overlay dialog |
| `status` | Status bar or notification area |
| `menu` | Dropdown or context menu |
| `desktop` | Root region (usually implicit) |

### 3.3 Region Lifecycle

```
Created:   When the HTML skeleton is first sent (or a new <region> appears in an update)
Populated: When the server sends an UPDATE targeting the region
Cleared:   When an UPDATE with empty html="" and no commands is sent
Destroyed: When the parent region is replaced
```

---

## 4. Actions Reference

### 4.1 Built-in Actions

| Action | Trigger | Payload |
|--------|---------|---------|
| `load` | click, load | `{ href: string }` |
| `submit` | click, submit | `{ formData: object }` |
| `click` | click | `{ }` |
| `change` | change | `{ value: any, checked: bool }` |
| `input` | input | `{ value: string, cursor: int }` |
| `focus` | focus | `{ }` |
| `blur` | blur | `{ }` |
| `keydown` | keydown | `{ key: string, modifiers: string[] }` |
| `keyup` | keyup | `{ key: string, modifiers: string[] }` |
| `poll` | timer | `{ interval: int }` (ms) |
| `stream:open` | load | `{ stream_id: string }` |
| `stream:close` | unload | `{ stream_id: string }` |

### 4.2 Custom Actions

Any action not in the built-in list is treated as `custom:verb`:

```
<button we-action="custom:export-csv">Export</button>
```

The server receives `"action": "custom:export-csv"` and handles it via its own dispatch table.

### 4.3 Polling

Polling is a special trigger that fires an action on a timer:

```
<div we-action="refresh" we-trigger="poll" we-poll-interval="5000">
  <!-- refreshed every 5 seconds -->
</div>
```

The `we-poll-interval` attribute (milliseconds) sets the interval. Minimum: 1000 ms (rate-limited by client).

---

## 5. HTML Skeleton (Initial Load)

When a client first connects, the server sends a full HTML skeleton. This is the only time a "full page" is sent.

```html
<region id="desktop" role="desktop">
  <region id="toolbar" role="toolbar">
    <button we-action="click" we-target="main" id="btn-home">Home</button>
    <button we-action="click" we-target="main" id="btn-settings">Settings</button>
  </region>
  <region id="sidebar" role="sidebar">
    <ul we-region="nav-list">
      <li><a we-action="load" we-target="main" href="/items/1">Item 1</a></li>
      <li><a we-action="load" we-target="main" href="/items/2">Item 2</a></li>
    </ul>
  </region>
  <region id="main" role="dashboard">
    <div we-action="load" we-trigger="load" we-target="main" href="/dashboard/home">
      Loading...
    </div>
  </region>
  <region id="status" role="status">
    Ready
  </region>
</region>
```

Key points:
- The `desktop` region is the implicit root; all regions are inside it.
- `<div we-action="load" we-trigger="load">` fires immediately when the client renders it, populating `#main` via server request.
- Regions are nested: clicking a button in `#toolbar` targets `#main`.

---

## 6. Server-Side Template (Pseudo-code)

The server generates HTML fragments programmatically. Example pseudo-code using string interpolation:

```
fn Web3_DashboardHome() -> string {
    return `<div>
        <h2>Dashboard</h2>
        <table we-region="recent-items">
            <tr><th>Name</th><th>Status</th></tr>
            ` +
            Web3_RenderItemRows(DB_GetRecentItems(10)) +
            `
        </table>
        <button we-action="click" we-target="main" id="refresh-btn">Refresh</button>
    </div>`
}
```

The server also generates the accompanying TVG commands for vector widgets (gradients, icons, custom-drawn elements) that are not representable in HTML alone.

---

## 7. Fragment Updates

After the skeleton is loaded, all subsequent updates are fragments targeted at a specific region.

### 7.1 HTML Fragment Only

```json
{
  "type": "update",
  "seq": 128,
  "in_reply_to": 42,
  "region": "main",
  "html": "<h2>Items</h2><ul><li>Apple</li><li>Banana</li></ul>"
}
```

The client replaces the content of region `main` with this HTML, building TVG nodes for each element.

### 7.2 TVG Commands Only

```json
{
  "type": "update",
  "seq": 129,
  "in_reply_to": 43,
  "region": "main",
  "commands": [
    {"op": "replace", "node": "header", "data": {...}},
    {"op": "transform", "node": "logo", "matrix": [0.5, 0, 0, 0.5, 10, 10]},
    {"op": "style", "node": "badge", "fill": "#FF0000"}
  ]
}
```

### 7.3 Mixed

```json
{
  "type": "update",
  "seq": 130,
  "in_reply_to": 44,
  "region": "main",
  "html": "<h2>Dashboard</h2>",
  "commands": [
    {"op": "replace", "node": "gauge-cpu", "data": {"value": 0.73}}
  ]
}
```

HTML is processed first (building structural nodes), then TVG commands are applied (refining appearance).

---

## 8. Form Handling

### 8.1 Markup

```html
<form we-action="submit" we-target="main" id="login-form">
  <label>Username:</label>
  <input type="text" name="username" we-action="input">
  <label>Password:</label>
  <input type="password" name="password">
  <button type="submit">Log In</button>
</form>
```

### 8.2 Wire Behavior

Each `input` event sends keystrokes to the server. The server can validate on the fly and send back error states via TVG commands (red border, error text). On `submit`, the entire form payload is sent:

```json
{
  "action": "submit",
  "target": "login-form",
  "region": "main",
  "payload": {
    "formData": {
      "username": "sean",
      "password": "••••••••"
    }
  }
}
```

### 8.3 Server Validation Response

```json
{
  "type": "update",
  "seq": 145,
  "in_reply_to": 58,
  "region": "main",
  "commands": [
    {"op": "style", "node": "login-form", "border_color": "#FF0000"},
    {"op": "text", "node": "error-msg", "content": "Invalid password"}
  ]
}
```

---

## 9. WebSocket Push (Streaming Regions)

A region can be designated as a streaming region:

```html
<region id="live-feed" role="dashboard" we-stream="true">
  <!-- Server pushes TVG commands in real time -->
</region>
```

The client does NOT poll. The server pushes UPDATE frames (with no `in_reply_to`) as data changes. The client applies them as they arrive. If the region is scrolled off-screen, the client may defer rendering until visible.

---

## 10. Markup Parser Reference (Client-Side)

The client's HTML parser is a minimal subset:

- Parse well-formed XML-style tags (self-closing supported)
- Recognize `<region>`, `<div>`, `<button>`, `<input>`, `<form>`, `<select>`, `<textarea>`, `<ul>`, `<ol>`, `<li>`, `<table>`, `<tr>`, `<td>`, `<th>`, `<img>`, `<icon>`, `<h1>`–`<h6>`, `<p>`, `<span>`, `<a>`, `<label>`, `<br>`, `<hr>`
- Extract `id`, `we-*`, `name`, `type`, `placeholder`, `href`, `class` attributes
- Ignore all other elements and attributes
- No CSS parsing, no `style` attribute execution
- No entity expansion beyond `&lt;`, `&gt;`, `&amp;`, `&quot;`, `&#xNNNN;`
- Max nesting depth: 64
- Max element count per fragment: 4096
