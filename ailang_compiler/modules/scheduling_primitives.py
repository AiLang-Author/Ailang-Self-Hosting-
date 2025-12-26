#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
AILANG Scheduling Primitives
Core building blocks for userland schedulers
"""

import struct
import sys
import os

# Add ailang_parser to path to find AST nodes
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ailang_parser')))
from ailang_ast import LoopActor

class SchedulingPrimitives:
    """Handles task scheduling and actor model primitives"""
    
    # Actor states
    STATE_EMPTY = 0
    STATE_READY = 1
    STATE_RUNNING = 2
    STATE_BLOCKED = 3
    STATE_DEAD = 4
    
    # ACB (Actor Control Block) layout - 128 bytes per actor
    # Offset | Content
    # -------|--------
    # 0-7    | RAX
    # 8-15   | RBX
    # 16-23  | RCX
    # 24-31  | RDX
    # 32-39  | RSI
    # 40-47  | RDI
    # 48-55  | RBP
    # 56-63  | RSP
    # 64-71  | R8
    # 72-79  | R9
    # 80-87  | R10
    # 88-95  | R11
    # 96-103 | R12
    # 104-111| R13
    # 112-119| R14
    # 120-127| R15
    
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm
        self.max_actors = 0 # Will be calculated by discover_actors
        self.acb_size = 128   # Bytes per actor
        self.spawn_queue = []
        self.current_actor = 0
    
    def discover_actors(self, node):
        """A pre-pass to count all LoopActor declarations."""
        if not hasattr(node, 'declarations'):
            return

        for decl in node.declarations:
            if isinstance(decl, LoopActor):
                self.max_actors += 1
        
        print(f"DEBUG: Discovered {self.max_actors} LoopActor declarations.")

    def compile_operation(self, node):
        """Route scheduling operations to their handlers"""
        op_map = {
            'LoopSpawn': self.compile_loop_spawn,
            'LoopYield': self.compile_loop_yield,
            'LoopGetACB': self.compile_get_acb,
            'LoopSetACB': self.compile_set_acb,
            'LoopGetCurrentActor': self.compile_get_current_actor,
            'LoopSetCurrentActor': self.compile_set_current_actor,
        }
        
        if node.function in op_map:
            return op_map[node.function](node)
        return False
        
    def initialize_actor_table(self):
        """Initialize the actor table in memory"""
        # Allocate space for actor table
        table_size = self.max_actors * self.actor_size
        
        # For now, use stack space (in real implementation, use heap)
        self.asm.emit_sub_rsp_imm32(table_size)
        self.asm.emit_mov_rax_rsp()  # Table base in RAX
        
        # Store table base for later use
        # (In real implementation, store in a global)
        self.asm.emit_push_rax()
        
        print(f"DEBUG: Initialized actor table for {self.max_actors} actors")
        
    def compile_loop_actor(self, node):
        """Compile LoopActor as a proper subroutine with skip jump"""
        try:
            actor_name = node.name
            print(f"DEBUG: Compiling LoopActor.{actor_name} as subroutine")
            
            # Register as a subroutine
            label = self.asm.create_label()
            self.compiler.subroutines[f"Actor.{actor_name}"] = label
            
            # CRITICAL: Skip over actor code in main flow
            skip_label = self.asm.create_label()
            print(f"DEBUG: Emitting skip jump at position {len(self.asm.code)}")
            self.asm.emit_jump_to_label(skip_label, "JMP")
            print(f"DEBUG: Skip jump emitted, will jump to label {skip_label}")
            
            # Subroutine entry
            self.asm.mark_label(label)
            print(f"DEBUG: Actor code starts at position {len(self.asm.code)}")
            
            # DON'T create new stack frame - use caller's frame
            # This allows actors to access main program variables
            # Comment out: self.asm.emit_bytes(0x55)  # PUSH RBP
            # Comment out: self.asm.emit_bytes(0x48, 0x89, 0xE5)  # MOV RBP, RSP
            
            # Compile actor body
            for stmt in node.body:
                self.compiler.compile_node(stmt)
            
            # No epilogue needed since we didn't create prologue  
            # Comment out: self.asm.emit_bytes(0x48, 0x89, 0xEC)  # MOV RSP, RBP
            # Comment out: self.asm.emit_bytes(0x5D)  # POP RBP
            self.asm.emit_ret()
            
            # Mark where main flow continues
            self.asm.mark_label(skip_label)
            print(f"DEBUG: Skip label marked at position {len(self.asm.code)}")
            
            print(f"DEBUG: Actor.{actor_name} registered as subroutine")
            return True
            
        except Exception as e:
            print(f"ERROR: LoopActor compilation failed: {str(e)}")
            raise
        
        
    def compile_loop_spawn(self, node):
        """Register actor for execution"""
        print("DEBUG: Compiling LoopSpawn")
        
        if len(node.arguments) > 0 and hasattr(node.arguments[0], 'value'):
            actor_name = node.arguments[0].value
            subroutine_name = f"Actor.{actor_name}"
            
            if subroutine_name in self.compiler.subroutines:
                self.spawn_queue.append(subroutine_name)
                handle = len(self.spawn_queue)
                print(f"DEBUG: Added {subroutine_name} to spawn_queue (handle {handle})")
                self.asm.emit_mov_rax_imm64(handle)
            else:
                print(f"DEBUG: Actor {subroutine_name} not found")
                self.asm.emit_mov_rax_imm64(0)
        else:
            self.asm.emit_mov_rax_imm64(0)
        
        return True

    def compile_loop_yield(self, node):
        """Execute next spawned actor in round-robin"""
        print("DEBUG: Compiling LoopYield")
        
        # Check if we have actors to run
        if hasattr(self, 'spawn_queue') and self.spawn_queue:
            # Initialize counter if needed
            if not hasattr(self, 'current_actor'):
                self.current_actor = 0
                
            # Get next actor in round-robin order
            actor_index = self.current_actor % len(self.spawn_queue)
            actor_name = self.spawn_queue[actor_index]
            
            print(f"DEBUG: Yielding to {actor_name} (index {actor_index})")
            
            # Call the actor if it exists
            if actor_name in self.compiler.subroutines:
                label = self.compiler.subroutines[actor_name]
                self.asm.emit_call_to_label(label)
            else:
                print(f"WARNING: Actor {actor_name} not found in subroutines")
                
            # Move to next actor for next yield
            self.current_actor += 1
        else:
            print("DEBUG: No actors in spawn queue")
            self.asm.emit_nop()
        
        return True
    
    
    def compile_get_acb(self, node):
        """Get ACB table base address"""
        print("DEBUG: Compiling LoopGetACB")
        if 'system_acb_table' in self.compiler.variables:
            offset = self.compiler.variables['system_acb_table']
            self.asm.emit_bytes(0x48, 0x8B, 0x85)  # MOV RAX, [RBP-offset]
            self.asm.emit_bytes(*struct.pack('<i', -offset))
        else:
            self.asm.emit_mov_rax_imm64(0)
        return True

    def compile_get_current_actor(self, node):
        """Get current actor ID"""
        print("DEBUG: Compiling LoopGetCurrentActor")
        if 'system_current_actor' in self.compiler.variables:
            offset = self.compiler.variables['system_current_actor']
            self.asm.emit_bytes(0x48, 0x8B, 0x85)  # MOV RAX, [RBP-offset]
            self.asm.emit_bytes(*struct.pack('<i', -offset))
        else:
            self.asm.emit_mov_rax_imm64(0)
        return True
    
    def compile_set_current_actor(self, node):
        """Set current actor ID"""
        print("DEBUG: Compiling LoopSetCurrentActor")
        
        # Get the actor ID to set
        if len(node.arguments) > 0:
            self.compiler.compile_expression(node.arguments[0])
        
        if 'system_current_actor' in self.compiler.variables:
            offset = self.compiler.variables['system_current_actor']
            self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP-offset], RAX
            self.asm.emit_bytes(*struct.pack('<i', -offset))
        
        return True
        
    def compile_set_acb(self, node):
        """Set ACB table base address"""
        print("DEBUG: Compiling LoopSetACB")
        
        # Get the address to set
        if len(node.arguments) > 0:
            self.compiler.compile_expression(node.arguments[0])
        
        if 'system_acb_table' in self.compiler.variables:
            offset = self.compiler.variables['system_acb_table']
            self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP-offset], RAX
            self.asm.emit_bytes(*struct.pack('<i', -offset))
        
        return True   
        
    def compile_loop_join(self, node):
        """Compile LoopJoin - wait for actor completion"""
        print("DEBUG: Compiling LoopJoin primitive")
        
        # Get actor handle
        self.compiler.compile_expression(node.handle)
        self.asm.emit_push_rax()  # Save handle
        
        # Spin-wait loop (userland scheduler can do better)
        wait_loop = self.asm.create_label()
        done_label = self.asm.create_label()
        
        self.asm.mark_label(wait_loop)
        
        # Check actor state
        self.asm.emit_mov_rbx_from_stack(0)  # Get handle
        self._get_actor_state()  # State in RAX
        
        # If DEAD, we're done
        self.asm.emit_cmp_rax_imm8(self.STATE_DEAD)
        self.asm.emit_jump_to_label(done_label, "JE")
        
        # Otherwise yield and retry
        self._save_actor_context()
        self._call_scheduler_hook()
        self._restore_actor_context()
        
        self.asm.emit_jump_to_label(wait_loop, "JMP")
        
        self.asm.mark_label(done_label)
        
        # Get return value
        self.asm.emit_pop_rbx()  # Handle
        self._get_actor_return_value()  # Return value in RAX
        
        return True
        
    def compile_loop_get_state(self, node):
        """Compile LoopGetState - query actor state"""
        print("DEBUG: Compiling LoopGetState primitive")
        
        # Get actor handle
        self.compiler.compile_expression(node.handle)
        self.asm.emit_mov_rbx_rax()
        
        # Get state from control block
        self._get_actor_state()  # State in RAX
        
        return True
        
    def compile_loop_set_priority(self, node):
        """Compile LoopSetPriority - set scheduling hint"""
        print("DEBUG: Compiling LoopSetPriority primitive")
        
        # Get actor handle
        self.compiler.compile_expression(node.handle)
        self.asm.emit_push_rax()
        
        # Get priority value
        self.compiler.compile_expression(node.priority)
        self.asm.emit_mov_rcx_rax()  # Priority in RCX
        
        # Set in control block
        self.asm.emit_pop_rbx()  # Handle in RBX
        self._set_actor_priority()
        
        return True
        
    def compile_loop_get_current(self, node):
        """Compile LoopGetCurrent - get current actor handle"""
        print("DEBUG: Compiling LoopGetCurrent primitive")
        
        # Return current actor handle
        # (In real implementation, this would be in a register or TLS)
        self._get_current_actor_handle()  # Handle in RAX
        
        return True
        
    def compile_loop_suspend(self, node):
        """Compile LoopSuspend - suspend an actor"""
        print("DEBUG: Compiling LoopSuspend primitive")
        
        # Get actor handle
        self.compiler.compile_expression(node.handle)
        self.asm.emit_mov_rbx_rax()
        
        # Set state to SUSPENDED
        self._set_actor_state(self.STATE_SUSPENDED)
        
        return True
        
    def compile_loop_resume(self, node):
        """Compile LoopResume - resume a suspended actor"""
        print("DEBUG: Compiling LoopResume primitive")
        
        # Get actor handle
        self.compiler.compile_expression(node.handle)
        self.asm.emit_mov_rbx_rax()
        
        # Set state to READY
        self._set_actor_state(self.STATE_READY)
        
        return True
        
    # Helper methods for actor management
    
    def _save_actor_context(self):
        """Save current CPU context to actor control block"""
        # Save all general purpose registers
        self.asm.emit_push_rax()
        self.asm.emit_push_rbx()
        self.asm.emit_push_rcx()
        self.asm.emit_push_rdx()
        self.asm.emit_push_rsi()
        self.asm.emit_push_rdi()
        self.asm.emit_push_r8()
        self.asm.emit_push_r9()
        self.asm.emit_push_r10()
        self.asm.emit_push_r11()
        self.asm.emit_push_r12()
        self.asm.emit_push_r13()
        self.asm.emit_push_r14()
        self.asm.emit_push_r15()
        
        # Save stack pointer
        self.asm.emit_mov_rax_rsp()
        # Store in control block...
        
    def _restore_actor_context(self):
        """Restore CPU context from actor control block"""
        # Restore all registers in reverse order
        self.asm.emit_pop_r15()
        self.asm.emit_pop_r14()
        self.asm.emit_pop_r13()
        self.asm.emit_pop_r12()
        self.asm.emit_pop_r11()
        self.asm.emit_pop_r10()
        self.asm.emit_pop_r9()
        self.asm.emit_pop_r8()
        self.asm.emit_pop_rdi()
        self.asm.emit_pop_rsi()
        self.asm.emit_pop_rdx()
        self.asm.emit_pop_rcx()
        self.asm.emit_pop_rbx()
        self.asm.emit_pop_rax()
        
    def _find_free_actor_slot(self):
        """Find a free actor slot, return handle in RAX"""
        # For MVP: just use a counter
        if not hasattr(self.compiler, 'next_actor_handle'):
            self.compiler.next_actor_handle = 1
        
        handle = self.compiler.next_actor_handle
        self.compiler.next_actor_handle += 1
        
        self.asm.emit_mov_rax_imm64(handle)
        
    def _allocate_actor_stack(self):
        """Allocate stack space for an actor"""
        # Each actor gets 64KB of stack
        stack_size = 65536
        self.asm.emit_sub_rsp_imm32(stack_size)
        self.asm.emit_mov_rax_rsp()  # Stack pointer in RAX
        
    def _set_actor_state(self, state):
        """Set actor state (handle in RBX, state constant)"""
        self.asm.emit_mov_rax_imm64(state)
        # Store in control block at offset 0
        # (Simplified - real implementation would calculate offset)
        
    def _get_actor_state(self):
        """Get actor state (handle in RBX, returns in RAX)"""
        # Load from control block at offset 0
        self.asm.emit_mov_rax_imm64(self.STATE_READY)  # Placeholder
        
    def _set_actor_priority(self):
        """Set actor priority (handle in RBX, priority in RCX)"""
        # Store in control block at offset 8
        pass
        
    def _set_actor_ip(self, label):
        """Set actor instruction pointer"""
        # Store label reference for later resolution
        pass
        
    def _get_actor_return_value(self):
        """Get actor return value (handle in RBX, returns in RAX)"""
        self.asm.emit_mov_rax_imm64(0)  # Placeholder
        
    def _get_current_actor_handle(self):
        """Get current actor handle in RAX"""
        # In real implementation, this would be in TLS or a register
        self.asm.emit_mov_rax_imm64(0)  # Placeholder
        
    def _set_current_actor_state(self, state):
        """Set current actor's state"""
        self._get_current_actor_handle()
        self.asm.emit_mov_rbx_rax()
        self._set_actor_state(state)
        
    def _call_scheduler_hook(self):
        """Call the registered scheduler (if any)"""
        # This is where userland schedulers plug in
        # For now, just a NOP
        self.asm.emit_nop()
        
        
    # In scheduling_primitives.py, add hooks

