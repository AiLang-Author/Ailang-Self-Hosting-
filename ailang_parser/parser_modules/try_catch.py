# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_parser/compiler_modules/try_catch.py
"""
Compiler module for handling Try/Catch/Finally constructs.
Isolated for modularity and easy disabling if needed.
"""
from ..ailang_ast import Try

class TryCatchCompiler:
    def __init__(self, compiler):
        self.compiler = compiler
        self.emitter = compiler.emitter

    def compile_try(self, node: Try):
        """
        Compiles a Try/Catch/Finally block into bytecode.

        This implementation relies on a runtime exception-handling stack
        and three new opcodes: SETUP_TRY, POP_HANDLER, and END_FINALLY.
        """
        finally_block_label = self.emitter.create_label("finally_block")
        catch_dispatcher_label = self.emitter.create_label("catch_dispatcher")
        end_try_label = self.emitter.create_label("end_try")

        catch_body_labels = [self.emitter.create_label(f"catch_body_{i}") for i, _ in enumerate(node.catch_clauses)]

        # --- Step 1: Setup the exception handler ---
        # Pushes a handler frame onto the runtime's exception stack.
        # This frame contains the addresses for the catch and finally logic.
        self.emitter.emit("SETUP_TRY", catch_dispatcher_label, finally_block_label)

        # --- Step 2: Compile the 'try' body ---
        # This is the protected code. If an exception occurs here, the
        # runtime will jump to the catch_dispatcher.
        for stmt in node.body:
            self.compiler.compile_node(stmt)

        # --- Step 3: Normal exit from 'try' block ---
        # If no exception occurred, pop the handler and jump to the finally block.
        self.emitter.emit("POP_HANDLER")
        self.emitter.emit("JUMP", finally_block_label)

        # --- Step 4: Build the catch dispatcher and blocks ---
        self.emitter.mark_label(catch_dispatcher_label)
        # The runtime jumps here when an exception is thrown.
        # The exception object is now on top of the main stack.

        for i, (error_type, catch_body) in enumerate(node.catch_clauses):
            is_any_catch = error_type.base_type == "Any"

            if is_any_catch:
                # This is a generic catch-all, so we don't need to check the type.
                self.emitter.emit("JUMP", catch_body_labels[i])
            else:
                # Placeholder for typed catch logic (e.g., CatchError: MyError)
                # self.emitter.emit("DUP_TOP") // Keep exception object on stack
                # self.emitter.emit("LOAD_CONST", hash(error_type.base_type))
                # self.emitter.emit("CHECK_EXCEPTION_TYPE")
                # self.emitter.emit("JUMP_IF_TRUE", catch_body_labels[i])
                pass

        # If no catch clause matched, the exception is unhandled by this block.
        # We jump to the finally block, and the END_FINALLY instruction will
        # ensure the exception continues to propagate up the stack.
        self.emitter.emit("JUMP", finally_block_label)

        # Compile the actual catch bodies
        for i, (error_type, catch_body) in enumerate(node.catch_clauses):
            self.emitter.mark_label(catch_body_labels[i])
            # The exception object is on the stack. For a simple catch, we pop it.
            # A more advanced implementation would bind it to a variable.
            self.emitter.emit("POP_TOP")
            for stmt in catch_body:
                self.compiler.compile_node(stmt)
            # After handling, jump to the finally block.
            self.emitter.emit("JUMP", finally_block_label)

        # --- Step 5: Compile the 'finally' body ---
        self.emitter.mark_label(finally_block_label)
        if node.finally_body:
            for stmt in node.finally_body:
                self.compiler.compile_node(stmt)

        # --- Step 6: End of the construct ---
        # END_FINALLY is a special instruction that tells the runtime:
        # - If an exception was handled, resume normal execution.
        # - If an unhandled exception is present, continue propagating it.
        self.emitter.emit("END_FINALLY")
        self.emitter.mark_label(end_try_label)