# 01 — Philosophy, Principles & Architecture

> **Web 3.0 Protocol Specification — Version 1.0 (Draft)**
> **License: CC0 1.0 Universal (Public Domain Dedication)**

---

## 1. What Is Web 3.0?

Web 3.0 is a server-authoritative hypermedia protocol that treats the client as a **pure display + input engine**. It is the clean reset the web has needed for thirty years.

### 1.1 The Three Generations

| Generation | Era | Model | Client Role |
|-----------|------|-------|-------------|
| **Web 1.0** | 1991–2004 | Server-rendered HTML pages | Dumb renderer |
| **Web 2.0** | 2004–2025 | Client-side JavaScript SPAs | Fat runtime, 10 MB bundles |
| **Web 3.0** | 2026– | Server-authoritative vector streams | Pure display + input |

Web 3.0 reclaims the original hypermedia vision while leveraging modern vector rendering and IPC transport.

### 1.2 The Bet

> Every byte of JavaScript you ship to the client is a byte you have lost control of. Every frame you let the client compute is a frame you cannot audit. Every vector you send is a vector you own forever.

Web 3.0 moves **all** computation, state, business logic, and semantics to the server. The client owns only five things:

1. **Rendering** — rasterizing TinyVG for widgets and standard HTML/CSS for text and flow
2. **Layout** — applying deterministic TVG layouts layered over the HTML flow
3. **Input capture** — keyboard, mouse, touch, gamepad events
4. **Networking** — maintaining the IPC channel to the server
5. **Caching** — retaining vector scene-graph nodes per server policy

That is the entire client surface.

---

## 2. Core Principles (Non-Negotiable)

| # | Principle | Meaning |
|---|-----------|---------|
| **I** | Server is single source of truth | All logic, state, validation lives on the server. The client never computes truth. |
| **II** | Client is deterministic | Given the same vector stream, the client produces pixel-identical output every time. |
| **III** | HTML is markup, not behavior | No `<script>`, no inline event handlers that execute code. `we-action`, `we-trigger`, `we-target` attributes only. |
| **IV** | Hybrid rendering | TVG handles high-performance UI widgets, charts, and icons. HTML/CSS is retained for complex text and flow layout. Raster images and media use standard DOM tags. |
| **V** | IPC is the native transport | Unix domain sockets, named pipes, WebSocket. Low-latency, bidirectional, frame-delimited. |
| **VI** | Deltas only | Never send a full page reload. Updates are targeted fragments with vector command batches. |
| **VII** | Telemetry-free by construction | The client sends only user-initiated events. No analytics surface exists. |
| **VIII** | Encryption is baseline | All channels support TLS 1.3, ephemeral key exchange, and optional per-message signing. |

---

## 3. Architecture

```
┌─────────────────────────────────────────┐
│  SERVER (AiLang, C, Rust, any language) │
│                                         │
│  ┌────────────┐  ┌───────────────────┐  │
│  │ Business    │  │ Vector Command    │  │
│  │ Logic       │  │ Generator (TVG)   │  │
│  └────────────┘  └───────────────────┘  │
│  ┌────────────┐  ┌───────────────────┐  │
│  │ State       │  │ Markup Generator  │  │
│  │ Manager     │  │ (HTML fragments)  │  │
│  └────────────┘  └───────────────────┘  │
│                                         │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │  IPC CHANNEL            │
    │  Unix Socket / WebSocket│
    │  Framed + Encrypted     │
    └────────────┬────────────┘
                 │
┌────────────────┴────────────────────────┐
│  CLIENT (Native Display Engine)         │
│                                         │
│  ┌────────────┐  ┌───────────────────┐  │
│  │ TVG Vector  │  │ Deterministic     │  │
│  │ Rasterizer  │  │ Layout Engine     │  │
│  └────────────┘  └───────────────────┘  │
│  ┌────────────┐  ┌───────────────────┐  │
│  │ Scene Graph │  │ Input Dispatcher  │  │
│  │ (retained)  │  │ (event→IPC)       │  │
│  └────────────┘  └───────────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

### 3.1 Lifecycle

```
INITIAL LOAD:
  Client connects → Server sends full HTML skeleton + root TVG scene
  → Client builds retained scene graph → Client renders frame 0

INTERACTION:
  User clicks button → Client sends event JSON over IPC (no rendering)
  → Server receives event, computes result
  → Server replies: HTML fragment (optional) + TVG command batch
  → Client applies delta to scene graph → Client re-renders

