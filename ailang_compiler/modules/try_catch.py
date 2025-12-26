# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_parser/compiler_modules/try_catch.py
"""
Complete Try/Catch/Finally implementation for AILANG compiler.
This handles control flow without requiring runtime exception support.
"""

from typing import List, Tuple, Optional
from ailang_parser.ailang_ast import *

class TryCatchCompiler:
    """
    Handles compilation of Try/Catch/Finally blocks.
    
    Since AILANG doesn't have runtime exceptions yet, this implementation
    uses a simple error flag approach where errors are simulated through
    variable checks rather than actual exception throwing.
    """
    
    def __init__(self, compiler):
        self.compiler = compiler
        self.asm = compiler.asm
        self.memory = compiler.memory if hasattr(compiler, 'memory') else None
        
        # Error flag variable name (used for error simulation)
        self.error_flag_var = "__error_flag__"
        self.error_occurred_var = "__error_occurred__"
        
    def compile_try(self, node: Try) -> bool:
        """
        Compile a Try/Catch/Finally construct.
        
        Control flow:
        1. Execute try block
        2. Check if error occurred (via flag)
        3. If error, execute matching catch block
        4. Always execute finally block
        """
        print(f"DEBUG: Compiling TryBlock")
        print(f"  - Body statements: {len(node.body)}")
        print(f"  - Catch clauses: {len(node.catch_clauses)}")
        print(f"  - Finally statements: {len(node.finally_body) if node.finally_body else 0}")
        
        try:
            # Generate all necessary labels
            catch_start_label = self.asm.create_label()
            finally_label = self.asm.create_label()
            end_label = self.asm.create_label()
            
            # Labels for each catch clause
            catch_labels = []
            for i in range(len(node.catch_clauses)):
                catch_labels.append(self.asm.create_label())
            
            # Initialize error tracking (if not already done)
            self._ensure_error_vars_initialized()
            
            # Clear any previous error state
            self._clear_error_flag()
            
            # === STEP 1: Execute Try Block ===
            print("DEBUG: Compiling try body")
            for stmt in node.body:
                self.compiler.compile_node(stmt)
            
            # After try block, check if error occurred
            self._check_error_flag()  # Result in RAX
            
            # If error occurred (RAX != 0), jump to catch dispatcher
            self.asm.emit_bytes(0x48, 0x83, 0xF8, 0x00)  # CMP RAX, 0
            self.asm.emit_jump_to_label(catch_start_label, "JNE")
            
            # No error - jump directly to finally
            self.asm.emit_jump_to_label(finally_label, "JMP")
            
            # === STEP 2: Catch Dispatcher ===
            self.asm.mark_label(catch_start_label)
            
            if node.catch_clauses:
                print(f"DEBUG: Setting up catch dispatcher for {len(node.catch_clauses)} clauses")
                
                # For now, we only support generic catch (Any type)
                # Jump to first catch block (in future, we'd check error types here)
                if catch_labels:
                    self.asm.emit_jump_to_label(catch_labels[0], "JMP")
                    
                # === STEP 3: Catch Blocks ===
                for i, (error_type, catch_body) in enumerate(node.catch_clauses):
                    self.asm.mark_label(catch_labels[i])
                    print(f"DEBUG: Compiling catch block {i}")
                    
                    # Clear error flag (error was handled)
                    self._clear_error_flag()
                    
                    # Execute catch body
                    for stmt in catch_body:
                        self.compiler.compile_node(stmt)
                    
                    # After catch, jump to finally
                    self.asm.emit_jump_to_label(finally_label, "JMP")
            else:
                # No catch clauses - error remains unhandled
                self.asm.emit_jump_to_label(finally_label, "JMP")
            
            # === STEP 4: Finally Block ===
            self.asm.mark_label(finally_label)
            
            if node.finally_body:
                print(f"DEBUG: Compiling finally block with {len(node.finally_body)} statements")
                for stmt in node.finally_body:
                    self.compiler.compile_node(stmt)
            
            # === STEP 5: End ===
            self.asm.mark_label(end_label)
            
            print("DEBUG: TryBlock compilation completed successfully")
            return True
            
        except Exception as e:
            print(f"ERROR: TryBlock compilation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _ensure_error_vars_initialized(self):
        """Ensure error tracking variables are allocated"""
        # Check if error flag variable exists
        if self.memory and not self.memory.is_variable_defined(self.error_occurred_var):
            print(f"DEBUG: Allocating error tracking variable: {self.error_occurred_var}")
            # Allocate space for error flag
            self.memory.allocate_variable(self.error_occurred_var)
            # Initialize to 0 (no error)
            self.asm.emit_mov_rax_imm64(0)
            offset = self.memory.get_variable_offset(self.error_occurred_var)
            self.asm.emit_mov_mem_rbp_offset_rax(offset)
    
    def _clear_error_flag(self):
        """Clear the error flag (set to 0)"""
        if self.memory and self.memory.is_variable_defined(self.error_occurred_var):
            print("DEBUG: Clearing error flag")
            self.asm.emit_mov_rax_imm64(0)
            offset = self.memory.get_variable_offset(self.error_occurred_var)
            self.asm.emit_mov_mem_rbp_offset_rax(offset)
    
    def _check_error_flag(self):
        """Check error flag and put result in RAX"""
        if self.memory and self.memory.is_variable_defined(self.error_occurred_var):
            print("DEBUG: Checking error flag")
            offset = self.memory.get_variable_offset(self.error_occurred_var)
            self.asm.emit_mov_rax_mem_rbp_offset(offset)
        else:
            # No error variable defined - assume no error
            self.asm.emit_mov_rax_imm64(0)
    
    def simulate_error(self):
        """
        Helper method to simulate an error occurring.
        This would be called by other parts of the compiler when
        an error condition is detected.
        """
        if self.memory and self.memory.is_variable_defined(self.error_occurred_var):
            print("DEBUG: Simulating error - setting error flag")
            self.asm.emit_mov_rax_imm64(1)
            offset = self.memory.get_variable_offset(self.error_occurred_var)
            self.asm.emit_mov_mem_rbp_offset_rax(offset)


class SimplifiedTryCatchCompiler:
    """
    Simplified version for basic testing where error handling isn't needed.
    This just executes try and finally blocks sequentially.
    """
    
    def __init__(self, compiler):
        self.compiler = compiler
        self.asm = compiler.asm
    
    def compile_try(self, node: Try) -> bool:
        """
        Simple sequential execution of try and finally blocks.
        Suitable for tests that don't actually throw errors.
        """
        print(f"DEBUG: SimplifiedTryCatch - Compiling TryBlock")
        
        try:
            # Execute try body
            print(f"DEBUG: Executing try body ({len(node.body)} statements)")
            for stmt in node.body:
                self.compiler.compile_node(stmt)
            
            # Execute finally block if present
            if node.finally_body:
                print(f"DEBUG: Executing finally block ({len(node.finally_body)} statements)")
                for stmt in node.finally_body:
                    self.compiler.compile_node(stmt)
            
            print("DEBUG: TryBlock completed")
            return True
            
        except Exception as e:
            print(f"ERROR: TryBlock compilation failed: {str(e)}")
            raise


# === Integration Helper ===

def register_try_catch_in_compiler(compiler):
    """
    Helper function to register the Try/Catch compiler in the main compiler.
    Call this from the main compiler's __init__ method.
    """
    # Use simplified version if testing, full version for production
    use_simplified = True  # Set to False for full error handling
    
    if use_simplified:
        compiler.try_catch = SimplifiedTryCatchCompiler(compiler)
        print("DEBUG: Registered SimplifiedTryCatchCompiler")
    else:
        compiler.try_catch = TryCatchCompiler(compiler)
        print("DEBUG: Registered full TryCatchCompiler")
    
    # Register in dispatch handlers
    if hasattr(compiler, 'dispatch_handlers'):
        compiler.dispatch_handlers['Try'] = lambda n: compiler.try_catch.compile_try(n)
        compiler.dispatch_handlers['TryBlock'] = lambda n: compiler.try_catch.compile_try(n)
        print("DEBUG: Registered Try/TryBlock in dispatch handlers")
    
    return compiler.try_catch