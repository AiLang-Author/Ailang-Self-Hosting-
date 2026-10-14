#!/usr/bin/env python3
"""
py2aim.py — Convert indentation-based Python to AIMacro brace syntax.

CPython tests (and most .py scripts) use suites after `:`. AIMacro wants
C-style `{ }`. This is the analog of the test262 preprocessor that rewrites
source before the JS harness sees a file.

Usage:
    python3 tools/py2aim.py input.py [output.aim]
    python3 tools/py2aim.py --stdin < input.py

Not a full Python-to-AIMacro transpiler: it only inserts braces. Keywords
AIMacro does not have (`yield`, `async`, `@decorator`) pass through and
will fail later at parse — same as unsupported test262 features.

Copyright (c) 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.
"""

from __future__ import annotations

import argparse
import re
import sys

CONTINUE_SUITE = ("else", "elif", "except", "finally")
SUITE_START = (
    "def",
    "class",
    "if",
    "elif",
    "else",
    "while",
    "for",
    "try",
    "except",
    "finally",
    "with",
    "async",
)


def _leading_ws(line: str) -> str:
    i = 0
    while i < len(line) and line[i] in " \t":
        i += 1
    return line[:i]


def _code_part(line: str) -> tuple[str, str]:
    """Split a physical line into code vs trailing comment, ignoring # in strings."""
    in_s = None
    esc = False
    i = 0
    while i < len(line):
        c = line[i]
        if in_s:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == in_s:
                in_s = None
            i += 1
            continue
        if c in ("'", '"'):
            # triple quotes
            if line[i : i + 3] in ("'''", '"""'):
                in_s = line[i : i + 3]
                i += 3
                continue
            in_s = c
            i += 1
            continue
        if c == "#":
            return line[:i].rstrip(), line[i:]
        i += 1
    return line.rstrip(), ""


def _indent_width(ws: str) -> int:
    n = 0
    for c in ws:
        n += 4 if c == "\t" else 1
    return n


def _advance_quote_state(s: str, state: str | None) -> str | None:
    """Track unclosed quotes across lines. state is None, ', \", ''', or \"\"\"."""
    i = 0
    n = len(s)
    while i < n:
        if state:
            closer = state
            if s.startswith(closer, i):
                i += len(closer)
                state = None
                continue
            if s[i] == "\\" and len(closer) == 1:
                i += 2
                continue
            i += 1
            continue
        c = s[i]
        if c == "#":
            break
        if s.startswith('"""', i):
            state = '"""'
            i += 3
            continue
        if s.startswith("'''", i):
            state = "'''"
            i += 3
            continue
        if c in ("'", '"'):
            state = c
            i += 1
            continue
        i += 1
    return state


def _bracket_delta(s: str) -> int:
    """Net open-paren/bracket/brace change, ignoring strings/comments."""
    delta = 0
    in_s = None
    esc = False
    i = 0
    while i < len(s):
        c = s[i]
        if in_s:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == in_s[0] and s.startswith(in_s, i):
                i += len(in_s)
                in_s = None
                continue
            i += 1
            continue
        if c == "#":
            break
        if s.startswith('"""', i):
            in_s = '"""'
            i += 3
            continue
        if s.startswith("'''", i):
            in_s = "'''"
            i += 3
            continue
        if c in ("'", '"'):
            in_s = c
            i += 1
            continue
        if c in "([{":
            delta += 1
        elif c in ")]}":
            delta -= 1
        i += 1
    return delta



