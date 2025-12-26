# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_parser/ast_modules/ast_debug.py
"""Debug-related AST nodes"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class DebugBlock:
    """Debug code block - compiled conditionally"""
    label: str
    level: int
    body: list
    line: int
    column: int

@dataclass
class DebugAssert:
    """Debug assertion"""
    condition: object
    message: str
    line: int
    column: int

@dataclass  
class DebugTrace:
    """Debug trace point"""
    trace_type: str  # "Entry", "Exit", "Point"
    label: str
    values: list
    line: int
    column: int

@dataclass
class DebugBreak:
    """Debug breakpoint"""
    break_type: str  # "Simple", "Conditional", "Count", "Data"
    label: str
    condition: object = None
    count: int = None
    line: int = 0
    column: int = 0

@dataclass
class DebugMemory:
    """Memory debugging operation"""
    operation: str  # "Dump", "Watch", "LeakStart", "LeakCheck", "Pattern"
    address: object = None
    size: int = None
    pattern: int = None
    label: str = None
    line: int = 0
    column: int = 0

@dataclass
class DebugPerf:
    """Performance debugging"""
    operation: str  # "Start", "End", "CacheStats", "TLBStats"
    label: str = None
    line: int = 0
    column: int = 0

@dataclass
class DebugInspect:
    """State inspection"""
    target: str  # "Variables", "Stack", "Pools", "Agents"
    line: int = 0
    column: int = 0