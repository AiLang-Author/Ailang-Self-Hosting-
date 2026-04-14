# Gemini Patch 2 (Revised): Concept-Vector Coordinator + Hot-Swap

## Depends on: Patch 1 (self-describing skill files) being complete and tested

## KEY CHANGE FROM ORIGINAL: Concept Signatures, Not Token Signatures

The original Patch 2 used raw token averages as skill signatures:
```
signature[i] = average(tokens[i]) over 100 training steps
```

This is a lexical fingerprint — it can distinguish "has plus signs" from "has repeating digits" but can't distinguish conceptually similar patterns. It also requires computing signatures during training, which couples the signature to the training data format.

**The revised approach:** Use the model's own learned internal representation as the signature. After a specialist is trained, run a few examples through it and capture the **rule cache vector** (`Wr · resid[write_pos]`). That vector IS the model's concept of "what kind of problem this is." Store that as the signature.

For matching: the coordinator runs a lightweight forward pass on new input (embed + attention + residual — skip FFN and output projection), extracts the residual at the write position, and compares against stored concept signatures. Matching happens in the model's own learned concept space, not raw token space.

## Part A: Revised Skill File Format

### File Layout (updated signature section)
```
Offset  Size    Field
0       8       Magic (0x534B494C4C303031 = "SKILL001")
8       8       DModel
16      8       SeqLen
24      8       VocabSize
32      8       NumHeads
40      8       DFF
48      8       ParamCount
56      8       HasRuleCache (0 or 1)
--- 64 bytes: config header ---

64      var     Concept Signature (DModel × 8 bytes)
                For DModel=64: 512 bytes
                This is the average rule_vec from the trained model
--- 64 + DModel*8 bytes total header ---

Next    N       Weight data (same flat buffer format)
```

**Note:** Signature size is now DModel elements, not fixed 32. This means the signature lives in the same dimensional space as the model's residual stream. For DModel=64, the header is 64 + 512 = 576 bytes before weights.

### Updated TF_WriteSkillHeader:

```ailang
Function.TF_WriteSkillHeader {
    Input: fd: Integer
    Input: signature: Integer   // pointer to concept signature vector [DModel]
    Input: has_rule_cache: Integer
    Output: Integer
    Body: {
        dmod = TFConfig.DModel
        hdr_size = Add(64, Multiply(dmod, 8))
        hdr = Allocate(hdr_size)
        
        // Magic: "SKILL001"
        StoreValue(hdr, 6004626762498105427)
        // Config
        StoreValue(Add(hdr, 8),  TFConfig.DModel)
        StoreValue(Add(hdr, 16), TFConfig.SeqLen)
        StoreValue(Add(hdr, 24), TFConfig.VocabSize)
        StoreValue(Add(hdr, 32), TFConfig.NumHeads)
        StoreValue(Add(hdr, 40), TFConfig.DFF)
        // Param count
        vd  = Multiply(TFConfig.VocabSize, dmod)
        sd  = Multiply(TFConfig.SeqLen, dmod)
        dd  = Multiply(dmod, dmod)
        ffn = Multiply(dmod, TFConfig.DFF)
        tot = Add(Add(Add(Multiply(vd, 2), sd), Multiply(dd, 3)), Multiply(ffn, 2))
        IfCondition EqualTo(has_rule_cache, 1) ThenBlock: {
            tot = Add(tot, dd)
        }
        StoreValue(Add(hdr, 48), tot)
        StoreValue(Add(hdr, 56), has_rule_cache)
        
        // Concept signature: copy DModel values
        sig_i = 0
        WhileLoop LessThan(sig_i, dmod) {
            sig_off = Add(64, Multiply(sig_i, 8))
            sig_val = TF_VecGet(signature, sig_i)
            StoreValue(Add(hdr, sig_off), sig_val)
            sig_i = Add(sig_i, 1)
        }
        
        // Write
        written = SystemCall(1, fd, hdr, hdr_size)
        Deallocate(hdr, hdr_size)
        ReturnValue(written)
    }
}
```

### Updated TF_ReadSkillHeader:

