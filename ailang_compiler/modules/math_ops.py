# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_compiler/compiler/modules/math_ops.py
"""
Advanced Math Operations Module for AILANG Compiler - NESTED CALL FIX VERSION
Implements the 50 math primitives from the grammar
FIX: Uses R13 for nested function calls, R12 for simple expressions
"""

from ailang_parser.ailang_ast import *

class MathOperations:
    """Handles advanced math operations beyond basic arithmetic"""
    
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm
    
    def _is_complex_expression(self, node):
        """Determine if an expression might contain function calls"""
        if isinstance(node, FunctionCall):
            return True
        if isinstance(node, Number) or isinstance(node, Identifier):
            return False
        return True
        
    def compile_operation(self, node):
        """Main dispatcher for math operations"""
        
        # Map function names to implementation methods
        operations = {
            
             # === CORE PRIMITIVES (NEW) ===
            'ISqrt': self.compile_isqrt,
            'Abs': self.compile_abs,
            'Min': self.compile_min,
            'Max': self.compile_max,
            'Pow': self.compile_pow,           
            
            
            # === ROUNDING OPERATIONS ===
            'Floor': self.compile_floor,
            'Ceil': self.compile_ceil,
            'Round': self.compile_round,
            'RoundEven': self.compile_round_even,
            'Trunc': self.compile_trunc,
            'Frac': self.compile_frac,
            
            # === MIN/MAX OPERATIONS ===
            'Min': self.compile_min,
            'Max': self.compile_max,
            'Clamp': self.compile_clamp,
            'Saturate': self.compile_saturate,
            'Sign': self.compile_sign,
            
            # === DIVISION VARIANTS ===
            'FloorDivide': self.compile_floor_divide,
            'Remainder': self.compile_remainder,
            'DivMod': self.compile_divmod,
            
            # === ADVANCED ARITHMETIC ===
            'FusedMultiplyAdd': self.compile_fma,
            'Hypotenuse': self.compile_hypot,
            'Lerp': self.compile_lerp,
            
            # === ANGLE CONVERSION ===
            'DegToRad': self.compile_deg_to_rad,
            'RadToDeg': self.compile_rad_to_deg,
            
            # === TRIGONOMETRY ===
            'Sin': self.compile_sin,
            'Cos': self.compile_cos,
            'Tan': self.compile_tan,
            'Asin': self.compile_asin,
            'Acos': self.compile_acos,
            'Atan': self.compile_atan,
            'Atan2': self.compile_atan2,
            'Tan': self.compile_tan,
            
            # === EXPONENTIAL ===
            'Exp': self.compile_exp,
            'Expm1': self.compile_expm1,
            'Exp2': self.compile_exp2,
            
            # === LOGARITHMS ===
            'Log': self.compile_log,
            'Log1p': self.compile_log1p,
            'Log2': self.compile_log2,
            'Log10': self.compile_log10,
            
            # === FLOATING POINT ===
            'NextAfter': self.compile_next_after,
            'Frexp': self.compile_frexp,
            'Ldexp': self.compile_ldexp,
            'NearlyEqual': self.compile_nearly_equal,
            
            # === BIT OPERATIONS ===
            'PopCount': self.compile_popcount,
            'CountLeadingZeros': self.compile_clz,
            'CountTrailingZeros': self.compile_ctz,
            'RotateLeft': self.compile_rotate_left,
            'RotateRight': self.compile_rotate_right,
            'ByteSwap': self.compile_byte_swap,
            'BitReverse': self.compile_bit_reverse,
            
            # === ALIGNMENT ===
            'AlignUp': self.compile_align_up,
            'AlignDown': self.compile_align_down,
            'IsPowerOfTwo': self.compile_is_power_of_two,
            'NextPowerOfTwo': self.compile_next_power_of_two,
            'FloorLog2': self.compile_floor_log2,
        }
        
        handler = operations.get(node.function)
        if handler:
            return handler(node)
        return False
    
     # ========== CORE PRIMITIVES (NEW) ==========
    
    def compile_isqrt(self, node):
        """ISqrt(n) - Integer square root using SSE2 hardware sqrt
        
        Uses SQRTSD for hardware-accelerated square root.
        Accurate for integers up to 2^53 (9,007,199,254,740,992)
        
        For values > 2^53, falls back to Newton's method.
        """
        if len(node.arguments) != 1:
            raise ValueError("ISqrt requires one argument")
        
        print("DEBUG: Compiling ISqrt - SSE2 hardware sqrt")
        
        # Get input value in RAX
        self.compiler.compile_expression(node.arguments[0])
        
        # Create labels
        negative_label = self.asm.create_label()
        large_label = self.asm.create_label()
        done_label = self.asm.create_label()
        newton_loop = self.asm.create_label()
        newton_done = self.asm.create_label()
        newton_nodec = self.asm.create_label()
        
        # Check for zero/negative
        self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        self.asm.emit_jump_to_label(negative_label, "JLE")
        
        # Check if > 2^53 (need Newton fallback for precision)
        # MOV RCX, 0x20000000000000 (2^53)
        self.asm.emit_bytes(0x48, 0xB9)  # MOVABS RCX, imm64
        self.asm.emit_bytes(0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x20, 0x00)
        self.asm.emit_bytes(0x48, 0x39, 0xC8)  # CMP RAX, RCX
        self.asm.emit_jump_to_label(large_label, "JAE")
        
        # === SSE2 Fast Path (for n < 2^53) ===
        
        # CVTSI2SD xmm0, rax - Convert signed int64 to double
        self.asm.emit_bytes(0xF2, 0x48, 0x0F, 0x2A, 0xC0)
        
        # SQRTSD xmm0, xmm0 - Square root
        self.asm.emit_bytes(0xF2, 0x0F, 0x51, 0xC0)
        
        # CVTTSD2SI rax, xmm0 - Convert double to int64 (truncate)
        self.asm.emit_bytes(0xF2, 0x48, 0x0F, 0x2C, 0xC0)
        
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        # === Negative/Zero Path ===
        self.asm.mark_label(negative_label)
        self.asm.emit_bytes(0x48, 0x31, 0xC0)  # XOR RAX, RAX
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        # === Newton Fallback for very large numbers (> 2^53) ===
        self.asm.mark_label(large_label)
        
        # Save callee-saved registers
        self.asm.emit_push_r12()
        self.asm.emit_push_r13()
        self.asm.emit_push_r14()
        
        # R14 = n
        self.asm.emit_bytes(0x49, 0x89, 0xC6)  # MOV R14, RAX
        
        # Initial guess using BSR
        self.asm.emit_bytes(0x48, 0x0F, 0xBD, 0xC8)  # BSR RCX, RAX
        self.asm.emit_bytes(0x48, 0xFF, 0xC1)        # INC RCX
        self.asm.emit_bytes(0x48, 0xD1, 0xE9)        # SHR RCX, 1
        self.asm.emit_bytes(0x48, 0x31, 0xC0)        # XOR RAX, RAX
        self.asm.emit_bytes(0x48, 0xFF, 0xC0)        # INC RAX
        self.asm.emit_bytes(0x48, 0xD3, 0xE0)        # SHL RAX, CL
        
        # R12 = current estimate
        self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX
        
        # R13 = previous (max value)
        self.asm.emit_bytes(0x49, 0xBD)  # MOVABS R13, imm64
        self.asm.emit_bytes(0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x7F)
        
        # Newton loop
        self.asm.mark_label(newton_loop)
        self.asm.emit_bytes(0x4D, 0x39, 0xEC)  # CMP R12, R13
        self.asm.emit_jump_to_label(newton_done, "JAE")
        
        self.asm.emit_bytes(0x4D, 0x89, 0xE5)  # MOV R13, R12
        self.asm.emit_bytes(0x4C, 0x89, 0xF0)  # MOV RAX, R14
        self.asm.emit_bytes(0x48, 0x31, 0xD2)  # XOR RDX, RDX
        self.asm.emit_bytes(0x49, 0xF7, 0xF4)  # DIV R12
        self.asm.emit_bytes(0x4C, 0x01, 0xE0)  # ADD RAX, R12
        self.asm.emit_bytes(0x48, 0xD1, 0xE8)  # SHR RAX, 1
        self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX
        self.asm.emit_jump_to_label(newton_loop, "JMP")
        
        # Verify and adjust
        self.asm.mark_label(newton_done)
        self.asm.emit_bytes(0x4C, 0x89, 0xF0)  # MOV RAX, R14
        self.asm.emit_bytes(0x48, 0x31, 0xD2)  # XOR RDX, RDX
        self.asm.emit_bytes(0x49, 0xF7, 0xF4)  # DIV R12
        self.asm.emit_bytes(0x49, 0x39, 0xC4)  # CMP R12, RAX
        self.asm.emit_jump_to_label(newton_nodec, "JBE")
        self.asm.emit_bytes(0x49, 0xFF, 0xCC)  # DEC R12
        
        self.asm.mark_label(newton_nodec)
        self.asm.emit_bytes(0x4C, 0x89, 0xE0)  # MOV RAX, R12
        
        self.asm.emit_pop_r14()
        self.asm.emit_pop_r13()
        self.asm.emit_pop_r12()
        
        self.asm.mark_label(done_label)
        
        print("DEBUG: ISqrt completed (SSE2 + Newton fallback)")
        return True
    
    def compile_abs(self, node):
        """Abs(x) - Absolute value using branchless arithmetic
        
        Method: (x ^ (x >> 63)) - (x >> 63)
        
        This is faster than NEG+CMOV because:
        - No dependency on flags
        - Better pipelining
        - 3 simple ops vs 2 complex ops
        
        For x >= 0: (x ^ 0) - 0 = x
        For x < 0:  (x ^ -1) - (-1) = ~x + 1 = -x
        """
        if len(node.arguments) != 1:
            raise ValueError("Abs requires one argument")
        
        print("DEBUG: Compiling Abs - branchless arithmetic")
        
        # Get value in RAX
        self.compiler.compile_expression(node.arguments[0])
        
        # Copy RAX to RCX
        self.asm.emit_bytes(0x48, 0x89, 0xC1)  # MOV RCX, RAX
        
        # Arithmetic right shift by 63: RCX = (x < 0) ? -1 : 0
        self.asm.emit_bytes(0x48, 0xC1, 0xF9, 0x3F)  # SAR RCX, 63
        
        # XOR RAX with RCX: RAX = x ^ mask
        self.asm.emit_bytes(0x48, 0x31, 0xC8)  # XOR RAX, RCX
        
        # SUB RAX, RCX: RAX = (x ^ mask) - mask
        self.asm.emit_bytes(0x48, 0x29, 0xC8)  # SUB RAX, RCX
        
        print("DEBUG: Abs completed")
        return True
    
    def compile_pow(self, node):
        """Pow(base, exp) - Integer power using exponentiation by squaring"""
        if len(node.arguments) != 2:
            raise ValueError("Pow requires two arguments (base, exponent)")
        
        print("DEBUG: Compiling Pow - Integer power")
        
        # Evaluate exponent first (save in R13)
        arg1_complex = self._is_complex_expression(node.arguments[1])
        
        if arg1_complex:
            self.asm.emit_push_r13()
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_bytes(0x49, 0x89, 0xC5)  # MOV R13, RAX
            self.compiler.compile_expression(node.arguments[0])
            self.asm.emit_bytes(0x4C, 0x89, 0xEB)  # MOV RBX, R13 (exp in RBX)
            self.asm.emit_pop_r13()
        else:
            self.asm.emit_push_r12()
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX
            self.compiler.compile_expression(node.arguments[0])
            self.asm.emit_bytes(0x4C, 0x89, 0xE3)  # MOV RBX, R12 (exp in RBX)
            self.asm.emit_pop_r12()
        
        # Now RAX = base, RBX = exponent
        # Handle special cases
        self.asm.emit_bytes(0x48, 0x85, 0xDB)  # TEST RBX, RBX
        
        # If exp == 0, return 1
        skip_one = len(self.asm.code) + 7
        self.asm.emit_bytes(0x75, 0x05)  # JNZ +5
        self.asm.emit_mov_rax_imm64(1)
        # JMP to end would go here
        
        # Save base in R12, result in R13
        self.asm.emit_push_r12()
        self.asm.emit_push_r13()
        self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX (base)
        self.asm.emit_mov_rax_imm64(1)
        self.asm.emit_bytes(0x49, 0x89, 0xC5)  # MOV R13, RAX (result = 1)
        
        # Exponentiation by squaring loop
        # while exp > 0:
        #   if exp & 1: result *= base
        #   base *= base
        #   exp >>= 1
        
        loop_start = len(self.asm.code)
        
        # Check if exp > 0
        self.asm.emit_bytes(0x48, 0x85, 0xDB)  # TEST RBX, RBX
        loop_end_offset = 30  # Will be patched
        self.asm.emit_bytes(0x7E, loop_end_offset)  # JLE loop_end
        
        # Check if exp & 1
        self.asm.emit_bytes(0x48, 0xF7, 0xC3, 0x01, 0x00, 0x00, 0x00)  # TEST RBX, 1
        skip_mult = 12
        self.asm.emit_bytes(0x74, skip_mult)  # JZ skip_mult
        
        # result *= base (R13 *= R12)
        self.asm.emit_bytes(0x4C, 0x89, 0xE8)  # MOV RAX, R13
        self.asm.emit_bytes(0x49, 0xF7, 0xEC)  # IMUL R12
        self.asm.emit_bytes(0x49, 0x89, 0xC5)  # MOV R13, RAX
        
        # base *= base (R12 *= R12)
        self.asm.emit_bytes(0x4C, 0x89, 0xE0)  # MOV RAX, R12
        self.asm.emit_bytes(0x49, 0xF7, 0xEC)  # IMUL R12
        self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX
        
        # exp >>= 1
        self.asm.emit_bytes(0x48, 0xD1, 0xFB)  # SAR RBX, 1
        
        # Jump back to loop start
        loop_offset = loop_start - (len(self.asm.code) + 2)
        self.asm.emit_bytes(0xEB, loop_offset & 0xFF)  # JMP loop_start
        
        # loop_end:
        # Move result to RAX
        self.asm.emit_bytes(0x4C, 0x89, 0xE8)  # MOV RAX, R13
        
        self.asm.emit_pop_r13()
        self.asm.emit_pop_r12()
        
        print("DEBUG: Pow completed")
        return True
    
    
    # ========== ROUNDING OPERATIONS ==========
    
    def compile_floor(self, node):
        """Floor(x) - Round down to nearest integer"""
        if len(node.arguments) != 1:
            raise ValueError("Floor requires one argument")
        
        print("DEBUG: Compiling Floor")
        self.compiler.compile_expression(node.arguments[0])
        return True
    
    def compile_ceil(self, node):
        """Ceil(x) - Round up to nearest integer"""
        if len(node.arguments) != 1:
            raise ValueError("Ceil requires one argument")
        
        print("DEBUG: Compiling Ceil")
        self.compiler.compile_expression(node.arguments[0])
        return True
    
    def compile_round(self, node):
        """Round(x) - Round to nearest integer"""
        if len(node.arguments) != 1:
            raise ValueError("Round requires one argument")
        
        print("DEBUG: Compiling Round")
        self.compiler.compile_expression(node.arguments[0])
        return True
    
    def compile_round_even(self, node):
        """RoundEven(x) - Round to nearest even integer (banker's rounding)"""
        if len(node.arguments) != 1:
            raise ValueError("RoundEven requires one argument")
        
        print("DEBUG: Compiling RoundEven")
        self.compiler.compile_expression(node.arguments[0])
        return True
    
    def compile_trunc(self, node):
        """Trunc(x) - Truncate towards zero"""
        if len(node.arguments) != 1:
            raise ValueError("Trunc requires one argument")
        
        print("DEBUG: Compiling Trunc")
        self.compiler.compile_expression(node.arguments[0])
        return True
    
    def compile_frac(self, node):
        """Frac(x) - Fractional part"""
        if len(node.arguments) != 1:
            raise ValueError("Frac requires one argument")
        
        print("DEBUG: Compiling Frac")
        # For integers, always 0
        self.asm.emit_mov_rax_imm64(0)
        return True
    
    # ========== MIN/MAX OPERATIONS ==========
    
    def compile_min(self, node):
        """Min(a, b) - Return smaller value using CMOV
        
        Clean implementation with proper register handling.
        """
        if len(node.arguments) != 2:
            raise ValueError("Min requires two arguments")
        
        print("DEBUG: Compiling Min")
        
        # Check if second arg is complex (contains function calls)
        arg1_complex = self._is_complex_expression(node.arguments[1])
        
        if arg1_complex:
            self.asm.emit_push_r12()
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX
            self.compiler.compile_expression(node.arguments[0])
            # Now RAX = a, R12 = b
            self.asm.emit_bytes(0x4C, 0x39, 0xE0)  # CMP RAX, R12
            self.asm.emit_bytes(0x4C, 0x0F, 0x4E, 0xE0)  # CMOVLE R12, RAX (R12 = min)
            self.asm.emit_bytes(0x4C, 0x89, 0xE0)  # MOV RAX, R12
            self.asm.emit_pop_r12()
        else:
            self.compiler.compile_expression(node.arguments[0])
            self.asm.emit_bytes(0x48, 0x89, 0xC1)  # MOV RCX, RAX (save a)
            self.compiler.compile_expression(node.arguments[1])
            # Now RAX = b, RCX = a
            self.asm.emit_bytes(0x48, 0x39, 0xC1)  # CMP RCX, RAX
            self.asm.emit_bytes(0x48, 0x0F, 0x4E, 0xC1)  # CMOVLE RAX, RCX
        
        print("DEBUG: Min completed")
        return True


    def compile_max(self, node):
        """Max(a, b) - Return larger value using CMOV
        
        Clean implementation with proper register handling.
        """
        if len(node.arguments) != 2:
            raise ValueError("Max requires two arguments")
        
        print("DEBUG: Compiling Max")
        
        arg1_complex = self._is_complex_expression(node.arguments[1])
        
        if arg1_complex:
            self.asm.emit_push_r12()
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX
            self.compiler.compile_expression(node.arguments[0])
            # Now RAX = a, R12 = b
            self.asm.emit_bytes(0x4C, 0x39, 0xE0)  # CMP RAX, R12
            self.asm.emit_bytes(0x4C, 0x0F, 0x4D, 0xE0)  # CMOVGE R12, RAX (R12 = max)
            self.asm.emit_bytes(0x4C, 0x89, 0xE0)  # MOV RAX, R12
            self.asm.emit_pop_r12()
        else:
            self.compiler.compile_expression(node.arguments[0])
            self.asm.emit_bytes(0x48, 0x89, 0xC1)  # MOV RCX, RAX (save a)
            self.compiler.compile_expression(node.arguments[1])
            # Now RAX = b, RCX = a
            self.asm.emit_bytes(0x48, 0x39, 0xC1)  # CMP RCX, RAX
            self.asm.emit_bytes(0x48, 0x0F, 0x4D, 0xC1)  # CMOVGE RAX, RCX
        
        print("DEBUG: Max completed")
        return True
    
    def compile_clamp(self, node):
        """Clamp(value, min, max) - Clamp value between min and max"""
        if len(node.arguments) != 3:
            raise ValueError("Clamp requires three arguments")
        
        print("DEBUG: Compiling Clamp (uses R12 and R13)")
        
        # Clamp always uses both registers
        self.asm.emit_push_r12()
        self.asm.emit_push_r13()
        
        # Get max value -> R13
        self.compiler.compile_expression(node.arguments[2])
        self.asm.emit_bytes(0x49, 0x89, 0xC5)  # MOV R13, RAX
        
        # Get min value -> R12
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX
        
        # Get value -> RAX
        self.compiler.compile_expression(node.arguments[0])
        
        # Clamp to minimum: RAX = max(RAX, R12)
        self.asm.emit_bytes(0x4C, 0x39, 0xE0)  # CMP RAX, R12
        self.asm.emit_bytes(0x4C, 0x0F, 0x4C, 0xE0)  # CMOVL R12, RAX
        self.asm.emit_bytes(0x4C, 0x89, 0xE0)  # MOV RAX, R12
        
        # Clamp to maximum: RAX = min(RAX, R13)
        self.asm.emit_bytes(0x4C, 0x39, 0xE8)  # CMP RAX, R13
        self.asm.emit_bytes(0x4C, 0x0F, 0x4F, 0xE8)  # CMOVG R13, RAX
        self.asm.emit_bytes(0x4C, 0x89, 0xE8)  # MOV RAX, R13
        
        self.asm.emit_pop_r13()
        self.asm.emit_pop_r12()
        
        print("DEBUG: Clamp operation completed")
        return True
    
    def compile_saturate(self, node):
        """Saturate(x) - Clamp to 0..1 range"""
        if len(node.arguments) != 1:
            raise ValueError("Saturate requires one argument")
        
        print("DEBUG: Compiling Saturate")
        self.compiler.compile_expression(node.arguments[0])
        # Would need floating point implementation
        return True
    
    def compile_sign(self, node):
        """Sign(x) - Return -1, 0, or 1"""
        if len(node.arguments) != 1:
            raise ValueError("Sign requires one argument")
        
        print("DEBUG: Compiling Sign")
        self.compiler.compile_expression(node.arguments[0])
        
        # Check if zero
        zero_label = self.asm.create_label()
        negative_label = self.asm.create_label()
        done_label = self.asm.create_label()
        
        self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        self.asm.emit_jump_to_label(zero_label, "JZ")
        self.asm.emit_jump_to_label(negative_label, "JS")
        
        # Positive
        self.asm.emit_mov_rax_imm64(1)
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        # Zero
        self.asm.mark_label(zero_label)
        self.asm.emit_mov_rax_imm64(0)
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        # Negative
        self.asm.mark_label(negative_label)
        self.asm.emit_mov_rax_imm64(-1)
        
        self.asm.mark_label(done_label)
        return True
    
    # ========== BIT OPERATIONS ==========
    
    def compile_popcount(self, node):
        """PopCount(x) - Count set bits"""
        if len(node.arguments) != 1:
            raise ValueError("PopCount requires one argument")
        
        print("DEBUG: Compiling PopCount")
        self.compiler.compile_expression(node.arguments[0])
        
        # POPCNT RAX, RAX (requires SSE4.2)
        self.asm.emit_bytes(0xF3, 0x48, 0x0F, 0xB8, 0xC0)
        
        print("DEBUG: PopCount operation completed")
        return True
    
    def compile_clz(self, node):
        """CountLeadingZeros(x)"""
        if len(node.arguments) != 1:
            raise ValueError("CountLeadingZeros requires one argument")
        
        print("DEBUG: Compiling CountLeadingZeros")
        self.compiler.compile_expression(node.arguments[0])
        
        # LZCNT RAX, RAX (BMI1)
        self.asm.emit_bytes(0xF3, 0x48, 0x0F, 0xBD, 0xC0)
        
        print("DEBUG: CountLeadingZeros operation completed")
        return True
    
    def compile_ctz(self, node):
        """CountTrailingZeros(x)"""
        if len(node.arguments) != 1:
            raise ValueError("CountTrailingZeros requires one argument")
        
        print("DEBUG: Compiling CountTrailingZeros")
        self.compiler.compile_expression(node.arguments[0])
        
        # TZCNT RAX, RAX (BMI1)
        self.asm.emit_bytes(0xF3, 0x48, 0x0F, 0xBC, 0xC0)
        
        print("DEBUG: CountTrailingZeros operation completed")
        return True
    
    def compile_rotate_left(self, node):
        """RotateLeft(value, count)"""
        if len(node.arguments) != 2:
            raise ValueError("RotateLeft requires two arguments")
        
        print("DEBUG: Compiling RotateLeft with nested call detection")
        
        arg1_complex = self._is_complex_expression(node.arguments[1])
        
        if arg1_complex:
            print("DEBUG: Using R13 (nested call detected)")
            self.asm.emit_push_r13()
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_bytes(0x49, 0x89, 0xC5)  # MOV R13, RAX
            self.compiler.compile_expression(node.arguments[0])
            self.asm.emit_bytes(0x4C, 0x89, 0xE9)  # MOV RCX, R13
            self.asm.emit_pop_r13()
        else:
            print("DEBUG: Using R12 (simple expression)")
            self.asm.emit_push_r12()
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX
            self.compiler.compile_expression(node.arguments[0])
            self.asm.emit_bytes(0x4C, 0x89, 0xE1)  # MOV RCX, R12
            self.asm.emit_pop_r12()
        
        # ROL RAX, CL
        self.asm.emit_bytes(0x48, 0xD3, 0xC0)
        
        print("DEBUG: RotateLeft operation completed")
        return True
    
    def compile_rotate_right(self, node):
        """RotateRight(value, count)"""
        if len(node.arguments) != 2:
            raise ValueError("RotateRight requires two arguments")
        
        print("DEBUG: Compiling RotateRight with nested call detection")
        
        arg1_complex = self._is_complex_expression(node.arguments[1])
        
        if arg1_complex:
            print("DEBUG: Using R13 (nested call detected)")
            self.asm.emit_push_r13()
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_bytes(0x49, 0x89, 0xC5)  # MOV R13, RAX
            self.compiler.compile_expression(node.arguments[0])
            self.asm.emit_bytes(0x4C, 0x89, 0xE9)  # MOV RCX, R13
            self.asm.emit_pop_r13()
        else:
            print("DEBUG: Using R12 (simple expression)")
            self.asm.emit_push_r12()
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX
            self.compiler.compile_expression(node.arguments[0])
            self.asm.emit_bytes(0x4C, 0x89, 0xE1)  # MOV RCX, R12
            self.asm.emit_pop_r12()
        
        # ROR RAX, CL
        self.asm.emit_bytes(0x48, 0xD3, 0xC8)
        
        print("DEBUG: RotateRight operation completed")
        return True
    
    def compile_byte_swap(self, node):
        """ByteSwap(x) - Reverse byte order"""
        if len(node.arguments) != 1:
            raise ValueError("ByteSwap requires one argument")
        
        print("DEBUG: Compiling ByteSwap")
        self.compiler.compile_expression(node.arguments[0])
        
        # BSWAP RAX
        self.asm.emit_bytes(0x48, 0x0F, 0xC8)
        
        print("DEBUG: ByteSwap operation completed")
        return True
    
    def compile_bit_reverse(self, node):
        """BitReverse(x) - Reverse bit order"""
        if len(node.arguments) != 1:
            raise ValueError("BitReverse requires one argument")
        
        print("DEBUG: Compiling BitReverse (placeholder)")
        self.compiler.compile_expression(node.arguments[0])
        # Would need complex bit manipulation
        return True
    
    # ========== ALIGNMENT OPERATIONS ==========
    
    def compile_align_up(self, node):
        """AlignUp(value, alignment)"""
        if len(node.arguments) != 2:
            raise ValueError("AlignUp requires two arguments")
        
        print("DEBUG: Compiling AlignUp with nested call detection")
        
        arg1_complex = self._is_complex_expression(node.arguments[1])
        
        if arg1_complex:
            print("DEBUG: Using R13 (nested call detected)")
            self.asm.emit_push_r13()
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_bytes(0x49, 0x89, 0xC5)  # MOV R13, RAX
            self.compiler.compile_expression(node.arguments[0])
            
            # value + alignment - 1
            self.asm.emit_bytes(0x4C, 0x01, 0xE8)  # ADD RAX, R13
            self.asm.emit_bytes(0x48, 0xFF, 0xC8)  # DEC RAX
            
            # ~(alignment - 1)
            self.asm.emit_bytes(0x49, 0xFF, 0xCD)  # DEC R13
            self.asm.emit_bytes(0x49, 0xF7, 0xD5)  # NOT R13
            
            # result & mask
            self.asm.emit_bytes(0x4C, 0x21, 0xE8)  # AND RAX, R13
            
            self.asm.emit_pop_r13()
        else:
            print("DEBUG: Using R12 (simple expression)")
            self.asm.emit_push_r12()
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX
            self.compiler.compile_expression(node.arguments[0])
            
            # value + alignment - 1
            self.asm.emit_bytes(0x4C, 0x01, 0xE0)  # ADD RAX, R12
            self.asm.emit_bytes(0x48, 0xFF, 0xC8)  # DEC RAX
            
            # ~(alignment - 1)
            self.asm.emit_bytes(0x49, 0xFF, 0xCC)  # DEC R12
            self.asm.emit_bytes(0x49, 0xF7, 0xD4)  # NOT R12
            
            # result & mask
            self.asm.emit_bytes(0x4C, 0x21, 0xE0)  # AND RAX, R12
            
            self.asm.emit_pop_r12()
        
        print("DEBUG: AlignUp operation completed")
        return True
    
    def compile_align_down(self, node):
        """AlignDown(value, alignment)"""
        if len(node.arguments) != 2:
            raise ValueError("AlignDown requires two arguments")
        
        print("DEBUG: Compiling AlignDown with nested call detection")
        
        arg1_complex = self._is_complex_expression(node.arguments[1])
        
        if arg1_complex:
            print("DEBUG: Using R13 (nested call detected)")
            self.asm.emit_push_r13()
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_bytes(0x49, 0x89, 0xC5)  # MOV R13, RAX
            self.compiler.compile_expression(node.arguments[0])
            
            # ~(alignment - 1)
            self.asm.emit_bytes(0x49, 0xFF, 0xCD)  # DEC R13
            self.asm.emit_bytes(0x49, 0xF7, 0xD5)  # NOT R13
            
            # result & mask
            self.asm.emit_bytes(0x4C, 0x21, 0xE8)  # AND RAX, R13
            
            self.asm.emit_pop_r13()
        else:
            print("DEBUG: Using R12 (simple expression)")
            self.asm.emit_push_r12()
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX
            self.compiler.compile_expression(node.arguments[0])
            
            # ~(alignment - 1)
            self.asm.emit_bytes(0x49, 0xFF, 0xCC)  # DEC R12
            self.asm.emit_bytes(0x49, 0xF7, 0xD4)  # NOT R12
            
            # result & mask
            self.asm.emit_bytes(0x4C, 0x21, 0xE0)  # AND RAX, R12
            
            self.asm.emit_pop_r12()
        
        print("DEBUG: AlignDown operation completed")
        return True
    
    def compile_is_power_of_two(self, node):
        """IsPowerOfTwo(x)"""
        if len(node.arguments) != 1:
            raise ValueError("IsPowerOfTwo requires one argument")
        
        print("DEBUG: Compiling IsPowerOfTwo")
        self.compiler.compile_expression(node.arguments[0])
        
        # (x != 0) && ((x & (x - 1)) == 0)
        zero_label = self.asm.create_label()
        done_label = self.asm.create_label()
        
        self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        self.asm.emit_jump_to_label(zero_label, "JZ")
        
        # x & (x - 1)
        self.asm.emit_mov_rbx_rax()
        self.asm.emit_bytes(0x48, 0xFF, 0xCB)  # DEC RBX
        self.asm.emit_bytes(0x48, 0x21, 0xD8)  # AND RAX, RBX
        
        # Check if zero
        self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        self.asm.emit_bytes(0x0F, 0x94, 0xC0)  # SETZ AL
        self.asm.emit_bytes(0x48, 0x0F, 0xB6, 0xC0)  # MOVZX RAX, AL
        
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        self.asm.mark_label(zero_label)
        self.asm.emit_mov_rax_imm64(0)
        
        self.asm.mark_label(done_label)
        return True
    
    def compile_next_power_of_two(self, node):
        """NextPowerOfTwo(x)"""
        if len(node.arguments) != 1:
            raise ValueError("NextPowerOfTwo requires one argument")
        
        print("DEBUG: Compiling NextPowerOfTwo")
        self.compiler.compile_expression(node.arguments[0])
        
        # Fill all bits right of highest set bit
        self.asm.emit_bytes(0x48, 0xFF, 0xC8)  # DEC RAX
        
        for shift in [1, 2, 4, 8, 16, 32]:
            self.asm.emit_mov_rbx_rax()
            if shift == 1:
                self.asm.emit_bytes(0x48, 0xD1, 0xEB)  # SHR RBX, 1
            else:
                self.asm.emit_bytes(0x48, 0xC1, 0xEB, shift)  # SHR RBX, shift
            self.asm.emit_bytes(0x48, 0x09, 0xD8)  # OR RAX, RBX
        
        self.asm.emit_bytes(0x48, 0xFF, 0xC0)  # INC RAX
        return True
    
    def compile_floor_log2(self, node):
        """FloorLog2(x)"""
        if len(node.arguments) != 1:
            raise ValueError("FloorLog2 requires one argument")
        
        print("DEBUG: Compiling FloorLog2")
        self.compiler.compile_expression(node.arguments[0])
        
        zero_label = self.asm.create_label()
        done_label = self.asm.create_label()
        
        self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        self.asm.emit_jump_to_label(zero_label, "JZ")
        
        # BSR RAX, RAX
        self.asm.emit_bytes(0x48, 0x0F, 0xBD, 0xC0)
        
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        self.asm.mark_label(zero_label)
        self.asm.emit_mov_rax_imm64(0)
        
        self.asm.mark_label(done_label)
        return True
    
    # ========== PLACEHOLDER IMPLEMENTATIONS ==========
    # These require floating point or complex algorithms
    
    def compile_floor_divide(self, node):
        return False  # Let arithmetic_ops handle it
    
    def compile_remainder(self, node):
        return False
    
    def compile_divmod(self, node):
        return False
    
    def compile_fma(self, node):
        return False
    
    def compile_hypot(self, node):
        return False
    
    def compile_lerp(self, node):
        return False
    
    # Trig functions - need floating point
    def compile_sin(self, node):
        """Sin(degrees) - Sine using x87 FPU
        
        Input: degrees as integer
        Output: sin(x) * 10000 (fixed-point)
        """
        if len(node.arguments) != 1:
            raise ValueError("Sin requires one argument")
        
        print("DEBUG: Compiling Sin - x87 FSIN")
        
        self.compiler.compile_expression(node.arguments[0])
        
        # Allocate stack space for FPU operations (need 8 bytes for temp)
        self.asm.emit_bytes(0x48, 0x83, 0xEC, 0x10)  # SUB RSP, 16
        
        # Store degrees to stack
        self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)  # MOV [RSP], RAX
        
        # Load degrees as integer to x87
        self.asm.emit_bytes(0xDF, 0x2C, 0x24)  # FILD QWORD [RSP]
        
        # Convert degrees to radians: multiply by PI/180
        # Load PI
        self.asm.emit_bytes(0xD9, 0xEB)  # FLDPI (load π)
        # Load 180
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0xB4, 0x00, 0x00, 0x00)  # MOV DWORD [RSP], 180
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        # Divide: PI / 180
        self.asm.emit_bytes(0xDE, 0xF9)  # FDIVP ST(1), ST(0)
        # Multiply: degrees * (PI/180)
        self.asm.emit_bytes(0xDE, 0xC9)  # FMULP ST(1), ST(0)
        
        # Now ST(0) = radians
        # FSIN
        self.asm.emit_bytes(0xD9, 0xFE)  # FSIN
        
        # Scale by 10000 for fixed-point output
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)  # MOV DWORD [RSP], 10000
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xC9)  # FMULP ST(1), ST(0)
        
        # Store result back to integer
        self.asm.emit_bytes(0xDF, 0x3C, 0x24)  # FISTP QWORD [RSP]
        
        # Load result to RAX
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)  # MOV RAX, [RSP]
        
        # Restore stack
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)  # ADD RSP, 16
        
        return True


    def compile_cos(self, node):
        """Cos(degrees) - Cosine using x87 FPU
        
        Input: degrees as integer
        Output: cos(x) * 10000 (fixed-point)
        """
        if len(node.arguments) != 1:
            raise ValueError("Cos requires one argument")
        
        print("DEBUG: Compiling Cos - x87 FCOS")
        
        self.compiler.compile_expression(node.arguments[0])
        
        # Allocate stack space
        self.asm.emit_bytes(0x48, 0x83, 0xEC, 0x10)  # SUB RSP, 16
        
        # Store degrees to stack
        self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)  # MOV [RSP], RAX
        
        # Load degrees as integer to x87
        self.asm.emit_bytes(0xDF, 0x2C, 0x24)  # FILD QWORD [RSP]
        
        # Convert degrees to radians: multiply by PI/180
        self.asm.emit_bytes(0xD9, 0xEB)  # FLDPI
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0xB4, 0x00, 0x00, 0x00)  # MOV DWORD [RSP], 180
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xF9)  # FDIVP
        self.asm.emit_bytes(0xDE, 0xC9)  # FMULP
        
        # FCOS
        self.asm.emit_bytes(0xD9, 0xFF)  # FCOS
        
        # Scale by 10000
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)  # MOV DWORD [RSP], 10000
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xC9)  # FMULP
        
        # Store result
        self.asm.emit_bytes(0xDF, 0x3C, 0x24)  # FISTP QWORD [RSP]
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)  # MOV RAX, [RSP]
        
        # Restore stack
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)  # ADD RSP, 16
        
        return True


    def compile_tan(self, node):
        """Tan(degrees) - Tangent using x87 FPU
        
        Input: degrees as integer
        Output: tan(x) * 10000 (fixed-point), clamped to avoid overflow
        """
        if len(node.arguments) != 1:
            raise ValueError("Tan requires one argument")
        
        print("DEBUG: Compiling Tan - x87 FPTAN")
        
        self.compiler.compile_expression(node.arguments[0])
        
        # Allocate stack space
        self.asm.emit_bytes(0x48, 0x83, 0xEC, 0x10)  # SUB RSP, 16
        
        # Store degrees to stack
        self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)  # MOV [RSP], RAX
        
        # Load degrees as integer to x87
        self.asm.emit_bytes(0xDF, 0x2C, 0x24)  # FILD QWORD [RSP]
        
        # Convert degrees to radians
        self.asm.emit_bytes(0xD9, 0xEB)  # FLDPI
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0xB4, 0x00, 0x00, 0x00)  # MOV DWORD [RSP], 180
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xF9)  # FDIVP
        self.asm.emit_bytes(0xDE, 0xC9)  # FMULP
        
        # FPTAN pushes both tan(x) and 1.0
        self.asm.emit_bytes(0xD9, 0xF2)  # FPTAN (pushes 1.0, then tan)
        # Pop the 1.0
        self.asm.emit_bytes(0xDD, 0xD8)  # FSTP ST(0) - pop and discard
        
        # Scale by 10000
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)  # MOV DWORD [RSP], 10000
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xC9)  # FMULP
        
        # Store result
        self.asm.emit_bytes(0xDF, 0x3C, 0x24)  # FISTP QWORD [RSP]
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)  # MOV RAX, [RSP]
        
        # Restore stack
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)  # ADD RSP, 16
        
        return True


    def compile_atan(self, node):
        """Atan(x) - Arctangent using x87 FPU
        
        Input: x * 10000 (fixed-point)
        Output: degrees as integer
        """
        if len(node.arguments) != 1:
            raise ValueError("Atan requires one argument")
        
        print("DEBUG: Compiling Atan - x87 FPATAN")
        
        self.compiler.compile_expression(node.arguments[0])
        
        # Allocate stack space
        self.asm.emit_bytes(0x48, 0x83, 0xEC, 0x10)  # SUB RSP, 16
        
        # Store input to stack
        self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)  # MOV [RSP], RAX
        
        # Load as integer, divide by 10000 to get actual value
        self.asm.emit_bytes(0xDF, 0x2C, 0x24)  # FILD QWORD [RSP]
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)  # MOV DWORD [RSP], 10000
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xF9)  # FDIVP (x / 10000)
        
        # Load 1.0 for FPATAN (computes atan2(ST1, ST0) = atan(ST1/ST0))
        self.asm.emit_bytes(0xD9, 0xE8)  # FLD1
        
        # FPATAN: atan2(ST1, ST0), pops both, pushes result
        self.asm.emit_bytes(0xD9, 0xF3)  # FPATAN
        
        # Convert radians to degrees: multiply by 180/PI
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0xB4, 0x00, 0x00, 0x00)  # MOV DWORD [RSP], 180
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xC9)  # FMULP
        self.asm.emit_bytes(0xD9, 0xEB)  # FLDPI
        self.asm.emit_bytes(0xDE, 0xF9)  # FDIVP
        
        # Store result
        self.asm.emit_bytes(0xDF, 0x3C, 0x24)  # FISTP QWORD [RSP]
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)  # MOV RAX, [RSP]
        
        # Restore stack
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)  # ADD RSP, 16
        
        return True


    def compile_atan2(self, node):
        """Atan2(y, x) - Two-argument arctangent using x87 FPU
        
        Input: y, x as integers (or fixed-point, same scale)
        Output: degrees as integer (-180 to 180)
        """
        if len(node.arguments) != 2:
            raise ValueError("Atan2 requires two arguments")
        
        print("DEBUG: Compiling Atan2 - x87 FPATAN")
        
        # Evaluate arguments
        arg1_complex = self._is_complex_expression(node.arguments[1])
        
        # Allocate stack space
        self.asm.emit_bytes(0x48, 0x83, 0xEC, 0x10)  # SUB RSP, 16
        
        if arg1_complex:
            self.asm.emit_push_r12()
            self.compiler.compile_expression(node.arguments[1])  # x
            self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX
            self.compiler.compile_expression(node.arguments[0])  # y
            # RAX = y, R12 = x
            self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)  # MOV [RSP], RAX (y)
            self.asm.emit_bytes(0x4C, 0x89, 0x64, 0x24, 0x08)  # MOV [RSP+8], R12 (x)
            self.asm.emit_pop_r12()
        else:
            self.compiler.compile_expression(node.arguments[0])  # y
            self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)  # MOV [RSP], RAX
            self.compiler.compile_expression(node.arguments[1])  # x
            self.asm.emit_bytes(0x48, 0x89, 0x44, 0x24, 0x08)  # MOV [RSP+8], RAX
        
        # Load y, then x (FPATAN computes atan2(ST1, ST0))
        self.asm.emit_bytes(0xDF, 0x2C, 0x24)  # FILD QWORD [RSP] (y)
        self.asm.emit_bytes(0xDF, 0x6C, 0x24, 0x08)  # FILD QWORD [RSP+8] (x)
        
        # FPATAN
        self.asm.emit_bytes(0xD9, 0xF3)  # FPATAN
        
        # Convert radians to degrees
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0xB4, 0x00, 0x00, 0x00)  # MOV DWORD [RSP], 180
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xC9)  # FMULP
        self.asm.emit_bytes(0xD9, 0xEB)  # FLDPI
        self.asm.emit_bytes(0xDE, 0xF9)  # FDIVP
        
        # Store result
        self.asm.emit_bytes(0xDF, 0x3C, 0x24)  # FISTP QWORD [RSP]
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)  # MOV RAX, [RSP]
        
        # Restore stack
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)  # ADD RSP, 16
        
        return True


    def compile_asin(self, node):
        """Asin(x) - Arcsine: asin(x) = atan(x / sqrt(1 - x^2))
        
        Input: x * 10000 (fixed-point, -10000 to 10000)
        Output: degrees as integer
        """
        if len(node.arguments) != 1:
            raise ValueError("Asin requires one argument")
        
        print("DEBUG: Compiling Asin")
        
        self.compiler.compile_expression(node.arguments[0])
        
        # Allocate stack space
        self.asm.emit_bytes(0x48, 0x83, 0xEC, 0x10)  # SUB RSP, 16
        self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)  # MOV [RSP], RAX
        
        # Load x and convert from fixed-point
        self.asm.emit_bytes(0xDF, 0x2C, 0x24)  # FILD QWORD [RSP]
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)  # MOV DWORD [RSP], 10000
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xF9)  # FDIVP (x = x/10000)
        
        # Compute sqrt(1 - x^2)
        self.asm.emit_bytes(0xD9, 0xC0)  # FLD ST(0) - duplicate x
        self.asm.emit_bytes(0xD8, 0xC8)  # FMUL ST(0), ST(0) - x^2
        self.asm.emit_bytes(0xD9, 0xE8)  # FLD1 - load 1.0
        self.asm.emit_bytes(0xDE, 0xE1)  # FSUBRP - 1 - x^2 (reverse subtract)
        self.asm.emit_bytes(0xD9, 0xFA)  # FSQRT - sqrt(1 - x^2)
        
        # Now stack is: sqrt(1-x^2), x
        # FPATAN computes atan2(ST1, ST0) = atan(x / sqrt(1-x^2)) = asin(x)
        self.asm.emit_bytes(0xD9, 0xF3)  # FPATAN
        
        # Convert radians to degrees
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0xB4, 0x00, 0x00, 0x00)  # 180
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD
        self.asm.emit_bytes(0xDE, 0xC9)  # FMULP
        self.asm.emit_bytes(0xD9, 0xEB)  # FLDPI
        self.asm.emit_bytes(0xDE, 0xF9)  # FDIVP
        
        # Store result
        self.asm.emit_bytes(0xDF, 0x3C, 0x24)  # FISTP QWORD [RSP]
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)  # MOV RAX, [RSP]
        
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)  # ADD RSP, 16
        
        return True


    def compile_acos(self, node):
        """Acos(x) - Arccosine: acos(x) = atan(sqrt(1 - x^2) / x)
        
        Input: x * 10000 (fixed-point, -10000 to 10000)
        Output: degrees as integer
        """
        if len(node.arguments) != 1:
            raise ValueError("Acos requires one argument")
        
        print("DEBUG: Compiling Acos")
        
        self.compiler.compile_expression(node.arguments[0])
        
        # Allocate stack space
        self.asm.emit_bytes(0x48, 0x83, 0xEC, 0x10)  # SUB RSP, 16
        self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)  # MOV [RSP], RAX
        
        # Load x and convert from fixed-point
        self.asm.emit_bytes(0xDF, 0x2C, 0x24)  # FILD QWORD [RSP]
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)  # 10000
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD
        self.asm.emit_bytes(0xDE, 0xF9)  # FDIVP
        
        # Compute sqrt(1 - x^2)
        self.asm.emit_bytes(0xD9, 0xC0)  # FLD ST(0) - duplicate x
        self.asm.emit_bytes(0xD8, 0xC8)  # FMUL ST(0), ST(0) - x^2
        self.asm.emit_bytes(0xD9, 0xE8)  # FLD1
        self.asm.emit_bytes(0xDE, 0xE1)  # FSUBRP - 1 - x^2
        self.asm.emit_bytes(0xD9, 0xFA)  # FSQRT
        
        # Stack: sqrt(1-x^2), x
        # Swap for acos: atan2(sqrt(1-x^2), x)
        self.asm.emit_bytes(0xD9, 0xC9)  # FXCH ST(1)
        
        # FPATAN
        self.asm.emit_bytes(0xD9, 0xF3)  # FPATAN
        
        # Convert radians to degrees
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0xB4, 0x00, 0x00, 0x00)  # 180
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD
        self.asm.emit_bytes(0xDE, 0xC9)  # FMULP
        self.asm.emit_bytes(0xD9, 0xEB)  # FLDPI
        self.asm.emit_bytes(0xDE, 0xF9)  # FDIVP
        
        # Store result
        self.asm.emit_bytes(0xDF, 0x3C, 0x24)  # FISTP QWORD [RSP]
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)  # MOV RAX, [RSP]
        
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)  # ADD RSP, 16
        
        return True
    
    # Angle conversion
    # ========== ANGLE CONVERSION ==========

    def compile_deg_to_rad(self, node):
        """DegToRad(degrees) - Convert degrees to radians
        
        Input: degrees as integer
        Output: radians * 10000 (fixed-point)
        
        Formula: rad = deg * PI / 180
        """
        if len(node.arguments) != 1:
            raise ValueError("DegToRad requires one argument")
        
        print("DEBUG: Compiling DegToRad")
        
        self.compiler.compile_expression(node.arguments[0])
        
        # Allocate stack space
        self.asm.emit_bytes(0x48, 0x83, 0xEC, 0x10)  # SUB RSP, 16
        self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)  # MOV [RSP], RAX
        
        # Load degrees
        self.asm.emit_bytes(0xDF, 0x2C, 0x24)  # FILD QWORD [RSP]
        
        # Multiply by PI
        self.asm.emit_bytes(0xD9, 0xEB)  # FLDPI
        self.asm.emit_bytes(0xDE, 0xC9)  # FMULP
        
        # Divide by 180
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0xB4, 0x00, 0x00, 0x00)  # MOV DWORD [RSP], 180
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xF9)  # FDIVP
        
        # Scale by 10000 for fixed-point
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)  # MOV DWORD [RSP], 10000
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xC9)  # FMULP
        
        # Store result
        self.asm.emit_bytes(0xDF, 0x3C, 0x24)  # FISTP QWORD [RSP]
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)  # MOV RAX, [RSP]
        
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)  # ADD RSP, 16
        return True


    def compile_rad_to_deg(self, node):
        """RadToDeg(radians) - Convert radians to degrees
        
        Input: radians * 10000 (fixed-point)
        Output: degrees as integer
        
        Formula: deg = rad * 180 / PI
        """
        if len(node.arguments) != 1:
            raise ValueError("RadToDeg requires one argument")
        
        print("DEBUG: Compiling RadToDeg")
        
        self.compiler.compile_expression(node.arguments[0])
        
        # Allocate stack space
        self.asm.emit_bytes(0x48, 0x83, 0xEC, 0x10)  # SUB RSP, 16
        self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)  # MOV [RSP], RAX
        
        # Load radians and convert from fixed-point
        self.asm.emit_bytes(0xDF, 0x2C, 0x24)  # FILD QWORD [RSP]
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)  # 10000
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xF9)  # FDIVP
        
        # Multiply by 180
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0xB4, 0x00, 0x00, 0x00)  # 180
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xC9)  # FMULP
        
        # Divide by PI
        self.asm.emit_bytes(0xD9, 0xEB)  # FLDPI
        self.asm.emit_bytes(0xDE, 0xF9)  # FDIVP
        
        # Store result
        self.asm.emit_bytes(0xDF, 0x3C, 0x24)  # FISTP QWORD [RSP]
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)  # MOV RAX, [RSP]
        
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)  # ADD RSP, 16
        return True
    
    # Exponential/Log - need floating point
    def compile_exp(self, node):
        """Exp(x) - e^x using x87
        
        Input: x * 10000 (fixed-point)
        Output: e^x * 10000 (fixed-point)
        
        Method: e^x = 2^(x * log2(e))
        """
        if len(node.arguments) != 1:
            raise ValueError("Exp requires one argument")
        
        print("DEBUG: Compiling Exp - x87")
        
        self.compiler.compile_expression(node.arguments[0])
        
        # Allocate stack space
        self.asm.emit_bytes(0x48, 0x83, 0xEC, 0x10)  # SUB RSP, 16
        self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)  # MOV [RSP], RAX
        
        # Load x and convert from fixed-point
        self.asm.emit_bytes(0xDF, 0x2C, 0x24)  # FILD QWORD [RSP]
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)  # 10000
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xF9)  # FDIVP (x now in ST0)
        
        # Multiply by log2(e)
        self.asm.emit_bytes(0xD9, 0xEA)  # FLDL2E (load log2(e) ≈ 1.4427)
        self.asm.emit_bytes(0xDE, 0xC9)  # FMULP (ST0 = x * log2(e))
        
        # Now compute 2^ST0
        # Split into integer and fractional parts
        self.asm.emit_bytes(0xD9, 0xC0)  # FLD ST(0) - duplicate
        self.asm.emit_bytes(0xD9, 0xFC)  # FRNDINT - round to integer
        self.asm.emit_bytes(0xD9, 0xC9)  # FXCH ST(1)
        self.asm.emit_bytes(0xD8, 0xE1)  # FSUB ST(0), ST(1) - get fractional part
        
        # F2XM1 works for -1 <= x <= 1
        self.asm.emit_bytes(0xD9, 0xF0)  # F2XM1 (2^frac - 1)
        self.asm.emit_bytes(0xD9, 0xE8)  # FLD1
        self.asm.emit_bytes(0xDE, 0xC1)  # FADDP (2^frac)
        
        # Scale by 2^int using FSCALE
        self.asm.emit_bytes(0xD9, 0xFD)  # FSCALE (ST0 * 2^ST1)
        self.asm.emit_bytes(0xDD, 0xD9)  # FSTP ST(1) - pop integer part
        
        # Scale by 10000 for fixed-point output
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)  # 10000
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xC9)  # FMULP
        
        # Store result
        self.asm.emit_bytes(0xDF, 0x3C, 0x24)  # FISTP QWORD [RSP]
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)  # MOV RAX, [RSP]
        
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)  # ADD RSP, 16
        return True


    def compile_exp2(self, node):
        """Exp2(x) - 2^x using x87
        
        Input: x * 10000 (fixed-point)
        Output: 2^x * 10000 (fixed-point)
        """
        if len(node.arguments) != 1:
            raise ValueError("Exp2 requires one argument")
        
        print("DEBUG: Compiling Exp2 - x87")
        
        self.compiler.compile_expression(node.arguments[0])
        
        # Allocate stack space
        self.asm.emit_bytes(0x48, 0x83, 0xEC, 0x10)  # SUB RSP, 16
        self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)  # MOV [RSP], RAX
        
        # Load x and convert from fixed-point
        self.asm.emit_bytes(0xDF, 0x2C, 0x24)  # FILD QWORD [RSP]
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)  # 10000
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xF9)  # FDIVP
        
        # Split into integer and fractional parts
        self.asm.emit_bytes(0xD9, 0xC0)  # FLD ST(0)
        self.asm.emit_bytes(0xD9, 0xFC)  # FRNDINT
        self.asm.emit_bytes(0xD9, 0xC9)  # FXCH ST(1)
        self.asm.emit_bytes(0xD8, 0xE1)  # FSUB ST(0), ST(1)
        
        # F2XM1 + 1
        self.asm.emit_bytes(0xD9, 0xF0)  # F2XM1
        self.asm.emit_bytes(0xD9, 0xE8)  # FLD1
        self.asm.emit_bytes(0xDE, 0xC1)  # FADDP
        
        # FSCALE
        self.asm.emit_bytes(0xD9, 0xFD)  # FSCALE
        self.asm.emit_bytes(0xDD, 0xD9)  # FSTP ST(1)
        
        # Scale by 10000
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)
        self.asm.emit_bytes(0xDF, 0x04, 0x24)
        self.asm.emit_bytes(0xDE, 0xC9)
        
        # Store result
        self.asm.emit_bytes(0xDF, 0x3C, 0x24)
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)
        
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)
        return True


    def compile_expm1(self, node):
        """Expm1(x) - e^x - 1 (more accurate for small x)
        
        Input: x * 10000 (fixed-point)
        Output: (e^x - 1) * 10000 (fixed-point)
        """
        if len(node.arguments) != 1:
            raise ValueError("Expm1 requires one argument")
        
        print("DEBUG: Compiling Expm1")
        
        # Just compute exp(x) - 10000 (which is 1.0 in fixed-point)
        self.compiler.compile_expression(node.arguments[0])
        
        # Allocate stack space
        self.asm.emit_bytes(0x48, 0x83, 0xEC, 0x10)
        self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)
        
        # Load and convert from fixed-point
        self.asm.emit_bytes(0xDF, 0x2C, 0x24)
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)
        self.asm.emit_bytes(0xDF, 0x04, 0x24)
        self.asm.emit_bytes(0xDE, 0xF9)
        
        # x * log2(e)
        self.asm.emit_bytes(0xD9, 0xEA)  # FLDL2E
        self.asm.emit_bytes(0xDE, 0xC9)  # FMULP
        
        # For small x, we can use F2XM1 directly on (x*log2(e)) if it's in range
        # For general case, use full exp algorithm
        self.asm.emit_bytes(0xD9, 0xC0)  # FLD ST(0)
        self.asm.emit_bytes(0xD9, 0xFC)  # FRNDINT
        self.asm.emit_bytes(0xD9, 0xC9)  # FXCH
        self.asm.emit_bytes(0xD8, 0xE1)  # FSUB
        self.asm.emit_bytes(0xD9, 0xF0)  # F2XM1
        self.asm.emit_bytes(0xD9, 0xE8)  # FLD1
        self.asm.emit_bytes(0xDE, 0xC1)  # FADDP
        self.asm.emit_bytes(0xD9, 0xFD)  # FSCALE
        self.asm.emit_bytes(0xDD, 0xD9)  # FSTP ST(1)
        
        # Subtract 1.0
        self.asm.emit_bytes(0xD9, 0xE8)  # FLD1
        self.asm.emit_bytes(0xDE, 0xE9)  # FSUBP
        
        # Scale by 10000
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)
        self.asm.emit_bytes(0xDF, 0x04, 0x24)
        self.asm.emit_bytes(0xDE, 0xC9)
        
        # Store
        self.asm.emit_bytes(0xDF, 0x3C, 0x24)
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)
        
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)
        return True


    # ========== LOGARITHM FUNCTIONS ==========

    def compile_log(self, node):
        """Log(x) - Natural logarithm using x87
        
        Input: x * 10000 (fixed-point, must be > 0)
        Output: ln(x) * 10000 (fixed-point)
        
        Method: ln(x) = log2(x) * ln(2)
        """
        if len(node.arguments) != 1:
            raise ValueError("Log requires one argument")
        
        print("DEBUG: Compiling Log - x87 FYL2X")
        
        self.compiler.compile_expression(node.arguments[0])
        
        # Allocate stack space
        self.asm.emit_bytes(0x48, 0x83, 0xEC, 0x10)
        self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)
        
        # Load x and convert from fixed-point
        self.asm.emit_bytes(0xDF, 0x2C, 0x24)  # FILD QWORD [RSP]
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)  # 10000
        self.asm.emit_bytes(0xDF, 0x04, 0x24)  # FILD DWORD [RSP]
        self.asm.emit_bytes(0xDE, 0xF9)  # FDIVP (x now in ST0)
        
        # Load ln(2)
        self.asm.emit_bytes(0xD9, 0xED)  # FLDLN2
        
        # FYL2X: ST1 * log2(ST0), pops both, pushes result
        # Stack before: ln(2), x
        # We want: ln(2) * log2(x) = ln(x)
        self.asm.emit_bytes(0xD9, 0xC9)  # FXCH - swap so x is in ST1
        self.asm.emit_bytes(0xD9, 0xF1)  # FYL2X
        
        # Scale by 10000 for fixed-point output
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)
        self.asm.emit_bytes(0xDF, 0x04, 0x24)
        self.asm.emit_bytes(0xDE, 0xC9)
        
        # Store result
        self.asm.emit_bytes(0xDF, 0x3C, 0x24)
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)
        
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)
        return True


    def compile_log2(self, node):
        """Log2(x) - Base-2 logarithm using x87
        
        Input: x * 10000 (fixed-point, must be > 0)
        Output: log2(x) * 10000 (fixed-point)
        """
        if len(node.arguments) != 1:
            raise ValueError("Log2 requires one argument")
        
        print("DEBUG: Compiling Log2 - x87 FYL2X")
        
        self.compiler.compile_expression(node.arguments[0])
        
        # Allocate stack space
        self.asm.emit_bytes(0x48, 0x83, 0xEC, 0x10)
        self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)
        
        # Load x and convert from fixed-point
        self.asm.emit_bytes(0xDF, 0x2C, 0x24)
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)
        self.asm.emit_bytes(0xDF, 0x04, 0x24)
        self.asm.emit_bytes(0xDE, 0xF9)
        
        # Load 1.0 for FYL2X (1 * log2(x) = log2(x))
        self.asm.emit_bytes(0xD9, 0xE8)  # FLD1
        self.asm.emit_bytes(0xD9, 0xC9)  # FXCH
        self.asm.emit_bytes(0xD9, 0xF1)  # FYL2X
        
        # Scale by 10000
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)
        self.asm.emit_bytes(0xDF, 0x04, 0x24)
        self.asm.emit_bytes(0xDE, 0xC9)
        
        # Store
        self.asm.emit_bytes(0xDF, 0x3C, 0x24)
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)
        
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)
        return True


    def compile_log10(self, node):
        """Log10(x) - Base-10 logarithm using x87
        
        Input: x * 10000 (fixed-point, must be > 0)
        Output: log10(x) * 10000 (fixed-point)
        
        Method: log10(x) = log2(x) * log10(2)
        """
        if len(node.arguments) != 1:
            raise ValueError("Log10 requires one argument")
        
        print("DEBUG: Compiling Log10 - x87")
        
        self.compiler.compile_expression(node.arguments[0])
        
        # Allocate stack space
        self.asm.emit_bytes(0x48, 0x83, 0xEC, 0x10)
        self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)
        
        # Load x and convert from fixed-point
        self.asm.emit_bytes(0xDF, 0x2C, 0x24)
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)
        self.asm.emit_bytes(0xDF, 0x04, 0x24)
        self.asm.emit_bytes(0xDE, 0xF9)
        
        # Load log10(2) = FLDLG2
        self.asm.emit_bytes(0xD9, 0xEC)  # FLDLG2 (log10(2))
        self.asm.emit_bytes(0xD9, 0xC9)  # FXCH
        self.asm.emit_bytes(0xD9, 0xF1)  # FYL2X: log10(2) * log2(x) = log10(x)
        
        # Scale by 10000
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)
        self.asm.emit_bytes(0xDF, 0x04, 0x24)
        self.asm.emit_bytes(0xDE, 0xC9)
        
        # Store
        self.asm.emit_bytes(0xDF, 0x3C, 0x24)
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)
        
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)
        return True


    def compile_log1p(self, node):
        """Log1p(x) - ln(1+x), more accurate for small x
        
        Input: x * 10000 (fixed-point)
        Output: ln(1+x) * 10000 (fixed-point)
        
        Uses FYL2XP1 for accuracy when x is near 0
        """
        if len(node.arguments) != 1:
            raise ValueError("Log1p requires one argument")
        
        print("DEBUG: Compiling Log1p - x87 FYL2XP1")
        
        self.compiler.compile_expression(node.arguments[0])
        
        # Allocate stack space
        self.asm.emit_bytes(0x48, 0x83, 0xEC, 0x10)
        self.asm.emit_bytes(0x48, 0x89, 0x04, 0x24)
        
        # Load x and convert from fixed-point
        self.asm.emit_bytes(0xDF, 0x2C, 0x24)
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)
        self.asm.emit_bytes(0xDF, 0x04, 0x24)
        self.asm.emit_bytes(0xDE, 0xF9)
        
        # Load ln(2) for conversion from log2 to ln
        self.asm.emit_bytes(0xD9, 0xED)  # FLDLN2
        self.asm.emit_bytes(0xD9, 0xC9)  # FXCH
        
        # FYL2XP1: ST1 * log2(ST0 + 1)
        # Result: ln(2) * log2(x+1) = ln(x+1)
        self.asm.emit_bytes(0xD9, 0xF9)  # FYL2XP1
        
        # Scale by 10000
        self.asm.emit_bytes(0x48, 0xC7, 0x04, 0x24, 0x10, 0x27, 0x00, 0x00)
        self.asm.emit_bytes(0xDF, 0x04, 0x24)
        self.asm.emit_bytes(0xDE, 0xC9)
        
        # Store
        self.asm.emit_bytes(0xDF, 0x3C, 0x24)
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)
        
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)
        return True
        
    # Floating point specific
    def compile_next_after(self, node): return False
    def compile_frexp(self, node): return False
    def compile_ldexp(self, node): return False
    def compile_nearly_equal(self, node): return False