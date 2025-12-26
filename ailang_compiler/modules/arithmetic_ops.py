# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.

# ailang_compiler/compiler/modules/arithmetic_ops.py
"""
Arithmetic Operations Module - DEPTH-BASED REGISTER ALLOCATION
Handles deeply nested expressions by cycling through R12->R13->R14->R15 based on depth
This solves the register collision problem for arbitrary nesting levels
"""

from ailang_parser.ailang_ast import *

class ArithmeticOps:
    """Handles basic arithmetic operations with depth-aware register allocation"""
    
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm
        
        # Initialize depth tracker
        if not hasattr(self.compiler, '_binary_op_depth'):
            self.compiler._binary_op_depth = 0
    
    def _get_depth_register(self):
        """
        Get register info for current nesting depth.
        Uses R12/R13 for depth 0-1, then STACK for deeper nesting.
        R14/R15 are RESERVED for FixedPool/LinkagePool base registers.
        Returns: (name, mov_to_reg_bytes, mov_to_rbx_bytes, push_fn, pop_fn)
        """
        depth = self.compiler._binary_op_depth
        
        # ONLY use R12 and R13 - R14/R15 are reserved for pool access
        if depth == 0:
            return ('R12', [0x49, 0x89, 0xC4], [0x4C, 0x89, 0xE3], 
                    self.asm.emit_push_r12, self.asm.emit_pop_r12)
        elif depth == 1:
            return ('R13', [0x49, 0x89, 0xC5], [0x4C, 0x89, 0xEB],
                    self.asm.emit_push_r13, self.asm.emit_pop_r13)
        else:
            # Depth 2+: Use stack instead of registers to avoid pool register collision
            return ('STACK', None, None, 
                    lambda: None,  # Stack push happens in _compile_binary_op
                    lambda: None)
    
    def _compile_binary_op(self, node, op_name, op_fn):
        """
        Generic binary operation compiler with depth tracking.
        Uses R12/R13 for depth 0-1, stack for depth 2+.
        op_fn: function to emit the actual operation (like emit_add_rax_rbx)
        """
        if not (hasattr(node, "arguments") and len(node.arguments) == 2):
            raise ValueError(f"{op_name} expects exactly 2 arguments")
        
        reg_name, mov_to_reg, mov_to_rbx, push_fn, pop_fn = self._get_depth_register()
        print(f"DEBUG: {op_name} using {reg_name} at depth {self.compiler._binary_op_depth}")
        
        # Increment depth for nested expression compilation
        self.compiler._binary_op_depth += 1
        
        try:
            if reg_name == 'STACK':
                # Depth 2+: Use stack to avoid R14/R15 collision with pool registers
                self.compiler.compile_expression(node.arguments[1])  # RIGHT operand
                self.asm.emit_push_rax()  # Save on stack
                self.compiler.compile_expression(node.arguments[0])  # LEFT operand
                self.asm.emit_pop_rbx()  # Pop RIGHT into RBX
            else:
                # Depth 0-1: Use R12 or R13
                push_fn()
                self.compiler.compile_expression(node.arguments[1])  # RIGHT operand
                self.asm.emit_bytes(*mov_to_reg)  # MOV Rxx, RAX
                self.compiler.compile_expression(node.arguments[0])  # LEFT operand  
                self.asm.emit_bytes(*mov_to_rbx)  # MOV RBX, Rxx
                pop_fn()
            
            op_fn()  # Emit the actual operation
        finally:
            # Always decrement depth, even if exception occurs
            self.compiler._binary_op_depth -= 1
        
        return True
    
    def compile_operation(self, node):
        """Main dispatcher for arithmetic operations"""
        
        operations = {
            'Add': self.compile_add,
            'Subtract': self.compile_subtract,
            'Multiply': self.compile_multiply,
            'Divide': self.compile_divide,
            'Modulo': self.compile_modulo,
            'Power': self.compile_power,
            
            'BitwiseAnd': self.compile_bitwise_and,
            'BitwiseOr': self.compile_bitwise_or,
            'BitwiseXor': self.compile_bitwise_xor,
            'BitwiseNot': self.compile_bitwise_not,
            'LeftShift': self.compile_left_shift,
            'RightShift': self.compile_right_shift,
            
            'LessThan': self.compile_less_than,
            'GreaterThan': self.compile_greater_than,
            'LessEqual': self.compile_less_equal,
            'GreaterEqual': self.compile_greater_equal,
            'EqualTo': self.compile_equal_to,
            'NotEqual': self.compile_not_equal,
            
            'And': self.compile_logical_and,
            'Or': self.compile_logical_or,
            'Not': self.compile_logical_not,
        }
        
        func_name = node.function
        
        if func_name in operations:
            return operations[func_name](node)
        else:
            return False
    
    # === BASIC ARITHMETIC ===
    
    def compile_add(self, node):
        return self._compile_binary_op(node, "Add", self.asm.emit_add_rax_rbx)
    
    def compile_subtract(self, node):
        return self._compile_binary_op(node, "Subtract", self.asm.emit_sub_rax_rbx)
    
    def compile_multiply(self, node):
        return self._compile_binary_op(node, "Multiply", self.asm.emit_imul_rax_rbx)
    
    def compile_divide(self, node):
        """Division with optimization for constants
        
        Optimization hierarchy:
        1. Divide by 1 → no-op
        2. Divide by -1 → negate
        3. Constant power of 2 → right shift (1 cycle)
        4. Known constant → magic multiply (4-5 cycles)  
        5. General case → IDIV (20-90 cycles)
        """
        if not (hasattr(node, "arguments") and len(node.arguments) == 2):
            raise ValueError("Divide expects exactly 2 arguments")
        
        divisor = node.arguments[1]
        
        # Check if divisor is a compile-time constant
        if hasattr(divisor, 'value') and isinstance(divisor.value, int):
            d = divisor.value
            
            if d == 0:
                raise ValueError("Division by zero")
            
            if d == 1:
                # x / 1 = x
                print("DEBUG: Divide by 1 - no-op")
                self.compiler.compile_expression(node.arguments[0])
                return True
            
            if d == -1:
                # x / -1 = -x
                print("DEBUG: Divide by -1 - negate")
                self.compiler.compile_expression(node.arguments[0])
                self.asm.emit_bytes(0x48, 0xF7, 0xD8)  # NEG RAX
                return True
            
            # Check if power of 2
            if d > 0 and (d & (d - 1)) == 0:
                return self._compile_power_of_two_divide(node.arguments[0], d)
            
            # Known constant - use magic multiplication
            if abs(d) in [3, 5, 6, 7, 9, 10, 100, 1000, 10000]:
                return self._compile_magic_divide(node.arguments[0], d)
        
        # General case - use existing depth register pattern
        print("DEBUG: Divide - general IDIV")
        
        reg_name, mov_to_reg, mov_to_rbx, push_fn, pop_fn = self._get_depth_register()
        print(f"DEBUG: Divide using {reg_name} at depth {self.compiler._binary_op_depth}")
        
        self.compiler._binary_op_depth += 1
        
        try:
            if reg_name == 'STACK':
                self.compiler.compile_expression(node.arguments[1])  # divisor
                self.asm.emit_push_rax()
                self.compiler.compile_expression(node.arguments[0])  # dividend
                self.asm.emit_pop_rbx()
            else:
                push_fn()
                self.compiler.compile_expression(node.arguments[1])  # divisor
                self.asm.emit_bytes(*mov_to_reg)
                self.compiler.compile_expression(node.arguments[0])  # dividend
                self.asm.emit_bytes(*mov_to_rbx)
                pop_fn()
            
            # Sign extend and divide
            self.asm.emit_cqo()
            self.asm.emit_bytes(0x48, 0xF7, 0xFB)  # IDIV RBX
        finally:
            self.compiler._binary_op_depth -= 1
        
        return True


    def _compile_power_of_two_divide(self, dividend_node, d):
        """Divide by power of 2 using arithmetic right shift
        
        For signed division, we need to handle negative dividends correctly.
        The trick: add (d-1) to negative numbers before shifting.
        """
        shift = d.bit_length() - 1
        print(f"DEBUG: Divide by power of 2 ({d}) - shift right {shift}")
        
        self.compiler.compile_expression(dividend_node)
        
        # For d=2, shift=1. For d=4, shift=2. etc.
        
        # Handle signed division correctly:
        # If dividend is negative, add (d-1) before shifting
        # This gives correct truncation toward zero
        
        # MOV RCX, RAX (copy dividend)
        self.asm.emit_bytes(0x48, 0x89, 0xC1)
        
        # SAR RCX, 63 (RCX = -1 if negative, 0 if positive)
        self.asm.emit_bytes(0x48, 0xC1, 0xF9, 0x3F)
        
        # AND RCX, (d-1) - mask to get adjustment
        adjustment = d - 1
        if adjustment <= 0x7FFFFFFF:
            # AND RCX, imm32 (sign-extended)
            self.asm.emit_bytes(0x48, 0x81, 0xE1)
            self.asm.emit_bytes(adjustment & 0xFF,
                            (adjustment >> 8) & 0xFF,
                            (adjustment >> 16) & 0xFF,
                            (adjustment >> 24) & 0xFF)
        else:
            # Large adjustment - use RDX as temp
            self.asm.emit_bytes(0x48, 0xBA)  # MOV RDX, imm64
            for i in range(8):
                self.asm.emit_bytes((adjustment >> (i * 8)) & 0xFF)
            self.asm.emit_bytes(0x48, 0x21, 0xD1)  # AND RCX, RDX
        
        # ADD RAX, RCX (add adjustment for negatives)
        self.asm.emit_bytes(0x48, 0x01, 0xC8)
        
        # SAR RAX, shift
        self.asm.emit_bytes(0x48, 0xC1, 0xF8, shift)
        
        return True


    def _compile_magic_divide(self, dividend_node, d):
        """Divide by constant using magic multiplication
        
        Replaces 40-90 cycle IDIV with 4-5 cycle IMUL + shifts
        """
        print(f"DEBUG: Divide by constant {d} - magic multiply")
        
        abs_d = abs(d)
        
        # Magic numbers computed for signed 64-bit division
        # Format: (magic_number, shift_amount, needs_add)
        magic_table = {
            3:     (0x5555555555555556, 0, False),
            5:     (0x6666666666666667, 1, False),
            6:     (0x2AAAAAAAAAAAAAAB, 0, False),
            7:     (0x4924924924924925, 1, False),
            9:     (0x1C71C71C71C71C72, 0, False),
            10:    (0x6666666666666667, 2, False),
            100:   (0x28F5C28F5C28F5C3, 2, False),
            1000:  (0x20C49BA5E353F7CF, 7, True),
            10000: (0x346DC5D63886594B, 11, True),
        }
        
        if abs_d not in magic_table:
            # Fall back to IDIV
            print(f"DEBUG: No magic for {d}, falling back to IDIV")
            return False  # Will trigger general case
        
        magic, shift, needs_add = magic_table[abs_d]
        
        # Compile dividend into RAX
        self.compiler.compile_expression(dividend_node)
        
        # Save original for sign correction
        self.asm.emit_bytes(0x48, 0x89, 0xC1)  # MOV RCX, RAX
        
        # Load magic number into RDX (using R11 as temp since we need RDX for IMUL result)
        # MOV R11, magic
        self.asm.emit_bytes(0x49, 0xBB)  # MOVABS R11, imm64
        for i in range(8):
            self.asm.emit_bytes((magic >> (i * 8)) & 0xFF)
        
        # IMUL R11 (signed multiply: RDX:RAX = RAX * R11)
        self.asm.emit_bytes(0x49, 0xF7, 0xEB)  # IMUL R11
        
        # For some divisors, we need to add the original dividend to RDX
        if needs_add:
            self.asm.emit_bytes(0x48, 0x01, 0xCA)  # ADD RDX, RCX
        
        # Result is in RDX (high 64 bits of 128-bit product)
        self.asm.emit_bytes(0x48, 0x89, 0xD0)  # MOV RAX, RDX
        
        # Arithmetic right shift if needed
        if shift > 0:
            self.asm.emit_bytes(0x48, 0xC1, 0xF8, shift)  # SAR RAX, shift
        
        # Correct for negative dividends: add sign bit of original
        # MOV RDX, RCX
        self.asm.emit_bytes(0x48, 0x89, 0xCA)
        # SHR RDX, 63 (extract sign bit)
        self.asm.emit_bytes(0x48, 0xC1, 0xEA, 0x3F)
        # ADD RAX, RDX
        self.asm.emit_bytes(0x48, 0x01, 0xD0)
        
        # If original divisor was negative, negate result
        if d < 0:
            self.asm.emit_bytes(0x48, 0xF7, 0xD8)  # NEG RAX
        
        return True
    
    def compile_modulo(self, node):
        """Modulo with optimization for constants
        
        Optimization hierarchy:
        1. Modulo by 1 → always 0
        2. Constant power of 2 → AND mask (1-3 cycles!)
        3. Known constant → magic multiply then subtract (8-10 cycles)
        4. General case → IDIV (20-90 cycles)
        """
        if not (hasattr(node, "arguments") and len(node.arguments) == 2):
            raise ValueError("Modulo expects exactly 2 arguments")
        
        divisor = node.arguments[1]
        
        # Check if divisor is a compile-time constant
        if hasattr(divisor, 'value') and isinstance(divisor.value, int):
            d = divisor.value
            
            if d == 0:
                raise ValueError("Modulo by zero")
            
            if abs(d) == 1:
                # x % 1 = 0, x % -1 = 0
                print("DEBUG: Modulo by 1 - always zero")
                self.asm.emit_bytes(0x48, 0x31, 0xC0)  # XOR RAX, RAX
                return True
            
            # Check if power of 2 (only for positive divisors)
            if d > 0 and (d & (d - 1)) == 0:
                return self._compile_power_of_two_modulo(node.arguments[0], d)
            
            # Known constant - use magic multiplication
            if abs(d) in [3, 5, 6, 7, 9, 10, 100, 1000, 10000]:
                return self._compile_magic_modulo(node.arguments[0], d)
        
        # General case - use existing depth register pattern
        print("DEBUG: Modulo - general IDIV")
        
        reg_name, mov_to_reg, mov_to_rbx, push_fn, pop_fn = self._get_depth_register()
        print(f"DEBUG: Modulo using {reg_name} at depth {self.compiler._binary_op_depth}")
        
        self.compiler._binary_op_depth += 1
        
        try:
            if reg_name == 'STACK':
                self.compiler.compile_expression(node.arguments[1])
                self.asm.emit_push_rax()
                self.compiler.compile_expression(node.arguments[0])
                self.asm.emit_pop_rbx()
            else:
                push_fn()
                self.compiler.compile_expression(node.arguments[1])
                self.asm.emit_bytes(*mov_to_reg)
                self.compiler.compile_expression(node.arguments[0])
                self.asm.emit_bytes(*mov_to_rbx)
                pop_fn()
            
            self.asm.emit_cqo()
            self.asm.emit_bytes(0x48, 0xF7, 0xFB)  # IDIV RBX
            self.asm.emit_bytes(0x48, 0x89, 0xD0)  # MOV RAX, RDX (remainder)
        finally:
            self.compiler._binary_op_depth -= 1
        
        return True


    def _compile_power_of_two_modulo(self, dividend_node, d):
        """Modulo by power of 2 using AND mask
        
        For positive dividends: x % d = x & (d-1)
        For negative dividends: need to preserve sign of remainder
        
        C semantics: remainder has same sign as dividend
        """
        mask = d - 1
        print(f"DEBUG: Modulo by power of 2 ({d}) - AND with {mask}")
        
        self.compiler.compile_expression(dividend_node)
        
        # For signed modulo matching C semantics:
        # If x >= 0: result = x & mask
        # If x < 0: result = -(-x & mask) if (-x & mask) != 0 else 0
        #
        # Simplified approach using: ((x % d) + d) % d for positive result,
        # but we want C semantics where sign matches dividend.
        #
        # Trick: result = x - (x / d) * d, but we optimized divide...
        # 
        # Better trick for power of 2:
        # remainder = x & mask
        # if x < 0 and remainder != 0: remainder -= d
        # But this needs branches...
        #
        # Branchless version:
        # sign_mask = x >> 63  (all 1s if negative, all 0s if positive)
        # adj = sign_mask & mask  (mask if negative, 0 if positive)
        # temp = (x + adj) & mask
        # result = temp - adj
        
        # Actually simpler branchless approach:
        # For x < 0: x % d == -(-x % d) when -x % d != 0
        # 
        # Even simpler - just compute correctly:
        # remainder = ((x % d) + d) % d gives positive result
        # but we want sign of x
        
        # Most straightforward branchless for signed power-of-2 modulo:
        # t = x >> 63          (all 1s if neg, else 0)
        # r = (x + (t & mask)) & mask
        # result = r - (t & mask)
        # But this doesn't quite work for all cases...
        
        # Let's use the simpler approach that matches IDIV behavior:
        # Compute x & mask, then fix sign
        
        # Save original for sign
        self.asm.emit_bytes(0x48, 0x89, 0xC1)  # MOV RCX, RAX
        
        # Compute absolute value, AND, then restore sign
        # abs_x = (x ^ (x >> 63)) - (x >> 63)
        self.asm.emit_bytes(0x48, 0x89, 0xC2)  # MOV RDX, RAX
        self.asm.emit_bytes(0x48, 0xC1, 0xFA, 0x3F)  # SAR RDX, 63
        self.asm.emit_bytes(0x48, 0x31, 0xD0)  # XOR RAX, RDX
        self.asm.emit_bytes(0x48, 0x29, 0xD0)  # SUB RAX, RDX (RAX = abs(x))
        
        # AND with mask
        if mask <= 0x7FFFFFFF:
            self.asm.emit_bytes(0x48, 0x25)  # AND RAX, imm32
            self.asm.emit_bytes(mask & 0xFF,
                            (mask >> 8) & 0xFF,
                            (mask >> 16) & 0xFF,
                            (mask >> 24) & 0xFF)
        else:
            # Large mask
            self.asm.emit_bytes(0x48, 0xBB)  # MOV RBX, imm64
            for i in range(8):
                self.asm.emit_bytes((mask >> (i * 8)) & 0xFF)
            self.asm.emit_bytes(0x48, 0x21, 0xD8)  # AND RAX, RBX
        
        # Now RAX = abs(x) & mask
        # If original was negative and result != 0, negate it
        
        # RCX still has original x
        # RDX has sign mask (-1 or 0)
        
        # Restore sign: if original < 0, negate result
        # result = (result ^ sign) - sign
        self.asm.emit_bytes(0x48, 0xC1, 0xF9, 0x3F)  # SAR RCX, 63 (sign mask in RCX)
        self.asm.emit_bytes(0x48, 0x31, 0xC8)  # XOR RAX, RCX
        self.asm.emit_bytes(0x48, 0x29, 0xC8)  # SUB RAX, RCX
        
        return True


    def _compile_magic_modulo(self, dividend_node, d):
        """Modulo by constant using magic division
        
        remainder = x - (x / d) * d
        
        Uses magic multiply for the division part.
        """
        print(f"DEBUG: Modulo by constant {d} - magic multiply")
        
        abs_d = abs(d)
        
        # Same magic table as division
        magic_table = {
            3:     (0x5555555555555556, 0, False),
            5:     (0x6666666666666667, 1, False),
            6:     (0x2AAAAAAAAAAAAAAB, 0, False),
            7:     (0x4924924924924925, 1, False),
            9:     (0x1C71C71C71C71C72, 0, False),
            10:    (0x6666666666666667, 2, False),
            100:   (0x28F5C28F5C28F5C3, 2, False),
            1000:  (0x20C49BA5E353F7CF, 7, True),
            10000: (0x346DC5D63886594B, 11, True),
        }
        
        if abs_d not in magic_table:
            print(f"DEBUG: No magic for {d}, falling back to IDIV")
            return False
        
        magic, shift, needs_add = magic_table[abs_d]
        
        # Compile dividend into RAX
        self.compiler.compile_expression(dividend_node)
        
        # Save original dividend in RCX
        self.asm.emit_bytes(0x48, 0x89, 0xC1)  # MOV RCX, RAX
        
        # === Compute quotient using magic multiply ===
        
        # Load magic number into R11
        self.asm.emit_bytes(0x49, 0xBB)  # MOVABS R11, imm64
        for i in range(8):
            self.asm.emit_bytes((magic >> (i * 8)) & 0xFF)
        
        # IMUL R11 (RDX:RAX = RAX * R11)
        self.asm.emit_bytes(0x49, 0xF7, 0xEB)  # IMUL R11
        
        # For some divisors, add original to high result
        if needs_add:
            self.asm.emit_bytes(0x48, 0x01, 0xCA)  # ADD RDX, RCX
        
        # Quotient is in RDX, shift if needed
        self.asm.emit_bytes(0x48, 0x89, 0xD0)  # MOV RAX, RDX
        
        if shift > 0:
            self.asm.emit_bytes(0x48, 0xC1, 0xF8, shift)  # SAR RAX, shift
        
        # Correct for negative: add sign bit
        self.asm.emit_bytes(0x48, 0x89, 0xCA)  # MOV RDX, RCX (original)
        self.asm.emit_bytes(0x48, 0xC1, 0xEA, 0x3F)  # SHR RDX, 63
        self.asm.emit_bytes(0x48, 0x01, 0xD0)  # ADD RAX, RDX
        
        # Now RAX = x / d (quotient)
        # === Compute remainder = x - quotient * d ===
        
        # RAX = quotient, RCX = original x
        # remainder = RCX - RAX * d
        
        # Multiply quotient by d
        if abs_d <= 0x7FFFFFFF:
            # IMUL RAX, RAX, d
            self.asm.emit_bytes(0x48, 0x69, 0xC0)  # IMUL RAX, RAX, imm32
            self.asm.emit_bytes(abs_d & 0xFF,
                            (abs_d >> 8) & 0xFF,
                            (abs_d >> 16) & 0xFF,
                            (abs_d >> 24) & 0xFF)
        else:
            # Load d into RBX and multiply
            self.asm.emit_bytes(0x48, 0xBB)  # MOV RBX, imm64
            for i in range(8):
                self.asm.emit_bytes((abs_d >> (i * 8)) & 0xFF)
            self.asm.emit_bytes(0x48, 0x0F, 0xAF, 0xC3)  # IMUL RAX, RBX
        
        # RAX = quotient * abs_d
        # Remainder = original - quotient * d
        # MOV RAX, RCX; SUB RAX, (quotient*d) -- but we have it backwards
        
        # SUB RCX, RAX (RCX = x - quotient * d)
        self.asm.emit_bytes(0x48, 0x29, 0xC1)  # SUB RCX, RAX
        
        # Move result to RAX
        self.asm.emit_bytes(0x48, 0x89, 0xC8)  # MOV RAX, RCX
        
        return True
    
    def compile_power(self, node):
        """Power operation (requires loop, uses R12 for base regardless of depth)"""
        if not (hasattr(node, "arguments") and len(node.arguments) == 2):
            raise ValueError("Power expects exactly 2 arguments")
        
        print("DEBUG: Power operation")
        
        # Power is special - always uses R12 for base, R13 for exponent
        self.asm.emit_push_r12()
        self.asm.emit_push_r13()
        
        self.compiler._binary_op_depth += 1
        
        try:
            # Exponent in R13
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_bytes(0x49, 0x89, 0xC5)  # MOV R13, RAX
            
            # Base in R12
            self.compiler.compile_expression(node.arguments[0])
            self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX
            
            # Result = 1
            self.asm.emit_mov_rax_imm64(1)
            
            loop_start = self.asm.create_label()
            loop_end = self.asm.create_label()
            
            self.asm.mark_label(loop_start)
            self.asm.emit_bytes(0x4D, 0x85, 0xED)  # TEST R13, R13
            self.asm.emit_jump_to_label(loop_end, "JZ")
            
            self.asm.emit_bytes(0x49, 0x0F, 0xAF, 0xC4)  # IMUL RAX, R12
            self.asm.emit_bytes(0x49, 0xFF, 0xCD)  # DEC R13
            self.asm.emit_jump_to_label(loop_start, "JMP")
            
            self.asm.mark_label(loop_end)
        finally:
            self.asm.emit_pop_r13()
            self.asm.emit_pop_r12()
            self.compiler._binary_op_depth -= 1
        
        return True
    
    # === BITWISE OPERATIONS ===
    
    def compile_bitwise_and(self, node):
        return self._compile_binary_op(node, "BitwiseAnd", self.asm.emit_and_rax_rbx)
    
    def compile_bitwise_or(self, node):
        return self._compile_binary_op(node, "BitwiseOr", self.asm.emit_or_rax_rbx)
    
    def compile_bitwise_xor(self, node):
        return self._compile_binary_op(node, "BitwiseXor", self.asm.emit_xor_rax_rbx)
    
    def compile_bitwise_not(self, node):
        """Unary NOT operation"""
        if not (hasattr(node, "arguments") and len(node.arguments) == 1):
            raise ValueError("BitwiseNot expects exactly 1 argument")
        
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_not_rax()
        return True
    
    def compile_left_shift(self, node):
        """Left shift (amount goes in RCX)"""
        if not (hasattr(node, "arguments") and len(node.arguments) == 2):
            raise ValueError("LeftShift expects exactly 2 arguments")
        
        reg_name, mov_to_reg, _, push_fn, pop_fn = self._get_depth_register()
        print(f"DEBUG: LeftShift using {reg_name}")
        
        self.compiler._binary_op_depth += 1
        
        try:
            if reg_name == 'STACK':
                # Depth 2+: Use stack to avoid register collision
                self.compiler.compile_expression(node.arguments[1])  # shift amount
                self.asm.emit_push_rax()
                self.compiler.compile_expression(node.arguments[0])  # value to shift
                # Pop shift amount into RCX
                self.asm.emit_pop_rcx()
            else:
                # Depth 0-1: Use R12 or R13
                push_fn()
                self.compiler.compile_expression(node.arguments[1])  # shift amount
                self.asm.emit_bytes(*mov_to_reg)
                self.compiler.compile_expression(node.arguments[0])  # value to shift
                # Move shift amount from Rxx to RCX
                if reg_name == 'R12':
                    self.asm.emit_bytes(0x4C, 0x89, 0xE1)  # MOV RCX, R12
                elif reg_name == 'R13':
                    self.asm.emit_bytes(0x4C, 0x89, 0xE9)  # MOV RCX, R13
                pop_fn()
            
            self.asm.emit_shl_rax_cl()
        finally:
            self.compiler._binary_op_depth -= 1
        
        return True

    def compile_right_shift(self, node):
        """Right shift (arithmetic)"""
        if not (hasattr(node, "arguments") and len(node.arguments) == 2):
            raise ValueError("RightShift expects exactly 2 arguments")
        
        reg_name, mov_to_reg, _, push_fn, pop_fn = self._get_depth_register()
        print(f"DEBUG: RightShift using {reg_name}")
        
        self.compiler._binary_op_depth += 1
        
        try:
            if reg_name == 'STACK':
                # Depth 2+: Use stack to avoid register collision
                self.compiler.compile_expression(node.arguments[1])  # shift amount
                self.asm.emit_push_rax()
                self.compiler.compile_expression(node.arguments[0])  # value to shift
                # Pop shift amount into RCX
                self.asm.emit_pop_rcx()
            else:
                # Depth 0-1: Use R12 or R13
                push_fn()
                self.compiler.compile_expression(node.arguments[1])  # shift amount
                self.asm.emit_bytes(*mov_to_reg)
                self.compiler.compile_expression(node.arguments[0])  # value to shift
                # Move shift amount from Rxx to RCX
                if reg_name == 'R12':
                    self.asm.emit_bytes(0x4C, 0x89, 0xE1)  # MOV RCX, R12
                elif reg_name == 'R13':
                    self.asm.emit_bytes(0x4C, 0x89, 0xE9)  # MOV RCX, R13
                pop_fn()
            
            self.asm.emit_sar_rax_cl()
        finally:
            self.compiler._binary_op_depth -= 1
        
        return True
    
    # === COMPARISON OPERATIONS ===
    
    def compile_less_than(self, node):
        def op():
            self.asm.emit_cmp_rax_rbx()
            self.asm.emit_bytes(0x0F, 0x9C, 0xC0)  # SETL AL
            self.asm.emit_bytes(0x48, 0x0F, 0xB6, 0xC0)  # MOVZX RAX, AL
        return self._compile_binary_op(node, "LessThan", op)
    
    def compile_greater_than(self, node):
        def op():
            self.asm.emit_cmp_rax_rbx()
            self.asm.emit_bytes(0x0F, 0x9F, 0xC0)  # SETG AL
            self.asm.emit_bytes(0x48, 0x0F, 0xB6, 0xC0)
        return self._compile_binary_op(node, "GreaterThan", op)
    
    def compile_less_equal(self, node):
        def op():
            self.asm.emit_cmp_rax_rbx()
            self.asm.emit_bytes(0x0F, 0x9E, 0xC0)  # SETLE AL
            self.asm.emit_bytes(0x48, 0x0F, 0xB6, 0xC0)
        return self._compile_binary_op(node, "LessEqual", op)
    
    def compile_greater_equal(self, node):
        def op():
            self.asm.emit_cmp_rax_rbx()
            self.asm.emit_bytes(0x0F, 0x9D, 0xC0)  # SETGE AL
            self.asm.emit_bytes(0x48, 0x0F, 0xB6, 0xC0)
        return self._compile_binary_op(node, "GreaterEqual", op)
    
    def compile_equal_to(self, node):
        def op():
            self.asm.emit_cmp_rax_rbx()
            self.asm.emit_bytes(0x0F, 0x94, 0xC0)  # SETE AL
            self.asm.emit_bytes(0x48, 0x0F, 0xB6, 0xC0)
        return self._compile_binary_op(node, "EqualTo", op)
    
    def compile_not_equal(self, node):
        def op():
            self.asm.emit_cmp_rax_rbx()
            self.asm.emit_bytes(0x0F, 0x95, 0xC0)  # SETNE AL
            self.asm.emit_bytes(0x48, 0x0F, 0xB6, 0xC0)
        return self._compile_binary_op(node, "NotEqual", op)
    
    # === LOGICAL OPERATIONS ===
    
    def compile_logical_and(self, node):
        """Short-circuit AND"""
        if not (hasattr(node, "arguments") and len(node.arguments) == 2):
            raise ValueError("And expects exactly 2 arguments")
        
        false_label = self.asm.create_label()
        end_label = self.asm.create_label()
        
        self.compiler._binary_op_depth += 1
        try:
            self.compiler.compile_expression(node.arguments[0])
            self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
            self.asm.emit_jump_to_label(false_label, "JZ")
            
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_bytes(0x48, 0x85, 0xC0)
            self.asm.emit_jump_to_label(false_label, "JZ")
            
            self.asm.emit_mov_rax_imm64(1)
            self.asm.emit_jump_to_label(end_label, "JMP")
            
            self.asm.mark_label(false_label)
            self.asm.emit_mov_rax_imm64(0)
            
            self.asm.mark_label(end_label)
        finally:
            self.compiler._binary_op_depth -= 1
        
        return True
    
    def compile_logical_or(self, node):
        """Short-circuit OR"""
        if not (hasattr(node, "arguments") and len(node.arguments) == 2):
            raise ValueError("Or expects exactly 2 arguments")
        
        true_label = self.asm.create_label()
        end_label = self.asm.create_label()
        
        self.compiler._binary_op_depth += 1
        try:
            self.compiler.compile_expression(node.arguments[0])
            self.asm.emit_bytes(0x48, 0x85, 0xC0)
            self.asm.emit_jump_to_label(true_label, "JNZ")
            
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_bytes(0x48, 0x85, 0xC0)
            self.asm.emit_jump_to_label(true_label, "JNZ")
            
            self.asm.emit_mov_rax_imm64(0)
            self.asm.emit_jump_to_label(end_label, "JMP")
            
            self.asm.mark_label(true_label)
            self.asm.emit_mov_rax_imm64(1)
            
            self.asm.mark_label(end_label)
        finally:
            self.compiler._binary_op_depth -= 1
        
        return True
    
    def compile_logical_not(self, node):
        """Logical NOT"""
        if not (hasattr(node, "arguments") and len(node.arguments) == 1):
            raise ValueError("Not expects exactly 1 argument")
        
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        self.asm.emit_bytes(0x0F, 0x94, 0xC0)  # SETZ AL
        self.asm.emit_bytes(0x48, 0x0F, 0xB6, 0xC0)  # MOVZX RAX, AL
        return True