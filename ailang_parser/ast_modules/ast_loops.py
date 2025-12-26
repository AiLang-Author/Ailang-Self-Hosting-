# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_parser/ast_modules/ast_loops.py
"""Loop and actor model AST nodes"""

from dataclasses import dataclass
from typing import List, Optional
from .ast_base import ASTNode

# --- Basic Loop Definition ---

@dataclass
class Loop(ASTNode):
    loop_type: str
    name: str
    body: List[ASTNode]
    end_name: Optional[str] = None

# --- Actor Model Loop Nodes ---

@dataclass
class LoopMain(ASTNode):
    """Main event loop"""
    name: str
    body: List[ASTNode]

@dataclass
class LoopActor(ASTNode):
    """Actor with isolated state"""
    name: str
    body: List[ASTNode]

@dataclass
class LoopStart(ASTNode):
    """Initialization loop"""
    name: str
    body: List[ASTNode]

@dataclass
class LoopShadow(ASTNode):
    """Background loop"""
    name: str
    body: List[ASTNode]

@dataclass
class LoopSend(ASTNode):
    """Send message to actor"""
    target: ASTNode
    message: ASTNode

@dataclass
class LoopReceive(ASTNode):
    """Receive message block"""
    variable: Optional[str]
    cases: List['LoopCase']

@dataclass
class LoopCase(ASTNode):
    """Case in receive block"""
    pattern: str
    action: List[ASTNode]

@dataclass
class LoopReply(ASTNode):
    """Reply to sender"""
    message: ASTNode

@dataclass
class LoopYield(ASTNode):
    """Yield control"""
    expression: Optional[ASTNode]

@dataclass
class LoopContinue(ASTNode):
    """Continuous loop"""
    body: List[ASTNode]

@dataclass
class LoopSpawn(ASTNode):
    """Spawn a new actor instance"""
    actor_reference: ASTNode
    initial_state: Optional[ASTNode] = None

@dataclass
class LoopJoin(ASTNode):
    """Wait for actor completion"""
    handle: ASTNode
    timeout: Optional[ASTNode] = None

@dataclass
class LoopGetState(ASTNode):
    """Get actor state"""
    handle: ASTNode

@dataclass
class LoopSetPriority(ASTNode):
    """Set actor priority hint"""
    handle: ASTNode
    priority: ASTNode

@dataclass
class LoopGetCurrent(ASTNode):
    """Get current actor handle"""
    pass

@dataclass
class LoopSuspend(ASTNode):
    """Suspend an actor"""
    handle: ASTNode

@dataclass
class LoopResume(ASTNode):
    """Resume a suspended actor"""
    handle: ASTNode

@dataclass
class LoopInterrupt(ASTNode):
    """Send interrupt signal to actor"""
    handle: ASTNode
    signal: ASTNode