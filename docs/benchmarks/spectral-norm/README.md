# Spectral norm

Plain port of the Benchmarks Game gcc #8 entry. One multiply-add of
`1 / ((i+j)*(i+j+1)/2 + i + 1)` with a carried sum, ten iterations.
The published answer at N=5500 is `1.274224153`.

`g++ -O3` is allowed to vectorize. The source has no SIMD intrinsics.
`run.sh` pins core 1 and checks that both programs print the same f64 bits.

```
./run.sh
```

N=100 is the fast bit check. N=5500 is the published run. The clock
wraps only the ten iterations and the final sqrt, not printing.

## FX-8320, one pinned core

Two runs, `taskset -c 1`. Bits matched both sizes, including
`1.274224153` at N=5500.

| N | g++ -O3 | AILANG |
| --- | --- | --- |
| 100 | 1.22–1.24 ms | 6.89–6.93 ms |
| 5500 | 3.39 s | 21.2–21.3 s |

`g++ -O3` left the loop scalar. The inner body is `imul`, `sar $1`,
`cvtsi2sd`, `divsd`, `mulsd`, `addsd`, with `1.0` kept in a register.
No `mulpd`. AILANG homes the carried sum in `xmm2` and the column
index in `r13`, and divides by 2 with `idiv`.
