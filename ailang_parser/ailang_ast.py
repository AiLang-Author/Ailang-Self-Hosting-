# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_parser/ailang_ast.py
"""
Main AST module - provides backward compatibility bridge
Imports all AST node classes from the modular structure
"""

# Explicitly import all AST nodes to create a stable public API.
# This avoids fragile wildcard imports and makes dependencies clear.
from ailang_parser.ast_modules.ast_base import ASTNode
from ailang_parser.ast_modules.ast_expressions import (
    TypeExpression, MathExpression, FunctionCall, Apply, RunMacro,
    Identifier, Number, String, Boolean, ArrayLiteral, MapLiteral,
    Array, MemberAccess
)
from ailang_parser.ast_modules.ast_program import (
    Program, Library, AcronymDefinitions, Constant, LinkagePoolDecl
)
from ailang_parser.ast_modules.ast_pools import (
    Pool, SubPool, ResourceItem, PoolEntry, Attribute
)
from ailang_parser.ast_modules.ast_fileio import (
    FilePool, FileHandle, FileOperation
)
from ailang_parser.ast_modules.ast_statements import (
    RunTask, PrintMessage, ReturnValue, Assignment,
    SendMessage, ReceiveMessage, HaltProgram,
    BreakLoop, ContinueLoop, If, While, ForEvery, Try, Fork, Branch,
    EveryInterval, WithSecurity
)
from ailang_parser.ast_modules.ast_functions import (
    Function, Lambda, Combinator, MacroBlock, MacroDefinition, SubRoutine
)
from ailang_parser.ast_modules.ast_loops import (
    Loop, LoopMain, LoopActor, LoopStart, LoopShadow,
    LoopSend, LoopReceive, LoopCase, LoopReply, LoopYield,
    LoopContinue, LoopSpawn, LoopJoin, LoopGetState,
    LoopSetPriority, LoopGetCurrent, LoopSuspend,
    LoopResume, LoopInterrupt
)
from ailang_parser.ast_modules.ast_security_types import (
    SecurityContext, SecurityLevel, ConstrainedType,
    RecordTypeDefinition, RecordType
)
from ailang_parser.ast_modules.ast_virtual_memory import (
    PageTableOperation, VirtualMemoryOperation,
    MemoryMappingOperation, TLBOperation, MemoryBarrierOperation
)
from ailang_parser.ast_modules.ast_low_level import (
    PointerOperation, Dereference, AddressOf, SizeOf,
    MemoryAllocation, MemoryDeallocation, MemoryOperation,
    HardwareRegisterAccess, PortOperation, InterruptHandler, InterruptControl,
    AtomicOperation, MemoryBarrier, CacheOperation, InlineAssembly, SystemCall,
    PrivilegeLevel, DeviceDriver, DeviceRegisterAccess, MMIOOperation, DMAOperation,
    BootloaderCode, KernelEntry, TaskSwitch, ProcessContext, PointerType, LowLevelType
)
from ailang_parser.ast_modules.ast_debug import (
    DebugBlock, DebugAssert, DebugTrace, DebugBreak,
    DebugMemory, DebugPerf, DebugInspect
)

__all__ = [
    # Base
    'ASTNode',
    
    # Expressions
    'TypeExpression', 'MathExpression', 'FunctionCall', 'Apply', 'RunMacro',
    'Identifier', 'Number', 'String', 'Boolean', 'ArrayLiteral', 'MapLiteral',
    'Array',
    
    # Program
    'Program', 'Library', 'AcronymDefinitions', 'Constant', 'LinkagePoolDecl',
    
    # Pools
    'Pool', 'SubPool', 'ResourceItem', 'PoolEntry', 'Attribute',
    
    # File I/O
    'FilePool', 'FileHandle', 'FileOperation',
    
    # Statements
    'RunTask', 'PrintMessage', 'ReturnValue', 'Assignment',
    'SendMessage', 'ReceiveMessage', 'HaltProgram',
    'BreakLoop', 'ContinueLoop',
    
    # Control Flow
    'If', 'While', 'ForEvery', 'Try', 'Fork', 'Branch', 'EveryInterval',
    'WithSecurity',
    
    # Functions
    'Function', 'Lambda', 'Combinator', 'MacroBlock', 'MacroDefinition', 'SubRoutine',
    
    # Loops
    'Loop', 'LoopMain', 'LoopActor', 'LoopStart', 'LoopShadow',
    'LoopSend', 'LoopReceive', 'LoopCase', 'LoopReply', 'LoopYield',
    'LoopContinue', 'LoopSpawn', 'LoopJoin', 'LoopGetState',
    'LoopSetPriority', 'LoopGetCurrent', 'LoopSuspend',
    'LoopResume', 'LoopInterrupt',
    
    # Security and Types
    'SecurityContext', 'SecurityLevel', 'ConstrainedType',
    'RecordTypeDefinition', 'RecordType',
    
    # Low-Level
    'PointerOperation', 'Dereference', 'AddressOf', 'SizeOf',
    'MemoryAllocation', 'MemoryDeallocation', 'MemoryOperation',
    'HardwareRegisterAccess', 'PortOperation',
    'InterruptHandler', 'InterruptControl',
    'AtomicOperation', 'MemoryBarrier', 'CacheOperation',
    'InlineAssembly', 'SystemCall', 'PrivilegeLevel',
    'DeviceDriver', 'DeviceRegisterAccess',
    'MMIOOperation', 'DMAOperation',
    'BootloaderCode', 'KernelEntry',
    'TaskSwitch', 'ProcessContext',
    'PointerType', 'LowLevelType',
    
    # Virtual Memory
    'PageTableOperation', 'VirtualMemoryOperation',
    'MemoryMappingOperation', 'TLBOperation', 'MemoryBarrierOperation',
    
    # Debug
    'DebugBlock', 'DebugAssert', 'DebugTrace', 'DebugBreak',
    'DebugMemory', 'DebugPerf', 'DebugInspect'
]