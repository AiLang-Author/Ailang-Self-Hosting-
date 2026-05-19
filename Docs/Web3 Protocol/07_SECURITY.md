# 07 — Security: Threat Model, Encryption, Sandboxing & Audit

> **Web 3.0 Protocol Specification — Version 1.0 (Draft)**
> **License: CC0 1.0 Universal (Public Domain Dedication)**

---

## 1. Security Philosophy

Web 3.0 is secure by construction, not by patching. The fundamental insight: the client executes no Turing-complete code, therefore there is no code-injection surface.

### 1.1 The JavaScript Problem

```
Web 2.0 attack surface:
  - XSS (injected <script>)
  - CSP bypass (JSONP, eval, setTimeout strings)
  - Prototype pollution
  - npm supply chain (10,000 transitive dependencies)
  - DOM clobbering
  - PostMessage origin confusion
  - WebSocket origin spoofing
  - Service worker hijacking
  - localStorage/sessionStorage exfiltration
  - Canvas fingerprinting
  - ...

Web 3.0 attack surface:
  - Malformed TVG stream → parse error → frame dropped
  - Malformed JSON → parse error → frame dropped
  - Replayed event → AEAD nonce mismatch → frame dropped
```

### 1.2 The Vector Safety Guarantee

TVG commands are data, not code. The worst a malicious TVG stream can do is render garbage pixels. It cannot:

- Allocate unbounded memory (all allocations are bounded by command parameters)
- Execute arbitrary instructions (no function pointers in the command stream)
- Access files (no file paths in the command stream)
- Open network connections (no URLs in the command stream)
- Read or write outside the framebuffer (all coordinates are bounds-checked)
- Crash the renderer (the TVG parser has zero unsafe unwrap or panic paths)

---

## 2. Threat Model

### 2.1 Attacker Profiles

| Attacker | Capability | Goal |
|----------|-----------|------|
| Passive network observer | Can read unencrypted traffic | Steal data, session tokens |
| Active MITM | Can intercept and modify traffic | Inject malicious frames, hijack session |
| Malicious server | Controls a legitimate domain | Exploit client parsing bugs |
| Compromised client | Malware on the client machine | Exfiltrate user input, inject events |
| Rogue Web 3.0 application | Server-side app with a vulnerability | Access other apps' data on the same server |

### 2.2 Attack Surface Analysis

```
┌──────────────────────────────────────────────────────┐
│ CLIENT                                               │
│                                                      │
│  ┌─────────────────┐   ┌──────────────────┐         │
│  │ JSON Parser     │◄──│ IPC Read          │         │
│  │ (EVENT frames)  │   │ (text frames)     │         │
│  └────────┬────────┘   └──────────────────┘         │
│           │                                          │
│  ┌────────▼────────┐   ┌──────────────────┐         │
│  │ HTML Parser     │◄──│ IPC Read          │         │
│  │ (fragments)     │   │ (HTML frames)     │         │
│  └────────┬────────┘   └──────────────────┘         │
│           │                                          │
│  ┌────────▼────────┐   ┌──────────────────┐         │
│  │ TVG Parser      │◄──│ IPC Read          │         │
│  │ (commands)      │   │ (binary frames)   │         │
│  └────────┬────────┘   └──────────────────┘         │
│           │                                          │
│  ┌────────▼────────┐                                │
│  │ Scene Graph     │  ← All frame data ends here    │
│  │ (retained)      │                                │
│  └────────┬────────┘                                │
│           │                                          │
│  ┌────────▼────────┐                                │
│  │ Rasterizer      │  ← Pixels only, no feedback    │
│  └────────┬────────┘                                │
│           │                                          │
│  ┌────────▼────────┐                                │
│  │ Framebuffer     │  ← Output, read-only to rest   │
│  └─────────────────┘                                │
│                                                      │
│  Attack surface: JSON parser, HTML parser,           │
│  TVG parser. All output pixels. Nothing else.        │
└──────────────────────────────────────────────────────┘
```

---

## 3. Defenses by Layer

### 3.1 Transport Layer

| Defense | Implementation |
|---------|---------------|
| TLS 1.3 | Mandatory for remote WebSocket connections |
| Certificate pinning | Client stores expected server public key hash |
| Unix socket permissions | `0600` mode, SO_PASSCRED for PID/UID verification |
| Session binding | Session key bound to TLS channel or Unix credentials |
| Frame sequence numbers | 64-bit monotonic, both directions, AEAD nonce |
| Replay protection | AEAD nonce must be strictly increasing; duplicates rejected |

### 3.2 Frame Layer

