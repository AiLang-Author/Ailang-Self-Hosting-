# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_compiler/assembler/modules/control_flow.py
"""Control flow operations - jumps, labels, calls"""

import struct

class ControlFlowOperations:
    """Jump, call, and label management"""
    
    def create_label(self):
        """Generate unique label name"""
        if not hasattr(self, '_label_counter'):
            self._label_counter = 0
        self._label_counter += 1
        return f"L{self._label_counter}"
    
    def mark_label(self, label_name, is_local=False):
        """Mark a label at current position"""
        position = len(self.code)
        self.jump_manager.add_label(label_name, position, is_local)
        
        # Initialize labels dict if needed
        if not hasattr(self, 'labels'):
            self.labels = {}
        if not hasattr(self, 'pending_jumps'):
            self.pending_jumps = []
        
        self.labels[label_name] = position
        print(f"DEBUG: Marked label {label_name} at position {position}")
    
    def emit_jump_to_label(self, label_name, jump_type, is_local=False):
        """Emit a conditional or unconditional jump to a label"""
        position = len(self.code)
        
        # Emit jump opcode based on type
        if jump_type == "JE" or jump_type == "JZ":
            self.emit_bytes(0x0F, 0x84, 0x00, 0x00, 0x00, 0x00)
        elif jump_type == "JNE" or jump_type == "JNZ":
            self.emit_bytes(0x0F, 0x85, 0x00, 0x00, 0x00, 0x00)
        elif jump_type == "JMP":
            self.emit_bytes(0xE9, 0x00, 0x00, 0x00, 0x00)
        elif jump_type == "JL":
            self.emit_bytes(0x0F, 0x8C, 0x00, 0x00, 0x00, 0x00)
        elif jump_type == "JGE":
            self.emit_bytes(0x0F, 0x8D, 0x00, 0x00, 0x00, 0x00)
        elif jump_type == "JG":
            self.emit_bytes(0x0F, 0x8F, 0x00, 0x00, 0x00, 0x00)
        elif jump_type == "JS":  # Jump if sign (negative)
            self.emit_bytes(0x0F, 0x88, 0x00, 0x00, 0x00, 0x00)
        elif jump_type == "JLE":
            self.emit_bytes(0x0F, 0x8E, 0x00, 0x00, 0x00, 0x00)
        elif jump_type == "JNS":
            self.emit_bytes(0x0F, 0x89, 0x00, 0x00, 0x00, 0x00)
        elif jump_type == "JS":  # Jump if sign (negative)
            self.emit_bytes(0x0F, 0x88, 0x00, 0x00, 0x00, 0x00)
        elif jump_type == "JB":
            self.emit_bytes(0x0F, 0x82, 0x00, 0x00, 0x00, 0x00)
        elif jump_type == "JA":
            self.emit_bytes(0x0F, 0x87, 0x00, 0x00, 0x00, 0x00)
        elif jump_type == "JAE":  # Jump if above or equal (unsigned >=)
            self.emit_bytes(0x0F, 0x83, 0x00, 0x00, 0x00, 0x00)
        elif jump_type == "JBE":  # Jump if below or equal (unsigned <=)
            self.emit_bytes(0x0F, 0x86, 0x00, 0x00, 0x00, 0x00)
        else:
            raise ValueError(f"Unknown jump type: {jump_type}")
        
        # Register with jump manager
        self.jump_manager.add_jump(position, label_name, jump_type, is_local)
        print(f"DEBUG: Emitted 32-bit {jump_type} to {label_name} at position {position}")
    
    def emit_call_to_label(self, label):
        """Emit CALL to a label"""
        current_pos = len(self.code)
        
        # Emit CALL opcode
        self.emit_bytes(0xE8)
        
        # Calculate and emit offset if label is already known
        if label in self.labels:
            target_pos = self.labels[label]
            offset = target_pos - (current_pos + 5)  # CALL uses next instruction address
            self.emit_bytes(*struct.pack('<i', offset))
        else:
            # Emit placeholder - will be fixed in resolve phase
            self.emit_bytes(0x00, 0x00, 0x00, 0x00)
            # Add to pending calls for resolution
            if not hasattr(self, 'pending_calls'):
                self.pending_calls = []
            self.pending_calls.append((current_pos, label))
        
        print(f"DEBUG: Emitted CALL to label {label}")
    
    def emit_call_register(self, register):
        """CALL register - indirect call through register"""
        register_lower = register.lower()
        
        if register_lower == 'rax':
            self.emit_bytes(0xFF, 0xD0)  # CALL RAX
        elif register_lower == 'rbx':
            self.emit_bytes(0xFF, 0xD3)  # CALL RBX
        elif register_lower == 'rcx':
            self.emit_bytes(0xFF, 0xD1)  # CALL RCX
        elif register_lower == 'rdx':
            self.emit_bytes(0xFF, 0xD2)  # CALL RDX
        elif register_lower == 'rsi':
            self.emit_bytes(0xFF, 0xD6)  # CALL RSI
        elif register_lower == 'rdi':
            self.emit_bytes(0xFF, 0xD7)  # CALL RDI
        elif register_lower == 'rbp':
            self.emit_bytes(0xFF, 0xD5)  # CALL RBP
        elif register_lower == 'rsp':
            self.emit_bytes(0xFF, 0xD4)  # CALL RSP
        elif register_lower == 'r8':
            self.emit_bytes(0x41, 0xFF, 0xD0)  # CALL R8
        elif register_lower == 'r9':
            self.emit_bytes(0x41, 0xFF, 0xD1)  # CALL R9
        elif register_lower == 'r10':
            self.emit_bytes(0x41, 0xFF, 0xD2)  # CALL R10
        elif register_lower == 'r11':
            self.emit_bytes(0x41, 0xFF, 0xD3)  # CALL R11
        elif register_lower == 'r12':
            self.emit_bytes(0x41, 0xFF, 0xD4)  # CALL R12
        elif register_lower == 'r13':
            self.emit_bytes(0x41, 0xFF, 0xD5)  # CALL R13
        elif register_lower == 'r14':
            self.emit_bytes(0x41, 0xFF, 0xD6)  # CALL R14
        elif register_lower == 'r15':
            self.emit_bytes(0x41, 0xFF, 0xD7)  # CALL R15
        else:
            raise ValueError(f"Unknown register for CALL: {register}")
        
        print(f"DEBUG: CALL {register}")
    
    def emit_jmp_register(self, register):
        """JMP register - indirect jump through register"""
        register_lower = register.lower()
        
        if register_lower == 'rax':
            self.emit_bytes(0xFF, 0xE0)  # JMP RAX
        elif register_lower == 'rbx':
            self.emit_bytes(0xFF, 0xE3)  # JMP RBX
        elif register_lower == 'rcx':
            self.emit_bytes(0xFF, 0xE1)  # JMP RCX
        elif register_lower == 'rdx':
            self.emit_bytes(0xFF, 0xE2)  # JMP RDX
        elif register_lower == 'rsi':
            self.emit_bytes(0xFF, 0xE6)  # JMP RSI
        elif register_lower == 'rdi':
            self.emit_bytes(0xFF, 0xE7)  # JMP RDI
        elif register_lower == 'rbp':
            self.emit_bytes(0xFF, 0xE5)  # JMP RBP
        elif register_lower == 'rsp':
            self.emit_bytes(0xFF, 0xE4)  # JMP RSP
        elif register_lower == 'r8':
            self.emit_bytes(0x41, 0xFF, 0xE0)  # JMP R8
        elif register_lower == 'r9':
            self.emit_bytes(0x41, 0xFF, 0xE1)  # JMP R9
        elif register_lower == 'r10':
            self.emit_bytes(0x41, 0xFF, 0xE2)  # JMP R10
        elif register_lower == 'r11':
            self.emit_bytes(0x41, 0xFF, 0xE3)  # JMP R11
        elif register_lower == 'r12':
            self.emit_bytes(0x41, 0xFF, 0xE4)  # JMP R12
        elif register_lower == 'r13':
            self.emit_bytes(0x41, 0xFF, 0xE5)  # JMP R13
        elif register_lower == 'r14':
            self.emit_bytes(0x41, 0xFF, 0xE6)  # JMP R14
        elif register_lower == 'r15':
            self.emit_bytes(0x41, 0xFF, 0xE7)  # JMP R15
        else:
            raise ValueError(f"Unknown register for JMP: {register}")
        
        print(f"DEBUG: JMP {register}")
    
    def emit_ret(self):
        """RET instruction"""
        self.emit_bytes(0xC3)
        print("DEBUG: RET")
    
    def resolve_jumps(self):
        """Resolve all global jumps"""
        jump_count = len(self.jump_manager.global_jumps)
        if jump_count > 0:
            self.jump_manager.resolve_global_jumps(self.code)
            print(f"DEBUG: Successfully resolved {jump_count} global jumps")
    
    # === GUARDED OPERATIONS ===
    
    def emit_write_guarded_rdi_rsi_size_in_rdx(self):
        """Guarded write(fd=RDI, buf=RSI, size=RDX). Skip if buf==NULL or size==0."""
        skip = self.create_label()
        cont = self.create_label()
        
        self.emit_bytes(0x48, 0x85, 0xF6)  # TEST RSI,RSI
        self.emit_jump_to_label(skip, "JZ")
        
        self.emit_bytes(0x48, 0x85, 0xD2)  # TEST RDX,RDX
        self.emit_jump_to_label(skip, "JZ")
        
        self.emit_mov_rax_imm64(1)
        self.emit_syscall()
        self.emit_jump_to_label(cont, "JMP")
        
        self.mark_label(skip)
        self.emit_mov_rax_imm64(0)
        self.mark_label(cont)
        
        
    def emit_jump_if_zero(self, label: str):
        """JZ label - Jump if zero flag is set"""
        # JZ rel32 is 0x0F 0x84
        self.emit_jump_to_label(label, "JZ")

    def emit_jump_if_not_zero(self, label: str):
        """JNZ label - Jump if zero flag is clear"""
        # JNZ rel32 is 0x0F 0x85
        self.emit_jump_to_label(label, "JNZ")    