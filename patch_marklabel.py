import re

core_path = "Librarys/Compiler/CodeEmit/Library.CEmitCore.ailang"

with open(core_path, "r") as f:
    core_code = f.read()

if "OpCode.MarkLabel" not in core_code:
    if "LibraryImport.Compiler.CodeEmit.CEmitBuffer" not in core_code:
        core_code = core_code.replace(
            "FixedPool.Emit {", 
            "LibraryImport.Compiler.CodeEmit.CEmitBuffer\n\nFixedPool.Emit {"
        )
    
    def repl(m):
        inputs_block = m.group(1)
        inputs = re.findall(r'Input:\s*(\w+)\s*:', inputs_block)
        op1 = inputs[0] if len(inputs) > 0 else "0"
        
        interceptor = f"""
        IfCondition EqualTo(EmitBuffer.enabled, 1) ThenBlock: {{
            EmitBuffer_Add(OpCode.MarkLabel, OptClass.BARRIER, {op1}, 0)
            ReturnValue(1)
        }}"""
        return f"Function.Emit_MarkLabel {{{inputs_block}Body: {{{interceptor}"

    pattern = re.compile(r'Function\.Emit_MarkLabel\s*\{([^}]*?)Body:\s*\{')
    core_code = pattern.sub(repl, core_code)

    with open(core_path, "w") as f:
        f.write(core_code)
    print("Successfully patched Emit_MarkLabel in CEmitCore.ailang!")
else:
    print("Emit_MarkLabel is already patched.")