# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_compiler/assembler/modules/stack.py

import traceback
import inspect

def _debug_trace(operation, register):
    """Show the complete call path for stack operations"""
    print(f"\n{'='*60}")
    print(f"STACK TRACE: {operation} {register}")
    print(f"{'='*60}")
    
    # Show the call stack
    frame = inspect.currentframe().f_back
    depth = 0
    while frame and depth < 10:
        info = inspect.getframeinfo(frame)
        local_vars = frame.f_locals
        
        print(f"  [{depth}] {info.filename}:{info.lineno} in {info.function}")
        
        # Show what 'self' is at this level
        if 'self' in local_vars:
            self_obj = local_vars['self']
            self_type = type(self_obj).__name__
            print(f"       self = {self_type}")
            
            # Check for compiler attribute
            if hasattr(self_obj, 'compiler'):
                print(f"       ✓ HAS self.compiler: {type(self_obj.compiler).__name__}")
            else:
                print(f"       ✗ NO self.compiler")
                
            # Check for asm attribute
            if hasattr(self_obj, 'asm'):
                print(f"       ✓ HAS self.asm: {type(self_obj.asm).__name__}")
        
        frame = frame.f_back
        depth += 1
    
    print(f"{'='*60}\n")

"""Stack operations - push, pop, stack pointer manipulation"""

import struct

