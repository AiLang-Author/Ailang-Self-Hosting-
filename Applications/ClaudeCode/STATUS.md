# ClaudeCode — Status & Parking Notes

## What This Is

The working, shipped native AILang Claude Code client. Anthropic API only, single-provider.
This is the **stable reference** — production-quality, don't break it.

## Current State (2026-04-30)

Fully working end-to-end:
- HAL Code 9000 branding, animated mascot, HAL quotes
- Streaming SSE against Anthropic Messages API
- 7 tools: Read, Head, LS, Write, Bash, WebFetch, Relmem
- OAuth stub (blocked on Anthropic issue #54184 — `/v1/messages` Bearer support)
- Alt-screen removed → terminal scrollback works (main screen, unlimited history)
- `find /` / `find /mnt` blocked at tool layer (not just system prompt)
- IPC framing: Relmem output capped at 50KB; socket sanity limit raised to 1MB

## Known Pending Issues

- **Scrollback fix needs a live test** — alt-screen removed but not yet visually verified
- Back-buffer artifacts on shutdown (deferred)
- `find /` system prompt instructions still too weak; tool-layer block is the real guard
- Issue #28: Library.JSON hash collision (`name` key returns `index`) — intermittent
- Issue #33: word-level smoothing in Anthropic_OnTextDelta
- Issue #38: History byte-cap eviction (MAX_MESSAGES=20)

## Backport Policy

Any bug fix here that also applies to HalCode9000 should be ported over.
Especially: cc_tools fixes, Library.Socket, Library.TUI, Library.SSE, Library.HTTP.

Key shared infrastructure (always keep in sync):
- `cc_tools/` — all 7 tools; cc_relmem_ipc is the most complex
- `Library.Socket` — IPC framing, sanity limits
- `Library.TUI` — raw mode, screen handling, alt-screen flag

## Build

```
bash build.sh --claude        # rebuild ClaudeCode only
bash build.sh                 # rebuild both ClaudeCode + HalCode9000
cd Applications/ClaudeCode && ./ClaudeCode.x
```
