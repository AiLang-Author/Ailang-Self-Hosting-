# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# tokens_operators.py - Math, Comparison, Logical, and Bitwise Operator Token Types
from enum import Enum, auto

class MathOperatorTokens(Enum):
    # Math Operators (Named)
    ADD = auto()
    SUBTRACT = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    POWER = auto()
    MODULO = auto()
    SQUAREROOT = auto()
    ABSOLUTEVALUE = auto()
    
    # === NEW MATH PRIMITIVES ===
    ISQRT = auto()          # Integer square root
    ABS = auto()            # Absolute value (short form)
    MIN = auto()            # Minimum of two values
    MAX = auto()            # Maximum of two values
    POW = auto()            # Power (short form, alias for POWER)

class ComparisonOperatorTokens(Enum):
    # Comparison Operators (Named)
    GREATERTHAN = auto()
    LESSTHAN = auto()
    GREATEREQUAL = auto()
    LESSEQUAL = auto()
    EQUALTO = auto()
    NOTEQUAL = auto()

class LogicalOperatorTokens(Enum):
    # Logical Operators (Named)
    AND = auto()
    OR = auto()
    NOT = auto()
    XOR = auto()
    IMPLIES = auto()

class BitwiseOperatorTokens(Enum):
    # Bitwise Operators (Named)
    BITWISEAND = auto()
    BITWISEOR = auto()
    BITWISEXOR = auto()
    BITWISENOT = auto()
    LEFTSHIFT = auto()
    RIGHTSHIFT = auto()