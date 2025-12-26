# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# File: ailang_parser/ast_modules/ast_expressions.py
# COMPLETE VERSION with MemberAccess

from dataclasses import dataclass
from typing import List, Tuple, Any, Optional, Union
from .ast_base import ASTNode

@dataclass
class TypeExpression(ASTNode):
    base_type: str
    element_type: Optional[str] = None

@dataclass
class MathExpression(ASTNode):
    operator: str
    left: ASTNode
    right: ASTNode

@dataclass
class FunctionCall(ASTNode):
    function: Union[str, ASTNode]  # Accept both for transition
    arguments: List[ASTNode]

@dataclass
class Apply(ASTNode):
    function: ASTNode
    arguments: List[ASTNode]

@dataclass
class RunMacro(ASTNode):
    macro_path: str
    arguments: List[ASTNode]

@dataclass
class Identifier(ASTNode):
    name: str
    original_name: Optional[str] = None

@dataclass
class Number(ASTNode):
    value: Union[int, float, str]

@dataclass
class String(ASTNode):
    value: str

@dataclass
class Boolean(ASTNode):
    value: bool

@dataclass
class ArrayLiteral(ASTNode):
    elements: List[ASTNode]

@dataclass
class MapLiteral(ASTNode):
    pairs: List[Tuple[ASTNode, ASTNode]]

@dataclass
class MemberAccess(ASTNode):
    """Represents accessing a member of an object, e.g., my_object.field"""
    obj: ASTNode
    member: ASTNode  # Using ASTNode instead of Identifier for flexibility

# Convenience alias
Array = ArrayLiteral