# Claude Code (AILang Native) — Status & Design

A native AILang implementation of a Claude Code-style chat client. Talks
directly to the Anthropic Messages API. No Node, no Bun, no JavaScript.
Tool calls dispatch via IPC to forked sysutil services.

This is the design source of truth. Code is the implementation; this file
explains the *why*.

---

## Current Status (2026-04-28)

**Functionally working end-to-end on the API-key path.**
Verified live: text streaming, multi-turn conversation, tool dispatch
(Read tool returns `/etc/hostname` content), all 6 tools register and
respond.

**Working components**
- Auth-mode prompt: option 1 (subscription / OAuth) or option 2 (API key)
- API key path: `ANTHROPIC_API_KEY` from env, billed against
  console.anthropic.com prepaid balance
- Streaming Messages API: SSE events parsed line-by-line, text deltas
  rendered live, tool_use blocks accumulated and dispatched on
  `message_stop`
- 6 IPC tool services: Read, Head, LS, Write, Bash, WebFetch — each a
  separate `cc_*_ipc.x` binary auto-launched by `ClaudeCode.x` at startup,
  killed on quit
- History ring buffer with tool_use/tool_result pairing-aware eviction
- UTF-8-aware display-width counting
- Anthropic orange truecolor (`#cc785c`) on supporting terminals

**Blocked / pending**
- **OAuth subscription flow (option 1)**: bound by Anthropic
  github.com/anthropics/claude-code issue #54184. Token endpoint accepts
  our request shape but returns `rate_limit_error` for any code we send.
  Code is built and ready (`Library.OAuth.ailang`, `Auth.ailang`) but
  falls back to API key on session entry. Awaiting guidance on whether
  third-party clients should use `/v1/messages` with Bearer or
  `/v1/sessions/*`.
- **TUI prompt pinning**: cooked-mode line input fights bottom-anchored
  cursor positioning. Visible bugs: prompt floats inline after responses,
  bottom rule sometimes wider than top rule on >100col terminals. Refactor
  to raw-mode `Library.TUI` (which dnd_game uses successfully) is the
  structural fix — task #26.
- **Library.JSON hash collision** (workaround in place): reading the key
  `"name"` back from a populated object returns `"index"` due to XSHash
  bucket collision when the object also holds an `"input"` sub-object.
  Workaround: `Anthropic.ailang` keeps a parallel string-pointer array
  for tool name/id; `IPCDispatch` reads from there. Real fix should be
  filed against Library.JSON.

---

## What this binary is

`ClaudeCode.x` is a single-user terminal chat client.

```
              ┌────────────────────────────────┐
              │       Anthropic Messages API   │  HTTPS
              │     api.anthropic.com/v1/...   │
              └─────────────┬──────────────────┘
                            │  curl --no-buffer
                            ▼
              ┌────────────────────────────────┐
              │  Library.HTTP.PostStream       │  fork+exec curl, pipes
              └─────────────┬──────────────────┘
                            │  one line at a time
                            ▼
              ┌────────────────────────────────┐
              │  Library.SSE.FeedLine          │  builds events from
              └─────────────┬──────────────────┘  event:/data: lines
                            │  type+data per event
                            ▼
              ┌────────────────────────────────┐
              │  Anthropic.OnEvent             │  text → stdout, tool_use
              └─────────────┬──────────────────┘  → tool_blocks queue
                            │  on message_stop
                            ▼
              ┌────────────────────────────────┐
              │  IPCDispatch.Dispatch          │  per tool: send call,
              └─────────────┬──────────────────┘  recv result
                            │  Unix socket
                            ▼
              ┌────────────────────────────────┐
              │  cc_*_ipc.x service            │  fork/syscall, return
              └────────────────────────────────┘  via IPC envelope
```

Inside the agent loop, the model emits text + zero-or-more tool_use blocks
per turn; we dispatch them all in parallel after `message_stop`, send the
results back as one user message containing N `tool_result` blocks, and
continue until the model emits a turn with no tool calls.

---

## File layout

