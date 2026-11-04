# optcheck: finding over-optimization

Three tools, all built on two compiler flags (see `Library.COptGate.ailang`):

- `-optoff=<groups>` turns optimizer rule groups off. Groups: `inline linscan regleaf fold dead homes select magic math byte scanrw skip reload`, or `all`. Each group is switched where it is armed, so turning it off takes the compiler's plain path.
- `-optlog` writes `<output>.optlog`, one line per fired rule that drops, skips or rewrites a statement: `function  +line  rule  name`. `+line` counts from the function's first line.

## When a program misbehaves

1. Rebuild it with `-optoff=all`. If it now works, the optimizer is at fault.
2. Rebuild it once per group (`-optoff=fold`, `-optoff=homes`, ...). The group whose build works holds the faulty rule.
3. Rebuild it with `-optlog` and read the lines for the failing function and that group's rules. The line names the rule, the statement and the variable.

## Census: did anything get deleted?

```bash
tools/optcheck/run_census.sh ./ailang.x programs.txt census.tsv
```

Builds every listed program twice, optimized and with every group but `inline` off, and compares each function's `syscall` instructions and memory stores (stores not addressed from `rbp` or `rsp`). A `DROP` row means the optimizer emitted fewer than the plain build, with the rules that fired in that function beside it. Only builds and disassembles, so it is safe on driver code. Needs `ndisasm` (nasm).

`whichgroup.py <compiler> <program> <function>` then shows which group's build restores the count.

## Are the off switches themselves right?

```bash
tools/optcheck/offtest.sh ./ailang.x
```

Builds the compiler with each group off and lets that compiler build the compiler again; every group should print `IDENTICAL`.
