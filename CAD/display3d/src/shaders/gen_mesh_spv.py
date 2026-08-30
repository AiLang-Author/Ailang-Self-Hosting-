#!/usr/bin/env python3
# Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
# Licensed under the Sean Collins Software License (SCSL v1.0).

"""Emit embedded SPIR-V for the default mesh graphics pipeline.

This is the *default* Display3D shader, not the Vulkan core. Compiler /
display / CAD consumers can bind their own SPIR-V via AilangVk_CreatePipeline.
No glslang required — the binary is generated from a tiny assembler.
"""
from __future__ import annotations

import os
import struct

# Opcodes we need (SPIR-V 1.0)
OpNop = 0
OpUndef = 1
OpSource = 3
OpName = 5
OpMemberName = 6
OpExtInstImport = 11
OpExtInst = 12
OpMemoryModel = 14
OpEntryPoint = 15
OpExecutionMode = 16
OpCapability = 17
OpTypeVoid = 19
OpTypeBool = 20
OpTypeInt = 21
OpTypeFloat = 22
OpTypeVector = 23
OpTypeMatrix = 24
OpTypeStruct = 30
OpTypePointer = 32
OpTypeFunction = 33
OpConstant = 43
OpConstantComposite = 44
OpFunction = 54
OpFunctionEnd = 56
OpVariable = 59
OpLoad = 61
OpStore = 62
OpAccessChain = 65
OpDecorate = 71
OpMemberDecorate = 72
OpCompositeConstruct = 80
OpCompositeExtract = 81
OpFAdd = 129
OpFMul = 133
OpVectorTimesScalar = 142
OpMatrixTimesVector = 145
OpDot = 148
OpLabel = 248
OpReturn = 253

# Extra
StorageFunction = 7
StorageInput = 1
StorageOutput = 3
StorageUniform = 2
AddressingLogical = 0
MemoryGLSL450 = 1
ExecVertex = 0
ExecFragment = 4
OriginUpperLeft = 7
CapabilityShader = 1
DecorationBlock = 2
DecorationColMajor = 5
DecorationMatrixStride = 7
DecorationBuiltIn = 11
DecorationLocation = 30
DecorationBinding = 33
DecorationDescriptorSet = 34
DecorationOffset = 35
BuiltInPosition = 0
FunctionControlNone = 0
GLSL_Normalize = 69
GLSL_FAbs = 4


def pack_str(s: str) -> list[int]:
    b = s.encode("utf-8") + b"\x00"
    while len(b) % 4:
        b += b"\x00"
    words = []
    for i in range(0, len(b), 4):
        words.append(struct.unpack_from("<I", b, i)[0])
    return words


class Module:
    def __init__(self) -> None:
        self.bound = 1
        self.preamble: list[int] = []
        self.debug: list[int] = []
        self.anno: list[int] = []
        self.types: list[int] = []
        self.funcs: list[int] = []

    def nid(self) -> int:
        i = self.bound
        self.bound += 1
        return i

    def emit(self, bucket: list[int], op: int, *words: int) -> None:
        wc = 1 + len(words)
        bucket.append((wc << 16) | op)
        bucket.extend(words)

    def finish(self) -> bytes:
        body = self.preamble + self.debug + self.anno + self.types + self.funcs
        header = [0x07230203, 0x00010000, 0x000A11A6, self.bound, 0]
        words = header + body
        return struct.pack("<%dI" % len(words), *words)


