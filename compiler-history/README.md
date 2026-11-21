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
| `ailang-2026-11-16-pre-memprim.x` | Host replaced 2026-11-16 by the RDMEM_/WRMEM_ compiler. 7888332 bytes, sha256 `6ee514776c33e8f680cc912bb3918ebf33de23ec3696937713b29517e4d2802a`. Knows GetByte/SetByte/Dereference/StoreValue only, so it cannot build the tree after that date. |
| `ailang-2026-11-16-memprim-seed.x` | Host retired 2026-11-18. Same bytes as root `ailang.x` from 2026-11-16 until the wide-multiply promotion: 7,875,176 bytes, sha256 `7cc4128adaf3c1be31de15007aca1f4d4e187187026a6618c509d2f9c50f2ec4`. |
| `ailang-2026-11-18-wide-mul.x` | Copy of the wide-multiply host (bf312820). 7,891,300 bytes, sha256 `596b108af36662a108279401e65c92f176cec8948f2bb8b151513013a9554872`. The register-hold promotion that replaced it was put back: that compiler aliased two live values onto one register. |
| `ailang-2026-11-19-1657-bf312820.x` | Host retired 2026-11-19 16:57 by the 0c1b8828 promotion (6ced82fa). Same bytes as `ailang-2026-11-18-wide-mul.x`: 7,891,300 bytes, sha256 `596b108af36662a108279401e65c92f176cec8948f2bb8b151513013a9554872`. Miscompiles a value held in rcx across the rcx-pair Subtract scratch (escbench ScanA). |
| `ailang-2026-11-19-0c1b8828.x` | Copy of the 0c1b8828 host when it was promoted. 6,503,295 bytes, sha256 `81c9077b6467176bb2e0ede107986ef8f789a8f2d51a8ffac1f2a32f2f54331f`. |
| `ailang-2026-11-21-0051-0c1b8828.x` | Host retired 2026-11-21 00:51 by the 0532729d promotion. Same bytes as `ailang-2026-11-19-0c1b8828.x`. Deprecated for two miscompiles. (1) A constant-count shift of a computed value loaded the count into rcx while the linear scan kept a live value there, giving wrong results with no error. (2) A 16- or 32-bit load or store through a hoisted loop pointer fails to compile ("Variable not found"). |
| `ailang-2026-11-21-0532729d.x` | Copy of the 0532729d host (byte-loop codegen, both fixes above), promoted 2026-11-21. Self-host fixed point, 6,450,365 bytes, sha256 `6e4f069f809f9b2bb3491bf0fb5d9f55f479417574874d60d947db9115b66daa`. |
| `analyzer-2026-11-16-pre-memprim.x`, `ailang_lsp-2026-11-16-pre-memprim.x` | Analyzer and LSP built from the old parser; both report RDMEM_/WRMEM_ calls as undefined. Replaced by rebuilds from the migrated source. |

Restore:

```
cp compiler-history/ailang-2026-11-21-0051-0c1b8828.x ./ailang.x   # previous host (0c1b8828)
```
