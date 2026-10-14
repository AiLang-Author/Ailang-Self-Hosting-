# 64×64 matmul

Row-major `C[i][j] += A[i][k] * B[k][j]` with a 2×2 register tile.
Both programs run that tile 2000 times. Entries are small integers
(`A = i+j+1`, `B = i*3-j+64`), so a fused multiply-add and a separate
multiply plus add print the same bits. The checksum is the sum of `C`,
which is exactly `2399076352.0`.

`run.sh` pins core 1. g++ is `-O3` with vectorization and unrolling off.
`-ffp-contract=fast` leaves scalar fma selection on. `AILANG_CC` overrides
the compiler. The default is the repo `./ailang.x`.

## FX-8320, one pinned core

Measured with `/tmp/opt2-dead/ailang2.x`
(sha256 `fa9deebddf2680a3fd1d52d1b48a55121ad516ed5f45ce3591990f4730ce2109`),
not the installed compiler. Bits and mix matched both runs:
`4747321635390881792` and `1028593127784448`. g++ was timed once on this
pin, the existing `matmul_cpp`.

| | run 1 | run 2 |
| --- | --- | --- |
| g++ | 0.291 s | — |
| AILANG | 0.443 s | 0.444 s |

Before dropping the dead address store, the same pin on
`/tmp/opt2-ptr/ailang2.x`
(sha256 `dc77304f25141a7d0e2fb441e997f92cf77f1bf9f7dedee42ffc063d4e7fe940`)
was 0.464 s and 0.460 s against g++ 0.283 s. Before the induction-pointer
rule, `/tmp/opt2-fma/ailang2.x`
(sha256 `ed0aa4692a807178238281cff90275ee442331d5b8bc2bb04592ae5f12ad1f3b`)
was 1.760 s and 1.746 s against g++ 0.300 s.

g++ `tile_mul` inner loop at `main+0x120` is 17 instructions. The four
sums stay in xmm3–xmm6. Each step is four `movsd`, two pointer bumps
(`add $8` along A, `add $0x200` down B), four `mulsd`, and four `addsd`.
No `mulpd` and no `vfmadd`.

The AILANG k loop keeps the four sums in xmm2–xmm5 and `k` in r13. Two
pointers step with `k`: `add $8` along A and `add $0x200` down B. The
second row is `movsd 0x200(%r11)` and the second column is `movsd
8(%r14)`. Each product is `vfmadd231sd` from xmm0 and xmm1 into the home.
The body is 19 instructions and no nops. The address temporary
`bk = k*64+j` is not computed. The four products do not reuse a factor
already sitting in xmm.