STREAMING:
  Server pushes periodic updates (live data) via the same IPC channel
  → Client applies each batch as it arrives
  → No polling, no WebSocket reconnection loop
```

### 3.2 Bandwidth Model

| Operation | Web 2.0 (Typical) | Web 3.0 | Ratio |
|-----------|-------------------|---------|-------|
| Page load | 2–10 MB JS bundle | 4–20 KB vector scene | 100–500× |
| Button click | 50 KB JSON + re-render | 200 B event + 1–2 KB TVG delta | 25–50× |
| Live dashboard tick | 100 KB HTML/JSON | 500 B TVG commands | 200× |
| Image (100×100) | 15 KB JPEG | 300 B–2 KB TVG path | 7–50× |

TinyVG paths for icons and widgets are typically 200–800 bytes, compared to 2–15 KB for equivalent PNG/SVG.

---

## 4. Relationship to Existing Standards

### 4.1 What We Use

| Standard | Use | Notes |
|----------|-----|-------|
| **TinyVG (TVG)** | Vector encoding | Custom binary format; compact, directly renderable |
| **JSON** | Event messages, metadata | Human-readable, universal parsing |
| **CBOR** | Optional binary alternative | For bandwidth-constrained links |
| **Unix Domain Sockets** | Local IPC | Zero-copy, kernel-mediated, 2–5 μs latency |
| **WebSocket** | Remote transport | WSS for browser compatibility |
| **HTTP/2, HTTP/3** | Fallback transport | SSE for unidirectional streams |
| **TLS 1.3** | Encryption | Mandatory for remote connections |
| **zstd / brotli** | Compression | Per-message or per-stream |

### 4.2 What We Reject

| Rejected | Reason |
|----------|--------|
| JavaScript | Turing-complete client code is a security and privacy liability |
| DOM for UI State | HTML/DOM is retained for text and document flow, but interactive widgets and chrome use TVG |
| CSS for UI Logic | Basic flow/styling is CSS, but complex UI decoration, animations, and pseudo-classes move to TVG |
| PNG/JPEG for Chrome | Raster images are fine for photos, but UI chrome and icons must use TVG |
| REST | Targeted region updates with TVG deltas are more efficient |
| GraphQL | Server owns queries; client never constructs them |
| npm, webpack, bundlers | There is no client-side code to bundle |

---

## 5. The TinyVG Advantage

TinyVG is the vector format at the heart of Web 3.0 rendering. It is already implemented in the AILANG Display System and has been proven across thousands of icons, fonts, and widgets.

### 5.1 Why TinyVG Over SVG?

| Property | SVG | TinyVG |
|----------|-----|--------|
| Parser size | 50–200 KB | ~5 KB |
| Parse time (1 KB icon) | 200–500 μs | 10–30 μs |
| Binary size (same icon) | 1.0× | 0.3–0.6× |
| Gradient support | Full | Linear, radial, conic |
| Path encoding | Text commands (M, L, C...) | Binary segments |
| Animation | SMIL/CSS (complex) | Server-driven deltas only |
| Security surface | XML entities, xlinks | Fixed binary format, no entities |

### 5.2 TVG Primitives (Summary)

The full command reference is in Document 04. Core primitives:

- **Paths**: move, line, quadratic/cubic bezier, arc, close
- **Shapes**: rect, rounded rect, circle, ellipse, polygon
- **Styles**: fill (solid, gradient), stroke (width, cap, join), opacity
- **Transforms**: translate, scale, rotate, skew, matrix
- **Text**: glyph runs with font reference, size, position
- **Groups**: named layers with inherited transforms and styles
- **Gradients**: linear, radial, conic with color stops

---

## 6. Comparison: Web 3.0 vs HTMX vs React

| Property | React SPA | HTMX | Web 3.0 |
|----------|-----------|------|---------|
| Client code size | 50–500 KB | 14 KB | 0 KB (native engine only) |
| Rendering | Virtual DOM diff → DOM | HTML swap | TVG vector rasterize |
| State ownership | Client + server | Server | Server only |
| Bandwidth per interaction | 10–100 KB | 1–10 KB HTML | 200 B–2 KB TVG |
| Latency (local) | 5–20 ms | 2–10 ms | 0.5–2 ms (Unix socket) |
| Privacy | Telemetry surface | CSS/JS tracking surface | Zero telemetry surface |
| Offline | Complex service workers | None | Server-defined cache policy |
| Encryption | TLS only | TLS only | TLS + per-message signing |
| GPU acceleration | Browser-dependent | None | Native framebuffer/TVG raster |
