# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# tokens_constants.py - Constants and Values Token Types
from enum import Enum, auto

class ConstantTokens(Enum):
    # Constants/Values
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    AUTOMATIC = auto()
    UNLIMITED = auto()

    # Mathematical Constants
    CONSTANT = auto()
    PI = auto()
    E = auto()
    PHI = auto()

class UnitTokens(Enum):
    # Units
    BYTES = auto()
    KILOBYTES = auto()
    MEGABYTES = auto()
    GIGABYTES = auto()
    SECONDS = auto()
    MILLISECONDS = auto()
    MICROSECONDS = auto()
    PERCENT = auto()