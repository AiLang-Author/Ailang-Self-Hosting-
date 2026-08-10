# 03 — Wire Protocol: Message Formats, BNF Grammar, JSON Schema

> **Web 3.0 Protocol Specification — Version 1.0 (Draft)**
> **License: CC0 1.0 Universal (Public Domain Dedication)**

---

## 1. Message Grammar (BNF)

### 1.1 Top-Level

```bnf
<message>       ::= <frame-header> <frame-payload>

<frame-header>  ::= <version> <type> <flags> <length>
<version>       ::= 0x01
<type>          ::= 0x01-0x0A   ; see Frame Types table
<flags>         ::= <uint16>
<length>        ::= <uint32>

<frame-payload> ::= <hello-msg>
                  | <welcome-msg>
                  | <event-msg>
                  | <update-msg>
                  | <tvg-cmds>
                  | <html-frag>
                  | <ping-msg>
                  | <pong-msg>
                  | <close-msg>
                  | <error-msg>
```

### 1.2 HELLO (0x01) — Client → Server

```bnf
<hello-msg>     ::= <json-object> containing:
                    "version"     : <semver-string>
                    "encryption"  : [ <encryption-mode>+ ]
                    "compression" : [ <compression-mode>* ]
                    "client_nonce": <base64-32-bytes>
                    "resume"      : <session-id> | null

<encryption-mode>   ::= "aead" | "signed" | "none"
<compression-mode>  ::= "zstd" | "brotli" | "none"
```

### 1.3 WELCOME (0x02) — Server → Client

```bnf
<welcome-msg>   ::= <json-object> containing:
                    "version"       : <semver-string>
                    "session_id"    : <uuid-string>
                    "encryption"    : <encryption-mode>
                    "compression"   : <compression-mode>
                    "server_nonce"  : <base64-32-bytes>
                    "server_pubkey" : <base64-32-bytes>
                    "resume_token"  : <opaque-string> | null
```

### 1.4 EVENT (0x03) — Client → Server

```bnf
<event-msg>     ::= <json-object> containing:
                    "version"   : "1.0"
                    "type"      : "event"
                    "action"    : <action-string>
                    "target"    : <node-id> | null
                    "region"    : <region-id> | null
                    "payload"   : <json-object>
                    "seq"       : <uint64>
                    "timestamp" : <iso8601-string>

<action-string> ::= <builtin-action> | "custom:" <verb>

<builtin-action> ::= "load"
                   | "submit"
                   | "click"
                   | "change"
                   | "input"
                   | "focus"
                   | "blur"
                   | "keydown"
                   | "keyup"
                   | "poll"
                   | "stream:open"
                   | "stream:close"
```

### 1.5 UPDATE (0x04) — Server → Client

```bnf
<update-msg>    ::= <json-object> containing:
                    "version"    : "1.0"
                    "type"       : "update"
                    "seq"        : <uint64>
                    "in_reply_to": <uint64> | null
                    "region"     : <region-id> | null
                    "html"       : <html-string> | null
                    "commands"   : [ <tvg-command>* ]
                    "layout"     : <layout-patch> | null

<layout-patch>  ::= <json-object> containing:
                    "node"     : <node-id>
                    "x"        : <int32> | null
                    "y"        : <int32> | null
                    "w"        : <uint32> | null
                    "h"        : <uint32> | null
                    "visible"  : <boolean> | null
```

### 1.6 TVG_CMDS (0x05) — Server → Client

```bnf
<tvg-cmds>      ::= <uint32: count> <tvg-command>*
```

Raw binary TVG commands. See Document 04 for the full TVG command set grammar.

### 1.7 HTML_FRAG (0x06) — Server → Client

```bnf
<html-frag>     ::= <utf8-string>
```

A valid HTML fragment (not a full document). Contains structural markup with `we-*` attributes.

### 1.8 PING (0x07), PONG (0x08)

Zero-length payload. Keepalive only.

### 1.9 CLOSE (0x09)

```bnf
<close-msg>     ::= <json-object> containing:
                    "reason" : <string>
                    "code"   : <uint16>
```

### 1.10 ERROR (0x0A)

```bnf
<error-msg>     ::= <json-object> containing:
                    "code"    : <uint16>
                    "message" : <string>
                    "context" : <json-object> | null
```

---

## 2. JSON Schema Definitions

### 2.1 HELLO Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Web3 Hello",
  "type": "object",
  "required": ["version", "encryption"],
  "properties": {
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+$"
    },
    "encryption": {
      "type": "array",
      "items": { "enum": ["aead", "signed", "none"] },
      "minItems": 1
    },
    "compression": {
      "type": "array",
      "items": { "enum": ["zstd", "brotli", "none"] }
    },
    "client_nonce": {
      "type": "string",
      "minLength": 43,
      "maxLength": 44
    },
    "resume": {
      "type": "string"
    }
  }
}
```

### 2.2 EVENT Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Web3 Event",
  "type": "object",
  "required": ["version", "type", "action", "seq"],
  "properties": {
    "version": { "const": "1.0" },
    "type": { "const": "event" },
    "action": {
      "type": "string",
      "pattern": "^(load|submit|click|change|input|focus|blur|keydown|keyup|poll|stream:(open|close)|custom:[a-z][a-z0-9_-]*)$"
    },
    "target": { "type": "string" },
    "region": { "type": "string" },
    "payload": { "type": "object" },
    "seq": { "type": "integer", "minimum": 0 },
    "timestamp": { "type": "string", "format": "date-time" }
  }
}
```

