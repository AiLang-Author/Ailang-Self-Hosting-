# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_parser/ast_modules/ast_pools.py
"""Pool-related AST nodes"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from .ast_base import ASTNode

@dataclass
class Pool(ASTNode):
    pool_type: str
    name: str
    body: List[ASTNode]

@dataclass
class SubPool(ASTNode):
    name: str
    items: Dict[str, 'ResourceItem']

@dataclass
class ResourceItem(ASTNode):
    key: str
    value: Optional[ASTNode]
    attributes: Dict[str, ASTNode] = field(default_factory=dict)
    
    
@dataclass  
class PoolEntry:
    """Entry in a Pool (FixedPool, DynamicPool, or LinkagePool)"""
    key: str
    attributes: List['Attribute']
    line: int
    column: int

@dataclass
class Attribute:
    """Attribute like Initialize=0, Direction=Input, CanChange=True"""
    key: str
    value: 'ASTNode'
    line: int
    column: int

@dataclass
class LinkageFieldAccess:
    """
    Access to a field in a LinkagePool parameter
    
    In: params.field1
    Out: LinkageFieldAccess(pool_param='params', field='field1')
    """
    pool_param: str  # The parameter name
    pool_type: str   # The LinkagePool type (e.g., 'LinkagePool.MyParams')
    field: str       # The field name
    is_write: bool   # True for assignment target, False for read
    line: int
    column: int