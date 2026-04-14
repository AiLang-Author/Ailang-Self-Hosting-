import os
import re

buffer_path = "Librarys/Compiler/CodeEmit/Library.CEmitBuffer.ailang"
arch_path = "Librarys/Compiler/CodeEmit/Library.CEmitCoreArch.ailang"

# 1. Dynamically read all valid OpCodes directly from your LIR Buffer pool
with open(buffer_path, "r") as f:
    buffer_code = f.read()
    
# Matches: "MovRbpRsp": Initialize=1
known_opcodes = set(re.findall(r'"(\w+)": Initialize=', buffer_code))
print(f"Discovered {len(known_opcodes)} OpCodes in CEmitBuffer...")

with open(arch_path, "r") as f:
    arch_code = f.read()

patched_count = 0

def repl(m):
    global patched_count
    func_name = m.group(1)
    inputs_block = m.group(2)
    
    # If this wrapper isn't in our OpCode LIR pool, leave it completely untouched
    if func_name not in known_opcodes:
        return m.group(0)
        
    # Extract the argument names to pass to EmitBuffer_Add
    inputs = re.findall(r'Input:\s*(\w+)\s*:', inputs_block)
    op1 = inputs[0] if len(inputs) > 0 else "0"
    op2 = inputs[1] if len(inputs) > 1 else "0"
    
    # Auto-categorize the OptClass for the optimizer pass
    cls = "OptClass.UNTRACKED"
    if "MovRbpOffsetRax" in func_name: cls = "OptClass.STORE_LOCAL"
    elif "MovRaxRbpOffset" in func_name: cls = "OptClass.LOAD_LOCAL"
    elif any(x in func_name for x in ["Add", "Sub", "Mul", "Div", "Imul", "Idiv", "Xor", "And", "Or", "Neg", "Inc", "Dec", "Not", "Shl", "Shr", "Sar", "Movzx"]): 
        cls = "OptClass.CLOBBER_RAX"
    elif any(x in func_name for x in ["Jmp", "J", "Call", "Ret", "Push", "Pop", "Sys", "DerefRdi", "DerefRsi", "DerefRbx", "Rep"]): 
        cls = "OptClass.BARRIER"
    
    # Inject the interceptor right at the start of the body
    interceptor = f"""
        IfCondition EqualTo(EmitBuffer.enabled, 1) ThenBlock: {{
            EmitBuffer_Add(OpCode.{func_name}, {cls}, {op1}, {op2})
            ReturnValue(1)
        }}"""
    
    patched_count += 1
    return f"Function.Emit_{func_name} {{{inputs_block}Body: {{{interceptor}"

# Regex targets: Function.Emit_Name { [Input block] Body: {
pattern = re.compile(r'Function\.Emit_(\w+)\s*\{([^}]*?)Body:\s*\{')
new_arch_code = pattern.sub(repl, arch_code)

with open(arch_path, "w") as f:
    f.write(new_arch_code)

print(f"Successfully patched {patched_count} wrapper functions in CEmitCoreArch.ailang!")
