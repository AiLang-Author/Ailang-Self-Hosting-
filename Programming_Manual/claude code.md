/mnt/c/Users/Sean/Documents/AILangSH# ATTN Bug Fixes

## Fix 1: Remove the ×32 scaling factor from attention scores

**File:** Library.Layer.ailang  
**Function:** TFLayer_AttnScores

Find:
```
sc_div = Multiply(scale, 32)
sc     = Divide(raw, sc_div)
```

Replace with:
```
sc = Divide(raw, scale)
```

**Why:** The standard transformer divides Q·K by √d. `scale = TF_ISqrt(16) = 4`, which is correct. The extra `×32` crushes the score range, making attention weights nearly uniform (~1/8 per position). The model can't attend to anything — every position sees the same averaged context, so it collapses to predicting the same tokens.

---

## Fix 2: Remove the matching ×32 from backward dScores

**File:** Library.Train.ailang  
**Function:** TFTrain_BackAttnCtx

Find:
```
sc_div_f = Float_FromInt(Multiply(scale, 32))
raw_ds_f = Float_Div(raw_ds_f, sc_div_f)
```

Replace with:
```
raw_ds_f = Float_Div(raw_ds_f, Float_FromInt(scale))
```

**Why:** The backward pass must match the forward pass scaling. With ×32 removed from forward, it must be removed from backward too, otherwise gradients flowing through attention are 32× too small and vanish.

---

## Summary of the problem

With `Multiply(scale, 32)`:
- Attention scores: small integers (10-23 range)
- Attention weights after softmax: nearly uniform (~32 each in Q8 ≈ 0.125, i.e. 1/8)
- Context vectors: mean of all V vectors at every position (no differentiation)
- Model degenerates to predicting the same tokens for all inputs

Without the ×32:
- Scores have 32× more dynamic range
- Softmax produces peaked distributions
- Attention can actually route information per-position
- Gradients flow back through attention properly