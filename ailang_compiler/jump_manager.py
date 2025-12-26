# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_compiler/jump_manager.py
from dataclasses import dataclass
from typing import Dict, List, Optional
import struct

@dataclass
class Jump:
    position: int          # Where the jump instruction is
    target_label: str      # Where it's jumping to
    instruction_type: str  # JE, JMP, JNE, etc.
    size: int             # 2 (short), 5 (near JMP), or 6 (near conditional)
    context: str          # 'local' or 'global'

@dataclass  
class Label:
    name: str
    position: int
    context: str  # 'local' or 'global'

@dataclass
class LeaFixup:
    position: int         # Where the offset bytes start in the LEA instruction
    target_label: str     # Label whose address we're loading
    context: str          # 'local' or 'global'

class JumpManager:
    """Manages all jump resolution with proper scoping"""
    
    def __init__(self):
        self.global_jumps: List[Jump] = []
        self.global_labels: Dict[str, Label] = {}
        self.local_context_stack = []
        self.label_counter = 0
        self.lea_fixups: List[LeaFixup] = []  # NEW: Track LEA instructions
        
        # Also expose labels property for compatibility
        self.labels = {}  # Unified label dictionary
        
    def enter_local_context(self, name: str):
        """Enter a function or local scope"""
        self.local_context_stack.append({
            'name': name,
            'jumps': [],
            'labels': {},
            'lea_fixups': [],  # NEW: Track local LEA fixups
            'start_position': None
        })
    
    def exit_local_context(self, code_buffer: bytearray) -> None:
        """Exit local scope and resolve all local jumps immediately"""
        if not self.local_context_stack:
            return
            
        context = self.local_context_stack.pop()
        
        # Resolve all local jumps NOW, not later
        for jump in context['jumps']:
            if jump.target_label not in context['labels']:
                raise ValueError(f"Undefined local label: {jump.target_label}")
                
            target = context['labels'][jump.target_label]
            self._resolve_single_jump(jump, target, code_buffer)
        
        # NEW: Resolve local LEA fixups
        for lea_fixup in context.get('lea_fixups', []):
            if lea_fixup.target_label not in context['labels']:
                raise ValueError(f"Undefined local label for LEA: {lea_fixup.target_label}")
            
            target = context['labels'][lea_fixup.target_label]
            self._resolve_single_lea(lea_fixup, target, code_buffer)
    
    def add_jump(self, position: int, target_label: str, 
                 instruction_type: str, is_local: bool = False):
        """Add a jump to be resolved"""
        
        # Determine jump size based on instruction type
        if instruction_type == "JMP":
            size = 5  # E9 + 4-byte offset
        else:  # JE, JNE, JL, JGE, etc.
            size = 6  # 0F 8x + 4-byte offset
            
        jump = Jump(position, target_label, instruction_type, size, 
                   'local' if is_local else 'global')
        
        if is_local and self.local_context_stack:
            self.local_context_stack[-1]['jumps'].append(jump)
        else:
            self.global_jumps.append(jump)
    
    def add_label(self, name: str, position: int, is_local: bool = False):
        """Mark a label position"""
        label = Label(name, position, 'local' if is_local else 'global')
        
        if is_local and self.local_context_stack:
            self.local_context_stack[-1]['labels'][name] = label
        else:
            self.global_labels[name] = label
            # Also add to unified labels dictionary
            self.labels[name] = position
    
    def add_lea_fixup(self, position: int, target_label: str, is_local: bool = False):
        """NEW: Add LEA instruction that needs fixup"""
        lea_fixup = LeaFixup(position, target_label, 'local' if is_local else 'global')
        
        print(f"DEBUG: Added LEA fixup at {position} for label {target_label}")
        
        if is_local and self.local_context_stack:
            if 'lea_fixups' not in self.local_context_stack[-1]:
                self.local_context_stack[-1]['lea_fixups'] = []
            self.local_context_stack[-1]['lea_fixups'].append(lea_fixup)
        else:
            self.lea_fixups.append(lea_fixup)
    
    def _resolve_single_jump(self, jump: Jump, label: Label, 
                            code_buffer: bytearray) -> None:
        """Resolve a single jump by patching the code buffer"""
        
        # Calculate offset from end of jump instruction
        jump_end = jump.position + jump.size
        offset = label.position - jump_end
        print(f"DEBUG: Jump at {jump.position} to label at {label.position}: offset={offset}")
        
        # CRITICAL CHECK: Verify the offset makes sense
        if offset == 0:
            print(f"WARNING: Jump offset is 0 - this means jumping to the next instruction!")
            print(f"  Jump position: {jump.position}, Label position: {label.position}")
            print(f"  Jump size: {jump.size}")
        
        # Validate offset fits in 32 bits
        if not (-2147483648 <= offset <= 2147483647):
            raise ValueError(f"Jump offset {offset} exceeds 32-bit range")
        
        # Pack as 32-bit signed integer
        offset_bytes = struct.pack('<i', offset)
        
        # DEBUG: Print what we're writing
        print(f"DEBUG: Writing offset bytes: {' '.join(f'{b:02x}' for b in offset_bytes)}")
        
        # Patch the code - the offset starts after the opcode(s)
        if jump.instruction_type == "JMP":
            offset_position = jump.position + 1  # After E9
        else:
            offset_position = jump.position + 2  # After 0F 8x
            
        # CRITICAL: Ensure buffer is large enough
        if offset_position + 4 > len(code_buffer):
            # Extend buffer if needed
            code_buffer.extend([0x90] * (offset_position + 4 - len(code_buffer)))
            
        # DEBUG: Show what's currently there
        print(f"DEBUG: Current bytes at {offset_position}: {' '.join(f'{b:02x}' for b in code_buffer[offset_position:offset_position+4])}")
            
        # Now safely write the offset
        code_buffer[offset_position:offset_position+4] = offset_bytes
        
        # DEBUG: Confirm what was written
        print(f"DEBUG: After patch: {' '.join(f'{b:02x}' for b in code_buffer[offset_position:offset_position+4])}")
    
    def _resolve_single_lea(self, lea_fixup: LeaFixup, label: Label, 
                           code_buffer: bytearray) -> None:
        """NEW: Resolve a single LEA instruction by patching the offset"""
        
        # Calculate RIP-relative offset
        # RIP points to the instruction after the displacement
        instruction_end = lea_fixup.position + 4
        offset = label.position - instruction_end
        
        print(f"DEBUG: Resolving LEA to {lea_fixup.target_label} at {lea_fixup.position}: "
              f"target={label.position}, offset={offset}")
        
        # Validate offset fits in 32 bits
        if not (-2147483648 <= offset <= 2147483647):
            raise ValueError(f"LEA offset {offset} exceeds 32-bit range")
        
        # Pack as 32-bit signed integer
        offset_bytes = struct.pack('<i', offset)
        
        # Patch the code at the offset position
        if lea_fixup.position + 4 > len(code_buffer):
            code_buffer.extend([0x90] * (lea_fixup.position + 4 - len(code_buffer)))
        
        code_buffer[lea_fixup.position:lea_fixup.position+4] = offset_bytes
    
    def resolve_global_jumps(self, code_buffer: bytearray) -> None:
        """Resolve all remaining global jumps and LEA fixups"""
        
        # Resolve jumps
        for jump in self.global_jumps:
            if jump.target_label not in self.global_labels:
                # Check unified labels as fallback
                if jump.target_label in self.labels:
                    label = Label(jump.target_label, self.labels[jump.target_label], 'global')
                else:
                    raise ValueError(f"Undefined global label: {jump.target_label}")
            else:
                label = self.global_labels[jump.target_label]
            self._resolve_single_jump(jump, label, code_buffer)
        
        # NEW: Resolve LEA fixups
        for lea_fixup in self.lea_fixups:
            if lea_fixup.target_label not in self.global_labels:
                # Check unified labels as fallback
                if lea_fixup.target_label in self.labels:
                    label = Label(lea_fixup.target_label, self.labels[lea_fixup.target_label], 'global')
                else:
                    print(f"ERROR: LEA fixup failed - label {lea_fixup.target_label} not found")
                    print(f"Available labels: {list(self.labels.keys())}")
                    raise ValueError(f"Undefined label for LEA: {lea_fixup.target_label}")
            else:
                label = self.global_labels[lea_fixup.target_label]
            self._resolve_single_lea(lea_fixup, label, code_buffer)
        
        # Clear after resolution
        self.global_jumps.clear()
        self.lea_fixups.clear()
    
    def create_unique_label(self) -> str:
        """Generate a unique label name"""
        self.label_counter += 1
        return f"L_{self.label_counter}"