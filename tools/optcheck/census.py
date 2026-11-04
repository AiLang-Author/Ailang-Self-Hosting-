#!/usr/bin/env python3
"""Side-effect census: does the emitted code keep every side effect the source asks for?

usage: census.py <opt binary> <base binary> <entry.ailang> <libdir> [--all]
Both binaries come from the same source and need .funcmap (-funcmap). The base is built
with every optimizer group off except inline (BASE_OFF below), so inlining is the same on
both sides. Reads <opt binary>.optlog if present (-optlog).

For each compiled function it counts, in the source body:
  sys  SystemCall(...)
  st   StoreValue(...), SetByte(...), Pool.field = ..., ptr@field = ...
and in the emitted machine code:
  sys  syscall instructions
  st   instructions that write memory not addressed from rbp or rsp
A function whose optimized code has fewer side-effect instructions than the base build is
flagged DROP; a legitimate drop (stores merged into one block copy, say) has a rule in the
optlog, printed beside it. Source counts are shown for reference: inlining pulls callee
side effects into callers, so source counts are only a floor.
Prints TSV: flag func file:line src_sys base_sys opt_sys src_st base_st opt_st rules
"""
import os, re, subprocess, sys
from collections import defaultdict

BASE_FILE_OFF = 0xB0          # code starts at file offset 0xb0 (vaddr 0x4000b0)
DECL = re.compile(r"^(?:Function|SubRoutine|InlineFunction)\.([A-Za-z_][\w.]*)\s*\{", re.M)
IMPORT = re.compile(r"^\s*LibraryImport\.([\w.]+)", re.M)
WRITE_OPS = {"mov", "movb", "movw", "movl", "movq", "movabs", "add", "sub", "inc", "dec", "and", "or",
             "xor", "not", "neg", "shl", "shr", "sar", "sal", "rol", "ror", "xchg", "adc", "sbb",
             "movnti", "movdqu", "movdqa", "movups", "movaps", "movsd", "movss", "movd", "movhps",
             "movlps", "bts", "btr", "btc", "setb", "sete", "setne", "setl", "setg", "setle", "setge",
             "seta", "setae", "setbe", "cmpxchg", "xadd"}
INT_RMW = {"add", "sub", "inc", "dec", "and", "or", "xor", "not", "neg", "shl", "shr", "sar", "sal",
           "rol", "ror", "adc", "sbb", "xchg", "bts", "btr", "btc", "cmpxchg", "xadd"}


