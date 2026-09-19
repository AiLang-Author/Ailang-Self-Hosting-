# NBS / ECMA-55 Minimal BASIC — full run

Date: 2026-09-18

Suite: National Bureau of Standards Minimal BASIC programs
`P001.BAS`–`P208.BAS` (208 files). Source:
https://github.com/sehugg/nbs-ecma55-test (NBS/).

Nothing was skipped. Runner: `tests/run_nbs.py` (paste.txt into the
Ailang kernel, transcript `/tmp/c64_basic/output.txt`). Per-file
verdict also in `tests/nbs/LAST_RUN.txt`.

## Score

| Result | Count | Meaning |
|---|---|---|
| PASS | 114 | Ran; no real `*** TEST FAILED ***` in execution output |
| FAIL | 25 | Language wrong or incomplete |
| ERROR | 63 | `?… ERROR` — many of these *are* the NBS error programs |
| TIMEOUT | 6 | Hung, mostly INPUT retry loops |
| UNKNOWN | 0 | |
| **Total** | **208** | |

A second pass over saved transcripts (ignore “TEST FAILS” in
instruction text, not the verdict) is about 116 pass / 22 fail.

ERROR is not a skip. NBS has a large error-condition set (missing END,
bad subscripts, extra `SIN` args, `DEF` cycles, log of a negative, …).
Those programs pass the NBS rule if the processor rejects them or
documents an extension.

## FAIL / TIMEOUT (language still short)

| Program | Title / note |
|---|---|
| P027 | Accuracy of constants and variables |
| P029, P030 | Overflow of expressions / constants |
| P044, P046–P049 | FOR: step, limit vs control var, nested counts |
| P061 | Numeric expressions containing … |
| P089, P090 | ON-GOTO control expression out of range |
| P098–P101 | READ unquoted/quoted string, string/numeric overflow |
| P107, P108 | INPUT numeric / subscripted (and retry) |
| P109, P110, P112 | INPUT — timeout on retry |
| P122, P129 | Overflow on function value |
| P132–P134 | RND average / chi-square / Kolmogorov |
| P161, P192 | Timeout |
| P166 | Compound expressions with control |
| P181 | Underflow in evaluation |
| P186 | Extra spaces have no effect |
| P203 | INPUT — timeout |

FOR `TO`/`STEP` must be evaluated *before* the control variable is
assigned (`FOR I=9 TO I STEP I`). That fix is in the source; this
score is from the binary before that rebuild.

## How to re-run

From the Ailang-Self-Hosting tree:

```
python3 "C-64 basic gtk/tests/run_nbs.py"
python3 "C-64 basic gtk/tests/rejudge_nbs.py"
```

Kernel: `C-64 basic gtk/c64_basic_gtk.x` (compile with `./ailang.x`).
State dir: `/tmp/c64_basic`. Transcripts: `tests/nbs/out/` (not in git).
