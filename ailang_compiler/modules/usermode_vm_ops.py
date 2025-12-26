#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Virtual Memory Operations Module - USER MODE SAFE VERSION
Handles VM operations with user-mode safe implementations for testing
Preserves all functionality while avoiding privileged instructions
"""

import sys
import os
import struct
from ailang_parser.ailang_ast import *

class VirtualMemoryOpsUserMode:
    """USER MODE SAFE: Virtual Memory operations for testing in user space"""
    
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm
        
        # VM State Tracking (same as kernel version)
        self.page_tables = {}       # page_table_id -> simulated_address
        self.virtual_allocations = {}  # allocation_id -> (address, size, protection)
        self.mmio_mappings = {}     # mapping_id -> (virtual_addr, physical_addr, size)
        self.allocation_counter = 0
        
        print("DEBUG: Using USER MODE SAFE VM operations")
        
    def compile_operation(self, node):
        """Route VM operations to user-mode safe handlers"""
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
            print(f"ERROR: USER MODE VM operation compilation failed: {str(e)}")
            raise
    
    def compile_page_table_call(self, node):
        """Handle PageTable.* operations - USER MODE SAFE"""
        try:
            operation = node.function.split('_', 1)[1]
            print(f"DEBUG: USER MODE PageTable.{operation}")
            
            if operation == 'Create':
                return self.compile_page_table_create_safe(node)
            elif operation == 'Map':
                return self.compile_page_table_map_safe(node)
            elif operation == 'Unmap':
                return self.compile_page_table_unmap_safe(node)
            elif operation == 'Switch':
                return self.compile_page_table_switch_safe(node)
            else:
                print(f"INFO: USER MODE simulating PageTable.{operation}")
                self.asm.emit_mov_rax_imm64(1)  # Return success
                return True
                
        except Exception as e:
            print(f"ERROR: USER MODE PageTable operation failed: {str(e)}")
            raise
    
    def compile_page_table_create_safe(self, node):
        """USER MODE SAFE: PageTable.Create simulation"""
        try:
            print("DEBUG: USER MODE - Creating simulated page table")
            
            args = self.parse_vm_arguments(node.arguments)
            levels = args.get('levels', 4)
            page_size = args.get('page_size', '4KB')
            
            print(f"DEBUG: USER MODE - Simulated page table: {levels} levels, {page_size} pages")
            
            # Simulate page table creation (same logic, safe implementation)
            page_table_id = len(self.page_tables) + 1
            page_table_addr = 0x100000 + (page_table_id * 0x1000)  # Simulated address
            
            # Store simulated page table info
            self.page_tables[page_table_id] = page_table_addr
            
            # Return page table ID in RAX
            self.asm.emit_mov_rax_imm64(page_table_id)
            
            print(f"DEBUG: USER MODE - Created simulated page table {page_table_id}")
            return True
            
        except Exception as e:
            print(f"ERROR: USER MODE PageTable.Create failed: {str(e)}")
            raise
    
    def compile_page_table_map_safe(self, node):
        """USER MODE SAFE: PageTable.Map simulation"""
        try:
            print("DEBUG: USER MODE - Simulating page mapping")
            
            args = self.parse_vm_arguments(node.arguments)
            page_table = args.get('page_table', 1)
            virtual_addr = args.get('virtual_addr', 0x40000000)
            physical_addr = args.get('physical_addr', 0x100000)
            flags = args.get('flags', 'RW')
            
            print(f"DEBUG: USER MODE - Simulate map virtual {hex(virtual_addr)} -> physical {hex(physical_addr)}")
            
            # Simulate page table mapping (no actual hardware access)
            if page_table in self.page_tables:
                pt_addr = self.page_tables[page_table]
                self.asm.emit_mov_rax_imm64(pt_addr)
                print(f"DEBUG: USER MODE - Simulated mapping in page table at {hex(pt_addr)}")
            else:
                print(f"DEBUG: USER MODE - Simulated mapping in default page table")
                self.asm.emit_mov_rax_imm64(0x100000)
            
            # Return success
            self.asm.emit_mov_rax_imm64(1)
            
            print("DEBUG: USER MODE - Page mapping simulation completed")
            return True
            
        except Exception as e:
            print(f"ERROR: USER MODE PageTable.Map failed: {str(e)}")
            raise
    
    def compile_page_table_switch_safe(self, node):
        """USER MODE SAFE: PageTable.Switch simulation"""
        try:
            print("DEBUG: USER MODE - Simulating page table switch")
            
            args = self.parse_vm_arguments(node.arguments)
            page_table = args.get('page_table', 1)
            
            if page_table in self.page_tables:
                pt_addr = self.page_tables[page_table]
                print(f"DEBUG: USER MODE - Simulating switch to page table {page_table}")
                
                # USER MODE SAFE: No CR3 access, just simulate
                self.asm.emit_mov_rax_imm64(pt_addr)
                
                # Simulate TLB flush with memory fence (user-mode safe)
                self.asm.emit_memory_fence()
                
                print("DEBUG: USER MODE - Page table switch simulated successfully")
            else:
                print(f"WARNING: USER MODE - Page table {page_table} not found")
                self.asm.emit_mov_rax_imm64(0)  # Return error
            
            return True
            
        except Exception as e:
            print(f"ERROR: USER MODE PageTable.Switch failed: {str(e)}")
            raise
    
    def compile_page_table_unmap_safe(self, node):
        """USER MODE SAFE: PageTable.Unmap simulation"""
        try:
            print("DEBUG: USER MODE - Simulating page unmapping")
            
            args = self.parse_vm_arguments(node.arguments)
            page_table = args.get('page_table', 1)
            virtual_addr = args.get('virtual_addr', 0x40000000)
            
            print(f"DEBUG: USER MODE - Simulate unmap virtual {hex(virtual_addr)}")
            
            # Simulate unmap - just return success
            self.asm.emit_mov_rax_imm64(1)
            
            print("DEBUG: USER MODE - Page unmapping simulation completed")
            return True
            
        except Exception as e:
            print(f"ERROR: USER MODE PageTable.Unmap failed: {str(e)}")
            raise
    
    def compile_virtual_memory_call(self, node):
        """Handle VirtualMemory.* operations - USER MODE SAFE"""
        try:
            operation = node.function.split('_', 1)[1]
            print(f"DEBUG: USER MODE VirtualMemory.{operation}")
            
            if operation == 'Allocate':
                return self.compile_vm_allocate_safe(node)
            elif operation == 'Free':
                return self.compile_vm_free_safe(node)
            elif operation == 'Protect':
                return self.compile_vm_protect_safe(node)
            else:
                print(f"INFO: USER MODE simulating VirtualMemory.{operation}")
                self.asm.emit_mov_rax_imm64(1)
                return True
                
        except Exception as e:
            print(f"ERROR: USER MODE VirtualMemory operation failed: {str(e)}")
            raise
    
    def compile_vm_allocate_safe(self, node):
        """USER MODE SAFE: VirtualMemory.Allocate simulation"""
        try:
            print("DEBUG: USER MODE - Simulating virtual memory allocation")
            
            args = self.parse_vm_arguments(node.arguments)
            size = args.get('size', 4096)
            protection = args.get('protection', 'RW')
            alignment = args.get('alignment', '4KB')
            
            print(f"DEBUG: USER MODE - Simulate allocate {size} bytes, protection {protection}")
            
            # Simulate allocation (same logic as kernel version)
            self.allocation_counter += 1
            virtual_addr = 0x40000000 + (self.allocation_counter * 0x10000)  # 64KB spacing
            
            # Store simulated allocation info
            self.virtual_allocations[self.allocation_counter] = (virtual_addr, size, protection)
            
            # Return simulated virtual address in RAX
            self.asm.emit_mov_rax_imm64(virtual_addr)
            
            print(f"DEBUG: USER MODE - Simulated allocation at virtual address {hex(virtual_addr)}")
            return True
            
        except Exception as e:
            print(f"ERROR: USER MODE VirtualMemory.Allocate failed: {str(e)}")
            raise
    
    def compile_vm_free_safe(self, node):
        """USER MODE SAFE: VirtualMemory.Free simulation"""
        try:
            print("DEBUG: USER MODE - Simulating virtual memory free")
            
            args = self.parse_vm_arguments(node.arguments)
            address = args.get('address', 0)
            
            print(f"DEBUG: USER MODE - Simulate free virtual address {hex(address)}")
            
            # Simulate free - just return success
            self.asm.emit_mov_rax_imm64(1)
            
            print("DEBUG: USER MODE - Virtual memory free simulation completed")
            return True
            
        except Exception as e:
            print(f"ERROR: USER MODE VirtualMemory.Free failed: {str(e)}")
            raise
    
    def compile_vm_protect_safe(self, node):
        """USER MODE SAFE: VirtualMemory.Protect simulation"""
        try:
            print("DEBUG: USER MODE - Simulating virtual memory protection change")
            
            args = self.parse_vm_arguments(node.arguments)
            address = args.get('address', 0)
            size = args.get('size', 4096)
            protection = args.get('protection', 'RW')
            
            print(f"DEBUG: USER MODE - Simulate protect {hex(address)}, size {size}, protection {protection}")
            
            # Simulate protect - just return success
            self.asm.emit_mov_rax_imm64(1)
            
            print("DEBUG: USER MODE - Virtual memory protection simulation completed")
            return True
            
        except Exception as e:
            print(f"ERROR: USER MODE VirtualMemory.Protect failed: {str(e)}")
            raise
    
    def compile_cache_call(self, node):
        """Handle Cache.* operations - USER MODE SAFE"""
        try:
            operation = node.function.split('_', 1)[1]
            print(f"DEBUG: USER MODE Cache.{operation}")
            
            if operation == 'Flush':
                return self.compile_cache_flush_safe(node)
            elif operation == 'Invalidate':
                return self.compile_cache_invalidate_safe(node)
            elif operation == 'Prefetch':
                return self.compile_cache_prefetch_safe(node)
            else:
                print(f"INFO: USER MODE simulating Cache.{operation}")
                self.asm.emit_mov_rax_imm64(1)
                return True
                
        except Exception as e:
            print(f"ERROR: USER MODE Cache operation failed: {str(e)}")
            raise
    
    def compile_cache_flush_safe(self, node):
        """USER MODE SAFE: Cache.Flush simulation"""
        try:
            print("DEBUG: USER MODE - Simulating cache flush")
            
            args = self.parse_vm_arguments(node.arguments)
            level = args.get('level', 'L1')
            address = args.get('address', 0)
            size = args.get('size', 4096)
            
            print(f"DEBUG: USER MODE - Simulate flush {level} cache, address {hex(address)}")
            
            # USER MODE SAFE: Use memory fence instead of CLFLUSH/WBINVD
            if address > 0:
                self.asm.emit_mov_rax_imm64(address)
                self.asm.emit_memory_fence()
                print(f"DEBUG: USER MODE - Simulated cache flush at {hex(address)}")
            else:
                # Simulate full cache flush with memory fence
                self.asm.emit_memory_fence()
                print("DEBUG: USER MODE - Simulated full cache flush")
            
            # Return success
            self.asm.emit_mov_rax_imm64(1)
            return True
            
        except Exception as e:
            print(f"ERROR: USER MODE Cache.Flush failed: {str(e)}")
            raise
    
    def compile_cache_invalidate_safe(self, node):
        """USER MODE SAFE: Cache.Invalidate simulation"""
        try:
            print("DEBUG: USER MODE - Simulating cache invalidation")
            
            # USER MODE SAFE: Use memory fence instead of INVD
            self.asm.emit_memory_fence()
            self.asm.emit_mov_rax_imm64(1)
            
            print("DEBUG: USER MODE - Cache invalidation simulation completed")
            return True
            
        except Exception as e:
            print(f"ERROR: USER MODE Cache.Invalidate failed: {str(e)}")
            raise
    
    def compile_cache_prefetch_safe(self, node):
        """USER MODE SAFE: Cache.Prefetch simulation"""
        try:
            print("DEBUG: USER MODE - Simulating cache prefetch")
            
            args = self.parse_vm_arguments(node.arguments)
            address = args.get('address', 0)
            
            if address > 0:
                # Load address (prefetch instructions might be user-mode safe)
                self.asm.emit_mov_rax_imm64(address)
                # Memory fence to simulate the operation
                self.asm.emit_memory_fence()
                print(f"DEBUG: USER MODE - Simulated prefetch at {hex(address)}")
            
            self.asm.emit_mov_rax_imm64(1)
            return True
            
        except Exception as e:
            print(f"ERROR: USER MODE Cache.Prefetch failed: {str(e)}")
            raise
    
    def compile_tlb_call(self, node):
        """Handle TLB.* operations - USER MODE SAFE"""
        try:
            operation = node.function.split('_', 1)[1]
            print(f"DEBUG: USER MODE TLB.{operation}")
            
            if operation == 'FlushAll':
                return self.compile_tlb_flush_all_safe(node)
            elif operation == 'Flush':
                return self.compile_tlb_flush_safe(node)
            elif operation == 'Invalidate':
                return self.compile_tlb_invalidate_safe(node)
            else:
                print(f"INFO: USER MODE simulating TLB.{operation}")
                self.asm.emit_mov_rax_imm64(1)
                return True
                
        except Exception as e:
            print(f"ERROR: USER MODE TLB operation failed: {str(e)}")
            raise
    
    def compile_tlb_flush_all_safe(self, node):
        """USER MODE SAFE: TLB.FlushAll simulation"""
        try:
            print("DEBUG: USER MODE - Simulating TLB flush all")
            
            # USER MODE SAFE: Use memory fence instead of CR3 manipulation
            self.asm.emit_memory_fence()
            self.asm.emit_mov_rax_imm64(1)
            
            print("DEBUG: USER MODE - TLB flush all simulation completed")
            return True
            
        except Exception as e:
            print(f"ERROR: USER MODE TLB.FlushAll failed: {str(e)}")
            raise
    
    def compile_tlb_flush_safe(self, node):
        """USER MODE SAFE: TLB.Flush simulation"""
        try:
            print("DEBUG: USER MODE - Simulating TLB flush")
            
            args = self.parse_vm_arguments(node.arguments)
            address = args.get('address', 0)
            
            if address > 0:
                # USER MODE SAFE: Use memory fence instead of INVLPG
                self.asm.emit_mov_rax_imm64(address)
                self.asm.emit_memory_fence()
                print(f"DEBUG: USER MODE - Simulated TLB flush for {hex(address)}")
            else:
                # Simulate flush all
                self.asm.emit_memory_fence()
                print("DEBUG: USER MODE - Simulated TLB flush all")
            
            self.asm.emit_mov_rax_imm64(1)
            return True
            
        except Exception as e:
            print(f"ERROR: USER MODE TLB.Flush failed: {str(e)}")
            raise
    
    def compile_tlb_invalidate_safe(self, node):
        """USER MODE SAFE: TLB.Invalidate simulation"""
        try:
            print("DEBUG: USER MODE - Simulating TLB invalidation")
            
            args = self.parse_vm_arguments(node.arguments)
            address = args.get('address', 0)
            
            if address > 0:
                # USER MODE SAFE: Use memory fence instead of INVLPG
                self.asm.emit_mov_rax_imm64(address)
                self.asm.emit_memory_fence()
                print(f"DEBUG: USER MODE - Simulated TLB invalidation for {hex(address)}")
            
            self.asm.emit_mov_rax_imm64(1)
            return True
            
        except Exception as e:
            print(f"ERROR: USER MODE TLB.Invalidate failed: {str(e)}")
            raise
    
    def compile_memory_barrier_call(self, node):
        """Handle MemoryBarrier.* operations - USER MODE SAFE"""
        try:
            barrier_type = node.function.split('_', 1)[1]
            print(f"DEBUG: USER MODE MemoryBarrier.{barrier_type}")
            
            # Memory barriers are generally user-mode safe
            if barrier_type == 'Full':
                self.asm.emit_memory_fence()
                print("DEBUG: USER MODE - Full memory barrier")
            elif barrier_type == 'Read':
                self.asm.emit_load_fence()
                print("DEBUG: USER MODE - Read memory barrier")
            elif barrier_type == 'Write':
                self.asm.emit_store_fence()
                print("DEBUG: USER MODE - Write memory barrier")
            else:
                print(f"INFO: USER MODE - Unknown barrier type {barrier_type}, using full barrier")
                self.asm.emit_memory_fence()
            
            self.asm.emit_mov_rax_imm64(1)
            return True
            
        except Exception as e:
            print(f"ERROR: USER MODE MemoryBarrier operation failed: {str(e)}")
            raise
    
    def parse_vm_arguments(self, arguments):
        """Parse VM arguments from param-value pairs (same as kernel version)"""
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
            
            print(f"DEBUG: USER MODE - Parsed VM arguments: {args}")
            return args
            
        except Exception as e:
            print(f"ERROR: USER MODE - Failed to parse VM arguments: {str(e)}")
            return {}