def strip(src):
    """Blank out comments and string literals, keeping line numbers and offsets."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c == '/' and src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i)); i = j
        elif c == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == "\\" else 1
            seg = src[i:j + 1]
            out.append("".join("\n" if ch == "\n" else " " for ch in seg)); i = j + 1
        else:
            out.append(c); i += 1
    return "".join(out)


def bodies(path):
    """name -> (decl line, body text) for each declaration in one file."""
    raw = open(path, errors="replace").read()
    s = strip(raw)
    res = {}
    for m in DECL.finditer(s):
        depth, j = 0, m.end() - 1
        while j < len(s):
            if s[j] == "{": depth += 1
            elif s[j] == "}":
                depth -= 1
                if depth == 0: break
            j += 1
        res[m.group(1)] = (s.count("\n", 0, m.start()) + 1, s[m.end():j])
    return res


def closure(entry, libdir):
    """Files reachable through LibraryImport, entry first."""
    seen, order, todo = set(), [], [os.path.abspath(entry)]
    # The compiler adds these without an import line.
    for auto in ("Arena", "Arrays", "Array"):
        p = os.path.join(libdir, "Library.%s.ailang" % auto)
        if os.path.exists(p): todo.append(p)
    while todo:
        p = todo.pop(0)
        if p in seen or not os.path.exists(p): continue
        seen.add(p); order.append(p)
        for imp in IMPORT.findall(strip(open(p, errors="replace").read())):
            parts = imp.split(".")
            todo.append(os.path.join(libdir, *parts[:-1], "Library.%s.ailang" % parts[-1]))
    return order


def src_counts(body):
    sys_n = len(re.findall(r"\bSystemCall\s*\(", body))
    st = len(re.findall(r"\b(?:StoreValue|SetByte)\s*\(", body))
    st += len(re.findall(r"^\s*[A-Z]\w*\.\w+\s*=(?!=)", body, re.M))
    st += len(re.findall(r"^\s*\w+@\w+\s*=(?!=)", body, re.M))
    return sys_n, st


def emitted(binary, ranges):
    """(start, stop) list -> list of (sys, st). One ndisasm pass that resyncs at every function
    start: code holds inline data, so a plain linear disassembly drifts out of step."""
    import bisect
    lo, hi = ranges[0][0], ranges[-1][1]
    data = open(binary, "rb").read()[:hi]
    cmd = ["ndisasm", "-b", "64", "-e", str(lo), "-o", str(lo)]
    for r in ranges:
        cmd += ["-s", str(r[0])]
    out = subprocess.run(cmd + ["-"], input=data, capture_output=True).stdout.decode(errors="replace")
    starts = [r[0] for r in ranges]
    counts = [[0, 0] for _ in ranges]
    for line in out.splitlines():
        f = line.split(None, 2)
        if len(f) < 3: continue
        try: addr = int(f[0], 16)
        except ValueError: continue
        k = bisect.bisect_right(starts, addr) - 1
        if k < 0 or addr >= ranges[k][1]: continue
        parts = f[2].split(None, 1)
        op = parts[0]
        if op in ("rep", "repe", "repne", "o64") and len(parts) > 1:
            parts = parts[1].split(None, 1); op = parts[0]
        if op == "syscall": counts[k][0] += 1; continue
        # String stores take no operands. movsd with operands is the SSE move.
        if re.match(r"(stos|movs)[bwdq]$", op) and len(parts) == 1: counts[k][1] += 1; continue
        if op not in WRITE_OPS or len(parts) < 2: continue
        dst = parts[1].split(",")[0]
        if "[" not in dst or re.search(r"\[(rbp|rsp)\b", dst): continue
        # Jump tables and other inline data decode as junk (add [rax],al, sbb [rax],al ...).
        # The compiler never uses 32-bit addressing, and its read-modify-write stores are
        # 64-bit with a REX.W prefix. Every store it emits starts with a REX prefix, 88 (a
        # byte store) or an SSE prefix (movsd [m],xmm is F2 0F 11); table bytes rarely do.
        if re.search(r"\[(?:[a-z]{2}:)?e[a-z]{2}", dst) or ":" in dst: continue
        if not re.match(r"(4[0-9a-fA-F]|88|[fF][23]|66)", f[1]): continue
        if op in INT_RMW and not re.match(r"4[89a-fA-F]", f[1]): continue
        # REX then zero bytes decodes as o64 add [r8],al. The compiler never does
        # read-modify-write from a byte register.
        src = parts[1].split(",")[1].strip() if "," in parts[1] else ""
        if op in INT_RMW and src in ("al", "cl", "dl", "bl", "ah", "ch", "dh", "bh"): continue
        counts[k][1] += 1
    return counts


BASE_OFF = "linscan,regleaf,fold,dead,homes,select,magic,math,byte,scanrw,skip,reload"


def counts_of(binary):
    """name -> (sys, st) for every function with a known end."""
    fmap = [(l.split("\t")[0], int(l.split("\t")[1], 16)) for l in open(binary + ".funcmap").read().split("\n") if "\t" in l]
    fmap.sort(key=lambda x: x[1])
    ranges, names = [], []
    for i, (name, off) in enumerate(fmap[:-1]):   # the last function's end is not known
        ranges.append((BASE_FILE_OFF + off, BASE_FILE_OFF + fmap[i + 1][1])); names.append(name)
    return dict(zip(names, emitted(binary, ranges)))


def main():
    binary, base, entry, libdir = sys.argv[1:5]
    show_all = "--all" in sys.argv
    opt, ref = counts_of(binary), counts_of(base)
    defs = {}
    for p in reversed(closure(entry, libdir)):  # entry wins on a clash
        for name, (line, body) in bodies(p).items():
            defs[name] = (p, line, body)
    rules = defaultdict(list)
    if os.path.exists(binary + ".optlog"):
        for l in open(binary + ".optlog"):
            f = l.rstrip("\n").split("\t")
            if len(f) == 4: rules[f[0]].append("%s(%s)%s" % (f[2], f[3], f[1]))
    for name, (es, et) in opt.items():
        if name not in ref: continue
        bs, bt = ref[name]
        where, ss, st = "?", "-", "-"
        if name in defs:
            p, line, body = defs[name]
            where = "%s:%d" % (os.path.relpath(p, os.path.dirname(libdir)), line)
            ss, st = src_counts(body)
        flag = "DROP" if (es < bs or et < bt) else "ok"
        if flag == "ok" and not show_all: continue
        print("\t".join([flag, name, where, str(ss), str(bs), str(es), str(st), str(bt), str(et),
                         " ".join(rules.get(name, [])[:12])]))


if __name__ == "__main__":
    main()