def build_vert() -> bytes:
    """Clip-space pass-through: gl_Position = vec4(inPos, 1).
    MVP lives in the CPU/SSE2 path and in a later UBO shader once validated."""
    m = Module()
    m.emit(m.preamble, OpCapability, CapabilityShader)
    m.emit(m.preamble, OpMemoryModel, AddressingLogical, MemoryGLSL450)

    main = m.nid()
    gl_pos = m.nid()
    v_nrm = m.nid()
    v_col = m.nid()
    in_pos = m.nid()
    in_nrm = m.nid()
    in_uv = m.nid()
    in_col = m.nid()

    m.emit(
        m.preamble,
        OpEntryPoint,
        ExecVertex,
        main,
        *pack_str("main"),
        gl_pos,
        v_nrm,
        v_col,
        in_pos,
        in_nrm,
        in_uv,
        in_col,
    )

    m.emit(m.debug, OpName, main, *pack_str("main"))
    m.emit(m.anno, OpDecorate, gl_pos, DecorationBuiltIn, BuiltInPosition)
    m.emit(m.anno, OpDecorate, v_nrm, DecorationLocation, 0)
    m.emit(m.anno, OpDecorate, v_col, DecorationLocation, 1)
    m.emit(m.anno, OpDecorate, in_pos, DecorationLocation, 0)
    m.emit(m.anno, OpDecorate, in_nrm, DecorationLocation, 1)
    m.emit(m.anno, OpDecorate, in_uv, DecorationLocation, 2)
    m.emit(m.anno, OpDecorate, in_col, DecorationLocation, 3)

    ty_void = m.nid()
    ty_fn = m.nid()
    ty_f32 = m.nid()
    ty_v2 = m.nid()
    ty_v3 = m.nid()
    ty_v4 = m.nid()
    ty_in_v2 = m.nid()
    ty_in_v3 = m.nid()
    ty_in_v4 = m.nid()
    ty_out_v3 = m.nid()
    ty_out_v4 = m.nid()
    c_f1 = m.nid()

    m.emit(m.types, OpTypeVoid, ty_void)
    m.emit(m.types, OpTypeFunction, ty_fn, ty_void)
    m.emit(m.types, OpTypeFloat, ty_f32, 32)
    m.emit(m.types, OpTypeVector, ty_v2, ty_f32, 2)
    m.emit(m.types, OpTypeVector, ty_v3, ty_f32, 3)
    m.emit(m.types, OpTypeVector, ty_v4, ty_f32, 4)
    m.emit(m.types, OpTypePointer, ty_in_v2, StorageInput, ty_v2)
    m.emit(m.types, OpTypePointer, ty_in_v3, StorageInput, ty_v3)
    m.emit(m.types, OpTypePointer, ty_in_v4, StorageInput, ty_v4)
    m.emit(m.types, OpTypePointer, ty_out_v3, StorageOutput, ty_v3)
    m.emit(m.types, OpTypePointer, ty_out_v4, StorageOutput, ty_v4)
    m.emit(m.types, OpConstant, ty_f32, c_f1, struct.unpack("<I", struct.pack("<f", 1.0))[0])

    m.emit(m.types, OpVariable, ty_out_v4, gl_pos, StorageOutput)
    m.emit(m.types, OpVariable, ty_out_v3, v_nrm, StorageOutput)
    m.emit(m.types, OpVariable, ty_out_v4, v_col, StorageOutput)
    m.emit(m.types, OpVariable, ty_in_v3, in_pos, StorageInput)
    m.emit(m.types, OpVariable, ty_in_v3, in_nrm, StorageInput)
    m.emit(m.types, OpVariable, ty_in_v2, in_uv, StorageInput)
    m.emit(m.types, OpVariable, ty_in_v4, in_col, StorageInput)

    m.emit(m.funcs, OpFunction, ty_void, main, FunctionControlNone, ty_fn)
    lab = m.nid()
    m.emit(m.funcs, OpLabel, lab)

    nrm = m.nid()
    col = m.nid()
    pos = m.nid()
    uv = m.nid()
    m.emit(m.funcs, OpLoad, ty_v3, nrm, in_nrm)
    m.emit(m.funcs, OpStore, v_nrm, nrm)
    m.emit(m.funcs, OpLoad, ty_v4, col, in_col)
    m.emit(m.funcs, OpStore, v_col, col)
    m.emit(m.funcs, OpLoad, ty_v2, uv, in_uv)
    m.emit(m.funcs, OpLoad, ty_v3, pos, in_pos)

    px = m.nid()
    py = m.nid()
    pz = m.nid()
    m.emit(m.funcs, OpCompositeExtract, ty_f32, px, pos, 0)
    m.emit(m.funcs, OpCompositeExtract, ty_f32, py, pos, 1)
    m.emit(m.funcs, OpCompositeExtract, ty_f32, pz, pos, 2)
    pos4 = m.nid()
    m.emit(m.funcs, OpCompositeConstruct, ty_v4, pos4, px, py, pz, c_f1)
    m.emit(m.funcs, OpStore, gl_pos, pos4)
    m.emit(m.funcs, OpReturn)
    m.emit(m.funcs, OpFunctionEnd)
    return m.finish()