```
Documents/AILangSH/
├── Librarys/                                 [generic, reusable]
│   ├── Library.HTTP.ailang                   curl-backed HTTP client + SSE-friendly streaming
│   ├── Library.SSE.ailang                    line-driven SSE parser
│   ├── Library.UtilArgs.ailang               schema → CLI/IPC/tool-schema/help (OS-wide arg format)
│   ├── Library.OAuth.ailang                  OAuth 2.0 + PKCE client (PKCE/S256, callback server, token storage)
│   └── Library.{TUI,JSON,Socket,Arena,HashMap,StringUtils,…}   reused, unchanged
├── splash.ans                                ANSI splash art read at boot (optional)
└── Applications/ClaudeCode/
    ├── ClaudeCode.md                         this file (design doc)
    ├── API.md                                IPC envelope spec + library API reference
    ├── ClaudeCode.ailang                     entry point + agent loop + tool dispatch
    ├── UI.ailang                             raw-mode TUI (Library.TUI wrapper)
    ├── Anthropic.ailang                      Messages API request shape + SSE event router
    ├── History.ailang                        message ring buffer (pairing-aware eviction)
    ├── IPCDispatch.ailang                    generic per-tool IPC client
    ├── Auth.ailang                           auth dispatcher: API key vs OAuth, with bootstrap UX
    ├── splash.png / splash.ans               splash assets (text loaded at runtime)
    └── cc_tools/
        ├── cc_read_ipc.ailang
        ├── cc_head_ipc.ailang
        ├── cc_ls_ipc.ailang
        ├── cc_write_ipc.ailang
        ├── cc_bash_ipc.ailang
        └── cc_webfetch_ipc.ailang
```

`LibraryImport.X` resolves `Librarys/Library.X.ailang` from project root.
`Import.Applications.ClaudeCode.X` resolves
`Applications/ClaudeCode/X.ailang`. Both must be invoked with the
project root as CWD (e.g. `cd /mnt/c/Users/Sean/Documents/AILangSH`
before running `./ailang.x ...` or `./ClaudeCode.x`).

User-private state (mode 0600) lives at `~/.claudecode/`:
- `oauth_config.json` — OAuth endpoints + scopes (per-user editable)
- `oauth_client.json` — Dynamic client registration result (cached)
- `oauth_tokens.json` — access + refresh tokens (refresh proactively)

---

## Tool envelope (the OS-wide format)

Every cc_tool service speaks the same JSON envelope over a Unix socket
with 4-byte big-endian length prefix (matching the existing IPC broker).

```
Schema discovery:
  request:  {"method":"schema"}
  response: {"method":"schema_response","schema":{...JSON Schema...}}

Tool call:
  request:  {"method":"call","id":"<tool_use_id>","args":{...}}
  response: {"method":"result","id":"<tool_use_id>","ok":true,
             "content":"...","truncated":false}
  error:    {"method":"result","id":"<tool_use_id>","ok":false,
             "error":"ENOENT: /missing"}
```

Adding a new tool:

1. Write `cc_<name>_ipc.ailang` defining its `UtilArgs` schema and
   handler. Bind a socket at `/tmp/ailang_cctools/<Name>.sock`.
2. Add one line to `ClaudeCode.ailang`:
   `IPCDispatch.RegisterTool("<Name>", "/tmp/ailang_cctools/<Name>.sock")`
3. Done. ClaudeCode pulls the schema at startup, the model sees the new
   tool in the next turn's `tools[]` array.

The ClaudeCode binary contains zero tool-specific logic. New tools never
require recompiling it.

---

## Tool table (Phase 1)

| Tool | Schema | Backed by |
|------|--------|-----------|
| `Read` | `path` (req), `offset` (int=0), `limit` (int=0) | `open` + `read` syscalls |
| `Head` | `path` (req), `lines` (int=10) | `open` + line-counting `read` |
| `LS` | `path` (req), `all` (bool) | fork+exec `/bin/ls -l[a]` |
| `Write` | `path` (req), `content` (req), `append` (bool) | `open(O_CREAT∣O_TRUNC∣O_APPEND)` + `write` |
| `Bash` | `command` (req), `timeout_secs` (int=0) | fork+exec `/bin/sh -c`, stdout+stderr merged |
| `WebFetch` | `url` (req) | `Library.HTTP.Get` (curl) |
| `Relmem` | `op` (req: query/where/callers/calls/symbols/index/focus/forget/drop/status/summary) + per-op args | Native AILang symbolic-memory engine |

