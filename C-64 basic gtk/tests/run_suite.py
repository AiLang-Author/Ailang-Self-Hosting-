#!/usr/bin/env python3
"""Feed .bas files into the C64 GTK kernel via paste.txt; check screen.bin."""
import glob, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
STATE = "/tmp/c64_basic"
KERN = os.path.join(ROOT, "c64_basic_gtk.x")
PASTE = os.path.join(STATE, "paste.txt")
SCREEN = os.path.join(STATE, "screen.bin")
TESTDIR = os.path.dirname(os.path.abspath(__file__))


def screen_text():
    if not os.path.isfile(SCREEN):
        return ""
    raw = open(SCREEN, "rb").read()
    cols, rows = 80, 24
    lines = []
    for r in range(rows):
        row = raw[r * cols:(r + 1) * cols]
        s = "".join(chr(b) if 32 <= b < 127 else " " for b in row).rstrip()
        if s:
            lines.append(s)
    return "\n".join(lines)


def wait_paste_empty(timeout=20.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if os.path.getsize(PASTE) == 0:
                time.sleep(0.4)
                return True
        except OSError:
            return True
        time.sleep(0.05)
    return False


def ensure_kernel():
    os.makedirs(STATE, exist_ok=True)
    if subprocess.call(["pgrep", "-x", "c64_basic_gtk.x"], stdout=subprocess.DEVNULL) == 0:
        return None
    if not os.path.isfile(KERN):
        print("missing", KERN)
        sys.exit(2)
    open(PASTE, "w").close()
    p = subprocess.Popen([KERN], cwd=REPO)
    time.sleep(0.5)
    return p


def run_one(bas_path):
    name = os.path.splitext(os.path.basename(bas_path))[0]
    want_path = os.path.splitext(bas_path)[0] + ".want"
    want = open(want_path).read().splitlines() if os.path.isfile(want_path) else []
    body = open(bas_path).read()
    payload = "NEW\n" + body
    if not payload.endswith("\n"):
        payload += "\n"
    payload += "RUN\n"
    open(PASTE, "w").write(payload)
    if not wait_paste_empty():
        return name, False, "timeout waiting for paste drain", screen_text()
    time.sleep(0.3)
    got = screen_text()
    missing = [w for w in want if w not in got]
    ok = not missing
    return name, ok, ("missing " + repr(missing) if missing else "ok"), got


def main():
    spawned = ensure_kernel()
    files = sorted(glob.glob(os.path.join(TESTDIR, "*.bas")))
    fail = 0
    for f in files:
        name, ok, msg, got = run_one(f)
        print(("PASS" if ok else "FAIL"), name, msg)
        if not ok:
            fail += 1
            print("--- screen ---")
            print(got)
            print("--------------")
    print("%d tests, %d fail" % (len(files), fail))
    if spawned:
        spawned.terminate()
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
