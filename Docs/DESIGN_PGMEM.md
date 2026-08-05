# cc_pgmem — PostgreSQL Memory & Context Tool Design

## What This Solves

- Replaces CLAUDE.md and relmem's flat JSON with a queryable, project-scoped
  knowledge store in Postgres
- Gives agents (main loop + sub-agents) a structured place to park and pickup
  working context without ballooning the chat history
- Token reduction: context window = system prompt + persistent summary + current
  turn. Everything else is on-demand from Postgres
- Enables the multi-agent workflow: sub-agents write findings as rows, parent
  reads rows — no replayed conversation, no massive context pass-through

## Schema

```sql
-- Top-level namespace
CREATE TABLE hc_projects (
    id   SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,   -- "HalCode9000", "AILangSH", etc.
    path TEXT NOT NULL
);

-- relmem feeds these two
CREATE TABLE hc_files (
    id         SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES hc_projects(id),
    path       TEXT NOT NULL,
    rel_path   TEXT NOT NULL,
    lang       TEXT,
    hash       TEXT,             -- sha256; skip re-index if unchanged
    indexed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, path)
);

CREATE TABLE hc_symbols (
    id         SERIAL PRIMARY KEY,
    file_id    INTEGER REFERENCES hc_files(id),
    project_id INTEGER REFERENCES hc_projects(id),
    name       TEXT NOT NULL,
    kind       TEXT,             -- 'function','type','variable','import'
    line_start INTEGER,
    signature  TEXT,
    body       TEXT,             -- full source of the symbol
    tsv        TSVECTOR GENERATED ALWAYS AS (
                   to_tsvector('english',
                       coalesce(name,'') || ' ' || coalesce(body,''))
               ) STORED
);
CREATE INDEX hc_symbols_tsv ON hc_symbols USING GIN(tsv);
-- pgvector: only add if FTS proves insufficient. One extra column:
--   embedding VECTOR(768)
-- and one extra index:
--   CREATE INDEX ON hc_symbols USING ivfflat(embedding vector_cosine_ops)
-- Don't build it until there's a concrete reason FTS can't do the job.

-- Agent sessions (main loop + every sub-agent)
CREATE TABLE hc_sessions (
    id         TEXT PRIMARY KEY,   -- UUID
    project_id INTEGER REFERENCES hc_projects(id),
    parent_id  TEXT REFERENCES hc_sessions(id),
    role       TEXT,               -- 'main', 'sub:reviewer', 'sub:codegen'
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at   TIMESTAMPTZ,
    status     TEXT DEFAULT 'active'  -- 'active','complete','failed','compacted'
);

-- Working context — the replacement for CLAUDE.md and inter-agent messaging
CREATE TABLE hc_context (
    id         SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES hc_projects(id),
    session_id TEXT REFERENCES hc_sessions(id),
    agent_id   TEXT,
    parent_id  INTEGER REFERENCES hc_context(id),   -- tree structure
    key        TEXT,               -- human label, e.g. "auth-decision"
    kind       TEXT,               -- see kinds below
    content    TEXT,
    scope      TEXT DEFAULT 'session', -- 'session' | 'project' | 'persistent'
    status     TEXT DEFAULT 'active',  -- 'active' | 'inactive' | 'archived'
    archived_by INTEGER REFERENCES hc_context(id),  -- points to the compaction row
    tsv        TSVECTOR GENERATED ALWAYS AS (
                   to_tsvector('english',
                       coalesce(key,'') || ' ' || coalesce(content,''))
               ) STORED,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ         -- session-scoped nodes auto-expire
);
CREATE INDEX hc_context_tsv     ON hc_context USING GIN(tsv);
CREATE INDEX hc_context_lookup  ON hc_context(project_id, scope, kind, status);
```

### Context kinds

| kind        | meaning |
|-------------|---------|
| `decision`  | architectural or design choice made |
| `finding`   | something discovered (bug, pattern, insight) |
| `todo`      | work item, may have a parent plan |
| `plan`      | work plan, contains todos as children |
| `summary`   | compacted summary of a completed session or phase |
| `note`      | free-form, no lifecycle expectations |
| `handoff`   | explicit message from sub-agent to parent |