Truncation: every tool caps output at 60KB and appends `\n[truncated]` so
the model knows. Silent truncation in the original draft was the source of
cryptic loops.

---

## Conversation history model

`History.ailang` is a ring of message JSON objects. Each entry is
`{role: ..., content: ...}` matching the API exactly.

Eviction: when count > MAX_MESSAGES (100), drop the oldest user/assistant
pair. **Special rule:** if the second message contains `tool_use` blocks,
drop **three** so the matching `tool_result` user message goes with it.
The API rejects requests where a `tool_use` lacks its paired `tool_result`,
so this pairing must be preserved across the eviction boundary.

Eviction prints a one-line warning. The user sees when context gets cut.

---

## TUI rendering model

Two-stage UX:

**Stage 1: cooked-mode bootstrap** (kernel handles input, plain stdout)
- Splash file scroll-in animation (loads `./splash.ans` if present)
- Auth-mode prompt (1 = subscription / 2 = API key)
- OAuth flow (if option 1) — browser launch + callback server
- API key fallback walkthrough if no key set
- Per-tool service launches print `[ipcd] registered X` lines

**Stage 2: raw-mode chat** (we own the screen via `Library.TUI`)
- `UI.Init()` grabs the terminal in raw mode (TUI alt-screen + non-canonical input)
- `UI.SessionHeader()` paints the small mascot with version/model/cwd
- Bottom-pinned 4-row prompt area: top rule / `> ` input / bottom rule / hint
- Chat region scrolls naturally above the prompt
- `UI.ReadLine()` handles input character-by-character via `TUI_GetKey`
  (handles backspace, ESC=quit, prints to body row)
- `UI.ChatPrint(s)` streams text into chat region with column tracking so
  successive `text_delta` events don't overwrite each other

The transition between stages happens once per session (after auth).
`UI.Shutdown()` restores the terminal on `/quit`.

---

## Splash art loader

`UI.SplashFile(path, delay_ms)` reads any ANSI-art file from disk, prints
each line centered with `delay_ms` between rows. Designed to be called
in cooked mode (before `UI.Init()`) so the kernel scrolls the terminal
naturally.

Generate art with chafa from any image:
```bash
chafa --format=symbols --symbols=block --colors=truecolor --size=80 splash.png > splash.ans
```

Skip the splash entirely with `CC_NO_SPLASH=1`.

---

## What we deliberately don't have (Phase 1)

- **MCP** — would require ~1500 LOC of stdio/SSE/HTTP transport. Add when
  someone asks.
- **Hooks** — single-user binary, no need for PreToolUse/PostToolUse.
- **Slash commands / skills / plugins** — only `/help`, `/clear`, `/quit`
  for now. No marketplace surface.
- **Settings hierarchy** — no global/project/local config layering. Env
  vars + `~/.claudecode/oauth_config.json` only.
- **Subagent infrastructure** — we don't spawn other agents.
- **Permission system** — single user on their own box, trust is implicit.
- **Native TLS** — would be months of work. Curl works today; the
  `Library.HTTP` API hides curl as an implementation detail so a future
  TLS rewrite is a drop-in.
- **Windowed mode** — Phase 4. Would render via `Library.ShmCanvas` to
  the AILang display server, same pattern as Chrome/VSCode IPC apps,
  using `Library.VIF` to rasterize TVG art for real PNG-quality graphics.
  See task #30 in `~/.claude/plans/`.

## Known issues / workarounds

- **Library.JSON XSHash bucket collision**: reading the key `"name"` back
  from a populated object can return `"index"` when the object also holds
  an `"input"` sub-object. Workaround: `Anthropic.ailang` keeps a parallel
  string-pointer array (`AnthState.tool_names[]` / `.tool_ids[]`) for
  tool name/id; ClaudeCode dispatch reads from there via
  `Anthropic.GetToolName(idx)` / `Anthropic.GetToolId(idx)`. JSON object
  is still built for history purposes, just not trusted for that one
  key. File a bug against Library.JSON when time permits.

