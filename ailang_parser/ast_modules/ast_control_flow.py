# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_parser/ast_modules/ast_control_flow.py
"""Control flow AST nodes"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Union
from .ast_base import ASTNode

@dataclass
class If(ASTNode):
    """If-then-else statement"""
    condition: ASTNode
    then_body: List[ASTNode]
    else_body: Optional[List[ASTNode]] = None

@dataclass
class While(ASTNode):
    """While loop statement"""
    condition: ASTNode
    body: List[ASTNode]

@dataclass
class ForEvery(ASTNode):
    """ForEvery loop statement"""
    variable: str
    collection: ASTNode
    body: List[ASTNode]

@dataclass
class Try(ASTNode):
    """Try-catch-finally statement"""
    body: List[ASTNode]
    catch_clauses: List[Tuple[str, List[ASTNode]]]
    finally_body: Optional[List[ASTNode]] = None

@dataclass
class Fork(ASTNode):
    """Fork construct for conditional branching"""
    condition: ASTNode
    true_block: List[ASTNode]
    false_block: List[ASTNode]

@dataclass
class Branch(ASTNode):
    """Branch construct for multi-way branching"""
    expression: ASTNode
    cases: List[Tuple[ASTNode, List[ASTNode]]]  # (value, statements)
    default: Optional[List[ASTNode]] = None

@dataclass
class EveryInterval(ASTNode):
    """Interval-based execution"""
    interval_type: str
    interval_value: Union[int, float]
    body: List[ASTNode]

@dataclass
class WithSecurity(ASTNode):
    """Security context statement"""
    context: str
    body: List[ASTNode]