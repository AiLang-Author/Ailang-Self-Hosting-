# High-Performance AILANG

How to write an AILANG program that stays readable and still runs with tools that have had decades of C work. The first worked example is `AiLang_CoreUtils/dist/grep_util/grep.ailang`, measured against GNU grep 3.11. The second, "Second example: a server" below, is a one-core HTTP server measured against a Rust entry in the same challenge.

The speed does not come from a secret instruction. It comes from doing the obvious thing once, with a compiler primitive, and from not doing the clever thing on every byte.

## What the grep result actually says

On a 133 MB, 2 million-line file, `LC_ALL=C`, output drained through a pipe, every case byte-identical with GNU grep 3.11:

| Case | AILang | GNU | |
|---|---|---|---|
| `kernel` | 211 ms | 269 ms | 1.27x |
| `-w kernel` | 225 ms | 348 ms | 1.55x |
| `UNIQUE_MARKER_XYZ` | 49 ms | 76 ms | 1.56x |
| `-F error_handler` | 200 ms | 256 ms | 1.28x |
| `-Fc error_handler` | 146 ms | 170 ms | 1.16x |
| `mem.*buf` | 192 ms | 298 ms | 1.55x |
| `ker[nm]el` | 228 ms | 415 ms | 1.82x |
| `-E 'socket\|daemon'` | 389 ms | 511 ms | 1.31x |

`^kernel` was a tie, 175 ms against 173 ms. `-v` was 1.05x. Those are the cases where both tools have to look at every line.

GNU grep is about 3,000 lines of driver plus a 4,400-line DFA and a keyword-set matcher. The AILang grep is one file, about 2,400 lines, and the binary is 132 KB. The file is long because flags and output are long. The scan itself is a handful of functions with names that say what they do: `ProcessMapped`, `BestPairOffset`, `ClassifyRegexFast`, `ProcessMappedRegex`.

GNU's decades are real. They went into a DFA that can accept a regular expression in C, and into locale handling this grep does not try to match. On a byte pattern, a required literal decides most lines before any automaton runs. Once that is true, the race is `MemMem` against `MemMem`. The compiler lowers `MemMem`, `MemMemFold`, `MemChr`, `MemCompare`, and `MemoryCopy` to SSE2. That is enough.

## Read this before tuning

Write the program so a person can say what the hot path does in one sentence. Then measure. Then replace that one sentence with a primitive. Do not start from a skip table.

A sentence that held up:

> Map the file, find the next needle, and emit the line that contains it.

A sentence that did not:

> For each line, copy it, lowercase it, and run the regex interpreter.

The second one was 12 times slower than GNU on `mem.*buf` (3473 ms against 292 ms). The first one, with the needle pulled out of the regex, is faster than GNU on that same pattern.

## Do this

### Scan the bytes once

For a regular file, map it and search the mapping. Split into lines only where a hit says the line matters.

```ailang
off = MemMem(Add(data, scan_pos), remaining, pat, plen)
IfCondition LessThan(off, 0) ThenBlock: { BreakLoop }
cand = Add(scan_pos, off)
line_start = FindLineStart(data, cand)
```

`ProcessMapped` in the grep is this loop. Printing `-v` cannot do it, because the lines you want are the ones with no hit. That path walks lines, and it is the close case in the table. That is the right trade.

### Call the SSE primitive

These are compiler primitives, not library loops:

| Primitive | Use |
|---|---|
| `MemChr(hay, byte, len)` | Find one byte. Newlines. A rare anchor. |
| `MemMem(hay, haylen, needle, needlen)` | First offset of an exact needle, or `-1`. |
| `MemMemFold(...)` | Same, folding ASCII `A`–`Z` to `a`–`z` on both sides. |
| `MemCompare(a, b, n)` | `0` when the `n` bytes match. |
| `MemoryCopy(dst, src, n)` | Move a line only when you must keep it. |

A `WhileLoop` of `RDMEM_8` over a multi-megabyte buffer is the slow version of one of these calls. The interpreter pays for every byte. The primitive pays for a 16-byte vector step.

### Pull a literal out of a pattern

If a match cannot exist without some bytes, search for those bytes and run the real matcher only on hits.

- `mem.*buf` is "find `mem`, then find `buf` after it on that line." The Thompson interpreter never runs.
- `^kernel` is "the hit is in column 0."
- `ker[nm]el` is "find `ker`, test one class byte, compare `el`."
- `socket|daemon` is "the earlier of two needles."
- Anything else with a literal prefix of two or more bytes still searches that prefix, then calls `LineMatches` on the candidate line only.

`ClassifyRegexFast` is the list of shapes. A pattern that is not one of those shapes stays on the engine. That is correct. It is also why `mem.*buf` moved from 3473 ms to 192 ms without a new regex implementation.

