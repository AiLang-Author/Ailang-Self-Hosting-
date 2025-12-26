#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
AILANG to x86-64 Compiler - Fixed Main Orchestrator
Coordinates compilation process using modular components with proper integration
"""

import struct
import sys
import os
import traceback
import copy as copy_module
# --- FIX: Import the parser from the ailang_parser package ---
from ailang_parser.compiler import AILANGCompiler
# --- End FIX ---
from ailang_compiler.modules.symbol_table import SymbolTable, SymbolType
from ailang_compiler.modules.semantic_analyzer import SemanticAnalyzer
from ailang_parser.ailang_ast import *

from ailang_compiler.assembler import X64Assembler
from ailang_compiler.elf_generator import ELFGenerator
from ailang_compiler.modules.arithmetic_ops import ArithmeticOps
from ailang_compiler.modules.math_ops import MathOperations
from ailang_compiler.modules.fileio_ops import FileIOOps
from ailang_compiler.modules.control_flow import ControlFlow
from ailang_compiler.modules.memory_manager import MemoryManager
from ailang_compiler.modules.debug_ops import DebugOps
from ailang_compiler.modules.code_generator import CodeGenerator
from ailang_compiler.modules.lowlevel_ops import LowLevelOps
from ailang_compiler.modules.virtual_memory import VirtualMemoryOps
from ailang_compiler.modules.library_inliner import LibraryInliner
from ailang_compiler.modules.hash_ops import HashOps
from ailang_compiler.modules.network_ops import NetworkOps
from ailang_compiler.modules.process_ops import ProcessOps
from ailang_compiler.modules.scheduling_primitives import SchedulingPrimitives
from ailang_compiler.modules.atomic_ops import AtomicOps
from ailang_compiler.modules.user_functions import UserFunctions
from ailang_compiler.modules.string_ops import StringOps
from ailang_compiler.modules.expression_compiler import ExpressionCompiler
from ailang_compiler.modules.memory_pool import MemoryPool
from ailang_compiler.modules.function_dispatch import FunctionDispatch
from ailang_compiler.modules.try_catch import SimplifiedTryCatchCompiler, register_try_catch_in_compiler
from ailang_compiler.modules.message_passing import MessagePassing
from ailang_compiler.modules.syscall_handler import SystemCallHandler
from ailang_compiler.modules.linkage_pool import LinkagePoolManager
from ailang_compiler.modules.memcompare_ops import MemCompareOps


from .scope_manager import ScopeManager

class AILANGToX64Compiler:
    """Main compiler orchestrator for AILANG to x86-64 compilation"""

    def __init__(self, vm_mode="user"):
        """Initialize compiler with proper module initialization order"""
        self.elf = ELFGenerator()
        self.asm = X64Assembler(self.elf)
        self.variables = {}
        self.symbol_table = SymbolTable()      # New symbol table for variable lookups
        self.semantic_analyzer = None          # Will be instantiated in compile()
        self.syscall_handler = SystemCallHandler(self)
        
        # Stack balance tracker
        self.stack_depth = 0
        self.stack_trace = []
        
        self.stack_size = 0
        self.label_counter = 0
        self.max_depth = 0
        self.acronym_table = {}
        self.acronym_map = {} 
        self.file_handles = {}
        self.file_buffer_size = 65536
        self.open_files = {}
        self.vm_mode = vm_mode.lower()
        
        self.ast = None # Will hold the root of the AST
        # Initialize core modules first
        self.function_dispatch = FunctionDispatch(self)
        self.arithmetic = ArithmeticOps(self)
        self.fileio = FileIOOps(self)
        self.math_ops = MathOperations(self)
        self.control_flow = ControlFlow(self)
        self.memory = MemoryManager(self)
        self.linkage_pool_mgr = LinkagePoolManager(self)
        self.parameter_types = {}  # Maps parameter_name -> type_string
        self.pointer_types = {}  # Maps variable_name -> LinkagePool type
        self.linkage_allocations = {}  # Maps return value -> allocated type
        self.memory_pool = MemoryPool(self)
        self.var_types = {} # NEW: Track variable types
        self.current_linkage_base = None # FIX: Initialize the attribute
        self.strings = StringOps(self)
        self.debug_ops = DebugOps(self)
        self.expressions = ExpressionCompiler(self)
        self.codegen = CodeGenerator(self)
        self.lowlevel = LowLevelOps(self)
        self.user_functions = UserFunctions(self)
        self.scope_mgr = ScopeManager(self)
        
        self.try_catch = SimplifiedTryCatchCompiler(self)
        print("DEBUG: Initialized Try/Catch compiler module")
        self.message_passing = MessagePassing(self)
        print("DEBUG: Initialized message passing module")
        
        # Loop model support
        self.subroutines = {}      # name -> label mapping
        self.loops = {}            # loop definitions
        self.actor_states = {}     # actor state storage
        self.task_fixups = []      # forward references to fix
        self.loop_starts = []      # LoopStart blocks to run first
        self.actor_blocks = {}  # Maps actor names to their entry labels
        
        # VM mode handling
        if self.vm_mode == "kernel":
            self.virtual_memory = VirtualMemoryOps(self)
        else:
            from ailang_compiler.modules.usermode_vm_ops import VirtualMemoryOpsUserMode
            self.virtual_memory = VirtualMemoryOpsUserMode(self)
        
        # IMPORTANT: Initialize HashOps BEFORE LibraryInliner
        self.hash_ops = HashOps(self)
        self.scheduler = SchedulingPrimitives(self)
        self.atomics = AtomicOps(self) # <-- ADD THIS LINE
        
        self.memcompare_ops = MemCompareOps(self)
        self.network_ops = NetworkOps(self)
        
        # ADD THIS:
        self.process_ops = ProcessOps(self)
        print("DEBUG: Initialized process operations module")
        
        # Initialize library inliner AFTER hash_ops
        self.library_inliner = LibraryInliner(self)
        
        # Keep track of loaded libraries to prevent circular imports
        self.loaded_libraries = set()

        # Track the current library being compiled for internal name resolution
        self.current_library_prefix = None
        
        self._node_dispatch = {
        'CallIndirect': self.function_dispatch.compile_call_indirect,
        'AddressOf': self.function_dispatch.compile_address_of,
        'Program': lambda n: self.memory.compile_program(n),
        'Library': lambda n: self.compile_library(n),
        'SubRoutine': lambda n: self.compile_subroutine(n),
        'AcronymDefinitions': lambda n: self.compile_acronym_definitions(n),
        'Pool': lambda n: self.memory.compile_pool(n, pre_pass_only=False),
        'LinkagePoolDecl': lambda n: self.linkage_pool_mgr.compile_linkage_pool(n),
        'SubPool': lambda n: self.memory.compile_subpool(n),
        'RecordTypeDefinition': lambda n: self._compile_record_type(n),
        'Loop': lambda n: self._compile_loop_body(n),
        'LoopMain': lambda n: self.compile_loop_main(n),
        'LoopActor': lambda n: (print(f"DISPATCH: LoopActor -> scheduler"), self.scheduler.compile_loop_actor(n))[1],
        'LoopStart': lambda n: self.compile_loop_start(n),
        'LoopShadow': lambda n: self.compile_loop_shadow(n),
        'LoopContinue': lambda n: self.compile_loop_continue(n),
        'LoopSpawn': lambda n: self.scheduler.compile_loop_spawn(n),
        'LoopSend': lambda n: self.compile_loop_send(n),
        'LoopReceive': lambda n: self.compile_loop_receive(n),
        'LoopReply': lambda n: self.compile_loop_reply(n),
        'LoopYield': lambda n: self.scheduler.compile_loop_yield(n), # This is an AST node, not a function call
        'Fork': lambda n: self.control_flow.compile_fork(n),
        'Branch': lambda n: self.control_flow.compile_branch(n),
        'While': lambda n: self.control_flow.compile_while_loop(n),
        'BreakLoop': lambda n: self.control_flow.compile_break(n),
        'ContinueLoop': lambda n: self.control_flow.compile_continue(n),
        'If': lambda n: self.control_flow.compile_if_condition(n),
        'Try': lambda n: self.try_catch.compile_try(n),
        'SendMessage': lambda n: self.message_passing.compile_sendmessage(n),
        'ReceiveMessage': lambda n: self.message_passing.compile_receivemessage(n), # ADDED COMMA
        
        'DebugBlock': lambda n: self.debug_ops.compile_operation(n) if hasattr(self, 'debug_ops') else None,
        'DebugAssert': lambda n: self.debug_ops.compile_operation(n) if hasattr(self, 'debug_ops') else None,
        'Assignment': lambda n: self.memory.compile_assignment(n),
        'PrintMessage': lambda n: self.strings.compile_print_message(n),
        'AllocateLinkage': lambda n: self.linkage_pool_mgr.compile_allocate_linkage(n),
        'RunTask': lambda n: self._compile_run_task_dispatch(n),
        'FunctionCall': lambda n: self._compile_function_call_dispatch(n),
        
        # === User Functions Module ====
        
        'Function': lambda n: self.user_functions.compile_function_definition(n),
        'FunctionDefinition': lambda n: self.user_functions.compile_function_definition(n),
        'ReturnValue': lambda n: self.user_functions.compile_return(n.value if hasattr(n, 'value') else None),
        'TryBlock': lambda n: self.try_catch.compile_try(n),
        
        # Memory Comparison Operations
        'MemCompare': lambda n: self.memcompare_ops.compile_memcompare([n.addr1, n.addr2, n.length]),
        'MemChr': lambda n: self.memcompare_ops.compile_memchr([n.addr, n.byte_value, n.length]),
        'MemCopy': lambda n: self.memcompare_ops.compile_memcopy([n.dest, n.src, n.length]),
        'MemFind': lambda n: self.memcompare_ops.compile_memfind([n.haystack, n.haystack_len, n.needle, n.needle_len]),
        }

    def compile_assignment(self, node):
        """Compile assignment statement"""
        print(f"DEBUG: compile_assignment called for target: {node.target}")
        target = node.target
        
        # Get target name first
        if isinstance(target, str):
            target_name = target
        elif hasattr(target, 'name'):
            target_name = target.name
        else:
            target_name = str(target)
        
        # Check if value is another typed pointer (for propagation)
        if isinstance(node.value, Identifier):
            source_name = node.value.name
            source_type = self.get_pointer_type(source_name) if hasattr(self, 'get_pointer_type') else None
            if source_type:
                self.pointer_types[target_name] = source_type
                print(f"DEBUG: Propagated type {source_type} from {source_name} to {target_name}")

        # Compile the value expression
        self.compile_expression(node.value)
        
        # Add debug to see if pending_type exists
        print(f"DEBUG: After compile_expression, checking pending_type...")
        if hasattr(self, 'pending_type') and self.pending_type:
            print(f"DEBUG: pending_type exists: {self.pending_type}")
            if self.pending_type:
                if not hasattr(self, 'pointer_types'):
                    self.pointer_types = {}
                self.pointer_types[target_name] = self.pending_type
                print(f"DEBUG: Tracked pointer type: {target_name} -> {self.pending_type}")
                self.pending_type = None
            else:
                print(f"DEBUG: pending_type is None or empty")
        else:
            print(f"DEBUG: No pending_type attribute found or it is empty")
        
        # Delegate the rest of the assignment logic to the memory manager
        # which handles the actual storage of the value in RAX.
        self.memory.compile_assignment(node)

    def get_pointer_type(self, var_name):
        """Get the LinkagePool type associated with a variable"""
        if hasattr(self, 'pointer_types') and var_name in self.pointer_types:
            return self.pointer_types[var_name]
        
        if hasattr(self, 'parameter_types') and var_name in self.parameter_types:
            param_type = self.parameter_types[var_name]
            if param_type and param_type.startswith('LinkagePool.'):
                return param_type
        
        return None

    def track_push(self, context=""):
        '''Track a PUSH operation'''
        self.stack_depth += 1
        position = len(self.asm.code) if hasattr(self, 'asm') else 0
        self.stack_trace.append({
            'op': 'PUSH',
            'depth': self.stack_depth,
            'position': position,
            'context': context
        })
        print(f"STACK: PUSH at {position} | depth={self.stack_depth} | {context}")
    
    def track_pop(self, context=""):
        '''Track a POP operation'''
        self.stack_depth -= 1
        position = len(self.asm.code) if hasattr(self, 'asm') else 0
        self.stack_trace.append({
            'op': 'POP',
            'depth': self.stack_depth,
            'position': position,
            'context': context
        })
        print(f"STACK: POP  at {position} | depth={self.stack_depth} | {context}")
        
        if self.stack_depth < 0:
            print(f"ERROR: Stack underflow! Depth={self.stack_depth}")
            self.print_stack_trace()
    
    def print_stack_trace(self):
        '''Print the stack operation trace'''
        print("\n=== STACK TRACE ===")
        for i, op in enumerate(self.stack_trace[-20:]):  # Last 20 operations
            print(f"  {i}: {op['op']:4s} pos={op['position']:5d} depth={op['depth']:3d} | {op['context']}")
        print("===================\n")
    
    def check_stack_balance(self, expected_depth, context=""):
        '''Verify stack is at expected depth'''
        if self.stack_depth != expected_depth:
            print(f"WARNING: Stack imbalance at {context}")
            print(f"  Expected depth: {expected_depth}, Actual depth: {self.stack_depth}")
            self.print_stack_trace()

    # --- NEW: Function to handle library compilation ---
    def compile_library(self, library_node):
        """Finds, parses, and compiles an AILANG library with 2-pass support."""
        original_prefix = self.current_library_prefix
        try:
            library_path_parts = library_node.name.split('.')
            
            if library_node.name in self.loaded_libraries:
                return

            # Try current directory first, then Librarys subdirectory
            file_name = f"Library.{library_path_parts[-1]}.ailang"
            library_file_path = file_name
            
            if not os.path.exists(library_file_path):
                search_path_parts = ['Librarys'] + library_path_parts[:-1] + [file_name]
                library_file_path = os.path.join(*search_path_parts)

            if not os.path.exists(library_file_path):
                raise FileNotFoundError(f"Library file not found: {library_file_path}")

            print(f"  Loading library: {library_file_path}")

            with open(library_file_path, 'r') as f:
                library_source = f.read()

            parser = AILANGCompiler()
            library_ast = parser.compile(library_source)

            self.loaded_libraries.add(library_node.name)

            # Extract library prefix (e.g., "RESP" from "Library.RESP")
            lib_prefix = library_path_parts[-1]
            self.current_library_prefix = lib_prefix
            
            # PASS 1: Register all library symbols (functions, pools, etc.) BEFORE compiling any
            print(f"  Pass 1: Discovering symbols in {lib_prefix} library...")
            for decl in library_ast.declarations:
                node_type = type(decl).__name__
                if node_type in ('Function', 'FunctionDefinition'):
                    # Fix function name to include library prefix
                    if '.' in decl.name:
                        # Already has dots - parse it properly
                        parts = decl.name.split('.')
                        if parts[0] == lib_prefix:
                            # Already prefixed correctly
                            full_name = decl.name
                        else:
                            # Add library prefix
                            full_name = f"{lib_prefix}.{decl.name}"
                    else:
                        # Simple name - add library prefix
                        full_name = f"{lib_prefix}.{decl.name}"
                    
                    # Update the node's name
                    original_name = decl.name
                    decl.name = full_name
                    
                    # Register with user_functions module
                    self.user_functions.register_function(decl)
                    
                    print(f"    Registered function: {full_name}")
                elif node_type == 'Pool':
                    # Pre-pass to discover pool variables so they exist before compilation
                    print(f"    Discovering pool: {decl.name}")
                    # This is the crucial step that was missing.
                    self.memory.compile_pool(decl, pre_pass_only=True)

            # PASS 2: Now compile all declarations
            print(f"  Pass 2: Compiling {lib_prefix} library...")
            for decl in library_ast.declarations:
                self.compile_node(decl)

        except FileNotFoundError as e:
            print(f"ERROR: Could not import library '{library_node.name}'. {e}")
            raise
        except Exception as e:
            print(f"ERROR: Failed during compilation of library '{library_node.name}': {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            # Restore the previous library context
            self.current_library_prefix = original_prefix

    def get_label(self):
        # ... (keep this method as is) ...
        label = f"L{self.label_counter}"
        self.label_counter += 1
        return label

    def compile_node(self, node):
        """Dispatch node compilation to appropriate module"""
        
        node_type = type(node).__name__
            
            # Handle dotted actor names like "LoopActor.TestActor"
        if node_type == 'FunctionCall' and hasattr(node, 'function'):  # ADD THIS BLOCK
            if node.function.startswith('LoopActor.'):
                print(f"DEBUG: Found LoopActor.{node.function[10:]}")
                # Create a proper actor node
                class ActorNode:
                    def __init__(self, name, body):
                        self.name = name
                        self.body = body
                actor = ActorNode(node.function[10:], node.arguments if hasattr(node, 'arguments') else [])
                return self.scheduler.compile_loop_actor(actor)
            
        if node_type in self._node_dispatch:
            return self._node_dispatch[node_type](node)

    def _compile_loop_body(self, node):
        """Compile Loop body statements"""
        for stmt in node.body:
            self.compile_node(stmt)
            
     

    def _compile_record_type(self, node):
        """Register record type definition"""
        if not hasattr(self, "record_types"):
            self.record_types = {}
        self.record_types[node.name] = node.record_type

    def _compile_run_task_dispatch(self, node):
        """Handle RunTask with proper routing"""
        task_name = node.task_name if hasattr(node, 'task_name') else None
        
        if task_name and '.' not in task_name:
            # Simple name - local subroutine
            self.compile_run_task(node)
        elif hasattr(self, "library_inliner"):
            # Dotted name - library call
            self.library_inliner.compile_runtask(node)
        else:
            print(f"ERROR: Cannot handle task: {task_name}")
            self.asm.emit_mov_rax_imm64(0)
            
            
    def _compile_function_call_dispatch(self, node):
        """Handle FunctionCall with special cases including ReturnValue"""
        if hasattr(node, "function"):
            if node.function == "RunTask":
                # Legacy RunTask as function call
                if hasattr(node, "task_name") and hasattr(node, "arguments"):
                    if hasattr(self, "library_inliner"):
                        self.library_inliner.compile_runtask(node)
                    else:
                        print("WARNING: No library_inliner available")
                        self.asm.emit_mov_rax_imm64(0)
            elif node.function == "ReturnValue":
                # Handle ReturnValue as a function call
                value = node.arguments[0] if node.arguments else None
                self.user_functions.compile_return(value)
            elif node.function.startswith("DebugPerf."):
                # Handle DebugPerf functions
                if hasattr(self, 'debug_ops'):
                    self.debug_ops.compile_operation(node)
                else:
                    print(f"WARNING: Debug ops not available for {node.function}")
                    self.asm.emit_mov_rax_imm64(0)
            else:
                # Regular function call
                self.compile_function_call(node)
        else:
            # Regular function call
            self.compile_function_call(node)
 
    def compile_comparison(self, node):
        """Delegate comparison operations to arithmetic module"""
        return self.arithmetic.compile_comparison(node)
            

    def compile_function_call(self, node):
        """Compile function call with user-defined functions and enhanced module support."""
        try:
            original_function_name = node.function
            print(f"DEBUG compile_function_call: ENTRY with function='{node.function}'")
            # print(f"DEBUG: Compiling function call: {node.function}")
            
            # === ALIAS RESOLUTION FIX ===
            # Check if this function name contains an aliased prefix (e.g., NS64KZ1X_XArray.XCreate)
            if hasattr(self, 'alias_mappings') and self.alias_mappings:
                original_name = node.function
                # The aliases are like "NS64KZ1X_XArrays" -> "XArrays"
                for alias, original in self.alias_mappings.items():
                    # Check if the function starts with an alias prefix
                    if node.function.startswith(alias):
                        # Replace the entire alias with the original
                        # e.g., "NS64KZ1X_XArray.XCreate" -> "XArray.XCreate"
                        node.function = node.function.replace(alias, original, 1)
                        print(f"DEBUG: Resolved alias {original_name} -> {node.function}")
                        break
            # === END ALIAS RESOLUTION FIX ===
            
            # === SYSTEMCALL HANDLER ===
            if node.function == "SystemCall":
                return self.syscall_handler.compile_system_call(node)

            # === EARLY USER FUNCTION CHECK ===
            # Check user functions FIRST before trying library resolution
            # This handles direct calls like ESCAL056_0000_MAINLINE_CONTROL(...)
            if hasattr(self, 'user_functions') and hasattr(self.user_functions, 'user_functions'):
                if node.function in self.user_functions.user_functions:
                    print(f"DEBUG: Found user function (early check): {node.function}")
                    if self.user_functions.compile_function_call(node):
                        return
            # === END EARLY CHECK ===

            # --- Context-aware library function resolution ---
            # If compiling inside a library, try to resolve the function with the library's prefix.
            # This handles calls between functions within the same library (e.g., Trig.Sin calling Trig.NormalizeDegrees).
            if self.current_library_prefix:
                prefixed_name = f"{self.current_library_prefix}.{node.function}"
                if hasattr(self.user_functions, 'is_function_registered') and self.user_functions.is_function_registered(prefixed_name):
                    print(f"DEBUG: Library context '{self.current_library_prefix}' found. Resolving '{node.function}' to '{prefixed_name}'")
                    # Create a temporary node with the corrected name and compile it.
                    node_copy = copy_module.copy(node)
                    node_copy.function = prefixed_name
                    if self.user_functions.compile_function_call(node_copy):
                        return

            # === Check if this is a registered library function first ===
            # This handles forward references from the 2-pass registration
            if hasattr(self.user_functions, 'is_function_registered'):
                # Try the name as-is first
                if self.user_functions.is_function_registered(node.function):
                    print(f"DEBUG: Found registered function: {node.function}")
                    if self.user_functions.compile_function_call(node):
                        return
                
                # --- Search through imported libraries ---
                # If the name wasn't found, try prefixing it with the names of imported libraries.
                for lib_name in self.loaded_libraries:
                    # lib_name is like "Library.XArrays"
                    lib_prefix = lib_name.split('.')[-1]
                    prefixed_name = f"{lib_prefix}.{node.function}"
                    if self.user_functions.is_function_registered(prefixed_name):
                        print(f"DEBUG: Resolved '{node.function}' to '{prefixed_name}' via imported library '{lib_name}'")
                        node_copy = copy_module.copy(node)
                        node_copy.function = prefixed_name
                        if self.user_functions.compile_function_call(node_copy):
                            return
            
            # Extract base function name (handles both "Category.Name" and "Name")
            base_name = node.function
            if '.' in node.function:
                parts = node.function.split('.')
                
                # === Check for library function patterns (e.g., RESP.ParseInteger) ===
                if len(parts) == 2:
                    lib_name, func_name = parts
                    
                    # Try as registered library function
                    if hasattr(self.user_functions, 'is_function_registered'):
                        # Try full name first
                        if self.user_functions.is_function_registered(node.function):
                            print(f"DEBUG: Found library function: {node.function}")
                            if self.user_functions.compile_function_call(node):
                                return
                        
                        # Try with "Function." prefix removed if present
                        if lib_name == "Function" and self.user_functions.is_function_registered(func_name):
                            node_copy = copy_module.copy(node)
                            node_copy.function = func_name
                            if self.user_functions.compile_function_call(node_copy):
                                return
                
                # Check full name first for user functions (existing code)
                if node.function in self.user_functions.user_functions:
                    if self.user_functions.compile_function_call(node):
                        return
                
                # Try without "Function." prefix if present (existing code)
                if node.function.startswith("Function."):
                    clean_name = node.function[9:]
                    if clean_name in self.user_functions.user_functions:
                        node_copy = copy_module.copy(node)
                        node_copy.function = clean_name
                        if self.user_functions.compile_function_call(node_copy):
                            return
                
                # Check for pool operations (existing code)
                if len(parts) == 2 and parts[1] in ['Init', 'Alloc', 'Free', 'Reset', 'Status']:
                    if hasattr(self, 'memory_pool') and self.memory_pool.compile_operation(node):
                        return
                
                # Try base name for primitives
                base_name = node.function.split('.')[-1]
            
            # Check user functions with base name (existing code)
            if base_name in self.user_functions.user_functions:
                node_copy = copy_module.copy(node)
                node_copy.function = base_name
                if self.user_functions.compile_function_call(node_copy):
                    return

            # Check for pooled string operations (existing code)
            if node.function == 'StringConcatPooled':
                if hasattr(self, 'strings') and self.strings.compile_operation(node):
                    return

            # Dispatch to modules (existing code)
            dispatch_modules = [
                self.process_ops,        # ADD THIS FIRST - syscalls have priority
                self.function_dispatch,  # Handle CallIndirect, AddressOf first
                self.math_ops,          # Try math operations next
                self.arithmetic,        # Then basic arithmetic.
                self.fileio, self.strings,
                self.lowlevel, self.hash_ops, self.network_ops,
                self.virtual_memory, self.atomics,
            ]

            print(f"DEBUG: Before module dispatch, function still='{node.function}'")

            # Try with original name first
            for module in dispatch_modules:
                print(f"DEBUG: Checking module {module.__class__.__name__}")
                print(f"DEBUG: node.function BEFORE module = '{node.function}'")
                
                if hasattr(module, 'compile_operation'):
                    result = module.compile_operation(node)
                
                print(f"DEBUG: node.function AFTER module = '{node.function}'")
                
                if node.function != original_function_name:
                    print(f"ERROR: Module {module.__class__.__name__} CORRUPTED name!")
                    print(f"  Original: '{original_function_name}'")
                    print(f"  Corrupted to: '{node.function}'")
                    # Fix it
                    node.function = original_function_name
                
                if hasattr(module, 'compile_operation'):
                    if result:
                        return
                else:
                    print(f"DEBUG: {module_name} has no compile_operation method")

            # === PROTECTION AGAINST NAME CORRUPTION ===
            original_function_name = node.function
            
            # Dispatch to modules (existing code)
            for module in dispatch_modules:
                node.function = original_function_name # Restore name before each module attempt
                if hasattr(module, 'compile_operation'):
                    result = module.compile_operation(node)
                    if result:
                        return
                else:
                    print(f"DEBUG: {module_name} has no compile_operation method")

            # If dotted name failed, try with base name
            if '.' in node.function:
                node_copy = copy_module.copy(node)
                node_copy.function = base_name
                print(f"DEBUG: Trying base name {base_name}")
                node.function = original_function_name # Restore name before each module attempt
                for module in dispatch_modules:
                    module_name = module.__class__.__name__ if hasattr(module, '__class__') else str(module)
                    print(f"DEBUG: Trying module {module_name} with base name")
                    if hasattr(module, 'compile_operation'):
                        result = module.compile_operation(node_copy)
                        print(f"DEBUG: {module_name}.compile_operation returned {result}")
                        if result:
                            return

            # Special cases (existing code)
            if base_name == 'PrintNumber':
                return self.strings.compile_print_number(node)
            # LinkagePool operations         
            if base_name in ['AllocateLinkage', 'FreeLinkage']:
                linkage_ops = {
                    'AllocateLinkage': self.linkage_pool_mgr.compile_allocate_linkage,
                    'FreeLinkage': self.linkage_pool_mgr.compile_free_linkage,
                }
                if base_name in linkage_ops:
                    return linkage_ops[base_name](node)
            # Memory pool operations (existing code)
            if base_name in ['PoolResize', 'PoolMove', 'PoolCompact',
                            'PoolAllocate', 'PoolFree', 'PoolGetSize',
                            'ArrayCreate', 'ArraySet', 'ArrayGet', 'ArrayLength','ArrayDestroy']:
                memory_ops = {
                    'PoolResize': self.memory.compile_pool_resize,
                    'PoolMove': self.memory.compile_pool_move,
                    'PoolCompact': self.memory.compile_pool_compact,
                    'PoolAllocate': self.memory.compile_pool_allocation,
                    'PoolFree': self.memory.compile_pool_free,
                    'PoolGetSize': self.memory.compile_pool_get_size,
                    'ArrayCreate': self.memory.compile_array_create,
                    'ArraySet': self.memory.compile_array_set,
                    'ArrayGet': self.memory.compile_array_get,
                    'ArrayLength': self.memory.compile_array_length,
                    'ArrayDestroy': self.memory.compile_array_destroy, 
                }
                if base_name in memory_ops:
                    return memory_ops[base_name](node)

            # Scheduling primitives (existing code)
            if self._is_scheduler_primitive(base_name):
                return self._compile_scheduler_primitive(node)

            # Exit (existing code) - bare Exit with no arguments
            # ProcessExit is handled by process_ops module and takes an argument
            if base_name == 'Exit' and (not hasattr(node, 'arguments') or len(node.arguments) == 0):
                # Legacy Exit() with no status code - exits with 0
                self.asm.emit_mov_rax_imm64(60)
                self.asm.emit_xor_edi_edi()
                self.asm.emit_syscall()
                return
            
            if base_name == 'ProcessFork':
                return self.process_ops.compile_operation(node)

            # Unknown function
            node.function = original_function_name # Restore name before error
            raise ValueError(f"Unknown function: {node.function}")
            
        except Exception as e:
            print(f"DEBUG compile_function_call: EXCEPTION - {e}")
            print(f"  Final node.function = '{node.function}'")
            print(f"ERROR: compile_function_call failed: {e}")
            traceback.print_exc()
            raise
    

    def compile_subroutine(self, node):
        """Compile SubRoutine as callable code"""
        print(f"DEBUG: Compiling SubRoutine.{node.name}")
        
        # Track entry stack state
        entry_depth = self.stack_depth
        print(f"STACK: SubRoutine.{node.name} entry, depth={entry_depth}")
        
        # Check if already compiled
        if node.name in self.subroutines:
            print(f"DEBUG: SubRoutine.{node.name} already compiled, skipping")
            return True
        
        # Create label for the subroutine
        label = self.asm.create_label()
        self.subroutines[node.name] = label
        
        # Jump over subroutine definition
        skip_label = self.asm.create_label()
        self.asm.emit_jump_to_label(skip_label, "JMP")
        
        # Mark subroutine start
        self.asm.mark_label(label)
        
        # === FIX: Save ALL callee-saved registers (AMD64 ABI: RBX, R12-R15) ===
        self.asm.emit_push_rbx()
        self.track_push(f"SubRoutine.{node.name} save RBX")
        self.asm.emit_push_r12()
        self.track_push(f"SubRoutine.{node.name} save R12")
        self.asm.emit_push_r13()
        self.track_push(f"SubRoutine.{node.name} save R13")
        self.asm.emit_push_r14()
        self.track_push(f"SubRoutine.{node.name} save R14")
        # === END FIX ===
        
        # Create return label for this subroutine
        return_label = self.asm.create_label()
        print(f"DEBUG: Created return label '{return_label}' for SubRoutine.{node.name}")
        
        # Set context for ReturnValue
        self.compiling_subroutine = True
        self.subroutine_return_label = return_label
        
        # Compile body
        for stmt in node.body:
            self.compile_node(stmt)
        
        # Mark return point
        self.asm.mark_label(return_label)
        
        # Check stack balance before return (now +5 for 5 saved registers)
        self.check_stack_balance(entry_depth + 4, f"SubRoutine.{node.name} before return (should have +4 for saved registers)")
        
        # Clear context
        self.compiling_subroutine = False
        self.subroutine_return_label = None
        
        # === FIX: Restore ALL callee-saved registers in REVERSE order ===
        self.track_pop(f"SubRoutine.{node.name} restore R14")
        self.asm.emit_pop_r14()
        self.track_pop(f"SubRoutine.{node.name} restore R13")
        self.asm.emit_pop_r13()
        self.track_pop(f"SubRoutine.{node.name} restore R12")
        self.asm.emit_pop_r12()
        self.track_pop(f"SubRoutine.{node.name} restore RBX")
        self.asm.emit_pop_rbx()
        # === END FIX ===
        
        self.asm.emit_ret()
        
        print(f"STACK: SubRoutine.{node.name} exit, depth should be {entry_depth}")
        
        # Mark skip label (continue main execution)
        self.asm.mark_label(skip_label)
        return True

    def compile_run_task(self, node):
        """Compile RunTask - call to subroutine"""
        task_name = node.task_name
        print(f"DEBUG: Compiling RunTask.{task_name}")
        
        if task_name in self.subroutines:
            # Known subroutine - emit call with known offset
            label = self.subroutines[task_name]
            current_pos = len(self.asm.code)
            self.asm.emit_bytes(0xE8)  # CALL opcode
            
            if label in self.asm.labels:
                # Label position is known
                target_pos = self.asm.labels[label]
                offset = target_pos - (current_pos + 5)
                self.asm.emit_bytes(*struct.pack('<i', offset))
            else:
                # Label exists but position unknown yet
                self.asm.emit_bytes(0x00, 0x00, 0x00, 0x00)
                self.task_fixups.append((task_name, current_pos))
        else:
            # Forward reference - will be resolved later
            current_pos = len(self.asm.code)
            self.asm.emit_bytes(0xE8, 0x00, 0x00, 0x00, 0x00)
            self.task_fixups.append((task_name, current_pos))
        
        return True
            
    def compile_loop_main(self, node):
        """Compile LoopMain - main event loop"""
        print(f"DEBUG: Compiling LoopMain.{node.name}")
        
        # LoopMain runs inline in main execution
        for stmt in node.body:
            self.compile_node(stmt)
            
    
        
    def compile_loop_start(self, node):
        """Compile LoopStart - initialization"""
        print(f"DEBUG: Compiling LoopStart.{node.name}")
        
        # LoopStart runs before main
        # Store for later execution
        if not hasattr(self, 'loop_starts'):
            self.loop_starts = []
        self.loop_starts.append(node)
        
    def compile_loop_shadow(self, node):
        """Compile LoopShadow - background loop"""
        print(f"DEBUG: Compiling LoopShadow.{node.name}")
        
        # Similar to LoopActor but for background tasks
        self.loops[f"LoopShadow.{node.name}"] = node
        
        # Skip in main flow
        skip_label = self.asm.create_label()
        self.asm.emit_jump_to_label(skip_label, "JMP")
        
        shadow_label = self.asm.create_label()
        self.loops[f"LoopShadow.{node.name}.label"] = shadow_label
        self.asm.mark_label(shadow_label)
        
        for stmt in node.body:
            self.compile_node(stmt)
            
        self.asm.emit_ret()
        self.asm.mark_label(skip_label)
        
    def compile_loop_continue(self, node):
        """Compile LoopContinue - infinite loop with yield points"""
        print("DEBUG: Compiling LoopContinue")
        
        loop_start = self.asm.create_label()
        self.asm.mark_label(loop_start)
        
        for stmt in node.body:
            self.compile_node(stmt)
            
        # Jump back to start
        self.asm.emit_jump_to_label(loop_start, "JMP")
        
    def compile_loop_yield(self, node):
        """Compile LoopYield - cooperative yield"""
        print("DEBUG: Compiling LoopYield")
        
        if node.expression:
            # Yield with delay
            self.compile_expression(node.expression)
            # For now, just a NOP - later: actual scheduling
            self.asm.emit_nop()
        else:
            # Simple yield
            self.asm.emit_nop()
            
    def compile_loop_send(self, node):
        """Write message to target actor's mailbox"""
        print("DEBUG: Compiling LoopSend")
        
        # Get target actor handle
        if len(node.arguments) >= 2:
            # First arg: target handle
            self.compile_expression(node.arguments[0])
            self.asm.emit_push_rax()  # Save target
            
            # Second arg: message value
            self.compile_expression(node.arguments[1])
            
            # Calculate mailbox address: ACB_base + (handle * 128) + 120
            # Using offset 120 in the ACB for mailbox (last 8 bytes)
            self.asm.emit_mov_rbx_rax()  # Message in RBX
            self.asm.emit_pop_rax()      # Target handle in RAX
            
            # Multiply handle by 128 (ACB size)
            self.asm.emit_bytes(0x48, 0xC1, 0xE0, 0x07)  # SHL RAX, 7
            
            # Add ACB base address
            if 'system_acb_table' in self.variables:
                offset = self.variables['system_acb_table']
                self.asm.emit_bytes(0x48, 0x03, 0x85)  # ADD RAX, [RBP-offset]
                self.asm.emit_bytes(*struct.pack('<i', -offset))
            
            # Add mailbox offset (120)
            self.asm.emit_bytes(0x48, 0x83, 0xC0, 0x78)  # ADD RAX, 120
            
            # Store message at mailbox address
            self.asm.emit_bytes(0x48, 0x89, 0x18)  # MOV [RAX], RBX
            
            print("DEBUG: Message sent to mailbox")
        
        return True
    def compile_loop_receive(self, node):
        """Read message from current actor's mailbox"""
        print("DEBUG: Compiling LoopReceive")
        
        # Get current actor handle
        if 'system_current_actor' in self.variables:
            offset = self.variables['system_current_actor']
            self.asm.emit_bytes(0x48, 0x8B, 0x85)  # MOV RAX, [RBP-offset]
            self.asm.emit_bytes(*struct.pack('<i', -offset))
            
            # Calculate mailbox address
            self.asm.emit_bytes(0x48, 0xC1, 0xE0, 0x07)  # SHL RAX, 7
            
            # Add ACB base
            if 'system_acb_table' in self.variables:
                acb_offset = self.variables['system_acb_table']
                self.asm.emit_bytes(0x48, 0x03, 0x85)  # ADD RAX, [RBP-offset]
                self.asm.emit_bytes(*struct.pack('<i', -acb_offset))
            
            # Add mailbox offset
            self.asm.emit_bytes(0x48, 0x83, 0xC0, 0x78)  # ADD RAX, 120
            
            # Load message from mailbox
            self.asm.emit_bytes(0x48, 0x8B, 0x00)  # MOV RAX, [RAX]
            
            print("DEBUG: Message received from mailbox")
        else:
            # No current actor, return 0
            self.asm.emit_mov_rax_imm64(0)
        
        return True
    def compile_loop_reply(self, node):
        """Compile LoopReply - reply to sender"""
        print("DEBUG: Compiling LoopReply")
        
        # Store reply for sender
        self.compile_expression(node.message)
        # Real implementation needs sender tracking
        
    def fixup_forward_references(self):
        """Fix forward references to subroutines"""
        
        print(f"DEBUG: Fixing {len(self.task_fixups)} forward references")
        print(f"DEBUG: Available subroutines: {self.subroutines}")
        if hasattr(self.asm, 'jump_manager') and hasattr(self.asm.jump_manager, 'labels'):
            print(f"DEBUG: Available labels in asm: {self.asm.jump_manager.labels}")
        else:
            print("DEBUG: No labels available in asm")
        
        for item in self.task_fixups:
            if len(item) == 2:
                task_name, call_pos = item
            else:
                task_name, call_pos, _ = item
                
            print(f"DEBUG: Fixing call to {task_name} at position {call_pos}")
            
            if task_name not in self.subroutines:
                raise ValueError(f"Undefined subroutine: {task_name}")
                
            label = self.subroutines[task_name]
            print(f"DEBUG: Subroutine {task_name} has label {label}")
            
            # Get the actual position of the subroutine
            if label in self.asm.labels:
                target_pos = self.asm.labels[label]
                
                # Calculate relative offset for CALL
                # CALL uses offset from instruction end (call_pos + 5)
                offset = target_pos - (call_pos + 5)
                
                # Patch the CALL instruction with the offset
                offset_bytes = struct.pack('<i', offset)  # Little-endian 32-bit
                for i in range(4):
                    self.asm.code[call_pos + 1 + i] = offset_bytes[i]
                
                print(f"DEBUG: Fixed call to {task_name}: offset={offset} ({hex(offset)})")
            else:
                print(f"DEBUG: ERROR - Label {label} not found in asm.labels!")
        
        # Fix user function forward references
        if hasattr(self, 'user_function_fixups'):
            print(f"DEBUG: Fixing {len(self.user_function_fixups)} user function references")
            for func_name, call_pos in self.user_function_fixups:
                print(f"DEBUG: Fixing call to user function {func_name} at position {call_pos}")
                
                if func_name in self.user_functions.user_functions:
                    func_info = self.user_functions.user_functions[func_name]
                    label = func_info['label']
                    
                    if label in self.asm.labels:
                        target_pos = self.asm.labels[label]
                        offset = target_pos - (call_pos + 5)
                        
                        # Patch the CALL instruction
                        offset_bytes = struct.pack('<i', offset)
                        for i in range(4):
                            self.asm.code[call_pos + 1 + i] = offset_bytes[i]
                        
                        print(f"DEBUG: Fixed call to {func_name}: offset={offset}")
                    else:
                        print(f"ERROR: Label {label} not found for function {func_name}")
                else:
                    print(f"ERROR: User function {func_name} not found")
    
    def _is_scheduler_primitive(self, func_name):
        """Check if a function is a scheduling primitive."""
        primitives = [
            'LoopYield', 'LoopSpawn', 'LoopJoin', 'LoopGetState',
            'LoopSetPriority', 'LoopGetCurrent', 'LoopSuspend', 'LoopResume'
        ]
        return func_name in primitives

    def _compile_scheduler_primitive(self, node):
        """Route to the correct scheduling primitive handler."""
        # Converts CamelCase (LoopYield) to snake_case (compile_loopyield)
        handler_name = "compile_" + ''.join(['_' + i.lower() if i.isupper() else i for i in node.function]).lstrip('_')
        handler = getattr(self.scheduler, handler_name, None)
        if handler:
            return handler(node)
        else:
            raise NotImplementedError(f"Scheduling primitive handler '{handler_name}' not found in scheduler module.")        

       
    def compile_expression(self, expr):
        return self.expressions.compile_expression(expr)
    
    def resolve_acronym_identifier(self, identifier_name):
        return self.memory.resolve_acronym_identifier(identifier_name)
    
    def resolve_acronym(self, name):
        """
        New simple acronym system - direct name mapping.
        Returns mapped name if exists, otherwise returns original.
        Backwards compatible.
        """
        if name in self.acronym_map:
            return self.acronym_map[name]
        return name
    
    def compile_acronym_definitions(self, node):
        """
        Compile AcronymDefinitions - populates the new simple acronym_map.
        Also calls the old system for backwards compatibility.
        """
        print(f"DEBUG: Processing AcronymDefinitions with {len(node.mappings)} mappings")
        
        # NEW system - simple direct mapping
        for acronym, full_name in node.mappings.items():
            self.acronym_map[acronym] = full_name
            print(f"DEBUG: New acronym map: {acronym} -> {full_name}")
        
        # OLD system - for backwards compatibility
        self.memory.compile_acronym_definitions(node)
        
        return True
    
    def compile(self, ast, debug_options=None) -> bytes:
        """Compile AST to executable with 2-pass function registration"""
        print("\n=== COMPILATION STARTING ===")
        
        # Configure debug options - auto-detect -P and -D flags from command line
        if debug_options is None:
            import sys
            debug_options = {}
            # Check for profiling flag
            if '-P' in sys.argv or '--profile' in sys.argv:
                debug_options['profile'] = True
                print("🔧 DEBUG: Auto-detected -P flag, enabling profiling")
            # Check for debug level flags
            if '-D4' in sys.argv:
                debug_options['debug_level'] = 4
                debug_options['debug'] = True
                print("🔧 DEBUG: Auto-detected -D4 flag")
            elif '-D3' in sys.argv:
                debug_options['debug_level'] = 3
                debug_options['debug'] = True
                print("🔧 DEBUG: Auto-detected -D3 flag")
            elif '-D2' in sys.argv:
                debug_options['debug_level'] = 2
                debug_options['debug'] = True
                print("🔧 DEBUG: Auto-detected -D2 flag")
            elif '-D1' in sys.argv:
                debug_options['debug_level'] = 1
                debug_options['debug'] = True
                print("🔧 DEBUG: Auto-detected -D1 flag")
        
        # CRITICAL: Configure debug_ops with the detected options
        self.debug_ops.set_debug_options(debug_options)
        
        # Store the AST so other modules can reference it (e.g., for global lookups)
        self.ast = ast

        
        # Run semantic analysis to populate symbol table
        print("Phase 1: Running semantic analysis...")
        self.semantic_analyzer = SemanticAnalyzer(self, self.symbol_table)
        if not self.semantic_analyzer.analyze(ast):
            raise ValueError("Semantic analysis failed - check errors above")
        
        print(f"✓ Symbol table populated with {len(self.symbol_table.scopes)} scopes")
        print(f"✓ Total symbols: {sum(len(s) for s in self.symbol_table.scopes.values())}\n")

       # PASS 1: Register ALL global symbols (functions, variables, pools)
        print("Phase 0: Registering all global symbols...")

        for decl in ast.declarations:
            # This first pass is for discovery and registration only
            node_type = type(decl).__name__
            if node_type in ('Function', 'FunctionDefinition'):
                self.user_functions.register_function(decl)
            elif node_type == 'Library':
                pass
            elif node_type == 'Pool':
                self.memory.compile_pool(decl, pre_pass_only=True)
            elif node_type == 'Assignment':
                if decl.target not in self.variables:
                    pool_prefixed = f"FixedPool.{decl.target}"
                    is_fixed_pool_var = (pool_prefixed in self.variables and
                                    (self.variables[pool_prefixed] & 0x80000000))
                    
                    is_dynamic_pool_member = False
                    is_linkage_field_access = False  # NEW

                    if '.' in decl.target:
                        parts = decl.target.split('.')
                        if len(parts) == 2:
                            base_name = parts[0]
                            pool_name = f"DynamicPool.{base_name}"
                            if hasattr(self.memory, 'dynamic_pool_metadata') and pool_name in self.memory.dynamic_pool_metadata:
                                member_name = parts[1]
                                if member_name in self.memory.dynamic_pool_metadata[pool_name]['members']:
                                    is_dynamic_pool_member = True
                                    print(f"DEBUG: Skipping '{decl.target}' (DynamicPool member)")
                                    
                                    
                                    
                                    
                                    
                                    
                    
                    if is_fixed_pool_var or is_dynamic_pool_member or is_linkage_field_access:
                        print(f"DEBUG: Skipping pre-registration of '{decl.target}' (pool variable)")
                    else:
                        if decl.target not in self.variables:
                            # Check if it's a function parameter
                            symbol = self.symbol_table.lookup(decl.target)
                            if not (symbol and symbol.type == SymbolType.PARAMETER):
                                # Not a parameter, allocate it
                                self.stack_size += 8
                                self.variables[decl.target] = self.stack_size
                                print(f"DEBUG: Pre-registered global variable '{decl.target}' at offset {self.stack_size}")
                            else:
                                print(f"DEBUG: Skipping pre-registration of '{decl.target}' (function parameter)")
                        else:
                            print(f"DEBUG: Skipping pre-registration of '{decl.target}' (already exists)")
                            
                            
                            
                            
                            
                            
                            

        # PASS 2: Compile everything
        print("Phase 1: Generating machine code...")
        self.compile_node(ast)
        print(f"✓ Registered {len(self.user_functions.user_functions)} user functions\n")

        # === PHASE 1.5: Compile ALL function bodies FIRST ===
        print("Phase 1.5: Compiling all user-defined function bodies...")
        for decl in ast.declarations:
            node_type = type(decl).__name__
            if node_type in ('Function', 'FunctionDefinition'):
                self.user_functions.compile_function_definition(decl)
        print(f"✓ Compiled {len(self.user_functions.user_functions)} function bodies\n")

        # PASS 2: Compile rest of program (SubRoutines, LoopMain, etc.)
        print("Phase 2: Compiling program structure...")
        for decl in ast.declarations:
            node_type = type(decl).__name__
        
        # Fix forward references
            # Skip functions - already compiled above
            if node_type in ('Function', 'FunctionDefinition'):
                continue
            
            self.compile_node(decl)
        
        # Fix forward references (this should now include all user functions)
        self.fixup_forward_references()
        
        # === DIAGNOSTIC: Check jump resolution before fixing ===
        # === DIAGNOSTIC: Check jump resolution before fixing === (kept for debugging)
        print("\n" + "="*60)
        print("DIAGNOSTIC: Checking jump/label state before resolution")
        print("DIAGNOSTIC: Checking jump/label state before final resolution")
        print("="*60)
        
        print(f"\nGlobal jumps to resolve: {len(self.asm.jump_manager.global_jumps)}")
        for jump in self.asm.jump_manager.global_jumps:
            print(f"  Jump #{self.asm.jump_manager.global_jumps.index(jump)}:")
            print(f"    Position: {jump.position}")
            print(f"    Target label: '{jump.target_label}'")
            print(f"    Type: {jump.instruction_type}")
            print(f"    Size: {jump.size} bytes")
            print(f"    Context: {jump.context}")
            
            # Check if target label exists
            if jump.target_label in self.asm.jump_manager.global_labels:
                target = self.asm.jump_manager.global_labels[jump.target_label]
                print(f"    ✓ Target found at position {target.position}")
                offset = target.position - (jump.position + jump.size)
                print(f"    Calculated offset: {offset} (0x{offset & 0xFFFFFFFF:08x})")
            elif jump.target_label in self.asm.jump_manager.labels:
                target_pos = self.asm.jump_manager.labels[jump.target_label]
                print(f"    ✓ Target found in unified labels at position {target_pos}")
                offset = target_pos - (jump.position + jump.size)
                print(f"    Calculated offset: {offset} (0x{offset & 0xFFFFFFFF:08x})")
            else:
                print(f"    ✗ TARGET LABEL NOT FOUND!")
                
        print(f"\nGlobal labels available: {len(self.asm.jump_manager.global_labels)}")
        for label_name, label in list(self.asm.jump_manager.global_labels.items())[:20]:  # Show first 20
            print(f"  '{label_name}' at position {label.position}")
            
        print(f"\nUnified labels count: {len(self.asm.jump_manager.labels)}")
        print(f"Sample unified labels: {list(self.asm.jump_manager.labels.keys())[:10]}")
        
        print("\n" + "="*60)
        print("END DIAGNOSTIC")
        print("="*60 + "\n")
        print("Phase 2: Resolving internal jump offsets...")
        self.asm.resolve_jumps()
        
        # After resolve_jumps(), add this:
        print("\n=== CHECKING CRITICAL POSITIONS ===")
        print(f"Position 1008-1020 (SimpleTest ReturnValue area):")
        for i in range(1008, min(1021, len(self.asm.code))):
            print(f"  {i}: 0x{self.asm.code[i]:02x}")
        print()

        print("Phase 3: Building executable...")
        code_bytes = bytes(self.asm.code)
        data_bytes = bytes(self.asm.data)
        
        executable = self.elf.generate(code_bytes, data_bytes, self.asm)
        
        print(f"\n=== COMPILATION COMPLETE ({len(executable)} bytes) ===")
        return executable
            
        
    