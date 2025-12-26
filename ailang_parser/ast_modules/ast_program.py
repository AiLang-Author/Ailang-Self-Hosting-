# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_parser/ast_modules/ast_program.py
"""Program structure AST nodes"""

from dataclasses import dataclass
from typing import List, Dict
from .ast_base import ASTNode

@dataclass
class Program(ASTNode):
    declarations: List[ASTNode]

@dataclass
class Library(ASTNode):
    name: str
    body: List[ASTNode]

@dataclass
class AcronymDefinitions(ASTNode):
    """
    AcronymDefinitions block
    Maps short names to long names
    """
    mappings: Dict[str, str]  # acronym -> full_name

@dataclass
class Constant(ASTNode):
    name: str
    value: ASTNode
    
    
@dataclass
class LinkagePoolDecl:
    """
    LinkagePool declaration with directional fields
    
    LinkagePool.MyParams {
        "field1": Initialize=0, Direction=Input
        "field2": Initialize=0, Direction=Output  
        "field3": Initialize=0, Direction=InOut
    }
    """
    name: str
    body: List['PoolEntry']
    line: int
    column: int