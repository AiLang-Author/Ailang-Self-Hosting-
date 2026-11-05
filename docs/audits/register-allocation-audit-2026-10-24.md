# Register Allocation Architecture Audit

**Date:** 2026-10-24
**Repository:** `/home/bob/Ailang-Self-Hosting-`
**Branch:** `optimizer4-regalloc` @ `a6961a14`
**Compiler binary used for all listings:** `./ailang.x` (6,954,176 bytes, mtime 2026-10-22 22:29, built from `a6961a14`)
**Author:** HAL Code 9000 (automated audit)

---

## 0. Scope, method, and provenance

### 0.1 Files read, in the order requested

| # | File | Lines | Role |
|---|------|------:|------|
| 1 | `Librarys/Compiler/Compile/Modules/Optimizer/Library.COptHome.ailang` | 2610 | scan, pick, loop-homes entry point |
| 2 | `Librarys/Compiler/Compile/Modules/Optimizer/Library.COptAlloc.ailang` | 890 | `AllocTab` location table |
| 3 | `Librarys/Compiler/Compile/Modules/Optimizer/Library.COptScan.ailang` | 1599 | extra float homes, mention counting |
| 4 | `Librarys/Compiler/Compile/Modules/Optimizer/Library.COptStrength.ailang` | 1986 | induction pointers `ip0`/`ip1`, `n0`–`n3` |
| 5 | `Librarys/Compiler/Compile/Modules/Optimizer/Library.COptPin.ailang` | 499 | fused multiply-add scheduling |
| 6 | `Librarys/Compiler/Compile/Modules/Optimizer/Library.COptAddr.ailang` | 1335 | second induction-pointer mechanism |
| 7 | `Librarys/Compiler/Compile/Modules/Optimizer/Library.COptMath.ailang` | 1091 | binary math, LEA, immediate fusion |
| 8 | `Librarys/Compiler/Compile/Modules/Library.CCompileFunc.ailang` | ~1700 | prologue/epilogue, `is_leaf`, may-clobber |
| 9 | `Librarys/Compiler/Compile/Modules/Library.CCompileStmt.ailang` | — | `CompileStmt_While`, loop rotation |

Supporting files read for context: `Library.CCompilerOptimizer.ailang` (fixed-pool declarations),
`Library.COptBranch.ailang` (`TryBranchConditionBack`), `Library.COptStride.ailang`
(`PickByteBase`, `rcx_on`), `Library.COptLocal.ailang`, `CodeEmit/Library.CEmitCoreArch.ailang`.

### 0.2 Name normalisation

The task brief used mnemonic names; the source uses different ones. Mapping:

| Brief name | Actual field |
|---|---|
| `int_namerrrr13` | `LoopHome.int_name` → **r13** |
| `acc_namerrrr12` | `LoopHome.acc_name` → **r12** |
| `flt_namexxxxmm2` | `LoopHome.flt_name` → **xmm2** |
| "n0-n3 named dereference result slots" | `LoopHome.n0_*` … `LoopHome.n3_*` (confirmed, exact names) |
| "PinDefer 4-slot batching" | `PinDefer.k0..k3, a0..a3, b0..b3, c0..c3, s0..s3` (confirmed, 4 slots) |

### 0.3 Verification method — and one important caveat

Every runtime claim below was verified by compiling with `./ailang.x -asm <src> <out>` and
running the produced ELF, **and** by byte-scanning the produced ELF's PT_LOAD text segment
directly with `readelf` + Python, because:

> **C9 (CONFIRMED, tooling): the `-asm` listing silently omits the `sub rsp, imm32`
> frame-allocation instruction.** This nearly produced a false-positive "missing stack
> frame" finding during this audit. Before writing this report I re-derived every
> prologue from the raw bytes. Anyone using `-asm` listings for stack-frame or
> prologue work must not trust them.

Proof — compressed listing vs. raw bytes for `Function.K3` from repro `leaf.ailang`:

```
; -asm listing (WRONG - frame allocation is missing)
K3:
; compiler: frame
    55 PUSH rbp
    48 89 E5 MOV rbp, rsp
    53 PUSH rbx              <-- jumps straight to the callee-saves
    41 54 PUSH r12
```

```
# raw bytes of the same function (CORRECT - 48 81 EC 60 00 00 00 is present)
fn#2 prologue@0x04d: 55 48 89 e5 48 81 ec 60 00 00 00 53 41 54 48 89
                     ^push rbp ^mov rbp,rsp ^sub rsp,0x60  ^push rbx ^push r12
```

`Emit_SubRspPatchable` is emitted under `Listing_Compiler("frame")` but its bytes are never
stitched into the listing buffer, so the listing renders the prologue with a hole in it.
**Finding C9 stands on its own** and is listed in §11.

### 0.4 What was *not* verifiable

Float-path runtime validation was blocked by an unrelated, pre-existing defect: `Float_ToInt`
returns `0` for every input. Repro `t4.ailang`:

```ailang
Function.Two { Output: Float Body: { ReturnValue(2.5) } }
SubRoutine.Main {
    PrintMessage("a=") PrintNumber(Float_ToInt(4.7))       PrintMessage("\n")
    x = 1.5  y = 2.5
    PrintMessage("b=") PrintNumber(Float_ToInt(Float_Add(x, y)))      PrintMessage("\n")
    PrintMessage("c=") PrintNumber(Float_ToInt(Float_Add(1.5, Two()))) PrintMessage("\n")
    PrintMessage("d=") PrintNumber(Float_ToInt(Two()))      PrintMessage("\n")
    ProcessExit(0)
}
RunTask(Main)
```

```
a=0          <- expected 4
b=0          <- expected 4
c=0          <- expected 4
d=0          <- expected 2
```

`PrintNumber` itself is fine (`PrintNumber(4)` prints `4`). This is **outside** the audited
area (a float-conversion/intrinsic problem, not a register-allocation problem) but it is
**flagged here as a blocker for all future float-home testing**. All float-home conclusions in
this report are therefore static-analysis only.

---

## 1. `Library.COptHome.ailang` — scan, pick, and the loop-homes entry point

### 1.1 Per-candidate records: `Optimize_HomeWalk` / `Optimize_HomeTouch`

`LoopHome.recs` is one `Allocate(3072)` buffer of **64 records × 48 bytes**
(`Optimize_HomeRec`, COptHome:190, multiplies the index by 48). Record layout:

| Offset | Field | Meaning |
|-------:|-------|---------|
| 0  | `name` | identifier string (AST-owned, not copied) |
| 8  | `loads` | read count |
| 16 | `stores` | write count |
| 24 | `fops` | *float* write count (only when the RHS is `Float_Add/Sub/Mul/Div`) |
| 32 | `selfn` | self-referential updates (`x = ... x ...`) |
| 40 | `seeds` | writes whose RHS is a bare `Dereference(...)` |

`Optimize_HomeTouch(name, is_store, is_float, is_seed)` (COptHome:554) does a **linear scan**
over `LoopHome.count` comparing names, creating a zeroed row on first sight (hard cap 64 rows,
`ReturnValue(0)` past that), then increments. Populating the five counters is the entire job of
the scan phase — it records no liveness, no intervals, and no frequencies.

`Optimize_HomeWalk(node)` (COptHome:650) is the AST recursion. It has three important
*blocking* behaviours:

1. `Optimize_HomeBlockNode(t)` lists 12 node types that immediately set `LoopHome.blocked = 1`
   and abort the walk: `WHILE, FOR_EVERY, UNTIL, TRY, LOOP_MAIN, LOOP_ACTOR, LOOP_START,
   LOOP_SHADOW, DEFER, WITH_CONTEXT, EVERY_INTERVAL, POINTER_FIELD_ASSIGN`. **A nested loop
   anywhere in the body kills all homes for the outer loop.** This is the direct cause of the
   cross-loop-boundary overhead the Fannkuch motivation describes.
2. An `ASSIGNMENT` whose target is a pointer (`AST_GetData2(node) != 0`) sets `blocked`.
3. A `CALL` that is neither home-safe (`Optimize_HomeCallOk`) nor a known function sets
   `blocked`. A *known* non-home-safe call instead sets `LoopHome.has_call = 1`, and its
   children are still walked (so a user call nested in an argument is counted).

`Optimize_HomeWalk` also *skips* the store count when the RHS is the literal `0`
(`skip_store`), which is why zero-initialised variables can still become homes.

### 1.2 `Optimize_HomePick` — scoring (COptHome:743)

Three separate passes over the same 64-row table, all with hard-coded tie-break rules:

**Pass 1 — float home (`xmm2`).** Requires `loads>0 && stores>0 && fops>0 &&
stores == fops+seeds`, `LoopHome.no_float == 0`, and a scope slot (`Scope_Resolve` offset < 0
for typed names, or `resolve_type == 0` for fresh names, which are then materialised through
`Optimize_EnsureSlot`). Two vetoes: `Optimize_ConstTempSkip` (when `loads==stores` and
`selfn==0`) and `Optimize_FltFieldUpd` (exactly the "load, one fp op, store back" shape —
`seeds==1, fops==1, stores==2, loads==2, selfn>0`). Ranking is lexicographic on
`(loads, selfn, fops)`.

**Pass 2 — integer home (`r13`).** Requires `fops == 0`, `loads>0 && stores>0`, a scope slot,
and `off < 0`. Score is `loads+stores`, strict `>` (first wins ties).

**Pass 3 — accumulator (`r12`).** Only runs if an integer home was found, and requires
`fops == 0`, `loads>0`, `stores>0`, `selfn > 0`, a different name than `int_name`, and a scope
slot. Ranking is lexicographic on `(selfn, loads+stores)`.

Then: `if (LoopHome.flt_name != 0) Optimize_HomePickExtras()` (COptHome:898) — extra float
homes are only taken **after** a primary float home exists.

### 1.3 `Optimize_LoopHomes` — the top-level entry (COptHome:1016)

Exact ordering (this ordering *is* the architecture):

