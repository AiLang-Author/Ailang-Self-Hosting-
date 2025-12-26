# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Enhanced Debug Operations Module for AILANG Compiler
Preserves existing functionality and adds advanced debugging features
"""

import struct
from typing import Optional, Dict, Any, List
from enum import Enum, auto

class DebugNodeType(Enum):
    """Types of debug operations"""
    # Existing types
    BLOCK = auto()
    ASSERT = auto()
    TRACE = auto()
    BREAK = auto()
    MEMORY = auto()
    PERF = auto()
    INSPECT = auto()
    
    # New enhanced types
    STACKTRACE = auto()
    MEMORY_DUMP = auto()
    WATCH = auto()
    LOCALS = auto()
    REGISTERS = auto()
    INTERACTIVE = auto()
    BREAKPOINT = auto()
    PROFILE = auto()
    LEAK_CHECK = auto()
    CORE = auto()
    CONFIG = auto()

class DebugOps:
    """Enhanced debug operations with backward compatibility"""
    
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm
        
        # Configuration from command-line flags
        self.debug_enabled = False
        self.debug_level = 0  # -D0 through -D4
        self.profile_enabled = False  # -P flag
        self.debug_flags = set()
        
        # Enhanced features
        self.watchpoints = {}
        self.breakpoints = {}
        self.profile_data = {}
        self.interactive_mode = False
        
        # Runtime support tracking
        self.runtime_emitted = False
        
    def set_debug_options(self, options: Dict[str, Any]):
        """Configure debug settings from compiler flags"""
        self.debug_enabled = options.get('debug', False)
        self.debug_level = options.get('debug_level', 0)
        self.profile_enabled = options.get('profile', False)
        self.debug_flags = options.get('debug_flags', set())
        
        # Map debug levels to features
        if self.debug_level >= 1:
            self.debug_flags.add('assert')
        if self.debug_level >= 2:
            self.debug_flags.update(['trace', 'locals', 'stacktrace'])
        if self.debug_level >= 3:
            self.debug_flags.update(['memory', 'watch', 'registers'])
        if self.debug_level >= 4:
            self.debug_flags.update(['all', 'interactive', 'breakpoint', 'core'])
        
        if self.profile_enabled:
            self.debug_flags.add('profile')
            
        print(f"DEBUG: Level={self.debug_level}, Profile={self.profile_enabled}, Flags={self.debug_flags}")
        
    def should_compile_debug(self, node_type: DebugNodeType) -> bool:
        """Check if debug node should be compiled based on level"""
        if self.debug_level == 0:
            return False
            
        level_requirements = {
            DebugNodeType.ASSERT: 1,
            DebugNodeType.TRACE: 2,
            DebugNodeType.STACKTRACE: 2,
            DebugNodeType.LOCALS: 2,
            DebugNodeType.MEMORY_DUMP: 3,
            DebugNodeType.WATCH: 3,
            DebugNodeType.REGISTERS: 3,
            DebugNodeType.BREAKPOINT: 4,
            DebugNodeType.INTERACTIVE: 4,
            DebugNodeType.CORE: 4,
            DebugNodeType.PROFILE: -1,  # Special: requires -P flag
        }
        
        if node_type == DebugNodeType.PROFILE:
            return self.profile_enabled
            
        required_level = level_requirements.get(node_type, 4)
        return self.debug_level >= required_level
        
    def compile_operation(self, node):
        """Main entry point for debug operations"""
        node_type = type(node).__name__
        
        # Handle FunctionCall nodes for DebugPerf
        if node_type == 'FunctionCall':
            if hasattr(node, 'function') and node.function.startswith('DebugPerf.'):
                operation = node.function.split('.', 1)[1]  # Get 'Start' from 'DebugPerf.Start'
                label_node = node.arguments[0] if node.arguments else None
                label = label_node.value if label_node and hasattr(label_node, 'value') else None
                # Create a simple object with the needed attributes
                class PerfNode:
                    pass
                perf_node = PerfNode()
                perf_node.operation = operation
                perf_node.label = label
                return self.compile_debug_perf(perf_node)
            # Don't try to call non-existent method
            return False
        
        handlers = {
            'DebugBlock': self.compile_debug_block,
            'DebugAssert': self.compile_debug_assert,
            'DebugTrace': self.compile_debug_trace,
            'DebugBreak': self.compile_debug_break,
            'DebugMemory': self.compile_debug_memory,
            'DebugPerf': self.compile_debug_perf,
            'DebugInspect': self.compile_debug_inspect,
        }
        
        handler = handlers.get(node_type)
        if handler:
            return handler(node)
        else:
            # Unknown debug operation - don't raise error, just return False
            return False
        
    def _compile_legacy_debug(self, node):
        """Handle existing debug operations"""
        handlers = {
            'DebugBlock': self.compile_debug_block,
            'DebugAssert': self.compile_debug_assert,
            'DebugTrace': self.compile_debug_trace,
            'DebugBreak': self.compile_debug_break,
            'DebugMemory': self.compile_debug_memory,
            'DebugPerf': self.compile_debug_perf,
            'DebugInspect': self.compile_debug_inspect,
        }
        
        handler = handlers.get(type(node).__name__)
        if handler:
            return handler(node)
        return False
        
    def _compile_enhanced_debug(self, node):
        """Handle new enhanced debug operations"""
        if not self.should_compile_debug(node.node_type):
            self.asm.emit_nop()  # Compile to NOP if disabled
            return True
            
        handlers = {
            DebugNodeType.STACKTRACE: self.compile_stacktrace,
            DebugNodeType.MEMORY_DUMP: self.compile_memory_dump,
            DebugNodeType.WATCH: self.compile_watch,
            DebugNodeType.LOCALS: self.compile_locals,
            DebugNodeType.REGISTERS: self.compile_registers,
            DebugNodeType.INTERACTIVE: self.compile_interactive,
            DebugNodeType.BREAKPOINT: self.compile_breakpoint,
            DebugNodeType.PROFILE: self.compile_profile,
            DebugNodeType.LEAK_CHECK: self.compile_leak_check,
            DebugNodeType.CORE: self.compile_core_dump,
        }
        
        handler = handlers.get(node.node_type)
        if handler:
            return handler(node)
        return False
        
    # ========== EXISTING DEBUG OPERATIONS (PRESERVED) ==========
    
    def compile_debug_block(self, node):
        """Compile debug block - existing implementation preserved"""
        if not self.debug_enabled:
            return
            
        if node.level > self.debug_level:
            return
            
        print(f"DEBUG: Compiling debug block '{node.label}' at level {node.level}")
        
        self.emit_debug_marker(node.label, "block_start")
        
        for stmt in node.body:
            self.compiler.compile_node(stmt)
            
        self.emit_debug_marker(node.label, "block_end")
        
    def compile_debug_assert(self, node):
        """Compile debug assertion - existing implementation preserved"""
        if not self.debug_enabled:
            return
            
        if 'assert' not in self.debug_flags and 'all' not in self.debug_flags:
            return
            
        print(f"DEBUG: Compiling assertion with message: {node.message}")
        
        self.compiler.compile_expression(node.condition)
        
        pass_label = self.asm.create_label()
        self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        self.asm.emit_jump_to_label(pass_label, "JNZ")
        
        self.emit_assertion_failure(node.message)
        
        self.asm.mark_label(pass_label)
        
    def compile_debug_trace(self, node):
        """Existing trace implementation"""
        if not self.debug_enabled:
            return
            
        if 'trace' not in self.debug_flags and 'all' not in self.debug_flags:
            return
            
        print(f"DEBUG: Compiling trace point '{node.label}' type={node.trace_type}")
        
        self.emit_debug_marker(node.label, f"trace_{node.trace_type.lower()}")
        
        if node.values:
            for value in node.values:
                self.compiler.compile_expression(value)
                
    def compile_debug_break(self, node):
        """Existing breakpoint implementation"""
        if not self.debug_enabled:
            return
            
        print(f"DEBUG: Compiling breakpoint '{node.label}'")
        
        if node.break_type == "Simple":
            self.asm.emit_byte(0xCC)
        elif node.break_type == "Conditional" and node.condition:
            self.compiler.compile_expression(node.condition)
            
            skip_label = self.asm.create_label()
            self.asm.emit_bytes(0x48, 0x85, 0xC0)
            self.asm.emit_jump_to_label(skip_label, "JZ")
            
            self.asm.emit_byte(0xCC)
            
            self.asm.mark_label(skip_label)
            
    def compile_debug_memory(self, node):
        """Existing memory debug - enhanced in memory_dump"""
        if not self.debug_enabled:
            return
            
        if 'mem' not in self.debug_flags and 'all' not in self.debug_flags:
            return
            
        print(f"DEBUG: Memory debug operation: {node.operation}")
        
        self.emit_debug_marker(f"mem_{node.operation}", "memory")
        
    def compile_debug_perf(self, node):
        """Existing performance measurement - enhanced with -P flag"""
        if not self.profile_enabled:
            return
            
        if node.operation == "Start":
            self.asm.emit_bytes(0x0F, 0x31)  # RDTSC
            self.asm.emit_bytes(0x48, 0xC1, 0xE2, 0x20)  # SHL RDX, 32
            self.asm.emit_bytes(0x48, 0x09, 0xD0)  # OR RAX, RDX
            
            # Store timestamp: MOV [RBP-offset], RAX
            var_name = f"__perf_start_{node.label}"
            if var_name in self.compiler.variables:
                offset = self.compiler.variables[var_name]
                # Use proper instruction encoding for offset size
                if offset <= 127:
                    # 8-bit displacement: MOV [RBP-imm8], RAX
                    self.asm.emit_bytes(0x48, 0x89, 0x45)  # MOV [RBP+disp8], RAX
                    self.asm.emit_bytes((256 - offset) & 0xFF)
                else:
                    # 32-bit displacement: MOV [RBP-imm32], RAX  
                    self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP+disp32], RAX
                    disp32 = (0x100000000 - offset) & 0xFFFFFFFF
                    self.asm.emit_bytes(disp32 & 0xFF, (disp32 >> 8) & 0xFF, 
                                       (disp32 >> 16) & 0xFF, (disp32 >> 24) & 0xFF)
                
        elif node.operation in ("Stop", "End"):  # Support both Stop and End
            # Read end timestamp
            self.asm.emit_bytes(0x0F, 0x31)  # RDTSC
            self.asm.emit_bytes(0x48, 0xC1, 0xE2, 0x20)
            self.asm.emit_bytes(0x48, 0x09, 0xD0)
            
            # Calculate delta: SUB RAX, [RBP-offset]
            var_name = f"__perf_start_{node.label}"
            if var_name in self.compiler.variables:
                offset = self.compiler.variables[var_name]
                # Use proper instruction encoding for offset size
                if offset <= 127:
                    # 8-bit displacement: SUB RAX, [RBP-imm8]
                    self.asm.emit_bytes(0x48, 0x2B, 0x45)  # SUB RAX, [RBP+disp8]
                    self.asm.emit_bytes((256 - offset) & 0xFF)
                else:
                    # 32-bit displacement: SUB RAX, [RBP-imm32]
                    self.asm.emit_bytes(0x48, 0x2B, 0x85)  # SUB RAX, [RBP+disp32]
                    disp32 = (0x100000000 - offset) & 0xFFFFFFFF
                    self.asm.emit_bytes(disp32 & 0xFF, (disp32 >> 8) & 0xFF,
                                       (disp32 >> 16) & 0xFF, (disp32 >> 24) & 0xFF)
                
                # Store result for reporting
                self.profile_data[node.label] = True
                
                # Print performance result: [PERF] label: cycles cycles (time ms)
                # RAX now contains the cycle count
                self.asm.emit_push_rax()  # Save cycle count
                
                # Print "[PERF] "
                perf_prefix = f"[PERF] {node.label}: "
                prefix_offset = self.asm.add_string(perf_prefix)
                self.asm.emit_mov_rax_imm64(1)  # sys_write
                self.asm.emit_mov_rdi_imm64(1)  # stdout
                self.asm.emit_load_data_address('rsi', prefix_offset)
                self.asm.emit_mov_rdx_imm64(len(perf_prefix))
                self.asm.emit_syscall()
                
                # Pop and print cycle count
                self.asm.emit_pop_rax()
                self.asm.emit_print_number()
                
                # Print " cycles\n"
                suffix = " cycles\n"
                suffix_offset = self.asm.add_string(suffix)
                self.asm.emit_mov_rax_imm64(1)  # sys_write
                self.asm.emit_mov_rdi_imm64(1)  # stdout
                self.asm.emit_load_data_address('rsi', suffix_offset)
                self.asm.emit_mov_rdx_imm64(len(suffix))
                self.asm.emit_syscall()
                
    def compile_debug_inspect(self, node):
        """Existing inspect implementation"""
        if not self.debug_enabled:
            return
            
        if 'inspect' not in self.debug_flags and 'all' not in self.debug_flags:
            return
            
        print(f"DEBUG: Compiling inspect for '{node.target}'")
        
        self.emit_debug_marker(f"inspect_{node.target}", "inspect")
        
    # ========== NEW ENHANCED DEBUG OPERATIONS ==========
    
    def compile_stacktrace(self, node):
        """Compile enhanced stacktrace"""
        print(f"DEBUG: Compiling stacktrace (max={node.max_frames})")
        
        # Parameters for stacktrace
        self.asm.emit_mov_rdi_imm64(node.max_frames or 0)
        
        flags = 0
        if node.show_locals:
            flags |= 0x01
        if node.show_args:
            flags |= 0x02
        self.asm.emit_mov_rsi_imm64(flags)
        
        # Call stacktrace runtime
        self.asm.emit_call('__debug_stacktrace_ex')
        
        return True
        
    def compile_memory_dump(self, node):
        """Compile enhanced memory dump"""
        print(f"DEBUG: Compiling memory dump")
        
        # Compile address expression
        self.compiler.compile_expression(node.address)
        self.asm.emit_push_rax()
        
        # Size
        if node.size:
            self.compiler.compile_expression(node.size)
        else:
            self.asm.emit_mov_rax_imm64(256)
        self.asm.emit_push_rax()
        
        # Format flags
        format_map = {'hex': 0, 'ascii': 1, 'mixed': 2}
        self.asm.emit_mov_rdx_imm64(format_map.get(node.format, 0))
        
        # Width
        self.asm.emit_mov_rcx_imm64(node.width)
        
        # Pop arguments
        self.asm.emit_pop_rsi()  # Size
        self.asm.emit_pop_rdi()  # Address
        
        # Call memory dump runtime
        self.asm.emit_call('__debug_memory_dump_ex')
        
        return True
        
    def compile_watch(self, node):
        """Compile watchpoint"""
        print(f"DEBUG: Setting watchpoint on {node.variable}")
        
        if node.variable not in self.compiler.variables:
            print(f"ERROR: Unknown variable for watchpoint: {node.variable}")
            return False
            
        offset = self.compiler.variables[node.variable]
        
        # Calculate variable address
        self.asm.emit_mov_rax_rbp()
        self.asm.emit_bytes(0x48, 0x2D)  # SUB RAX, imm32
        self.asm.emit_bytes(*struct.pack('<I', offset))
        self.asm.emit_mov_rdi_rax()
        
        # Watch type
        watch_map = {'read': 1, 'write': 2, 'access': 3}
        self.asm.emit_mov_rsi_imm64(watch_map.get(node.watch_type, 2))
        
        # Variable name for display
        name_offset = self.asm.add_string(node.variable)
        self.asm.emit_load_data_address('rdx', name_offset)
        
        # Call watchpoint setup
        self.asm.emit_call('__debug_set_watchpoint')
        
        # Track watchpoint
        self.watchpoints[node.variable] = node
        
        return True
        
    def compile_locals(self, node):
        """Compile locals display"""
        print("DEBUG: Compiling locals display")
        
        self.asm.emit_mov_rdi_rbp()
        
        flags = 0
        if node.show_types:
            flags |= 0x01
        if node.show_addresses:
            flags |= 0x02
        self.asm.emit_mov_rsi_imm64(flags)
        
        self.asm.emit_call('__debug_show_locals')
        
        return True
        
    def compile_registers(self, node):
        """Compile register dump"""
        print(f"DEBUG: Compiling register dump")
        
        # Save all registers first
        self.emit_save_all_state()
        
        # Register set
        sets = {'all': 0, 'general': 1, 'float': 2}
        self.asm.emit_mov_rdi_imm64(sets.get(node.register_set, 0))
        
        # Format
        formats = {'hex': 0, 'decimal': 1, 'binary': 2}
        self.asm.emit_mov_rsi_imm64(formats.get(node.format, 0))
        
        # Call register dump
        self.asm.emit_mov_rdx_rsp()  # Saved registers location
        self.asm.emit_call('__debug_dump_registers')
        
        # Restore registers
        self.emit_restore_all_state()
        
        return True
        
    def compile_interactive(self, node):
        """Compile interactive debugger entry"""
        print("DEBUG: Entering interactive debugger")
        
        self.emit_save_all_state()
        
        # Set up auto-display if provided
        if node.auto_display:
            for var in node.auto_display:
                if var in self.compiler.variables:
                    offset = self.compiler.variables[var]
                    self.asm.emit_mov_rdi_imm64(offset)
                    name_offset = self.asm.add_string(var)
                    self.asm.emit_load_data_address('rsi', name_offset)
                    self.asm.emit_call('__debug_add_auto_display')
                    
        # Enter interactive mode
        if node.breakpoint_here:
            self.asm.emit_byte(0xCC)  # INT3
            
        self.asm.emit_call('__debug_interactive_loop')
        
        self.emit_restore_all_state()
        
        return True
        
    def compile_breakpoint(self, node):
        """Compile enhanced breakpoint"""
        print(f"DEBUG: Setting breakpoint")
        
        if node.location:
            # Breakpoint at specific location
            if node.location in self.compiler.labels:
                addr = self.compiler.labels[node.location]
                self.asm.emit_mov_rdi_imm64(addr)
            else:
                # Forward reference
                self.compiler.add_fixup(node.location, self.asm.get_current_address())
                self.asm.emit_mov_rdi_imm64(0)
        else:
            # Immediate breakpoint
            self.asm.emit_byte(0xCC)
            return True
            
        # Hit count
        self.asm.emit_mov_rsi_imm64(node.hit_count or 0)
        
        # Temporary flag
        self.asm.emit_mov_rdx_imm64(1 if node.temporary else 0)
        
        self.asm.emit_call('__debug_set_breakpoint')
        
        # Track breakpoint
        self.breakpoints[node.location or len(self.breakpoints)] = node
        
        return True
        
    def compile_profile(self, node):
        """Compile profiling control"""
        print(f"DEBUG: Profile {node.action}")
        
        if node.action == 'start':
            if not self.profile_enabled:
                print("WARNING: Profiling requested but -P flag not set")
                return True
                
            type_map = {'time': 1, 'memory': 2, 'cache': 4}
            self.asm.emit_mov_rdi_imm64(type_map.get(node.profile_type, 1))
            self.asm.emit_call('__debug_profile_start')
            
        elif node.action == 'stop':
            self.asm.emit_call('__debug_profile_stop')
            
        elif node.action == 'report':
            formats = {'text': 0, 'json': 1}
            self.asm.emit_mov_rdi_imm64(formats.get(node.output_format, 0))
            
            if node.threshold:
                threshold_int = int(node.threshold * 100)
                self.asm.emit_mov_rsi_imm64(threshold_int)
            else:
                self.asm.emit_mov_rsi_imm64(0)
                
            self.asm.emit_call('__debug_profile_report')
            
        return True
        
    def compile_leak_check(self, node):
        """Compile memory leak check"""
        print("DEBUG: Compiling leak check")
        
        types = {'summary': 0, 'full': 1}
        self.asm.emit_mov_rdi_imm64(types.get(node.check_type, 0))
        
        flags = 0
        if node.show_backtraces:
            flags |= 0x01
        self.asm.emit_mov_rsi_imm64(flags)
        
        self.asm.emit_call('__debug_check_leaks')
        
        return True
        
    def compile_core_dump(self, node):
        """Compile core dump control"""
        print(f"DEBUG: Core dump {node.action}")
        
        if node.action == 'enable':
            self.asm.emit_mov_rdi_imm64(1)
            self.asm.emit_call('__debug_core_enable')
        elif node.action == 'disable':
            self.asm.emit_mov_rdi_imm64(0)
            self.asm.emit_call('__debug_core_enable')
        elif node.action == 'generate':
            if node.filename:
                filename_offset = self.asm.add_string(node.filename)
                self.asm.emit_load_data_address('rdi', filename_offset)
            else:
                self.asm.emit_xor_rdi_rdi()
            self.asm.emit_mov_rsi_imm64(1 if node.compress else 0)
            self.asm.emit_call('__debug_core_generate')
            
        return True
        
    # ========== HELPER METHODS ==========
    
    def emit_debug_marker(self, label: str, marker_type: str):
        """Emit a debug marker - existing implementation preserved"""
        self.asm.emit_bytes(0x0F, 0x1F, 0x44, 0x00, 0x00)
        
    def emit_assertion_failure(self, message: str):
        """Emit assertion failure - existing implementation preserved"""
        msg = f"ASSERTION FAILED: {message}\n"
        msg_offset = self.asm.add_string(msg)
        
        self.asm.emit_mov_rax_imm64(1)
        self.asm.emit_mov_rdi_imm64(2)
        self.asm.emit_load_data_address('rsi', msg_offset)
        self.asm.emit_mov_rdx_imm64(len(msg))
        self.asm.emit_syscall()
        
        self.asm.emit_mov_rax_imm64(60)
        self.asm.emit_mov_rdi_imm64(1)
        self.asm.emit_syscall()
        
    def emit_save_all_state(self):
        """Save all CPU state"""
        # Save all general purpose registers
        for reg in ['rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rbp', 
                   'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15']:
            self.asm.emit_push(reg)
        # Save flags
        self.asm.emit_bytes(0x9C)  # PUSHFQ
        
    def emit_restore_all_state(self):
        """Restore all CPU state"""
        self.asm.emit_bytes(0x9D)  # POPFQ
        # Restore in reverse order
        for reg in ['r15', 'r14', 'r13', 'r12', 'r11', 'r10', 'r9', 'r8',
                   'rbp', 'rdi', 'rsi', 'rdx', 'rcx', 'rbx', 'rax']:
            self.asm.emit_pop(reg)
            
    def emit_debug_runtime(self):
        """Emit complete debug runtime library"""
        if self.runtime_emitted:
            return
            
        print("DEBUG: Emitting debug runtime library")
        
        # Only emit runtime functions needed for enabled debug level
        if self.debug_level >= 1:
            self._emit_assertion_runtime()
            
        if self.debug_level >= 2:
            self._emit_stacktrace_runtime()
            self._emit_locals_runtime()
            
        if self.debug_level >= 3:
            self._emit_memory_dump_runtime()
            self._emit_watchpoint_runtime()
            self._emit_register_dump_runtime()
            
        if self.debug_level >= 4:
            self._emit_interactive_runtime()
            self._emit_breakpoint_runtime()
            self._emit_core_dump_runtime()
            
        if self.profile_enabled:
            self._emit_profile_runtime()
            
        self.runtime_emitted = True
        
    def _emit_stacktrace_runtime(self):
        """Emit stacktrace runtime function"""
        self.asm.define_label('__debug_stacktrace_ex')
        
        # Print header
        header = "=== STACK TRACE ===\n"
        header_offset = self.asm.add_string(header)
        self.asm.emit_mov_rax_imm64(1)
        self.asm.emit_mov_rdi_imm64(2)
        self.asm.emit_load_data_address('rsi', header_offset)
        self.asm.emit_mov_rdx_imm64(len(header))
        self.asm.emit_syscall()
        
        # Implementation would walk stack frames
        # For now, simplified version
        
        self.asm.emit_ret()
        
    # Additional runtime functions would follow...