### Anchor on a rare pair, and only when it is not the first pair

`MemMem` always anchors on the first two bytes of the needle. For `kernel` that is `ke`, which almost never false-hits. For `error_handler` that is `er`, which also sits in `buffer`, `read_buffer`, and `interface`. Every one of those was a 13-byte verify, and `-Fc` lost.

`BestPairOffset` scores adjacent pairs. Common letters (`e`, `a`, `r`, `o`, `n`, `t`, `i`, `s`) are cheap. `k` and `v` are rarer. `j`, `q`, `x`, `z` and punctuation, including `_`, are rarer still. The scan searches the winning pair, then checks the whole needle at `hit - pair_offset`.

If the winning pair is already at offset 0, do not do that. `MemMem` of the whole needle is the same anchor with the verify inside the primitive. Adding an AILANG check on every hit made `kernel` and `-i kernel` slower and did not change the result. `use_pair` is set only when `pair_off > 0`.

### Keep allocation out of the loop

The regex matcher used to allocate a thread buffer per line. On a large file that blew memory and time. Scratch for a NUL-terminated line lives in `Scratch` for the whole file. Pattern tables live in `Patterns` for the whole run.

Allocate before the scan. Free after the file, or let the arena die with the process. Do not `Allocate` the thing you touch on every hit.

### Resume past the candidate you rejected

A failed verify resumes at `pair_at + 1`. A failed `-w` check does too.

Resuming at `cand + 1` looks right and loops forever when the anchor sits later in the needle. The same pair is still in the window, the word check fails again, and `scan_pos` does not move. The next real match has its pair at `cand + 1 + pair_off`, which is `pair_at + 1`.

### Count lines only when a human asked for numbers

`-n` does not count newlines from the start of the file on every match. `CountNewlines` runs from the previous match to this one. Matches are sparse. The file is not.

## Do not do this

### Do not walk bytes in AILANG when a primitive exists

```ailang
// Slow. One interpreter step per byte.
i = 0
WhileLoop LessThan(i, n) {
    IfCondition EqualTo(RDMEM_8(hay, i), 101) ThenBlock: { ReturnValue(i) }
    i = Add(i, 1)
}

// The same search.
ReturnValue(MemChr(hay, 101, n))
```

A short compare of a needle you already located is fine as `MemCompare`. A scan of the file is not.

This rule is about long buffers. A primitive call has a fixed price of its own, and on a short string that price wins. See "Price the call, not only the loop" in the server part below.

### Do not call a function per line

`LineMatches` is the right call when the pattern is a real regex and the line is a real candidate. It is the wrong call for two million lines that are mostly misses. The literal fast path never calls it. The regex fast path calls it only after a literal hit, and several patterns do not call it at all.

An extra AILANG call on every hit is visible. Checking the whole needle from AILANG, on top of a `MemMem` that had already anchored on those same first bytes, cost about 30 ms on `kernel`. The fix was to delete the call, not to micro-optimize the call.

### Do not allocate inside the scan

Per-line `Allocate` plus `Deallocate` dominated an earlier regex grep and pushed the process into gigabytes. Reuse one scratch buffer. If the buffer must grow, grow it outside the per-byte loop.

### Do not run an engine on lines that cannot match

A leading literal, a required pair, or an alternation of literals is a filter. The engine is the check for the lines that pass. Running the Thompson interpreter on every line is how `mem.*buf` lost by 12x while the literal path was already winning.

### Do not trust a textbook skip

Scalar Horspool is implemented in the compiler's `MemMem` and then jumped over. It lost the long miss and it loses to the streaming pair filter on a short word. A longer needle is not automatically a skip-table needle. `error_handler` got faster by choosing a rarer pair for the filter that was already winning, not by enabling the skip.

### Do not time a lie

GNU grep treats output to `/dev/null` like `-q` and stops at the first match. That produced 1 ms "timings" that were not the scan. Drain a pipe. Force `LC_ALL=C` when the program is byte-oriented, or a UTF-8 locale makes GNU do multibyte work and flatters the byte scanner. Refuse to record a time when the output differs. `AiLang_CoreUtils/grep_bench_repro.sh` is that protocol. hyperfine, a few warmups, the median.

### Do not anchor a long literal on its first letters without looking

`er` is a terrible anchor in English text. `_h` is a good one. The score table lives in `LiteralByteScore`. If you add a new scan, score the needle you actually search, including the lowercased form when `-i` folded it.

## A shape that keeps working

