# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_compiler/assembler/modules/inline_asm.py
"""Inline assembly parser and emitter"""

class InlineAssemblyOperations:
    """Parse and emit inline assembly code"""
    
    def emit_inline_assembly(self, assembly_code: str):
        """Emit inline assembly - WARNING: Direct byte emission"""
        print(f"DEBUG: INLINE ASSEMBLY: {assembly_code}")
        
        # Simple assembly parser for common instructions
        lines = assembly_code.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith(';'):
                continue
            
            # Parse simple instructions
            if line.upper() == "NOP":
                self.emit_nop()
            elif line.upper() == "CLI":
                self.emit_cli()
            elif line.upper() == "STI":
                self.emit_sti()
            elif line.upper() == "HLT":
                self.emit_hlt()
            elif line.upper() == "MFENCE":
                self.emit_memory_fence()
            elif line.upper() == "SFENCE":
                self.emit_store_fence()
            elif line.upper() == "LFENCE":
                self.emit_load_fence()
            elif line.upper() == "RDMSR":
                self.emit_read_msr()
            elif line.upper() == "WRMSR":
                self.emit_write_msr()
            elif line.upper().startswith("MOV RAX, CR"):
                cr_num = int(line.split("CR")[1])
                self.emit_read_cr(cr_num)
            elif line.upper().startswith("MOV CR") and ", RAX" in line.upper():
                cr_num = int(line.split("CR")[1].split(",")[0])
                self.emit_write_cr(cr_num)
            else:
                print(f"WARNING: Unrecognized assembly instruction: {line}")
                # For unknown instructions, emit NOP as placeholder
                self.emit_nop()