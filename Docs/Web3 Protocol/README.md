# Web 3.0 Protocol Specification

> **Version 1.0 (Draft)**  
> **License: CC0 1.0 Universal (Public Domain Dedication)**

Welcome to the **Web 3.0 Protocol**. 

Web 3.0 is a server-authoritative hypermedia protocol that treats the client as a **pure display and input engine**. It is a clean reset of the web—stripping away thirty years of accumulated bloat, complex browser engines, and client-side execution vulnerabilities.

By moving all logic, state, and complex layout computation back to the server, Web 3.0 communicates with lightweight, deterministic clients via highly efficient vector commands (TinyVG) and structured JSON over IPC or WebSockets.

## The Core Philosophy

- **No Client-Side Code:** No JavaScript. No Turing-complete execution on the client. 
- **Hybrid Rendering:** Core UI widgets, icons, overlays, and server-driven canvases use compact TinyVG binary streams. HTML/CSS is retained for complex text and flow layout.
- **Server-Authoritative State:** The server owns the interactive state, dictates the TVG scene graph, and handles all business logic.
- **Micro-Binaries:** Backend servers can be written in any language (C, Rust, Go, Python) as highly optimized micro-binaries.
- **AI-Native:** Web 3.0's structured JSON contract perfectly aligns with how modern LLMs and AI Agents use function calling to interact with the world.

---

## Documentation Index

The specification is divided into 10 core documents detailing every aspect of the protocol:

### 📖 [01 — Philosophy, Principles & Architecture](01_PHILOSOPHY.md)
The fundamental "Why" of Web 3.0. Details the three generations of the web, the non-negotiable core principles, and the overarching architecture comparing it to Web 2.0 SPA and HTMX models.

### 🔌 [02 — Transport Layer](02_TRANSPORT.md)
Defines the physical communication layer. Unix Domain Sockets for blazing-fast 2–5 μs local IPC, and WebSockets (WSS) for remote connections. Covers frame structures and encryption modes.

### 🗣️ [03 — Wire Protocol](03_WIRE_PROTOCOL.md)
The structured contract between client and server. Includes the BNF grammar and JSON schemas for `HELLO`, `EVENT`, and `UPDATE` frames, defining exactly how state and input are exchanged.

### 🎨 04 — TinyVG Rendering
The visual heart of Web 3.0. Details the binary vector command set, scene-graph management, path drawing, gradients, text layout queries, and deterministic UI rendering.

### 🧱 05 — Markup
HTML relegated strictly to its original purpose: structure. Explains the `we-*` declarative attributes (`we-action`, `we-trigger`, `we-target`) used to map client interaction to server logic.

### 🛠️ 06 — Applications & Reference
Real-world examples and reference implementations. Walks through how to build a Todo List, a Real-Time Dashboard, a Chat App, and an IDE using the Web 3.0 paradigm.

### 🛡️ 07 — Security
The threat model of a system with zero client-side code execution. Details AEAD ChaCha20-Poly1305 encryption, sandboxing, parser constraints, and privacy guarantees (no telemetry).

### 🎥 08 — Media & WebRTC
How continuous, opaque media payloads are handled. Defines the pure client buffer stream contract, WebRTC signaling encapsulation over Web 3.0 frames, and the zero client-side DRM policy.

### ⚡ 09 — Efficiency, Computation & AI
The massive bandwidth and server computation savings of Web 3.0. Explains how removing the Virtual DOM enables edge-computing micro-binaries and creates a seamless impedance match for AI agent tool-calling.

### ✅ 10 — Compliance & Benchmarks
The test suite and conformance levels required to carry the "Web 3.0 Certified" badge. Outlines strict performance benchmarks for client cold starts, rendering speed, and server scaling.

---

## Getting Started

Because Web 3.0 is a language-agnostic contract, you can build a server or client in whichever environment you prefer. 

1. Start with the **Philosophy** to understand the paradigm shift.
2. Check out **Applications** to see what the server-client interaction looks like in practice.
3. Dive into the **Wire Protocol** to start building your own socket handlers.

## Contributing & Licensing

The Web 3.0 Protocol is released into the public domain under the **CC0 1.0 Universal License**. 

We believe the foundational layers of the internet should belong to everyone, completely free of intellectual property restrictions or corporate capture. You are free to copy, modify, distribute, and implement this standard without asking permission.