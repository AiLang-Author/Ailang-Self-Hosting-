# AILang Coreutils

> **Source repository:** [`AiLang-Author/Ailang-Self-Hosting-`](https://github.com/AiLang-Author/Ailang-Self-Hosting-)
> The standalone `CoreUtils-` repository is deprecated — everything now lives under `AiLang_CoreUtils/` inside the main AILang tree.

POSIX-compliant reimplementation of core Unix utilities in AILang. Drop-in replacements for GNU coreutils with competitive performance, smaller binary sizes, and explicit memory management.

## Quick Start

```bash
# Clone the main AILang repo (includes the compiler and the utilities)
git clone https://github.com/AiLang-Author/Ailang-Self-Hosting-.git
cd Ailang-Self-Hosting-/AiLang_CoreUtils

# Build all 57 utilities from source
./build_all_utils.sh

# Install utilities to ~/.local/bin
./install_ailang_utils.sh

# Benchmark AILang vs GNU equivalents
./bench_all_utils.sh
```

Pre-compiled executables live under `AiLang_CoreUtils/dist/{utility}_util/` alongside their source.

## Project Status

**57 utilities building cleanly** — verified by `build_all_utils.sh` (57/57 pass) and `smoke_ailang_utils.sh` (40/40 pass).

The utility set changes over time. See `AiLang_CoreUtils/dist/` for the canonical current list.

## Available Utilities

### File operations
`cat`, `cp`, `mv`, `rm`, `ln`, `touch`, `mkdir`, `file`, `chmod`, `chown`, `chgrp`, `readlink`, `realpath`, `stat`, `df`, `du`

### Text processing
`grep`, `head`, `tail`, `wc`, `cut`, `tr`, `sort`, `uniq`, `nl`, `rev`, `tac`, `fold`, `diff`, `tee`, `paste`, `split`, `expand`, `unexpand`

### Output & display
`echo`, `seq`, `yes`, `true`, `false`, `printenv`

### System information
`ls`, `find`, `pwd`, `whoami`, `logname`, `id`, `uname`, `env`, `date`, `tty`, `which`

### Path manipulation
`basename`, `dirname`

### Process / timing
`sleep`, `nohup`, `sync`

### I/O
`dd`

## Key features

- **Small binaries** — typically 8–40 KB, 50–70% smaller than GNU equivalents
- **Competitive performance** — matches or beats GNU coreutils on common workloads
- **POSIX-first** — the specification is authoritative
- **Explicit memory management** — no hidden allocations, bounded buffers
- **Direct syscalls** — minimal abstraction, no libc dependency
- **Streaming** — fixed memory usage regardless of input size
- **Self-compiled** — built by the AILang self-hosting compiler (`ailang.x`)

## Installation

The `install_ailang_utils.sh` script installs all built utilities to `~/.local/bin` and sets up the `ailang-utils` manager:

```bash
./install_ailang_utils.sh
```

This will:
1. Copy every built utility from `dist/{utility}_util/{utility}_exec` to `~/.local/bin`
2. Create `_ailang`-suffixed aliases alongside the main names
3. Ensure `~/.local/bin` is on your `PATH`
4. Install the `ailang-utils` management tool

### Managing utilities

```bash
ailang-utils status              # List enabled utilities
ailang-utils enable <utility>    # Enable one
ailang-utils disable <utility>   # Disable one (falls back to GNU)
ailang-utils enable all          # Enable everything
ailang-utils disable all         # Revert everything to GNU
ailang-utils benchmark <utility> # Compare one against GNU
```

## Benchmarking

```bash
./bench_all_utils.sh             # All utilities vs GNU
ailang-utils benchmark grep      # Single utility
```

Benchmarks use realistic workloads — no cherry-picked microbenchmarks.

## Building from source

From `AiLang_CoreUtils/`:

```bash
./build_all_utils.sh
```

Per-utility sources live at `dist/{utility}_util/{utility}.ailang`; the script compiles each in place to `{utility}_exec`.

Requires the AILang self-hosting compiler at the repo root (`ailang.x`). If you've just cloned, build it first:

```bash
cd ..                    # to repo root
./ailang.x ailang_cli.ailang ailang.x    # self-host if needed
```

## Repository layout

```
Ailang-Self-Hosting-/
├── ailang.x                         # Self-hosted compiler binary
├── ailang_cli.ailang                # Compiler source
├── AiLang_CoreUtils/                # ← this project
│   ├── dist/
│   │   ├── cat_util/
│   │   │   ├── cat.ailang           # Source
│   │   │   ├── cat_exec             # Compiled binary
│   │   │   └── README.md            # Utility-specific notes
│   │   ├── grep_util/
│   │   ├── ls_util/
│   │   └── ...                      # 57 directories
│   ├── build_all_utils.sh
│   ├── install_ailang_utils.sh
│   ├── bench_all_utils.sh
│   └── README.md                    # This file
├── Librarys/                        # AILang standard library sources
└── Testcode/                        # Example programs & teaching corpus
```

## Design principles

1. **POSIX first** — the specification is authoritative
2. **GNU compatible** — byte-identical output where GNU aligns with POSIX
3. **Explicit memory** — no hidden allocations, bounded buffers
4. **Direct syscalls** — the libc wrapping layer is not between us and the kernel
5. **Streaming** — fixed memory footprint for arbitrary input size
6. **Clear errors** — fail fast with a specific diagnostic

## Performance philosophy

Competitive real-world performance with readable, maintainable code. Measurements drive optimization decisions; no speculative micro-tuning. Most utilities match GNU performance or beat it while staying far smaller as binaries.

## Platform support

- **Linux x86_64** — primary, fully supported
- Argument parsing reads `/proc/self/cmdline` (Linux)
- System calls are x86_64 Linux syscalls
- Windows and macOS are not currently supported

## Known gaps vs GNU

The AILang utilities don't implement every GNU flag. If a script of yours depends on niche GNU extensions (e.g. `stat -c` / `--format`, long-form flags, exotic `find` predicates), verify behavior first. Explicit paths to `/usr/bin/grep`, `/usr/bin/stat` etc. will bypass the shims if needed.

Per-utility documentation under `dist/{utility}_util/README.md` lists known differences.

## Contributing

Contributions welcome for:
- Bug fixes and performance improvements
- Additional utilities matching the project criteria
- GNU feature-gap closures (documented in per-utility READMEs)
- Documentation and examples

### Requirements

- Match or beat GNU performance on typical workloads
- 100% of the utility's test suite passing
- POSIX compliance
- Memory safety verified
- Follow the existing code patterns

## Testing

All utilities include test suites covering:
- Functional correctness (byte-for-byte match with GNU where POSIX agrees)
- POSIX compliance
- Edge cases and error handling
- Memory safety (no leaks, no out-of-bounds)
- Performance characteristics

## License

MIT for the utilities. The AILang compiler itself is under SCSL — see the main repo's `LICENSE` files.

## References

- **AILang (compiler + utilities):** https://github.com/AiLang-Author/Ailang-Self-Hosting-
- **POSIX.1-2017:** https://pubs.opengroup.org/onlinepubs/9699919799/
- **GNU Coreutils:** https://www.gnu.org/software/coreutils/

---

**Quality over quantity.** Each utility aims to be the best version of itself before the next one gets added.
