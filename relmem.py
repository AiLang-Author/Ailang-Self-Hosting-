#!/usr/bin/env python3
"""
relmem — symbolic memory tool for Claude Code sessions.

Stores a compressed symbolic representation of project files across
sessions so keyword lookups and cross-file navigation don't require
re-reading source every time. Derived from (and simplified from)
Documents/A_Brain_m/RelMem.py — shaped for CLI invocation rather than
a REPL, with AiLang/shell/markdown-aware parsers added.

Storage: ~/.claude/relmem/index.json  (JSON, diffable, portable)
Tool:    Librarys-adjacent in the AiLangSH tree — visible,
         collaboration-friendly, no hidden-state install.

Commands (all non-interactive, parseable output):
  index  <dir> [--ext py,ailang,sh,md]    Walk + parse into the index.
                                          Incremental by mtime.
  summary    [--project <path>]           Project-wide compressed view.
  query    <kw>... [--limit N]            Search across ALL indexed projects.
  focus    <file> <symbol>                Symbols matching a substring.
  symbols  <file>                         All symbols in one file.
  where    <symbol>                       Find where a symbol is defined.
  forget   <file>                         Drop a single file from the index.
  drop     [--project <path>]             Drop entire project index.
  status                                  Index size + projects.

Design choices:
  * JSON over pickle — diffable, portable, survives Python upgrades.
  * Per-project namespacing keyed by git toplevel (fallback: dir).
  * Incremental indexing via mtime — re-running `index` is cheap.
  * AiLang parser knows Function./SubRoutine./FixedPool./LibraryImport.
  * Plain-text output by default — every line is easy to parse downstream.

Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
"""
import argparse
import ast
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

STORE_DIR  = Path.home() / ".claude" / "relmem"
INDEX_PATH = STORE_DIR / "index.json"

# Bumped when the parsers change. Files whose cached `pv` (parser version)
# differs get re-parsed on next index, even if their mtime hasn't moved.
# That way an upgrade doesn't silently serve stale nodes/edges.
PARSER_VERSION = 2

# AiLang builtins / control-flow keywords. Calls to these aren't
# interesting as graph edges — every function would "call" IfCondition.
AILANG_BUILTINS = frozenset({
    # arithmetic / logic
    "Add", "Subtract", "Multiply", "Divide", "Modulo", "Power", "Negate",
    "Increment", "Decrement", "AbsoluteValue", "SquareRoot", "Minimum", "Maximum",
    "And", "Or", "Not", "Xor",
    "BitwiseAnd", "BitwiseOr", "BitwiseXor", "BitwiseNot", "LeftShift", "RightShift",
    # comparison
    "EqualTo", "NotEqual", "GreaterThan", "LessThan", "GreaterEqual", "LessEqual",
    # control flow
    "IfCondition", "ThenBlock", "ElseBlock", "WhileLoop", "ForEvery",
    "BreakLoop", "ContinueLoop", "ReturnValue", "Branch", "Case", "Default",
    "RunTask", "HaltProgram", "TryBlock", "CatchError", "FinallyBlock",
    # memory / data
    "Allocate", "Deallocate", "GetByte", "SetByte", "Dereference", "StoreValue",
    "AddressOf", "SizeOf", "MemoryCopy", "MemorySet",
    # i/o
    "PrintMessage", "PrintNumber", "PrintChar", "PrintString",
    "ReadInput", "ReadInputNumber", "SystemCall",
    # arrays
    "ArrayCreate", "ArrayDestroy", "ArrayGet", "ArraySet", "ArraySize",
    # strings
    "StringLength", "StringCompare", "StringConcat", "StringEquals",
    "StringSubstring", "StringCharAt", "NumberToString", "StringToInt",
    "StringToNumber",
    # debug
    "DebugAssert", "DebugTrace", "DebugBreak", "DebugMemory", "DebugPerf",
    "DebugInspect",
    # atomic
    "AtomicCompareSwap", "AtomicAdd", "AtomicLoad", "AtomicStore",
})

# Dirs we never descend into — junk / generated / vendor.
SKIP_PARTS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".claude", ".idea", ".vscode", "dist", "build",
    "Backups",  # project-specific, but universally low-signal
}


# =============================================================================
# INDEX I/O  (JSON, atomic writes)
# =============================================================================