### Scope

| scope        | meaning |
|--------------|---------|
| `session`    | only relevant for this run; auto-expires when session ends |
| `project`    | relevant across sessions but may become stale (compactable) |
| `persistent` | long-lived project knowledge; only retired by explicit compaction |

---

## Memory Compaction via ACID Transactions

Stale items are never hard-deleted — they're retired with a transaction that:

1. Writes a `summary` row capturing what was superseded and why
2. Sets `status = 'inactive'` on all superseded rows in the same transaction
3. Links superseded rows back to the summary via `archived_by`

Because it's ACID, the summary and the retirements are atomic — you never have a
state where rows are marked inactive but no summary exists explaining why.

```sql
-- Compact a work plan once it's done
BEGIN;

-- Write the archive summary
INSERT INTO hc_context (project_id, session_id, key, kind, scope, content)
VALUES ($proj, $sess, 'phase-1-complete', 'summary', 'persistent',
        'Phase 1 (tool bootstrap) complete as of 2026-04-30. All 7 tools
         operational. Key decisions: curl-backed HTTP, abstract Unix sockets,
         50KB tool output cap. See commit aad6066b.')
RETURNING id INTO $summary_id;

-- Retire the now-stale plan and its todos
UPDATE hc_context
   SET status = 'inactive', archived_by = $summary_id
 WHERE project_id = $proj
   AND key IN ('phase-1-plan', 'phase-1-todo-http', 'phase-1-todo-sse',
               'phase-1-todo-tools')
   AND status = 'active';

COMMIT;
```

Queries always filter `status = 'active'` so compacted rows disappear from
normal use. They're still there for audit/archaeology — just invisible to the
agent by default.

---

## Tool API — cc_pgmem_ipc

```
// Code index (replaces relmem FTS path)
op=sym_search   query=<text>  [kind=function]  [project=...]
op=sym_get      name=<exact>  [project=...]
op=sym_list     file=<path>

// Context — park
op=park         key=<label>   kind=<...>   content=<text>
                [scope=session|project|persistent]
                [parent_key=<key>]
                [session_id=<id>]

// Context — retrieve
op=pickup       key=<label>   [session_id=<id>]
op=search       query=<text>  [kind=...]  [scope=...]  [session_id=...]
op=tree         [session_id=<id>]  [scope=project]

// Context — compact (atomic)
op=compact      keys=<comma-list>   summary=<text>   kind=summary
                [scope=persistent]

// Session lifecycle
op=session_start  role=<main|sub:...>  [parent_id=<id>]   → session_id
op=session_end    session_id=<id>      [auto_compact=1]

// relmem sync — push file/symbol index into hc_files + hc_symbols
op=sync         path=<dir>  [project=<name>]
```

---

## Multi-Agent Wiring

```
Main agent:
  pgmem.session_start(role="main")  → S1

  pgmem.search("what is the current state of HalCode9000", scope="persistent")
  → gets all persistent context compactly; no CLAUDE.md needed

  pgmem.park(key="task-scope", kind="plan", scope="session",
             content="fix scroll region + add OpenAI backend")

  [spawns sub-agent via cc_agent_ipc]
    Sub-agent gets session_parent=S1, role="sub:scroll-fix"
    pgmem.session_start(role="sub:scroll-fix", parent=S1) → S2
    pgmem.sym_search("UI_ScrollChatUp")                   ← real code
    pgmem.pickup("task-scope", session_id=S1)             ← parent's plan

    pgmem.park(key="scroll-root-cause", kind="finding", scope="project",
               content="ESC[r after scroll region resets to full screen.
                        Line 349, Library.TUI. Fix: don't reset scroll region
                        after each scroll, or use main screen.")
    pgmem.session_end(S2)

  Main agent:
    pgmem.search("scroll fix finding", scope="project")  ← compact result
    [applies the fix, never saw S2's full conversation]

  At end of session:
    pgmem.compact(keys=["task-scope"], summary="scroll fix shipped, commit abc123")
    pgmem.session_end(S1)
```

---

## Replacing CLAUDE.md