```
 1  Optimize_AllocReset()                          wipe the location table
 2  ~90 field resets on LoopHome                   int/flt/acc/der/ip/pin/tab/... -> 0
 3  Optimize_AliasClearAll / PtrClearAll / IpClear
 4  LoopHome.recs = Allocate(3072) if null
 5  Optimize_HomeWalk(condition)
 6  Optimize_HomeWalk(body)
 7  if LoopHome.blocked == 1 -> zero every home and RETURN 0        <-- early exit Q
 8  if Optimize_EdgeBad(condition, body) == 0 -> LoopHome.has_call = 0
 9  LoopHome.body = body                                           <-- SET POINT
10  LoopHome.cond = condition                                      <-- SET POINT
11  Optimize_HomePick()                     int=r13, flt=xmm2, acc=r12, + extras
12  Optimize_AliasClearAll; hold_on = hold_name = 0
13  have = any of (int_name, flt_name, acc_name, ExtraAny())
14  Optimize_ScanTable(body)
15  Optimize_PickByteBase(body)             sets tab_on/tab_name/tab_off  (r14 record base)
16  Optimize_PickStride(body)               sets st_on / st_base
17  have |= tab_on || st_on
18  if have == 0 -> RETURN 0                                      <-- early exit R
19  Optimize_ScanBody(body) / ScanCondTemps / ScanLimit        (rbx limit)
20  Optimize_PickInvariant(condition, body)
21  Optimize_FindStep(body)                 iv_step / iv_at
22  Optimize_NoteIv(condition, body)
23  Optimize_PickDerived(body)              der_on -> r11
24  Optimize_PickIp(condition, body)        ip0/ip1 (mode 0) -> r11 then r14
25  Optimize_PickAddr(condition, body)      ip0/ip1 (mode 1) - only if both still off
26  Optimize_PickReload(body)
27  Optimize_NoteProd()                     prod_on -> r11
28  Optimize_PickKmul(condition, body)      kmul -> r11
29  Optimize_NoteRbxScratch(condition, body)
30  Optimize_AllocPublish()                 builds AllocTab, then AllocExtend (r11/r14)
31  RETURN 1
```

**`Optimize_EdgeBad` (COptHome:1003)** is the `has_call` gate. It returns `1` when a
home-clobbering call can reach the loop back edge or a `break`. `Optimize_Flow` classifies each
statement: `0` falls through clean, `1` falls through with a clobbering call, `2` always
returns, `3` hits `ContinueLoop`/`ExitLoop`. `Return` code `2` is *not* fatal because the frame
dies; code `3` **is** fatal because homes are spilled at a break. So `has_call` is cleared when
every clobbering call sits on a path that ends in `Return`.

This is a **sound and clever** design: a call immediately followed by `Return` cannot corrupt a
home, because nothing reads the home afterwards. It is also the reason `has_call == 0` is a
*weaker* condition than "no calls", which matters in §8.

---

## 2. `Library.COptAlloc.ailang` — the location table

**`AllocTab`** is `Allocate(1024)` = **32 rows × 32 bytes**: `name`, `class`, `register`,
`frame offset`. Class `1` = GPR, class `2` = XMM. Register numbers are hardware numbers.
This is the "where is this name *right now*?" map — the frame remains the permanent home of
every local.

Key operations:

* `Optimize_AllocAdd(name, cls, reg, off)` (COptAlloc:99) — appends unless the name is null,
  the table is full (`n >= 32`), or the name is already present (**first row wins**, and
  `Optimize_Loc` scans front-to-back, so this is load-bearing).
* `Optimize_Loc(name)` (COptAlloc:121) — linear lookup; on hit sets
  `AllocTab.hit_class / hit_reg / hit_off`. Every emission site consults this.
* `Optimize_AllocPublish()` (COptAlloc:235) — **this is the phase boundary**. It copies the
  existing rows (the ones `Optimize_InstallFlt` published during `HomePickExtras`) into a
  staging area at **row `20 + i`**, calls `AllocReset`, re-adds the primary homes in a fixed
  order, then re-adds the staged rows, then calls `Optimize_AllocExtend()`:

```ailang
Optimize_AllocReset()
Optimize_AllocAdd(LoopHome.int_name, 1, 13, LoopHome.int_off)        // r13
Optimize_AllocAdd(LoopHome.acc_name, 1, 12, LoopHome.acc_off)        // r12
if LoopHome.der_on == 1 : AllocAdd(der_name, 1, 11, der_off)         // r11
if lim_on == 1 && rbx_free == 1 : AllocAdd(lim_name, 1, 3, lim_off)  // rbx
Optimize_AllocAdd(LoopHome.flt_name, 2, 2, LoopHome.flt_off)         // xmm2
<replay staged rows 20..>
Optimize_AllocExtend()
```

**Row-20 staging has a hard invariant:** `saved = AllocTab.n` at publish time must be ≤ 12 or
the replay writes past row 31 and off the end of the 1024-byte allocation. Today the only
publish-time writer is `Optimize_InstallFlt`, which scans xmm3..xmm14 → at most 12 rows.
**S2** in §11 records this as a SUSPECTED latent overflow with no assert.

**`Optimize_AllocExtend` (COptAlloc:442)** — the "extra GPR homes" feature. It requires at
least one of `int_name`/`acc_name`, computes `free11 = Optimize_AllocRegFree(11)` and
`free14 = AllocRegFree(14)`, and **bails entirely if `Optimize_AllocBad(cond)==1` or
`AllocBad(body)==1`**. `Optimize_AllocBad` (COptAlloc:273) flags `AST.INLINEASM` anywhere, and
any `CALL` that is not `Optimize_HomeCallOk` — regardless of reachability. So an extra integer
home is *strongly* guarded (stricter than `has_call`).

It then picks the best and second-best candidates from the scan table (loads>0, fops==0, not
already held by `Optimize_AllocHeld`, live in or stored) and assigns:

```ailang
if free11 == 1 { AllocAdd(best, 1, 11, ...)
                 if free14 == 1 && second != 0 { AllocAdd(second, 1, 14, ...) } }
else           { AllocAdd(best, 1, 14, ...) }
```

`Optimize_AllocRegFree` (COptAlloc:377) is the **anti-collision arbiter for r11/r14** and is the
single most important function in this file:

* **r11 is busy** if `der_on || kmul_on || prod_on || ip0_reg==11 || ip1_reg==11`
* **r14 is busy** if `tab_on || st_on || ip0_reg==14 || ip1_reg==14 ||
  WritesR14(cond) || WritesR14(body) || AllocMemR14(cond) || AllocMemR14(body)`

`AllocMemR14` exists because the memory emitter will do `MOV r14, base` for **any** scaled qword
whose base is not already the parked table — `WritesR14` only notices identifier bases.

Emission/cache plumbing: `Optimize_AllocGprIn` loads r11/r14 at loop entry (skipping the derived
name, which `Optimize_EmitDerived` handles), `AllocGprOut` writes them back at exit,
`AllocXmmIn`/`AllocXmmOut` do the same for xmm3–xmm14, `Optimize_LocLoad`/`Optimize_LocStore`
turn a `Loc` hit into a move. **`LocLoad` handles reg 13, 12, 11, 14 and class-2; `LocStore`
handles 13, 12, 11, 14 and class-2. Neither handles reg 3 (rbx), so an rbx row falls through to
the frame path — which is correct, because rbx is a *cache* of the frame slot, not a home.**

---

## 3. `Library.COptScan.ailang` — extra float homes

`Optimize_ExtraTake` (COptScan:362) is the float analogue of the integer picker. It gates on
`Optimize_FltRoom()` (fewer than 12 *permanent* extras — offset `< 0` means permanent, offset
`0` means a borrow), skips names already taken (`Optimize_NameTaken`), and applies the identical
shape test as `HomePick`'s float pass (`stores == fops+seeds`, `ConstTempSkip`, `FltFieldUpd`).
Ranking: `(loads, selfn, fops)`.

`Optimize_HomePickExtras` (COptScan:453) is a 12-iteration loop:

```ailang
if LoopHome.flt_name == 0 { ReturnValue(0) }
n = 0
WhileLoop LessThan(n, 12) {
    IfCondition EqualTo(Optimize_ExtraTake(), 0) ThenBlock: { n = 12 }
    n = Add(n, 1)
}
```

`Optimize_InstallFlt(name, off)` (COptHome:232) walks `reg = 3..14` and takes the first
register where `Optimize_ExtraXmm(reg) == 0`, adding a class-2 row immediately. **The row is
visible before publish** — that is how `FltSlot` can already return xmm3..xmm14 during the
window between `HomePick` and `AllocPublish`.

`Optimize_Mentions` / `Optimize_CountWalk` (COptScan:55/82) are plain AST walks counting
identifier occurrences; they are the frequency proxy used by `PinWorth` (`Mentions >= 3`) and by
`AddrOk` (`block_n == func_n`, `block_n >= 2`).

---

## 4. `Library.COptStrength.ailang` — induction pointers and the `n0`–`n3` slots

Three distinct mechanisms live in this file. They are frequently confused; the audit separates
them explicitly.

### 4.1 Cursor-affine pointer groups (`ip0`/`ip1`, `mode == 0`)

`Optimize_IpIndex(node, depth)` (COptStrength:941) symbolically differentiates an address
expression with respect to the loop cursor `int_name`, producing
`LoopHome.ip_coeff` (coefficient), `ip_add` (constant), `ip_inv` (invariant addend, validated
by `Optimize_IpInvOk`). It follows single-assignment temporaries up to depth 4 (total depth 6)
via `Optimize_IpRhs` + `Optimize_AssignCount(body, name) == 1`.

`Optimize_IpAddrSides` then resolves the base: `via = 2` when the base is `acc_name`, `via = 3`
when it is a frame local (`Optimize_FrameOff`), refusing the cursor itself and any base the loop
assigns.

`Optimize_IpCommit(name)` (COptStrength:1299) is the allocator. Its guards, in order:

```
coeff in [1, 1048576] ; iv_step <= 1048576
bump = coeff * scale * iv_step   must be >= 1 and fit32
addk must fit32
  -> reuse ip0 if (base, coeff, scale) match
  -> else reuse ip1 if (base, coeff, scale) match
  -> else: require Optimize_IpNameFree() (an n0..n3 slot must be free)
           reg = Optimize_IpTakeReg()          <-- register choice
           install into ip0, else ip1, else give up
           disp = 0
  reused slot: disp = (iv_delta + (addk - anchor_add)) * scale
```

**`Optimize_IpTakeReg` (COptStrength:1226) is the r11/r14 arbiter for induction pointers:**

```ailang
used11 = (ip0_on && ip0_reg==11) || (ip1_on && ip1_reg==11)
used14 = (ip0_on && ip0_reg==14) || (ip1_on && ip1_reg==14)
if !used11 && !der_on -> 11
if !used14 && !tab_on -> 14
return 0
```

Note it consults `der_on` and `tab_on` but **not** `kmul_on` / `prod_on`. That is safe only
because of ordering: `PickIp` (step 24) runs before `NoteProd` (step 27) and `PickKmul`
(step 28), and both of *those* re-check `ip0_reg`/`ip1_reg` before claiming r11 (see 4.3).

### 4.2 The `n0`–`n3` "named dereference result" slots

`Optimize_IpNote(name, reg, disp)` (COptStrength:1260) fills the first free slot of
`n0..n3` with `(name, reg, disp)`. This is purely a **name → (base register, displacement)**
mapping: it says "the value the source calls `name` is already addressable as `[reg+disp]`".
`Optimize_IpMatchName(name)` reads it back into `LoopHome.ip_hit_reg / ip_hit_disp`, and the
consumer emits a memory operand instead of a load. `Optimize_IpNameFree` simply checks that at
least one of the four slots is off; there are exactly four.

`Optimize_IpMatch(node)` (COptStrength:1746) is the dispatcher: identifier → `IpMatchName`,
otherwise → `IpAddr` + `IpMatchGroup` (a live re-derivation of the displacement from the
current `iv_delta`, which is how a pointer stays correct at an arbitrary statement index).

