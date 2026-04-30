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

1. Schema migration — create `hc_*` tables in existing Postgres instance
2. `relmem op=sync` — write to `hc_files` + `hc_symbols` alongside JSON update
3. `cc_pgmem_ipc` — new tool binary, FTS queries first (`op=sym_search`, `op=park`, `op=pickup`, `op=search`)
4. `op=compact` — ACID compaction
5. `op=session_start/end` — session lifecycle
6. Wire into HalCode9000 agent loop — auto-load persistent on start, auto-park decisions
7. Wire into cc_agent_ipc when that tool exists — sub-agents inherit session parent
8. pgvector — only if FTS search quality proves insufficient for a specific use case

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
