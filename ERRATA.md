# Errata

This tree is not a claim of full GNU coreutils 9.4 conformance.

The score below is the 2026-11-17 `make check` of coreutils 9.4 (644 tests), adjusted by the targeted rescored logs from that day. It is not a second full run. Skips are not passes.

- 503 pass
- 138 skip
- 3 fail
- 0 error

## Fails

- `tests/factor/factor-parallel.sh` exits 124. `src/factor` is the GNU binary. It is not an AILANG port.
- `tests/misc/nohup.sh` opens `/dev/tty` in the test script. A `setsid` run has no controlling terminal, so that open returns "No such device or address".
- `tests/cp/sparse-perf.sh` hits the wrapper file-size cap, `ulimit -f 32768` (1 KiB blocks, 32 MiB). That cap stays in place.

## Skips

The 138 skips are the ones recorded in the full run. Later rescored tests were fails or the usage error, not skips.

- 44 very expensive. `RUN_VERY_EXPENSIVE_TESTS` is left unset. This includes `factor/t00` through `factor/t36`, sort benchmarks, `rm/ext3-perf`, `cp/perm`, and `du/2g`.
- 9 expensive. `RUN_EXPENSIVE_TESTS` is left unset.
- 32 need root.
- 9 need SELinux.
- 6 `seq` tests are stopped by the suite disk guard.
- 4 need a controlling terminal (`stty` three times, and `mv/i-3`).
- 5 need `LD_PRELOAD` or gdb. `rm/r-root` is here because gdb will not load the `src/rm` shell wrapper. The others are `rm-readdir-fail`, `cp/nfs-removal-race`, `df/no-mtab-status`, and `df/skip-duplicates`.
- 3 need inotify, gdb, or Python `pyinotify`.
- 3 need SMACK.
- 2 need valgrind.
- 2 need a program that is not built (`arch`, and the `coreutils` multicall).
- 2 stop because `NAME_MAX` is too small for the test.

One each: Perl Expect, the Swedish locale, nice level 0, a timezone database (`date-debug`), `O_DIRECT`, filesystem timestamps that cannot hold the big-time value, the `du/8gb` file cap, a full partition, a directory `cat` that still succeeds, GNU/Hurd, `runcon` setup, an unreadable directory, `capget` (`ls/no-cap`), xattr support, and a rootfs entry in mtab.

## AILANG behavior that still skips

- `tests/ls/ls-time.sh` skips because `ls --full -l` prints `Jan 15  1998`. The test wants `1998-01-15 23:00:00.000000000 +0000`. `touch -m -d '1998-01-15 23:00'` already stores that UTC time.
- `tests/stat/stat-nanoseconds.sh` skips because `ls --full-time` does not print `18:43:33.023456789`.

`tests/misc/usage_vs_getopt.sh` was an error in the full run (exit 99 at `cut`) and passed in the later rescore. Do not count it as an error.

`tests/help/help-version-getopt.sh` is not part of this score. `yes -- --help` can loop.

The suite logs are not in this repository. They are under `/home/bob/gnu-conformance/logs/`. `full-rescore-2.log` is the full run. A later log supersedes it only for the tests that log names.