### 4.3 The product cache (`prod_on`, also r11)

`Optimize_NoteProd` (COptStrength:575) caches `int_name * prod_c` in **r11**. It is the most
defensively guarded mechanism in the file:

```ailang
if has_call == 1                                      -> bail
if int_name == 0 || iv_step < 1 || !fit32(iv_step)    -> bail
if der_on == 1                                        -> bail
if ip0_on && ip0_reg == 11                            -> bail   <-- defers to §4.1
if ip1_on && ip1_reg == 11                            -> bail
if TreeHasAsm(body) || TreeHasAsm(cond)               -> bail
if !LiveIn(int_name, cond, body)                      -> bail
```

`Optimize_TryProdUse` then turns `Multiply(int_name, prod_c)` into `MOV rax, r11`, and
`Optimize_TryHomeAssign` bumps it with `Optimize_EmitProdBump()` when the cursor step matches.

### 4.4 `Optimize_TryIpDef` / `Optimize_TryIpDrop`

```ailang
Function.Optimize_TryIpDef  { if LoopHome.active == 0 { ReturnValue(0) } ReturnValue(Optimize_IpMatchName(name)) }
Function.Optimize_TryIpDrop { <same active gate>; return 1 if name is one of d0..d3 }
```

`TryIpDef` intercepts an assignment target that is already a named dereference (so the
assignment is never emitted). `TryIpDrop` suppresses the address temporaries `d0..d3`
(`Optimize_IpPickDrops`, COptStrength:1589) — "the address temporary is never computed; its
reads are pointer disp".

---

## 5. `Library.COptPin.ailang` — fused multiply-add scheduling

`PinDefer` is a **4-slot** batch (`k0..k3, a0..a3, b0..b3, c0..c3, s0..s3`);
`Optimize_PinPush` (COptPin:266) flushes when the batch is full. The multi-pass design means a
`home = home ± a*b` can be emitted as `mulsd` on one pass and `addsd/subsd` on another, which
lets the last use of a factor be a destructive `mulsd` instead of a copy.

Register choice for pins is `Optimize_PinFree`, restricted by `Optimize_PinTaken`
(COptPin:22):

```ailang
xmm < 2  -> taken          (xmm0/xmm1 are scratch/hold)
xmm > 14 -> taken          (xmm15 reserved)
xmm == 2 -> taken if LoopHome.flt_name != 0
xmm >= 3 -> taken if Optimize_ExtraXmm(xmm)      <-- defers to the AllocTab extra homes
+ taken if already in a PinDefer record
```

So pinning starts at **xmm6** (`Optimize_PinRoom` scans `xmm = 6..14`) and therefore can never
steal xmm2–xmm5 (the named float home plus up to three extras). Worth/room/keep chain:

* `Optimize_PinWorth` — keep only if the pin already exists, or the operand is an identifier
  mentioned ≥ 3 times in `LoopHome.body`.
* `Optimize_PinRoom` — refuse if `pin_n + need > 4` or fewer than `need` xmm6–14 are free.
* `Optimize_PinKeep` — load once with `X86_MovsdPtr(xmm, reg, disp)`, record `uses left = -1`.
* `Optimize_PinReuse` — the entry point; note it goes through `Optimize_IpMatch` to get
  `ip_hit_reg/disp`, so **pinning is layered directly on top of the §4 induction-pointer
  system** and inherits its correctness.

---

## 6. `Library.COptAddr.ailang` — the second induction-pointer mechanism

The brief asked specifically whether this **overlaps or conflicts** with §4's `n0`–`n3` system
for the same variable in the same loop. Answer: **it cannot. It is structurally excluded.**

`Optimize_AddrInstall(name, rhs)` (COptAddr:316) reuses the **same fields** as §4.1 —
`ip0_*` / `ip1_*` — with a discriminator:

```ailang
LoopHome.ip0_on   = 1
LoopHome.ip0_mode = 1          // 1 = "address home", 0 = "cursor-affine group"
LoopHome.ip0_reg  = reg
LoopHome.ip0_bump = bump
LoopHome.ip0_rhs  = rhs
LoopHome.ip0_aname = name
```

`Optimize_AddrFind` only matches slots whose `mode == 1`. §4.1's code never reads or writes
`mode`, and it keys on `ip0_base` (which `AddrInstall` never sets), so a mode-1 slot is
invisible to it.

The exclusion is enforced twice:

1. **`Optimize_PickAddr` bails outright if any `ip` slot is already on:**

```ailang
IfCondition EqualTo(LoopHome.ip0_on, 1) ThenBlock: { ReturnValue(0) }
IfCondition EqualTo(LoopHome.ip1_on, 1) ThenBlock: { ReturnValue(0) }
```

   and `PickIp` (step 24) runs *before* `PickAddr` (step 25). First come, first served —
   §4.1 always wins when both shapes are present.

2. **`Optimize_AddrOk` excludes every name §4 might own:** `int_name`, `acc_name`,
   `der_name`, and `Optimize_IpIsNoted(name)` (i.e. anything in `n0..n3`). Since §4.1 always
   calls `Optimize_IpNote` on commit, `IpIsNoted` is a superset guard for §4's name space.

**Verdict: no overlap, no conflict, for the same variable in the same loop — CONFIRMED (C5).**
The residual coupling is on the *register*, not the *name*: both use r11/r14 via
`Optimize_IpTakeReg`, which is a single shared arbiter, so they also cannot collide on registers.

`PickAddr`'s other guards: `Hw.level >= 2`, `has_call == 0`, no inline asm, `body` must be a
`BLOCK`, and it refuses when `Optimize_AddrScaled(body)` matched (a scaled dereference already
writes r14).

`Optimize_AddrLoad` (COptAddr:371) is the payoff: `X86_MovRaxIp(ip_hit_reg, ip_hit_disp)` — a
single `MOV rax, [reg+disp]` for a whole `Dereference(Add(ptr, ...))` expression.

---

## 7. `Library.COptMath.ailang` — immediate fusion, LEA, and rbx-leaf

### 7.1 Ordering inside `Optimize_BinaryMathOp` (COptMath:874)

```
880  nargs != 2                                -> 0
886  if op == "Multiply" && TryProdUse(...)     -> 1    (r11 product cache, §4.3)
897  lea_hit = Optimize_TryLea(op, arg0, arg1)          <-- LEA FIRST
903      lea_hit == 2 -> 0        (emitted then failed)
904      lea_hit == 1 -> 1
906  if type1 == NUMBER:                                <-- IMMEDIATE FUSION SECOND
913      imm_fast for Add/Subtract when imm fits int32
928      imm_fast for Multiply when imm fits int32 and !IsPow2  (3-operand IMUL)
940      if imm_fast: LoadToRax(arg0); Emit_AddRaxImm32 / Emit_SubRaxImm32 / Emit_ImulRaxImm32
948  save_rbx = (lim_on==1) || (ihold_reg==3); if save_rbx: Emit_PushRbx()   <-- HOOK
953  leaf_hit = Optimize_TryRbxLeaf(...)  -> wrap with Emit_PopRbx on every exit
967  PATH A (right simple) / PATH B (left simple) / PATH C (both complex)
1030 emit_result = Optimize_EmitOperation(...)
1031 if save_rbx: Emit_PopRbx()
1032 ReturnValue(emit_result)
1036 ReturnValue(Optimize_EmitOperation(node, func_name))   <-- UNREACHABLE
```

### 7.2 Are the immediate-fusion fast paths still present and correctly ordered?

**CONFIRMED (C6): yes, present, and correctly *after* `TryLea` and *before* the `save_rbx`
window.** Provenance: `git log -S imm_fast` yields exactly the two session commits
`5ca0027a` ("Emit direct immediate Add/Subtract outside loop homes too") and `51a300d4`
("Emit direct IMUL rax,rax,imm for non-power-of-2 constant multiply"), both ancestors of
`HEAD`.

`TryLea` only fires when a **loop home** is on one side (`Optimize_LeaReg` requires
`Optimize_HomeReg(...) != 0`), so the two paths are disjoint: `TryLea` owns
`Add(other, home±disp)`, immediate fusion owns the plain `x ± 5` / `x * 3` case that would
otherwise be shuttled through rbx for nothing. Live proof from `leaf.ailang` /
`Function.K3` (`y = Add(x, 1)`):

```
    48 83 C0 01 ADD rax, 1                  <- fused immediate, no rbx, no push/pop
```

`Optimize_SkipRbx` (COptMath:832) is the complementary optimisation: it tells PATH A not to
load rbx at all for constant shifts, power-of-two multiplies, and resolvable power-of-two
divides/magic multiplies.

### 7.3 Dead code

`ReturnValue(Optimize_EmitOperation(...))` at COptMath:1036 is unreachable — every path above
returns. Harmless today; it is a stale second copy of the real emit at line 1030. (See S3.)

---

## 8. `Library.CCompileFunc.ailang` — prologue/epilogue, `is_leaf`, may-clobber

### 8.1 The actual prologue and epilogue

`CompileFunc_Function` (CCompileFunc:107), in emission order:

```
Emit_PushRbp(); Emit_MovRegReg(RBP, RSP)
... local counting ...
is_leaf = (CompileFunc_HasCalls(body_node) == 0)
... float constant plan, frame size arithmetic ...
if is_leaf == 0 && stack_space > 0 { frame_patch_pos = Emit_SubRspPatchable(stack_space) }
if is_leaf == 0 { Emit_PushRbx(); Emit_PushR12() }        <-- ONLY rbx and r12
... arg spill to [rbp-8], [rbp-16], ... RDI RSI RDX RCX R8 R9 ...
...
Emit_MarkLabel(return_label)
if is_leaf == 0 { Emit_PopR12(); Emit_PopRbx() }
Emit_MovRspRbp(); Emit_PopRbp(); Emit_Ret()
```

The file header documents this as intentional (CCompileFunc:89-99):

> `This prologue saves RBX and R12 only. R13, R14, and R11 are scratch.`
> `R15 is the pool base and is not saved here. RBP is the frame pointer.`

**There is no `sub rsp` for leaf functions** — they use the System V 128-byte red zone. That is
correct *provided* nothing calls out, which `HasCalls == 0` guarantees. Verified at byte level
(repro `leaf.ailang`):

```
fn#0 (Function.K,  0 CALL nodes -> is_leaf) : 55 48 89 e5 | 48 c7 c0 07 00 00 00 ...
                                              ^push rbp  ^mov rbp,rsp ^mov rax,7  (NO sub rsp)
fn#1 (Function.K2, 0 CALL nodes)            : 55 48 89 e5 | 48 89 f8 48 89 45 f8 ...
fn#2 (Function.K3, has Add(x,1) CALL)       : 55 48 89 e5 | 48 81 ec 60 00 00 00 | 53 41 54 ...
```

### 8.2 `is_leaf` detection — CONFIRMED defeated by operators (C8)