At project init (or on first run):
```
pgmem.park(key="project-init", kind="summary", scope="persistent",
           content="HalCode9000: multi-provider LLM agent in native AILang.
                    Architecture: JSON config + compiled backends.
                    Internal message format: OpenAI schema.
                    cc_tools use @halcode/ socket namespace.
                    See commit aad6066b for fork point from ClaudeCode.")
```

Any future session starts with:
```
pgmem.tree(scope="persistent")  → compact structured summary of the whole project
```

No file drift. No stale decisions. Timestamps on every row.

---

## Olympus Integration (Future)

The `hc_context` table is a natural feed into the Olympus repo mana/commit system:

- Every `scope=persistent` decision row maps to a commit annotation
- Every `op=compact` transaction maps to a milestone boundary
- The `hc_sessions` parent-child tree maps to a task/subtask hierarchy

When that integration is ready: a webhook or trigger on `hc_context` inserts
into the Olympus side. No changes to cc_pgmem_ipc itself — Postgres handles
the fan-out.

---

## Implementation Order (When Ready)

1. Schema migration — create `hc_*` tables in existing Postgres instance (`hc_projects`, `hc_files`, `hc_symbols`, `hc_sessions`, `hc_context`, `hc_tasks`)
2. `relmem op=sync` — write to `hc_files` + `hc_symbols` alongside JSON update
3. `cc_pgmem_ipc` — new tool binary, FTS queries first (`op=sym_search`, `op=park`, `op=pickup`, `op=search`)
4. `op=compact` — ACID compaction
5. `op=session_start/end` — session lifecycle
6. `op=task_create/start/end/list/get` — task tracking + token recording
7. Wire into HalCode9000 agent loop — auto-load persistent on start, auto-park decisions, record token usage per turn
8. Load provider capability index at startup — read `providers/*.json` tier/strengths into memory for routing decisions
9. Wire into cc_agent_ipc when that tool exists — sub-agents inherit session parent, tasks record assigned_to + token counts
10. pgvector — only if FTS search quality proves insufficient for a specific use case

---

## Capability/Cost Routing and Task Tracking

### Design Principle

The orchestrator (main agent) always runs on the flagship model. It decomposes
work, classifies effort, and routes subtasks to the cheapest model that can
handle them. Sub-agents execute, park findings in `hc_context`, and return.
The orchestrator never downgrades itself — cheap models are workers, not peers.

### Provider JSON Extension

Each `providers/*.json` gains two fields:

```json
{
  "name": "Groq",
  "backend": "openai",
  "tier": 3,
  "strengths": ["speed", "json", "summarization", "rename", "simple-refactor"],
  "weaknesses": ["multi-file-reasoning", "long-context", "architecture"],
  "models": [...]
}
```

`tier`: 1 = flagship (Claude Opus, GPT-4o, Gemini Ultra), 2 = mid (Sonnet,
GPT-4o-mini), 3 = cheap/fast (Haiku, Groq Llama, local Ollama). Lower is
more capable. Router picks the highest-tier (cheapest) model that satisfies
`min_tier` and has the required strength.

### `hc_tasks` Table

```sql
CREATE TABLE hc_tasks (
    id           SERIAL PRIMARY KEY,
    project_id   INTEGER REFERENCES hc_projects(id),
    session_id   TEXT    REFERENCES hc_sessions(id),
    parent_id    INTEGER REFERENCES hc_tasks(id),   -- sub-task tree
    title        TEXT NOT NULL,
    kind         TEXT,                               -- 'plan'|'refactor'|'codegen'|'review'|'search'|'summarize'
    effort       TEXT,                               -- 'low'|'medium'|'high' (set by orchestrator)
    min_tier     INTEGER DEFAULT 1,                  -- minimum model tier required (orchestrator sets this)
    assigned_to  TEXT,                               -- model ID actually used, e.g. "llama-3.3-70b-versatile"
    provider     TEXT,                               -- provider name, e.g. "Groq"
    status       TEXT DEFAULT 'pending',             -- 'pending'|'running'|'complete'|'failed'
    result_key   TEXT,                               -- hc_context key where result was parked
    input_tokens  INTEGER DEFAULT 0,                 -- tokens sent to model for this task
    output_tokens INTEGER DEFAULT 0,                 -- tokens received from model
    cost_usd      NUMERIC(10,6),                     -- computed from provider pricing at task end
    started_at   TIMESTAMPTZ,
    ended_at     TIMESTAMPTZ,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX hc_tasks_session ON hc_tasks(session_id, status);
CREATE INDEX hc_tasks_parent  ON hc_tasks(parent_id);
```

