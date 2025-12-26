# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# heap_allocator.py - FIXED VERSION without R14/R15

import struct

class HeapManager: # Renamed from HeapAllocator
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm
        self.initialized = False
        self.heap_base_var = None
        self.heap_current_var = None
        
    def inject_early_init(self):
        """Inject heap init at the absolute start of the program"""
        if self.initialized:
            return
        
        print("DEBUG: Injecting heap init as first code")
        
        # Save current code position
        saved_code = bytes(self.asm.code)
        
        # Clear code buffer temporarily
        self.asm.code = bytearray()
        
        # Generate heap init
        self._generate_heap_init_unchecked()
        
        # Get init code
        init_code = bytes(self.asm.code)
        
        # Restore original code with init prepended
        self.asm.code = bytearray()
        self.asm.code.extend(init_code)
        self.asm.code.extend(saved_code)
        
        self.initialized = True
        
    def _generate_heap_init_unchecked(self):
        """Generate heap init without any checks"""
        # Allocate 32MB heap
        self.asm.emit_mov_rdi_imm64(0)
        self.asm.emit_mov_rsi_imm64(32 * 1024 * 1024)
        self.asm.emit_mov_rdx_imm64(3)
        self.asm.emit_mov_r10_imm64(0x22)
        self.asm.emit_mov_r8_imm64(0xFFFFFFFFFFFFFFFF)
        self.asm.emit_mov_r9_imm64(0)
        self.asm.emit_mov_rax_imm64(9)
        self.asm.emit_syscall()
        
        # Store in stack vars (using RBP-relative addressing)
        # These offsets need to be managed by the SymbolTable in the new architecture
        # For now, using fixed offsets for heap_base and heap_current
        self.asm.emit_bytes(0x48, 0x89, 0x45, 0xE0)  # MOV [RBP-32], RAX (heap_base)
        self.asm.emit_bytes(0x48, 0x89, 0x45, 0xE8)  # MOV [RBP-24], RAX (heap_current)
        
    def compile_alloc(self):
        """Allocate from heap"""
        if not self.initialized:
            self.inject_early_init()
            
        # Size in RAX, align to 8
        self.asm.emit_bytes(0x48, 0x83, 0xC0, 0x07)  # ADD RAX, 7
        self.asm.emit_bytes(0x48, 0x83, 0xE0, 0xF8)  # AND RAX, -8
        
        # Get current from [RBP-24]
        self.asm.emit_bytes(0x48, 0x8B, 0x4D, 0xE8)  # MOV RCX, [RBP-24]
        
        # Save old current
        self.asm.emit_mov_rdx_rcx()
        
        # Update current
        self.asm.emit_bytes(0x48, 0x01, 0xC1)  # ADD RCX, RAX
        self.asm.emit_bytes(0x48, 0x89, 0x4D, 0xE8)  # MOV [RBP-24], RCX
        
        # Return old current
        self.asm.emit_mov_rax_rdx()