class StackOperations:
    """Stack manipulation operations"""
    
    # === PUSH OPERATIONS ===
    
    def emit_push_rax(self):
        """PUSH RAX"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_push'):
            self.compiler.track_push("PUSH RAX")
        self.emit_bytes(0x50)
    
    def emit_push_rbx(self):
        """PUSH RBX"""
        _debug_trace("PUSH", "RBX")
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_push'):
            self.compiler.track_push("PUSH RBX")
        self.emit_bytes(0x53)
    
    def emit_push_rcx(self):
        """PUSH RCX"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_push'):
            self.compiler.track_push("PUSH RCX")
        self.emit_bytes(0x51)
    
    def emit_push_rdx(self):
        """PUSH RDX"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_push'):
            self.compiler.track_push("PUSH RDX")
        self.emit_bytes(0x52)
    
    def emit_push_rsi(self):
        """PUSH RSI"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_push'):
            self.compiler.track_push("PUSH RSI")
        self.emit_bytes(0x56)
    
    def emit_push_rdi(self):
        """PUSH RDI"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_push'):
            self.compiler.track_push("PUSH RDI")
        self.emit_bytes(0x57)
    
    def emit_push_rbp(self):
        """PUSH RBP - Standard frame pointer save"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_push'):
            self.compiler.track_push("PUSH RBP")
        self.emit_bytes(0x55)
        print("DEBUG: PUSH RBP")
    
    def emit_push_r8(self):
        """PUSH R8"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_push'):
            self.compiler.track_push("PUSH R8")
        self.emit_bytes(0x41, 0x50)
    
    def emit_push_r9(self):
        """PUSH R9"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_push'):
            self.compiler.track_push("PUSH R9")
        self.emit_bytes(0x41, 0x51)
    
    def emit_push_r10(self):
        """PUSH R10"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_push'):
            self.compiler.track_push("PUSH R10")
        self.emit_bytes(0x41, 0x52)
        print("DEBUG: PUSH R10")
    
    def emit_push_r11(self):
        """PUSH R11"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_push'):
            self.compiler.track_push("PUSH R11")
        self.emit_bytes(0x41, 0x53)
    
    def emit_push_r12(self):
        """PUSH R12 - Callee-saved register"""
        _debug_trace("PUSH", "R12")
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_push'):
            self.compiler.track_push("PUSH R12")
        self.emit_bytes(0x41, 0x54)
    
    def emit_push_r13(self):
        """PUSH R13 - Callee-saved register"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_push'):
            self.compiler.track_push("PUSH R13")
        self.emit_bytes(0x41, 0x55)
    
    def emit_push_r14(self):
        """PUSH R14 - Callee-saved register"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_push'):
            self.compiler.track_push("PUSH R14")
        self.emit_bytes(0x41, 0x56)
    
    def emit_push_r15(self):
        """PUSH R15 - Callee-saved register"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_push'):
            self.compiler.track_push("PUSH R15")
        self.emit_bytes(0x41, 0x57)
    
    # === POP OPERATIONS ===
    
    def emit_pop_rax(self):
        """POP RAX"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_pop'):
            self.compiler.track_pop("POP RAX")
        self.emit_bytes(0x58)
    
    def emit_pop_rbx(self):
        """POP RBX"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_pop'):
            self.compiler.track_pop("POP RBX")
        self.emit_bytes(0x5B)
    
    def emit_pop_rcx(self):
        """POP RCX"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_pop'):
            self.compiler.track_pop("POP RCX")
        self.emit_bytes(0x59)
    
    def emit_pop_rdx(self):
        """POP RDX"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_pop'):
            self.compiler.track_pop("POP RDX")
        self.emit_bytes(0x5A)
    
    def emit_pop_rsi(self):
        """POP RSI"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_pop'):
            self.compiler.track_pop("POP RSI")
        self.emit_bytes(0x5E)
    
    def emit_pop_rdi(self):
        """POP RDI"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_pop'):
            self.compiler.track_pop("POP RDI")
        self.emit_bytes(0x5F)
    
    def emit_pop_rbp(self):
        """POP RBP - Standard frame pointer restore"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_pop'):
            self.compiler.track_pop("POP RBP")
        self.emit_bytes(0x5D)
        print("DEBUG: POP RBP")
    
    def emit_pop_r8(self):
        """POP R8"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_pop'):
            self.compiler.track_pop("POP R8")
        self.emit_bytes(0x41, 0x58)
    
    def emit_pop_r9(self):
        """POP R9"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_pop'):
            self.compiler.track_pop("POP R9")
        self.emit_bytes(0x41, 0x59)
    
    def emit_pop_r10(self):
        """POP R10"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_pop'):
            self.compiler.track_pop("POP R10")
        self.emit_bytes(0x41, 0x5A)
        print("DEBUG: POP R10")
    
    def emit_pop_r11(self):
        """POP R11"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_pop'):
            self.compiler.track_pop("POP R11")
        self.emit_bytes(0x41, 0x5B)
    
    def emit_pop_r12(self):
        """POP R12 - Callee-saved register"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_pop'):
            self.compiler.track_pop("POP R12")
        self.emit_bytes(0x41, 0x5C)
    
    def emit_pop_r13(self):
        """POP R13 - Callee-saved register"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_pop'):
            self.compiler.track_pop("POP R13")
        self.emit_bytes(0x41, 0x5D)
    
    def emit_pop_r14(self):
        """POP R14 - Callee-saved register"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_pop'):
            self.compiler.track_pop("POP R14")
        self.emit_bytes(0x41, 0x5E)
    
    def emit_pop_r15(self):
        """POP R15 - Callee-saved register"""
        if hasattr(self, 'compiler') and hasattr(self.compiler, 'track_pop'):
            self.compiler.track_pop("POP R15")
        self.emit_bytes(0x41, 0x5F)
    
    # === STACK POINTER MANIPULATION ===
    
    def emit_add_rsp_imm8(self, value):
        """ADD RSP, imm8 - Adjust stack pointer"""
        self.emit_bytes(0x48, 0x83, 0xC4, value & 0xFF)
        print(f"DEBUG: ADD RSP, {value}")
    
    def emit_add_rsp_imm32(self, value):
        """ADD RSP, imm32 - Add 32-bit immediate to RSP"""
        if value <= 127:
            # Use 8-bit form if possible
            self.emit_add_rsp_imm8(value)
        else:
            # ADD RSP, imm32: REX.W + 81 /0 id
            self.emit_bytes(0x48, 0x81, 0xC4)
            self.emit_bytes(*struct.pack('<I', value))
            print(f"DEBUG: ADD RSP, {value}")
    
    def emit_sub_rsp_imm32(self, value):
        """SUB RSP, imm32 - Allocate stack space"""
        self.emit_bytes(0x48, 0x81, 0xEC)
        self.emit_bytes(*struct.pack('<I', value))
        print(f"DEBUG: SUB RSP, {value}")

    def emit_sub_rsp_imm8(self, value):
        """SUB RSP, imm8 - Allocate small amount of stack space"""
        if not 0 <= value <= 255:
            raise ValueError(f"Value {value} out of 8-bit range")
        self.emit_bytes(0x48, 0x83, 0xEC, value & 0xFF)
        print(f"DEBUG: SUB RSP, {value}")

    def emit_sub_rsp_imm8(self, value):
        """SUB RSP, imm8 - Allocate small amount of stack space"""
        if not 0 <= value <= 255:
            raise ValueError(f"Value {value} out of 8-bit range")
        self.emit_bytes(0x48, 0x83, 0xEC, value & 0xFF)
        print(f"DEBUG: SUB RSP, {value}")

    def emit_mov_word_ptr_rsp(self, value):
        """MOV WORD PTR [RSP], imm16 - Store 16-bit immediate to top of stack"""
        self.emit_bytes(0x66, 0xC7, 0x04, 0x24)  # MOV WORD [RSP], imm16
        self.emit_bytes(value & 0xFF, (value >> 8) & 0xFF)
        print(f"DEBUG: MOV WORD [RSP], {value}")

    def emit_mov_word_ptr_rsp_offset(self, offset):
        """MOV WORD PTR [RSP+offset], AX - Store AX at stack offset"""
        if offset <= 127:
            self.emit_bytes(0x66, 0x89, 0x44, 0x24, offset & 0xFF)
        else:
            self.emit_bytes(0x66, 0x89, 0x84, 0x24)
            self.emit_bytes(*struct.pack('<I', offset))
        print(f"DEBUG: MOV WORD [RSP+{offset}], AX")

    def emit_mov_dword_ptr_rsp_offset(self, offset):
        """MOV DWORD PTR [RSP+offset], EAX - Store EAX at stack offset"""
        if offset <= 127:
            self.emit_bytes(0x89, 0x44, 0x24, offset & 0xFF)
        else:
            self.emit_bytes(0x89, 0x84, 0x24)
            self.emit_bytes(*struct.pack('<I', offset))
        print(f"DEBUG: MOV DWORD [RSP+{offset}], EAX")

    def emit_mov_word_ptr_rsp_value(self, value):
        """MOV WORD [RSP], value - More explicit version"""
        self.emit_bytes(0x66, 0xC7, 0x04, 0x24, value & 0xFF, (value >> 8) & 0xFF)
        print(f"DEBUG: MOV WORD [RSP], {value:#x}")

    def emit_store_ax_to_stack(self, offset):
        """Store AX register to [RSP+offset]"""
        self.emit_bytes(0x66, 0x89, 0x44, 0x24, offset & 0xFF)
        print(f"DEBUG: MOV [RSP+{offset}], AX")

    def emit_store_eax_to_stack(self, offset):
        """Store EAX register to [RSP+offset]"""
        self.emit_bytes(0x89, 0x44, 0x24, offset & 0xFF)
        print(f"DEBUG: MOV [RSP+{offset}], EAX")

    def emit_zero_qword_at_stack(self, offset):
        """Zero out 8 bytes at [RSP+offset]"""
        self.emit_bytes(0x48, 0xC7, 0x44, 0x24, offset & 0xFF, 0x00, 0x00, 0x00, 0x00)
        print(f"DEBUG: MOV QWORD [RSP+{offset}], 0")
        print(f"DEBUG: SUB RSP, {value}")