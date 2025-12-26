# ailang_parser/ast_modules/__init__.py
"""AST modules package - exports all AST node classes"""

# Import all AST node classes from their respective modules
from .ast_base import ASTNode
from .ast_expressions import (
    TypeExpression, MathExpression, FunctionCall, Apply, RunMacro,
    Identifier, Number, String, Boolean, ArrayLiteral, MapLiteral,
    MemberAccess,  # ADD THIS
    Array
)
from .ast_statements import (
    Loop, SubRoutine, RunTask, PrintMessage, ReturnValue,  # ReturnValue must be here
    Assignment, If, While, ForEvery, Try,
    SendMessage, ReceiveMessage, EveryInterval, WithSecurity,
    BreakLoop, ContinueLoop, HaltProgram
)

from .ast_program import (
    Program, Library, AcronymDefinitions, Constant
)

from .ast_pools import (
    Pool, SubPool, ResourceItem
)

from .ast_fileio import (
    FilePool, FileHandle, FileOperation
)

from .ast_memops import (
    MemCompare, MemChr, MemFind
)



from .ast_control_flow import (
    If, While, ForEvery, Try, Fork, Branch,
    EveryInterval, WithSecurity
)

from .ast_functions import (
    Function, Lambda, Combinator, MacroBlock, MacroDefinition, SubRoutine
)

from .ast_loops import (
    Loop, LoopMain, LoopActor, LoopStart, LoopShadow,
    LoopSend, LoopReceive, LoopCase, LoopReply, LoopYield,
    LoopContinue, LoopSpawn, LoopJoin, LoopGetState,
    LoopSetPriority, LoopGetCurrent, LoopSuspend,
    LoopResume, LoopInterrupt
)

from .ast_security_types import (
    SecurityContext, SecurityLevel, ConstrainedType,
    RecordTypeDefinition, RecordType
)

from .ast_low_level import (
    PointerOperation, Dereference, AddressOf, SizeOf,
    MemoryAllocation, MemoryDeallocation, MemoryOperation,
    HardwareRegisterAccess, PortOperation,
    InterruptHandler, InterruptControl,
    AtomicOperation, MemoryBarrier, CacheOperation,
    InlineAssembly, SystemCall, PrivilegeLevel,
    DeviceDriver, DeviceRegisterAccess,
    MMIOOperation, DMAOperation,
    BootloaderCode, KernelEntry,
    TaskSwitch, ProcessContext,
    PointerType, LowLevelType
)

from .ast_virtual_memory import (
    PageTableOperation, VirtualMemoryOperation,
    MemoryMappingOperation, TLBOperation, MemoryBarrierOperation
)

from .ast_debug import (
    DebugBlock, DebugAssert, DebugTrace, DebugBreak,
    DebugMemory, DebugPerf, DebugInspect
)

# Export all classes for easy import
__all__ = [
    # Base
    'ASTNode',
    
    # Expressions
    'TypeExpression', 'MathExpression', 'FunctionCall', 'Apply', 'RunMacro',
    'Identifier', 'Number', 'String', 'Boolean', 'ArrayLiteral', 'MapLiteral',
    'Array',
    
    # Program
    'Program', 'Library', 'AcronymDefinitions', 'Constant',
    
    # Pools
    'Pool', 'SubPool', 'ResourceItem',
    
    # File I/O
    'FilePool', 'FileHandle', 'FileOperation',
    
    # Statements
    'RunTask', 'PrintMessage', 'ReturnValue', 'Assignment',
    'SendMessage', 'ReceiveMessage', 'HaltProgram',
    'BreakLoop', 'ContinueLoop',
    
    # Control Flow
    'If', 'While', 'ForEvery', 'Try', 'Fork', 'Branch',
    'EveryInterval', 'WithSecurity',
    
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
    'DebugMemory', 'DebugPerf', 'DebugInspect',

    # Memory Operations
    'MemCompare', 'MemChr', 'MemFind',
]