`CompileFunc_HasCalls` (CCompileFunc:1641) returns `1` for **any** `AST.CALL` node. In this
frontend every builtin operator is a `CALL` node (`Add`, `LessThan`, `Multiply`, …), which is
why `Optimize_BinaryMathOp` takes a `CALL` node. Consequence:

* `Function.K  { ReturnValue(7) }` → leaf → 4 bytes of prologue.
* `Function.K2 { y = 9  ReturnValue(y) }` → leaf → red-zone local.
* `Function.K3 { y = Add(x, 1)  ReturnValue(y) }` → **not** a leaf → `sub rsp, 0x60` +
  `push rbx` + `push r12` for a single `ADD rax, 1`.

So the leaf fast path fires only for bodies with **zero operator calls** — i.e. for exactly the
functions that need it least. The remaining trivially-leaf shapes (`ReturnValue(x op y)` over
parameters/fit32 literals) are already intercepted *earlier*, before the prologue, by the
"reg leaf" path (`Optimize_RegLeafExpr` → `Optimize_EmitRegLeaf`, CCompileFunc:186), which
emits **no frame at all**:

```
clob binary, Id @0x008: 55 48 89 e5 | 48 89 f8 | 90*8 | e9 03 00 00 00
                        ^push rbp   ^mov rax,rdi        ^jmp (no sub rsp, no callee-saves)
```

Net effect: the `is_leaf` mechanism is **reachable but nearly vestigial**. Performance finding,
not a correctness finding.

### 8.3 The rbx/r12 may-clobber mechanism — located, verified, complete (C3)

The brief said this was "resolved" and asked for the actual diff/commit. It is
**commit `69d9e590`** — *"Fix rbx clobber in BinaryMathOp and IndexDead over-optimization"*
(Thu Oct 22 2026), whose message states:

> Bug 1: BinaryMathOp paths (TryRbxLeaf, PATH A LoadToRbx, PATH B MovRbxRax, PATH C LoadToRbx)
> clobber rbx when it holds the loop limit (lim_on=1) or a parked value (ihold_reg=3).
> Wrap all paths with conditional PUSH/POP rbx.

The diff introduced `save_rbx` immediately after the immediate-fusion block and added
`Emit_PopRbx()` to **every** exit of the four paths (including the two failure paths that
previously returned without emitting anything, and the `Emit_PopRax()` failure path in
PATH C). That code is present verbatim at `HEAD` (COptMath:946-1032) and is quoted in §7.1.

**Coverage audit of the hook (is it complete?).** Every early-return in
`Optimize_BinaryMathOp` was checked for a matching `Emit_PopRbx`. The returns that occur
*before* the `save_rbx` point at line 948 are:

| Return site | Writes rbx? | Verdict |
|---|---|---|
| `nargs != 2` (880) | no | safe |
| `TryProdUse` (886) | no — emits `MOV rax, r11` | safe |
| `TryLea` 0/1/2 (902-904) | no — `X86_LeaRaxHome` is `LEA rax,[home+rax+disp]` | safe |
| `imm_fast` (940-946) | no — `ADD/SUB/IMUL rax, imm32` | safe |

`imm_fast` calls `Optimize_LoadToRax(arg0)` before the hook, but any nested
`Optimize_BinaryMathOp` reached from there re-computes `save_rbx` itself and pushes/pops
symmetrically, so the nesting is balanced. **No gap found in the rbx hook — CONFIRMED closed.**

**r12** needs no hook at all: it is callee-saved under SysV *and* every generated prologue
pushes it (see §8.1), so any AILang or C callee preserves it.

### 8.4 The r13/xmm may-clobber hook — correct, but load-bearing on a non-local invariant

The *real* may-clobber hook for loop homes is
`Optimize_HomesClobber` / `Optimize_NodeClobbers` (COptScan:469/508), consumed by
`Optimize_HomeCallSave` / `Optimize_HomeCallLoad` (COptHome:2363/2384) from
`CompileFunc_UserCall`:

```ailang
Function.Optimize_HomeCallSave { if LoopHome.active == 1 {
    keep = Optimize_HomesClobber(callee)
    if keep == 1 {
        if int_name != 0 { Emit_HomeMove(1,0); Emit_MovRbpOffsetRax(int_off) }   // r13 -> frame
        if flt_name != 0 { Emit_HomeMove(5,0); Emit_MovRbpOffsetRax(flt_off) }   // xmm2 -> frame
        Optimize_AllocXmmSave()                                                // xmm3..14
    } } }
```

`HomesClobber` is a memoised (`OptState.clean_cache`), cycle-guarded
(`clean_visit`, `clean_depth > 16` → *assume clobber*) transitive walk of the callee's
reachable bodies, returning 1 when anything in them writes r13/xmm2–xmm5 or contains a nested
`WhileLoop`/`InlineAsm`.

**Verified firing correctly in both directions (C4)** — repro `r13probe.ailang`, `Outer`'s body
calls `Inner`, which has its own loop:

```ailang
Function.Inner { Input: n: Integer Output: Integer
    Body: { i = 0  acc = 0
            WhileLoop LessThan(i, n) { acc = Add(acc, i)  i = Add(i, 1) }
            ReturnValue(acc) } }
Function.Outer { Input: n: Integer Output: Integer
    Body: { i = 0  acc = 0
            WhileLoop LessThan(i, n) { acc = Add(acc, Add(Inner(3), i))  i = Add(i, 1) }
            ReturnValue(acc) } }
SubRoutine.Main { PrintMessage("outer4=") PrintNumber(Outer(4)) PrintMessage("\n") ProcessExit(0) }
RunTask(Main)
```

```
$ ./r13probe
outer4=18                     # correct: (3+0)+(3+1)+(3+2)+(3+3) = 18
```

`Outer` listing — note the **spill of r13 to the frame and reload after the call**:

```
; r13probe.ailang:22    acc = Add(acc, Add(Inner(3), i))
    4C 89 E0             MOV rax, r12          ; left operand -> stack
    50                   PUSH rax
    48 C7 C0 03 00 00 00 MOV rax, 3
    48 89 C7             MOV rdi, rax
    4C 89 E8             MOV rax, r13
    48 89 45 F0          MOV [rbp+-16], rax    <-- r13 spilled (HomesClobber said "dirty")
    E8 23 FF FF FF       CALL Inner
    50                   PUSH rax
    48 8B 45 F0          MOV rax, [rbp+-16]
    49 89 C5             MOV r13, rax          <-- r13 reloaded
    58                   POP rax
```

and the negative case — repro `clob.ailang`, where the callee is provably clean
(`Body: { ReturnValue(x) }`), correctly emits **no** spill at all:

```
; clob.ailang:13    acc = Add(acc, Id(i))
    4C 89 E8             MOV rax, r13
    48 89 C7             MOV rdi, rax
    E8 91 FF FF FF       CALL Id               <-- no r13 spill/reload: correct
    49 01 C4             ADD r12, rax
```

### 8.5 **C2 — CONFIRMED: r13 is a callee-saved register that no function ever saves**

SysV AMD64 callee-saved set: `rbx, rbp, r12, r13, r14, r15`. The prologue saves only `rbx`
and `r12`, and the file header declares the deviation:

> `R13, R14, and R11 are scratch.`

`r11`/`r14` genuinely are caller-saved, so treating them as scratch is free. **`r13` is not.**
The compiler writes it as the primary integer loop home in essentially every loop, and:

* the prologue does not push it (§8.1, confirmed at byte level),
* the only in-tree save mechanism is the *caller-side* spill in `Optimize_HomeCallSave`, gated
  on the memoised `HomesClobber` analysis,
* and — decisively — **another part of the same compiler treats r13 as callee-saved.**
  The library body of `PrintNumber`, emitted inline by `ailang.x` itself, does:

```
r13probe ELF, text offset 164/165:   41 55   PUSH r13
                                     41 56   PUSH r14
                     offset 210/211: 41 5E   POP r14
                                     41 5D   POP r13
```

while `Function.Outer` in the same binary writes r13 (`49 89 C5  MOV r13, rax`) and never saves
it. Byte scan over all four repro binaries:

```
r13probe:  PUSH r13 occurrences: 1     <- the inlined PrintNumber body only
home:      PUSH r13 occurrences: 1
clob:      PUSH r13 occurrences: 1
leaf:      PUSH r13 occurrences: 1
```

Every user function prologue in all four binaries is exactly
`55 48 89 e5 | 48 81 ec <imm32> | 53 | 41 54` (`push rbp; mov rbp,rsp; sub rsp,N; push rbx;
push r12`). **No user function saves r13.**

**Impact assessment.** Inside a pure-AILang program this is *self-consistent and currently
benign*: every caller-side spill is emitted by the same `HomesClobber` analysis, and the audit
found no reachable path where a home survives an unsaved clobber (§8.4, §8.6). The finding is
therefore **not** a miscompile today. It is:

1. an **ABI violation** that blocks any C/asm caller from holding a value in r13 across a call
   into AILang code — relevant because this tree already links C (SynthKit, DAW host binaries,
   `Library.Sample`, `Library.Synth`), and
2. an **internal contradiction** (PrintNumber saves r13; every compiled function does not),
   which becomes a real miscompile the moment an inline-spliced library body contains a *loop*
   rather than straight-line code.

Severity: correctness risk **medium-high**, surface **latent**. Ranked #2 in §12.

### 8.6 The complete call-clobber coverage matrix

This is the audit's central safety table. "Guard" is the mechanism that makes the register safe
across a call.

| Reg | Role | Saved how | Guard | Sound? |
|---|---|---|---|---|
| r13 | `int_name` home | frame spill in `HomeCallSave` | `HomesClobber` | yes (C4) |
| xmm2 | `flt_name` home | frame spill | `HomesClobber` | yes |
| xmm3–14 | extra float homes / borrows | `AllocXmmSave/Load` | `HomesClobber` | yes |
| r12 | `acc_name` home | prologue `push r12` | SysV callee-saved | yes |
| rbx | limit / `ihold` scratch | prologue `push rbx` | SysV callee-saved | yes |
| r14 | table base `tab_on` | reload from frame after call | unconditional in `HomeCallLoad` | yes |
| r11 | `der_on` derived sum | **not saved** | `has_call == 0` | yes |
| r11 | `ip0/ip1` home | **not saved** | `has_call == 0` | yes |
| r14 | `ip0/ip1` home | **not saved** | `has_call == 0` | yes |
| r11 | `prod_on` product | **not saved** | `has_call == 0` **and** explicit `ip*_reg` check | yes |
| r11 | `kmul_on` constant factor | **not saved** | `has_call == 0` + `AllocRegFree(11)` | yes |
| r11/r14 | `AllocExtend` extra integers | **not saved** | `AllocBad(cond)`/`(body)` — *stronger* than `has_call` | yes |
| rcx | `rcx_on` stride offset base | **not saved** | **none found** | **SUSPECTED — S1** |
| rdx | `rdx_on` compare chain | **not saved** | `Optimize_RdxSafe` (per-chain only) | SUSPECTED — S1 |