| Defense | Implementation |
|---------|---------------|
| Max frame size | 16 MB (configurable; default 256 KB for events, 4 MB for updates) |
| Frame type whitelist | Unknown frame types produce ERROR, not undefined behavior |
| Fragment reassembly | Max 64 fragments per message; timeout 5 seconds |
| Compression bomb detection | Max expansion ratio 100:1; exceeding it → ERROR |
| Version check | Frame version != 0x01 → ERROR 100 |

### 3.3 JSON Parser

| Defense | Implementation |
|---------|---------------|
| Max depth | 32 nested objects/arrays |
| Max keys | 256 per object |
| Max string length | 65536 bytes |
| Max number of digits | 100 (before switching to string representation) |
| Duplicate keys | Last value wins (no prototype pollution possible) |
| UTF-8 validation | Invalid UTF-8 sequences → ERROR 104 |

### 3.4 HTML Parser

| Defense | Implementation |
|---------|---------------|
| Element whitelist | Only the 20 recognized elements; everything else is ignored |
| Attribute whitelist | Only `id`, `we-*`, `name`, `type`, `placeholder`, `href`, `class` |
| No entity expansion | Only the 5 XML built-in entities; no custom entities |
| Max nesting depth | 64 |
| Max elements per fragment | 4096 |
| No `<script>`, `<style>`, `<link>`, `<object>`, `<embed>`, `<iframe>` | These elements are not in the whitelist and are treated as unknown (discarded) |

### 3.5 TVG Parser

| Defense | Implementation |
|---------|---------------|
| Opcode whitelist | 32 recognized opcodes; unknown → skip via length field |
| Bounds checking | Every coordinate, index, and length is checked against buffer bounds |
| Alloc limits | Max 65536 nodes, max 65536 resources, max 256 children per node |
| Gradient stop limit | Max 32 stops per gradient |
| Path segment limit | Max 65536 segments per path |
| Cycle detection | Parent reference must not create a cycle (checked on SG_NODE_CREATE) |
| Resource exhaustion | Total resources capped at 65536; LRU eviction when full |

---

## 4. Encryption Details

### 4.1 AEAD Specification

```
Algorithm:   ChaCha20-Poly1305 (RFC 8439)
Key:         256-bit session key from HKDF handshake
Nonce:       96-bit = [0x00 × 4 bytes] || [sequence_number × 8 bytes, big-endian]
             (The 32-bit zero prefix ensures nonce uniqueness within a session;
              sequence number is per-direction and monotonic.)

AEAD Input:
  Associated Data (AD):  Frame header bytes [0..7] (version, type, flags, length)
  Plaintext:             Frame payload bytes
  Key:                   Session key

AEAD Output:
  Ciphertext:            Replaces plaintext in the frame
  Tag:                   128-bit Poly1305 tag appended to ciphertext

Frame layout with AEAD:
  [u8: version] [u8: type] [u16: flags] [u32: length]   ← AD (not encrypted)
  [u8 × (length-16): ciphertext]                          ← encrypted
  [u8 × 16: tag]                                          ← authentication tag
```

### 4.2 Key Derivation

```
HKDF-SHA256 (RFC 5869):
  IKM   = client_nonce (32 bytes) || server_nonce (32 bytes)
  salt  = session_id (UUID, 36 bytes ASCII)
  info  = "web3-session-v1" (17 bytes)
  output = 32 bytes (256-bit session key)

Properties:
  - Both sides contribute entropy (neither can force a known key)
  - Session ID binds the key to a specific session
  - The info string prevents cross-protocol key reuse
```

### 4.3 Key Rotation

For long-lived sessions (>1 hour), the server may initiate key rotation:

1. Server sends an UPDATE-like frame with a new `server_nonce` in the payload
2. Client acknowledges with an EVENT containing a new `client_nonce`
3. Both sides derive a new session key using HKDF with the new nonces
4. The old key is retained for 5 seconds to decrypt in-flight frames
5. Sequence numbers continue (do not reset)

### 4.4 Signed Messages (Ed25519)

For public servers where per-message AEAD is not feasible (too many clients, no session state), the server signs each UPDATE with an Ed25519 key:

```
Signature = Ed25519_Sign(server_private_key, frame_header || frame_payload)
Frame layout with signature:
  [u8: version] [u8: type] [u16: flags] [u32: length]
  [u8 × length: payload]
  [u8 × 64: signature]  ← appended; length field includes signature
```

The client verifies using the server's public key (sent in WELCOME). This prevents tampering but does not provide confidentiality. Use with TLS for confidentiality.

---

## 5. Server-Side Security

### 5.1 Application Isolation

The Web 3.0 server hosts multiple applications. Each application:

