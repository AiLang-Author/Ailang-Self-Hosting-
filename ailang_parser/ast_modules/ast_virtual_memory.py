# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_parser/ast_modules/ast_virtual_memory.py
"""Virtual memory management AST nodes"""

from dataclasses import dataclass
from typing import Optional
from .ast_base import ASTNode

@dataclass
class PageTableOperation(ASTNode):
    """Page table management"""
    operation: str  # "create", "map", "unmap", "switch", "get_entry"
    page_table: Optional[ASTNode] = None  # Page table identifier
    virtual_addr: Optional[ASTNode] = None  # Virtual address
    physical_addr: Optional[ASTNode] = None  # Physical address
    size: Optional[ASTNode] = None  # Size in bytes
    flags: Optional[ASTNode] = None  # Protection flags
    levels: Optional[ASTNode] = None  # Page table levels (4 for x86-64)
    page_size: Optional[ASTNode] = None  # Page size (4KB, 2MB, 1GB)

@dataclass
class VirtualMemoryOperation(ASTNode):
    """Virtual memory allocation and management"""
    operation: str  # "allocate", "free", "protect", "query", "commit"
    address: Optional[ASTNode] = None  # Memory address
    size: ASTNode = None  # Size to allocate/operate on
    alignment: Optional[ASTNode] = None  # Memory alignment requirement
    protection: Optional[ASTNode] = None  # Memory protection flags
    numa_node: Optional[ASTNode] = None  # NUMA node preference
    cache_policy: Optional[ASTNode] = None  # Cache behavior hint

@dataclass
class MemoryMappingOperation(ASTNode):
    """Memory-mapped I/O and device mapping"""
    operation: str  # "map", "unmap", "remap", "sync"
    device_addr: Optional[ASTNode] = None  # Physical device address
    virtual_addr: Optional[ASTNode] = None  # Virtual address to map to
    size: ASTNode = None  # Size of mapping
    access_type: Optional[ASTNode] = None  # "read", "write", "execute"
    cache_type: Optional[ASTNode] = None  # "cached", "uncached", "write_combining"
    device_type: Optional[ASTNode] = None  # Device type hint for optimization

@dataclass
class TLBOperation(ASTNode):
    """Translation Lookaside Buffer operations"""
    operation: str  # "invalidate", "flush", "flush_global", "flush_single"
    address: Optional[ASTNode] = None  # Address to invalidate (for single)
    asid: Optional[ASTNode] = None  # Address space identifier
    global_pages: Optional[ASTNode] = None  # Include global pages

@dataclass
class MemoryBarrierOperation(ASTNode):
    """Memory barrier and ordering operations"""
    barrier_type: str  # "read", "write", "full", "acquire", "release"
    scope: Optional[ASTNode] = None  # "local", "global", "device"
    ordering: Optional[ASTNode] = None  # Memory ordering semantics