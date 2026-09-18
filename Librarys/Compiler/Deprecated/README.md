# Deprecated emit libraries

Hand-encoded `X86_*` opcode files superseded by:

- `Library.CEmitX86Enc.ailang` (generated assembler)
- `Library.CEmitCoreArch.ailang` (generated `Emit_*` → Assemble)
- `Library.CEmitKeep.ailang` (remaining mem/fixup/frame/Enc-gap helpers)

Not on the compiler import graph. Kept for rollback / archaeology.