```ailang
// Once per run.
pair_off = BestPairOffset(pat, plen)
use_pair = 0
IfCondition GreaterThan(pair_off, 0) ThenBlock: { use_pair = 1 }

scan_pos = 0
WhileLoop LessThan(scan_pos, data_len) {
    IfCondition EqualTo(use_pair, 1) ThenBlock: {
        off = MemMem(Add(data, scan_pos), Subtract(data_len, scan_pos),
                     Add(pat, pair_off), 2)
        // Reject, verify the whole needle at off - pair_off, or emit
        // the line and set scan_pos to the next line.
    } ElseBlock: {
        off = MemMem(Add(data, scan_pos), Subtract(data_len, scan_pos), pat, plen)
        // Emit the line and move to the next line.
    }
}
```

The branch is the whole optimization. One side is the primitive. The other side is the primitive aimed at a better pair, plus one compare of a needle that is already in hand.

## Where to read it in the grep

| Function | What it is for |
|---|---|
| `ProcessMapped` | The mapped-file scan. Literals, `-w`, and `-c -v` live here. |
| `LiteralByteScore`, `BestPairOffset` | Which two bytes to search. |
| `ClassifyRegexFast` | Which regex shapes can skip the interpreter. |
| `ProcessMappedRegex` | The mapped scan for those shapes. |
| `LineMatches` | The per-line engine for everything that is still a real regex. |

Read `ProcessMapped` before `LineMatches`. The fast program is the first one. The second one is what you call when the first one cannot decide.

## Second example: a server

The grep reads one big file. A server does the opposite: millions of small requests, each a few hundred bytes of parsing, a few B-tree pages, and a few kilobytes of JSON. The worked example is the twelve-dollar server challenge entry `submissions/ailang-native-2paws` (HTTP/1.1 on io_uring, a native SQLite reader and writer, JWT HS256), measured on one core of an FX-8320 at 200,000 users against the Rust entry `rust-iouring-kensac`.

### Measure per request, user and kernel apart

`perf record -e cycles:u -p <pids>` for 30 seconds in the middle of a steady load, with the binary built by `ailang.x -funcmap`, so samples map to function names (code starts at `0x4000b0` plus the map offset). Read `utime` and `stime` of every thread from `/proc/<pid>/task/*/stat` before and after. Divide CPU time by requests served in the same window.

| per request | AILang | Rust |
|---|---:|---:|
| total CPU | 41.4 µs | 30.0 µs |
| kernel | 23.5 µs | 20.2 µs |
| user | 17.9 µs | 9.8 µs |

Without the split you optimize the wrong half. Here most of the gap was user time, and most of that was spread thin across every hot function, not one bad loop.

Know your noise before you claim a win. Kernel time moved between 23.4 and 24.7 µs per request across identical runs. A change worth less than about 1 µs per request does not show in a whole-server profile. Measure it with a micro-benchmark of the one function, hot and cold, and only then confirm with the server.

### Price the call, not only the loop

