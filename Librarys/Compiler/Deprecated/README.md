# Deprecated emit libraries

Hand-encoded `X86_*` opcode files superseded by:

- `Library.CEmitX86Enc.ailang` (generated assembler)
- `Library.CEmitCoreArch.ailang` (generated `Emit_*` → Assemble)
- `Library.CEmitKeep.ailang` (remaining mem/fixup/frame/Enc-gap helpers)

Not on the compiler import graph. Kept for rollback / archaeology.

The V1.0.0 compiler retired on 2026-10-06 is `ailang-2026-10-04.x` in this directory: 3,186,548 bytes, sha256 `e47de63c09611f246acb958fcec0a6d71111c9fbf19d13510c136fb1e7c88b3d`, built 2026-10-04. `*.x` stays ignored except the live `ailang.x`, so this copy is local. The same bytes are `ailang.x` in commit `9ebc16bb`.