```ailang
Function.TF_ReadSkillHeader {
    Input: fd: Integer
    Input: signature_out: Integer   // pointer to write concept signature [DModel]
    Output: Integer
    Body: {
        // Read fixed config header first (64 bytes)
        cfg = Allocate(64)
        red = SystemCall(0, fd, cfg, 64)
        IfCondition NotEqual(red, 64) ThenBlock: {
            Deallocate(cfg, 64)
            ReturnValue(0)
        }
        // Check magic
        magic = Dereference(cfg)
        IfCondition NotEqual(magic, 6004626762498105427) ThenBlock: {
            Deallocate(cfg, 64)
            ReturnValue(0)
        }
        // Read config
        SkillInfo.DModel    = Dereference(Add(cfg, 8))
        SkillInfo.SeqLen    = Dereference(Add(cfg, 16))
        SkillInfo.VocabSize = Dereference(Add(cfg, 24))
        SkillInfo.NumHeads  = Dereference(Add(cfg, 32))
        SkillInfo.DFF       = Dereference(Add(cfg, 40))
        SkillInfo.Params    = Dereference(Add(cfg, 48))
        SkillInfo.HasRC     = Dereference(Add(cfg, 56))
        Deallocate(cfg, 64)
        
        // Read concept signature (DModel elements)
        sig_size = Multiply(SkillInfo.DModel, 8)
        sig_buf = Allocate(sig_size)
        red2 = SystemCall(0, fd, sig_buf, sig_size)
        IfCondition NotEqual(red2, sig_size) ThenBlock: {
            Deallocate(sig_buf, sig_size)
            ReturnValue(0)
        }
        sig_i = 0
        WhileLoop LessThan(sig_i, SkillInfo.DModel) {
            TF_VecSet(signature_out, sig_i, Dereference(Add(sig_buf, Multiply(sig_i, 8))))
            sig_i = Add(sig_i, 1)
        }
        Deallocate(sig_buf, sig_size)
        
        ReturnValue(1)
    }
}
```

## Part B: Computing Concept Signatures After Training

Instead of accumulating token averages during training, compute the concept signature AFTER convergence by running a few examples through the trained model and averaging the rule vectors.

### New function: Compute concept signature from trained model

```ailang
SubRoutine.ComputeConceptSignature {
    // Run 50 examples through the trained model, average the rule vectors
    cs_dmod = TFConfig.DModel
    cs_count = 50
    
    // Allocate accumulator
    cs_accum = TF_VecAlloc(cs_dmod)
    TF_VecZero(cs_accum, cs_dmod)
    
    cs_i = 0
    WhileLoop LessThan(cs_i, cs_count) {
        ATTN_GenSample()
        ATTN_ConvertWeights()
        TFRuleCache.written = 0
        ATTN_Forward()
        
        // The rule cache vec now contains Wr · resid[write_pos]
        // This IS the concept vector for this input
        cs_j = 0
        WhileLoop LessThan(cs_j, cs_dmod) {
            cs_old = TF_VecGet(cs_accum, cs_j)
            cs_rv = TF_VecGet(TFRuleCache.vec, cs_j)
            TF_VecSet(cs_accum, cs_j, Add(cs_old, cs_rv))
            cs_j = Add(cs_j, 1)
        }
        cs_i = Add(cs_i, 1)
    }
    
    // Average
    cs_j = 0
    WhileLoop LessThan(cs_j, cs_dmod) {
        cs_val = TF_VecGet(cs_accum, cs_j)
        TF_VecSet(TFState.ConceptSig, cs_j, Divide(cs_val, cs_count))
        cs_j = Add(cs_j, 1)
    }
    
    TF_VecFree(cs_accum, cs_dmod)
}
```

### Add to TFState:
```ailang
"ConceptSig": Initialize=0    // pointer to concept signature vector [DModel]
```

### In ATTN_Init:
```ailang
TFState.ConceptSig = TF_VecAlloc(init_dmod)
```

### In the save block (after CONVERGED), before writing skill file:
```ailang
// Compute concept signature from trained model
ComputeConceptSignature()

// Save skill file with concept signature
save_fd = SystemCall(2, TFState.SkillPath, 577, 420)
TF_WriteSkillHeader(save_fd, TFState.ConceptSig, 1)
// ... write weight buffers as before
```

## Part C: Skill Registry with Concept Matching

