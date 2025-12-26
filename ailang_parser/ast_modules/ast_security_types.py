# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_parser/ast_modules/ast_security_types.py
"""Security context and type system AST nodes"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from .ast_base import ASTNode
from .ast_expressions import TypeExpression

@dataclass
class SecurityContext(ASTNode):
    name: str
    levels: Dict[str, 'SecurityLevel']

@dataclass
class SecurityLevel(ASTNode):
    name: str
    allowed_operations: List[str]
    denied_operations: List[str]
    memory_limit: Optional[ASTNode]
    cpu_quota: Optional[ASTNode]

@dataclass
class ConstrainedType(ASTNode):
    name: str
    base_type: ASTNode
    constraints: ASTNode

@dataclass
class RecordTypeDefinition(ASTNode):
    """Type definition for a Record structure"""
    name: str
    record_type: TypeExpression

@dataclass
class RecordType(ASTNode):
    """Record type definition"""
    name: str
    fields: Dict[str, ASTNode]