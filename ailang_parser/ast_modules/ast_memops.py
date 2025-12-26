# ailang_parser/ast_modules/ast_memops.py
"""Memory operation AST nodes for optimized string/pattern operations"""

from dataclasses import dataclass
from typing import List
from .ast_base import ASTNode

@dataclass
class MemCompare(ASTNode):
    """Memory comparison operation - compares two memory regions"""
    addr1: ASTNode
    addr2: ASTNode
    length: ASTNode

@dataclass
class MemChr(ASTNode):
    """Memory character search - finds byte in memory"""
    addr: ASTNode
    byte_value: ASTNode
    length: ASTNode

@dataclass
class MemFind(ASTNode):
    """Memory pattern search - finds pattern in memory"""
    haystack: ASTNode
    haystack_len: ASTNode
    needle: ASTNode
    needle_len: ASTNode
    
@dataclass
class MemCopy(ASTNode):
    """MemCopy(dest, src, length) - SSE2-optimized bulk copy"""
    dest: ASTNode
    src: ASTNode
    length: ASTNode