### Routing Algorithm

```
orchestrator decomposes plan into tasks:
  for each task:
    classify: kind, effort → min_tier
    router: SELECT provider, model WHERE tier >= min_tier
              AND strengths @> ARRAY[required_strength]
              ORDER BY tier DESC, input_per_1m DESC   -- cheapest first
              LIMIT 1
    if no match: fall back to tier=1 (flagship)
    pgmem.task_create(title, kind, effort, min_tier, assigned_to=model)
    cc_agent_ipc(task_id, model, session_parent)
    → sub-agent runs, parks result at result_key, records tokens
```

The orchestrator never sees the sub-agent's conversation. It reads the parked
result from `hc_context` via `pgmem.pickup(result_key)`.

### cc_pgmem Tool API — Task Operations

```
op=task_create   title=<...>  kind=<...>  effort=<low|medium|high>  [min_tier=1]
                 [parent_id=<id>]  [session_id=<id>]
                 → task_id

op=task_start    task_id=<id>  assigned_to=<model_id>  provider=<name>
op=task_end      task_id=<id>  status=<complete|failed>  [result_key=<key>]
                 input_tokens=<n>  output_tokens=<n>  cost_usd=<f>

op=task_list     [session_id=<id>]  [status=pending]  [parent_id=<id>]
op=task_get      task_id=<id>
```

---

## Token Consumption Tracking

Every model call records token counts in `hc_tasks`. The data is always in
Postgres — no in-memory aggregation needed; any query runs against the live
table.

### Useful Queries

```sql
-- Per-model totals for the current session
SELECT assigned_to, provider,
       SUM(input_tokens) AS total_in,
       SUM(output_tokens) AS total_out,
       SUM(cost_usd) AS total_cost_usd
  FROM hc_tasks
 WHERE session_id = $sess AND status = 'complete'
 GROUP BY assigned_to, provider
 ORDER BY total_cost_usd DESC;

-- Per-project totals across all sessions (cost audit)
SELECT provider, assigned_to,
       SUM(input_tokens) AS total_in,
       SUM(output_tokens) AS total_out,
       SUM(cost_usd) AS total_cost_usd,
       COUNT(*) AS task_count
  FROM hc_tasks t
  JOIN hc_sessions s ON t.session_id = s.id
 WHERE s.project_id = $proj AND t.status = 'complete'
 GROUP BY provider, assigned_to
 ORDER BY total_cost_usd DESC;

-- What's expensive to send (input tokens by task kind)
SELECT kind, AVG(input_tokens) AS avg_in, AVG(output_tokens) AS avg_out,
       COUNT(*) AS n
  FROM hc_tasks
 WHERE status = 'complete'
 GROUP BY kind
 ORDER BY avg_in DESC;
```

The third query is the "what does and doesn't need sending" diagnostic. High
input tokens on low-effort tasks (e.g. `kind=rename`) means the context being
passed to the sub-agent is too large — trim the pickup scope or reduce the
history passed to the worker.

### Token Recording in the Agent Loop

When HalCode9000 finishes a streaming turn, the `usage` field in the final
`message_delta` event contains `input_tokens` and `output_tokens`. The agent
loop writes these to the active `hc_tasks` row via `op=task_end` before
parking the result. If no task row exists (bare conversation turn, not a
spawned sub-task), a session-level aggregate row is upserted instead so no
tokens are lost.

---

## Vector Search Decision

**Don't build it yet.** Full-text search (tsvector/GIN) handles:
- Symbol lookup by name/keyword
- Context search by key and content words
- "Find all decisions about X"

pgvector adds semantic similarity — useful when you want "code that does the
same thing as X even if the words are different." That's a real need but it
only shows up after the FTS layer is working and you hit a concrete case where
keyword search fails. Add the column and index then, not now.
