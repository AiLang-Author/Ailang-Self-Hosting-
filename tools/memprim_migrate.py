#!/usr/bin/env python3
"""Rewrite GetByte / SetByte / Dereference / StoreValue into RDMEM_ / WRMEM_.

    python3 -I tools/memprim_migrate.py [--write] [--split-add] PATH...

PATH is a file or a directory (searched for *.ailang). Without --write it
only reports what it would change.

Mapping:

    GetByte(b, o)                 RDMEM_8(b, o)
    SetByte(b, o, v)              WRMEM_8(b, o, v)
    Dereference(a)                RDMEM_64(a)
    Dereference(a, "byte")        RDMEM_8(a)          (the parser adds offset 0)
    Dereference(a, "word")        RDMEM_16(a)
    Dereference(a, "dword")       RDMEM_32(a)
    StoreValue(a, v)              WRMEM_64(a, v)
    Dereference(a, "qword")       RDMEM_64(a)
    Dereference(a, "sdword")      RDMEM_S32(a)        (and sbyte, sword; the old
                                                   compiler read 8 bytes here)
    StoreValue(a, v, "byte")      WRMEM_8(a, v)       (and word, dword, qword)

--split-add   also turns an address written as Add(b, o) into the
              two-part form: Dereference(Add(b, o), "dword") becomes
              RDMEM_32(b, o). The parser rebuilds the same Add node.
              A "byte" hint keeps the whole address, since RDMEM_8(b, o)
              is GetByte, which the optimizer treats differently.
Anything the tool cannot map exactly (a hint that is not a string literal,
a wrong argument count) is left as it is and listed.

A migrated compiler source can only be built by a compiler that already
knows RDMEM_/WRMEM_.
"""
import os
import sys

NAMES = ("GetByte", "SetByte", "Dereference", "StoreValue")
HINT_W = {'"byte"': "8", '"word"': "16", '"dword"': "32", '"qword"': "64"}
# Never valid on the old compiler (it read 8 bytes), but the intent is plain.
SIGNED_W = {'"sbyte"': "S8", '"sword"': "S16", '"sdword"': "S32"}

SKIP_DIRS = {".git", "third_party", "archive", "test262"}


def code_mask(text):
    """True for each char that is code (not inside a string or // comment)."""
    mask = [True] * len(text)
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"' and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            j = min(j + 1, n)
            for k in range(i + 1, j - 1):
                mask[k] = False
            i = j
        elif c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                mask[k] = False
            i = j
        else:
            i += 1
    return mask


def is_ident(c):
    return c.isalnum() or c == "_"


def split_args(text, open_at, mask):
    """Args of the call whose '(' is at open_at.

    Returns (close_at, [(start, end), ...]) with spans into text, or None.
    """
    depth = 0
    spans = []
    start = open_at + 1
    i = open_at
    while i < len(text):
        if mask[i]:
            c = text[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    if text[start:i].strip() or spans:
                        spans.append((start, i))
                    return i, spans
            elif c == "," and depth == 1:
                spans.append((start, i))
                start = i + 1
        i += 1
    return None


class Stats:
    def __init__(self):
        self.changed = {n: 0 for n in NAMES}
        self.skipped = []


def as_add(arg):
    """(b, o) text when arg is exactly Add(b, o), else None."""
    s = arg.strip()
    if not s.startswith("Add(") or not s.endswith(")"):
        return None
    m = code_mask(s)
    r = split_args(s, 3, m)
    if r is None or r[0] != len(s) - 1 or len(r[1]) != 2:
        return None
    (a0, a1), (b0, b1) = r[1]
    return s[a0:a1].strip(), s[b0:b1].strip()


def rewrite(text, opts, stats, where):
    mask = code_mask(text)
    out = []
    i = 0
    n = len(text)
    while i < n:
        hit = None
        if mask[i] and (i == 0 or not is_ident(text[i - 1])):
            for name in NAMES:
                e = i + len(name)
                if text.startswith(name, i) and e < n and text[e] == "(" and mask[e]:
                    hit = name
                    break
        if hit is None:
            out.append(text[i])
            i += 1
            continue
        open_at = i + len(hit)
        r = split_args(text, open_at, mask)
        if r is None:
            out.append(text[i])
            i += 1
            continue
        close_at, spans = r
        # Rewrite nested calls inside each argument first.
        args = [rewrite(text[a:b], opts, stats, where) for a, b in spans]
        new = convert(hit, args, opts)
        if new is None:
            line = text.count("\n", 0, i) + 1
            stats.skipped.append((where, line, text[i:close_at + 1].split("\n")[0][:100]))
            out.append(hit + "(" + ",".join(args) + ")")
        else:
            stats.changed[hit] += 1
            out.append(new)
        i = close_at + 1
    return "".join(out)


def convert(name, args, opts):
    """New call text, or None to leave the call alone."""
    def join(fn, parts):
        return fn + "(" + ", ".join(p.strip() for p in parts) + ")"

    def addr_parts(addr, width=None):
        # RDMEM_8(b, o) / WRMEM_8(b, o, v) lower to GetByte / SetByte, not
        # to the byte-hinted Dereference / StoreValue. Splitting those
        # would change the tree, so an 8-bit hinted address stays whole.
        if opts["split_add"] and width != "8":
            ab = as_add(addr)
            if ab is not None:
                return list(ab)
        return [addr]

    if name == "GetByte":
        return join("RDMEM_8", args) if len(args) == 2 else None
    if name == "SetByte":
        return join("WRMEM_8", args) if len(args) == 3 else None
    if name == "Dereference":
        if len(args) == 1:
            return join("RDMEM_64", addr_parts(args[0]))
        if len(args) == 2:
            w = HINT_W.get(args[1].strip()) or SIGNED_W.get(args[1].strip())
            if w is None:
                return None
            return join("RDMEM_" + w, addr_parts(args[0], w))
        return None
    if name == "StoreValue":
        if len(args) == 2:
            return join("WRMEM_64", addr_parts(args[0]) + [args[1]])
        if len(args) == 3:
            w = HINT_W.get(args[2].strip())
            if w is None:
                return None
            return join("WRMEM_" + w, addr_parts(args[0], w) + [args[1]])
        return None
    return None


def files(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
            continue
        for d, dirs, fs in os.walk(p):
            dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS)
            for f in sorted(fs):
                if f.endswith(".ailang"):
                    yield os.path.join(d, f)


def main(argv):
    opts = {"write": False, "split_add": False}
    paths = []
    for a in argv:
        if a == "--write":
            opts["write"] = True
        elif a == "--split-add":
            opts["split_add"] = True
        elif a.startswith("-"):
            sys.exit("unknown flag " + a)
        else:
            paths.append(a)
    if not paths:
        sys.exit(__doc__)
    stats = Stats()
    nfiles = 0
    for f in files(paths):
        rel = os.path.relpath(f)
        with open(f, encoding="utf-8", errors="surrogateescape") as h:
            src = h.read()
        new = rewrite(src, opts, stats, rel)
        if new != src:
            nfiles += 1
            if opts["write"]:
                with open(f, "w", encoding="utf-8", errors="surrogateescape") as h:
                    h.write(new)
    total = sum(stats.changed.values())
    print("%s %d calls in %d files" % ("rewrote" if opts["write"] else "would rewrite", total, nfiles))
    for k, v in stats.changed.items():
        print("  %-12s %d" % (k, v))
    if stats.skipped:
        print("left alone: %d" % len(stats.skipped))
        for where, line, snip in stats.skipped:
            print("  %s:%d  %s" % (where, line, snip))


if __name__ == "__main__":
    main(sys.argv[1:])
