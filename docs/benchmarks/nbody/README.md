# n-body

Five planets, one array of `{x, y, z, vx, vy, vz, mass}` at stride 56.
The literals are the Benchmarks Game solar system. `dt` is `0.01`.
Both programs offset momentum, print the starting energy, time only
`advance`, then print the energy again. Each line is

```
NBODY <steps> e0 <signed bits> e1 <signed bits> ns <ns>
```

`run.sh` pins core 1. g++ is `-O3` with vectorization off, loop
unrolling off, and complete peeling off (`-fno-peel-loops` and
`max-completely-peel-times=0`). `-fno-unroll-loops` alone still peeled
the five-iteration inner loop; that peeled binary had the same energy
bits and the same speed. `-ffp-contract=off` keeps C++ multiplies and
adds separate. `AILANG_CC` overrides the compiler. The default is the
repo `./ailang.x`.

## FX-8320, one pinned core

Measured with `/tmp/opt2-rld/ailang-div2b.x`
(sha256 `82771b7f3c2176d551b50979c50951bd7ef2d50a0a149377e2364308fdc3fc4c`,
6,041,742 bytes), not the installed compiler. That binary matches
`ailang-div2.x` and `ailang-div2c.x`. N=1000 checks the bits.
N=1000000 is the timing run.

Both energies match the peel-off g++ binary at both sizes. `e0` is
`-4628112441805714397` (`-0.16907516382852447`).

| steps | e1 |
| --- | --- |
| 1000 | -4628111993556820050 |
| 1000000 | -4628112044740627921 |

`dx2`, `dy2`, and `dz2` stay their own multiplies. `Optimize_FoldOnce`
leaves a one-use multiply out of every `Float_Add` and `Float_Sub`, so
`dist2 = dx2 + dy2` is `addsd`. The pair body uses `mulsd` and `addsd`.
`dist` and `dist3` fold into `mag = dt / (dist2 * sqrt(dist2))`. That
divide is `movsd` of `dt` into the `mag` home and `divsd` by the product
still in xmm0.

| | N=1000000 |
| --- | --- |
| g++ | 0.153 s, 0.153 s |
| AILANG | 0.316 s, 0.294 s, 0.293 s |

The AILANG pins are `taskset -c 1`, ns `316465671`, `293966838`, and
`292978653`. The g++ pair is the earlier peel-off pin. The ratio is
about 1.9×.

g++ walks the pair with `add $0x38`. Its inner body is 50 instructions,
including the compare and branch: squares and adds in xmm, one `sqrtsd`,
one `divsd`, then the velocity stores. `dt` stays in a register.
Products are overwritten once their velocity update has consumed them.

AILANG `Advance` keeps `base` in r12 and `j` in r13. `bi` is
`base + i * 56` in r11, computed once per outer `i`. `bj` is
`base + j * 56` in r14 and adds 56 when `j` steps. Position loads and
velocity updates are `movsd` / `subsd` / `addsd` on `[r11+disp]` and
`[r14+disp]`. Float homes are xmm2–xmm14: `dx`, `dy`, `dz`, `dist2`,
`m2`, `m1`, the three products, `mag`, and the three squares. xmm0 and
xmm1 are the working pair. xmm15 is the expression-FMA scratch and is
not a home. The repeating body, from the first field load through the
back edge, is 59 instructions. `dt` is still read from its stack slot
on every pair. No xmm is left for it without dropping a value the loop
still reads.
