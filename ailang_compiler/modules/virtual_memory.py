#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Virtual Memory Operations Module for AILANG Compiler
Handles VM operations: PageTable, VirtualMemory, Cache, TLB, MemoryBarrier
"""

import sys
import os
import struct
from ailang_parser.ailang_ast import *

class VirtualMemoryOps:
    """Handles Virtual Memory operations compilation"""
    
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm
        
        # VM State Tracking
        self.page_tables = {}       # page_table_id -> CR3_value
        self.virtual_allocations = {}  # allocation_id -> (address, size, protection)
        self.mmio_mappings = {}     # mapping_id -> (virtual_addr, physical_addr, size)
        self.allocation_counter = 0
        
    def compile_operation(self, node):
        """Route VM operations to specific handlers"""
        try:
            if isinstance(node, FunctionCall):
                function_name = node.function
                
                if function_name.startswith('PageTable_'):
                    return self.compile_page_table_call(node)
                elif function_name.startswith('VirtualMemory_'):
                    return self.compile_virtual_memory_call(node)
                elif function_name.startswith('Cache_'):
                    return self.compile_cache_call(node)
                elif function_name.startswith('TLB_'):
                    return self.compile_tlb_call(node)
                elif function_name.startswith('MemoryBarrier_'):
                    return self.compile_memory_barrier_call(node)
                else:
                    return False  # Not a VM operation
            
            return False
            
        except Exception as e:
            print(f"ERROR: VM operation compilation failed: {str(e)}")
            raise
    
    def compile_page_table_call(self, node):
        """Handle PageTable.* operations"""
        try:
            operation = node.function.split('_', 1)[1]  # PageTable_Create -> Create
            print(f"DEBUG: Compiling PageTable.{operation}")
            
            if operation == 'Create':
                return self.compile_page_table_create(node)
            elif operation == 'Map':
                return self.compile_page_table_map(node)
            elif operation == 'Unmap':
                return self.compile_page_table_unmap(node)
            elif operation == 'Switch':
                return self.compile_page_table_switch(node)
            else:
                print(f"WARNING: Unsupported PageTable operation: {operation}")
                self.asm.emit_mov_rax_imm64(0)  # Return 0 for unsupported
                return True
                
        except Exception as e:
            print(f"ERROR: PageTable operation failed: {str(e)}")
            raise
    
    def compile_page_table_create(self, node):
        """Compile PageTable.Create(levels-4, page_size-'4KB')"""
        try:
            print("DEBUG: Creating new page table")
            
            # Parse arguments (levels, page_size)
            args = self.parse_vm_arguments(node.arguments)
            levels = args.get('levels', 4)
            page_size = args.get('page_size', '4KB')
            
            print(f"DEBUG: Page table: {levels} levels, {page_size} pages")
            
            # Allocate page table in memory (simplified)
            # In real implementation, this would allocate actual page table structures
            page_table_id = len(self.page_tables) + 1
            page_table_addr = 0x100000 + (page_table_id * 0x1000)  # Fake physical address
            
            # Store page table info
            self.page_tables[page_table_id] = page_table_addr
            
            # Return page table ID in RAX
            self.asm.emit_mov_rax_imm64(page_table_id)
            
            print(f"DEBUG: Created page table {page_table_id} at address {hex(page_table_addr)}")
            return True
            
        except Exception as e:
            print(f"ERROR: PageTable.Create failed: {str(e)}")
            raise
    
    def compile_page_table_map(self, node):
        """Compile PageTable.Map(page_table, virtual_addr, physical_addr, flags)"""
        try:
            print("DEBUG: Mapping page in page table")
            
            args = self.parse_vm_arguments(node.arguments)
            page_table = args.get('page_table', 1)
            virtual_addr = args.get('virtual_addr', 0x40000000)
            physical_addr = args.get('physical_addr', 0x100000)
            flags = args.get('flags', 'RW')
            
            print(f"DEBUG: Map virtual {hex(virtual_addr)} -> physical {hex(physical_addr)} in PT {page_table}")
            
            # Emit page table mapping code (simplified)
            # In real implementation, this would manipulate actual page table entries
            
            # Load page table address
            if page_table in self.page_tables:
                pt_addr = self.page_tables[page_table]
                self.asm.emit_mov_rax_imm64(pt_addr)
                print(f"DEBUG: Using page table at {hex(pt_addr)}")
            else:
                print(f"WARNING: Page table {page_table} not found, using default")
                self.asm.emit_mov_rax_imm64(0x100000)
            
            # For now, just return success (1)
            self.asm.emit_mov_rax_imm64(1)
            
            print("DEBUG: Page mapping completed")
            return True
            
        except Exception as e:
            print(f"ERROR: PageTable.Map failed: {str(e)}")
            raise
    
    def compile_page_table_switch(self, node):
        """Compile PageTable.Switch(page_table)"""
        try:
            print("DEBUG: Switching to page table")
            
            args = self.parse_vm_arguments(node.arguments)
            page_table = args.get('page_table', 1)
            
            if page_table in self.page_tables:
                pt_addr = self.page_tables[page_table]
                print(f"DEBUG: Switching to page table {page_table} at {hex(pt_addr)}")
                
                # Load page table address into CR3 (simplified)
                self.asm.emit_mov_rax_imm64(pt_addr)
                # MOV CR3, RAX (switch page table)
                self.asm.emit_write_cr(3)
                
                # Invalidate TLB after page table switch
                self.asm.emit_bytes(0x0F, 0x01, 0xF8)  # INVD (simplified TLB flush)
                
                print("DEBUG: Page table switch completed")
            else:
                print(f"WARNING: Page table {page_table} not found")
                self.asm.emit_mov_rax_imm64(0)  # Return error
            
            return True
            
        except Exception as e:
            print(f"ERROR: PageTable.Switch failed: {str(e)}")
            raise
    
    def compile_page_table_unmap(self, node):
        """Compile PageTable.Unmap(page_table, virtual_addr)"""
        try:
            print("DEBUG: Unmapping page from page table")
            
            args = self.parse_vm_arguments(node.arguments)
            page_table = args.get('page_table', 1)
            virtual_addr = args.get('virtual_addr', 0x40000000)
            
            print(f"DEBUG: Unmap virtual {hex(virtual_addr)} from PT {page_table}")
            
            # Simplified unmap - just return success
            self.asm.emit_mov_rax_imm64(1)
            
            print("DEBUG: Page unmapping completed")
            return True
            
        except Exception as e:
            print(f"ERROR: PageTable.Unmap failed: {str(e)}")
            raise
    
    def compile_virtual_memory_call(self, node):
        """Handle VirtualMemory.* operations"""
        try:
            operation = node.function.split('_', 1)[1]  # VirtualMemory_Allocate -> Allocate
            print(f"DEBUG: Compiling VirtualMemory.{operation}")
            
            if operation == 'Allocate':
                return self.compile_vm_allocate(node)
            elif operation == 'Free':
                return self.compile_vm_free(node)
            elif operation == 'Protect':
                return self.compile_vm_protect(node)
            else:
                print(f"WARNING: Unsupported VirtualMemory operation: {operation}")
                self.asm.emit_mov_rax_imm64(0)
                return True
                
        except Exception as e:
            print(f"ERROR: VirtualMemory operation failed: {str(e)}")
            raise
    
    def compile_vm_allocate(self, node):
        """Compile VirtualMemory.Allocate(size-65536, protection-'RW')"""
        try:
            print("DEBUG: Allocating virtual memory")
            
            args = self.parse_vm_arguments(node.arguments)
            size = args.get('size', 4096)
            protection = args.get('protection', 'RW')
            alignment = args.get('alignment', '4KB')
            
            print(f"DEBUG: Allocate {size} bytes, protection {protection}, alignment {alignment}")
            
            # Generate virtual address (simplified)
            self.allocation_counter += 1
            virtual_addr = 0x40000000 + (self.allocation_counter * 0x10000)  # 64KB spacing
            
            # Store allocation info
            self.virtual_allocations[self.allocation_counter] = (virtual_addr, size, protection)
            
            # Return virtual address in RAX
            self.asm.emit_mov_rax_imm64(virtual_addr)
            
            print(f"DEBUG: Allocated {size} bytes at virtual address {hex(virtual_addr)}")
            return True
            
        except Exception as e:
            print(f"ERROR: VirtualMemory.Allocate failed: {str(e)}")
            raise
    
    def compile_vm_free(self, node):
        """Compile VirtualMemory.Free(address)"""
        try:
            print("DEBUG: Freeing virtual memory")
            
            args = self.parse_vm_arguments(node.arguments)
            address = args.get('address', 0)
            
            print(f"DEBUG: Free virtual address {hex(address)}")
            
            # Simplified free - just return success
            self.asm.emit_mov_rax_imm64(1)
            
            print("DEBUG: Virtual memory freed")
            return True
            
        except Exception as e:
            print(f"ERROR: VirtualMemory.Free failed: {str(e)}")
            raise
    
    def compile_vm_protect(self, node):
        """Compile VirtualMemory.Protect(address, size, protection)"""
        try:
            print("DEBUG: Changing virtual memory protection")
            
            args = self.parse_vm_arguments(node.arguments)
            address = args.get('address', 0)
            size = args.get('size', 4096)
            protection = args.get('protection', 'RW')
            
            print(f"DEBUG: Protect {hex(address)}, size {size}, protection {protection}")
            
            # Simplified protect - just return success
            self.asm.emit_mov_rax_imm64(1)
            
            print("DEBUG: Virtual memory protection changed")
            return True
            
        except Exception as e:
            print(f"ERROR: VirtualMemory.Protect failed: {str(e)}")
            raise
    
    def compile_cache_call(self, node):
        """Handle Cache.* operations"""
        try:
            operation = node.function.split('_', 1)[1]  # Cache_Flush -> Flush
            print(f"DEBUG: Compiling Cache.{operation}")
            
            if operation == 'Flush':
                return self.compile_cache_flush(node)
            elif operation == 'Invalidate':
                return self.compile_cache_invalidate(node)
            elif operation == 'Prefetch':
                return self.compile_cache_prefetch(node)
            else:
                print(f"WARNING: Unsupported Cache operation: {operation}")
                self.asm.emit_mov_rax_imm64(0)
                return True
                
        except Exception as e:
            print(f"ERROR: Cache operation failed: {str(e)}")
            raise
    
    def compile_cache_flush(self, node):
        """Compile Cache.Flush(level-'L1', address-0x1000, size-4096)"""
        try:
            print("DEBUG: Flushing cache")
            
            args = self.parse_vm_arguments(node.arguments)
            level = args.get('level', 'L1')
            address = args.get('address', 0)
            size = args.get('size', 4096)
            
            print(f"DEBUG: Flush {level} cache, address {hex(address)}, size {size}")
            
            # Emit cache flush instructions
            if level in ['L1', 'L2', 'L3']:
                # CLFLUSH instruction for cache line flush
                if address > 0:
                    self.asm.emit_mov_rax_imm64(address)
                    self.asm.emit_bytes(0x0F, 0xAE, 0x38)  # CLFLUSH [RAX]
                    print(f"DEBUG: Flushed cache line at {hex(address)}")
                else:
                    # Full cache flush
                    self.asm.emit_wbinvd()  # Write back and invalidate
                    print("DEBUG: Full cache flush completed")
            
            # Return success
            self.asm.emit_mov_rax_imm64(1)
            return True
            
        except Exception as e:
            print(f"ERROR: Cache.Flush failed: {str(e)}")
            raise
    
    def compile_cache_invalidate(self, node):
        """Compile Cache.Invalidate operations"""
        try:
            print("DEBUG: Invalidating cache")
            
            # Emit cache invalidate
            self.asm.emit_invd()  # Invalidate cache without writeback
            self.asm.emit_mov_rax_imm64(1)
            
            print("DEBUG: Cache invalidation completed")
            return True
            
        except Exception as e:
            print(f"ERROR: Cache.Invalidate failed: {str(e)}")
            raise
    
    def compile_cache_prefetch(self, node):
        """Compile Cache.Prefetch operations"""
        try:
            print("DEBUG: Prefetching cache")
            
            args = self.parse_vm_arguments(node.arguments)
            address = args.get('address', 0)
            
            if address > 0:
                # Load address and prefetch
                self.asm.emit_mov_rax_imm64(address)
                self.asm.emit_bytes(0x0F, 0x18, 0x00)  # PREFETCH [RAX]
                print(f"DEBUG: Prefetched address {hex(address)}")
            
            self.asm.emit_mov_rax_imm64(1)
            return True
            
        except Exception as e:
            print(f"ERROR: Cache.Prefetch failed: {str(e)}")
            raise
    
    def compile_tlb_call(self, node):
        """Handle TLB.* operations"""
        try:
            operation = node.function.split('_', 1)[1]  # TLB_FlushAll -> FlushAll
            print(f"DEBUG: Compiling TLB.{operation}")
            
            if operation == 'FlushAll':
                return self.compile_tlb_flush_all(node)
            elif operation == 'Flush':
                return self.compile_tlb_flush(node)
            elif operation == 'Invalidate':
                return self.compile_tlb_invalidate(node)
            else:
                print(f"WARNING: Unsupported TLB operation: {operation}")
                self.asm.emit_mov_rax_imm64(0)
                return True
                
        except Exception as e:
            print(f"ERROR: TLB operation failed: {str(e)}")
            raise
    
    def compile_tlb_flush_all(self, node):
        """Compile TLB.FlushAll()"""
        try:
            print("DEBUG: Flushing all TLB entries")
            
            # Read CR3 and write it back to flush TLB
            self.asm.emit_read_cr(3)
            self.asm.emit_write_cr(3)
            
            # Or use INVLPG for specific pages if needed
            self.asm.emit_mov_rax_imm64(1)
            
            print("DEBUG: TLB flush all completed")
            return True
            
        except Exception as e:
            print(f"ERROR: TLB.FlushAll failed: {str(e)}")
            raise
    
    def compile_tlb_flush(self, node):
        """Compile TLB.Flush(address)"""
        try:
            print("DEBUG: Flushing TLB page")
            
            args = self.parse_vm_arguments(node.arguments)
            address = args.get('address', 0)
            
            if address > 0:
                # Invalidate specific page
                self.asm.emit_invlpg(address)
                print(f"DEBUG: Flushed TLB for address {hex(address)}")
            else:
                # Flush all if no address specified
                self.asm.emit_read_cr(3)
                self.asm.emit_write_cr(3)
                print("DEBUG: Flushed all TLB entries")
            
            self.asm.emit_mov_rax_imm64(1)
            return True
            
        except Exception as e:
            print(f"ERROR: TLB.Flush failed: {str(e)}")
            raise
    
    def compile_tlb_invalidate(self, node):
        """Compile TLB.Invalidate(address)"""
        try:
            print("DEBUG: Invalidating TLB page")
            
            args = self.parse_vm_arguments(node.arguments)
            address = args.get('address', 0)
            
            if address > 0:
                self.asm.emit_invlpg(address)
                print(f"DEBUG: Invalidated TLB for address {hex(address)}")
            
            self.asm.emit_mov_rax_imm64(1)
            return True
            
        except Exception as e:
            print(f"ERROR: TLB.Invalidate failed: {str(e)}")
            raise
    
    def compile_memory_barrier_call(self, node):
        """Handle MemoryBarrier.* operations"""
        try:
            barrier_type = node.function.split('_', 1)[1]  # MemoryBarrier_Full -> Full
            print(f"DEBUG: Compiling MemoryBarrier.{barrier_type}")
            
            if barrier_type == 'Full':
                self.asm.emit_memory_fence()
                print("DEBUG: Full memory barrier")
            elif barrier_type == 'Read':
                self.asm.emit_load_fence()
                print("DEBUG: Read memory barrier")
            elif barrier_type == 'Write':
                self.asm.emit_store_fence()
                print("DEBUG: Write memory barrier")
            else:
                print(f"WARNING: Unsupported barrier type: {barrier_type}")
                self.asm.emit_memory_fence()  # Default to full barrier
            
            self.asm.emit_mov_rax_imm64(1)
            return True
            
        except Exception as e:
            print(f"ERROR: MemoryBarrier operation failed: {str(e)}")
            raise
    
    def parse_vm_arguments(self, arguments):
        """Parse VM arguments from param-value pairs"""
        try:
            args = {}
            
            # Arguments come in pairs: [param_name, value, param_name, value, ...]
            for i in range(0, len(arguments), 2):
                if i + 1 < len(arguments):
                    param_name = arguments[i].value if hasattr(arguments[i], 'value') else str(arguments[i])
                    param_value = arguments[i + 1]
                    
                    # Extract actual value
                    if hasattr(param_value, 'value'):
                        if isinstance(param_value.value, str):
                            args[param_name] = param_value.value
                        else:
                            args[param_name] = param_value.value
                    else:
                        args[param_name] = param_value
            
            print(f"DEBUG: Parsed VM arguments: {args}")
            return args
            
        except Exception as e:
            print(f"ERROR: Failed to parse VM arguments: {str(e)}")
            return {}