def compile_loop_send(self, node):
    """Enhanced LoopSend with deadlock detection"""
    # ... existing send code ...
    
    # If debug level >= 3, check for deadlock
    if self.compiler.debug_ops.debug_level >= 3:
        # Get current actor ID
        self._get_current_actor_handle()
        self.asm.emit_mov_rdi_rax()  # Waiting actor
        
        # Get target actor ID
        self.compiler.compile_expression(node.target)
        self.asm.emit_mov_rsi_rax()  # Waited-for actor
        
        # Check for deadlock
        self.asm.emit_call('__debug_deadlock_check')
    
    # Continue with normal send...

def compile_memory_access(self, address, is_write=False):
    """Wrap memory access with race detection"""
    if self.compiler.debug_ops.debug_level >= 3:
        # Set up race detection
        self.asm.emit_push_rdi()
        self.asm.emit_push_rsi()
        self.asm.emit_push_rdx()
        
        self.asm.emit_mov_rdi_from_address(address)  # Memory address
        self.asm.emit_mov_rsi_imm64(1 if is_write else 0)  # Access type
        self._get_current_actor_handle()
        self.asm.emit_mov_rdx_rax()  # Actor ID
        
        self.asm.emit_call('__debug_race_check')
        
        self.asm.emit_pop_rdx()
        self.asm.emit_pop_rsi()
        self.asm.emit_pop_rdi()
    
    # Perform actual memory access...
    