def _load_index() -> dict:
    if not INDEX_PATH.exists():
        return {"projects": {}}
    try:
        return json.loads(INDEX_PATH.read_text())
    except json.JSONDecodeError:
        # Corrupt index — start fresh rather than silently keep old state
        sys.stderr.write(f"warning: {INDEX_PATH} corrupt, starting fresh\n")
        return {"projects": {}}


def _save_index(data: dict) -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = INDEX_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    tmp.replace(INDEX_PATH)


def _project_root(path) -> Path:
    """Nearest ancestor with a .git; fallback to the given path."""
    p = Path(path).resolve()
    if p.is_file():
        p = p.parent
    cur = p
    while cur != cur.parent:
        if (cur / ".git").exists():
            return cur
        cur = cur.parent
    return p


# =============================================================================
# PARSERS
# Return: {node_id: {"tok": str, "cat": str, "kind": str, "line": int, "edges": list}}
# node_id is a stable lowercased key used for lookup; tok is the original name.
# =============================================================================

def _parse_python(content: str, path: str) -> dict:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return _parse_text(content, path)

    nodes: dict = {}
    def add(nid, tok, cat, kind="", line=0):
        if nid and nid not in nodes:
            nodes[nid] = {"tok": tok, "cat": cat, "kind": kind,
                          "line": line, "edges": []}

    # Two-pass: first collect definitions, then collect calls via a
    # NodeVisitor that tracks the enclosing function via a stack.
    class V(ast.NodeVisitor):
        def __init__(self):
            self.stack: list = []  # names of enclosing funcs, innermost last

        def visit_ClassDef(self, n):
            add(n.name.lower(), n.name, "class", "py", n.lineno)
            self.generic_visit(n)

        def _visit_func(self, n):
            add(n.name.lower(), n.name, "function", "py", n.lineno)
            self.stack.append(n.name.lower())
            self.generic_visit(n)
            self.stack.pop()

        visit_FunctionDef = _visit_func
        visit_AsyncFunctionDef = _visit_func

        def visit_Import(self, n):
            for a in n.names:
                add("import_" + a.name.lower(), a.name, "import", "py", n.lineno)

        def visit_ImportFrom(self, n):
            mod = n.module or ""
            if mod:
                add("import_" + mod.lower(), mod, "import", "py", n.lineno)

        def visit_Call(self, n):
            # Only record edges when we're inside a tracked function.
            if self.stack:
                caller = self.stack[-1]
                callee = _call_name(n.func)
                if callee and caller in nodes:
                    edge = [callee.lower(), "calls"]
                    if edge not in nodes[caller]["edges"]:
                        nodes[caller]["edges"].append(edge)
            self.generic_visit(n)

    V().visit(tree)
    return nodes


def _call_name(func_expr) -> str:
    """Best-effort extraction of a callable's display name from ast.Call.func.

    Handles plain Name, attribute chain (a.b.c → 'c'), and a few niche cases.
    Returns "" when we can't recover a stable name (e.g. lambdas, subscripts).
    """
    if isinstance(func_expr, ast.Name):
        return func_expr.id
    if isinstance(func_expr, ast.Attribute):
        return func_expr.attr
    return ""


# AiLang declaration keywords that introduce named entities.
_AILANG_FUNC_KWS = ("Function", "SubRoutine", "Combinator", "Lambda", "MacroBlock")
_AILANG_POOL_KWS = ("FixedPool", "DynamicPool", "TemporalPool", "NeuralPool",
                    "KernelPool", "ActorPool", "SecurityPool", "ConstrainedPool",
                    "FilePool", "LinkagePool", "SubPool")

_AILANG_FUNC_RE = re.compile(
    r"^(?:" + "|".join(_AILANG_FUNC_KWS) + r")\.([A-Za-z0-9_.]+)"
)
_AILANG_POOL_RE = re.compile(
    r"^(?:" + "|".join(_AILANG_POOL_KWS) + r")\.([A-Za-z0-9_.]+)"
)
_AILANG_IMPORT_RE = re.compile(r"^LibraryImport\.(\S+)")


_AILANG_CALL_RE = re.compile(r"\b([A-Z][A-Za-z0-9_.]*)\s*\(")


