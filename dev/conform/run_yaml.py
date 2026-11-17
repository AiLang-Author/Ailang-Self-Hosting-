#!/usr/bin/env python3
"""Run yaml_events against the YAML 1.2 test suite (data-2022-01-17)."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITE = os.path.join(HERE, "yaml-test-suite")


def loads_all(data):
    if isinstance(data, bytes):
        text = data.decode("utf-8")
    else:
        text = data
    dec = json.JSONDecoder()
    i = 0
    vals = []
    n = len(text)
    while True:
        while i < n and text[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        val, j = dec.raw_decode(text, i)
        vals.append(val)
        i = j
    return vals


def main():
    if len(sys.argv) != 2:
        print("usage: run_yaml.py /path/to/yaml_events.x", file=sys.stderr)
        return 2
    bin_path = sys.argv[1]
    event_ok = 0
    event_bad = 0
    err_ok = 0
    err_bad = 0
    json_bad = 0
    samples = []
    for dirpath, _dirs, files in os.walk(SUITE):
        if "in.yaml" not in files:
            continue
        if "/tags/" in dirpath + "/":
            continue
        rel = os.path.relpath(dirpath, SUITE)
        src = os.path.join(dirpath, "in.yaml")
        want_err = os.path.exists(os.path.join(dirpath, "error"))
        try:
            proc = subprocess.run([bin_path, src], capture_output=True, timeout=2)
        except subprocess.TimeoutExpired:
            event_bad += 1
            if len(samples) < 25:
                samples.append((rel, "hang", "", ""))
            continue
        if want_err:
            if proc.returncode != 0:
                err_ok += 1
            else:
                err_bad += 1
                if len(samples) < 25:
                    samples.append((rel, "accepted an error case", proc.stdout[:160]))
            continue
        want = open(os.path.join(dirpath, "test.event"), "rb").read()
        if proc.returncode == 0 and proc.stdout == want:
            event_ok += 1
        else:
            event_bad += 1
            if len(samples) < 25:
                samples.append((rel, "event", proc.returncode, proc.stdout[:200], want[:200]))
            continue
        jpath = os.path.join(dirpath, "in.json")
        if not os.path.exists(jpath):
            continue
        try:
            jproc = subprocess.run([bin_path, src, "json"], capture_output=True, timeout=2)
        except subprocess.TimeoutExpired:
            json_bad += 1
            continue
        try:
            got = loads_all(jproc.stdout)
            exp = loads_all(open(jpath, "rb").read())
            same = jproc.returncode == 0 and got == exp
        except Exception as exc:
            same = False
            got = str(exc)
            exp = ""
        if not same:
            json_bad += 1
            if len(samples) < 25:
                samples.append((rel, "json", str(got)[:180], str(exp)[:180]))
    total = event_ok + event_bad + err_ok + err_bad
    print("tests %d" % total)
    print("events pass %d fail %d" % (event_ok, event_bad))
    print("errors pass %d fail %d" % (err_ok, err_bad))
    print("json mismatches %d" % json_bad)
    for row in samples:
        print("---")
        for part in row:
            print(part)
    if event_bad or err_bad:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
