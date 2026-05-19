# 10 — Compliance: Test Suite, Conformance Levels, and Benchmarks

> **Web 3.0 Protocol Specification — Version 1.0 (Draft)**
> **License: CC0 1.0 Universal (Public Domain Dedication)**

---

## 1. Conformance Levels

To ensure interoperability, Web 3.0 implementations are categorized into conformance levels. An implementation MUST pass all test cases for a given level to claim compliance.

### 1.1 Client Conformance Levels

| Level | Description | Target Use Case |
|-------|-------------|-----------------|
| **Level 0 (Core)** | Unix Socket only, plaintext or basic AEAD. Only basic TVG primitives (rects, text, basic paths). No WebRTC, no streaming. | Local IoT displays, embedded UI screens, simple text interfaces. |
| **Level 1 (Standard)** | WebSocket + TLS, full AEAD support. Full TVG path and gradient support. HTML layout parsing. | Desktop native clients, general-purpose application browsers. |
| **Level 2 (Advanced)** | Stream compression, WebRTC buffer encapsulation, hardware device access, complex TVG grid layouts. | Rich media applications, collaborative editors, video conferencing. |

### 1.2 Server Conformance Levels

| Level | Description | Target Use Case |
|-------|-------------|-----------------|
| **Level 0 (Core)** | Synchronous request/response. HTML/TVG generation. Unix sockets. | Embedded device control panels, local microservices. |
| **Level 1 (Standard)** | WebSocket WSS, asynchronous updates, session state management, AEAD/Ed25519 signing. | Standard web applications, dynamic forms, CRUD interfaces. |
| **Level 2 (Advanced)** | WebRTC signaling, high-frequency streaming updates, zstd dictionary compression. | Real-time dashboards, multiplayer games, live chat servers. |

---

## 2. Client Test Suite

A compliant client MUST execute deterministically. The test suite provides a set of mocked server interactions, and the client's framebuffer output and event generation are asserted against expected values.

### 2.1 Handshake & Transport (C-TRANS)

| ID | Test Case | Expected Client Behavior |
|----|-----------|--------------------------|
| C-TRANS-01 | Server accepts HELLO with AEAD | Client negotiates key and transitions to encrypted mode. |
| C-TRANS-02 | Server rejects connection | Client fires local connection error and cleans up socket. |
| C-TRANS-03 | Server sends invalid AEAD tag | Client immediately drops the frame and closes connection. |
| C-TRANS-04 | Server sequence number gap | Client closes connection with ERROR 109. |
| C-TRANS-05 | Keepalive (PING/PONG) | Client responds to PING with PONG within 5 seconds. |

### 2.2 Wire Protocol & Parsing (C-WIRE)

| ID | Test Case | Expected Client Behavior |
|----|-----------|--------------------------|
| C-WIRE-01 | Valid UPDATE with HTML only | Client builds scene graph nodes representing the structural HTML. |
| C-WIRE-02 | Valid UPDATE with TVG commands | Client updates the scene graph and triggers a re-render. |
| C-WIRE-03 | Malformed JSON in text frame | Client drops the frame, emits ERROR 105, logs locally. |
| C-WIRE-04 | Unknown TVG Opcode | Client uses command length field to skip the opcode safely. |
| C-WIRE-05 | Max nesting depth exceeded | Client truncates or rejects the HTML fragment securely. |

### 2.3 Rendering & Layout (C-REND)

These tests verify the deterministic nature of the TVG rasterizer.

| ID | Test Case | Expected Client Behavior |
|----|-----------|--------------------------|
| C-REND-01 | Draw 100x100 Rect at (10,10) | Framebuffer hash matches reference hash exactly. |
| C-REND-02 | Linear Gradient Fill | Pixels interpolate correctly according to the 2 specified color stops. |
| C-REND-03 | Z-Order manipulation | SG_ZORDER command correctly occludes a lower-indexed node. |
| C-REND-04 | Text Measurement Query | Client sends correct `text:measured` EVENT bounds to server. |
| C-REND-05 | Node Visibility Toggle | Hiding a parent node makes all child nodes invisible. |

### 2.4 Input & Events (C-INPUT)

