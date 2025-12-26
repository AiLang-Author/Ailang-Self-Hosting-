#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Type Tagging System for AILANG
Uses odd/even addresses to distinguish types:
- Numbers: EVEN (bit 0 = 0)
- String pointers: ODD (bit 0 = 1)
"""

class TypeTagging:
    """Helper methods for type tagging operations"""
    
    @staticmethod
    def tag_string_address(address):
        """Tag an address as a string pointer by setting bit 0"""
        return address | 1
    
    @staticmethod
    def untag_string_address(address):
        """Remove string tag to get actual pointer"""
        return address & ~1
    
    @staticmethod
    def is_string_address(address):
        """Check if address is tagged as string (odd)"""
        return address & 1 == 1
    
    @staticmethod
    def ensure_number(value):
        """Ensure value is tagged as number (even)"""
        return value & ~1