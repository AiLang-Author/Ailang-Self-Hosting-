# Compiler history (rollback binaries)

Dated `ailang.x` / `analyzer.x` snapshots for bug tracking and easy reversal.
Binaries are gitignored (`*.x`). Sources live on git tags/commits.

| File | What |
|------|------|
| `ailang-2026-10-02.x` | Host replaced 2026-10-04 by the tree-shake compiler. Built 2026-10-02 19:36, 3,125,174 bytes, sha256 `bb2120ab0ecbdbd82584819a0f5e5aeb2bc272d6572c9421ff31ec00b9448b8d`. Pre -TS and -asm. |
| `ailang-2026-09-18.x` | Host replaced 2026-10-02. Built 2026-09-18, 3,120,966 bytes, sha256 `6d414a9f45ba271c92831fe92a47d00e83cb09894c6ea251ce7ca6c76e29b40a`. Pre RDTSC leaf fix. |
| `ailang-2026-08-11.x` | Frozen host used during `compiler-improvement` (pre-Assemble wrap) |
| `analyzer-2026-08-05.x` | Analyzer from that era |
| `ailang-2026-06-02-backup8-4.x` | Older root `ailang-backup8-4-2026.x` copy |
| `ailang-2026-10-04.x`, `ailang-2026-10-06-*.x`, `ailang-2026-10-13-*.x` | Moved here from `Librarys/Compiler/Deprecated/` on 2026-11-04. The suffix is the source commit. |
| `ailang-2026-11-16-memprim-seed.x` | Seed for branch `memprim-rdwr`, where the tree spells memory access as RDMEM_/WRMEM_ and GetByte/SetByte/Dereference/StoreValue no longer exist. The root `ailang.x` cannot build that tree; build it with this file until a new host is promoted. Bootstrap fixed point, 7875176 bytes, sha256 `7cc4128adaf3c1be31de15007aca1f4d4e187187026a6618c509d2f9c50f2ec4`. |

Restore:

```
cp compiler-history/ailang-2026-08-11.x ./ailang.x
```
