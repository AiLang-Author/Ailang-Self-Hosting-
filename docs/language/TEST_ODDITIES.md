# Test Oddities

## 2026-05-23: First-run fail, second-run pass (+ sentinel bleed-through)

### Run Sequence (all on same boot, back-to-back)

| # | Test | Result | Key observation |
|---|------|--------|-----------------|
| 1 | test_accel_gcn.x | 0/64 FAIL | dst[0..3] = 0xDEADBEEF..F2 (sentinels), rest = 0. Shader didn't write. |
| 2 | test_accel_gcn.x | 64/64 PASS | dst = 42,43,44... correct. Fence 2 polls. |
| 3 | test_gemv.x | 0/512 FAIL | y[0..7] = 0x0. Fence 100 polls. L2 not flushed? |
| 4 | test_3buf.x | 0/64 FAIL | y[0] = 1115684864 (= 0x42800000 = 64.0f!). Stale GEMV data from run 3 visible. |
| 5 | test_3buf.x | 64/64 PASS | y = 100..163, correct. |
| 6 | test_gemv.x | 0/512 FAIL | y[0..7] = 0x64..0x6B (= 100..107 decimal). This is test_3buf x[] data! |
| 7 | test_gemv.x | 511/512 PASS | y[0] = 0x42800000 OK, y[1] = 0xDFADBEF0 FAIL (sentinel corruption), rest OK. |

### Analysis

**The shader IS executing on first run** — the fence completes (val=1), and
debug sentinel writes (0xDEADBEEF) appear in dst[0..3] on run 1. But the
shader's actual buffer writes are invisible to CPU readback.

**Cross-run data bleeding confirms L2 cache is the issue:**
- Run 4 (3buf) sees GEMV's 64.0f result from run 3 — it leaked through L2
- Run 6 (GEMV) sees 3buf's x[i]=i+100 data from run 5 — stale L2 again
- Run 7: y[1] = 0xDFADBEF0 — looks like a partially-overwritten sentinel
  (0xDEADBEF0 with high nibble flipped D→F, possibly a GPU write collision)

**The EVENT_WRITE_EOP was changed from 0x528 to 0x514 (CACHE_FLUSH_AND_INV_TS_EVENT)**
but the L2 flush is still not working on first dispatch. Possible causes:

1. **SURFACE_SYNC before dispatch only invalidates, doesn't flush** — The
   pre-dispatch SURFACE_SYNC uses TC invalidate bits (0xC000 + 0xE000) to make
   sure the shader sees fresh data. But on first run after CP reset, the TC
   may need a full flush+invalidate, not just invalidate.

2. **Write-combine BAR0 writes not committed** — CPU writes to VRAM go through
   write-combining MMIO (BAR0/BAR2). These may sit in CPU WC buffers and not
   reach physical VRAM before the GPU reads them. Need `sfence` or `mfence`
   after VramWrite and before dispatch. The second run works because the first
   run's WC buffer eventually drained.

3. **Fence memory not zeroed** — The fence VRAM location (0x10040) isn't
   explicitly zeroed before dispatch. If it already contains `1` from a prior
   run, the poll returns immediately and the CPU reads before the shader
   finishes. However, the fence shows `val=1 after 2/100 polls` which suggests
   it IS polling (not instant), so this may not be the primary issue.

4. **y[1] = 0xDFADBEF0 on run 7** — The sentinel debug code writes
   0xDEADBEEF/F0/F1/F2 to dst[0..3] via BAR0 just before dispatch. On run 7,
   y[1] = 0xDFADBEF0 (not 0xDEADBEF0, not 0x42800000). The high nibble
   D→F flip suggests a partial GPU write over a BAR0-written sentinel —
   a race between CPU BAR0 write and GPU shader store to the same address.
   This sentinel write should be removed or moved before data upload.

### Most likely root cause

**Write-combine ordering (#2)** combined with **sentinel race (#4)**. The CPU
BAR0 writes (VramWrite + sentinel) haven't drained to VRAM backing when the
shader launches. First run reads stale/zero VRAM. Second run's data is already
committed from the first run's WC drain.

### Recommended fixes to try

1. Add x86 `sfence` (or `mfence`) syscall after all VramWrite calls, before dispatch
2. Zero the fence VRAM location before each dispatch
3. Remove or relocate the debug sentinel writes (they race with shader stores)
4. Add SURFACE_SYNC with TCL1_ACTION_ENA + TC_ACTION_ENA (full flush+inv) before dispatch

### Terminal Output

See `test oddity` file in repo root for full terminal output of all 7 runs.
