# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Fixed Multi-Arena Memory Manager for AILANG
Uses .data section for persistent storage instead of stack.
"""

import struct

class RuntimeMemory:
    """
    Arena allocator with proper persistent storage.
    1. Single mmap creates a large super-arena (stored in .data)
    2. CreateArena(size) carves out sub-arenas from super-arena
    3. ArenaAlloc(arena_ptr, size) allocates from a specific sub-arena
    """
    
    def __init__(self, compiler):
        self.compiler = compiler
        self.asm = compiler.asm
        
        # 128MB Super-Arena
        self.SUPER_ARENA_SIZE = 128 * 1024 * 1024
        
        # Track data section offsets (NOT stack offsets)
        self.data_labels = {}
        
        # Labels for our functions
        self.init_label = None
        self.labels = {}
    
    def _add_data_qword(self, label_name):
        """Add 8-byte zero-initialized data"""
        offset = len(self.asm.data)
        self.data_labels[label_name] = offset
        self.asm.data.extend(b'\x00' * 8)
        return offset
    
    def emit_data_section(self):
        """Create persistent storage in .data section"""
        print("Generating RuntimeMemory .data section")
        self._add_data_qword('super_arena_base')
        self._add_data_qword('super_arena_current')
        self._add_data_qword('global_heap_arena')
    
    def emit_init_memory_func(self):
        """Generate memory initialization and helper functions"""
        print("Generating RuntimeMemory functions")
        
        # Generate helper functions FIRST (they have skip jumps)
        self._generate_create_arena()
        self._generate_arena_alloc()
        self._generate_arena_reset()
        self._generate_heap_alloc()
        
        # NOW generate init function
        self.init_label = self.asm.create_label()
        self.labels['SystemInit'] = self.init_label
        
        self.asm.mark_label(self.init_label)
        self.asm.emit_push_rbp()
        self.asm.emit_mov_rbp_rsp()
        
        # mmap the super-arena
        self.asm.emit_mov_rax_imm64(9)  # sys_mmap
        self.asm.emit_xor_edi_edi()     # addr = NULL
        self.asm.emit_mov_rsi_imm64(self.SUPER_ARENA_SIZE)
        self.asm.emit_mov_rdx_imm64(3)  # PROT_READ | PROT_WRITE
        self.asm.emit_mov_r10_imm64(0x22)  # MAP_PRIVATE | MAP_ANONYMOUS
        self.asm.emit_mov_r8_imm64(-1)
        self.asm.emit_xor_r9_r9()
        self.asm.emit_syscall()
        
        # Check for failure
        self.asm.emit_test_rax_rax()
        success_label = self.asm.create_label()
        self.asm.emit_jump_to_label(success_label, "JNS")
        
        # mmap failed
        self._emit_error_exit("mmap failed in memory init")
        
        self.asm.mark_label(success_label)
        
        # Store super-arena base in .data using relocation
        base_offset = self.data_labels['super_arena_base']
        self.asm.emit_load_data_address('rcx', base_offset)
        self.asm.emit_bytes(0x48, 0x89, 0x01)  # MOV [RCX], RAX
        
        # Init super-arena current = base
        current_offset = self.data_labels['super_arena_current']
        self.asm.emit_load_data_address('rcx', current_offset)
        self.asm.emit_bytes(0x48, 0x89, 0x01)  # MOV [RCX], RAX
        
        # Create global heap arena (4MB for misc allocations)
        self.asm.emit_mov_rsi_imm64(4 * 1024 * 1024)
        self.asm.emit_call_to_label(self.labels['CreateArena'])
        heap_offset = self.data_labels['global_heap_arena']
        self.asm.emit_load_data_address('rcx', heap_offset)
        self.asm.emit_bytes(0x48, 0x89, 0x01)  # MOV [RCX], RAX
        
        self.asm.emit_ret()
    
    def _generate_create_arena(self):
        """CreateArena(size in RSI) -> arena_ptr in RAX"""
        self.labels['CreateArena'] = self.asm.create_label()
        
        skip_label = self.asm.create_label()
        self.asm.emit_jump_to_label(skip_label, "JMP")
        self.asm.mark_label(self.labels['CreateArena'])
        
        self.asm.emit_push_rcx()
        self.asm.emit_push_rdx()
        
        # Align size to 8
        self.asm.emit_bytes(0x48, 0x83, 0xC6, 0x07)  # ADD RSI, 7
        self.asm.emit_bytes(0x48, 0x83, 0xE6, 0xF8)  # AND RSI, ~7
        
        # Add header size (24 bytes now: base, current, capacity)
        self.asm.emit_bytes(0x48, 0x83, 0xC6, 0x18)  # ADD RSI, 24
        
        # Load super current
        current_offset = self.data_labels['super_arena_current']
        self.asm.emit_load_data_address('rax', current_offset)
        self.asm.emit_bytes(0x48, 0x8B, 0x10)  # MOV RDX, [RAX]
        
        # New current = current + size
        self.asm.emit_bytes(0x48, 0x89, 0xD1)  # MOV RCX, RDX
        self.asm.emit_bytes(0x48, 0x01, 0xF1)  # ADD RCX, RSI
        
        # Check overflow (super base + SUPER_SIZE)
        base_offset = self.data_labels['super_arena_base']
        self.asm.emit_load_data_address('rax', base_offset)
        self.asm.emit_bytes(0x48, 0x8B, 0x00)  # MOV RAX, [RAX]
        self.asm.emit_bytes(0x48, 0x05)  # ADD RAX, imm64
        self.asm.emit_bytes(*struct.pack('<Q', self.SUPER_ARENA_SIZE))
        
        oom_label = self.asm.create_label()
        self.asm.emit_bytes(0x48, 0x39, 0xC1)  # CMP RCX, RAX
        self.asm.emit_jump_to_label(oom_label, "JA")
        
        # Update super current
        current_offset = self.data_labels['super_arena_current']
        self.asm.emit_load_data_address('rax', current_offset)
        self.asm.emit_bytes(0x48, 0x89, 0x08)  # MOV [RAX], RCX
        
        # Init arena header: [0] = base+24, [8] = 24 (current offset), [16] = size
        self.asm.emit_bytes(0x48, 0x8D, 0x4A, 0x18)  # LEA RCX, [RDX+24]
        self.asm.emit_bytes(0x48, 0x89, 0x0A)  # MOV [RDX], RCX
        self.asm.emit_bytes(0x48, 0xC7, 0x42, 0x08, 0x18, 0x00, 0x00, 0x00)  # MOV [RDX+8], 24
        self.asm.emit_bytes(0x48, 0x89, 0x72, 0x10)  # MOV [RDX+16], RSI  # capacity
        
        self.asm.emit_mov_rax_rdx()  # Return arena_ptr = base
        
        success_label = self.asm.create_label()
        self.asm.emit_jump_to_label(success_label, "JMP")
        
        self.asm.mark_label(oom_label)
        self.asm.emit_xor_eax_eax()
        
        self.asm.mark_label(success_label)
        self.asm.emit_pop_rdx()
        self.asm.emit_pop_rcx()
        self.asm.emit_ret()
        self.asm.mark_label(skip_label)
    
    def _generate_arena_alloc(self):
        """ArenaAlloc(arena_ptr in RDI, size in RSI) -> ptr in RAX"""
        self.labels['ArenaAlloc'] = self.asm.create_label()
        
        skip_label = self.asm.create_label()
        self.asm.emit_jump_to_label(skip_label, "JMP")
        self.asm.mark_label(self.labels['ArenaAlloc'])
        
        self.asm.emit_push_rcx()
        self.asm.emit_push_rdx()
        
        # Align size to 8
        self.asm.emit_bytes(0x48, 0x83, 0xC6, 0x07)  # ADD RSI, 7
        self.asm.emit_bytes(0x48, 0x83, 0xE6, 0xF8)  # AND RSI, ~7
        
        # Load current offset
        self.asm.emit_bytes(0x48, 0x8B, 0x47, 0x08)  # MOV RAX, [RDI+8]
        
        # New offset = current + size
        self.asm.emit_bytes(0x48, 0x89, 0xC2)  # MOV RDX, RAX
        self.asm.emit_bytes(0x48, 0x01, 0xF2)  # ADD RDX, RSI
        
        # Check against capacity [RDI+16]
        self.asm.emit_bytes(0x48, 0x8B, 0x4F, 0x10)  # MOV RCX, [RDI+16]
        oom_label = self.asm.create_label()
        self.asm.emit_bytes(0x48, 0x39, 0xD1)  # CMP RCX, RDX
        self.asm.emit_jump_to_label(oom_label, "JB")  # new > cap
        
        # Update current
        self.asm.emit_bytes(0x48, 0x89, 0x57, 0x08)  # MOV [RDI+8], RDX
        
        # Return ptr = arena + old_offset
        self.asm.emit_bytes(0x48, 0x01, 0xF8)  # ADD RAX, RDI
        
        success_label = self.asm.create_label()
        self.asm.emit_jump_to_label(success_label, "JMP")
        
        self.asm.mark_label(oom_label)
        self.asm.emit_xor_eax_eax()
        
        self.asm.mark_label(success_label)
        self.asm.emit_pop_rdx()
        self.asm.emit_pop_rcx()
        self.asm.emit_ret()
        self.asm.mark_label(skip_label)
    
    def _generate_arena_reset(self):
        """ArenaReset(arena_ptr in RDI)"""
        self.labels['ArenaReset'] = self.asm.create_label()
        
        skip_label = self.asm.create_label()
        self.asm.emit_jump_to_label(skip_label, "JMP")
        self.asm.mark_label(self.labels['ArenaReset'])
        
        self.asm.emit_mov_rax_imm64(24)  # Updated for new header size
        self.asm.emit_bytes(0x48, 0x89, 0x47, 0x08)  # MOV [RDI+8], RAX
        self.asm.emit_ret()
        self.asm.mark_label(skip_label)
    
    def _generate_heap_alloc(self):
        """HeapAlloc(size in RSI) -> ptr in RAX"""
        self.labels['HeapAlloc'] = self.asm.create_label()
        skip_label = self.asm.create_label()
        self.asm.emit_jump_to_label(skip_label, "JMP")
        self.asm.mark_label(self.labels['HeapAlloc'])
        
        # Load global arena
        heap_offset = self.data_labels['global_heap_arena']
        self.asm.emit_load_data_address('rax', heap_offset)
        self.asm.emit_bytes(0x48, 0x8B, 0x38)  # MOV RDI, [RAX]
        
        # ArenaAlloc(arena in RDI, size in RSI)
        self.asm.emit_call_to_label(self.labels['ArenaAlloc'])
        self.asm.emit_ret()
        
        self.asm.mark_label(skip_label)
    
    def _emit_error_exit(self, message):
        """Print error and exit"""
        msg_bytes = message.encode('utf-8') + b'\n\x00'
        msg_offset = len(self.asm.data)
        self.asm.data.extend(msg_bytes)
        
        self.asm.emit_mov_rax_imm64(1)  # sys_write
        self.asm.emit_mov_rdi_imm64(2)  # stderr
        self.asm.emit_load_data_address('rsi', msg_offset)
        self.asm.emit_mov_rdx_imm64(len(msg_bytes) - 1)
        self.asm.emit_syscall()
        
        self.asm.emit_mov_rax_imm64(60)  # sys_exit
        self.asm.emit_mov_rdi_imm64(1)
        self.asm.emit_syscall()
    
    # Public API
    def compile_create_arena(self, node):
        """Compile CreateArena(size)"""
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rsi_rax()
        self.asm.emit_call_to_label(self.labels['CreateArena'])
        return True
    
    def compile_arena_alloc(self, node):
        """Compile ArenaAlloc(arena_ptr, size)"""
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_push_rax()
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()
        self.asm.emit_pop_rsi()
        self.asm.emit_call_to_label(self.labels['ArenaAlloc'])
        return True
    
    def compile_arena_reset(self, node):
        """Compile ArenaReset(arena_ptr)"""
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()
        self.asm.emit_call_to_label(self.labels['ArenaReset'])
        return True
    
    # Compatibility stubs
    def register_function_pool(self, name, size):
        pass
    
    def register_main_pool(self, node):
        pass
    
    def compile_pool_alloc(self, context, size):
        self.asm.emit_xor_eax_eax()