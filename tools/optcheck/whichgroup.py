#!/usr/bin/env python3
"""Which optimizer group drops a function's stores?

usage: whichgroup.py <compiler> <program> <function>
Builds <program> once per -optoff group and prints the function's memory-store count for
each. The group whose build restores the base count is the one doing the dropping; its
rules in <program>.optlog (-optlog) name the statement.
"""
import os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census

C, prog, fn = sys.argv[1:4]
repo = os.path.dirname(os.path.dirname(HERE))
env = dict(os.environ)
env.setdefault("AILANG_LIB_PATH", os.path.join(repo, "Librarys"))
groups = ["(none)", "linscan", "regleaf", "fold", "dead", "homes", "select", "magic", "math",
          "byte", "scanrw", "skip", "reload", census.BASE_OFF]
with tempfile.TemporaryDirectory() as d:
    row = []
    for g in groups:
        out = os.path.join(d, "x.x")
        args = [os.path.abspath(C), "-funcmap"] + ([] if g == "(none)" else ["-optoff=" + g]) + [prog, "-o", out]
        subprocess.run(args, cwd=repo, env=env, capture_output=True)
        c = census.counts_of(out).get(fn) if os.path.exists(out + ".funcmap") else None
        row.append("%s=%s" % ("base" if g == census.BASE_OFF else g, c[1] if c else "?"))
print(fn, " ".join(row))