def _parse_ailang(content: str, path: str) -> dict:
    """Regex-based AiLang entity extractor + call-graph edges.

    Catches the user-visible declaration shapes:
       Function.X / SubRoutine.X / Combinator.X / Lambda.X / MacroBlock.X
       FixedPool.X (and other pool variants)
       LibraryImport.X.Y.Z

    Call edges are approximated by tracking current-function context via
    brace-depth relative to the declaration line, and recording any
    CapitalizedName(...) invocation that isn't in AILANG_BUILTINS. This
    misses lowercase-identifier calls and gets fooled by strings/comments
    containing '(' — documented approximation, not a proper parser.

    Block comments don't exist in AiLang (per memory note); only // line
    comments are stripped.
    """
    nodes: dict = {}
    def add(nid, tok, cat, line):
        if nid and nid not in nodes:
            nodes[nid] = {"tok": tok, "cat": cat, "kind": "ailang",
                          "line": line, "edges": []}

    # Caller-tracking state. When we see `Function.Foo` at brace-depth 0,
    # we set current_fn = "foo" and remember the entry depth (+1 after the
    # opening `{`). When depth drops back to entry, current_fn resets.
    current_fn: str | None = None
    entry_depth: int = -1
    depth: int = 0

    for i, line in enumerate(content.splitlines(), 1):
        raw = line
        s = raw.strip()
        if "//" in s:
            s = s[: s.index("//")].strip()

        # Declarations must be at brace-depth 0 to count as top-level.
        if depth == 0 and s:
            m = _AILANG_FUNC_RE.match(s)
            if m:
                name = m.group(1)
                add(name.lower(), name, "function", i)
                current_fn = name.lower()
            else:
                mp = _AILANG_POOL_RE.match(s)
                if mp:
                    add(mp.group(1).lower(), mp.group(1), "pool", i)
                else:
                    mi = _AILANG_IMPORT_RE.match(s)
                    if mi:
                        add("import_" + mi.group(1).lower(), mi.group(1), "import", i)

        # Look for calls in the current line (before updating depth) —
        # they belong to the function whose body this line is inside.
        if current_fn and s:
            for callee in _AILANG_CALL_RE.findall(s):
                # Strip trailing dotted path — 'X.Y.Z(' becomes 'Z'
                callee_short = callee.split(".")[-1]
                # Skip builtins and self-recursion noise
                if callee_short in AILANG_BUILTINS:
                    continue
                if callee_short == current_fn.split(".")[-1]:
                    # direct recursion — still record once
                    pass
                caller_node = nodes.get(current_fn)
                if caller_node is not None:
                    edge = [callee_short.lower(), "calls"]
                    if edge not in caller_node["edges"]:
                        caller_node["edges"].append(edge)

        # Update brace depth. Counts on the ORIGINAL line because comments
        # are rare and stripping them risks missing e.g. a `}` after code
        # and before a comment on the same line.
        opens  = raw.count("{")
        closes = raw.count("}")
        depth += opens - closes
        if depth < 0:
            depth = 0  # be forgiving on malformed input

        # Did we just see the opening `{` of a new function?
        if current_fn and entry_depth < 0 and depth > 0:
            entry_depth = 1
        # Did we just leave the current function's body?
        if current_fn and entry_depth >= 0 and depth < entry_depth:
            current_fn = None
            entry_depth = -1

    return nodes


def _parse_shell(content: str, path: str) -> dict:
    nodes: dict = {}
    for i, line in enumerate(content.splitlines(), 1):
        s = line.strip()
        m = re.match(r"^(\w+)\s*\(\)\s*\{", s)
        if m is None:
            m = re.match(r"^function\s+(\w+)", s)
        if m:
            name = m.group(1)
            nodes[name.lower()] = {"tok": name, "cat": "function",
                                   "kind": "shell", "line": i, "edges": []}
    return nodes


def _parse_markdown(content: str, path: str) -> dict:
    nodes: dict = {}
    for i, line in enumerate(content.splitlines(), 1):
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()[:80]
            nid = "h_" + re.sub(r"[^A-Za-z0-9]+", "_", title).lower()[:60]
            if nid and nid not in nodes:
                nodes[nid] = {"tok": title, "cat": f"h{level}",
                              "kind": "md", "line": i, "edges": []}
    return nodes


def _parse_text(content: str, path: str) -> dict:
    """Cheap fallback — capitalized tokens, capped. Not great, but beats nothing."""
    nodes: dict = {}
    for i, line in enumerate(content.splitlines(), 1):
        if i > 400:
            break
        for w in re.findall(r"\b[A-Z][A-Za-z0-9_]{2,}\b", line):
            nid = w.lower()
            if nid not in nodes:
                nodes[nid] = {"tok": w, "cat": "symbol",
                              "kind": "text", "line": i, "edges": []}
    return nodes


