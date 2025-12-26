# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_parser/ast_modules/ast_fileio.py
"""File I/O AST nodes"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from .ast_base import ASTNode

@dataclass
class FilePool(ASTNode):
    """Represents a FilePool declaration for managing file handles"""
    name: str
    handles: Dict[str, 'FileHandle']

@dataclass
class FileHandle(ASTNode):
    """Represents a file handle with path and mode"""
    handle_name: str
    file_path: ASTNode  # Usually a String node
    mode: str          # "read", "write", "append", "readwrite", etc.
    options: Dict[str, ASTNode] = field(default_factory=dict)

@dataclass
class FileOperation(ASTNode):
    """Generic file operation node"""
    operation: str              # "open", "read", "write", "close", etc.
    file_argument: ASTNode      # File path or handle
    mode: Optional[str] = None  # File mode for open operations
    data: Optional[ASTNode] = None      # Data for write operations
    position: Optional[ASTNode] = None  # Position for seek operations
    buffer_size: Optional[ASTNode] = None  # Buffer size for buffered operations