### Updated FixedPool:
```ailang
FixedPool.SkillRegistry {
    "count":      Initialize=0
    "signatures": Initialize=0     // DModel-dimensional concept vectors per skill
    "paths":      Initialize=0
    "max_skills": Initialize=32
    "sig_dim":    Initialize=0     // set to DModel at init
}
```

### Registry Init:
```ailang
SubRoutine.Registry_Init {
    reg_dmod = TFConfig.DModel
    SkillRegistry.sig_dim = reg_dmod
    // Each skill has a DModel-dimensional signature
    SkillRegistry.signatures = Allocate(Multiply(32, Multiply(reg_dmod, 8)))
    SkillRegistry.paths = Allocate(Multiply(32, 8))
    SkillRegistry.count = 0
}
```

### Registry Add (updated for DModel-dimensional signatures):
```ailang
Function.Registry_AddSkill {
    Input: path: Address
    Input: signature: Integer
    Output: Integer
    Body: {
        idx = SkillRegistry.count
        dmod = SkillRegistry.sig_dim
        IfCondition GreaterEqual(idx, SkillRegistry.max_skills) ThenBlock: {
            PrintMessage("[REGISTRY] Full\n")
            ReturnValue(0)
        }
        StoreValue(Add(SkillRegistry.paths, Multiply(idx, 8)), path)
        // Copy DModel-dimensional signature
        sig_base = Add(SkillRegistry.signatures, Multiply(idx, Multiply(dmod, 8)))
        sig_i = 0
        WhileLoop LessThan(sig_i, dmod) {
            sig_off = Multiply(sig_i, 8)
            StoreValue(Add(sig_base, sig_off), TF_VecGet(signature, sig_i))
            sig_i = Add(sig_i, 1)
        }
        SkillRegistry.count = Add(idx, 1)
        PrintMessage("[REGISTRY] Added skill ")
        PrintNumber(idx)
        PrintMessage(": ")
        PrintString(path)
        PrintMessage("\n")
        ReturnValue(1)
    }
}
```

### Registry Match — concept-space distance:
```ailang
Function.Registry_Match {
    Input: input_sig: Integer   // pointer to DModel-dimensional concept vector
    Output: Integer
    Body: {
        best_idx = -1
        best_dist = 999999999
        dmod = SkillRegistry.sig_dim
        
        idx = 0
        WhileLoop LessThan(idx, SkillRegistry.count) {
            sig_base = Add(SkillRegistry.signatures, Multiply(idx, Multiply(dmod, 8)))
            dist = 0
            sig_i = 0
            WhileLoop LessThan(sig_i, dmod) {
                sig_off = Multiply(sig_i, 8)
                stored_val = Dereference(Add(sig_base, sig_off))
                input_val = TF_VecGet(input_sig, sig_i)
                diff = Subtract(stored_val, input_val)
                IfCondition LessThan(diff, 0) ThenBlock: { diff = Subtract(0, diff) }
                dist = Add(dist, diff)
                sig_i = Add(sig_i, 1)
            }
            
            IfCondition LessThan(dist, best_dist) ThenBlock: {
                best_dist = dist
                best_idx = idx
            }
            idx = Add(idx, 1)
        }
        
        // Threshold — might need tuning for concept space
        IfCondition GreaterThan(best_dist, 50000) ThenBlock: {
            PrintMessage("[REGISTRY] No concept match (dist=")
            PrintNumber(best_dist)
            PrintMessage(")\n")
            ReturnValue(-1)
        }
        
        PrintMessage("[REGISTRY] Matched skill ")
        PrintNumber(best_idx)
        PrintMessage(" (concept dist=")
        PrintNumber(best_dist)
        PrintMessage(")\n")
        ReturnValue(best_idx)
    }
}
```

## Part D: Coordinator — Concept Extraction from New Input

When new input arrives, the coordinator needs to compute a concept vector WITHOUT knowing which specialist to use. It can't run a full specialist forward pass because it doesn't know which weights to load yet.

### Solution: A lightweight "concept encoder" model

The coordinator maintains its own small model (can be very tiny — just embed + attention + residual, no FFN needed). Its job is to project raw input into concept space.

### Option A (Simple — use for Phase 1):
Use the LAST trained specialist's weights to compute the concept vector. This is a bootstrap problem — you need a model to classify, but you need to classify to pick a model. The workaround: load ANY specialist, run the input through just the embedding + attention layers, extract the residual. The residual captures structural information (token relationships, sequence patterns) that is largely independent of which specialist's weights are loaded.