PARSERS = {
    ".py":     _parse_python,
    ".pyw":    _parse_python,
    ".ailang": _parse_ailang,
    ".sh":     _parse_shell,
    ".bash":   _parse_shell,
    ".md":     _parse_markdown,
}


def _parse_file(path: Path) -> dict:
    content = path.read_text(errors="ignore")
    return PARSERS.get(path.suffix, _parse_text)(content, str(path))


# =============================================================================
# COMMANDS
# =============================================================================

def cmd_index(args) -> int:
    root = Path(args.dir).resolve()
    if not root.exists():
        print(f"error: {root} does not exist", file=sys.stderr)
        return 1

    proot = _project_root(root)
    exts = {"." + e.lstrip(".") for e in args.ext.split(",")}

    idx  = _load_index()
    proj = idx["projects"].setdefault(str(proot), {"files": {}})

    new = updated = skipped = failed = 0
    for fp in root.rglob("*"):
        if not fp.is_file():
            continue
        if fp.suffix not in exts:
            continue
        if any(part in SKIP_PARTS for part in fp.parts):
            continue

        try:
            rel = str(fp.relative_to(proot))
        except ValueError:
            rel = str(fp)

        mtime = fp.stat().st_mtime
        existing = proj["files"].get(rel)
        # Skip only when BOTH mtime unchanged AND the cached parse is from
        # the current parser version — upgrading relmem shouldn't silently
        # keep serving stale nodes/edges.
        if existing \
           and abs(existing.get("mtime", -1) - mtime) < 1e-6 \
           and existing.get("pv") == PARSER_VERSION:
            skipped += 1
            continue

        try:
            nodes = _parse_file(fp)
        except Exception as e:
            failed += 1
            sys.stderr.write(f"parse failed: {rel}: {e}\n")
            continue

        proj["files"][rel] = {"mtime": mtime, "pv": PARSER_VERSION,
                              "nodes": nodes}
        if existing:
            updated += 1
        else:
            new += 1

    _save_index(idx)
    print(f"[{proot.name}] {new} new, {updated} updated, "
          f"{skipped} unchanged, {failed} failed  →  {len(proj['files'])} files total")
    return 0


def cmd_summary(args) -> int:
    idx = _load_index()
    if args.project:
        proot = Path(args.project).resolve()
    else:
        proot = _project_root(Path.cwd())

    proj = idx["projects"].get(str(proot))
    if not proj:
        print(f"[no index for {proot.name}]")
        return 1

    files = proj["files"]
    by_cat = defaultdict(set)
    for rel, f in files.items():
        for _, n in f["nodes"].items():
            by_cat[n["cat"]].add(n["tok"])

    total_symbols = sum(len(f["nodes"]) for f in files.values())
    print(f"[{proot.name}: {len(files)} files, {total_symbols} symbols]")
    for cat in sorted(by_cat):
        toks = sorted(by_cat[cat])
        if len(toks) <= 8:
            print(f"  {cat}({len(toks)}): {', '.join(toks)}")
        else:
            print(f"  {cat}({len(toks)}): {', '.join(toks[:6])}  ...+{len(toks)-6}")
    return 0


def cmd_query(args) -> int:
    idx = _load_index()
    keywords = [k.lower() for k in args.keyword]

    results: list = []
    for proot, proj in idx["projects"].items():
        for rel, f in proj["files"].items():
            score = 0
            matched: list = []
            for _, n in f["nodes"].items():
                tok_low = n["tok"].lower()
                cat_low = n["cat"].lower()
                for kw in keywords:
                    if kw in tok_low:
                        score += 2
                        matched.append(n["tok"])
                    elif kw in cat_low:
                        score += 1
            if score:
                results.append((score, proot, rel, list(dict.fromkeys(matched))))

    results.sort(key=lambda r: (-r[0], r[1], r[2]))
    if not results:
        print(f"[no matches for: {' '.join(args.keyword)}]")
        return 1

    for score, proot, rel, matched in results[: args.limit]:
        pname = Path(proot).name
        shown = ", ".join(matched[:5])
        extra = f"  +{len(matched)-5}" if len(matched) > 5 else ""
        print(f"  [{pname}] {rel}  (score {score})  {shown}{extra}")
    return 0