The invariant that makes the r11/r14 rows safe is:

> **Every consumer of r11 or r14 as a long-lived home requires `LoopHome.has_call == 0`.**

Verified for all four `has_call` consumers:
`Optimize_PickDerived` (COptStrength:433) `if has_call == 1 { ReturnValue(0) }`;
`Optimize_PickIp` (1612) same; `Optimize_PickAddr` (COptAddr:1058) same;
`Optimize_NoteProd` (575) same, plus the explicit `ip0_reg/ip1_reg == 11` re-check.

And `has_call == 0` is sound even when calls exist, because `Optimize_EdgeBad == 0` means every
clobbering call lies on a `Return`-terminated path (§1.3). `AllocExtend` is stricter still — it
refuses on **any** non-home-safe call anywhere in `cond`/`body`, reachable or not.

**Conclusion: no gap found in the r11/r14 may-clobber coverage.**

---

## 9. `Library.CCompileStmt.ailang` — `CompileStmt_While` and loop rotation

### 9.1 Eligibility and gating — **intact and correctly gated (C7)**

```
393  // A pure leaf compare can be re-run at the back edge with no side effects,
     // so the loop can be rotated: one-time entry test, then a bottom test
     // that jumps back on true. This drops the per-iteration unconditional jmp.
396  rotate_elig = 0
397  if type(condition) == CALL
       && Optimize_IsCompareName(data1(condition))
       && childcount(condition) == 2
       && Optimize_IsLeaf(child0) && Optimize_IsLeaf(child1)   -> rotate_elig = 1     (line 402)

410  outer = LoopHome.active
411  if outer == 0 { Optimize_LoopHomes(condition, body); ...entry loads...; Optimize_TripArm() }

469  // Trip loops already have an optimal pointer-compare back edge, and
     // a nested home inherits trip_on from the outer loop, so neither
     // case rotates here.
471  rotate = 0
472  if rotate_elig == 1 {
473      if outer == 0 {
474          if LoopHome.trip_on == 0 { rotate = 1 }
475      }
476  }
```

