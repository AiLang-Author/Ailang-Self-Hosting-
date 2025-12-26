# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# tokens_systems.py - Low-Level Systems Programming Token Types
from enum import Enum, auto

class SystemsMemoryTokens(Enum):
    # Memory and Pointer Operations
    POINTER = auto()
    DEREFERENCE = auto()
    ADDRESSOF = auto()
    SIZEOF = auto()
    ALLOCATE = auto()
    DEALLOCATE = auto()
    MEMORYCOPY = auto()
    MEMORYSET = auto()
    MEMORYCOMPARE = auto()
    STOREVALUE = auto()

class HardwareTokens(Enum):
    # Hardware Register Access
    HARDWAREREGISTER = auto()
    CONTROLREGISTER = auto()
    SEGMENTREGISTER = auto()
    FLAGSREGISTER = auto()
    MODELSPECIFICREGISTER = auto()

    # Port I/O Operations
    PORTREAD = auto()
    PORTWRITE = auto()
    PORTREADBYTE = auto()
    PORTWRITEBYTE = auto()
    PORTREADWORD = auto()
    PORTWRITEWORD = auto()
    PORTREADDWORD = auto()
    PORTWRITEDWORD = auto()

class InterruptTokens(Enum):
    # Interrupt and Exception Handling
    INTERRUPTHANDLER = auto()
    EXCEPTIONHANDLER = auto()
    ENABLEINTERRUPTS = auto()
    DISABLEINTERRUPTS = auto()
    HALT = auto()
    WAIT = auto()
    TRIGGERSOFTWAREINTERRUPT = auto()
    INTERRUPTVECTOR = auto()

class AtomicTokens(Enum):
    # Atomic Operations
    ATOMICREAD = auto()
    ATOMICWRITE = auto()
    ATOMICADD = auto()
    ATOMICSUBTRACT = auto()
    ATOMICCOMPARESWAP = auto()
    ATOMICEXCHANGE = auto()
    COMPILERFENCE = auto()

class CacheTokens(Enum):
    # Cache and Memory Management
    CACHEINVALIDATE = auto()
    CACHEFLUSH = auto()
    TLBINVALIDATE = auto()
    TLBFLUSH = auto()
    PHYSICALMEMORY = auto()

class AssemblyTokens(Enum):
    # Inline Assembly
    INLINEASSEMBLY = auto()
    ASSEMBLY = auto()
    VOLATILE = auto()
    BARRIER = auto()

class KernelTokens(Enum):
    # System Calls and Kernel Operations
    SYSTEMCALL = auto()
    PRIVILEGELEVEL = auto()
    TASKSWITCH = auto()
    PROCESSCONTEXT = auto()

class DeviceTokens(Enum):
    # Device Driver Operations
    DEVICEDRIVER = auto()
    DEVICEREGISTER = auto()
    DMAOPERATION = auto()
    MMIOREAD = auto()
    MMIOWRITE = auto()
    DEVICEINTERRUPT = auto()

class BootTokens(Enum):
    # Boot and Initialization
    BOOTLOADER = auto()
    KERNELENTRY = auto()
    INITIALIZATION = auto()
    GLOBALCONSTRUCTORS = auto()
    GLOBALDESTRUCTORS = auto()