def cmd_focus(args) -> int:
    idx = _load_index()
    fp = Path(args.file).resolve()
    proot = _project_root(fp)
    proj = idx["projects"].get(str(proot))
    if not proj:
        print(f"[no index for {proot.name}]")
        return 1

    try:
        rel = str(fp.relative_to(proot))
    except ValueError:
        rel = str(fp)
    f = proj["files"].get(rel)
    if not f:
        print(f"[file not indexed: {rel}]")
        return 1

    needle = args.symbol.lower()
    hits = []
    for nid, n in f["nodes"].items():
        if needle in nid or needle in n["tok"].lower():
            hits.append((n["line"], n))
    if not hits:
        print(f"[no symbol in {rel} matches {args.symbol!r}]")
        return 1

    for line, n in sorted(hits):
        print(f"  {n['cat']:12s} {n['tok']}  :{line}")
    return 0


def cmd_symbols(args) -> int:
    idx = _load_index()
    fp = Path(args.file).resolve()
    proot = _project_root(fp)
    proj = idx["projects"].get(str(proot))
    if not proj:
        print(f"[no index]")
        return 1

    try:
        rel = str(fp.relative_to(proot))
    except ValueError:
        rel = str(fp)
    f = proj["files"].get(rel)
    if not f:
        print(f"[file not indexed: {rel}]")
        return 1

    by_cat: dict = defaultdict(list)
    for _, n in f["nodes"].items():
        by_cat[n["cat"]].append((n["line"], n["tok"]))

    print(f"[{rel}: {sum(len(v) for v in by_cat.values())} symbols]")
    for cat in sorted(by_cat):
        for line, tok in sorted(by_cat[cat]):
            print(f"  {cat:12s} {tok}  :{line}")
    return 0


def cmd_where(args) -> int:
    idx = _load_index()
    needle = args.symbol.lower()
    exact  = []
    partial = []
    for proot, proj in idx["projects"].items():
        for rel, f in proj["files"].items():
            for nid, n in f["nodes"].items():
                if nid == needle or n["tok"].lower() == needle:
                    exact.append((proot, rel, n))
                elif needle in nid or needle in n["tok"].lower():
                    partial.append((proot, rel, n))

    if not exact and not partial:
        print(f"[no hits for {args.symbol}]")
        return 1

    for group, label in ((exact, "exact"), (partial, "partial")):
        if not group:
            continue
        print(f"[{label}]")
        for proot, rel, n in group[:20]:
            pname = Path(proot).name
            print(f"  [{pname}] {rel}:{n['line']}  {n['cat']}  {n['tok']}")
    return 0


def cmd_callers(args) -> int:
    """Reverse edge lookup: who calls <symbol>?

    Walks every indexed file's nodes, scans their edges for a 'calls'
    pointing at a node whose id matches needle. Exact match on node id
    (lowercased), partial match on tok.
    """
    idx = _load_index()
    needle = args.symbol.lower()

    hits: list = []
    for proot, proj in idx["projects"].items():
        for rel, f in proj["files"].items():
            for nid, n in f["nodes"].items():
                for edge in n.get("edges", []):
                    if not isinstance(edge, list) or len(edge) < 2:
                        continue
                    target, rel_kind = edge[0], edge[1]
                    if rel_kind != "calls":
                        continue
                    if target == needle or needle in target:
                        hits.append((proot, rel, n, target))

    if not hits:
        print(f"[no callers found for {args.symbol}]")
        return 1

    for proot, rel, n, target in hits[: args.limit]:
        pname = Path(proot).name
        print(f"  [{pname}] {rel}:{n['line']}  {n['cat']} {n['tok']}  →  {target}")
    if len(hits) > args.limit:
        print(f"  ...+{len(hits) - args.limit} more (raise --limit)")
    return 0