def build_vert_ubo() -> bytes:
    """gl_Position = ubo.mvp * vec4(inPos,1) via four column dots (no OpMatrixTimesVector)."""
    m = Module()
    m.emit(m.preamble, OpCapability, CapabilityShader)
    m.emit(m.preamble, OpMemoryModel, AddressingLogical, MemoryGLSL450)

    main = m.nid()
    gl_pos = m.nid()
    v_nrm = m.nid()
    v_col = m.nid()
    in_pos = m.nid()
    in_nrm = m.nid()
    in_uv = m.nid()
    in_col = m.nid()
    ubo = m.nid()

    m.emit(
        m.preamble,
        OpEntryPoint,
        ExecVertex,
        main,
        *pack_str("main"),
        gl_pos, v_nrm, v_col, in_pos, in_nrm, in_uv, in_col,
    )
    m.emit(m.anno, OpDecorate, gl_pos, DecorationBuiltIn, BuiltInPosition)
    m.emit(m.anno, OpDecorate, v_nrm, DecorationLocation, 0)
    m.emit(m.anno, OpDecorate, v_col, DecorationLocation, 1)
    m.emit(m.anno, OpDecorate, in_pos, DecorationLocation, 0)
    m.emit(m.anno, OpDecorate, in_nrm, DecorationLocation, 1)
    m.emit(m.anno, OpDecorate, in_uv, DecorationLocation, 2)
    m.emit(m.anno, OpDecorate, in_col, DecorationLocation, 3)
    m.emit(m.anno, OpDecorate, ubo, DecorationDescriptorSet, 0)
    m.emit(m.anno, OpDecorate, ubo, DecorationBinding, 0)

    ty_void = m.nid()
    ty_fn = m.nid()
    ty_f32 = m.nid()
    ty_u32 = m.nid()
    ty_v2 = m.nid()
    ty_v3 = m.nid()
    ty_v4 = m.nid()
    ty_m4 = m.nid()
    ty_ubo = m.nid()
    ty_in_v2 = m.nid()
    ty_in_v3 = m.nid()
    ty_in_v4 = m.nid()
    ty_out_v3 = m.nid()
    ty_out_v4 = m.nid()
    ty_uni_ubo = m.nid()
    ty_uni_v4 = m.nid()
    c_f1 = m.nid()
    c0 = m.nid()
    c1 = m.nid()
    c2 = m.nid()
    c3 = m.nid()

    m.emit(m.types, OpTypeVoid, ty_void)
    m.emit(m.types, OpTypeFunction, ty_fn, ty_void)
    m.emit(m.types, OpTypeFloat, ty_f32, 32)
    m.emit(m.types, OpTypeInt, ty_u32, 32, 0)
    m.emit(m.types, OpTypeVector, ty_v2, ty_f32, 2)
    m.emit(m.types, OpTypeVector, ty_v3, ty_f32, 3)
    m.emit(m.types, OpTypeVector, ty_v4, ty_f32, 4)
    m.emit(m.types, OpTypeMatrix, ty_m4, ty_v4, 4)
    m.emit(m.types, OpTypeStruct, ty_ubo, ty_m4, ty_v4)
    m.emit(m.types, OpTypePointer, ty_in_v2, StorageInput, ty_v2)
    m.emit(m.types, OpTypePointer, ty_in_v3, StorageInput, ty_v3)
    m.emit(m.types, OpTypePointer, ty_in_v4, StorageInput, ty_v4)
    m.emit(m.types, OpTypePointer, ty_out_v3, StorageOutput, ty_v3)
    m.emit(m.types, OpTypePointer, ty_out_v4, StorageOutput, ty_v4)
    m.emit(m.types, OpTypePointer, ty_uni_ubo, StorageUniform, ty_ubo)
    m.emit(m.types, OpTypePointer, ty_uni_v4, StorageUniform, ty_v4)
    m.emit(m.types, OpConstant, ty_f32, c_f1, struct.unpack("<I", struct.pack("<f", 1.0))[0])
    m.emit(m.types, OpConstant, ty_u32, c0, 0)
    m.emit(m.types, OpConstant, ty_u32, c1, 1)
    m.emit(m.types, OpConstant, ty_u32, c2, 2)
    m.emit(m.types, OpConstant, ty_u32, c3, 3)

    m.emit(m.anno, OpDecorate, ty_ubo, DecorationBlock)
    m.emit(m.anno, OpMemberDecorate, ty_ubo, 0, DecorationColMajor)
    m.emit(m.anno, OpMemberDecorate, ty_ubo, 0, DecorationOffset, 0)
    m.emit(m.anno, OpMemberDecorate, ty_ubo, 0, DecorationMatrixStride, 16)
    m.emit(m.anno, OpMemberDecorate, ty_ubo, 1, DecorationOffset, 64)

    m.emit(m.types, OpVariable, ty_out_v4, gl_pos, StorageOutput)
    m.emit(m.types, OpVariable, ty_out_v3, v_nrm, StorageOutput)
    m.emit(m.types, OpVariable, ty_out_v4, v_col, StorageOutput)
    m.emit(m.types, OpVariable, ty_in_v3, in_pos, StorageInput)
    m.emit(m.types, OpVariable, ty_in_v3, in_nrm, StorageInput)
    m.emit(m.types, OpVariable, ty_in_v2, in_uv, StorageInput)
    m.emit(m.types, OpVariable, ty_in_v4, in_col, StorageInput)
    m.emit(m.types, OpVariable, ty_uni_ubo, ubo, StorageUniform)

    m.emit(m.funcs, OpFunction, ty_void, main, FunctionControlNone, ty_fn)
    lab = m.nid()
    m.emit(m.funcs, OpLabel, lab)

    nrm = m.nid(); col = m.nid(); pos = m.nid(); uv = m.nid()
    m.emit(m.funcs, OpLoad, ty_v3, nrm, in_nrm)
    m.emit(m.funcs, OpStore, v_nrm, nrm)
    m.emit(m.funcs, OpLoad, ty_v4, col, in_col)
    m.emit(m.funcs, OpStore, v_col, col)
    m.emit(m.funcs, OpLoad, ty_v2, uv, in_uv)
    m.emit(m.funcs, OpLoad, ty_v3, pos, in_pos)
    px = m.nid(); py = m.nid(); pz = m.nid(); pos4 = m.nid()
    m.emit(m.funcs, OpCompositeExtract, ty_f32, px, pos, 0)
    m.emit(m.funcs, OpCompositeExtract, ty_f32, py, pos, 1)
    m.emit(m.funcs, OpCompositeExtract, ty_f32, pz, pos, 2)
    m.emit(m.funcs, OpCompositeConstruct, ty_v4, pos4, px, py, pz, c_f1)

    def load_col(idx):
        ptr = m.nid()
        val = m.nid()
        m.emit(m.funcs, OpAccessChain, ty_uni_v4, ptr, ubo, c0, idx)
        m.emit(m.funcs, OpLoad, ty_v4, val, ptr)
        return val

    col0 = load_col(c0)
    col1 = load_col(c1)
    col2 = load_col(c2)
    col3 = load_col(c3)
    t0 = m.nid(); t1 = m.nid(); t2 = m.nid(); t3 = m.nid()
    s0 = m.nid(); s1 = m.nid(); clip = m.nid()
    m.emit(m.funcs, OpVectorTimesScalar, ty_v4, t0, col0, px)
    m.emit(m.funcs, OpVectorTimesScalar, ty_v4, t1, col1, py)
    m.emit(m.funcs, OpVectorTimesScalar, ty_v4, t2, col2, pz)
    m.emit(m.funcs, OpVectorTimesScalar, ty_v4, t3, col3, c_f1)
    m.emit(m.funcs, OpFAdd, ty_v4, s0, t0, t1)
    m.emit(m.funcs, OpFAdd, ty_v4, s1, t2, t3)
    m.emit(m.funcs, OpFAdd, ty_v4, clip, s0, s1)
    m.emit(m.funcs, OpStore, gl_pos, clip)
    m.emit(m.funcs, OpReturn)
    m.emit(m.funcs, OpFunctionEnd)
    return m.finish()