- Has its own set of regions (cannot target another app's regions)
- Has its own action namespace (`custom:appname:verb`)
- Cannot read another app's session data
- Cannot access the filesystem except through allowed paths
- Cannot open network connections except through allowed hosts/ports

### 5.2 Resource Limits

| Resource | Per-Session Limit | Hard Limit |
|----------|-------------------|------------|
| Concurrent sessions | 256 | 1024 |
| Events per second | 100 | 500 |
| HTML fragment size | 256 KB | 1 MB |
| TVG commands per batch | 1024 | 4096 |
| Scene graph nodes | 16384 | 65536 |
| Active streams | 8 | 16 |
| Session lifetime | 24 hours | 7 days |

### 5.3 Input Validation

All EVENT payloads are validated server-side:
- `action` must match the regex `^[a-z][a-z0-9:_-]*$`
- `target` must refer to a node the client is allowed to target
- `region` must refer to a region the session owns
- `payload` size must be ≤ 64 KB
- `seq` must be strictly increasing

---

## 6. Privacy Guarantees

### 6.1 No Telemetry Surface

Because the client only sends explicit user-initiated events, there is no mechanism for:

- Tracking pixels (no `<img>` loading from third parties)
- Canvas fingerprinting (no client-side canvas API)
- WebRTC IP leaks (no WebRTC)
- Battery/device fingerprinting (no navigator API)
- localStorage/sessionStorage tracking (no storage API)
- CSS history sniffing (no CSS)
- Beacon API / Navigator.sendBeacon (no beacon API)
- Performance API timing attacks (no performance API)

### 6.2 What The Server Knows

The server can only know:
- The sequence of user actions (clicks, inputs)
- The content of those actions (form values, button IDs)
- Connection metadata (IP address, TLS fingerprint, session duration)

This is the minimum information required to provide the service. Any additional data collection must be explicit (a form the user fills out).

---

## 7. Compliance Testing

### 7.1 Client Security Test Suite

| Test | Description |
|------|-------------|
| S-01 | Reject frame with unknown version |
| S-02 | Reject frame with unknown type |
| S-03 | Reject EVENT with invalid action name |
| S-04 | Reject HTML fragment with `<script>` tag |
| S-05 | Reject HTML fragment with `onclick` attribute |
| S-06 | Reject HTML fragment exceeding max nesting depth |
| S-07 | Reject TVG command with out-of-bounds node ID |
| S-08 | Reject TVG command with out-of-bounds coordinate |
| S-09 | Reject TVG gradient with >32 stops |
| S-10 | Reject frame with AEAD tag mismatch |
| S-11 | Reject replayed frame (sequence number reuse) |
| S-12 | Handle 10,000 sequential valid frames without memory growth |
| S-13 | Handle 1000 malformed frames without crash |
| S-14 | Reject frame > max frame size |
| S-15 | Drop unknown HTML element (don't error) |
| S-16 | Limit total scene graph nodes to 65536 |

### 7.2 Server Security Test Suite

| Test | Description |
|------|-------------|
| S-20 | Reject event targeting another session's region |
| S-21 | Enforce event rate limiting |
| S-22 | Validate all form input before processing |
| S-23 | Prevent path traversal in file operations |
| S-24 | Reject action with invalid custom verb |
| S-25 | Session isolation: app A cannot read app B's data |
| S-26 | Key rotation: old frames rejected after rotation |
| S-27 | Session expiry: resume token invalid after timeout |

---

## 8. Security FAQ

**Q: What if the server is compromised?**
A: The client is unaffected. The attacker can send malicious TVG commands, which at worst render garbage pixels. The client cannot be taken over through the TVG stream because TVG is data, not code.

**Q: What about DDoS?**
A: The server controls all traffic. Rate limiting, session caps, and payload size limits are enforced at the frame layer before any application logic runs.

**Q: Can Web 3.0 be used for phishing?**
A: The URL bar and security indicators are rendered by the client from server-provided TVG. A rogue server could draw a fake padlock icon. However, the client's native chrome (title bar, window border) is rendered by the client OS, not the server. Future versions will add a server-identity indicator in the client chrome.

**Q: What about accessibility?**
A: HTML structure (headings, labels, regions) is preserved for screen readers. The client exposes an accessibility tree mapped from the scene graph. TVG rendering does not preclude accessibility — it just means the accessibility tree is built from structural markup, not from pixel heuristics.

**Q: How do you handle WebRTC / video conferencing?**
A: Real-time media (audio, video) uses separate channels (WebRTC, RTMP) with permission gates controlled by the server. The TVG stream carries the UI around the video, not the video pixels themselves (though a video-surface resource type is planned for v1.1).