def cmd_calls(args) -> int:
    """Forward edge lookup: what does <symbol> call?

    Find the definition node for <symbol> (exact id match preferred),
    then list its outbound 'calls' edges. If multiple matches, list
    all of them grouped.
    """
    idx = _load_index()
    needle = args.symbol.lower()

    matches: list = []
    for proot, proj in idx["projects"].items():
        for rel, f in proj["files"].items():
            for nid, n in f["nodes"].items():
                if nid == needle or n["tok"].lower() == needle:
                    callees = [e[0] for e in n.get("edges", [])
                               if isinstance(e, list) and len(e) >= 2
                               and e[1] == "calls"]
                    matches.append((proot, rel, n, callees))

    if not matches:
        print(f"[no definitions found for {args.symbol}]")
        return 1

    for proot, rel, n, callees in matches:
        pname = Path(proot).name
        print(f"[{pname}] {rel}:{n['line']}  {n['cat']} {n['tok']}  "
              f"calls {len(callees)}:")
        if not callees:
            print("  (none)")
        else:
            for c in callees:
                print(f"  → {c}")
    return 0


def cmd_status(args) -> int:
    idx = _load_index()
    print(f"store: {INDEX_PATH}")
    projects = idx["projects"]
    if not projects:
        print("  (empty)")
        return 0

    print(f"projects: {len(projects)}")
    for proot in sorted(projects):
        proj = projects[proot]
        nfiles = len(proj["files"])
        nsym   = sum(len(f["nodes"]) for f in proj["files"].values())
        print(f"  {Path(proot).name:24s}  {nfiles:5d} files   {nsym:6d} symbols")
    return 0


def cmd_forget(args) -> int:
    idx = _load_index()
    fp = Path(args.file).resolve()
    proot = _project_root(fp)
    proj = idx["projects"].get(str(proot))
    if not proj:
        print(f"[no index]")
        return 1
    try:
        rel = str(fp.relative_to(proot))
    except ValueError:
        rel = str(fp)
    if rel in proj["files"]:
        del proj["files"][rel]
        _save_index(idx)
        print(f"forgot {rel}")
        return 0
    print(f"[not indexed: {rel}]")
    return 1


def cmd_drop(args) -> int:
    idx = _load_index()
    if args.project:
        proot = Path(args.project).resolve()
    else:
        proot = _project_root(Path.cwd())
    if str(proot) in idx["projects"]:
        del idx["projects"][str(proot)]
        _save_index(idx)
        print(f"dropped index for {proot.name}")
        return 0
    print(f"[no index for {proot.name}]")
    return 1


# =============================================================================
# CLI
# =============================================================================

def main() -> int:
    p = argparse.ArgumentParser(
        prog="relmem",
        description="Symbolic memory tool for Claude Code sessions.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("index", help="recursively parse files into the index (incremental)")
    pi.add_argument("dir")
    pi.add_argument("--ext", default="py,ailang,sh,md",
                    help="comma-separated extensions without dot (default: py,ailang,sh,md)")
    pi.set_defaults(f=cmd_index)

    ps = sub.add_parser("summary", help="project-wide symbolic summary")
    ps.add_argument("--project", default=None)
    ps.set_defaults(f=cmd_summary)

    pq = sub.add_parser("query", help="search keywords across all indexed projects")
    pq.add_argument("keyword", nargs="+")
    pq.add_argument("--limit", type=int, default=15)
    pq.set_defaults(f=cmd_query)

    pf = sub.add_parser("focus", help="symbols matching a substring in one file")
    pf.add_argument("file")
    pf.add_argument("symbol")
    pf.set_defaults(f=cmd_focus)

    psy = sub.add_parser("symbols", help="all symbols in a single file")
    psy.add_argument("file")
    psy.set_defaults(f=cmd_symbols)

    pw = sub.add_parser("where", help="find where a symbol is defined across all projects")
    pw.add_argument("symbol")
    pw.set_defaults(f=cmd_where)

    pc = sub.add_parser("callers", help="who calls <symbol> (reverse edge lookup)")
    pc.add_argument("symbol")
    pc.add_argument("--limit", type=int, default=25)
    pc.set_defaults(f=cmd_callers)

    pca = sub.add_parser("calls", help="what <symbol> calls (forward edges from a definition)")
    pca.add_argument("symbol")
    pca.set_defaults(f=cmd_calls)

    pforg = sub.add_parser("forget", help="drop a single file from the index")
    pforg.add_argument("file")
    pforg.set_defaults(f=cmd_forget)

    pd = sub.add_parser("drop", help="drop entire project index")
    pd.add_argument("--project", default=None)
    pd.set_defaults(f=cmd_drop)

    pst = sub.add_parser("status", help="index location + project sizes")
    pst.set_defaults(f=cmd_status)

    args = p.parse_args()
    return args.f(args)


if __name__ == "__main__":
    sys.exit(main())
