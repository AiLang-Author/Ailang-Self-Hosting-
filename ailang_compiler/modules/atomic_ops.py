# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_compiler/modules/atomic_ops.py

class AtomicOps:
    """Handles compilation of atomic operations."""
    def __init__(self, compiler):
        self.compiler = compiler
        self.asm = compiler.asm

    def compile_operation(self, node):
        """Dispatches an atomic operation to the correct handler."""
        op_map = {
            'AtomicAdd': self.compile_atomic_add,
            # Add other atomics like AtomicSubtract, etc. here later
        }
        if node.function in op_map:
            return op_map[node.function](node)
        return False

    def compile_atomic_add(self, node):
        """Compiles AtomicAdd(address, value)"""
        if len(node.arguments) != 2:
            raise ValueError("AtomicAdd requires exactly two arguments: an address and a value.")

        # First argument is the address (e.g., AddressOf(variable))
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_push_rax() # Save the address on the stack

        # Second argument is the value to add
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_mov_rbx_rax() # Move the value into RBX

        # Retrieve the address from the stack into RAX
        self.asm.emit_pop_rax()

        # Emit the atomic instruction: LOCK ADD [RAX], RBX
        # 0xF0 is the LOCK prefix, making the following instruction atomic.
        # 0x48 0x01 0x18 is ADD [RAX], RBX
        self.asm.emit_bytes(0xF0, 0x48, 0x01, 0x18)
        print(f"DEBUG: Emitted LOCK ADD [RAX], RBX")

        return True