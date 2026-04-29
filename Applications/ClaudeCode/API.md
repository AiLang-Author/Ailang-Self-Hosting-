# Claude Code (AILang Native) — API Reference

Companion to `ClaudeCode.md` (which is design rationale). This document is
**reference material** — every wire protocol, every public function, every
JSON shape. Read this when you want to extend the system.

Conventions used throughout:
- All sockets use **4-byte big-endian length prefix + JSON body** framing
  (matches the existing `Library.IPCBroker` protocol elsewhere in the
  AILang stack — same `Socket.SendMsg` / `Socket.RecvMsg` works for any
  IPC endpoint here).
- All file paths are absolute (the binary doesn't do CWD-relative resolution).
- All token storage files are mode `0600`.

---

## Part 1 — cc_tools wire protocol

The single source of truth for how `ClaudeCode.x` talks to its tool
services. If you build a new tool, conform to this and you're done.

### Transport

- Unix domain socket per tool, at `/tmp/ailang_cctools/<ToolName>.sock`
- One persistent connection per tool, opened once at ClaudeCode startup,
  reused for every dispatch
- Framing: 4-byte big-endian length + UTF-8 JSON body
- Both sides use `Library.Socket.SendMsg` / `Library.Socket.RecvMsg`
  which already implement the framing

### Messages

#### Schema discovery (called once at registration time)

Request:
```json
{ "method": "schema" }
```

Response:
```json
{
  "method": "schema_response",
  "schema": {
    "name": "Read",
    "description": "Read a file from disk and return its contents",
    "input_schema": {
      "type": "object",
      "properties": {
        "path":   { "type": "string",  "description": "Absolute path to the file to read" },
        "offset": { "type": "integer", "description": "Byte offset to start reading from" },
        "limit":  { "type": "integer", "description": "Max bytes to read (0 = all up to MAX_OUTPUT)" }
      },
      "required": ["path"]
    }
  }
}
```

The `schema` object's shape matches the Anthropic `tools[]` array entry
exactly — `IPCDispatch.GetToolSchemasArray()` aggregates these and feeds
them straight into the API request without transformation.

#### Tool call

Request:
```json
{
  "method": "call",
  "id": "toolu_01ABC...",
  "args": { "path": "/etc/hostname" }
}
```

Success response:
```json
{
  "method": "result",
  "id": "toolu_01ABC...",
  "ok": true,
  "content": "DESKTOP-3EKCN32\n",
  "truncated": false
}
```

Failure response:
```json
{
  "method": "result",
  "id": "toolu_01ABC...",
  "ok": false,
  "error": "open failed: /missing"
}
```

Field semantics:
- **`id`** — opaque, echoed back. ClaudeCode uses it to match results to
  the originating `tool_use` block when sending `tool_result`s back to
  the model.
- **`ok`** — boolean. If false, the model's `tool_result` is marked
  `is_error: true` and the model usually retries or asks the user for
  guidance.
- **`content`** — the string body the model sees. Free-form. For a
  shell command it's stdout+stderr+exit; for a file read it's the file
  bytes; for a fetch it's the response body.
- **`truncated`** — set true when `content` was capped at `MAX_OUTPUT`
  (60KB by convention). Tool services SHOULD append a marker line
  (`\n[truncated]`) to make the cutoff visible to the model.

### Adding a new tool

```bash
# 1. Author the service. Easiest path: copy an existing one.
cp Applications/ClaudeCode/cc_tools/cc_read_ipc.ailang \
   Applications/ClaudeCode/cc_tools/cc_mytool_ipc.ailang
# Edit: change CCRead → CCMytool, swap the schema + handler body

# 2. Compile
./ailang.x Applications/ClaudeCode/cc_tools/cc_mytool_ipc.ailang cc_mytool_ipc.x

# 3. Register in ClaudeCode.ailang Main:
#      CC_LaunchTool("./cc_mytool_ipc.x")
#      IPCDispatch.RegisterTool("MyTool", "/tmp/ailang_cctools/MyTool.sock")

# 4. Rebuild ClaudeCode.x
./ailang.x Applications/ClaudeCode/ClaudeCode.ailang ClaudeCode.x
```

The model sees the new tool in the next `/v1/messages` request's
`tools[]` array, learns its schema, and can call it.

### Standalone testability

Every cc_tool can be exercised without ClaudeCode running:

```python
import socket, struct, json
s = socket.socket(socket.AF_UNIX)
s.connect('/tmp/ailang_cctools/Read.sock')

# Schema check
req = json.dumps({'method': 'schema'}).encode()
s.send(struct.pack('>I', len(req)) + req)
hdr = s.recv(4); n = struct.unpack('>I', hdr)[0]
print(json.loads(s.recv(n)))

# Real call
req = json.dumps({'method': 'call', 'id': 'test1', 'args': {'path': '/etc/hostname'}}).encode()
s.send(struct.pack('>I', len(req)) + req)
hdr = s.recv(4); n = struct.unpack('>I', hdr)[0]
print(json.loads(s.recv(n)))
```

This is the recommended way to verify a new tool service before adding
the registration line in ClaudeCode.

---

## Part 2 — Library.UtilArgs schema format

The OS-wide unified argument-format library. Every cc_tool defines its
schema once, gets four surfaces from it for free:

1. CLI flag parser (for shell users who run the tool directly)
2. IPC JSON parser (for ClaudeCode dispatch)
3. JSON Schema export (for the Anthropic API tools array)
4. `--help` text generator

### Building a schema

```ailang
schema = UtilArgs_NewSchema(
    "Read",
    "Read a file from disk and return its contents"
)

// Field: AddField(schema, name, type, required, description, cli_long)
UtilArgs_AddField(schema, "path",   "path",   1, "Absolute path to read", "path")
UtilArgs_AddField(schema, "offset", "int",    0, "Byte offset",           "offset")
UtilArgs_AddField(schema, "limit",  "int",    0, "Max bytes (0=all)",     "limit")

// Optional: short flag and default value
UtilArgs_SetShort(schema, "path", "p")
UtilArgs_SetDefault(schema, "offset", "0")
UtilArgs_SetDefault(schema, "limit",  "0")
```

### Type system

| Type     | JSON Schema mapping | CLI parsing                       |
|----------|---------------------|------------------------------------|
| `string` | `"string"`          | next arg consumed as value         |
| `int`    | `"integer"`         | next arg parsed as decimal integer |
| `bool`   | `"boolean"`         | presence-only flag (no value)      |
| `path`   | `"string"`          | hint for tooling; same as string   |

### Public API

```
UtilArgs_NewSchema(name, description)              -> schema_obj
UtilArgs_AddField(schema, name, type, required, desc, cli_long)
UtilArgs_SetShort(schema, field_name, short_char)
UtilArgs_SetDefault(schema, field_name, default_str)

UtilArgs_ParseCLI(schema)                          -> args_obj  (reads /proc/self/cmdline)
UtilArgs_ParseIPC(schema, args_obj)                -> args_obj  (validates + applies defaults)

UtilArgs_GetString(args, name)                     -> Address
UtilArgs_GetInt(args, name)                        -> Integer
UtilArgs_GetBool(args, name)                       -> Integer (0 or 1)

UtilArgs_PrintHelp(schema)                         -> writes to stdout
UtilArgs_ExportToolSchema(schema)                  -> JSON string (Anthropic-compatible)
```

The same library is intended for backporting all 56 AiLang sysutils to a
single common arg format. Claude Code's six tools are just the first six
adopters.

---

## Part 3 — Library.HTTP

Generic HTTP client + server. Server side is unchanged from
`Library.HTTPServer.ailang`; the client side is new and curl-backed
(via subprocess pipes, hidden behind the public API).

### Public client API

```
HTTP.Get(url, header_list_str)                     -> body_str (one-shot)
HTTP.Post(url, header_list_str, body_str)          -> body_str (one-shot)
HTTP.PostStream(url, header_list_str, body_str)    -> stream_handle
HTTP.ReadLine(stream_handle, buf, maxlen)          -> bytes_read (-1 on EOF)
HTTP.CloseStream(stream_handle)
```

### header_list_str format

Newline-separated header lines, no values escaped:
```
"x-api-key: sk-ant-api03-...\nanthropic-version: 2023-06-01\ncontent-type: application/json"
```

Empty string is fine (no headers).

### Stream lifecycle

Streaming POST is the workhorse for the Anthropic Messages API:

```ailang
handle = HTTP.PostStream(url, headers, body_str)
buf = Allocate(16384)
WhileLoop 1 {
    n = HTTP.ReadLine(handle, buf, 16384)
    IfCondition LessThan(n, 0) ThenBlock: { BreakLoop }
    // process the line — typically feed to SSE.FeedLine
}
HTTP.CloseStream(handle)
```

Internals: `HTTP.PostStream` does `fork+exec curl --no-buffer -N --data-binary @-`,
pipes the body in via stdin, exposes stdout as a line-buffered stream.
Curl handles TLS, IPv6, redirects, keepalive. Future native-TLS
implementations can replace the curl subprocess; the public API doesn't
mention curl.

---

## Part 4 — Library.SSE

Line-driven Server-Sent Events parser. Caller drives by feeding one
physical line at a time (already stripped of `\n`).

### Public API

```
SSE.Init(state_buf, state_buf_len)
SSE.FeedLine(state, line, line_len)                -> 1 if event ready, 0 otherwise
SSE.GetEventType(state)                            -> Address
SSE.GetEventData(state)                            -> Address
SSE.GetEventDataLen(state)                         -> Integer
SSE.Reset(state)                                   -> reset after consuming event
```

### Typical loop

```ailang
sse = Allocate(SSE_STATE_SIZE)   // 88 bytes
SSE.Init(sse, SSE_STATE_SIZE)
WhileLoop EqualTo(stream_done, 0) {
    n = HTTP.ReadLine(handle, line, 16384)
    IfCondition LessThan(n, 0) ThenBlock: { stream_done = 1 }
    IfCondition GreaterEqual(n, 0) ThenBlock: {
        IfCondition EqualTo(SSE.FeedLine(sse, line, n), 1) ThenBlock: {
            evt_type = SSE.GetEventType(sse)
            evt_data = SSE.GetEventData(sse)
            // dispatch the event
            SSE.Reset(sse)
        }
    }
}
```

Why line-driven: SSE events span multiple TCP reads, and chunks split
across event boundaries randomly. A chunk-driven parser desyncs. The
caller (HTTP.ReadLine) handles byte-stream-to-line; SSE only deals with
the protocol. Survives any TCP fragmentation.

---

## Part 5 — Library.OAuth

Generic OAuth 2.0 + PKCE client. Knows nothing about Anthropic. Could
drive any provider that supports authorization-code flow with PKCE.

### Public API

```
OAuth.GeneratePKCE()                                            -> JSON {verifier, challenge}
OAuth.FetchAuthServerMetadata(metadata_url)                     -> JSON of RFC 8414 metadata
OAuth.RegisterClient(registration_endpoint, metadata_obj)        -> JSON registration response (DCR, RFC 7591)

OAuth.BuildAuthorizeURL(authorize_ep, client_id, redirect_uri,
                        scopes_arr, state, code_challenge)       -> URL string
OAuth.LaunchBrowser(url, browser_cmd)                            -> 0/1
OAuth_BindLocalhostPort(port, out_port_ptr)                      -> listen_fd or -1
OAuth_BindLocalhostAny(out_port_ptr)                             -> listen_fd or -1
OAuth.RunCallbackServer(listen_fd, expected_state, timeout_secs) -> JSON {code} or 0

OAuth.ExchangeCode(token_endpoint, client_id, code,
                   redirect_uri, code_verifier)                  -> tokens JSON or 0
OAuth.RefreshTokens(token_endpoint, client_id, refresh_token)    -> tokens JSON or 0

OAuth.SaveTokens(path, tokens_obj)                               -> 0/1 (writes mode 0600)
OAuth.LoadTokens(path)                                           -> tokens JSON or 0
OAuth.IsExpired(tokens_obj, leeway_secs)                         -> 0/1
OAuth.GetAccessToken(tokens_obj)                                 -> string or 0
OAuth.GetRefreshToken(tokens_obj)                                -> string or 0
```

### PKCE primitives

- `verifier` is `base64url(32 random bytes from /dev/urandom)`
- `challenge` is `base64url(sha256(verifier))`
- SHA256 is computed by shelling to `sha256sum | xxd | base64 | tr` —
  one call per OAuth handshake, not in any hot path
- All base64url is RFC 4648 §5 (no padding, `+/` → `-_`)

### Token storage shape

`oauth_tokens.json`:
```json
{
  "access_token":  "sk-ant-oat01-...",
  "refresh_token": "sk-ant-ort01-...",
  "expires_in":    3600,
  "expires_at":    1730000000,
  "token_type":    "Bearer",
  "scope":         "user:inference user:profile"
}
```

`expires_at` is computed at save time (`now + expires_in`) so freshness
checks don't need to know when the token was issued.

---

## Part 6 — App-level modules (Applications/ClaudeCode/)

These are NOT generic — they're Claude Code app code. Documented here so
future contributors can extend the agent loop without re-reading source.

### Anthropic.ailang

```
Anthropic.Init(auth_mode_str, credential, model, system_prompt)

Anthropic.BuildHeaders()                          -> string  (x-api-key OR Authorization: Bearer)
Anthropic.BuildRequest(messages_arr, tools_arr)   -> body_str (full /v1/messages JSON)
Anthropic.GetURL()                                -> string

Anthropic.OnEvent(event_type, event_data)         -> signal
   // signal values:
   //   AnthSignal.CONTINUE             (0) — keep streaming
   //   AnthSignal.TURN_DONE_NO_TOOLS   (1) — message_stop, no tool calls
   //   AnthSignal.TURN_DONE_WITH_TOOLS (2) — message_stop, dispatch tools

Anthropic.GetPendingTools()                       -> JSON array of tool_use objects
Anthropic.GetToolName(idx)                        -> stable string (workaround)
Anthropic.GetToolId(idx)                          -> stable string (workaround)

Anthropic.CommitAssistantToHistory()              -> wrap text+tool_blocks, push to History
Anthropic.AppendToolResultsToHistory(results_arr) -> wrap as user message, push
Anthropic.Reset()                                 -> clear per-turn state
```

`auth_mode_str` is `"oauth"` or `"apikey"`. `credential` is the bearer
token or API key respectively.

### History.ailang

```
History.Init()
History.AppendUser(text)
History.AppendAssistantText(text)
History.AppendAssistantBlocks(content_arr)        -> with tool_use blocks
History.AppendToolResults(content_arr)            -> with tool_result blocks
History.GetMessagesArray()                        -> JSON array (live ref)
History.Count()                                   -> Integer
```

Eviction is automatic when `count > MAX_MESSAGES` (100). Drops the
oldest user/assistant pair, preserving `tool_use`/`tool_result` pairing.

### IPCDispatch.ailang

```
IPCDispatch.Init()
IPCDispatch.Shutdown()                            -> closes all tool sockets
IPCDispatch.RegisterTool(name, sock_path)         -> 1 on success, 0 on fail
IPCDispatch.GetToolSchemasArray()                 -> JSON array (feed to BuildRequest)
IPCDispatch.Dispatch(name, input_obj, tool_use_id, out_is_error_ptr) -> content_str
```

### Auth.ailang

```
Auth.LoadConfig(path)                             -> JSON or 0
Auth.WriteDefaultOAuthConfig(path)                -> 0/1
Auth.RunOAuthFlow(config_path, client_path, tokens_path) -> result_obj
Auth.RunAPIKeyFlow(api_key)                       -> result_obj
```

Result object:
```json
{
  "status":     "ok" | "needs_setup_oauth" | "needs_setup_apikey" | "error",
  "mode":       "oauth" | "apikey",      // when status=="ok"
  "credential": "<token-or-key>",        // when status=="ok"
  "message":    "<human-readable>"
}
```

### UI.ailang

```
UI.Init()                                         -> grab raw mode, paint initial frame
UI.Shutdown()                                     -> restore terminal

UI.SplashFile(path, delay_ms)                     -> scroll-print ANSI art (cooked mode!)

UI.SessionHeader(version, model_line, cwd)        -> small mascot + info block
UI.ChatPrint(s)                                   -> append text to chat region
UI.ChatPrintln(s)                                 -> append text + newline
UI.ChatTag(tag, body, color_index)                -> colored prefix line
UI.ToolCallStart(name, arg_summary)               -> "● Read(/etc/hostname)"
UI.ToolCallEnd(ok)                                -> "  ✓" or "  ✗"

UI.ReadLine()                                     -> blocking input from pinned bottom prompt
UI.PrintHelp()                                    -> render the slash-command list
```

`color_index` values for `ChatTag`:
```
UIColors.ORANGE_FG = 3   // Anthropic brand orange (TUI yellow ≈ orange)
UIColors.DIM_FG    = 8
UIColors.WHITE_FG  = 7
UIColors.GREEN_FG  = 2
UIColors.RED_FG    = 1
UIColors.CYAN_FG   = 6
```

### ClaudeCode.ailang

Entry point. Not a library, but the high-level flow:

```
Main() {
    UI.SplashFile("./splash.ans", 30)
    auth_choice = CC_PromptAuthMode()
    auth_result = (choice == 1) ? Auth.RunOAuthFlow(...) : Auth.RunAPIKeyFlow(...)
    handle bootstrap (needs_setup_*)
    History.Init()
    IPCDispatch.Init()
    Anthropic.Init(mode, credential, MODEL, SYSTEM_PROMPT)
    fork+exec each cc_tool service
    IPCDispatch.RegisterTool(...) for each
    UI.Init()
    UI.SessionHeader(...)
    loop {
        line = UI.ReadLine()
        if /quit -> break
        if /help -> UI.PrintHelp()
        if /clear -> History.Init()
        else -> History.AppendUser(line); CC_RunTurn()
    }
    IPCDispatch.Shutdown()
    CC_KillAllChildren()
    UI.Shutdown()
}

CC_RunTurn() {
    loop {
        body = Anthropic.BuildRequest(History.GetMessagesArray(),
                                      IPCDispatch.GetToolSchemasArray())
        handle = HTTP.PostStream(Anthropic.GetURL(), Anthropic.BuildHeaders(), body)
        SSE.Init(...)
        loop {
            line = HTTP.ReadLine(handle, ...)
            if EOF -> break
            if SSE.FeedLine(...) ready -> Anthropic.OnEvent(...) -> maybe set stream_done
        }
        Anthropic.CommitAssistantToHistory()
        if no pending tools -> break
        for each pending tool:
            content = IPCDispatch.Dispatch(name, input, id, ...)
            collect result
        Anthropic.AppendToolResultsToHistory(results)
        Anthropic.Reset()
    }
}
```

---

## Part 7 — Build & runtime requirements

### Build

```bash
cd /mnt/c/Users/Sean/Documents/AILangSH

./ailang.x Applications/ClaudeCode/ClaudeCode.ailang ClaudeCode.x

for t in read head ls write bash webfetch; do
  ./ailang.x Applications/ClaudeCode/cc_tools/cc_${t}_ipc.ailang cc_${t}_ipc.x
done
```

### Runtime prerequisites (WSL or native Linux)

- `curl` on PATH (for HTTPS via `Library.HTTP`)
- `sha256sum`, `xxd`, `base64`, `tr` — coreutils (for OAuth PKCE; should
  be present on any default distro)
- `chafa` if you want to regenerate `splash.ans` from new images
- `wslview` (WSL only) or `xdg-open` (Linux) for OAuth browser launch
- `/dev/urandom` readable (always is)

### Environment variables

| Var                   | Purpose                                                |
|-----------------------|--------------------------------------------------------|
| `ANTHROPIC_API_KEY`   | API key path (option 2). Without it: bootstrap flow.    |
| `CC_NO_SPLASH`        | Skip the boot splash if set to anything non-empty.      |
| `PWD`                 | Used as cwd display in `UI.SessionHeader`.              |
| `HOME`                | Used by `~/.claudecode/` config path expansion.         |

### Files written by ClaudeCode

| Path                              | Purpose                          |
|-----------------------------------|----------------------------------|
| `~/.claudecode/oauth_config.json` | OAuth endpoints (mode 0600)      |
| `~/.claudecode/oauth_client.json` | DCR client_id (mode 0600)        |
| `~/.claudecode/oauth_tokens.json` | Access + refresh tokens (mode 0600) |
| `/tmp/ailang_cctools/<Tool>.sock` | Per-tool Unix socket (auto-removed)  |

### Files read by ClaudeCode

| Path                  | Purpose                                                  |
|-----------------------|----------------------------------------------------------|
| `./splash.ans`        | Optional ANSI splash art (loaded at boot if present)     |
| `./cc_*_ipc.x`        | The 6 tool service binaries, fork+exec'd at startup       |
| `~/.claudecode/*`     | Auth state (created by first OAuth flow if option 1)     |
| `/proc/self/environ`  | For `CC_GetEnv` env-var reads (used everywhere)          |
| `/proc/self/cmdline`  | For `UtilArgs_ParseCLI` (used by tool services for `--help`) |

---

*Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.*