def convert(src: str) -> str:
    """Insert `{` / `}` from indentation. Preserve comments."""
    raw_lines = src.splitlines()
    if src.endswith("\n"):
        raw_lines.append("")  # dummy to flush dedents; dropped if empty

    out: list[str] = []
    stack = [0]
    i = 0
    n = len(raw_lines)
    qstate: str | None = None
    # >0 while inside an unclosed ([{ on a suite header (multiline def/class)
    header_depth = 0
    header_indent = 0

    def is_blank_or_comment(s: str) -> bool:
        t = s.strip()
        return t == "" or t.startswith("#")

    while i < n:
        line = raw_lines[i]
        if i == n - 1 and line == "" and src.endswith("\n"):
            # flush remaining closes
            while len(stack) > 1:
                pad = " " * stack[-2]
                out.append(f"{pad}}}")
                stack.pop()
            break

        # Docstrings / multi-line strings: do not treat colons as suites.
        if qstate:
            out.append(line)
            qstate = _advance_quote_state(line, qstate)
            i += 1
            continue

        if is_blank_or_comment(line):
            out.append(line)
            i += 1
            continue

        ws = _leading_ws(line)
        width = _indent_width(ws)
        code, comment = _code_part(line[len(ws) :])
        first = code.split(None, 1)[0] if code else ""
        first = first.rstrip(":")
        line_q = _advance_quote_state(line, None)

        # Dedent: close braces. else/elif/except/finally share the brace.
        while width < stack[-1]:
            stack.pop()
            pad = " " * stack[-1]
            if width == stack[-1] and first in CONTINUE_SUITE:
                # `} else {` on this line — brace emitted with the keyword
                break
            out.append(f"{pad}}}")

        if width == stack[-1] and first in CONTINUE_SUITE:
            # replace implicit close: emit `} else {` using this line's indent
            body = code
            if body.endswith(":"):
                body = body[:-1].rstrip()
            extra = ""
            if comment:
                extra = "  " + comment
            out.append(f"{ws}}} {body} {{{extra}")
            # next indent will push
            i += 1
            # look ahead: if next real line is more indented, push that width
            j = i
            while j < n and is_blank_or_comment(raw_lines[j]):
                j += 1
            if j < n:
                nxt_w = _indent_width(_leading_ws(raw_lines[j]))
                if nxt_w > width:
                    stack.append(nxt_w)
            qstate = line_q
            continue

        colon = code.find(":")
        if first in SUITE_START and colon != -1 and colon < len(code) - 1 and not code.endswith(":"):
            head = code[:colon].rstrip()
            tail = code[colon + 1 :].strip()
            extra = ""
            if comment:
                extra = "  " + comment
            out.append(f"{ws}{head} {{ {tail} }}{extra}")
            i += 1
            qstate = line_q
            continue

        if code.endswith(":") and first in SUITE_START:
            body = code[:-1].rstrip()
            extra = ""
            if comment:
                extra = "  " + comment
            out.append(f"{ws}{body} {{{extra}")
            i += 1
            j = i
            while j < n and is_blank_or_comment(raw_lines[j]):
                j += 1
            if j < n:
                nxt_w = _indent_width(_leading_ws(raw_lines[j]))
                if nxt_w > width:
                    stack.append(nxt_w)
                elif nxt_w == width:
                    # one-liner already consumed? treat as empty block
                    out.append(f"{ws}}}")
            else:
                out.append(f"{ws}}}")
            qstate = line_q
            continue

        # Multiline def/class/(if) header: track brackets; closing '):' → ') {'
        if header_depth > 0:
            delta = _bracket_delta(code)
            header_depth += delta
            if header_depth <= 0 and code.rstrip().endswith(":"):
                # signature finished: width=None):  →  width=None) {
                body = code[:-1].rstrip()
                extra = ""
                if comment:
                    extra = "  " + comment
                out.append(f"{ws}{body} {{{extra}")
                header_depth = 0
                i += 1
                j = i
                while j < n and is_blank_or_comment(raw_lines[j]):
                    j += 1
                if j < n:
                    nxt_w = _indent_width(_leading_ws(raw_lines[j]))
                    if nxt_w > header_indent:
                        stack.append(nxt_w)
                    elif nxt_w == header_indent:
                        out.append(f"{' ' * header_indent}}}")
                else:
                    out.append(f"{' ' * header_indent}}}")
                qstate = line_q
                continue
            out.append(line)
            qstate = line_q
            i += 1
            continue

        # Suite header that opens brackets without ending ':' on this line
        if first in SUITE_START and not code.endswith(":"):
            delta = _bracket_delta(code)
            if delta > 0:
                out.append(line)
                header_depth = delta
                header_indent = width
                qstate = line_q
                i += 1
                continue

        out.append(line)
        qstate = line_q
        i += 1

    # drop trailing dummy empties from flush
    while out and out[-1] == "":
        out.pop()
    text = "\n".join(out)
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("input", nargs="?", help="Python source file")
    ap.add_argument("output", nargs="?", help="AIMacro .aim path (default stdout)")
    ap.add_argument("--stdin", action="store_true", help="Read source from stdin")
    args = ap.parse_args()

    if args.stdin or not args.input:
        src = sys.stdin.read()
    else:
        with open(args.input, encoding="utf-8") as f:
            src = f.read()

    aim = convert(src)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(aim)
    else:
        sys.stdout.write(aim)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
