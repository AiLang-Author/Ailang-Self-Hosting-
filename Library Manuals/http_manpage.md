# Library.HTTP (ailang)

## NAME
`Library.HTTP` — HTTP/1.1 client via curl subprocess with streaming line-read

## SYNOPSIS
```ailang
LibraryImport.HTTP
```
> Requires: `LibraryImport.Arena`, `LibraryImport.StringUtils`

## DESCRIPTION

HTTP is a **curl-backed** HTTP/1.1 client. It forks a `curl` subprocess for
each request, piping stdin/stdout. Curl handles TLS 1.3, IPv6, redirects,
chunked encoding, and keepalive — the library provides a thin streaming
wrapper and line-oriented read API.

Two modes are provided:

| Mode | Functions | Use when |
|------|-----------|----------|
| **One-shot** | `Get`, `Post` | Simple request/response, body fits in memory |
| **Streaming** | `GetStream`, `PostStream`, `ReadLine`, `ReadLineTimeout`, `CloseStream` | SSE, chunked responses, large downloads |

The library uses raw Linux syscalls (`fork`, `execve`, `pipe`, `read`, `poll`,
`wait4`) — no libc dependency beyond the `curl` binary on `PATH` (default
`/usr/bin/curl`, overridable via `HConst.CURL_PATH`).

---

## ONE-SHOT API

### GET

```
HTTP.Get(url, headers_str)  → Address (body String) or 0
```

Sends a GET request, drains the response body into a single heap-allocated
string, and returns it. Returns **0** on failure (curl spawn failure, non-200
status, etc.). The caller must `Deallocate` the returned string.

### POST

```
HTTP.Post(url, headers_str, body_str)  → Address (body String) or 0
```

Sends a POST request with `body_str` as the request body (Content-Type must
be set via `headers_str`). Otherwise identical to `Get`.

---

## STREAMING API

### Starting a stream

```
HTTP.GetStream(url, headers_str, conn_to, max_to)  → Address (handle) or 0
HTTP.PostStream(url, headers_str, body_str, conn_to, max_to)  → Address (handle) or 0
```

Spawns `curl` and returns a **stream handle** (40-byte heap allocation). The
handle is opaque; pass it to `ReadLine`/`ReadLineTimeout`/`CloseStream`.

Parameters:
- `url` — null-terminated URL string
- `headers_str` — newline-separated header lines, or 0 for none
- `body_str` — request body (PostStream only), or 0
- `conn_to` — reserved (passed through, not used by curl build currently)
- `max_to` — reserved (passed through)

The curl command assembled is:
```
/usr/bin/curl -sS -N --limit-rate 1M --connect-timeout 10 -m 180 \
    [-X POST --data-binary @- -H "Expect:"] \
    [-H "<each header line>"] \
    <url>
```

Key flags:
- `-sS` — silent but show errors
- `-N` — disable buffering (required for streaming SSE)
- `--limit-rate 1M` — cap download at 1 MB/s
- `--connect-timeout 10` — 10-second connect timeout
- `-m 180` — 180-second total timeout
- `-H "Expect:"` — suppresses curl's automatic `Expect: 100-continue` header for POST bodies > 1024 bytes

### Reading lines

```
HTTP.ReadLine(handle, out_buf, maxlen)  → Integer
HTTP.ReadLineTimeout(handle, out_buf, maxlen, timeout_ms)  → Integer
```

Reads the next line from the curl stdout pipe. Lines are delimited by `\n`;
trailing `\r` is stripped. The decoded line is copied into the caller-provided
`out_buf` (up to `maxlen` bytes). Longer lines are silently truncated.

Return values:

| Return | Meaning |
|--------|---------|
| ≥ 0   | Line length copied into `out_buf` (0 = blank line, just `\n`) |
| -1    | EOF — stream exhausted or closed |
| -2    | Timeout — no data available after `timeout_ms` milliseconds (**ReadLineTimeout only**) |

`ReadLine` blocks until a line is available or EOF.

`ReadLineTimeout` polls with `SYS_POLL` before blocking. When no data is ready
within `timeout_ms`, it returns `-2` — the caller should tick animations/UI
and retry. The handle remains valid and subsequent calls will continue reading.

### Closing a stream

```
HTTP.CloseStream(handle)  → void
```

Closes the stdout pipe, waits for the curl child process (non-blocking
`wait4`), frees the internal line buffer and handle. Safe to call on 0.

---

## HEADERS FORMAT

`headers_str` is a **newline-separated** string of HTTP header lines:

```
"Authorization: Bearer sk-abc123\nContent-Type: application/json\n"
```

Each non-empty line becomes a separate `-H "<line>"` argument to curl. Empty
lines are ignored. No trailing newline is required. Pass **0** if no headers
are needed.