def build_frag() -> bytes:
    """Pass color through. Lighting is applied in the vertex UBO path later;
    keep the fragment module tiny so lavapipe cannot JIT-crash on ExtInst."""
    m = Module()
    m.emit(m.preamble, OpCapability, CapabilityShader)
    m.emit(m.preamble, OpMemoryModel, AddressingLogical, MemoryGLSL450)

    main = m.nid()
    out_col = m.nid()
    v_nrm = m.nid()
    v_col = m.nid()

    m.emit(
        m.preamble,
        OpEntryPoint,
        ExecFragment,
        main,
        *pack_str("main"),
        out_col,
        v_nrm,
        v_col,
    )
    m.emit(m.preamble, OpExecutionMode, main, OriginUpperLeft)

    m.emit(m.anno, OpDecorate, out_col, DecorationLocation, 0)
    m.emit(m.anno, OpDecorate, v_nrm, DecorationLocation, 0)
    m.emit(m.anno, OpDecorate, v_col, DecorationLocation, 1)

    ty_void = m.nid()
    ty_fn = m.nid()
    ty_f32 = m.nid()
    ty_v3 = m.nid()
    ty_v4 = m.nid()
    ty_in_v3 = m.nid()
    ty_in_v4 = m.nid()
    ty_out_v4 = m.nid()

    m.emit(m.types, OpTypeVoid, ty_void)
    m.emit(m.types, OpTypeFunction, ty_fn, ty_void)
    m.emit(m.types, OpTypeFloat, ty_f32, 32)
    m.emit(m.types, OpTypeVector, ty_v3, ty_f32, 3)
    m.emit(m.types, OpTypeVector, ty_v4, ty_f32, 4)
    m.emit(m.types, OpTypePointer, ty_in_v3, StorageInput, ty_v3)
    m.emit(m.types, OpTypePointer, ty_in_v4, StorageInput, ty_v4)
    m.emit(m.types, OpTypePointer, ty_out_v4, StorageOutput, ty_v4)

    m.emit(m.types, OpVariable, ty_out_v4, out_col, StorageOutput)
    m.emit(m.types, OpVariable, ty_in_v3, v_nrm, StorageInput)
    m.emit(m.types, OpVariable, ty_in_v4, v_col, StorageInput)

    m.emit(m.funcs, OpFunction, ty_void, main, FunctionControlNone, ty_fn)
    lab = m.nid()
    m.emit(m.funcs, OpLabel, lab)
    col = m.nid()
    nrm = m.nid()
    m.emit(m.funcs, OpLoad, ty_v4, col, v_col)
    m.emit(m.funcs, OpLoad, ty_v3, nrm, v_nrm)  # keep the interpolator live
    (void_use := nrm)
    m.emit(m.funcs, OpStore, out_col, col)
    m.emit(m.funcs, OpReturn)
    m.emit(m.funcs, OpFunctionEnd)
    return m.finish()


