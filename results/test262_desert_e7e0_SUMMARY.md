# Desert e7e0 — 2064/2931 (70.8%)

After e7dz 2058. **+6** from SpeciesConstructor TypeError paths.

## Fixes
- Non-constructor `@@species` (0/string/{}): exc_prop only (no ThrowValue VM-error)
- SpeciesConstructor step 4: Type(C) not Object → TypeError (incl. null/number/bool/NaN)
- Symbols are OBJECT-tagged but ES Type is Symbol → treat via JSVM_IsSymbol
- Subarray TypedArraySpeciesCreate: same non-Object/Symbol TypeError; no ThrowValue

## Score
TOTAL 2064/2931 (70.8%). Goal 95% ≈ 2784 (−720 remaining).
