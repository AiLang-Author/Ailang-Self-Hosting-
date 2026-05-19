# 02 — Transport Layer: IPC Sockets, Framing, Encryption

> **Web 3.0 Protocol Specification — Version 1.0 (Draft)**
> **License: CC0 1.0 Universal (Public Domain Dedication)**

---

## 1. Overview

The transport layer carries framed, encrypted messages between server and client. It is designed for minimal overhead on local IPC and robust security on remote connections.

### 1.1 Transport Selection

| Scenario | Transport | Latency | Overhead |
|----------|-----------|---------|----------|
| Local / self-hosted | Unix Domain Socket (SOCK_STREAM) | 2–5 μs | ~0 bytes framing |
| Same machine, named | Named Pipe (FIFO) | 3–8 μs | ~0 bytes framing |
| Remote, browser | WebSocket (WSS) | 5–50 ms | TLS + WS framing |
| Remote, fallback | HTTP/2 SSE + POST | 10–100 ms | HTTP headers |

The server chooses the transport per connection. The client MUST support Unix sockets as primary and WebSocket as secondary.

---

## 2. Unix Domain Socket (Primary Transport)

### 2.1 Socket Path

```
Default socket path:  /tmp/web3.sock
Configurable via:     WEB3_SOCKET environment variable
                      or -s/--socket command-line flag
```

The server listens on this path. The client connects as a stream client.

### 2.2 Connection Lifecycle

```
SERVER                          CLIENT
  │                               │
  │  socket() + bind() + listen() │
  │                               │
  │◄──────── connect() ───────────│
  │                               │
  │── accept() ──────────────────►│
  │                               │
  │◄──────── HELLO ───────────────│  (client capabilities)
  │                               │
  │── WELCOME ───────────────────►│  (server capabilities, session key)
  │                               │
  │◄══════ encrypted stream ════►│
  │                               │
  │── CLOSE / ◄── CLOSE ──────────│
```

### 2.3 Server Implementation (AiLang)

The server uses the existing `Library.Socket.ailang` with Unix domain socket support:

```
Web3_ServerInit(path):
    sock = Socket_Create(AF_UNIX, SOCK_STREAM, 0)
    Socket_Bind(sock, path)
    Socket_Listen(sock, 16)
    return sock

Web3_ServerAccept(server_sock):
    client_fd = Socket_Accept(server_sock)
    session = Web3_SessionCreate(client_fd)
    Web3_HandshakeServer(session)
    return session
```

### 2.4 Client Implementation (AiLang)

```
Web3_ClientConnect(path):
    sock = Socket_Create(AF_UNIX, SOCK_STREAM, 0)
    Socket_Connect(sock, path)
    session = Web3_SessionCreate(sock)
    Web3_HandshakeClient(session)
    return session
```

### 2.5 Unix Socket Security

Unix sockets on the same machine carry no network-level encryption but benefit from kernel-mediated access control:

- Socket file permissions: `0600` (owner read/write only)
- SO_PASSCRED: server can verify client PID/UID/GID
- Abstract socket namespace: no filesystem entry, no cleanup needed

For local-only deployments, the socket permission model plus optional per-message AEAD (see Section 5) provides defense-in-depth without TLS overhead.

---

## 3. WebSocket Transport (Remote)

### 3.1 Connection

```
Client connects to:  wss://host:port/web3
Mandatory:           TLS 1.3
Subprotocol:         web3-v1
```

### 3.2 Framing

WebSocket messages map 1:1 to Web 3.0 frames. Binary messages carry TVG commands; text messages carry JSON events and HTML fragments.

| Web 3.0 Frame Type | WebSocket Opcode |
|--------------------|------------------|
| HELLO, WELCOME, CLOSE | Text (JSON) |
| EVENT (client→server) | Text (JSON) |
| UPDATE (server→client) | Binary or Text |
| TVG_COMMANDS | Binary |
| HTML_FRAGMENT | Text |
| PING / PONG | WebSocket native |

---

## 4. Frame Format

All messages (over any transport) use a common frame header followed by a typed payload.

### 4.1 Frame Header (8 bytes)

```
Byte 0:     Version (0x01)
Byte 1:     Frame Type
Byte 2-3:   Flags (16-bit, big-endian)
Byte 4-7:   Payload Length (32-bit, big-endian)
```

### 4.2 Frame Types

| Value | Name | Direction | Payload |
|-------|------|-----------|---------|
| 0x01 | HELLO | C→S | JSON: client capabilities |
| 0x02 | WELCOME | S→C | JSON: server capabilities, session token |
| 0x03 | EVENT | C→S | JSON: action, target, region, payload |
| 0x04 | UPDATE | S→C | Mixed: HTML fragment + TVG command batch |
| 0x05 | TVG_CMDS | S→C | Binary: TVG command stream |
| 0x06 | HTML_FRAG | S→C | Text: HTML fragment for region |
| 0x07 | PING | Both | Empty (keepalive) |
| 0x08 | PONG | Both | Empty (keepalive response) |
| 0x09 | CLOSE | Both | JSON: reason |
| 0x0A | ERROR | Both | JSON: code, message |

### 4.3 Flags

| Bit | Name | Meaning |
|-----|------|---------|
| 0 | COMPRESSED | Payload is zstd-compressed |
| 1 | ENCRYPTED | Payload is AEAD-encrypted |
| 2 | FRAGMENTED | Frame is part of a larger message |
| 3 | LAST | Last fragment in sequence |
| 4–15 | Reserved | Set to 0 |

---

## 5. Encryption

### 5.1 Threat Model