def emit_header(path: str, symbol: str, blob: bytes) -> None:
    words = list(struct.unpack("<%dI" % (len(blob) // 4), blob))
    lines = [
        "/* Auto-generated by gen_mesh_spv.py — do not edit. */",
        "#ifndef %s_H" % symbol.upper(),
        "#define %s_H" % symbol.upper(),
        "#include <stdint.h>",
        "static const uint32_t %s[] = {" % symbol,
    ]
    row = []
    for i, w in enumerate(words):
        row.append("0x%08x" % w)
        if len(row) == 6:
            lines.append("    " + ", ".join(row) + ",")
            row = []
    if row:
        lines.append("    " + ", ".join(row) + ",")
    lines.append("};")
    lines.append("static const uint32_t %s_WORDS = %d;" % (symbol, len(words)))
    lines.append("#endif")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    vert = build_vert()
    frag = build_frag()
    assert vert[:4] == b"\x03\x02\x23\x07"
    assert frag[:4] == b"\x03\x02\x23\x07"
    emit_header(os.path.join(here, "mesh_vert.spv.h"), "kMeshVertSpv", vert)
    emit_header(os.path.join(here, "mesh_frag.spv.h"), "kMeshFragSpv", frag)
    print("vert %d bytes, frag %d bytes" % (len(vert), len(frag)))


if __name__ == "__main__":
    main()