```ailang
SubRoutine.Brain_ComputeInputConcept {
    // Assumes SOME specialist weights are loaded (any will do for structural features)
    // Run minimal forward pass: embed + QKV + attention + residual
    // Skip FFN, skip output projection — we just want the residual
    
    bc_dmod = TFConfig.DModel
    bc_seqln = TFConfig.SeqLen
    bc_tok = TFState.tokens
    
    TFRuleCache.written = 0
    ATTN_ConvertWeights()
    
    // Embed
    TFLayer_Embed(TFW.emb, bc_tok, TFW.Embed, TFW.PosEmb, bc_seqln, bc_dmod)
    
    // QKV Projection
    TFProjCarrier.Wk    = TFW.Wk
    TFProjCarrier.Wv    = TFW.Wv
    TFProjCarrier.seqln = bc_seqln
    TFProjCarrier.dmod  = bc_dmod
    TFLayer_ProjQKV(TFW.qvec, TFW.kvec, TFW.vvec, TFW.emb, TFW.Wq)
    
    // Attention Scores + Causal Mask + Softmax + Context
    TFLayer_AttnScores(TFW.scores, TFW.qvec, TFW.kvec, bc_seqln, bc_dmod, TFConfig.NumHeads)
    
    // Causal mask
    mask_h = 0
    WhileLoop LessThan(mask_h, TFConfig.NumHeads) {
        mask_r = 0
        WhileLoop LessThan(mask_r, bc_seqln) {
            mask_c = Add(mask_r, 1)
            WhileLoop LessThan(mask_c, bc_seqln) {
                mask_row_idx = Add(Multiply(mask_h, bc_seqln), mask_r)
                TF_MatSet(TFW.scores, mask_row_idx, mask_c, bc_seqln, -1000000)
                mask_c = Add(mask_c, 1)
            }
            mask_r = Add(mask_r, 1)
        }
        mask_h = Add(mask_h, 1)
    }
    
    TFLayer_AttnSoftmax(TFW.attn, TFW.scores, bc_seqln, TFConfig.NumHeads)
    TFLayer_Context(TFW.ctx, TFW.attn, TFW.vvec, bc_seqln, bc_dmod, TFConfig.NumHeads)
    TFLayer_Residual(TFW.resid, TFW.ctx, TFW.emb, bc_seqln, bc_dmod)
    
    // Extract concept vector: Wr · resid[write_pos]
    bc_wpos = TFState.RuleWritePos
    bc_src = TF_VecAlloc(bc_dmod)
    bc_col = 0
    WhileLoop LessThan(bc_col, bc_dmod) {
        TF_VecSet(bc_src, bc_col, TF_MatGet(TFW.resid, bc_wpos, bc_col, bc_dmod))
        bc_col = Add(bc_col, 1)
    }
    TF_MatVecMul(TFState.InputConcept, TFW.Wr, bc_src, bc_dmod, bc_dmod)
    TF_VecFree(bc_src, bc_dmod)
}
```

### Add to TFState:
```ailang
"InputConcept": Initialize=0    // pointer to concept vector for current input [DModel]
```

### In ATTN_Init:
```ailang
TFState.InputConcept = TF_VecAlloc(init_dmod)
```

### Option B (Better — Phase 2):
Train a dedicated "concept encoder" specialist whose ONLY job is to project inputs into concept space. It trains on examples from ALL skill types, learning to produce distinct concept vectors for each type. Store it as a special skill file that the brain always loads first.

## Part E: Integrated Brain Loop