JSON escaping needs three tests per byte (`"`, `\`, below `0x20`). On a 114-byte post body, hot:

| scan | ns per body |
|---|---:|
| one 8-byte SWAR loop testing all three | 129 |
| `MemChr` for `"`, `MemChr` for `\`, SWAR only for bytes below `0x20` | 110 |
| one `MemChr` alone | 19 |

One `MemChr` call covers the whole body in 19 ns, call included. Its SSE2 loop tests 16 bytes per step. The compiled SWAR loop spends about 60 instructions on every 8 bytes. At this size, two primitive passes plus a smaller loop beat one loop that does every test. Price the call before you avoid it. Measure the crossover for your own case; 114 bytes is the only size this was measured at.

### Check the answer before you read the clock

An earlier version of this section said the opposite: 47 ns for the single SWAR loop and 121 ns for the `MemChr` version. The 47 came from a miscompiled loop. The register holding the `\` pattern was overwritten with the space pattern, so every space matched as a backslash and the scan stopped at the second word. It was fast because it did almost no work. The server's tests still passed: a wrong "needs escaping" answer only sends the body down the slower escaping path, and the output is the same. Make every benchmark print or check the result it timed, and compare that result with a reference before you trust the time.

### Write short fixed pieces with stores

`MemoryCopy` copies 16 bytes per step and then copies the rest one byte at a time. A 6-byte `{"id":` never reaches the vector step; it is six trips through a byte loop. A feed entry wrote five such pieces with `MemoryCopy`. Writing each as one or two `WRMEM_64` stores of a precomputed little-endian word took that function from 1.18 to 0.63 µs per request.

```ailang
// '{"id":' as one word; the two bytes past it are overwritten by what follows
WRMEM_64(Add(out, ol), FeedSt.k_id)
FeedSt.len = Add(ol, 6)
```

This needs slack past the end of the buffer: allocate the output buffer 64 bytes larger than its capacity.

### One operation per statement in a hot loop

Nested expressions compile to `push`/`pop` chains and stack spills. SHA-256's compression function written as nested expressions ran at 3.59 µs per block. The same rounds written one operation per statement, stepping pointers instead of computing `Add(base, Multiply(i, 8))`, ran at 2.67 µs, with identical digests.

```ailang
// slower
se = BitwiseAnd(BitwiseXor(BitwiseXor(RightShift(xe, 6), RightShift(xe, 11)), RightShift(xe, 25)), m32)

// faster
t = RightShift(xe, 6)
u = RightShift(xe, 11)
t = BitwiseXor(t, u)
u = RightShift(xe, 25)
t = BitwiseXor(t, u)
se = BitwiseAnd(t, m32)
```

Do this in the few loops a profile names, not everywhere. The readable form is the right default, and the compiler is meant to close this gap. It mostly has. After the November 2026 register work, nested and flattened ran at 2.70 and 2.03 µs. Two later changes cut the nested time to 2.19 µs, against about 2.0 flattened. An operator with two compound operands now parks the left operand in rbx instead of on the stack whenever the right side provably never writes rbx. When rbx already holds a variable, the operator reads the left operand from memory instead of pushing and popping rbx.

### Divide by a constant with a multiply

`x / 10` for `0 <= x < 2^32` is `RightShift(Multiply(x, 3435973837), 35)`. Seven digits went from 48 to 36 ns.

Keep that constant in a variable or a pool field until the compiler fix lands. `Multiply` by a literal strictly between 2^31 and 2^32 used a 32-bit `IMUL` and kept only the low 32 bits of the product: `Multiply(7, 2147483649)` gave 2147483655. Exactly 2^31 and 2^32, negatives, every other operation and the constant held in a variable were all correct. An 11,089-case sweep of constants through every operation and form found this one bug and nothing else.

### Use `_IO` only for memory someone else writes while you run

`RDMEM_IO_*` and `WRMEM_IO_*` are volatile: the optimizer never caches, merges or moves them. They exist for devices. In an io_uring ring the device is the kernel, but only the head and tail indices (and the provided-buffer ring tail) change under you. Submission and completion entries are filled before the tail store publishes them and read after the tail load says they are ready, so plain `WRMEM`/`RDMEM` is correct there, ordered by those volatile accesses. `RDMEM_S8/S16/S32` are the plain signed reads; a signed field does not need `_IO`.

### The first reader pays the miss

The single-loop escape scan took 129 ns on a hot body and about 235 ns on bodies spread over 128 MB, one per 4 KB page. A second pass over the same pages cost the same as the first. Huge pages took it to about 215 ns. In the server this scan was the first code to touch each post body, so the profile charged it with those misses. Rust paid the same misses in `memmove`. Before you optimize a function, run it hot and cold. If the cold number is the profile's number, the cost is memory, not code.

### Keep the disk off the response path

A commit's responses must wait for its WAL write, but nothing else should. The server writes through a shared-memory ring to a separate I/O process, and a second process does checkpoints (WAL fdatasync, write-back, database fdatasync), so WAL appends never queue behind a sync. That took a 220,000-user hold on an SSD from p99 7.4 s to 583 ms.

What remained was the kernel. In a memory-limited cgroup the dirty-page limit is scaled to the cgroup's free memory, and a write that crosses it waits in `balance_dirty_pages`. Sampling `/proc/<pid>/task/*/wchan` every 10 ms while the process is in `D` state shows exactly where. The Rust entry stalled the same way, on its event loop.

### Do not log from the processes you are timing

Forked processes share their stdout file position. When one process's `write` to the log blocks on a throttled disk, the others wait in `fdget_pos` for the same file. Diagnostic logging turned one 220,000-user run into a different result. Log to a separate file per process, or keep the threshold high, and never quote a number measured with logging on.

### Where to read it in the server

| Function | What it is for |
|---|---|
| `Feed.PutPost`, `Feed.PutEscN`, `Feed.PutInt` | The feed JSON: word stores, the SWAR escape scan, digits by multiply |
| `Crypto.SHA256_Compress` | One operation per statement |
| `IoUring.GetSqe`, `IoUring.PBufRingAdd` | Plain entry writes, volatile tail stores |
| `SQLite.IoServe`, `SQLite.CkServe` | The I/O process and the checkpoint worker |

## When this advice stops

A pattern with no literal, a real `-v` print, a pipe you cannot map, and a UTF-8 locale are different programs. They walk lines, or they walk bytes, and they should say so. The manual is not a claim that every AILANG loop beats gcc. It is the set of moves that made one AILANG program beat GNU grep without hiding the algorithm.
