# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_parser/ast_modules/ast_statements.py
"""Core statement AST nodes - CORRECT VERSION from project knowledge"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from .ast_base import ASTNode

@dataclass
class RunTask(ASTNode):
    task_name: str  # This is the correct parameter name
    arguments: List[Tuple[str, ASTNode]]

@dataclass
class PrintMessage(ASTNode):
    message: ASTNode

@dataclass
class ReturnValue(ASTNode):
    value: ASTNode

@dataclass
class Assignment(ASTNode):
    target: str  # Keep as string for now
    value: ASTNode

@dataclass
class SendMessage(ASTNode):
    target: str
    parameters: Dict[str, ASTNode]

@dataclass
class ReceiveMessage(ASTNode):
    message_type: str
    body: List[ASTNode]

@dataclass
class HaltProgram(ASTNode):
    message: Optional[str] = None

@dataclass
class BreakLoop(ASTNode):
    pass

@dataclass
class ContinueLoop(ASTNode):
    pass

# Add these if they're missing:
@dataclass
class Loop(ASTNode):
    name: str
    is_main: bool = False
    is_actor: bool = False
    is_shadow: bool = False
    body: List[ASTNode] = None

@dataclass
class SubRoutine(ASTNode):
    name: str
    body: List[ASTNode]

@dataclass
class If(ASTNode):
    condition: ASTNode
    then_body: List[ASTNode]  # Note: then_body not then_block
    else_body: Optional[List[ASTNode]] = None

@dataclass
class While(ASTNode):
    condition: ASTNode
    body: List[ASTNode]

@dataclass
class ForEvery(ASTNode):
    variable: str
    collection: ASTNode  # or iterable
    body: List[ASTNode]

@dataclass
class Try(ASTNode):
    body: List[ASTNode]  # Note: body not try_block
    catch_clauses: List[tuple]  # List of (error_type, block) tuples
    finally_body: Optional[List[ASTNode]] = None

@dataclass
class EveryInterval(ASTNode):
    interval_type: str
    interval_value: int
    body: List[ASTNode]

@dataclass
class WithSecurity(ASTNode):
    context: str
    body: List[ASTNode]

# Add Fork and Branch if they exist
@dataclass
class Fork(ASTNode):
    condition: ASTNode
    true_block: List[ASTNode]
    false_block: List[ASTNode]

@dataclass
class Branch(ASTNode):
    expression: ASTNode
    cases: List[Tuple[ASTNode, List[ASTNode]]]
    default: Optional[List[ASTNode]] = None