Both conditions the brief asked about are present and unchanged: **`outer == 0`** (line 473)
and **`LoopHome.trip_on == 0`** (line 474), plus `rotate_elig` (line 472). Provenance:
`git log -S rotate_elig` → exactly one commit, `8535a0fd` ("Rotate WhileLoop into a
bottom-tested loop for pure leaf compares"), ancestor of `HEAD`.

Emitted shape when `rotate == 1`:

```
    <one-time entry condition test>      ; Optimize_TryBranchCondition -> jz loop_end
loop_start:                              ; Emit_MarkLabel(loop_start) AFTER the entry test
    <body>
test_label:                              ; Compile_PushLoop(loop_end, test_label)
    <back-edge condition test>           ; Optimize_TryBranchConditionBack -> jtrue loop_start
loop_end:
```

`Compile_PushLoop(loop_end, test_label)` makes `ContinueLoop` re-test rather than re-enter the
body — correct for the rotated form.

### 9.2 Live proof of rotation

Repro `r13probe.ailang`, `Function.Outer`, condition `LessThan(i, n)` (both leaves):

```
; r13probe.ailang:24    }
    48 8B 45 F0          MOV rax, [rbp+-16]
    49 89 C5             MOV r13, rax
    48 8B 45 E8          MOV rax, [rbp+-24]
    49 89 C4             MOV r12, rax
    4C 3B 6D F8          CmpHomeMem            ; entry test ONLY
    0F 8D 46 00 00 00    JGE .L12              ; -> loop_end
    4C 89 E8             MOV rax, r12          ; .L11 = loop_start
    ...
; r13probe.ailang:23    i = Add(i, 1)
    49 83 C5 01          ADD r13, 1
    4C 3B 6D F8          CmpHomeMem            ; back-edge test, re-evaluated
    0F 8C BA FF FF FF    JL .L11               ; -> loop_start   (no unconditional jmp)
```

There is **no `JMP` at the back edge** — the per-iteration branch was folded in. Rotation is
working as designed.

### 9.3 One landmine in the back edge (S3)

```ailang
IfCondition EqualTo(back_handled, 0) ThenBlock: {
    Emit_Jmp(loop_start)          // <-- unconditional, does NOT re-test the condition
}
```

`Optimize_TryBranchConditionBack` (COptBranch:225) can only return `1` (compare emitted) or `2`
(`CompileCompare_Binary` failed). It **cannot return 0**, so this arm is dead code today. If
that contract ever changes — or if `CompileCompare_Binary` ever returns success after emitting
nothing — the rotated loop becomes an unconditional infinite jump. Same failure shape as the
unreachable `ReturnValue(Optimize_EmitOperation(...))` in `Optimize_BinaryMathOp`.

---

## 10. Data-flow map

### 10.1 The pipeline

```
                              ┌─────────────────────────────────────────────┐
   AST (WhileLoop cond+body)  │  Library.CCompilerOptimizer.ailang          │
        │                     │  FixedPool.LoopHome   (~230 mutable fields) │
        ▼                     │  FixedPool.AllocTab   (32 rows × 32 B)      │
 ┌─────────────────────────┐  │  FixedPool.PinDefer   (4 slots)             │
 │ 1  SCAN                 │  └─────────────────────────────────────────────┘
 │ Optimize_LoopHomes      │
 │  HomeWalk(cond)         │      LoopHome.recs: 64 rows × 48 B
 │  HomeWalk(body)         │      ┌──────┬───────┬────────┬──────┬───────┬───────┐
 │   └ HomeTouch           │─────▶│ name │ loads │ stores │ fops │ selfn │ seeds │
 │  HomeBlockNode →blocked │      └──────┴───────┴────────┴──────┴───────┴───────┘
 └───────────┬─────────────┘
             │  blocked==1 ─────────────────────────────▶ all homes = 0, return 0
             ▼
 ┌─────────────────────────┐
 │ 2  CALL-REACHABILITY    │   Optimize_EdgeBad(cond, body)
 │  Optimize_Flow / FlowIf │     code 0 fall-clean | 1 fall-with-clobber
 │  Optimize_FlowBlock     │          2 always-Return  | 3 break/continue
 │  Optimize_EdgeBad       │   → if 0: LoopHome.has_call = 0
 └───────────┬─────────────┘
             ▼
   ┌───────────────────────────────────────────────────────────────┐
   │  ★ LoopHome.body = body        (COptHome:1147)  ★             │
   │  ★ LoopHome.cond = condition   (COptHome:1148)  ★             │  ← the single
   │  (zeroed at COptHome:1037-1038; left 0 by the blocked exit)   │    set point
   └───────────────────────────────┬───────────────────────────────┘
                                   ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ 3  PICK  (scoring only; no code emitted)                         │
 │  Optimize_HomePick        loads/stores/fops/selfn/seeds →        │
 │                            int_name   = r13                      │
 │                            acc_name   = r12                      │
 │                            flt_name   = xmm2                     │
 │    └ Optimize_HomePickExtras  (COptScan:453)                     │
 │         └ Optimize_ExtraTake  → Optimize_InstallFlt → xmm3..14   │
 │  Optimize_ScanTable / PickByteBase  → tab_on  (r14 record base)  │
 │  Optimize_PickStride               → st_on   (st_base/st_off)    │
 │  Optimize_ScanBody/CondTemps/Limit → lim_on  (rbx)               │
 │  Optimize_PickInvariant            → may promote into acc (r12)  │
 │  Optimize_PickDerived              → der_on  (r11)               │
 │  Optimize_PickIp   (mode 0)        → ip0/ip1 (r11 then r14)      │
 │  Optimize_PickAddr (mode 1)        → ip0/ip1, ONLY if both off   │
 │  Optimize_NoteProd                 → prod_on (r11)               │
 │  Optimize_PickKmul                 → kmul    (r11)               │
 └───────────────────────────────┬──────────────────────────────────┘
                                 ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ 4  PUBLISH                                                       │
 │  Optimize_AllocPublish (COptAlloc:235)                           │
 │    stage existing (extras) rows → rows 20..31                    │
 │    AllocReset                                                    │
 │    add r13, r12, r11(der), rbx(lim), xmm2                        │
 │    replay staged rows (first row wins)                           │
 │    Optimize_AllocExtend → AllocRegFree(11)/(14) → r11, r14       │
 │  ────────────── AllocTab is now the single query surface ──────  │
 └───────────────────────────────┬──────────────────────────────────┘
                                 ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ 5  ENTRY LOADS  (CompileStmt_While, outer == 0)                  │
 │    frame → r13, xmm2, r12, rbx, r11(kmul), r14(tab), xmm3..14    │
 │    Optimize_AllocXmmIn / Optimize_AllocGprIn                     │
 │    Optimize_EmitDerived (r11) / Optimize_EmitIp / Optimize_EmitProd│
 │    Optimize_TripArm   (sets trip_on)                             │
 └───────────────────────────────┬──────────────────────────────────┘
                                 ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ 6  PER-STATEMENT COMPILE   ── every register decision goes       │
 │                               through Optimize_Loc(AllocTab) ──  │
 │                                                                  │
 │  TryHomeAssign (COptHome:1202)                                   │
 │      IsIntHome(name) → ADD/SUB r13,imm  (skipped if trip_on)     │
 │      + IpBump() + derived ADD r11 + EmitProdBump()               │
 │  TryLocArith   (COptHome:1280)  reg-reg ADD/SUB for r11/r14 homes │
 │  LocLoad / LocStore (COptAlloc:807/849)  rax ←→ r13/r12/r11/r14  │
 │  FltSlot / LocLoad class 2        xmm2 ←→ xmm3..14               │
 │  TryIpDef / TryIpDrop             n0..n3 named deref + d0..d3    │
 │  TryHomeCompare / TryAccCompare / TryRdxCmp                      │
 │  TryAccCall / TryAccMem / TryAccAssign                           │
 │  HomeCallSave / HomeCallLoad → HomesClobber (the may-clobber hook)│
 └───────────────────────────────┬──────────────────────────────────┘
                                 ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ 7  EMIT                                                          │
 │  Emit_HomeMove(kind, imm)  — kinds 1..46 are the ONLY place      │
 │                              r13 / r12 / xmm2 are named          │
 │  X86Enc_Assemble / X86_EmitR13Mem / X86_* R11/R14 helpers        │
 └───────────────────────────────┬──────────────────────────────────┘
                                 ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │ 8  LOOP EXIT  (outer == 0)                                       │
 │  FwdFail / IholdFlush / FlushHold / AliasFlush                   │
 │  AllocXmmOut → spills xmm3..14 to frame                          │
 │  AllocGprOut → writes back r11/r14                               │
 │  Optimize_HomeRelease → LoopHome.body = 0, cond = 0, AllocReset  │
 │  r13 → frame, xmm2 → frame, r12 → frame (LiveOut gated)          │
 └──────────────────────────────────────────────────────────────────┘
```

### 10.2 `LoopHome.body` / `LoopHome.cond` — the shared state the brief flagged

The brief called this "the single most error-prone piece of shared state". The audit confirms
that assessment and pins down the exact facts:

| Event | Location | Effect |
|---|---|---|
| zeroed | `COptHome:1037` / `1038` | `LoopHome.body = 0`, `LoopHome.cond = 0` at `Optimize_LoopHomes` entry |
| **set** | **`COptHome:1147` / `1148`** | **the only set point, after `HomeWalk` + `EdgeBad`, before `HomePick`** |
| left unset | `COptHome:~1108` | the `blocked == 1` early exit returns with `body == cond == 0` |
| zeroed again | `COptHome:117` / `142` | `Optimize_HomeRelease()` — called at loop exit when `outer == 0` |

Why this is fragile:

1. **It is set once and read for the rest of the *whole* loop's compilation**, including from
   the deepest statement compilers (`Optimize_PinWorth`, `Optimize_AddrOk`,
   `Optimize_AllocExtend`, `Optimize_AllocRegFree`, `Optimize_LiveIn/Out`).
2. **For a nested loop it deliberately keeps pointing at the *outer* body.** The inner
   `WhileLoop` never calls `Optimize_LoopHomes` when `outer != 0` (CCompileStmt:411), so
   `LoopHome.body` still refers to the outer body while inner statements compile. That is the
   intended "homes stay off" behaviour, but it means every `Mentions(LoopHome.body, name)`
   inside an inner loop is measured against the **outer** loop — an inflated count. Direction of
   error is conservative today (`PinWorth` more willing to pin; `AddrOk` requires exact
   equality so it bails), but nothing enforces that.
3. **`body`/`cond` outlive the loop when `outer != 0`** — `HomeRelease` is gated on
   `outer == 0`, so a nested loop leaves them pointing at the enclosing body until the
   enclosing loop exits.
4. **No consumer re-validates.** `Optimize_PinWorth` and `Optimize_AddrOk` both guard
   `LoopHome.body == 0`, but nothing distinguishes "this body" from "an enclosing body".

The mitigation applied throughout is ordering discipline: every `body`/`cond` consumer either
runs at pick time (steps 3–4, when the value is guaranteed current) or re-checks a scoping flag
(`LoopHome.active`, `has_call`, `trip_on`). **There is no assertion or generation counter.**
Recommended: add a monotonically increasing `LoopHome.body_gen` bumped at line 1147 and stored
alongside any pick-time decision that is later re-read, so a stale read can be *detected*
rather than silently trusted (§13, item 5).

---

## 11. The SSA / graph-colouring register allocator: hunt and findings

### 11.1 What the brief asked for

> "There is reportedly SSA and/or graph-coloring register-allocation infrastructure somewhere in
> this codebase, discussed in the context of a Phase 2 regalloc effort (motivated by
> cross-loop-boundary overhead in a Fannkuch benchmark…). Locate it."

### 11.2 What was actually found: **nothing (C10, CONFIRMED)**

Search performed, exhaustively:

| Search | Result |
|---|---|
| `git log --all --oneline \| grep -i "ssa\|graph\|regalloc\|liveness\|coloring"` | 13 hits, **all false positives** — every one matched the substring `ssa` inside `Message`/`PrintMessage`, or referred to HDL netlist graphs and GPU "liveness probes". Zero SSA / regalloc / colouring commits. |
| `find Librarys/Compiler -iname "*ssa*" -o -iname "*graph*" -o -iname "*regalloc*" -o -iname "*liveness*" -o -iname "*color*"` | **0 files** |
| `grep -rniE "\bssa\b\|interfer\|coloring\|regalloc\|spillcost\|dominat\|graph" --include=*.ailang Librarys/Compiler` (word-bounded, `message` filtered out) | only prose comments: "dominates" in `COptAddr.ailang:208` and `COptBranch.ailang:629/726`; `"PHI": Initialize=349` in `CLexerTypes.ailang:361` (a **lexer token id** for an unrelated language keyword, not an IR phi node); HDL netlist-graph files under `Compile/ModulesHDL/`. |
| Same search in the sibling tree `/home/bob/Ailang-Self-Hosting-graph` (the repo literally named "graph") | **0 hits** — the name refers to the HDL/netlist graph backend, not to a register-interference graph. |
| `grep -rliE "\bSSA\b\|graph coloring\|regalloc\|register allocation"` across `*.md`, `*.ailang`, `*.txt` | `docs/design/COMPILER_BATTLE_PLAN.md`, `docs/design/AILang Self-Hosting Compiler Architect.md`, `Programming_Manual/*`, `docs/cad/*`, `docs/browser/js-engine-design.md` — see 11.3 |
| `docs/compiler/NEXT.md`, `docs/compiler/00_ARCHITECTURE.md`, `docs/compiler/08_DATA_FLOW.md` | **0 hits** for SSA / regalloc / AllocTab / LoopHome |
| `grep -rli fannkuch` | `docs/benchmarks/fannkuch/*` (the benchmark itself, `fannkuch.ailang`, `fannkuch.cpp`, `compare.py`, `run.sh`) — **no design note referencing a Phase 2 regalloc effort** |

**Conclusion (C10, CONFIRMED): there is no SSA infrastructure, no interference graph, no
liveness lattice, no spill-cost model, and no graph-colouring allocator in this codebase.**

The only "liveness" in the tree is the *predicate* liveness in `Library.COptHome.ailang`
(`Optimize_LiveIn`, `Optimize_LiveOut`, `Optimize_LiveFullDef`, `Optimize_LiveEscape`,
`Optimize_LiveOut`/`OutsideHit`) — boolean "does this name appear outside statement k" tests used
to gate a spill, **not** a dataflow lattice and not a basis for allocation.

The only "register allocation" artefact is `AllocTab` (COptAlloc), and it is a **lookup map**,
not an allocator: every register choice in the system is a literal constant written by a
pattern picker (`13`, `12`, `11`, `14`, `3`, `2`, `3..14`). `AllocTab` records the *result* of
those hard-coded choices so that the emitters can ask "where is `x` right now?".

### 11.3 What *does* exist that could have been mistaken for it

Three documents/artefacts plausibly generated the "Phase 2 regalloc" recollection:

1. **`docs/design/COMPILER_BATTLE_PLAN.md` §"Problem 4 — Nested-call-arg codegen / explicit
   hoist syntax"`.** It presents a literal **"Option D: fix register allocation"**, with a
   **"Phase 1: document. Phase 2: audit existing hoist module. Phase 3: pick Option C or D.
   Phase 4 (stretch): CodeBlock syntax"** plan. This is a *hoisting* plan about
   `f(a, g(b, c))` argument nesting — **not** SSA and **not** graph colouring — but it is the
   only "Phase 2" + "fix register allocation" text in the repository, and it is the most likely
   source of the recollection. It explicitly rejects the automatic transform on DO-178C
   traceability grounds.
2. **`docs/design/AILang Self-Hosting Compiler Architect.md:383`** — a one-line design note:
   *"Register Allocation: R15 reserved for pool table base. R12, R13 for temps in nested
   expressions. Use stack for depth > 2."* This is the fixed-register-convention design that
   the code actually implements.
3. **`docs/benchmarks/fannkuch/`** — the Fannkuch benchmark exists with `.ailang`, `.cpp`,
   `compare.py`, and a checked-in prebuilt `fannkuch.x`, and `docs/README.md` references it.
   The *cross-loop-boundary teardown/setup overhead* that motivates the recollection is real and
   traceable in code: `Optimize_HomeBlockNode` (COptHome:630) declares **any nested loop a hard
   blocker for the outer loop's homes**, so a loop nested inside a hot loop forces the outer
   loop's r13/r12/xmm2 homes to be released and re-acquired — exactly the "teardown/setup cost
   paid repeatedly" description. But **no Phase 2 work has been started**.

Branch naming is also suggestive but contentless: the current branch is
**`optimizer4-regalloc`**, but `git log` shows it contains only the peephole commits
(`Skip SIB for constant-zero array index`, `Direct r13 SIB in swap block`, `Emit fast SUB …`,
etc.) and the diff against `master` touches no allocation code. **The branch name is
aspirational; the branch content is pattern-optimizer work.**

### 11.4 Is it wired into the active compile path?

**N/A — it does not exist.** Nothing to wire in, nothing dormant. The active path is 100 %
the pattern system described in §1–§9.

### 11.5 Therefore: the requested CONFIRMED-CRITICAL "two systems" finding cannot be constructed

The brief's conditional was:

> "If wired in: … could both systems independently decide to use the same register for different
> purposes in the same function? If the latter, that's a CONFIRMED CRITICAL finding — construct
> a repro."

Since the second system does not exist, **the antecedent is false and no such repro is
possible.** I am reporting that as a finding rather than fabricating one.

**However**, the *underlying worry is correct* — the pattern system has **five or six
independent agents** that each want r11 or r14, and the audit therefore went looking for a
same-register/different-purpose collision *inside* the existing system. That is the honest
substitute for the requested finding, and it is where the real risk lives.

### 11.6 The real multi-owner registers: r11 and r14, and their two arbiters

| Register | Independent claimants |
|---|---|
| **r11** | ① `der_on` derived sum · ② `ip0`/`ip1` induction pointer · ③ `prod_on` running product · ④ `kmul_on` constant factor · ⑤ `AllocExtend` extra integer home |
| **r14** | ① `tab_on` record base · ② `st_on` stride base · ③ `ip0`/`ip1` induction pointer · ④ `AllocExtend` second extra integer · ⑤ transient `MOV r14, base` emitted by the memory unit for *any* scaled qword |
| **rbx** | ① `lim_on` parked limit · ② `ihold_reg==3` parked intermediate · ③ `rbx_scratch` · ④ every `LoadToRbx`/`TryRbxLeaf` path |

Three mechanisms keep this from exploding, and **all three were verified**:

1. **`Optimize_AllocRegFree(reg)`** (COptAlloc:377) — the *positive* arbiter, consulted by
   `AllocExtend` before publishing an extra integer. Checks all five r11 claimants and all five
   r14 claimants (§2).
2. **`Optimize_IpTakeReg()`** (COptStrength:1226) — the arbiter for induction pointers,
   consulting `der_on` / `tab_on` plus its own two slots.
3. **Ordering** — `PickDerived` (23) → `PickIp` (24) → `PickAddr` (25) → `NoteProd` (27) →
   `PickKmul` (28) → `AllocPublish`/`AllocExtend` (30). Every later claimant re-checks the
   earlier ones; the earlier ones cannot check the later ones and do not have to, because the
   later ones defer.

**Live proof that the arbitrage works.** Repro `arb.ailang` puts four subsystems into one loop —
extra-integer home, transient r14 address base, r13 cursor, r12 accumulator, rbx scratch — and
the disassembly shows a clean, non-overlapping assignment:

```ailang
Function.Pick { Input: n: Integer Input: p: Integer Output: Integer
    Body: { i = 0  acc = 0  k = 7
            WhileLoop LessThan(i, n) {
                j = Add(k, i)
                acc = Add(acc, Dereference(Add(j, Multiply(i, 8))))
                i = Add(i, 1) }
            ReturnValue(acc) } }
```

```
    48 8B 45 E8          MOV rax, [rbp+-24]    ; i
    49 89 C5             MOV r13, rax          ; r13 = cursor      (HomePick)
    48 8B 45 E0          MOV rax, [rbp+-32]    ; acc
    49 89 C4             MOV r12, rax          ; r12 = accumulator (HomePick)
    48 8B 45 F8          MOV rax, [rbp+-8]     ; n
    49 89 C3             MOV r11, rax          ; r11 = extra home  (AllocExtend)
    4D 39 DD             CMP r13, r11          ; loop test reads the r11 home
    ...
    4C 89 E9             MOV rcx, r13
    48 8B 45 D8          MOV rax, [rbp+-40]    ; k
    4C 89 EB             MOV rbx, r13          ; rbx = scratch
    48 01 D8             ADD rax, rbx
    49 89 C6             MOV r14, rax          ; r14 = transient address base
    ...
    49 83 C5 01          ADD r13, 1
    4D 39 DD             CMP r13, r11
    4C 89 D8             MOV rax, r11          ; exit writeback of the r11 home
    48 89 45 F8          MOV [rbp+-8], rax
```

Five registers, five owners, no collision. `AllocRegFree(14)` correctly refused to publish a
second extra integer *because* `AllocMemR14(body)` detected the transient `MOV r14, base` that
this very expression needs — which is exactly what that otherwise-odd helper exists for.

**Verdict: no CONFIRMED CRITICAL same-register/different-purpose collision exists in the
pattern system today.** The risk is real but *serialised*, and the serialisation depends on
ordering that is documented nowhere and asserted nowhere. See §13 items 3–4.

---

## 12. Findings register

Every finding carries a tag. **CONFIRMED** = proven by reading the code at `HEAD` *and* by an
empirical artefact (a compiled listing, a byte dump, a run, or a git commit hash) reproduced in
this report. **SUSPECTED** = strongly indicated by code reading but not proven; a concrete test
is given.

### 12.1 CONFIRMED

| ID | Finding | Section |
|----|---------|---------|
| **C1** | Pipeline order is exactly scan → reachability → publish-set → pick → allocate → publish → entry-loads → per-statement → emit. `LoopHome.body`/`cond` have exactly one set point (`COptHome:1147/1148`), zeroed at `1037/1038`, left 0 by the `blocked` exit, and re-zeroed by `HomeRelease`. | §1.3, §10.2 |
| **C2** | **r13 is used as the primary integer loop home by essentially every compiled function and is never saved by any function prologue**, despite being callee-saved under SysV AMD64 — and despite another part of the *same compiler* (`PrintNumber`'s inlined body) pushing r13/r14/rbx/r12. Currently benign inside pure AILang because `Optimize_HomeCallSave` + `Optimize_HomesClobber` inserts caller-side spills; an ABI violation at any C/asm↔AILang boundary. | §8.5 |
| **C3** | The rbx/r12 "may-clobber mechanism" is commit **`69d9e590`**; present verbatim at `HEAD`; wraps all four `BinaryMathOp` rbx-using paths plus both failure paths. Coverage audit found **no gap** — the four pre-hook returns (`nargs`, `TryProdUse`, `TryLea`, `imm_fast`) provably never write rbx. r12 needs no hook (ABI + every prologue pushes it). | §8.3 |
| **C4** | The r13/xmm2–xmm5 clobber hook (`HomesClobber` → `HomeCallSave`/`HomeCallLoad`) verified in both directions: fires (spill+reload of r13 around a call to a loop-containing callee) and correctly does *not* fire for a provably clean callee. | §8.4 |
| **C5** | COptAddr's second induction-pointer mechanism (§6) and COptStrength's `ip0/ip1` + `n0`–`n3` system (§4) **cannot conflict on the same variable in the same loop**: `PickAddr` bails if `ip0_on || ip1_on`; `PickIp` runs first; `AddrInstall` reuses the same slots under `ip*_mode = 1`; `AddrOk` excludes `int_name`, `acc_name`, `der_name` and every `IpIsNoted` name. They also cannot conflict on registers (`IpTakeReg` is shared). | §6 |
| **C6** | The immediate-fusion fast paths (Add/Subtract imm32, non-pow2 Multiply → `IMUL rax,rax,imm32`) are **still present** (commits `5ca0027a`, `51a300d4`) and **correctly ordered**: after `TryLea` (which owns only home-bearing LEA shapes) and before the `save_rbx` window. Proven reachable: `y = Add(x,1)` → `48 83 C0 01 ADD rax, 1`. | §7 |
| **C7** | Loop rotation in `CompileStmt_While` is intact and still gated on **`rotate_elig == 1` && `outer == 0` && `LoopHome.trip_on == 0`** (commit `8535a0fd`; single historical commit). Proven live: `LessThan(i,n)` compiles to a one-time entry test plus a bottom-tested `JL loop_start` with no back-edge `JMP`. | §9 |
| **C8** | `is_leaf` detection is defeated by the frontend: `CompileFunc_HasCalls` counts **every** `AST.CALL`, and every builtin operator is a `AST.CALL`, so the red-zone leaf prologue fires only for bodies with zero operator calls. `Function.K3 { y = Add(x,1) }` therefore gets `sub rsp,0x60` + `push rbx` + `push r12` for one `ADD`. Performance only. | §8.2 |
| **C9** | The `-asm` listing **silently omits the `sub rsp, imm32` frame allocation**. Proven by diffing the listing against the raw PT_LOAD bytes for the same function. Any future audit, bug report, or review that reads `-asm` output for prologue/frame work is reading a corrupted artefact. | §0.3 |
| **C10** | **No SSA, no interference graph, no liveness lattice, no spill-cost model, no graph-colouring allocator exists** anywhere in `Librarys/Compiler` (or in the sibling `-graph`/`-math` trees, or in `git log --all`). `AllocTab` is a name→(class,reg,offset) **map**, not an allocator; every register choice is a literal constant in a pattern picker. The "Phase 2 regalloc" recollection traces to `docs/design/COMPILER_BATTLE_PLAN.md` "Problem 4 / Option D" (a *hoisting* plan that mentions "fix register allocation") and to the aspirational branch name `optimizer4-regalloc`, whose contents are peephole work only. | §11 |
| **C11** | The five-way r11 contention (`der_on`, `ip0/ip1`, `prod_on`, `kmul_on`, `AllocExtend`) and five-way r14 contention (`tab_on`, `st_on`, `ip0/ip1`, `AllocExtend`, transient memory-unit bases) **is correctly serialised** by `Optimize_AllocRegFree`, `Optimize_IpTakeReg`, and pick ordering. Demonstrated live on a loop with four simultaneous claimants. | §11.6 |

### 12.2 SUSPECTED

| ID | Finding | Why suspected | Suggested test |
|----|---------|---------------|----------------|
| **S1** | **`LoopHome.rcx_on` (the "byte base" / stride offset parked in `rcx`) and `LoopHome.rdx_on` (compare chain in `rdx`) are caller-saved and have no call-save hook.** `HomeCallSave`/`HomeCallLoad` cover r13, xmm2, xmm3–14 and reload only r14 (for `tab_on`). Nothing in the optimizer clears `LoopHome.rcx_on` at a call, and `Optimize_StrideOff` (`COptStride:1003`) trusts `rcx_on` + matching `rcx_name`/`rcx_base`. If a call lands between the park and the reuse, `rcx` is garbage and `rcx_on` still says 1. | code reading; no `has_call`/`AllocBad` guard found on the `rcx`/`rdx` pickers | loop with a strided store-based expression that parks `rcx`, then a real call, then another use of the same offset. Check `-asm` for a `rcx` reload and confirm the arithmetic. |
| **S2** | `Optimize_AllocPublish` stages old rows at **row `20 + i`** but never asserts `saved <= 12`; rows are `Allocate(1024)` = 32 × 32 B, so `saved > 12` writes off the end of the allocation. Separately, `Optimize_InstallFlt` **ignores `Optimize_AllocAdd`'s return value** and reports success even when the table is full (`n >= 32`), so a picker can believe a float home exists when it does not. | invariant is implicit (§2), no assert, no failure path | `DEBUG` build with a bounds assert in `AllocPublish`; construct a loop with 12 permanent float extras *plus* a coal/borrow row present before publish. |
| **S3** | Two dead arms that are landmines: (a) `CompileStmt_While`'s rotated back edge has `if back_handled == 0 { Emit_Jmp(loop_start) }` — an **unconditional** jump that does not re-test the condition; unreachable today only because `Optimize_TryBranchConditionBack` can return 1 or 2 but never 0. (b) `Optimize_EmitOperation(...)` at `COptMath:1036` is unreachable. | contract is undocumented and unasserted | if (a) ever becomes reachable → infinite loop. Add a `Compile.error = 1` on `back_handled == 0` instead of a silent `Jmp`. |
| **S4** | Leaf functions (C8) rely **solely** on `CompileFunc_HasCalls == 0` to justify skipping `sub rsp`. Today the only syscalls in a leaf-capable body are inline `SYSCALL` sequences (which do not touch the user stack), so it is safe — but any future inlining of a `CALL` into a leaf path silently writes locals into the red zone that the callee will overwrite. `Function.K2` uses 16 bytes of red zone with no frame. | single-condition guard, no assert | assert in `CompileFunc_Function` that `is_leaf == 1` implies the body contains no `CALL` *and* no inline-asm block containing a `CALL`. |
| **S5** | `LoopHome.body`/`cond` alias the **enclosing** loop's body while an inner loop compiles, because the inner `WhileLoop` skips `LoopHomes` entirely and `HomeRelease` is gated on `outer == 0` (§10.2). All current consumers happen to fail safe, but no mechanism distinguishes "this body" from "an enclosing body". | no generation counter, no assert | add `LoopHome.body_gen`; log a warning when a consumer reads `body` whose generation is older than the current loop's. |
| **S6** | **`Float_ToInt` returns 0 for every input** (`Float_ToInt(4.7)`, `Float_ToInt(1.5+2.5)`, `Float_ToInt(2.5-returning-function)` all print `0`). Outside the audited scope, but it **blocks all float-home runtime validation** and should be tracked. | separate defect | `PrintNumber(Float_ToInt(4.7))` → `0`. |

---

## 13. Prioritised recommended next actions

Ranked by **correctness risk first**, then **performance impact**. Effort is rough
engineer-days for someone already familiar with the files.

### Priority 1 — Correctness risk, must not be deferred

| # | Action | Why | Effort |
|---|--------|-----|--------|
| 1 | **Verify and close S1 (rcx/rdx call-clobber)**. Determine whether `rcx_on`/`rdx_on` parks can survive a call; if not, add an invalidation hook alongside `Optimize_HomeCallSave` (or fold them into the `AllocBad`/`has_call` gate like every r11/r14 claimant). This is the **only may-clobber gap the audit could not close** and it is the one item the brief explicitly scoped as in-bounds for a fix. | Unprotected caller-saved register trusted across a call is a silent-wrong-answer class bug. | 1–2 d (verify 0.5, fix 0.5–1, regression 0.5) |
| 2 | **Resolve C2 (r13 not saved)**. Two defensible options: (a) declare r13 formally caller-saved *for AILang only* and add a `Compile.error = 1` whenever `HomesClobber` is bypassed, plus a build-time note forbidding C→AILang calls that hold r13; or (b) add `push r13`/`pop r13` to the non-leaf prologue/epilogue. Option (b) costs one push/pop per function and removes the entire class of hazard — but it interacts with `HomeCallSave`'s spill slots and the `Compile.stack_size` arithmetic (frame alignment), so it needs the full Fannkuch + bench suite. | ABI violation + internal contradiction with `PrintNumber`. Latent, but this tree already links C. | (a) 0.5 d · (b) 2–3 d + full bench |
| 3 | **Assert the register-claim invariants (C11)** in debug builds only: `Optimize_AllocRegFree`/`Optimize_IpTakeReg` should assert that no two *live* claimants report the same register at `AllocPublish` time. This converts the currently undocumented ordering discipline into a machine-checked property. | The whole r11/r14 safety argument rests on ordering that is asserted nowhere. | 0.5–1 d |
| 4 | **Fix S3(a)** — replace the unreachable `Emit_Jmp(loop_start)` arm with `Compile.error = 1`. Cheap insurance against an infinite-loop miscompile. | Dead code that is wrong if it ever becomes live. | 0.25 d |
| 5 | **Fix S2** — bounds assert in `AllocPublish` (`saved <= 12`) and honour `Optimize_AllocAdd`'s return in `Optimize_InstallFlt`. | Latent heap overflow / phantom home. | 0.5 d |

### Priority 2 — Correctness infrastructure

| # | Action | Why | Effort |
|---|--------|-----|--------|
| 6 | **Add `LoopHome.body_gen` (S5/C1)** — a monotonic counter bumped where `body`/`cond` are set, stored in any decision that a later phase re-reads, and checked at the read sites (`PinWorth`, `AddrOk`, `AllocExtend`, `AllocRegFree`). Fail closed on a stale read. | `LoopHome.body`/`cond` is the highest-blast-radius shared state and the brief correctly identified it. Currently invisible-by-construction. | 1–2 d |
| 7 | **Fix C9** — make `Emit_SubRspPatchable` write its bytes into the listing buffer. | Every future audit/review reading `-asm` is currently misled about frames. Cheap, high leverage on *all* future debugging. | 0.25 d |
| 8 | **Track S6 (`Float_ToInt`)** as a separate bug. Until it is fixed, no float-home change can be runtime-validated, so it gates the whole float half of this optimizer. | Blocks verification, not correctness itself. | 0.5–1 d |

### Priority 3 — Performance (the Fannkuch motivation)

| # | Action | Why | Effort |
|---|--------|-----|--------|
| 9 | **Fix C8 (`is_leaf`).** Give `CompileFunc_HasCalls` a notion of "operator call" vs "real call" (it already has `Optimize_HomeCallOk` and `Optimize_IsMathOp` lists to lean on). Every arithmetic-only helper currently pays `sub rsp` + 2 pushes + 2 pops + frame arithmetic it does not need. | Large, broad, low-risk win — the single biggest perf item in this report. | 1–2 d + bench |
| 10 | **Attack the cross-loop-boundary teardown (C10/§11.3 item 3).** `Optimize_HomeBlockNode` treats *any* nested loop as a total blocker for the outer loop's homes. A narrower rule — allow the outer homes to survive a nested loop when the inner loop acquires **no** homes of its own (which is already the case, since inner loops skip `LoopHomes` when `outer != 0`) — would remove the repeated acquire/release cost that motivates the Fannkuch work. This is the *real* Phase-2 item; it is a pattern-system extension, not an SSA rewrite. | This is the actual measured overhead the brief describes. | 3–5 d + Fannkuch + full bench, high risk |
| 11 | **De-duplicate the two float pickers.** `Optimize_ExtraTake` (COptScan:362) is a near-verbatim copy of the float pass inside `Optimize_HomePick` (COptHome:743) — same shape test, same vetoes, same ranking. They have already drifted once (the extra pass gates additionally on `NameTaken`). Fold into one parameterised scorer. | Reduces the chance of the two float paths disagreeing about which name is a home. | 1 d |
| 12 | **If graph-colouring regalloc is genuinely wanted (C10)**, it must be scoped as a *new* subsystem, not an audit of an existing one: there is nothing to extend. Realistic minimum is (i) build the `LiveIn/LiveOut` predicates out into a per-block dataflow lattice, (ii) build an interference graph from `AllocTab`'s current hard-coded assignments, (iii) colour it, (iv) keep the entire pattern system as a "hint" source. Estimate below assumes the whole pattern system stays as the fallback. | Sets honest expectations: the premise of "existing infrastructure" is false. | 3–5 weeks, not days |

### Explicitly *not* done

Per the brief, **no code was changed and nothing was fixed**. The only write in this session is
this report. Priority-1 item 1 (the rcx/rdx may-clobber gap) is the sole item the brief
pre-authorised for a fix, and it is left **unfixed and flagged for review** because it is
currently SUSPECTED rather than CONFIRMED — fixing a suspected gap before proving it would
violate the "confirm first" standard the rest of this report is held to.

---

## Appendix A — repro files (verbatim)

All repros were compiled with `./ailang.x -asm <file> <out>` from
`/home/bob/Ailang-Self-Hosting-/ailang.x` and run from `/tmp/raudit`.

### A.1 `r13probe.ailang` — C2 (r13 never saved) + C4 (hook fires) + C7 (rotation)

```ailang
// r13probe.ailang -- audit repro: callee-saved r13 used as a loop home.
Function.Inner {
    Input: n: Integer
    Output: Integer
    Body: {
        i = 0
        acc = 0
        WhileLoop LessThan(i, n) {
            acc = Add(acc, i)
            i = Add(i, 1)
        }
        ReturnValue(acc)
    }
}
Function.Outer {
    Input: n: Integer
    Output: Integer
    Body: {
        i = 0
        acc = 0
        WhileLoop LessThan(i, n) {
            acc = Add(acc, Add(Inner(3), i))
            i = Add(i, 1)
        }
        ReturnValue(acc)
    }
}
SubRoutine.Main {
    PrintMessage("outer4=")
    PrintNumber(Outer(4))
    PrintMessage("\n")
    ProcessExit(0)
}
RunTask(Main)
```

Observed: `outer4=18` (correct).

### A.2 `clob.ailang` — C4 negative case (clean callee, no spill emitted)

```ailang
Function.Id {
    Input: x: Integer
    Output: Integer
    Body: { ReturnValue(x) }
}
Function.Work {
    Input: n: Integer
    Output: Integer
    Body: {
        i = 0
        acc = 0
        WhileLoop LessThan(i, n) {
            acc = Add(acc, Id(i))
            i = Add(i, 1)
        }
        ReturnValue(acc)
    }
}
SubRoutine.Main {
    Output: Integer
    Body: {
        PrintNumber(Work(5))
        PrintMessage("\n")
        ReturnValue(0)
    }
}
```

### A.3 `arb.ailang` — C11 (five-way r11/r14 arbitration inside one loop)

```ailang
Function.Pick {
    Input: n: Integer
    Input: p: Integer
    Output: Integer
    Body: {
        i = 0
        acc = 0
        k = 7
        WhileLoop LessThan(i, n) {
            j = Add(k, i)
            acc = Add(acc, Dereference(Add(j, Multiply(i, 8))))
            i = Add(i, 1)
        }
        ReturnValue(acc)
    }
}
SubRoutine.Main {
    PrintMessage("pick=")
    PrintNumber(Pick(10, 0))
    PrintMessage("\n")
    ProcessExit(0)
}
RunTask(Main)
```

> Note: this repro *dereferences an invalid address* by construction (`j = 7+i`, `p` is
> unused), so the run terminates with `Segmentation fault` — that is the test program's own
> bug, deliberately left as-written because the file's purpose is the **static** register
> assignment, not the run.

### A.4 `leaf.ailang` — C8 (`is_leaf`) + C9 (listing drops `sub rsp`)

```ailang
Function.K {
    Output: Integer
    Body: { ReturnValue(7) }
}
Function.K2 {
    Input: x: Integer
    Output: Integer
    Body: { y = 9 ReturnValue(y) }
}
Function.K3 {
    Input: x: Integer
    Output: Integer
    Body: { y = Add(x, 1) ReturnValue(y) }
}
SubRoutine.Main {
    PrintMessage("k=")
    PrintNumber(Add(K(), Add(K2(0), K3(1))))
    PrintMessage("\n")
    ProcessExit(0)
}
RunTask(Main)
```

Observed: `k=18` (correct).

### A.5 `t4.ailang` — S6 (`Float_ToInt` returns 0)

```ailang
Function.Two {
    Output: Float
    Body: { ReturnValue(2.5) }
}
SubRoutine.Main {
    PrintMessage("a=")
    PrintNumber(Float_ToInt(4.7))
    PrintMessage("\n")
    x = 1.5
    y = 2.5
    PrintMessage("b=")
    PrintNumber(Float_ToInt(Float_Add(x, y)))
    PrintMessage("\n")
    PrintMessage("c=")
    PrintNumber(Float_ToInt(Float_Add(1.5, Two())))
    PrintMessage("\n")
    PrintMessage("d=")
    PrintNumber(Float_ToInt(Two()))
    PrintMessage("\n")
    ProcessExit(0)
}
RunTask(Main)
```

Observed: `a=0 b=0 c=0 d=0` (expected `4 4 4 2`).

---

## Appendix B — commit references

| Commit | Relevance |
|---|---|
| `69d9e590` | **C3** — the rbx may-clobber hook (`save_rbx` in `Optimize_BinaryMathOp`) |
| `8535a0fd` | **C7** — loop rotation (`rotate_elig`) |
| `5ca0027a` | **C6** — immediate Add/Subtract fusion outside loop homes |
| `51a300d4` | **C6** — direct `IMUL rax,rax,imm32` for non-power-of-2 constant multiply |
| `a20cd04e` | "Fix two pre-existing bugs in the induction-pointer optimizer" — §4 |
| `90a944ec` | `AllocGprOut` loop-exit writeback; removal of `TryLocArith` frame stores — §2 |
| `b59398f0` | "Load float homes into rbx through the location table" — `LocLoad`/`LocToRbx` |
| `f2df9ee2` | "Back-patch function frame size after body compilation" — §8.1, C9 |
| `01bd6817`, `5244c6fc`, `36d45b73`, `a6961a14` | SIB / r13 / r14 addressing in the memory unit — §2 `AllocMemR14` |

**End of report.**
