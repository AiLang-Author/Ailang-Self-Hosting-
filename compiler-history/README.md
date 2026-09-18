# Compiler history (rollback binaries)

Dated `ailang.x` / `analyzer.x` snapshots for bug tracking and easy reversal.
Binaries are gitignored (`*.x`). Sources live on git tags/commits.

| File | What |
|------|------|
| `ailang-2026-08-11.x` | Frozen host used during `compiler-improvement` (pre-Assemble wrap) |
| `analyzer-2026-08-05.x` | Analyzer from that era |
| `ailang-2026-06-02-backup8-4.x` | Older root `ailang-backup8-4-2026.x` copy |

Restore:

```
cp compiler-history/ailang-2026-08-11.x ./ailang.x
```
