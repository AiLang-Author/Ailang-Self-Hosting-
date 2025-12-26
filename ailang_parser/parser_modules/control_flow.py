# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_parser/compiler_modules/control_flow.py
"""
Compiler module for handling core flow control constructs like If, While, Branch, etc.

Try/Catch logic has been moved to its own module: try_catch.py
"""

class ControlFlowCompiler:
    def __init__(self, compiler):
        self.compiler = compiler
        self.emitter = compiler.emitter

    # Methods like compile_if, compile_while, etc. would go here.