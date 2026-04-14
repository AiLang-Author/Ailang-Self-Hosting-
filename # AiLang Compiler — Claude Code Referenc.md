
Sean Collins, 2 Paws Machine and Engineering. SCSL License.

---

## CRITICAL: WSL System Utilities
**Always use full /usr/bin/ paths. Symlink issue means bare commands may fail.**

```
/usr/bin/grep       /usr/bin/find       /usr/bin/head
/usr/bin/tail       /usr/bin/diff       /usr/bin/wc
/usr/bin/sort       /usr/bin/cat        /usr/bin/ls
/usr/bin/cp         /usr/bin/mv         /usr/bin/rm
/usr/bin/mkdir      /usr/bin/chmod      /usr/bin/sed
/usr/bin/awk        /usr/bin/cut        /usr/bin/tr
/usr/bin/xxd        /usr/bin/od         /usr/bin/strings
```

---

## Project Location
```
/mnt/c/Users/Sean/Documents/AILangSH/
```

## Build & Test
```bash
./ailang.x SOURCE.ailang OUTPUT.x    # compile
./OUTPUT.x                            # run
./ailang.x -D1 SOURCE.ailang OUT.x   # compile with debug assertions
./ailang.x -D2 SOURCE.ailang OUT.x   # compile with trace debug
./ailang.x -P  SOURCE.ailang OUT.x   # compile with perf profiling
```

## Self-Host Build Chain
```bash
./ailang.x ailang_cli.ailang ailang1.x
./ailang1.x ailang_cli.ailang ailang2.x
/usr/bin/diff <(xxd ailang1.x) <(xxd ailang2.x)   # verify fixed point
./ailang2.x ailang_cli.ailang ailang3.x             # three-gen deep build
```

---

## Language Rules — MUST FOLLOW

### Expressions must be fully flattened
```
// WRONG — nested calls crash or miscompile
result = Add(Multiply(a, b), c)

// CORRECT — every intermediate is a named variable
tmp = Multiply(a, b)
result = Add(tmp, c)
```

### Max 6 inputs per Function
```
// If you need more than 6 args, use a carrier FixedPool:
FixedPool.MyCarrier {
    "extra1": Initialize=0
    "extra2": Initialize=0
}
// Caller sets fields, callee reads them directly by name
```

### SubRoutine locals are GLOBAL scope
All SubRoutine variable names share one namespace. Use unique prefixes per SubRoutine to avoid collisions:
```
SubRoutine.ATTN_Forward {
    fwd_dmod  = TFConfig.DModel    // prefix: fwd_
    fwd_seqln = TFConfig.SeqLen
    ...
}
SubRoutine.ATTN_Backward {
    bwd_dmod  = TFConfig.DModel    // prefix: bwd_
    bwd_seqln = TFConfig.SeqLen
    ...
}
```

### Libraries: pure Functions only
- No SubRoutines in library files
- No FixedPool state in library files
- All state passed as explicit arguments
- FixedPool carriers defined in a shared carrier library

### No parentheses inside string literals
```
PrintMessage("value is ok\n")     // fine
PrintMessage("value (ok)\n")      // BREAKS PARSER
```

### ReturnValue in conditional blocks (known bug)
`ReturnValue` inside a `ThenBlock` in a recursive function falls through. Use a result variable instead:
```
// WRONG
IfCondition LessThan(n, 2) ThenBlock: {
    ReturnValue(n)    // falls through in recursive context
}

// CORRECT
result = n
IfCondition GreaterEqual(n, 2) ThenBlock: {
    result = Add(Fib(Subtract(n,1)), Fib(Subtract(n,2)))
}
ReturnValue(result)
```

---

## Float Intrinsics (SSE2 Compiler Builtins)
These are compiler-level builtins, not library functions. They compile directly to SSE2 instructions.

| AiLang Call | x86 Instruction | Description |
|-------------|-----------------|-------------|
| `Float_FromInt(n)` | CVTSI2SD | integer → double |
| `Float_ToInt(f)` | CVTTSD2SI | double → integer (truncate) |
| `Float_Add(a, b)` | ADDSD | double add |
| `Float_Sub(a, b)` | SUBSD | double subtract |
| `Float_Mul(a, b)` | MULSD | double multiply |
| `Float_Div(a, b)` | DIVSD | double divide |
| `Float_Sqrt(n)` | SQRTSD | double square root |
| `Float_Lt(a, b)` | UCOMISD+SETB | less than → 0 or 1 |
| `Float_Gt(a, b)` | UCOMISD+SETA | greater than → 0 or 1 |
| `Float_Eq(a, b)` | UCOMISD+SETE | equal → 0 or 1 |

**Must be fully flattened — no nesting:**
```
// CORRECT float multiply
fa     = Float_FromInt(a)
fb     = Float_FromInt(b)
fmul   = Float_Mul(fa, fb)
result = Float_ToInt(fmul)
```

---

## Key Files

### Compiler
| File | Purpose |
|------|---------|
| `ailang_cli.ailang` | Compiler entry point |
| `Librarys/Compiler/Compile/Library.CCompileMain.ailang` | Main dispatch. Optimizer at line 660 (top of chain). |
| `Librarys/Compiler/Compile/Library.CCompilerOptimizer.ailang` | Peephole optimizer — 3-way operand loading |
| `Librarys/Compiler/Compile/Library.CCompileArith.ailang` | Arithmetic compilation |
| `Librarys/Compiler/Compile/Library.CCompileFunc.ailang` | Function/subroutine compilation. Prologue: PUSH RBX + PUSH R12 only. |
| `Librarys/Compiler/Compile/Library.CCompileMem.ailang` | Memory ops, SIB optimization |
| `Librarys/Compiler/Compile/FPU/X86/Library.FPUCompileX86SSE.ailang` | Float/SSE2 intrinsic compilation |
| `Librarys/Compiler/Compile/FPU/X86/Library.FPUEmitX86SSE.ailang` | SSE2 byte emission |
| `Librarys/Compiler/Compile/FPU/X86/Library.FPUCompileX86MemOps.ailang` | SSE2 memory ops |
| `Librarys/Compiler/CodeEmit/Library.CEmitCoreArch.ailang` | Architecture abstraction emit layer |

