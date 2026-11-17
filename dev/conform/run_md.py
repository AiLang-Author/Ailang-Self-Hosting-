#!/usr/bin/env python3
"""Run md_html against the CommonMark 0.31.2 spec examples."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "commonmark", "spec-0.31.2.json")


def main():
    if len(sys.argv) < 2:
        print("usage: run_md.py /path/to/md_html.x [start] [count]", file=sys.stderr)
        return 2
    bin_path = sys.argv[1]
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    data = json.load(open(SPEC, encoding="utf-8"))
    ok = 0
    bad = 0
    samples = []
    seen = 0
    for e in data:
        num = e["example"]
        if num < start:
            continue
        if count and seen >= count:
            break
        seen += 1
        raw = e["markdown"].encode("utf-8")
        want = e["html"].encode("utf-8")
        fd, path = tempfile.mkstemp(prefix="mdspec-")
        os.write(fd, raw)
        os.close(fd)
        try:
            proc = subprocess.run([bin_path, path], capture_output=True, timeout=2)
        except subprocess.TimeoutExpired:
            bad += 1
            if len(samples) < 20:
                samples.append((num, e["section"], "hang", b"", want[:180]))
            os.unlink(path)
            continue
        os.unlink(path)
        if proc.returncode == 0 and proc.stdout == want:
            ok += 1
        else:
            bad += 1
            if len(samples) < 20:
                samples.append((num, e["section"], proc.returncode, proc.stdout[:220], want[:220]))
    print(f"tests {ok + bad}")
    print(f"pass {ok} fail {bad}")
    for num, sec, code, got, exp in samples:
        print(f"--- ex {num} {sec} rc={code}")
        print("got", got)
        print("exp", exp)
    if bad:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