- **OAuth subscription path**: gated on Anthropic providing third-party
  guidance. Token endpoint at `https://platform.claude.com/v1/oauth/token`
  consistently returns `rate_limit_error` for codes obtained from
  `https://claude.ai/oauth/authorize` using the official CLI's static
  `client_id`. Likely we need a different audience claim or session API
  flow. Issue #54184 on `anthropics/claude-code` filed, awaiting reply.

- **WSL terminal width**: the prompt rule used to span the entire
  terminal width on wide terminals (191 cols). Now capped at 100 cells
  via `UILayout.max_bar`. Any chafa-rendered splash should fit within
  the same cap or it'll wrap.

---

## Build & run

```bash
cd /mnt/c/Users/Sean/Documents/AILangSH

# Build the entry binary
./ailang.x Applications/ClaudeCode/ClaudeCode.ailang ClaudeCode.x

# Build all six tools
for t in read head ls write bash webfetch; do
  ./ailang.x Applications/ClaudeCode/cc_tools/cc_${t}_ipc.ailang cc_${t}_ipc.x
done

# Start each tool service in the background
for t in cc_read_ipc cc_head_ipc cc_ls_ipc cc_write_ipc cc_bash_ipc cc_webfetch_ipc; do
  ./$t.x &
done

# Set the API key (in WSL shell)
export ANTHROPIC_API_KEY=sk-ant-...

# Run
./ClaudeCode.x
```

Output:
```
[ipcd] registered Read
[ipcd] registered Head
[ipcd] registered LS
[ipcd] registered Write
[ipcd] registered Bash
[ipcd] registered WebFetch
Claude Code (AILang Native) — Phase 1
Type your message. /quit to exit.

>
```

---

## Verification (smoke tests passed)

- `cc_read_ipc` returns `/etc/hostname` content correctly.
- `cc_head_ipc` returns 3 lines of `/etc/passwd` when `lines=3` (caught a
  defaults bug — `UtilArgs.UA_ApplyDefaults` used GetString to detect
  presence, which always returned 0 for int fields; fixed to use GetType).
- `cc_bash_ipc` returns `exit=3 / hello / err` for
  `echo hello && echo err >&2; exit 3`.
- `ClaudeCode` connects to all six services, fetches each schema, lists
  registrations cleanly.

What's not yet smoke-tested (requires real API key): live streaming, real
tool dispatch in a real conversation. End-to-end test plan in `Verification`
section of `~/.claude/plans/if-we-need-generic-lucky-hellman.md`.

---

## Sizes

| Binary | Size |
|--------|------|
| ClaudeCode.x | ~126 KB |
| cc_read_ipc.x | ~109 KB |
| cc_head_ipc.x | ~109 KB |
| cc_ls_ipc.x | ~109 KB |
| cc_write_ipc.x | ~109 KB |
| cc_bash_ipc.x | ~113 KB |
| cc_webfetch_ipc.x | ~117 KB |
| **Total** | **~792 KB** |

For comparison: shipped TS Claude Code is on the order of 50 MB before
node_modules and 200 MB+ after. We're roughly 1/250th the size.

---

## Phase 2 candidates (not committed)

- **`cc_grep_ipc`** — refit existing `Applications/grep_ipc.ailang` (which
  is currently a display-window app) into a tool service using the
  existing 1303 LOC `grep_util` core.
- **`cc_relmem_ipc`** — wrap a sibling AILang relmem implementation when
  it lands. Same pattern as the rest of the cc_tools.
- **`cc_glob_ipc`** — fork `find_util`, give the model recursive glob.
- **Native TLS** — only if curl ever becomes a real bottleneck.
- **Tool isolation** — currently each cc_tool is a long-lived process; no
  per-call sandbox. For untrusted commands, fork-per-call with rlimits
  would be the move.
- **Backporting all 56 sysutils to UtilArgs** — separate project; the
  schema lib is ready.

---

*Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.*
