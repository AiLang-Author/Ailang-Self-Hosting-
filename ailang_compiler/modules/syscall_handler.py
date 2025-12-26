#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.
"""
System Call Handler Module for AILANG Compiler
Handles compilation of SystemCall() primitives
"""

class SystemCallHandler:
    """Handles SystemCall primitive compilation"""
    
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm
    
    def compile_system_call(self, node):
        """
        Compile SystemCall(number, arg1, arg2, ...) primitive
        
        Handles Linux x86-64 syscall convention:
        - RAX: syscall number
        - RDI, RSI, RDX, R10, R8, R9: arguments 1-6
        
        Returns: Syscall result in RAX (NOT pushed - caller expects it in RAX)
        """
        syscall_arg_regs = ['rdi', 'rsi', 'rdx', 'r10', 'r8', 'r9']
        num_syscall_args = len(node.arguments) - 1  # Subtract syscall number

        if num_syscall_args > len(syscall_arg_regs):
            raise ValueError(
                f"SystemCall supports up to {len(syscall_arg_regs)} arguments, "
                f"got {num_syscall_args}"
            )

        print(f"DEBUG: Compiling SystemCall with {num_syscall_args} arguments")

        # CRITICAL: Zero ALL argument registers first to prevent garbage values
        self.asm.zero_syscall_registers()

        # Compile all arguments and push to stack to prevent register clobbering
        for i in range(num_syscall_args):
            arg_node = node.arguments[i + 1]
            self.compiler.compile_expression(arg_node)  # Use compile_expression instead of compile_node
            self.asm.emit_push_rax()                    # Save to stack
            print(f"DEBUG: Compiled and pushed argument {i+1}")

        # Pop from stack into registers in REVERSE order
        for i in reversed(range(num_syscall_args)):
            reg = syscall_arg_regs[i]
            if reg == 'rdi':
                self.asm.emit_pop_rdi()
            elif reg == 'rsi':
                self.asm.emit_pop_rsi()
            elif reg == 'rdx':
                self.asm.emit_pop_rdx()
            elif reg == 'r10':
                self.asm.emit_pop_r10()
            elif reg == 'r8':
                self.asm.emit_pop_r8()
            elif reg == 'r9':
                self.asm.emit_pop_r9()
            print(f"DEBUG: Popped argument into {reg}")

        # Load syscall number into RAX (last, so it doesn't get clobbered)
        self.compiler.compile_expression(node.arguments[0])  # Use compile_expression instead of compile_node
        print(f"DEBUG: Loaded syscall number into RAX")

        # Execute the syscall
        self.asm.emit_syscall()

        # Result is now in RAX - DON'T PUSH IT
        # The compiler expects function results to be in RAX
        print(f"DEBUG: SystemCall completed, result in RAX")
        
        return True