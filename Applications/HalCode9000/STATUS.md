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

Planned as a new cc_tool `cc_agent_ipc` that:
- Accepts a task description + tool subset + session parent ID
- Spins up a sub-agent conversation (separate history, same backend pool)
- Returns the result as a tool response to the parent agent
- Parent can fan out N sub-agents in parallel (each gets its own socket call)

**Prerequisite: cc_pgmem must exist first.** Sub-agents need somewhere to park
findings that the parent can read without replaying the full sub-conversation.
That's what `hc_context` provides. Build pgmem first, then cc_agent_ipc on top.

## cc_pgmem — Postgres Memory Tool

Full design in `DESIGN_PGMEM.md`. Summary:

- **relmem → Postgres**: `op=sync` writes symbols/files into `hc_files` +
  `hc_symbols` (FTS via tsvector/GIN). Replaces the flat JSON index.
- **Working context**: `op=park` / `op=pickup` / `op=search` against `hc_context`.
  Agents store findings, decisions, todos as structured rows.
- **Replaces CLAUDE.md**: persistent-scope rows ARE the project knowledge.
  Any session starts with `op=tree(scope=persistent)`.
- **ACID compaction**: stale work plans are retired atomically — a summary row
  is written and old rows are marked inactive in the same transaction.
  Nothing is deleted; archaeology is always possible.
- **Olympus tie-in (future)**: persistent decisions + compaction boundaries map
  naturally onto Olympus commit/mana annotations. No pgmem changes needed —
  Postgres trigger or webhook handles the fan-out when that integration exists.
- **pgvector**: skip unless FTS proves concretely insufficient. tsvector handles
  symbol lookup and context search well. Add the column + index only when there's
  a specific failing query that vector search would fix.

## Roadmap (Parked, Priority Order)

1. **cc_pgmem** (`cc_pgmem_ipc.ailang`) — Postgres memory tool, prerequisite for everything else
   - Schema migration (`hc_projects`, `hc_files`, `hc_symbols`, `hc_sessions`, `hc_context`)
   - `relmem op=sync` writes into `hc_files` + `hc_symbols`
   - `op=park/pickup/search/compact/session_start/session_end`
2. **Multi-agent tool** (`cc_agent_ipc.ailang`) — sub-agents as tools, built on cc_pgmem
3. **Startup screen** — HAL text art slow-scroll + provider selection menu
4. **`backends/OpenAI.ailang`** — covers OpenAI + all compatible clones
5. **`providers/*.json`** — Anthropic, OpenAI, Groq, Ollama, etc.
6. **Token cost display** — per-turn from usage field × provider pricing
7. **Wire backend selection** into agent loop

## Backport From ClaudeCode

When ClaudeCode gets a fix, check if HalCode9000 needs it too.
Especially anything in: `cc_tools/`, `Library.Socket`, `Library.TUI`, `Library.SSE`.

## Build

```
bash build.sh --hal           # rebuild HalCode9000 only
bash build.sh                 # rebuild both
cd Applications/HalCode9000 && ./HalCode9000.x
```