```ailang
SubRoutine.Brain_Run {
    Registry_Init()
    
    // Load all skill files from known paths
    // (Future: directory scanning)
    Brain_TryRegister("skills/skill_0.bin")
    Brain_TryRegister("skills/skill_1.bin")
    Brain_TryRegister("skills/skill_2.bin")
    Brain_TryRegister("skills/skill_3.bin")
    
    PrintMessage("\n[BRAIN] ")
    PrintNumber(SkillRegistry.count)
    PrintMessage(" skills loaded\n")
    
    IfCondition EqualTo(SkillRegistry.count, 0) ThenBlock: {
        PrintMessage("[BRAIN] No skills available!\n")
        ReturnValue(0)
    }
    
    // Load the first skill's weights as bootstrap for concept extraction
    first_path = Dereference(SkillRegistry.paths)
    Specialist_LoadWeights(first_path)
    ATTN_ConvertWeights()
    
    // Run inference tests
    brain_test = 0
    WhileLoop LessThan(brain_test, 12) {
        // Generate random test input from a random skill type
        test_type = TF_RandMod(SkillRegistry.count)
        Brain_GenerateTestInput(test_type)
        
        // Print what we're testing
        PrintMessage("\n[TEST ")
        PrintNumber(brain_test)
        PrintMessage("] Type=")
        PrintNumber(test_type)
        PrintMessage(" Input: ")
        inf_pp = 0
        WhileLoop LessThan(inf_pp, 8) {
            PrintNumber(TF_VecGet(TFState.tokens, inf_pp))
            PrintMessage(" ")
            inf_pp = Add(inf_pp, 1)
        }
        PrintMessage("...")
        
        // Compute concept vector from input
        Brain_ComputeInputConcept()
        
        // Match against registry
        matched = Registry_Match(TFState.InputConcept)
        
        IfCondition GreaterEqual(matched, 0) ThenBlock: {
            // Load matched specialist
            matched_path = Dereference(Add(SkillRegistry.paths, Multiply(matched, 8)))
            Specialist_LoadWeights(matched_path)
            ATTN_ConvertWeights()
            
            // Full forward pass + autoregressive generation
            TFRuleCache.written = 0
            
            PrintMessage("\n  => ")
            
            inf_gen = 4
            WhileLoop LessThan(inf_gen, TFConfig.SeqLen) {
                ATTN_Forward()
                inf_read = Subtract(inf_gen, 1)
                inf_col = 0
                inf_best = 0
                inf_best_val = -999999
                WhileLoop LessThan(inf_col, TFConfig.VocabSize) {
                    inf_v = TF_MatGet(TFW.probs, inf_read, inf_col, TFConfig.VocabSize)
                    IfCondition GreaterThan(inf_v, inf_best_val) ThenBlock: {
                        inf_best_val = inf_v
                        inf_best = inf_col
                    }
                    inf_col = Add(inf_col, 1)
                }
                TF_VecSet(TFState.tokens, inf_gen, inf_best)
                inf_gen = Add(inf_gen, 1)
            }
            
            // Print output
            inf_pp = 4
            WhileLoop LessThan(inf_pp, TFConfig.SeqLen) {
                inf_out = TF_VecGet(TFState.tokens, inf_pp)
                // Stop at separator token for arithmetic
                IfCondition EqualTo(inf_out, 14) ThenBlock: {
                    inf_pp = TFConfig.SeqLen
                } ElseBlock: {
                    PrintNumber(inf_out)
                    PrintMessage(" ")
                    inf_pp = Add(inf_pp, 1)
                }
            }
            
            // Report match correctness
            IfCondition EqualTo(matched, test_type) ThenBlock: {
                PrintMessage(" [CORRECT ROUTING]")
            } ElseBlock: {
                PrintMessage(" [WRONG ROUTING: expected ")
                PrintNumber(test_type)
                PrintMessage("]")
            }
            PrintMessage("\n")
            
        } ElseBlock: {
            PrintMessage("\n  => [UNKNOWN PATTERN]\n")
        }
        
        brain_test = Add(brain_test, 1)
    }
}
```