| ID | Test Case | Expected Client Behavior |
|----|-----------|--------------------------|
| C-INPUT-01 | Click on `we-action="submit"` | Client generates exact JSON EVENT payload with correct target and sequence. |
| C-INPUT-02 | Text input modification | Client generates `input` EVENT with correct string value and cursor position. |
| C-INPUT-03 | Focus traversal (Tab key) | Client visually highlights focused node and sends `focus` / `blur` events. |
| C-INPUT-04 | Rate Limiting (Rapid clicks) | Client debounces clicks exceeding 10 per second to prevent server flooding. |

---

## 3. Server Test Suite

Server tests involve a mock client driving the server with specific sequences of EVENT frames.

### 3.1 State & Routing (S-ROUTE)

| ID | Test Case | Expected Server Behavior |
|----|-----------|--------------------------|
| S-ROUTE-01 | Initial connection | Server replies with WELCOME and initial HTML skeleton UPDATE. |
| S-ROUTE-02 | Action dispatch | Server receives custom action and replies with targeted TVG UPDATE. |
| S-ROUTE-03 | Missing region target | Server replies with ERROR 107 if target region does not exist. |
| S-ROUTE-04 | Client session resume | Server correctly bypasses skeleton and resumes delta updates. |

### 3.2 Security & Limits (S-SEC)

| ID | Test Case | Expected Server Behavior |
|----|-----------|--------------------------|
| S-SEC-01 | Replayed EVENT sequence | Server drops EVENT with a sequence number ≤ the current processed sequence. |
| S-SEC-02 | Out-of-bounds target | Server rejects EVENT trying to act on a node ID not owned by the session. |
| S-SEC-03 | Payload Too Large | Server drops EVENT exceeding 64KB and returns ERROR 201. |
| S-SEC-04 | Flooding (DDoS simulation) | Server terminates session after 500 events per second threshold is breached. |

---

## 4. Benchmarks & Performance Requirements

To proudly carry the Web 3.0 badge, implementations must not only pass functional tests but also meet strict performance criteria. Web 3.0 is designed to be orders of magnitude more efficient than Web 2.0.

### 4.1 Client Performance Thresholds

Tested on a reference low-end ARM Cortex-A53 (e.g., Raspberry Pi 3 class) or a mid-range x86 desktop.

| Metric | Target Threshold | Notes |
|--------|------------------|-------|
| **Cold Start Time** | < 50 ms | From socket connect to first painted frame. |
| **Frame Parse Latency** | < 1 ms | Time to parse a 4 KB TVG UPDATE frame. |
| **Rasterization Time** | < 16 ms | Time to draw a scene with 500 nodes (guarantees 60 FPS). |
| **Memory Footprint** | < 25 MB | Resident RAM for a complex dashboard with 10,000 nodes. |
| **Binary Size** | < 2 MB | Uncompressed native executable size for a Standard Level client. |

### 4.2 Server Density & Scaling

Tested on a standard 1 vCPU, 1 GB RAM cloud instance (e.g., AWS t3.micro or equivalent).

| Metric | Target Threshold | Notes |
|--------|------------------|-------|
| **Concurrent Sessions** | > 10,000 | Using Unix Sockets or WebSocket with lightweight keepalive. |
| **Event Processing** | < 100 μs | Average time to process an input event and generate the TVG delta. |
| **Memory per Session** | < 10 KB | Server overhead to maintain the session state and sequence counters. |
| **Stream Throughput** | > 50,000 msg/sec | Capable of saturating a gigabit link with small TVG telemetry packets. |

### 4.3 Bandwidth Consumption Matrix

A reference implementation should achieve these bandwidth ratios compared to an equivalent Web 2.0 React/SPA stack:

| Scenario | Web 2.0 Data | Web 3.0 Data | Required Reduction |
|----------|--------------|--------------|--------------------|
| App Cold Load (JS vs TVG) | 2,500 KB | 12 KB | > 99% reduction |
| Simple Form Submission | 40 KB (JSON+DOM) | 0.8 KB (Event+TVG) | > 95% reduction |
| Real-time Graph (60s at 1Hz)| 120 KB | 6 KB | > 95% reduction |

---

## 5. Certification

Implementations that pass the complete test suite for their respective conformance levels may claim "Web 3.0 Certified" status. 

The reference testing harness (a CLI tool that acts as both a mock client and a mock server) will be provided as an open-source utility alongside this standard.