---

## INTERNALS

### Stream handle layout (40 bytes)

| Offset | Size | Field |
|--------|------|-------|
| 0  | 4 | `stdin_fd` (always -1 after spawn; parent closes it) |
| 4  | 4 | `stdout_fd` (read end of stdout pipe) |
| 8  | 8 | `pid` (curl child PID) |
| 16 | 8 | `line_buf` (Address of 8192-byte ring buffer) |
| 24 | 4 | `buf_pos` (read cursor) |
| 28 | 4 | `buf_end` (end of valid data) |
| 32 | 4 | `eof_flag` (1 once read returns 0/error) |
| 36 | 4 | reserved |

### Constants (`HConst`)

| Constant | Default | Meaning |
|----------|---------|---------|
| `CURL_PATH` | `/usr/bin/curl` | Path to curl binary (set before first request) |
| `MAX_HEADERS` | 32 | Maximum header lines (internal limit) |
| `READ_BUF_SZ` | 8192 | Internal line buffer size |

### Syscall constants (`HSys`)

The library uses raw syscall numbers: `SYS_READ`(0), `SYS_WRITE`(1),
`SYS_OPEN`(2), `SYS_CLOSE`(3), `SYS_POLL`(7), `SYS_PIPE`(22),
`SYS_DUP2`(33), `SYS_FORK`(57), `SYS_EXECVE`(59), `SYS_EXIT`(60),
`SYS_WAIT4`(61), `SYS_FCNTL`(72).

---

## MEMORY

| Allocation | Freed by |
|---|---|
| Stream handle (40 bytes) | `CloseStream` |
| Internal line buffer (8192 bytes) | `CloseStream` |
| One-shot body string | **Caller** (`Deallocate`) |
| Duplicated header lines (internal) | **Caller** (strings aliased into argv, freed after child exits) |

---

## EXAMPLE: One-shot GET

```ailang
LibraryImport.HTTP
LibraryImport.StringUtils

body = HTTP.Get("http://example.com/api/status", 0)
IfCondition EqualTo(body, 0) ThenBlock: {
    StringUtils.PrintString "[ERROR] HTTP.Get failed\n"
    ReturnValue(1)
}
StringUtils.PrintString body
Deallocate body, 0
```

## EXAMPLE: One-shot POST with JSON

```ailang
LibraryImport.HTTP
LibraryImport.JSON
LibraryImport.StringUtils

# Build JSON body
JSON.NewObject → payload
JSON.SetString payload "prompt" "Hello"
JSON.SetNumber payload "max_tokens" "256"
body_json = JSON.Serialize(payload)

# Headers
hdr = "Content-Type: application/json\nAuthorization: Bearer sk-...\n"

resp = HTTP.Post("https://api.example.com/v1/chat", hdr, body_json)
# ... use resp ...
Deallocate body_json, 0
JSON.Free payload
Deallocate resp, 0
```

## EXAMPLE: Streaming SSE

```ailang
LibraryImport.HTTP
LibraryImport.StringUtils

hdr = "Authorization: Bearer sk-...\nContent-Type: application/json\n"
body_json = ...  # serialized JSON request
handle = HTTP.PostStream("https://api.example.com/v1/stream", hdr, body_json, 10000, 900000)
IfCondition EqualTo(handle, 0) ThenBlock: {
    StringUtils.PrintString "[ERROR] PostStream failed\n"
    ReturnValue(1)
}

line_buf = Allocate(1048576)  # 1 MB line buffer
WhileLoop 1 {
    line_len = HTTP.ReadLineTimeout(handle, line_buf, 1048575, 15)
    IfCondition LessThan(line_len, 0) ThenBlock: {
        IfCondition EqualTo(line_len, -1) ThenBlock: { BreakLoop }  # EOF
        IfCondition EqualTo(line_len, -2) ThenBlock: { ContinueLoop }  # timeout, retry
    }
    IfCondition GreaterThan(line_len, 0) ThenBlock: {
        SetByte line_buf line_len 0  # null-terminate
        # Process line_buf (e.g. "data: {...}")
    }
}
HTTP.CloseStream(handle)
Deallocate line_buf, 1048576
```

---

## SEE ALSO
- `Library.Socket` — raw TCP sockets (curl provides TLS, but Socket is available for direct connections)
- `Library.JSON` — serialises/parses the bodies this library transports
- `Library.StringUtils` — string operations for header/body manipulation
- `Library.HTTPServer` — server-side HTTP (separate library)

---

## VERSION
2026-05-16 — rewritten to match actual curl-backed streaming implementation

## COPYRIGHT
Copyright (c) 2025–2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
