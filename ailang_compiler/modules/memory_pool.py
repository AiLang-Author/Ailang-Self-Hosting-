# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# memory_pool.py
import struct
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ailang_parser')))
from ailang_ast import *

class MemoryPool:
    """Dynamic memory pool allocator module with automatic resizing"""
    
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm
        self.pools = {}  # Track multiple named pools
        self.pool_counter = 0
        
    def compile_operation(self, node):
        """Route pool operations to handlers"""
        if not hasattr(node, 'function'):
            return False
            
        parts = node.function.split('.')
        if len(parts) < 2:
            return False
            
        pool_name = parts[0]
        operation = parts[1]
        
        handlers = {
            'Init': self.compile_pool_init,
            'Alloc': self.compile_pool_alloc,
            'Reset': self.compile_pool_reset,
            'Status': self.compile_pool_status,
            'Resize': self.compile_pool_resize,
        }
        
        handler = handlers.get(operation)
        if handler:
            return handler(pool_name, node)
        return False
    
    def compile_pool_init(self, pool_name, node):
        """Initialize a named memory pool with configurable size"""
        print(f"DEBUG: Initializing pool '{pool_name}'")
        
        pool_size = 65536  # Default 64KB
        if node.arguments and len(node.arguments) > 0:
            if hasattr(node.arguments[0], 'value'):
                pool_size = int(node.arguments[0].value)
                if pool_size < 4096:  # Minimum 4KB
                    pool_size = 4096
                elif pool_size > 1024*1024*16:  # Cap at 16MB
                    pool_size = 1024*1024*16
        
        # Allocate pool via mmap
        self.asm.emit_mov_rax_imm64(9)  # mmap syscall
        self.asm.emit_mov_rdi_imm64(0)  # addr = NULL
        self.asm.emit_mov_rsi_imm64(pool_size)  # length
        self.asm.emit_mov_rdx_imm64(3)  # PROT_READ | PROT_WRITE
        self.asm.emit_mov_r10_imm64(0x22)  # MAP_PRIVATE | MAP_ANONYMOUS
        self.asm.emit_mov_r8_imm64(-1)  # fd = -1
        self.asm.emit_mov_r9_imm64(0)  # offset = 0
        self.asm.emit_syscall()
        self.asm.emit_mov_rbx_rax()  # Save base address
        
        # Check for mmap failure
        self.asm.emit_cmp_rax_imm64(-1)
        error_label = self.asm.create_label()
        self.asm.emit_jump_to_label(error_label, "JE")
        
        # Store pool info
        pool_base_var = f"_pool_{pool_name}_base"
        pool_next_var = f"_pool_{pool_name}_next"
        pool_size_var = f"_pool_{pool_name}_size"
        
        offset = self.compiler.stack_size
        self.compiler.variables[pool_base_var] = offset
        self.compiler.stack_size += 8
        self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP + offset], RBX
        self.asm.emit_bytes(*struct.pack('<i', offset))
        
        offset = self.compiler.stack_size
        self.compiler.variables[pool_next_var] = offset
        self.compiler.stack_size += 8
        self.asm.emit_mov_rax_imm64(0)  # Initial offset = 0
        self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP + offset], RAX
        self.asm.emit_bytes(*struct.pack('<i', offset))
        
        offset = self.compiler.stack_size
        self.compiler.variables[pool_size_var] = offset
        self.compiler.stack_size += 8
        self.asm.emit_mov_rax_imm64(pool_size)  # Store size
        self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP + offset], RAX
        self.asm.emit_bytes(*struct.pack('<i', offset))
        
        self.pools[pool_name] = {
            'base_var': pool_base_var,
            'next_var': pool_next_var,
            'size_var': pool_size_var,
            'size': pool_size
        }
        
        done_label = self.asm.create_label()
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        self.asm.mark_label(error_label)
        self.asm.emit_mov_rax_imm64(0)  # Failure
        
        self.asm.mark_label(done_label)
        print(f"DEBUG: Pool '{pool_name}' initialized with {pool_size} bytes")
        self.asm.emit_mov_rax_imm64(1)  # Success
        return True
    
    def compile_pool_alloc(self, pool_name, node):
        """Allocate from a named pool with auto-resize"""
        if pool_name not in self.pools:
            print(f"DEBUG: Pool '{pool_name}' not found")
            self.asm.emit_mov_rax_imm64(0)
            return True
                
        pool = self.pools[pool_name]
        print(f"DEBUG: Allocating from pool '{pool_name}'")
        
        if len(node.arguments) < 1:
            raise ValueError("Pool.Alloc requires size argument")
        
        # Get requested size
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rsi_rax()  # Size in RSI
        
        # Load current offset
        offset = self.compiler.variables[pool['next_var']]
        self.asm.emit_bytes(0x48, 0x8B, 0x8D)  # MOV RCX, [RBP + offset]
        self.asm.emit_bytes(*struct.pack('<i', offset))
        
        # Load pool size
        size_offset = self.compiler.variables[pool['size_var']]
        self.asm.emit_bytes(0x48, 0x8B, 0x95)  # MOV RDX, [RBP + size_offset]
        self.asm.emit_bytes(*struct.pack('<i', size_offset))
        
        # Check if current_offset + size fits
        self.asm.emit_mov_rax_rcx()  # Current offset
        self.asm.emit_add_rax_rsi()  # Add requested size
        self.asm.emit_cmp_rax_rdx()  # Compare with pool size
        resize_label = self.asm.create_label()
        self.asm.emit_jump_to_label(resize_label, "JAE")  # Jump if overflow
        
        # Allocate from pool
        self.asm.emit_bytes(0x48, 0x8B, 0xBD)  # MOV RDI, [RBP + base_offset]
        self.asm.emit_bytes(*struct.pack('<i', self.compiler.variables[pool['base_var']]))
        self.asm.emit_add_rdi_rcx()  # Base + offset
        self.asm.emit_mov_rdx_rax()  # New offset
        self.asm.emit_bytes(0x48, 0x89, 0x95)  # MOV [RBP + next_offset], RDX
        self.asm.emit_bytes(*struct.pack('<i', offset))
        self.asm.emit_mov_rax_rdi()  # Return allocation address
        
        done_label = self.asm.create_label()
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        # Resize pool if needed
        self.asm.mark_label(resize_label)
        new_size = pool['size'] * 2  # Double pool size
        if new_size > self.max_pool_size:
            new_size = self.max_pool_size
        if self.total_allocated + new_size - pool['size'] > self.max_total_memory:
            print(f"DEBUG: Total memory limit exceeded, reverting to current size")
            new_size = pool['size']
        
        self.asm.emit_mov_rax_imm64(25)  # mremap syscall
        self.asm.emit_bytes(0x48, 0x8B, 0xBD)  # MOV RDI, [RBP + base_offset]
        self.asm.emit_bytes(*struct.pack('<i', self.compiler.variables[pool['base_var']]))
        self.asm.emit_mov_rsi_imm64(pool['size'])  # Old size
        self.asm.emit_mov_rdx_imm64(new_size)  # New size
        self.asm.emit_mov_r10_imm64(0x01)  # MREMAP_MAYMOVE
        self.asm.emit_mov_r8_imm64(0)  # No new address
        self.asm.emit_syscall()
        
        # Check for mremap failure
        self.asm.emit_cmp_rax_imm64(-1)
        error_label = self.asm.create_label()
        self.asm.emit_jump_to_label(error_label, "JE")
        
        # Update base and size
        self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP + base_offset], RAX
        self.asm.emit_bytes(*struct.pack('<i', self.compiler.variables[pool['base_var']]))
        self.asm.emit_mov_rax_imm64(new_size)
        self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP + size_offset], RAX
        self.asm.emit_bytes(*struct.pack('<i', size_offset))
        self.total_allocated += new_size - pool['size']
        pool['size'] = new_size
        
        # Retry allocation
        self.asm.emit_bytes(0x48, 0x8B, 0x8D)  # MOV RCX, [RBP + next_offset]
        self.asm.emit_bytes(*struct.pack('<i', offset))
        self.asm.emit_bytes(0x48, 0x8B, 0xBD)  # MOV RDI, [RBP + base_offset]
        self.asm.emit_bytes(*struct.pack('<i', self.compiler.variables[pool['base_var']]))
        self.asm.emit_add_rdi_rcx()  # Base + offset
        self.asm.emit_mov_rdx_rcx()  # New offset
        self.asm.emit_add_rdx_rsi()  # Add requested size
        self.asm.emit_bytes(0x48, 0x89, 0x95)  # MOV [RBP + next_offset], RDX
        self.asm.emit_bytes(*struct.pack('<i', offset))
        self.asm.emit_mov_rax_rdi()  # Return allocation address
        
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        self.asm.mark_label(error_label)
        self.asm.emit_mov_rax_imm64(0)  # Failure
        
        self.asm.mark_label(done_label)
        print(f"DEBUG: Pool allocation completed for '{pool_name}'")
        return True
    
    def compile_pool_reset(self, pool_name, node):
        """Reset pool to empty (fast deallocation)"""
        if pool_name not in self.pools:
            print(f"DEBUG: Pool '{pool_name}' not found")
            self.asm.emit_mov_rax_imm64(0)
            return True
            
        pool = self.pools[pool_name]
        print(f"DEBUG: Resetting pool '{pool_name}'")
        
        self.asm.emit_mov_rax_imm64(0)
        offset = self.compiler.variables[pool['next_var']]
        self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP + offset], RAX
        self.asm.emit_bytes(*struct.pack('<i', offset))
        
        self.asm.emit_mov_rax_imm64(1)
        return True
    
    def compile_pool_status(self, pool_name, node):
        """Get pool usage statistics"""
        if pool_name not in self.pools:
            print(f"DEBUG: Pool '{pool_name}' not found")
            self.asm.emit_mov_rax_imm64(0)
            return True
        
        pool = self.pools[pool_name]
        print(f"DEBUG: Getting status for pool {pool_name}")
        
        offset = self.compiler.variables[pool['next_var']]
        self.asm.emit_bytes(0x48, 0x8B, 0x85)  # MOV RAX, [RBP + offset]
        self.asm.emit_bytes(*struct.pack('<i', offset))
        return True
    
    def compile_pool_resize(self, pool_name, node):
        """Resize a named memory pool"""
        if pool_name not in self.pools:
            print(f"DEBUG: Pool '{pool_name}' not found")
            self.asm.emit_mov_rax_imm64(0)
            return True
            
        pool = self.pools[pool_name]
        new_size = pool['size'] * 2  # Default: double size
        if node.arguments and len(node.arguments) > 0:
            if hasattr(node.arguments[0], 'value'):
                new_size = int(node.arguments[0].value)
                if new_size < 4096:
                    new_size = 4096
                elif new_size > 1024*1024*16:
                    new_size = 1024*1024*16
        
        self.asm.emit_mov_rax_imm64(25)  # mremap syscall
        self.asm.emit_bytes(0x48, 0x8B, 0xBD)  # MOV RDI, [RBP + base_offset]
        self.asm.emit_bytes(*struct.pack('<i', self.compiler.variables[pool['base_var']]))
        self.asm.emit_mov_rsi_imm64(pool['size'])  # Old size
        self.asm.emit_mov_rdx_imm64(new_size)  # New size
        self.asm.emit_mov_r10_imm64(0x01)  # MREMAP_MAYMOVE
        self.asm.emit_mov_r8_imm64(0)  # No new address
        self.asm.emit_syscall()
        
        self.asm.emit_cmp_rax_imm64(-1)
        error_label = self.asm.create_label()
        self.asm.emit_jump_to_label(error_label, "JE")
        
        self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP + base_offset], RAX
        self.asm.emit_bytes(*struct.pack('<i', self.compiler.variables[pool['base_var']]))
        self.asm.emit_mov_rax_imm64(new_size)
        self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP + size_offset], RAX
        self.asm.emit_bytes(*struct.pack('<i', self.compiler.variables[pool['size_var']]))
        pool['size'] = new_size
        
        self.asm.emit_mov_rax_imm64(1)
        done_label = self.asm.create_label()
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        self.asm.mark_label(error_label)
        self.asm.emit_mov_rax_imm64(0)
        
        self.asm.mark_label(done_label)
        print(f"DEBUG: Resized pool '{pool_name}' to {new_size} bytes")
        return True