# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# tokens_virtual_memory.py - Virtual Memory Token Types
from enum import Enum, auto

class VirtualMemoryTokens(Enum):
    # === VIRTUAL MEMORY TOKENS ===
    PAGETABLE = auto()
    VIRTUALMEMORY = auto()
    MMIO = auto()
    CACHE = auto()
    TLB = auto()
    MEMORYBARRIER = auto()

    # Memory Management Flags
    READONLY = auto()
    READWRITE = auto()
    READEXECUTE = auto()
    READWRITEEXECUTE = auto()
    USERMODE = auto()
    KERNELMODE = auto()
    GLOBAL = auto()
    DIRTY = auto()
    ACCESSED = auto()

    # Cache Types and Levels
    CACHED = auto()
    UNCACHED = auto()
    WRITECOMBINING = auto()
    WRITETHROUGH = auto()
    WRITEBACK = auto()
    L1CACHE = auto()
    L2CACHE = auto()
    L3CACHE = auto()

    # Page Sizes
    PAGESIZE4KB = auto()
    PAGESIZE2MB = auto()
    PAGESIZE1GB = auto()

    # TLB Operations
    INVALIDATE = auto()
    FLUSH = auto()
    FLUSHALL = auto()
    FLUSHGLOBAL = auto()