### Transformer (ATTN project)
| File | Purpose |
|------|---------|
| `ATTN.ailang` | Orchestration — owns ALL state and SubRoutines |
| `Librarys/TF/Library.Math.ailang` | TFConfig hyperparameters, matrix alloc, LCG random |
| `Librarys/TF/Library.Vec.ailang` | Vector ops — dot, add, scale, argmax |
| `Librarys/TF/Library.Mat.ailang` | Matrix ops — matmul, SGD, outer product |
| `Librarys/TF/Library.Act.ailang` | Softmax (exp table), cross-entropy (log table) |
| `Librarys/TF/Library.Layer.ailang` | Forward pass — embed, QKV, attention, residual, output |
| `Librarys/TF/Library.Train.ailang` | Backward pass — gradient functions |
| `Librarys/TF/Library.Float.ailang` | Float wrappers for backward pass precision |
| `Librarys/TF/Library.Carriers.ailang` | Shared FixedPool carriers for >6-arg functions |

---

## Transformer Architecture

### Task
Learn to reverse a sequence of 8 digits (0-9). Input: `[4,7,2,1,8,3,6,5]` → Output: `[5,6,3,8,1,2,7,4]`

### Model (matches ATTN/11 by Damien Boureille)
- 1 layer, 1 head, d_model=16, seq_len=8, vocab=10
- 1216 parameters total
- Encoder-only: embed → self-attention → residual → projection → softmax
- No layer norm, no FFN, no decoder

### Hyperparameters (Library.Math.ailang — TFConfig)
```
DModel    = 16
SeqLen    = 8
VocabSize = 10
LR_Attn   = 80     // Wq/Wk/Wv learning rate (×1000 = 0.08)
LR_Embed  = 10     // embedding learning rate (×1000 = 0.01)
LR_Out    = 25     // Wout learning rate (×1000 = 0.025)
LR_Scale  = 1000   // divisor for all LR values
MaxSteps  = 1000
LogEvery  = 100
```

### State Pools (ATTN.ailang)
```
TFW.*       — weights (Embed, PosEmb, Wq, Wk, Wv, Wout)
            — forward cache (emb, qvec, kvec, vvec, scores, attn, ctx, resid, logits, probs)
            — gradient buffers (dEmbed, dPosEmb, dWq, dWk, dWv, dWout, dLogits, dResid, dCtx, dEmb, dQ, dK, dV, dScores)
TFState.*   — tokens, targets, step, loss_acc, acc_num, acc_den
TFConfig.*  — hyperparameters (read-only)
```

### Carrier FixedPools (Library.Carriers.ailang)
Used to pass extra args beyond the 6-input limit:
```
TFProjCarrier   — extra args for TFLayer_ProjQKV (.Wk .Wv .seqln .dmod)
TFOutProjCarrier — extra args for TFLayer_OutputProj (.seqln .dmod .vocab)
TFBackOut       — extra args for TFTrain_BackOutProj (.Wout .targets .seqln .dmod .vocab)
TFBackCtx       — extra args for TFTrain_BackAttnCtx (.attn .vvec .seqln .dmod .scale)
TFBackQK        — extra args for TFTrain_BackQK (.seqln .dmod)
TFBackWA        — extra args for TFTrain_BackWeightsA (.Wq .Wk .Wv .emb .seqln .dmod .dK .dV)
TFBackWB        — extra args for TFTrain_BackWeightsB (.tokens .seqln .dmod)
```

### Numeric Representation
- Forward pass: raw integers, softmax outputs Q8 (0-256 representing 0.0-1.0)
- Softmax gradient: Q8 (probs - one_hot, range ±256) — do NOT multiply by 128
- Backward pass gradients: raw integers, float ops used in TF_FOuterAccum for precision
- SGD: integer (TF_MatSGD), lr = LR_Attn * grad / LR_Scale

### Current Status
- Training runs end to end ✓
- Weights updating ✓
- Loss at ~0.96 (random chance baseline for 10 classes) — NOT yet converging
- Gradient `dWq[0,0]` is non-zero ✓
- Inference produces all zeros — model not learning reversal task yet

---

## Debug Flags
```
-D1   assertions only (DebugAssert)
-D2   trace level (Debug blocks level=1 and level=2)
-D3   detailed (memory inspection)
-D4   full (breakpoints — requires debugger)
-P    performance profiling (RDTSC — do NOT use in recursive/loop-heavy code, causes crashes)
```

---

## Benchmarks
```bash
# Fair comparison (no DebugPerf overhead)
./ailang.x bench_suite.ailang bench_suite.x
/usr/bin/time ./bench_suite.x

/usr/bin/gcc -O2 -o bench_suite_c bench_suite.c
/usr/bin/time ./bench_suite_c
```

---

## Known Issues
1. **ReturnValue in ThenBlock** — falls through in recursive functions (see above)
2. **DebugPerf in recursive contexts** — uses fixed slots, unsafe in loops/recursion
3. **WSL symlink issue** — always use `/usr/bin/` prefix for all system utilities
4. **No variable liveness** — values stored/reloaded from stack even when in register (compiler optimization opportunity)
5. **Large stack frames** — 64 + 16 bytes per local, oversized for small functions