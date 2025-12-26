# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# tokens_types.py - Type System Token Types
from enum import Enum, auto

class TypeTokens(Enum):
    # Type Keywords
    INTEGER = auto()
    FLOATINGPOINT = auto()
    TEXT = auto()
    BOOLEAN = auto()
    ADDRESS = auto()
    ARRAY = auto()
    MAP = auto()
    TUPLE = auto()
    RECORD = auto()
    OPTIONALTYPE = auto()
    CONSTRAINEDTYPE = auto()
    ANY = auto()
    VOID = auto()

class LowLevelTypeTokens(Enum):
    # === NEW: Low-Level Type Keywords ===
    BYTE = auto()
    WORD = auto()
    DWORD = auto()
    QWORD = auto()
    UINT8 = auto()
    UINT16 = auto()
    UINT32 = auto()
    UINT64 = auto()
    INT8 = auto()
    INT16 = auto()
    INT32 = auto()
    INT64 = auto()