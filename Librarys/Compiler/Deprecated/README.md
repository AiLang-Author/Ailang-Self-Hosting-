# Deprecated emit libraries

Hand-encoded `X86_*` opcode files superseded by:

- `Library.CEmitX86Enc.ailang` (generated assembler)
- `Library.CEmitCoreArch.ailang` (generated `Emit_*` → Assemble)
- `Library.CEmitKeep.ailang` (remaining mem/fixup/frame/Enc-gap helpers)

Not on the compiler import graph. Kept for rollback / archaeology.

The V1.0.0 compiler retired on 2026-10-06 is `ailang-2026-10-04.x` in this directory: 3,186,548 bytes, sha256 `e47de63c09611f246acb958fcec0a6d71111c9fbf19d13510c136fb1e7c88b3d`, built 2026-10-04. `*.x` stays ignored except the live `ailang.x`, so this copy is local. The same bytes are `ailang.x` in commit `9ebc16bb`.

The compiler replaced later the same day, when the cursor field fold was installed, is `ailang-2026-10-06-bdf49c48.x`: 3,099,699 bytes, sha256 `bdf49c483b2301112a384c7140025132f69b629a2013f022cef9c6d975a42e04`. Local only.

The compiler replaced when InlineAsm functions stopped being spliced is `ailang-2026-10-06-f3aac2f4.x`: 3,103,795 bytes, sha256 `f3aac2f4f59812e29828fe734cb0c927bcb02cd6fe436a681770d2da43886615`. Local only.
