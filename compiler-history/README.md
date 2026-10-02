# Compiler history (rollback binaries)

Dated `ailang.x` / `analyzer.x` snapshots for bug tracking and easy reversal.
Binaries are gitignored (`*.x`). Sources live on git tags/commits.

| File | What |
|------|------|
| `ailang-2026-09-18.x` | Host replaced 2026-10-02. Built 2026-09-18, 3,120,966 bytes, sha256 `6d414a9f45ba271c92831fe92a47d00e83cb09894c6ea251ce7ca6c76e29b40a`. Pre RDTSC leaf fix. |
| `ailang-2026-08-11.x` | Frozen host used during `compiler-improvement` (pre-Assemble wrap) |
| `analyzer-2026-08-05.x` | Analyzer from that era |
| `ailang-2026-06-02-backup8-4.x` | Older root `ailang-backup8-4-2026.x` copy |

Restore:

```
cp compiler-history/ailang-2026-08-11.x ./ailang.x
```