| Threat | Mitigation |
|--------|-----------|
| Passive eavesdropping | TLS 1.3 (remote); Unix socket permissions (local) |
| Active MITM | TLS certificate pinning; session token binding |
| Message replay | Monotonic sequence numbers + AEAD nonce |
| Message tampering | AEAD authentication tag (ChaCha20-Poly1305 or AES-256-GCM) |
| Session hijacking | Session token bound to client PID/UID (Unix) or TLS channel (remote) |
| Downgrade attack | Version pinning in HELLO; server enforces minimum version |

### 5.2 Encryption Modes

#### Mode 0: Plaintext (local Unix socket only)

No encryption. Used when both client and server are on the same machine and the socket is protected by filesystem permissions. Frames have the ENCRYPTED flag clear.

#### Mode 1: TLS 1.3 (remote WebSocket)

Standard WSS. The WebSocket connection is wrapped in TLS. Per-message encryption is redundant and disabled (ENCRYPTED flag clear). Server certificate must be valid and optionally pinned.

#### Mode 2: Per-Message AEAD (local or remote)

Each frame payload is independently encrypted with a symmetric session key negotiated during handshake. Frame header is NOT encrypted (routers/inspectors can see type + length). Payload is encrypted with:

```
Algorithm:     ChaCha20-Poly1305 (preferred) or AES-256-GCM
Key:           256-bit session key from handshake
Nonce:         96-bit = frame sequence number (64-bit, big-endian) + padding
AD:            Frame header bytes 0-7 (authenticated but not encrypted)
Plaintext:     Frame payload
Ciphertext:    Replaces plaintext in payload field
Tag:           128-bit authentication tag appended to ciphertext
```

#### Mode 3: Signed Messages (untrusted environments)

For public-facing servers where clients cannot be trusted with session keys, each UPDATE frame is signed with an Ed25519 server key. The client verifies the signature before applying any TVG commands. This prevents a compromised transport from injecting malicious vector data (which could, at worst, render garbage — but cannot execute code).

### 5.3 Handshake: Session Key Establishment

```
CLIENT                                SERVER
  │                                     │
  │── HELLO ──────────────────────────►│
  │   {                                 │
  │     "version": "1.0",               │
  │     "encryption": ["aead"],          │
  │     "compress": ["zstd"],            │
  │     "client_nonce": "<random 32B>"  │
  │   }                                 │
  │                                     │
  │◄───────── WELCOME ─────────────────│
  │   {                                 │
  │     "version": "1.0",               │
  │     "session_id": "<uuid>",         │
  │     "encryption": "aead",           │
  │     "server_nonce": "<random 32B>", │
  │     "server_pubkey": "<ed25519>"    │
  │   }                                 │
  │                                     │
  │  session_key = HKDF(                │
  │    client_nonce || server_nonce,    │
  │    salt = session_id,               │
  │    info = "web3-session-v1"         │
  │  )                                  │
  │                                     │
  │◄══════ encrypted frames ═════════►│
```

HKDF-SHA256 with 256-bit output. The session key is never transmitted on the wire.

### 5.4 Sequence Numbers

Each direction maintains an independent 64-bit monotonic sequence number starting at 0. The sequence number is used as the AEAD nonce and is incremented after each frame. Replayed or out-of-order frames are detected by nonce mismatch and dropped.

---

## 6. Compression

### 6.1 Algorithm

zstd compression with dictionary pre-training on common TVG command patterns. The COMPRESSED flag in the frame header indicates the payload is compressed.

### 6.2 Compression Policy

| Frame Type | Compression |
|------------|-------------|
| HELLO, WELCOME, CLOSE | Never (small, one-time) |
| EVENT | Never (already tiny: 100–500 B) |
| UPDATE (HTML fragment) | Optional (HTML compresses well) |
| UPDATE (TVG commands) | Always (TVG binary compresses 3–8×) |
| PING, PONG | Never |

### 6.3 Stream Compression

For high-frequency TVG command streams (live dashboards, real-time collaboration), the server can negotiate stream compression during handshake. This uses a single zstd compression context across frames, improving compression ratio by 20–40% over per-frame compression.

---

## 7. Connection Management

### 7.1 Keepalive

PING frames are sent after 30 seconds of inactivity. The receiver must respond with PONG within 5 seconds. Two missed PONGs triggers connection close.

### 7.2 Reconnection

The client is responsible for reconnection. On reconnect, the client sends a new HELLO with a `resume` token from the previous WELCOME. The server may:

- **Accept resume**: Skip full HTML skeleton, send only TVG deltas since last acknowledged sequence number
- **Reject resume (full reload)**: Send full HTML skeleton + root TVG scene

The server decides based on session expiry (default: 5 minutes) and whether the scene graph can be reconstructed from the delta log.

### 7.3 Graceful Close

Either side sends CLOSE with a reason string. The receiver acknowledges by closing the transport. CLOSE frames are always plaintext (encrypted CLOSE is pointless if the key is about to be destroyed).

---

## 8. Reference: Socket Library (AiLang)

The Web 3.0 transport layer is built on `Library.Socket.ailang` and `Library.Http.ailang`:

```
Socket_Create(domain, type, protocol)     → fd
Socket_Bind(fd, address)                  → 0/error
Socket_Listen(fd, backlog)                → 0/error
Socket_Accept(fd)                         → client_fd
Socket_Connect(fd, address)               → 0/error
Socket_Read(fd, buffer, len)              → bytes_read
Socket_Write(fd, buffer, len)             → bytes_written
Socket_Close(fd)                          → 0/error
Socket_SetOpt(fd, level, opt, value)      → 0/error
```

For Unix sockets, the address is a path string (e.g. `/tmp/web3.sock`). Abstract sockets are supported by prepending `\0` to the path.