### 2.3 UPDATE Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Web3 Update",
  "type": "object",
  "required": ["version", "type", "seq"],
  "properties": {
    "version": { "const": "1.0" },
    "type": { "const": "update" },
    "seq": { "type": "integer", "minimum": 0 },
    "in_reply_to": { "type": "integer", "minimum": 0 },
    "region": { "type": "string" },
    "html": { "type": "string" },
    "commands": {
      "type": "array",
      "items": { "$ref": "#/$defs/tvg-command" }
    },
    "layout": {
      "type": "object",
      "properties": {
        "node": { "type": "string" },
        "x": { "type": "integer" },
        "y": { "type": "integer" },
        "w": { "type": "integer", "minimum": 0 },
        "h": { "type": "integer", "minimum": 0 },
        "visible": { "type": "boolean" }
      },
      "required": ["node"]
    }
  }
}
```

---

## 3. Error Codes

| Code | Name | Meaning |
|------|------|---------|
| 100 | BAD_VERSION | Unsupported protocol version |
| 101 | BAD_HANDSHAKE | Invalid HELLO or WELCOME format |
| 102 | ENCRYPTION_REQUIRED | Server demands encryption, client sent none |
| 103 | ENCRYPTION_FAILED | Key negotiation or AEAD verification failed |
| 104 | BAD_FRAME | Malformed frame header |
| 105 | BAD_JSON | Invalid JSON in a text-type frame |
| 106 | BAD_TVG | Malformed TVG command stream |
| 107 | UNKNOWN_REGION | Referenced region does not exist |
| 108 | UNKNOWN_NODE | Referenced scene-graph node does not exist |
| 109 | SEQUENCE_GAP | Missing sequence number (unrecoverable) |
| 110 | SESSION_EXPIRED | Resume token expired or invalid |
| 200 | RATE_LIMIT | Too many events per second |
| 201 | PAYLOAD_TOO_LARGE | Frame exceeds max payload size |
| 500 | SERVER_ERROR | Internal server error |

---

## 4. Message Sequencing

### 4.1 Sequence Number Rules

- Each direction has an independent 64-bit monotonic sequence number starting at 0.
- EVENT frames carry the client's sequence number; UPDATE frames carry the server's.
- The `in_reply_to` field in UPDATE indicates which client EVENT triggered the update (null for server-initiated pushes).
- Missing sequence numbers are a fatal error (ERROR 109). Retransmission is NOT supported; the client must reconnect.

### 4.2 Batching

Multiple UPDATE frames MAY be sent by the server in response to a single EVENT. The client MUST process them in order. Each UPDATE carries its own sequence number.

### 4.3 Streaming Updates

For server-push scenarios (live dashboards, chat, collaborative editing):

1. Client sends `stream:open` event
2. Server responds with WELCOME-like ack
3. Server pushes UPDATE frames without `in_reply_to`
4. Client sends `stream:close` to stop
5. Server may also close the stream unilaterally

---

## 5. Examples

### 5.1 Button Click — Full Exchange

**Client (EVENT, seq=42):**
```json
{
  "version": "1.0",
  "type": "event",
  "action": "click",
  "target": "save-button",
  "region": "main-toolbar",
  "payload": {},
  "seq": 42,
  "timestamp": "2026-06-15T14:32:00Z"
}
```

**Server (UPDATE, seq=128, in_reply_to=42):**
```json
{
  "version": "1.0",
  "type": "update",
  "seq": 128,
  "in_reply_to": 42,
  "region": "main-toolbar",
  "html": "<button we-action='click' id='save-button' class='saved'>Saved ✓</button>",
  "commands": [
    {"op": "style", "node": "save-button", "fill": "#228B22"}
  ]
}
```

### 5.2 Form Input — Key-by-Key Update

**Client (EVENT, seq=43):**
```json
{
  "version": "1.0",
  "type": "event",
  "action": "input",
  "target": "name-field",
  "region": "form",
  "payload": {"value": "Sean Collins", "cursor": 12},
  "seq": 43
}
```

**Server (UPDATE, seq=129, in_reply_to=43):**
```json
{
  "version": "1.0",
  "type": "update",
  "seq": 129,
  "in_reply_to": 43,
  "region": "form",
  "commands": [
    {"op": "text", "node": "name-field-text", "content": "Sean Collins"}
  ]
}
```

### 5.3 Live Dashboard Tick (Server Push)

**Server (UPDATE, seq=130, in_reply_to=null):**
```json
{
  "version": "1.0",
  "type": "update",
  "seq": 130,
  "region": "dashboard",
  "commands": [
    {"op": "replace", "node": "cpu-gauge", "data": {"value": 0.73, "color": "#FFA500"}},
    {"op": "replace", "node": "mem-bar", "data": {"value": 0.45, "color": "#228B22"}},
    {"op": "transform", "node": "needle-1", "matrix": [0.866, -0.5, 0.5, 0.866, 0, 0]}
  ]
}
```
