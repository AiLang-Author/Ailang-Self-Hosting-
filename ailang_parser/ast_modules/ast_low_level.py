# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_parser/ast_modules/ast_low_level.py
"""Low-level systems programming AST nodes"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from .ast_base import ASTNode

# --- Pointer Operations ---

@dataclass
class PointerOperation(ASTNode):
    """Base class for pointer operations"""
    operation: str  # "dereference", "address_of", "pointer_arithmetic"
    target: ASTNode
    offset: Optional[ASTNode] = None  # For pointer arithmetic

@dataclass
class Dereference(ASTNode):
    """Dereference a pointer to get the value it points to"""
    pointer: ASTNode  # The pointer to dereference
    size_hint: Optional[str] = None  # "byte", "word", "dword", "qword"

@dataclass
class AddressOf(ASTNode):
    """Get the address of a variable"""
    variable: ASTNode  # The variable to get address of

@dataclass
class SizeOf(ASTNode):
    """Get the size of a type or variable"""
    target: ASTNode  # Type or variable to get size of

# --- Memory Management ---

@dataclass
class MemoryAllocation(ASTNode):
    """Allocate memory"""
    size: ASTNode = None  # Size to allocate
    alignment: Optional[ASTNode] = None  # Memory alignment

@dataclass
class MemoryDeallocation(ASTNode):
    """Free allocated memory"""
    pointer: ASTNode  # Pointer to memory to free

@dataclass
class MemoryOperation(ASTNode):
    """Generic memory operation (copy, set, compare)"""
    operation: str  # "copy", "set", "compare"
    destination: ASTNode
    source: Optional[ASTNode] = None
    size: ASTNode = None
    value: Optional[ASTNode] = None  # For memory set operations

# --- Hardware Access ---

@dataclass
class HardwareRegisterAccess(ASTNode):
    """Access CPU/hardware registers"""
    register_type: str  # "general", "control", "segment", "flags", "msr"
    register_name: str  # "RAX", "CR3", "CS", etc.
    operation: str  # "read", "write"
    value: Optional[ASTNode] = None  # For write operations

@dataclass
class PortOperation(ASTNode):
    """I/O port operations"""
    operation: str  # "read", "write"
    port: ASTNode  # Port number
    size: str  # "byte", "word", "dword"
    value: Optional[ASTNode] = None  # For write operations

# --- Interrupt Handling ---

@dataclass
class InterruptHandler(ASTNode):
    """Define an interrupt or exception handler"""
    handler_type: str  # "interrupt", "exception"
    vector: ASTNode  # Interrupt vector number
    handler_name: str  # Name of the handler function
    body: List[ASTNode]

@dataclass
class InterruptControl(ASTNode):
    """Control interrupt state"""
    operation: str  # "enable", "disable", "trigger"
    interrupt_number: Optional[ASTNode] = None  # For software interrupts

# --- Atomic Operations ---

@dataclass
class AtomicOperation(ASTNode):
    """Atomic memory operations"""
    operation: str  # "read", "write", "add", "subtract", "compare_swap", "exchange"
    target: ASTNode  # Memory location
    value: Optional[ASTNode] = None  # Value for operations
    compare_value: Optional[ASTNode] = None  # For compare_swap
    ordering: str = "sequential"  # Memory ordering

@dataclass
class MemoryBarrier(ASTNode):
    """Memory barrier/fence operations"""
    barrier_type: str  # "memory", "compiler", "acquire", "release"

# --- Cache Operations ---

@dataclass
class CacheOperation(ASTNode):
    """Cache management operations"""
    operation: str  # "invalidate", "flush"
    cache_type: str  # "data", "instruction", "tlb"
    address: Optional[ASTNode] = None  # Specific address or None for all

# --- Assembly and System Calls ---

@dataclass
class InlineAssembly(ASTNode):
    """Inline assembly code"""
    assembly_code: str  # Raw assembly instructions
    inputs: List[Tuple[str, ASTNode]] = field(default_factory=list)  # Input constraints
    outputs: List[Tuple[str, ASTNode]] = field(default_factory=list)  # Output constraints
    clobbers: List[str] = field(default_factory=list)  # Clobbered registers
    volatile: bool = False  # Whether assembly has side effects

@dataclass
class SystemCall(ASTNode):
    """Make a system call"""
    call_number: ASTNode  # System call number
    arguments: List[ASTNode] = field(default_factory=list)  # System call arguments

# --- Privilege and Security ---

@dataclass
class PrivilegeLevel(ASTNode):
    """Set or check privilege level"""
    operation: str  # "set", "get", "check"
    level: Optional[ASTNode] = None  # Privilege level (0-3)

# --- Device Management ---

@dataclass
class DeviceDriver(ASTNode):
    """Device driver declaration"""
    driver_name: str
    device_type: str  # "block", "character", "network", etc.
    operations: Dict[str, ASTNode]  # Driver operation handlers

@dataclass
class DeviceRegisterAccess(ASTNode):
    """Access device registers"""
    operation: str  # "read", "write"
    device: ASTNode  # Device identifier
    register_offset: ASTNode  # Register offset
    value: Optional[ASTNode] = None  # For write operations

@dataclass
class MMIOOperation(ASTNode):
    """Memory-mapped I/O operations"""
    operation: str  # "read", "write"
    address: ASTNode  # Physical/virtual address
    size: str  # "byte", "word", "dword", "qword"
    value: Optional[ASTNode] = None  # For write operations
    volatile: bool = True  # MMIO is typically volatile

@dataclass
class DMAOperation(ASTNode):
    """Direct Memory Access operations"""
    operation: str  # "setup", "start", "stop", "status"
    channel: ASTNode  # DMA channel
    source: Optional[ASTNode] = None  # Source address
    destination: Optional[ASTNode] = None  # Destination address
    size: Optional[ASTNode] = None  # Transfer size

# --- Boot and Kernel ---

@dataclass
class BootloaderCode(ASTNode):
    """Bootloader-specific code"""
    stage: str  # "stage1", "stage2", "uefi"
    body: List[ASTNode]

@dataclass
class KernelEntry(ASTNode):
    """Kernel entry point"""
    entry_name: str
    parameters: List[Tuple[str, ASTNode]] = field(default_factory=list)
    body: List[ASTNode] = field(default_factory=list)

# --- Task Management ---

@dataclass
class TaskSwitch(ASTNode):
    """Context/task switching"""
    operation: str  # "save", "restore", "switch"
    context: ASTNode  # Context identifier or structure

@dataclass
class ProcessContext(ASTNode):
    """Process context management"""
    operation: str  # "create", "destroy", "switch"
    process_id: Optional[ASTNode] = None
    context_data: Optional[ASTNode] = None

# --- Low-Level Types ---

@dataclass
class PointerType(ASTNode):
    """Pointer type declaration"""
    pointed_type: ASTNode  # Type being pointed to

@dataclass
class LowLevelType(ASTNode):
    """Low-level primitive types"""
    type_name: str  # "byte", "word", "dword", "qword", "uint8", etc.
    signed: bool = False  # Whether type is signed
    size: int = 1  # Size in bytes