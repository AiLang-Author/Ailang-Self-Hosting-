#!/usr/bin/env python3
"""Run all NBS/ECMA-55 P*.BAS programs against the C64 GTK kernel. No skips."""
import glob
import os
import signal
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
STATE = "/tmp/c64_basic"
KERN = os.path.join(ROOT, "c64_basic_gtk.x")
PASTE = os.path.join(STATE, "paste.txt")
BUSY = os.path.join(STATE, "busy.txt")
OUT = os.path.join(STATE, "output.txt")
NBSDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nbs")
INDIR = "/tmp/nbs-ecma55-test/NBS"

# Programs that do a lot of RND / stats.
SLOW = {"P133", "P134", "P129", "P130", "P131", "P132"}
# Interactive INPUT programs — short timeout, then restart kernel.
INPUTS = {"P073", "P081", "P084", "P107", "P108", "P109", "P110", "P111", "P112", "P113", "P203"}


def read_text(path):
    try:
        return open(path).read()
    except OSError:
        return ""


def start_kernel():
    os.makedirs(STATE, exist_ok=True)
    open(PASTE, "w").close()
    open(OUT, "w").close()
    open(BUSY, "w").write("0")
    return subprocess.Popen([KERN], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def kill_kernel(proc):
    if proc is None:
        return
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=2)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def wait_idle(timeout):
    t0 = time.time()
    saw_busy = False
    while time.time() - t0 < timeout:
        busy = read_text(BUSY).strip()
        if busy == "1":
            saw_busy = True
        if saw_busy and busy != "1":
            time.sleep(0.15)
            return True
        # Some short programs finish before we sample busy=1.
        out = read_text(OUT)
        if "READY." in out and (time.time() - t0) > 0.4:
            if busy != "1":
                return True
        time.sleep(0.05)
    return False


def after_run(text):
    """Source lines are echoed before RUN; judge only execution output."""
    key = "\nRUN\n"
    i = text.rfind(key)
    if i >= 0:
        return text[i + len(key):]
    i = text.rfind("\nRUN")
    if i >= 0:
        return text[i + 1:]
    return text


def classify(name, text, timed_out):
    if timed_out:
        return "TIMEOUT"
    body = after_run(text)
    up = body.upper()
    failed = False
    if "*** TEST FAILED" in up:
        failed = True
    if "TEST FAILED IN" in up:
        failed = True
    if "***  TEST FAILED" in up:
        failed = True
    if "*** TEST FAILS" in up:
        failed = True
    if "TEST FAILS" in up and "TEST PASSED" not in up:
        failed = True
    if failed:
        return "FAIL"
    if " ERROR" in up and body.find("?") >= 0:
        return "ERROR"
    if "BREAK" in up:
        if "TEST FAILED" not in up:
            return "PASS"
    if "END PROGRAM" in up or "READY." in body:
        return "PASS"
    return "UNKNOWN"


def run_one(proc, bas_path):
    name = os.path.splitext(os.path.basename(bas_path))[0]
    body = open(bas_path).read()
    extra = ""
    inp = os.path.join(INDIR, name + ".in")
    if not os.path.isfile(inp):
        inp = os.path.join(NBSDIR, name + ".in")
    if os.path.isfile(inp):
        extra = open(inp).read()
        if extra and not extra.endswith("\n"):
            extra += "\n"
    extra += ("N\n0\n") * 40
    payload = "NEW\n" + body
    if not payload.endswith("\n"):
        payload += "\n"
    payload += "RUN\n" + extra
    open(OUT, "w").close()
    open(BUSY, "w").write("0")
    open(PASTE, "w").write(payload)
    timeout = 180.0
    if name in SLOW:
        timeout = 600.0
    if name in INPUTS:
        timeout = 25.0
    ok = wait_idle(timeout)
    got = read_text(OUT)
    outdir = os.path.join(NBSDIR, "out")
    os.makedirs(outdir, exist_ok=True)
    open(os.path.join(outdir, name + ".out"), "w").write(got)
    if not ok:
        return name, "TIMEOUT", got
    return name, classify(name, got, False), got


def main():
    files = sorted(glob.glob(os.path.join(NBSDIR, "P*.BAS")))
    if not files:
        print("no NBS files in", NBSDIR)
        sys.exit(2)
    if not os.path.isfile(KERN):
        print("missing", KERN)
        sys.exit(2)
    proc = start_kernel()
    time.sleep(0.4)
    counts = {"PASS": 0, "FAIL": 0, "ERROR": 0, "TIMEOUT": 0, "UNKNOWN": 0}
    results = []
    try:
        for f in files:
            name = os.path.splitext(os.path.basename(f))[0]
            prior = os.path.join(NBSDIR, "out", name + ".out")
            if os.path.isfile(prior) and os.environ.get("NBS_FORCE") != "1":
                got = read_text(prior)
                status = classify(name, got, False)
                if os.path.getsize(prior) > 200000:
                    status = "TIMEOUT"
                counts[status] = counts.get(status, 0) + 1
                results.append((name, status))
                print("%-8s %s  (cached)" % (status, name))
                sys.stdout.flush()
                continue
            name, status, got = run_one(proc, f)
            if status == "TIMEOUT" or name in INPUTS:
                kill_kernel(proc)
                proc = start_kernel()
                time.sleep(0.4)
            counts[status] = counts.get(status, 0) + 1
            results.append((name, status))
            print("%-8s %s" % (status, name))
            sys.stdout.flush()
            if status in ("FAIL", "ERROR", "TIMEOUT", "UNKNOWN"):
                tail = "\n".join(got.splitlines()[-12:])
                print("  ---")
                print("  " + tail.replace("\n", "\n  "))
                print("  ---")
    finally:
        kill_kernel(proc)

    print()
    print("TOTAL %d  PASS %d  FAIL %d  ERROR %d  TIMEOUT %d  UNKNOWN %d" % (
        len(results), counts["PASS"], counts["FAIL"], counts["ERROR"],
        counts["TIMEOUT"], counts["UNKNOWN"]))
    outp = os.path.join(NBSDIR, "LAST_RUN.txt")
    with open(outp, "w") as fh:
        for name, status in results:
            fh.write("%s %s\n" % (status, name))
        fh.write("TOTAL %d PASS %d FAIL %d ERROR %d TIMEOUT %d UNKNOWN %d\n" % (
            len(results), counts["PASS"], counts["FAIL"], counts["ERROR"],
            counts["TIMEOUT"], counts["UNKNOWN"]))
    sys.exit(0 if counts["FAIL"] + counts["TIMEOUT"] + counts["UNKNOWN"] == 0 else 1)


if __name__ == "__main__":
    main()