### Brain_GenerateTestInput — create test prompts for each skill type:
```ailang
Function.Brain_GenerateTestInput {
    Input: skill_type: Integer
    Body: {
        seqln = TFConfig.SeqLen
        start = TF_RandMod(10)
        
        IfCondition EqualTo(skill_type, 0) ThenBlock: {
            // Count by 2
            pp = 0
            WhileLoop LessThan(pp, seqln) {
                TF_VecSet(TFState.tokens, pp, Modulo(Add(start, Multiply(pp, 2)), 10))
                pp = Add(pp, 1)
            }
        }
        IfCondition EqualTo(skill_type, 1) ThenBlock: {
            // Count by 1
            pp = 0
            WhileLoop LessThan(pp, seqln) {
                TF_VecSet(TFState.tokens, pp, Modulo(Add(start, pp), 10))
                pp = Add(pp, 1)
            }
        }
        IfCondition EqualTo(skill_type, 2) ThenBlock: {
            // Repeat-3
            pp = 0
            WhileLoop LessThan(pp, seqln) {
                TF_VecSet(TFState.tokens, pp, Modulo(Add(start, Modulo(pp, 3)), 10))
                pp = Add(pp, 1)
            }
        }
        IfCondition EqualTo(skill_type, 3) ThenBlock: {
            // Addition prompt: A + B =
            a = TF_RandMod(10)
            b = TF_RandMod(10)
            TF_VecSet(TFState.tokens, 0, a)
            TF_VecSet(TFState.tokens, 1, 10)  // +
            TF_VecSet(TFState.tokens, 2, b)
            TF_VecSet(TFState.tokens, 3, 13)  // =
            pp = 4
            WhileLoop LessThan(pp, seqln) {
                TF_VecSet(TFState.tokens, pp, 0)
                pp = Add(pp, 1)
            }
        }
        ReturnValue(0)
    }
}
```

## Part F: Weight Hot-Swap (unchanged from original)

```ailang
Function.Specialist_LoadWeights {
    Input: path: Address
    Output: Integer
    Body: {
        fd = SystemCall(2, path, 0, 0)
        IfCondition LessThan(fd, 0) ThenBlock: {
            PrintMessage("[SPECIALIST] Cannot open: ")
            PrintString(path)
            PrintMessage("\n")
            ReturnValue(0)
        }
        
        tmp_sig = TF_VecAlloc(TFConfig.DModel)
        ok = TF_ReadSkillHeader(fd, tmp_sig)
        TF_VecFree(tmp_sig, TFConfig.DModel)
        
        IfCondition EqualTo(ok, 0) ThenBlock: {
            SystemCall(3, fd)
            ReturnValue(0)
        }
        
        IfCondition NotEqual(SkillInfo.DModel, TFConfig.DModel) ThenBlock: {
            PrintMessage("[SPECIALIST] DModel mismatch\n")
            SystemCall(3, fd)
            ReturnValue(0)
        }
        
        TF_ReadBuffer(fd, TFWf.Embed,  Multiply(SkillInfo.VocabSize, SkillInfo.DModel))
        TF_ReadBuffer(fd, TFWf.PosEmb, Multiply(SkillInfo.SeqLen, SkillInfo.DModel))
        TF_ReadBuffer(fd, TFWf.Wq,     Multiply(SkillInfo.DModel, SkillInfo.DModel))
        TF_ReadBuffer(fd, TFWf.Wk,     Multiply(SkillInfo.DModel, SkillInfo.DModel))
        TF_ReadBuffer(fd, TFWf.Wv,     Multiply(SkillInfo.DModel, SkillInfo.DModel))
        TF_ReadBuffer(fd, TFWf.W1,     Multiply(SkillInfo.DModel, SkillInfo.DFF))
        TF_ReadBuffer(fd, TFWf.W2,     Multiply(SkillInfo.DFF, SkillInfo.DModel))
        TF_ReadBuffer(fd, TFWf.Wout,   Multiply(SkillInfo.VocabSize, SkillInfo.DModel))
        
        IfCondition EqualTo(SkillInfo.HasRC, 1) ThenBlock: {
            TF_ReadBuffer(fd, TFWf.Wr, Multiply(SkillInfo.DModel, SkillInfo.DModel))
        }
        
        SystemCall(3, fd)
        
        PrintMessage("[SPECIALIST] Loaded: ")
        PrintString(path)
        PrintMessage("\n")
        ReturnValue(1)
    }
}
```

## Part G: Main Entry Point with Mode Switch

```ailang
SubRoutine.Main {
    ATTN_Init()
    
    IfCondition EqualTo(TrainJob.Mode, 0) ThenBlock: {
        // Training mode — auto-train all skills sequentially
        // (existing auto-train loop from Patch 1)
        ATTN_AutoTrainAll()
    }
    
    IfCondition EqualTo(TrainJob.Mode, 1) ThenBlock: {
        // Brain mode — load specialists and run integrated inference
        Brain_Run()
    }
    
    ATTN_Shutdown()
}
```

