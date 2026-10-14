# fannkuch-redux

Single thread. Permute `0 .. n-1`, flip until the first slot is 0,
and alternate the flip counts into a checksum. Arrays are length 16,
allocated once outside the clock. Each line is

```
FANNKUCH <n> checksum <c> max <m> ns <ns>
```

`run.sh` pins core 1. g++ is `-O3` with vectorization off, loop
unrolling off, and complete peeling off. `-fno-unroll-loops` alone
peeled the flip into a chain of swaps. That peeled binary was 0.243 s
at n=10 and 40.2 s at n=12, against the scalar loop below. `AILANG_CC`
overrides the compiler. The default is the repo `./ailang.x`.

## FX-8320, one pinned core

Measured with `/tmp/opt2-dead/ailang2.x`
(sha256 `fa9deebddf2680a3fd1d52d1b48a55121ad516ed5f45ce3591990f4730ce2109`),
not the installed compiler. Checksums matched every run. n=12 is the
Benchmarks Game answer: checksum `3968050`, max flips `65`. n=7 is
`228` and `16`. n=10 is `73196` and `38`.

| | n=10 | n=12 |
| --- | --- | --- |
| g++ | 0.277 s, 0.299 s | 47.4 s, 48.6 s |
| AILANG | 2.532 s, 2.540 s, 2.577 s | 460.8 s |

n=12 is one AILANG pin. n=7 is about 2.08–2.10 ms versus g++ 0.277 ms
and 0.289 ms.

g++ flips with two pointers. The inner swap is eight instructions:
load, load, `add $8`, `sub $8`, store, store, compare, jump.

AILANG `At` is a scaled `mov (%r14,%rcx,8)`, and `Put` is `shl $3`
plus a push/pop store. Both stay real calls. The splice in
`Optimize_InlineEligible` only takes a function whose last action is
`ReturnValue` of a local name. `At` returns the dereference
expression. `Put` does not return. Each swap in the flip calls `At`
twice and `Put` twice, and each call builds a frame. That is the gap.
It is the same shape at n=10 and n=12, about 9×.
