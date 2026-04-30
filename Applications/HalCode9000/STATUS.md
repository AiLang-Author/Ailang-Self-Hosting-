# HalCode9000 — Design & Roadmap

## What This Is

Multi-provider fork of ClaudeCode. The goal: one terminal agent that can route to
any LLM backend (Anthropic, OpenAI-compatible APIs, Google, local models) via a
JSON config + compiled backend system. No FFI, no dynamic loading — clean AILang.

Forked from ClaudeCode on 2026-04-30. Currently identical minus socket namespace
(`@halcode/` instead of `@claudecode/`) and `backends/` directory structure.

## Architecture (Decided)

```
HalCode9000.ailang          — entry, startup screen, provider menu, agent loop
backends/Anthropic.ailang   — existing Anthropic wire format (first backend)
backends/OpenAI.ailang      — OpenAI + all compatible clones (TODO)
providers/*.json            — one file per provider: URL, auth, models, pricing (TODO)
cc_tools/                   — same 7 tools as ClaudeCode, own socket namespace
```

**Internal message format**: OpenAI schema (lingua franca). Each backend
translates to/from its own wire format. Anthropic backend converts TO Anthropic
format on outbound. OpenAI backend passes through as-is.

**Provider config JSON shape** (planned):
```json
{
  "name": "Groq",
  "backend": "openai",
  "base_url": "https://api.groq.com/openai/v1",
  "auth": "bearer",
  "models": [
    { "id": "llama-3.3-70b-versatile", "display": "Llama 3.3 70B",
      "input_per_1m": 0.59, "output_per_1m": 0.79 }
  ],
  "default_model": "llama-3.3-70b-versatile"
}
```

## Startup Screen (Planned)

Replace the current boot sequence with:
1. HAL 9000 text-art slow scroll (red on black, line by line)
2. Provider selection menu (populated from `providers/*.json`)
3. API key prompt if not cached
4. Drop into chat — same agent loop as ClaudeCode

## Multi-Agent Tool (Next Big Thing)

The biggest gap. Planned as a new cc_tool `cc_agent_ipc` that:
- Accepts a task description + tool subset
- Spins up a sub-agent conversation (separate history, same backend pool)
- Returns the result as a tool response to the parent agent
- Parent can fan out N sub-agents in parallel (each gets its own socket call)

This is the foundation for: parallel file analysis, multi-pass review, code gen + test.

## Roadmap (Parked, Priority Order)

1. **Multi-agent tool** (`cc_agent_ipc.ailang`) — fan-out sub-agents as tools
2. **Startup screen** — HAL text art + provider menu (UI.ailang rewrite)
3. **`backends/OpenAI.ailang`** — second backend, covers 90% of the ecosystem
4. **`providers/*.json`** — config files for Anthropic, OpenAI, Groq, Ollama, etc.
5. **Token cost display** — per-turn cost from usage field × provider pricing
6. **Wire backend selection** into agent loop
7. **Per-turn cost display** in status area

## Backport From ClaudeCode

When ClaudeCode gets a fix, check if HalCode9000 needs it too.
Especially anything in: `cc_tools/`, `Library.Socket`, `Library.TUI`, `Library.SSE`.

## Build

```
bash build.sh --hal           # rebuild HalCode9000 only
bash build.sh                 # rebuild both
cd Applications/HalCode9000 && ./HalCode9000.x
```