## Rules (DO NOT VIOLATE)
- No TF_VecScale in forward or backward pass
- No /256 gradient rescaling
- No weight decay
- Do not modify Library.Layer.ailang, Library.Train.ailang, Library.Act.ailang
- Do not modify the forward or backward pass
- Do not modify the causal mask or rule cache
- Max 6 inputs per function — use carriers if needed
- The concept signature computation reuses the existing rule cache mechanism — do NOT add new forward pass code, just call the existing functions

## Testing

### After all 4 specialists are trained (Patch 1 auto-train):
1. Set TrainJob.Mode = 1, recompile
2. Run — brain loads all skill files
3. For each test: generates input, computes concept vector, matches, loads specialist, generates output
4. Check [CORRECT ROUTING] vs [WRONG ROUTING] — the concept matching should correctly identify which skill each input belongs to
5. Check generated output — the loaded specialist should produce correct continuations

### Expected Output:
```
[REGISTRY] Added skill 0: skills/skill_0.bin
[REGISTRY] Added skill 1: skills/skill_1.bin
[REGISTRY] Added skill 2: skills/skill_2.bin
[REGISTRY] Added skill 3: skills/skill_3.bin

[BRAIN] 4 skills loaded

[TEST 0] Type=1 Input: 3 4 5 6 7 8 9 0 ...
[REGISTRY] Matched skill 1 (concept dist=234)
[SPECIALIST] Loaded: skills/skill_1.bin
  => 1 2 3 4 5 6 7 8 9 0 1 2 3 4 ...  [CORRECT ROUTING]

[TEST 1] Type=2 Input: 4 5 6 4 5 6 4 5 ...
[REGISTRY] Matched skill 2 (concept dist=189)
[SPECIALIST] Loaded: skills/skill_2.bin
  => 6 4 5 6 4 5 6 4 5 6 4 ...  [CORRECT ROUTING]

[TEST 2] Type=3 Input: 7 10 3 13 0 0 0 0 ...
[REGISTRY] Matched skill 3 (concept dist=412)
[SPECIALIST] Loaded: skills/skill_3.bin
  => 1 0  [CORRECT ROUTING]
```

## Files Changed
- Library.TFLoadStore.ailang: UPDATE TF_WriteSkillHeader, TF_ReadSkillHeader (concept signatures)
- ATTN.ailang: ADD ComputeConceptSignature, Brain_ComputeInputConcept, Brain_GenerateTestInput
- ATTN.ailang: ADD Registry_Init, Registry_AddSkill, Registry_Match (concept-space matching)
- ATTN.ailang: ADD Specialist_LoadWeights, Brain_Run, Brain_TryRegister
- ATTN.ailang: UPDATE save block (concept signature instead of token average)
- ATTN.ailang: UPDATE Main (mode switch)


---

## 🤖 Gemini's Architecture Notes (April 2026)

*Note: Holding implementation until the Addition Target Masking proves successful.*

**1. Cross-Weight Concept Extraction Fragility:**
In Part D (Option A), using *any* currently loaded specialist's weights to extract the concept vector for a *new* input is a brilliant bootstrap hack. However, because this architecture does not use LayerNorm, the magnitude of the residual stream is highly dependent on the specific `Wq/Wk/Wv/W1/W2` weights. An `adder` model might project a `counting` sequence into a vastly different numerical space than a `skipper` model would. 
*Recommendation:* If routing accuracy is low or inconsistent during testing, we should fast-track Option B (a dedicated, frozen Concept Encoder model) to ensure the concept space is stable regardless of which specialist was used last.

**2. Distance Threshold (50,000):**
In `Registry_Match`, the threshold is set to `50000`. With `DModel=64` and our raw integer accumulators, L1 distances could easily exceed this if the residual vectors are large. We may need to monitor the `best_dist` logs closely and either adjust this threshold or implement a simple vector normalization (scaling) before the distance calculation.

**3. Target Masking Compatibility:**
Since we just implemented Target Masking in `ATTN_GenSample` to fix the Addition task, `ComputeConceptSignature` will inherit those masks automatically. Because these functions only perform Forward passes (no Backward pass or SGD), the target masks won't interfere, but the fact that `ATTN_GenSample` safely initializes them ensures we won't hit any uninitialized memory during the concept generation phase!