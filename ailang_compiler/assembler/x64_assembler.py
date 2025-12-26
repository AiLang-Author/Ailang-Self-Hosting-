#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
x86-64 Machine Code Generator - ENHANCED FOR SYSTEMS PROGRAMMING
Modularized version combining all assembler functionality
"""

# Import all module mixins using relative imports
from .modules.base import AssemblerBase
from .modules.registers import RegisterOperations
from .modules.memory import MemoryOperations
from .modules.stack import StackOperations
from .modules.arithmetic import ArithmeticOperations
from .modules.bitwise import BitwiseOperations
from .modules.control_flow import ControlFlowOperations
from .modules.syscalls import SystemCallOperations
from .modules.strings import StringOperations
from .modules.low_level import LowLevelOperations
from .modules.hardware import HardwareOperations
from .modules.cache import CacheOperations
from .modules.inline_asm import InlineAssemblyOperations

# Import dependencies using parent-relative imports
from ..jump_manager import JumpManager
from ..modules.relocation_manager import RelocationManager

class X64Assembler(
    AssemblerBase,
    RegisterOperations,
    MemoryOperations,
    StackOperations,
    ArithmeticOperations,
    BitwiseOperations,
    ControlFlowOperations,
    SystemCallOperations,
    StringOperations,
    LowLevelOperations,
    HardwareOperations,
    CacheOperations,
    InlineAssemblyOperations
):
    """Raw x86-64 machine code generation with ENHANCED low-level operations"""
    
    def __init__(self, elf_generator=None):
        # Initialize base class
        super().__init__(elf_generator)
        
        # Initialize managers that base class expects
        self.jump_manager = JumpManager()
        self.relocation_manager = RelocationManager()
