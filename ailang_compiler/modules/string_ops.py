# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
String Operations Module for AILANG Compiler
Provides general-purpose string manipulation primitives.
"""

import sys
import os
import struct
from ailang_parser.ailang_ast import *

class StringOps:
    """General-purpose string operations"""

    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm

    def compile_operation(self, node):
        """Route to specific string operation handlers"""
        function = node.function
        handlers = {
            'StringConcat': self.compile_string_concat,
            'StringConcatPooled': self.compile_string_concat_pooled,
            'StringCompare': self.compile_string_compare,
            'StringLength': self.compile_string_length,
            'StringCopy': self.compile_string_copy,
            'StringToNumber': self.compile_string_to_number,
            'NumberToString': self.compile_number_to_string,
            'StringEquals': self.compile_string_equals,
            'ReadInput': self.compile_read_input,
            'PrintString': self.compile_print_string,
            # === NEW: Wire up all string handlers ===
            'StringFromChar': self.compile_char_to_string,
            'StringToUpper': self.compile_string_to_upper,
            'StringToLower': self.compile_string_to_lower,
            'StringContains': self.compile_string_contains,
            # Alias StringExtract to the existing StringSubstring implementation
            'StringExtract': self.compile_string_substring,
            'StringSubstring': self.compile_string_substring,
            'StringCharAt': self.compile_string_char_at,
            'StringExtractUntil': self.compile_string_extract_until,
            'StringIndexOf': self.compile_string_index_of,
            'StringTrim': self.compile_string_trim,
            'StringReplace': self.compile_string_replace,
         #   'StringReplaceAll': self.compile_string_replace_all,  
            'StringSplit': self.compile_string_split,
            
        }
        
        handler = handlers.get(function)
        if handler:
            return handler(node)
        return False


    

    def compile_read_input(self, node):
        """Read a line from standard input"""
        try:
            print("DEBUG: Compiling ReadInput")
            
            # Allocate buffer for input (e.g., 1024 bytes)
            buffer_size = 1024
            
            # Allocate buffer on heap
            self.asm.emit_mov_rdi_imm(buffer_size)
            self.asm.emit_syscall_mmap()  # Returns buffer in RAX
            self.asm.emit_push_rax()  # Save buffer address
            
            # Read from stdin (fd = 0)
            self.asm.emit_pop_rsi()  # Buffer address in RSI
            self.asm.emit_push_rsi()  # Save it again
            self.asm.emit_mov_rdi_imm(0)  # stdin = 0
            self.asm.emit_mov_rdx_imm(buffer_size - 1)  # Max bytes to read
            self.asm.emit_mov_rax_imm64(0)  # sys_read = 0
            self.asm.emit_syscall()
            
            # RAX now contains number of bytes read (or -1 on error, 0 on EOF)
            # Check if we got EOF or error
            self.asm.emit_test_rax_rax()
            eof_label = self.asm.create_label()
            self.asm.emit_jle(eof_label)  # Jump if <= 0
            
            # Not EOF - null terminate the string
            self.asm.emit_pop_rsi()  # Get buffer address
            self.asm.emit_push_rsi()  # Keep it on stack
            self.asm.emit_mov_rbx_rax()  # Save byte count
            
            # Find newline and replace with null
            self.asm.emit_mov_rcx_rax()  # Counter
            find_newline_loop = self.asm.create_label()
            found_newline = self.asm.create_label()
            self.asm.mark_label(find_newline_loop)
            self.asm.emit_test_rcx_rcx()
            self.asm.emit_jz(found_newline)
            self.asm.emit_mov_al_byte_ptr_rsi()  # Load byte
            self.asm.emit_cmp_al_imm(10)  # Check for '\n'
            self.asm.emit_je(found_newline)
            self.asm.emit_inc_rsi()
            self.asm.emit_dec_rcx()
            self.asm.emit_jmp(find_newline_loop)
            
            self.asm.mark_label(found_newline)
            self.asm.emit_mov_byte_ptr_rsi_imm(0)  # Null terminate
            
            # Return buffer address
            self.asm.emit_pop_rax()
            done_label = self.asm.create_label()
            self.asm.emit_jmp(done_label)
            
            # EOF/error case - return 0
            self.asm.mark_label(eof_label)
            self.asm.emit_pop_rax()  # Clean stack
            self.asm.emit_xor_rax_rax()  # Return 0
            
            self.asm.mark_label(done_label)
            
            return True
            
        except Exception as e:
            print(f"ERROR: ReadInput compilation failed: {str(e)}")
            return False



    def compile_string_to_number(self, node):
        """Convert ASCII string to integer - general purpose"""
        if len(node.arguments) < 1:
            raise ValueError("StringToNumber requires 1 argument")
        
        # Save registers
        self.asm.emit_push_rbx()
        self.asm.emit_push_rcx()
        self.asm.emit_push_rdx()
        self.asm.emit_push_rsi()
        
        # Get string pointer
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rsi_rax()  # String ptr in RSI
        
        # Initialize result = 0, sign = 1
        self.asm.emit_mov_rax_imm64(0)   # Result
        self.asm.emit_mov_rcx_imm64(1)   # Sign (1 = positive)
        self.asm.emit_mov_rbx_imm64(10)  # Base 10
        
        # Check for negative sign
        self.asm.emit_bytes(0x8A, 0x16)  # MOV DL, [RSI]
        self.asm.emit_bytes(0x80, 0xFA, 0x2D)  # CMP DL, '-'
        not_negative = self.asm.create_label()
        self.asm.emit_jump_to_label(not_negative, "JNE")
        
        # Handle negative
        # Use 2's complement for -1: 0xFFFFFFFFFFFFFFFF
        self.asm.emit_bytes(0x48, 0xC7, 0xC1, 0xFF, 0xFF, 0xFF, 0xFF)  # MOV RCX, -1
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI (skip '-')
        
        self.asm.mark_label(not_negative)
        
        # Parse digits
        parse_loop = self.asm.create_label()
        parse_done = self.asm.create_label()
        
        self.asm.mark_label(parse_loop)
        
        # Load byte
        self.asm.emit_bytes(0x0F, 0xB6, 0x16)  # MOVZX EDX, BYTE [RSI]
        
        # Check if null terminator
        self.asm.emit_bytes(0x84, 0xD2)  # TEST DL, DL
        self.asm.emit_jump_to_label(parse_done, "JE")
        
        # Check if digit ('0' to '9')
        self.asm.emit_bytes(0x80, 0xFA, 0x30)  # CMP DL, '0'
        self.asm.emit_jump_to_label(parse_done, "JL")
        self.asm.emit_bytes(0x80, 0xFA, 0x39)  # CMP DL, '9'
        self.asm.emit_jump_to_label(parse_done, "JG")
        
        # Convert digit: result = result * 10 + (char - '0')
        self.asm.emit_bytes(0x48, 0x0F, 0xAF, 0xC3)  # IMUL RAX, RBX (result * 10)
        self.asm.emit_bytes(0x48, 0x83, 0xEA, 0x30)  # SUB RDX, '0'
        self.asm.emit_bytes(0x48, 0x01, 0xD0)        # ADD RAX, RDX
        
        # Next character
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_jump_to_label(parse_loop, "JMP")
        
        self.asm.mark_label(parse_done)
        
        # Apply sign
        self.asm.emit_bytes(0x48, 0x0F, 0xAF, 0xC1)  # IMUL RAX, RCX
        
        # Restore registers
        self.asm.emit_pop_rsi()
        self.asm.emit_pop_rdx()
        self.asm.emit_pop_rcx()
        self.asm.emit_pop_rbx()
        
        return True

    # In string_ops.py
    def compile_print_message(self, node):
        """Compile PrintMessage with proper string address handling and newline"""
        try:
            if isinstance(node.message, String):
                # Print the string
                self.asm.emit_print_string(node.message.value)
                # Don't add extra newline here - emit_print_string handles it
                
            elif isinstance(node.message, Number):
                self.asm.emit_mov_rax_imm64(int(node.message.value))
                self.asm.emit_print_number()
                # Add newline after number
                newline_offset = self.asm.add_string("\n")
                self.asm.emit_mov_rax_imm64(1)  # sys_write
                self.asm.emit_mov_rdi_imm64(1)  # stdout
                self.asm.emit_load_data_address('rsi', newline_offset)
                self.asm.emit_mov_rdx_imm64(1)
                self.asm.emit_syscall()

            elif isinstance(node.message, Identifier):
                # Just use compile_expression like FunctionCalls do
                # This ensures consistent variable loading
                self.compiler.compile_expression(node.message)
                self.emit_smart_print_with_jumps()

                # Add newline after identifier value
                newline_offset = self.asm.add_string("\n")
                self.asm.emit_mov_rax_imm64(1)  # sys_write
                self.asm.emit_mov_rdi_imm64(1)  # stdout
                self.asm.emit_load_data_address('rsi', newline_offset)
                self.asm.emit_mov_rdx_imm64(1)
                self.asm.emit_syscall()

            elif isinstance(node.message, FunctionCall):
                self.compiler.compile_function_call(node.message)
                self.emit_smart_print_with_jumps()
                # Add newline after function result
                newline_offset = self.asm.add_string("\n")
                self.asm.emit_mov_rax_imm64(1)  # sys_write
                self.asm.emit_mov_rdi_imm64(1)  # stdout
                self.asm.emit_load_data_address('rsi', newline_offset)
                self.asm.emit_mov_rdx_imm64(1)
                self.asm.emit_syscall()
            else:
                raise ValueError(f"Unsupported PrintMessage type: {type(node.message)}")
        except Exception as e:
            raise ValueError(f"PrintMessage compilation failed: {str(e)}")

    def compile_print_number(self, node):
        """Compile PrintNumber function - prints numeric value"""
        try:
            if isinstance(node, FunctionCall) and node.function == 'PrintNumber':
                if len(node.arguments) != 1:
                    raise ValueError("PrintNumber requires exactly 1 argument")
                # Compile the argument to get value in RAX
                self.compiler.compile_expression(node.arguments[0])
                # Print the number in RAX
                self.asm.emit_print_number()
                # Print newline
                newline_offset = self.asm.add_string("\n")
                self.asm.emit_mov_rax_imm64(1)  # sys_write
                self.asm.emit_mov_rdi_imm64(1)  # stdout
                self.asm.emit_load_data_address('rsi', newline_offset)  # string address
                self.asm.emit_mov_rdx_imm64(1)  # length
                self.asm.emit_syscall()
                print("DEBUG: PrintNumber completed")
                return True
            return False
        except Exception as e:
            print(f"ERROR: PrintNumber compilation failed: {str(e)}")
            raise
        
    
    def compile_print_string(self, node):
        """PrintString(string_var) - Print a string variable to stdout"""
        try:
            print("DEBUG: Compiling PrintString operation")
            
            if len(node.arguments) != 1:
                raise ValueError("PrintString requires exactly 1 argument")
            
            # Evaluate the argument to get string address in RAX
            self.compiler.compile_expression(node.arguments[0])
            
            # RAX now contains the string address
            # We need to calculate the string length
            
            # Save string address
            self.asm.emit_push_rax()
            
            # Calculate strlen: RDI = string, returns length in RCX
            self.asm.emit_mov_rdi_rax()  # String address to RDI
            self.asm.emit_bytes(0x48, 0x31, 0xC9)  # XOR RCX, RCX (counter = 0)
            
            # Create labels for strlen loop
            strlen_loop = self.asm.create_label()
            strlen_done = self.asm.create_label()
            
            # strlen loop
            self.asm.mark_label(strlen_loop)
            self.asm.emit_bytes(0x80, 0x3C, 0x0F, 0x00)  # CMP BYTE [RDI+RCX], 0
            self.asm.emit_jump_to_label(strlen_done, "JE")
            self.asm.emit_bytes(0x48, 0xFF, 0xC1)  # INC RCX
            self.asm.emit_jump_to_label(strlen_loop, "JMP")
            
            self.asm.mark_label(strlen_done)
            # RCX now contains string length
            
            # Restore string address to RSI
            self.asm.emit_pop_rsi()
            
            # Make sys_write syscall
            self.asm.emit_mov_rax_imm64(1)  # sys_write
            self.asm.emit_mov_rdi_imm64(1)  # stdout
            # RSI already has string address
            self.asm.emit_bytes(0x48, 0x89, 0xCA)  # MOV RDX, RCX (length)
            self.asm.emit_syscall()
            
            print("DEBUG: PrintString completed")
            return True
            
        except Exception as e:
            print(f"ERROR: PrintString compilation failed: {str(e)}")
            raise
    
    
    def emit_smart_print_with_jumps(self):
        """Smart print - check if value is likely a string address or number"""
        string_label = self.asm.create_label()
        number_label = self.asm.create_label()
        end_label = self.asm.create_label()

        # Check if small number (< 1000000)
        self.asm.emit_bytes(0x48, 0x3D, 0x40, 0x42, 0x0F, 0x00)  # CMP RAX, 1000000
        self.asm.emit_jump_to_label(number_label, "JL")

        # Check if in data section (>= 0x400000)
        self.asm.emit_bytes(0x48, 0x3D, 0x00, 0x00, 0x40, 0x00)  # CMP RAX, 0x400000
        self.asm.emit_jump_to_label(string_label, "JGE")

        # Number path
        self.asm.mark_label(number_label)
        self.asm.emit_print_number()
        self.asm.emit_jump_to_label(end_label, "JMP")

        # String path
        self.asm.mark_label(string_label)
        self.emit_print_string_at_address()

        self.asm.mark_label(end_label)

    def emit_print_string_at_address(self):
        """Print null-terminated string at address in RAX (NULL-safe)."""
        # Save the incoming pointer (could be NULL)
        self.asm.emit_push_rax()
        self.asm.emit_mov_rbx_rax()

        # ===== NULL GUARD =====
        null_done = self.asm.create_label()
        self.asm.emit_bytes(0x48, 0x85, 0xDB)      # TEST RBX, RBX
        self.asm.emit_jump_to_label(null_done, "JZ")  # if RBX==0 -> skip printing

        # Compute length (RCX) from RBX
        self.asm.emit_mov_rcx_imm64(0)

        strlen_loop = self.asm.create_label()
        strlen_end  = self.asm.create_label()

        self.asm.mark_label(strlen_loop)
        self.asm.emit_bytes(0x80, 0x3C, 0x0B, 0x00)   # CMP BYTE PTR [RBX+RCX], 0
        self.asm.emit_jump_to_label(strlen_end, "JE")
        self.asm.emit_bytes(0x48, 0xFF, 0xC1)         # INC RCX
        self.asm.emit_jump_to_label(strlen_loop, "JMP")

        self.asm.mark_label(strlen_end)

        # write(1, RBX, RCX)
        self.asm.emit_mov_rax_imm64(1)   # sys_write
        self.asm.emit_mov_rdi_imm64(1)   # stdout
        self.asm.emit_bytes(0x48, 0x89, 0xDE)  # MOV RSI, RBX
        self.asm.emit_bytes(0x48, 0x89, 0xCA)  # MOV RDX, RCX
        self.asm.emit_syscall()

        # newline
        newline_offset = self.asm.add_string("\n")
        self.asm.emit_mov_rax_imm64(1)          # sys_write
        self.asm.emit_mov_rdi_imm64(1)          # stdout
        self.asm.emit_load_data_address('rsi', newline_offset)
        self.asm.emit_mov_rdx_imm64(1)
        self.asm.emit_syscall()

        # ===== END NULL GUARD =====
        self.asm.mark_label(null_done)

        # Restore and return
        self.asm.emit_pop_rax()


    def compile_number_to_string(self, node):
        """Convert integer to ASCII string - general purpose"""
        if len(node.arguments) < 1:
            raise ValueError("NumberToString requires 1 argument")
        
        # --- FIX: Save callee-saved registers RBX and R12 ---
        self.asm.emit_push_rbx()
        self.asm.emit_push_r12()  # PUSH R12 (tracked)

        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_push_rax()

        # Allocate buffer (32 bytes)
        self.asm.emit_mov_rax_imm64(9)
        self.asm.emit_mov_rdi_imm64(0)
        self.asm.emit_mov_rsi_imm64(32)
        self.asm.emit_mov_rdx_imm64(3)
        self.asm.emit_mov_r10_imm64(0x22)
        self.asm.emit_mov_r8_imm64(0xFFFFFFFFFFFFFFFF)  # R8 = -1 (fd)
        self.asm.emit_mov_r9_imm64(0)
        self.asm.emit_syscall()

        # --- FIX: Use R12 (which we saved) instead of the critical R15 ---
        self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX
        self.asm.emit_pop_rax()

        # Handle negative numbers
        self.asm.emit_push_rax()
        self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        not_negative = self.asm.create_label()
        self.asm.emit_jump_to_label(not_negative, "JNS")
        
        # Negate for processing
        self.asm.emit_bytes(0x48, 0xF7, 0xD8)  # NEG RAX
        
        self.asm.mark_label(not_negative)

        # Convert to string (backward from end of buffer)
        # --- FIX: Use R12 ---
        self.asm.emit_bytes(0x4C, 0x89, 0xE7)  # MOV RDI, R12
        self.asm.emit_bytes(0x48, 0x83, 0xC7, 0x1F)
        self.asm.emit_bytes(0xC6, 0x07, 0x00)
        self.asm.emit_bytes(0x48, 0xFF, 0xCF)

        # CRITICAL FIX: Create done_label BEFORE branching
        done_label = self.asm.create_label()
        
        self.asm.emit_bytes(0x48, 0x85, 0xC0)
        zero_case = self.asm.create_label()
        not_zero = self.asm.create_label()
        self.asm.emit_jump_to_label(not_zero, "JNZ")

        self.asm.mark_label(zero_case)
        self.asm.emit_bytes(0xC6, 0x07, 0x30)  # MOV BYTE [RDI], '0'
        self.asm.emit_mov_rax_rdi()
        # FIX: Pop the pushed value to balance stack
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x08)  # ADD RSP, 8
        self.asm.emit_jump_to_label(done_label, "JMP")

        self.asm.mark_label(not_zero)
        # --- FIX: Use RBX (which we saved) for the divisor ---
        self.asm.emit_bytes(0x48, 0xBB, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)

        convert_loop = self.asm.create_label()
        convert_done = self.asm.create_label()

        self.asm.mark_label(convert_loop)
        self.asm.emit_bytes(0x48, 0x85, 0xC0)
        self.asm.emit_jump_to_label(convert_done, "JZ")
        self.asm.emit_bytes(0x48, 0x31, 0xD2)
        self.asm.emit_bytes(0x48, 0xF7, 0xF3)
        self.asm.emit_bytes(0x48, 0x83, 0xC2, 0x30)
        self.asm.emit_bytes(0x88, 0x17)
        self.asm.emit_bytes(0x48, 0xFF, 0xCF)
        self.asm.emit_jump_to_label(convert_loop, "JMP")

        self.asm.mark_label(convert_done)
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)
        
        # Check if original was negative
        self.asm.emit_pop_rax()  # Original value
        self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        positive_done = self.asm.create_label()
        self.asm.emit_jump_to_label(positive_done, "JNS")
        
        # Add minus sign
        self.asm.emit_bytes(0x48, 0xFF, 0xCF)  # DEC RDI
        self.asm.emit_bytes(0xC6, 0x07, 0x2D)  # MOV BYTE [RDI], '-'
        
        self.asm.mark_label(positive_done)
        self.asm.emit_mov_rax_rdi()

        self.asm.mark_label(done_label)

        # --- FIX: Restore callee-saved registers ---
        self.asm.emit_pop_r12()
        self.asm.emit_pop_rbx()

        return True

        # ABI-compliant fix for string_ops.py - compile_string_concat
    # Following System V AMD64 ABI calling conventions

    def compile_string_concat(self, node):
        """Concatenate two strings - Stack-based version to avoid R13/R14 clobbering"""
        if len(node.arguments) < 2:
            raise ValueError("StringConcat requires 2 arguments")
        
        print("DEBUG: StringConcat - Stack-based version (safe from register clobbering)")
        
        # Save callee-saved registers that we'll use
        self.asm.emit_push_rbx()
        self.asm.emit_push_r12()
        
        # CRITICAL FIX: Don't trust R13/R14 across compile_expression calls
        # because user functions may clobber them. Use stack instead.
        
        # Evaluate first argument and save on stack
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_push_rax()  # str1 on stack
        
        # Evaluate second argument and save on stack
        self.compiler.compile_expression(node.arguments[1])  
        self.asm.emit_push_rax()  # str2 on stack
        
        # Now pop them into registers (after all expressions evaluated)
        self.asm.emit_pop_r14()  # str2 into R14 (most recent push)
        self.asm.emit_pop_r13()  # str1 into R13 (first push)
        
        # Now work with R13 (str1) and R14 (str2)
        
        # Calculate len1 - use R13 as source
        self.asm.emit_bytes(0x4C, 0x89, 0xEF)  # MOV RDI, R13
        self.asm.emit_mov_rcx_imm64(0)
        
        # Null check str1
        self.asm.emit_bytes(0x48, 0x85, 0xFF)  # TEST RDI, RDI
        null1_label = self.asm.create_label()
        self.asm.emit_jump_to_label(null1_label, "JZ")
        
        # Calculate length of str1
        len1_loop = self.asm.create_label()
        len1_done = self.asm.create_label()
        self.asm.mark_label(len1_loop)
        self.asm.emit_bytes(0x80, 0x3C, 0x0F, 0x00)  # CMP BYTE [RDI+RCX], 0
        self.asm.emit_jump_to_label(len1_done, "JE")
        self.asm.emit_bytes(0x48, 0xFF, 0xC1)  # INC RCX
        self.asm.emit_jump_to_label(len1_loop, "JMP")
        self.asm.mark_label(len1_done)
        
        self.asm.mark_label(null1_label)
        self.asm.emit_bytes(0x48, 0x89, 0xCB)  # MOV RBX, RCX (save len1 in RBX)
        
        # Calculate len2 - use R14 as source
        self.asm.emit_bytes(0x4C, 0x89, 0xF7)  # MOV RDI, R14
        self.asm.emit_mov_rcx_imm64(0)
        
        # Null check str2
        self.asm.emit_bytes(0x48, 0x85, 0xFF)  # TEST RDI, RDI
        null2_label = self.asm.create_label()
        self.asm.emit_jump_to_label(null2_label, "JZ")
        
        # Calculate length of str2
        len2_loop = self.asm.create_label()
        len2_done = self.asm.create_label()
        self.asm.mark_label(len2_loop)
        self.asm.emit_bytes(0x80, 0x3C, 0x0F, 0x00)  # CMP BYTE [RDI+RCX], 0
        self.asm.emit_jump_to_label(len2_done, "JE")
        self.asm.emit_bytes(0x48, 0xFF, 0xC1)  # INC RCX
        self.asm.emit_jump_to_label(len2_loop, "JMP")
        self.asm.mark_label(len2_done)
        
        self.asm.mark_label(null2_label)
        # RCX = len2, RBX = len1
        
        # Calculate total size (len1 + len2 + 1)
        self.asm.emit_bytes(0x48, 0x01, 0xD9)  # ADD RCX, RBX
        self.asm.emit_bytes(0x48, 0xFF, 0xC1)  # INC RCX (for null terminator)
        
        # Allocate new buffer using mmap
        # Setup syscall arguments
        self.asm.emit_mov_rax_imm64(9)  # mmap syscall
        self.asm.emit_mov_rdi_imm64(0)  # addr = NULL
        self.asm.emit_mov_rsi_rcx()  # length = total size
        self.asm.emit_mov_rdx_imm64(0x3)  # PROT_READ | PROT_WRITE
        self.asm.emit_mov_r10_imm64(0x22)  # MAP_PRIVATE | MAP_ANONYMOUS
        self.asm.emit_bytes(0x49, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF)  # MOV R8, -1
        self.asm.emit_mov_r9_imm64(0)  # offset = 0
        self.asm.emit_syscall()
        
        # RAX = new buffer, save it
        self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX - save result in R12
        self.asm.emit_mov_rdi_rax()  # RDI = destination for copying
        
        # Copy str1 (from R13)
        self.asm.emit_bytes(0x4C, 0x89, 0xEE)  # MOV RSI, R13
        self.asm.emit_bytes(0x48, 0x85, 0xF6)  # TEST RSI, RSI
        skip_copy1 = self.asm.create_label()
        self.asm.emit_jump_to_label(skip_copy1, "JZ")
        
        copy1_loop = self.asm.create_label()
        copy1_done = self.asm.create_label()
        self.asm.mark_label(copy1_loop)
        self.asm.emit_bytes(0x8A, 0x0E)  # MOV CL, [RSI]
        self.asm.emit_bytes(0x84, 0xC9)  # TEST CL, CL
        self.asm.emit_jump_to_label(copy1_done, "JZ")
        self.asm.emit_bytes(0x88, 0x0F)  # MOV [RDI], CL
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_jump_to_label(copy1_loop, "JMP")
        self.asm.mark_label(copy1_done)
        
        self.asm.mark_label(skip_copy1)
        
        # Copy str2 (from R14)
        self.asm.emit_bytes(0x4C, 0x89, 0xF6)  # MOV RSI, R14
        self.asm.emit_bytes(0x48, 0x85, 0xF6)  # TEST RSI, RSI
        skip_copy2 = self.asm.create_label()
        self.asm.emit_jump_to_label(skip_copy2, "JZ")
        
        copy2_loop = self.asm.create_label()
        copy2_done = self.asm.create_label()
        self.asm.mark_label(copy2_loop)
        self.asm.emit_bytes(0x8A, 0x0E)  # MOV CL, [RSI]
        self.asm.emit_bytes(0x84, 0xC9)  # TEST CL, CL
        self.asm.emit_jump_to_label(copy2_done, "JZ")
        self.asm.emit_bytes(0x88, 0x0F)  # MOV [RDI], CL
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_jump_to_label(copy2_loop, "JMP")
        self.asm.mark_label(copy2_done)
        
        self.asm.mark_label(skip_copy2)
        
        # Null terminate
        self.asm.emit_bytes(0xC6, 0x07, 0x00)  # MOV BYTE [RDI], 0
        
        # Move result from R12 to RAX
        self.asm.emit_bytes(0x4C, 0x89, 0xE0)  # MOV RAX, R12
        
        # Restore callee-saved registers in reverse order
        self.asm.emit_pop_r12()
        self.asm.emit_pop_rbx()
        
        print("DEBUG: StringConcat completed (stack-based, safe from clobbering)")
        return True

    def compile_string_compare(self, node):
        """Compare two strings - returns 0 if equal, non-zero if different"""
        if len(node.arguments) < 2:
            raise ValueError("StringCompare requires 2 arguments")

        # --- FIX: Save callee-saved RBX register ---
        self.asm.emit_push_rbx()

        self.asm.emit_push_rbx()
        self.asm.emit_push_rcx()
        self.asm.emit_push_rdx()
        self.asm.emit_push_rsi()
        self.asm.emit_push_rdi()

        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_mov_rsi_rax()

        cmp_loop = self.asm.create_label()
        cmp_equal = self.asm.create_label()
        cmp_not_equal = self.asm.create_label()

        self.asm.mark_label(cmp_loop)
        self.asm.emit_bytes(0x8A, 0x07)  # MOV AL, [RDI]
        self.asm.emit_bytes(0x8A, 0x1E)  # MOV BL, [RSI]
        self.asm.emit_bytes(0x38, 0xD8)  # CMP AL, BL
        self.asm.emit_jump_to_label(cmp_not_equal, "JNE")
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL
        self.asm.emit_jump_to_label(cmp_equal, "JZ")
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_jump_to_label(cmp_loop, "JMP")

        self.asm.mark_label(cmp_equal)
        self.asm.emit_mov_rax_imm64(0)
        done_label = self.asm.create_label()
        self.asm.emit_jump_to_label(done_label, "JMP")

        self.asm.mark_label(cmp_not_equal)
        self.asm.emit_mov_rax_imm64(1)

        self.asm.mark_label(done_label)

        self.asm.emit_pop_rdi()
        self.asm.emit_pop_rsi()
        self.asm.emit_pop_rdx()
        self.asm.emit_pop_rcx()
        self.asm.emit_pop_rbx()

        # --- FIX: Restore callee-saved RBX register ---
        self.asm.emit_pop_rbx()
        return True

    def compile_string_length(self, node):
        """Get length of null-terminated string"""
        if len(node.arguments) < 1:
            raise ValueError("StringLength requires 1 argument")

        self.asm.emit_push_rbx()
        self.asm.emit_push_rcx()

        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rbx_rax()
        self.asm.emit_mov_rax_imm64(0)

        len_loop = self.asm.create_label()
        len_done = self.asm.create_label()

        self.asm.mark_label(len_loop)
        self.asm.emit_bytes(0x8A, 0x0B)  # MOV CL, [RBX]
        self.asm.emit_bytes(0x84, 0xC9)  # TEST CL, CL
        self.asm.emit_jump_to_label(len_done, "JZ")
        self.asm.emit_bytes(0x48, 0xFF, 0xC0)  # INC RAX
        self.asm.emit_bytes(0x48, 0xFF, 0xC3)  # INC RBX
        self.asm.emit_jump_to_label(len_loop, "JMP")

        self.asm.mark_label(len_done)

        self.asm.emit_pop_rcx()
        self.asm.emit_pop_rbx()
        return True

    def compile_string_copy(self, node):
        """Copy source string to destination"""
        if len(node.arguments) < 2:
            raise ValueError("StringCopy requires 2 arguments")

        self.asm.emit_push_rbx()
        self.asm.emit_push_rcx()
        self.asm.emit_push_rsi()
        self.asm.emit_push_rdi()

        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_mov_rsi_rax()

        copy_loop = self.asm.create_label()
        copy_done = self.asm.create_label()
        # NULL-safe: if first source RSI==0, skip first copy
        self.asm.emit_test_rsi_rsi()
        skip_first = self.asm.create_label()
        self.asm.emit_jump_to_label(skip_first, "JZ")
        # NULL-safe first source: treat NULL as empty
        self.asm.emit_test_rsi_rsi()
        copy_first_skip = self.asm.create_label()
        self.asm.emit_jump_to_label(copy_first_skip, "JZ")

        self.asm.mark_label(copy_loop)
        self.asm.emit_bytes(0x8A, 0x06)  # MOV AL, [RSI]
        self.asm.emit_bytes(0x88, 0x07)  # MOV [RDI], AL
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL
        self.asm.emit_jump_to_label(copy_done, "JE")
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_jump_to_label(copy_loop, "JMP")
        
        self.asm.mark_label(copy_done)
        self.asm.emit_mov_rax_imm64(1)

    def compile_string_equals(self, node):
        """Compare two strings - returns 1 if equal, 0 if different"""
        if len(node.arguments) < 2:
            raise ValueError("StringEquals requires 2 arguments")
        
        print("DEBUG: Compiling StringEquals")
        
        # Save registers we'll use
        self.asm.emit_push_rcx()
        self.asm.emit_push_rdx()
        self.asm.emit_push_rsi()
        self.asm.emit_push_rdi()
        
        # Get string pointers
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()  # First string in RDI
        
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_mov_rsi_rax()  # Second string in RSI
        
        # Create labels for control flow
        cmp_loop = self.asm.create_label()
        strings_equal = self.asm.create_label()
        strings_not_equal = self.asm.create_label()
        done = self.asm.create_label()
        
        self.asm.mark_label(cmp_loop)
        
        # Load bytes to compare
        self.asm.emit_bytes(0x8A, 0x07)  # MOV AL, [RDI]
        self.asm.emit_bytes(0x8A, 0x16)  # MOV DL, [RSI]
        
        # Compare the bytes
        self.asm.emit_bytes(0x38, 0xD0)  # CMP AL, DL
        self.asm.emit_jump_to_label(strings_not_equal, "JNE")
        
        # Check if we hit null terminator (strings ended)
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL
        self.asm.emit_jump_to_label(strings_equal, "JZ")
        
        # Move to next characters
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_jump_to_label(cmp_loop, "JMP")
        
        # Strings are equal
        self.asm.mark_label(strings_equal)
        self.asm.emit_mov_rax_imm64(1)
        self.asm.emit_jump_to_label(done, "JMP")
        
        # Strings are not equal
        self.asm.mark_label(strings_not_equal)
        self.asm.emit_mov_rax_imm64(0)
        
        self.asm.mark_label(done)
        
        # Restore registers
        self.asm.emit_pop_rdi()
        self.asm.emit_pop_rsi()
        self.asm.emit_pop_rdx()
        self.asm.emit_pop_rcx()
        
        print("DEBUG: StringEquals completed")
        return True


    def compile_read_input(self, node):
        """Read input from stdin into dynamically allocated buffer"""
        print("DEBUG: Compiling ReadInput")
        
        # Handle optional argument (prompt string) - just ignore it for now
        # The argument would be a prompt to display, but we handle that separately
        
        # Allocate buffer for input (256 bytes) using mmap
        buffer_size = 256
        
        self.asm.emit_mov_rax_imm64(9)  # sys_mmap
        self.asm.emit_mov_rdi_imm64(0)  # addr = NULL
        self.asm.emit_mov_rsi_imm64(buffer_size)  # length
        self.asm.emit_mov_rdx_imm64(3)  # PROT_READ | PROT_WRITE
        self.asm.emit_mov_r10_imm64(0x22)  # MAP_PRIVATE | MAP_ANONYMOUS  
        self.asm.emit_bytes(0x49, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF)  # MOV R8, -1 (fd)
        self.asm.emit_mov_r9_imm64(0)  # offset = 0
        self.asm.emit_syscall()
        
        # Save buffer address in RBX (preserved across syscalls)
        self.asm.emit_mov_rbx_rax()
        
        # Read from stdin
        self.asm.emit_mov_rdi_imm64(0)  # fd = stdin
        self.asm.emit_mov_rsi_from_rbx()  # buffer address from RBX (USE CORRECT METHOD NAME)
        self.asm.emit_mov_rdx_imm64(buffer_size - 1)  # leave room for null
        self.asm.emit_mov_rax_imm64(0)  # sys_read
        self.asm.emit_syscall()
        
        # RAX now contains number of bytes read
        # Check if we read anything
        self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        no_input = self.asm.create_label()
        has_input = self.asm.create_label()
        done = self.asm.create_label()
        self.asm.emit_jump_to_label(has_input, "JNZ")
        
        # No input case - just null terminate at start
        self.asm.mark_label(no_input)
        self.asm.emit_bytes(0xC6, 0x03, 0x00)  # MOV BYTE [RBX], 0
        self.asm.emit_jump_to_label(done, "JMP")
        
        # Has input - null terminate and strip newline if present
        self.asm.mark_label(has_input)
        
        # RBX still has buffer start, RAX has bytes read
        # Calculate position of last character: RBX + RAX - 1
        self.asm.emit_mov_rdi_from_rbx()  # Copy buffer address to RDI (USE CORRECT METHOD NAME)
        self.asm.emit_add_rdi_rax()  # ADD RDI, RAX (end of input)
        self.asm.emit_dec_rdi()  # DEC RDI (last char)
        
        # Check if it's a newline
        self.asm.emit_bytes(0x80, 0x3F, 0x0A)  # CMP BYTE [RDI], 0x0A
        not_newline = self.asm.create_label()
        self.asm.emit_jump_to_label(not_newline, "JNE")
        
        # Replace newline with null
        self.asm.emit_mov_byte_ptr_rdi_zero()  # MOV BYTE [RDI], 0
        self.asm.emit_jump_to_label(done, "JMP")
        
        # Not a newline - null terminate after the last char
        self.asm.mark_label(not_newline)
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI (move past last char)
        self.asm.emit_mov_byte_ptr_rdi_zero()  # MOV BYTE [RDI], 0
        
        self.asm.mark_label(done)
        
        # Return buffer address (still in RBX)
        self.asm.emit_mov_rax_rbx()
        
        print("DEBUG: ReadInput completed")
        return True
    
    
    # Add these methods to string_ops.py

    def compile_string_pool_init(self, node):
        """Initialize a pre-allocated string pool"""
        print("DEBUG: Initializing string pool")
        
        # Allocate a large buffer (64KB) once
        pool_size = 65536
        
        # Single mmap call for entire pool
        self.asm.emit_mov_rax_imm64(9)  # sys_mmap
        self.asm.emit_mov_rdi_imm64(0)  # addr = NULL
        self.asm.emit_mov_rsi_imm64(pool_size)  # 64KB
        self.asm.emit_mov_rdx_imm64(3)  # PROT_READ | PROT_WRITE
        self.asm.emit_mov_r10_imm64(0x22)  # MAP_PRIVATE | MAP_ANONYMOUS
        self.asm.emit_bytes(0x49, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF)  # MOV R8, -1
        self.asm.emit_mov_r9_imm64(0)  # offset = 0
        self.asm.emit_syscall()
        
        # Store pool base address in a known location
        # We'll use a fixed memory location for simplicity
        pool_base_addr = self.asm.add_data_qword(0)  # Pool base
        pool_next_offset = self.asm.add_data_qword(0)  # Next free offset
        
        # Store pool base address
        self.asm.emit_push_rax()  # Save pool address
        self.asm.emit_load_data_address('rbx', pool_base_addr)
        self.asm.emit_bytes(0x48, 0x89, 0x03)  # MOV [RBX], RAX
        
        # Initialize next_offset to 0
        self.asm.emit_load_data_address('rbx', pool_next_offset)
        self.asm.emit_mov_rax_imm64(0)
        self.asm.emit_bytes(0x48, 0x89, 0x03)  # MOV [RBX], RAX
        
        # Return pool base address
        self.asm.emit_pop_rax()
        
        print("DEBUG: String pool initialized")
        return True

    def compile_string_pool_alloc(self, size):
        """Sub-allocate from the string pool"""
        print(f"DEBUG: Pool allocating {size} bytes")
        
        # Get current offset
        pool_next_offset = self.asm.get_data_offset('pool_next_offset')
        self.asm.emit_load_data_address('rbx', pool_next_offset)
        self.asm.emit_bytes(0x48, 0x8B, 0x03)  # MOV RAX, [RBX] - current offset
        
        # Save current offset (this is our allocation)
        self.asm.emit_push_rax()
        
        # Add size to offset
        self.asm.emit_bytes(0x48, 0x05)  # ADD RAX, imm32
        self.asm.emit_bytes(*struct.pack('<I', size))
        
        # Store new offset
        self.asm.emit_bytes(0x48, 0x89, 0x03)  # MOV [RBX], RAX
        
        # Get pool base
        pool_base_addr = self.asm.get_data_offset('pool_base_addr')
        self.asm.emit_load_data_address('rbx', pool_base_addr)
        self.asm.emit_bytes(0x48, 0x8B, 0x03)  # MOV RAX, [RBX] - pool base
        
        # Add offset to base
        self.asm.emit_pop_rbx()  # Get saved offset
        self.asm.emit_bytes(0x48, 0x01, 0xD8)  # ADD RAX, RBX
        
        # RAX now contains the allocated address
        return True

    def compile_string_pool_concat(self, node):
        """Optimized string concatenation using pool allocation"""
        if len(node.arguments) < 2:
            raise ValueError("StringPoolConcat requires 2 arguments")
        
        print("DEBUG: Pool-optimized string concatenation")
        
        # Get both strings
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_push_rax()  # Save str1
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_push_rax()  # Save str2
        
        # Calculate total size needed
        # Get length of str1
        self.asm.emit_mov_rdi_from_stack(8)  # Get str1 from stack
        self.asm.emit_mov_rcx_imm64(0)
        
        len1_loop = self.asm.create_label()
        len1_done = self.asm.create_label()
        
        self.asm.mark_label(len1_loop)
        self.asm.emit_bytes(0x80, 0x3C, 0x0F, 0x00)  # CMP BYTE [RDI+RCX], 0
        self.asm.emit_jump_to_label(len1_done, "JE")
        self.asm.emit_bytes(0x48, 0xFF, 0xC1)  # INC RCX
        self.asm.emit_jump_to_label(len1_loop, "JMP")
        
        self.asm.mark_label(len1_done)
        self.asm.emit_push_rcx()  # Save len1
        
        # Get length of str2
        self.asm.emit_mov_rdi_from_stack(8)  # Get str2 from stack
        self.asm.emit_mov_rdx_imm64(0)
        
        len2_loop = self.asm.create_label()
        len2_done = self.asm.create_label()
        
        self.asm.mark_label(len2_loop)
        self.asm.emit_bytes(0x80, 0x3C, 0x17, 0x00)  # CMP BYTE [RDI+RDX], 0
        self.asm.emit_jump_to_label(len2_done, "JE")
        self.asm.emit_bytes(0x48, 0xFF, 0xC2)  # INC RDX
        self.asm.emit_jump_to_label(len2_loop, "JMP")
        
        self.asm.mark_label(len2_done)
        
        # Total size = len1 + len2 + 1
        self.asm.emit_pop_rcx()  # Get len1
        self.asm.emit_bytes(0x48, 0x01, 0xD1)  # ADD RCX, RDX
        self.asm.emit_bytes(0x48, 0xFF, 0xC1)  # INC RCX (for null terminator)
        
        # Allocate from pool
        self.compile_string_pool_alloc(rcx)  # Size in RCX
        self.asm.emit_mov_rdi_rax()  # Destination in RDI
        self.asm.emit_push_rdi()  # Save result address
        
        # Copy str1
        self.asm.emit_pop_rsi()  # str2 (discard for now)
        self.asm.emit_pop_rsi()  # str1
        
        copy1_loop = self.asm.create_label()
        copy1_done = self.asm.create_label()
        
        self.asm.mark_label(copy1_loop)
        self.asm.emit_bytes(0x8A, 0x06)  # MOV AL, [RSI]
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL
        self.asm.emit_jump_to_label(copy1_done, "JZ")
        self.asm.emit_bytes(0x88, 0x07)  # MOV [RDI], AL
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_jump_to_label(copy1_loop, "JMP")
        
        self.asm.mark_label(copy1_done)
        
        # Copy str2
        self.asm.emit_pop_rsi()  # str2
        
        copy2_loop = self.asm.create_label()
        copy2_done = self.asm.create_label()
        
        self.asm.mark_label(copy2_loop)
        self.asm.emit_bytes(0x8A, 0x06)  # MOV AL, [RSI]
        self.asm.emit_bytes(0x88, 0x07)  # MOV [RDI], AL
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL
        self.asm.emit_jump_to_label(copy2_done, "JZ")
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_jump_to_label(copy2_loop, "JMP")
        
        self.asm.mark_label(copy2_done)
        
        self.asm.emit_bytes(0xC6, 0x07, 0x00)  # MOV BYTE [RDI], 0
        
        # Return result address
        self.asm.emit_pop_rax()
        
        print("DEBUG: Pool concat completed")
        return True

    
    # In string_ops.py
    def compile_string_concat_pooled(self, node):
        """Concatenate strings using pool allocation with dynamic pool size"""
        if len(node.arguments) < 2:
            raise ValueError("StringConcatPooled requires 2 arguments")

        print("DEBUG: Compiling StringConcatPooled with pool allocation")

        # Save registers
        self.asm.emit_push_rbx()
        self.asm.emit_push_rcx()
        self.asm.emit_push_rdx()
        self.asm.emit_push_rsi()
        self.asm.emit_push_rdi()

        # Compile and save both string arguments
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_push_rax()  # Save first string pointer

        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_push_rax()  # Save second string pointer

        # Get pool variable offset
        pool_offset = self.compiler.variables.get('_pool_StringPool_base')
        if pool_offset is None:
            print("DEBUG: Pool not found, returning first string")
            self.asm.emit_bytes(0x48, 0x8B, 0x44, 0x24, 0x08)  # MOV RAX, [RSP+8]
            self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)  # ADD RSP, 16
            self.asm.emit_pop_rdi()
            self.asm.emit_pop_rsi()
            self.asm.emit_pop_rdx()
            self.asm.emit_pop_rcx()
            self.asm.emit_pop_rbx()
            return True

        print(f"DEBUG: Pool found at offset {pool_offset}")

        # Load pool base address
        self.asm.emit_bytes(0x48, 0x8B, 0xBD)  # MOV RDI, [RBP + offset]
        self.asm.emit_bytes(*struct.pack('<i', pool_offset))

        # Load current pool offset
        self.asm.emit_bytes(0x48, 0x8B, 0x8D)  # MOV RCX, [RBP + offset+8]
        self.asm.emit_bytes(*struct.pack('<i', pool_offset + 8))

        # Load pool size
        self.asm.emit_bytes(0x48, 0x8B, 0x95)  # MOV RDX, [RBP + offset+16]
        self.asm.emit_bytes(*struct.pack('<i', pool_offset + 16))

        # Check if current offset is too large (10% margin)
        self.asm.emit_bytes(0x48, 0x89, 0xD0)  # MOV RAX, RDX
        self.asm.emit_bytes(0x48, 0xC1, 0xE8, 0x03)  # SHR RAX, 3
        self.asm.emit_bytes(0x48, 0x29, 0xC2)  # SUB RDX, RAX
        self.asm.emit_bytes(0x48, 0x39, 0xD1)  # CMP RCX, RDX
        overflow_label = self.asm.create_label()
        self.asm.emit_jump_to_label(overflow_label, "JAE")

        # Calculate allocation address
        self.asm.emit_bytes(0x48, 0x01, 0xCF)  # ADD RDI, RCX

        # Save start address
        self.asm.emit_push_rdi()

        # Calculate total length
        self.asm.emit_bytes(0x48, 0x8B, 0x74, 0x24, 0x10)  # MOV RSI, [RSP+16]
        self.asm.emit_bytes(0x48, 0x31, 0xDB)  # XOR RBX, RBX
        length_loop1 = self.asm.create_label()
        self.asm.mark_label(length_loop1)
        self.asm.emit_bytes(0x8A, 0x0E)  # MOV CL, [RSI]
        self.asm.emit_bytes(0x84, 0xC9)  # TEST CL, CL
        length_done1 = self.asm.create_label()
        self.asm.emit_jump_to_label(length_done1, "JZ")
        self.asm.emit_bytes(0x48, 0xFF, 0xC3)  # INC RBX
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_jump_to_label(length_loop1, "JMP")
        self.asm.mark_label(length_done1)

        self.asm.emit_bytes(0x48, 0x8B, 0x74, 0x24, 0x08)  # MOV RSI, [RSP+8]
        length_loop2 = self.asm.create_label()
        self.asm.mark_label(length_loop2)
        self.asm.emit_bytes(0x8A, 0x0E)  # MOV CL, [RSI]
        self.asm.emit_bytes(0x84, 0xC9)  # TEST CL, CL
        length_done2 = self.asm.create_label()
        self.asm.emit_jump_to_label(length_done2, "JZ")
        self.asm.emit_bytes(0x48, 0xFF, 0xC3)  # INC RBX
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_jump_to_label(length_loop2, "JMP")
        self.asm.mark_label(length_done2)

        self.asm.emit_bytes(0x48, 0xFF, 0xC3)  # INC RBX (null terminator)

        # Check length against remaining space
        self.asm.emit_bytes(0x48, 0x8B, 0x95)  # MOV RDX, [RBP + offset+16]
        self.asm.emit_bytes(*struct.pack('<i', pool_offset + 16))
        self.asm.emit_bytes(0x48, 0x29, 0xCA)  # SUB RDX, RCX
        self.asm.emit_bytes(0x48, 0x39, 0xD3)  # CMP RBX, RDX
        self.asm.emit_jump_to_label(overflow_label, "JAE")

        # Restore RDI to start of allocation
        self.asm.emit_bytes(0x48, 0x8B, 0x3C, 0x24)  # MOV RDI, [RSP]

        # Copy first string
        self.asm.emit_bytes(0x48, 0x8B, 0x74, 0x24, 0x10)  # MOV RSI, [RSP+16]
        copy1_loop = self.asm.create_label()
        self.asm.mark_label(copy1_loop)
        self.asm.emit_bytes(0x8A, 0x0E)  # MOV CL, [RSI]
        self.asm.emit_bytes(0x84, 0xC9)  # TEST CL, CL
        copy1_done = self.asm.create_label()
        self.asm.emit_jump_to_label(copy1_done, "JZ")
        self.asm.emit_bytes(0x88, 0x0F)  # MOV [RDI], CL
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_jump_to_label(copy1_loop, "JMP")
        self.asm.mark_label(copy1_done)

        # Copy second string
        self.asm.emit_bytes(0x48, 0x8B, 0x74, 0x24, 0x08)  # MOV RSI, [RSP+8]
        copy2_loop = self.asm.create_label()
        self.asm.mark_label(copy2_loop)
        self.asm.emit_bytes(0x8A, 0x0E)  # MOV CL, [RSI]
        self.asm.emit_bytes(0x84, 0xC9)  # TEST CL, CL
        copy2_done = self.asm.create_label()
        self.asm.emit_jump_to_label(copy2_done, "JZ")
        self.asm.emit_bytes(0x88, 0x0F)  # MOV [RDI], CL
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_jump_to_label(copy2_loop, "JMP")
        self.asm.mark_label(copy2_done)

        self.asm.emit_bytes(0xC6, 0x07, 0x00)  # MOV BYTE [RDI], 0
        
        # Update pool offset
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)  # MOV RAX, [RSP] (start address)
        self.asm.emit_bytes(0x48, 0x89, 0xF9)  # MOV RCX, RDI (end address)
        self.asm.emit_bytes(0x48, 0xFF, 0xC1)  # INC RCX (past null)
        self.asm.emit_bytes(0x48, 0x29, 0xC1)  # SUB RCX, RAX (bytes used)
        self.asm.emit_bytes(0x48, 0x8B, 0x95)  # MOV RDX, [RBP + offset+8]
        self.asm.emit_bytes(*struct.pack('<i', pool_offset + 8))
        self.asm.emit_bytes(0x48, 0x01, 0xCA)  # ADD RDX, RCX
        self.asm.emit_bytes(0x48, 0x89, 0x95)  # MOV [RBP + offset+8], RDX
        self.asm.emit_bytes(*struct.pack('<i', pool_offset + 8))

        # Return result - pop saved allocation address
        self.asm.emit_pop_rax()  # Get the saved allocation address
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x10)  # ADD RSP, 16 - clean string pointers
        
        # Jump to done
        done_label = self.asm.create_label()
        self.asm.emit_jump_to_label(done_label, "JMP")

        # Overflow case
        self.asm.mark_label(overflow_label)
        print("DEBUG: Pool overflow, returning first string")
        self.asm.emit_bytes(0x48, 0x8B, 0x44, 0x24, 0x08)  # MOV RAX, [RSP+8]
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x18)  # ADD RSP, 24 (saved addr + 2 strings)

        # Done - restore registers
        self.asm.mark_label(done_label)
        self.asm.emit_pop_rdi()
        self.asm.emit_pop_rsi()
        self.asm.emit_pop_rdx()
        self.asm.emit_pop_rcx()
        self.asm.emit_pop_rbx()

        print("DEBUG: StringConcatPooled completed")
        return True
    
    def compile_char_to_string(self, node):
        """Convert single ASCII character code to string"""
        if len(node.arguments) < 1:
            raise ValueError("StringFromChar requires 1 argument (ASCII code)")
        
        print("DEBUG: Compiling StringFromChar")
        
        # Get ASCII code
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_push_rax()  # Save ASCII code
        
        # Allocate 2 bytes (char + null terminator)
        self.asm.emit_mov_rax_imm64(9)  # mmap syscall
        self.asm.emit_mov_rdi_imm64(0)  # addr = NULL
        self.asm.emit_mov_rsi_imm64(2)  # length = 2 bytes
        self.asm.emit_mov_rdx_imm64(0x3)  # PROT_READ | PROT_WRITE
        self.asm.emit_mov_r10_imm64(0x22)  # MAP_PRIVATE | MAP_ANONYMOUS
        self.asm.emit_bytes(0x49, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF)  # MOV R8, -1
        self.asm.emit_mov_r9_imm64(0)  # offset = 0
        self.asm.emit_syscall()
        
        # RAX now contains allocated address
        self.asm.emit_mov_rdi_rax()  # Save address in RDI
        
        # Store ASCII character
        self.asm.emit_pop_rax()  # Get ASCII code
        self.asm.emit_bytes(0x88, 0x07)  # MOV [RDI], AL (low byte of RAX)
        
        # Store null terminator
        self.asm.emit_bytes(0xC6, 0x47, 0x01, 0x00)  # MOV BYTE [RDI+1], 0
        
        # Return string address
        self.asm.emit_mov_rax_rdi()
        
        print("DEBUG: StringFromChar completed")
        return True

    def compile_string_to_upper(self, node):
        """Convert string to uppercase"""
        if len(node.arguments) < 1:
            raise ValueError("StringToUpper requires 1 argument")
        
        print("DEBUG: Compiling StringToUpper")
        
        # Save registers
        self.asm.emit_push_rbx()
        self.asm.emit_push_rcx()
        self.asm.emit_push_rdx()
        self.asm.emit_push_rsi()
        self.asm.emit_push_rdi()
        
        # Get source string
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rsi_rax()  # Source in RSI
        
        # Calculate string length first
        self.asm.emit_push_rsi()  # Save source for later
        self.asm.emit_mov_rbx_rsi()
        self.asm.emit_mov_rcx_imm64(0)
        
        len_loop = self.asm.create_label()
        len_done = self.asm.create_label()
        
        self.asm.mark_label(len_loop)
        self.asm.emit_bytes(0x8A, 0x03)  # MOV AL, [RBX]
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL
        self.asm.emit_jump_to_label(len_done, "JZ")
        self.asm.emit_bytes(0x48, 0xFF, 0xC3)  # INC RBX
        self.asm.emit_bytes(0x48, 0xFF, 0xC1)  # INC RCX
        self.asm.emit_jump_to_label(len_loop, "JMP")
        
        self.asm.mark_label(len_done)
        # RCX now contains length
        
        # Allocate new string (length + 1 for null terminator)
        self.asm.emit_bytes(0x48, 0xFF, 0xC1)  # INC RCX
        self.asm.emit_mov_rax_imm64(9)  # mmap
        self.asm.emit_mov_rdi_imm64(0)
        self.asm.emit_mov_rsi_rcx()  # size
        self.asm.emit_mov_rdx_imm64(0x3)
        self.asm.emit_mov_r10_imm64(0x22)
        self.asm.emit_bytes(0x49, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF)  # MOV R8, -1
        self.asm.emit_mov_r9_imm64(0)
        self.asm.emit_syscall()
        
        self.asm.emit_mov_rdi_rax()  # Destination in RDI
        self.asm.emit_pop_rsi()  # Restore source
        self.asm.emit_push_rdi()  # Save result address
        
        # Copy and convert loop
        copy_loop = self.asm.create_label()
        copy_done = self.asm.create_label()
        
        self.asm.mark_label(copy_loop)
        self.asm.emit_bytes(0x8A, 0x06)  # MOV AL, [RSI]
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL
        self.asm.emit_jump_to_label(copy_done, "JZ")
        
        # Check if lowercase letter (a-z: 97-122)
        self.asm.emit_bytes(0x3C, 0x61)  # CMP AL, 'a'
        not_lower = self.asm.create_label()
        self.asm.emit_jump_to_label(not_lower, "JB")
        self.asm.emit_bytes(0x3C, 0x7A)  # CMP AL, 'z'
        self.asm.emit_jump_to_label(not_lower, "JA")
        
        # Convert to uppercase (subtract 32)
        self.asm.emit_bytes(0x2C, 0x20)  # SUB AL, 32
        
        self.asm.mark_label(not_lower)
        self.asm.emit_bytes(0x88, 0x07)  # MOV [RDI], AL
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_jump_to_label(copy_loop, "JMP")
        
        self.asm.mark_label(copy_done)
        self.asm.emit_bytes(0xC6, 0x07, 0x00)  # MOV BYTE [RDI], 0
        
        # Return result
        self.asm.emit_pop_rax()  # Get result address
        
        # Restore registers
        self.asm.emit_pop_rdi()
        self.asm.emit_pop_rsi()
        self.asm.emit_pop_rdx()
        self.asm.emit_pop_rcx()
        self.asm.emit_pop_rbx()
        
        print("DEBUG: StringToUpper completed")
        return True

    def compile_string_to_lower(self, node):
        """Convert string to lowercase"""
        if len(node.arguments) < 1:
            raise ValueError("StringToLower requires 1 argument")
        
        print("DEBUG: Compiling StringToLower")
        
        # Save registers
        self.asm.emit_push_rbx()
        self.asm.emit_push_rcx()
        self.asm.emit_push_rdx()
        self.asm.emit_push_rsi()
        self.asm.emit_push_rdi()
        
        # Get source string
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rsi_rax()  # Source in RSI
        
        # Calculate string length
        self.asm.emit_push_rsi()
        self.asm.emit_mov_rbx_rsi()
        self.asm.emit_mov_rcx_imm64(0)
        
        len_loop = self.asm.create_label()
        len_done = self.asm.create_label()
        
        self.asm.mark_label(len_loop)
        self.asm.emit_bytes(0x8A, 0x03)  # MOV AL, [RBX]
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL
        self.asm.emit_jump_to_label(len_done, "JZ")
        self.asm.emit_bytes(0x48, 0xFF, 0xC3)  # INC RBX
        self.asm.emit_bytes(0x48, 0xFF, 0xC1)  # INC RCX
        self.asm.emit_jump_to_label(len_loop, "JMP")
        
        self.asm.mark_label(len_done)
        
        # Allocate new string
        self.asm.emit_bytes(0x48, 0xFF, 0xC1)  # INC RCX
        self.asm.emit_mov_rax_imm64(9)  # mmap
        self.asm.emit_mov_rdi_imm64(0)
        self.asm.emit_mov_rsi_rcx()
        self.asm.emit_mov_rdx_imm64(0x3)
        self.asm.emit_mov_r10_imm64(0x22)
        self.asm.emit_bytes(0x49, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF)  # MOV R8, -1
        self.asm.emit_mov_r9_imm64(0)
        self.asm.emit_syscall()
        
        self.asm.emit_mov_rdi_rax()  # Destination in RDI
        self.asm.emit_pop_rsi()  # Restore source
        self.asm.emit_push_rdi()  # Save result
        
        # Copy and convert loop
        copy_loop = self.asm.create_label()
        copy_done = self.asm.create_label()
        
        self.asm.mark_label(copy_loop)
        self.asm.emit_bytes(0x8A, 0x06)  # MOV AL, [RSI]
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL
        self.asm.emit_jump_to_label(copy_done, "JZ")
        
        # Check if uppercase letter (A-Z: 65-90)
        self.asm.emit_bytes(0x3C, 0x41)  # CMP AL, 'A'
        not_upper = self.asm.create_label()
        self.asm.emit_jump_to_label(not_upper, "JB")
        self.asm.emit_bytes(0x3C, 0x5A)  # CMP AL, 'Z'
        self.asm.emit_jump_to_label(not_upper, "JA")
        
        # Convert to lowercase (add 32)
        self.asm.emit_bytes(0x04, 0x20)  # ADD AL, 32
        
        self.asm.mark_label(not_upper)
        self.asm.emit_bytes(0x88, 0x07)  # MOV [RDI], AL
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_jump_to_label(copy_loop, "JMP")
        
        self.asm.mark_label(copy_done)
        self.asm.emit_bytes(0xC6, 0x07, 0x00)  # MOV BYTE [RDI], 0
        
        # Return result
        self.asm.emit_pop_rax()
        
        # Restore registers
        self.asm.emit_pop_rdi()
        self.asm.emit_pop_rsi()
        self.asm.emit_pop_rdx()
        self.asm.emit_pop_rcx()
        self.asm.emit_pop_rbx()
        
        print("DEBUG: StringToLower completed")
        return True

    def compile_string_contains(self, node):
        """Check if string contains substring (naive search)"""
        if len(node.arguments) < 2:
            raise ValueError("StringContains requires 2 arguments")
        
        print("DEBUG: Compiling StringContains")
        
        # Save registers
        self.asm.emit_push_rbx()
        self.asm.emit_push_rcx()
        self.asm.emit_push_rdx()
        self.asm.emit_push_rsi()
        self.asm.emit_push_rdi()
        self.asm.emit_push_r8()
        self.asm.emit_push_r9()
        
        # Get haystack (string to search in)
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()  # Haystack in RDI
        
        # Get needle (string to search for)
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_mov_rsi_rax()  # Needle in RSI
        
        # Main search loop
        outer_loop = self.asm.create_label()
        found = self.asm.create_label()
        not_found = self.asm.create_label()
        inner_loop = self.asm.create_label()
        continue_outer = self.asm.create_label()
        
        self.asm.mark_label(outer_loop)
        # Check if we've reached end of haystack
        self.asm.emit_bytes(0x8A, 0x07)  # MOV AL, [RDI]
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL
        self.asm.emit_jump_to_label(not_found, "JZ")
        
        # Set up for inner comparison
        self.asm.emit_mov_r8_rdi()  # R8 = current haystack position
        self.asm.emit_mov_r9_rsi()  # R9 = needle start
        
        self.asm.mark_label(inner_loop)
        # Load characters to compare
        self.asm.emit_bytes(0x41, 0x8A, 0x01)  # MOV AL, [R9]
        self.asm.emit_bytes(0x41, 0x8A, 0x18)  # MOV BL, [R8]
        
        # Check if we've matched entire needle
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL
        self.asm.emit_jump_to_label(found, "JZ")  # Needle ended = match found
        
        # Compare characters
        self.asm.emit_bytes(0x38, 0xD8)  # CMP AL, BL
        self.asm.emit_jump_to_label(continue_outer, "JNE")
        
        # Characters match, continue inner loop
        self.asm.emit_bytes(0x49, 0xFF, 0xC0)  # INC R8
        self.asm.emit_bytes(0x49, 0xFF, 0xC1)  # INC R9
        self.asm.emit_jump_to_label(inner_loop, "JMP")
        
        self.asm.mark_label(continue_outer)
        # No match at this position, try next
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_jump_to_label(outer_loop, "JMP")
        
        self.asm.mark_label(found)
        self.asm.emit_mov_rax_imm64(1)
        done_label = self.asm.create_label()
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        self.asm.mark_label(not_found)
        self.asm.emit_mov_rax_imm64(0)
        
        self.asm.mark_label(done_label)
        
        # Restore registers
        self.asm.emit_pop_r9()
        self.asm.emit_pop_r8()
        self.asm.emit_pop_rdi()
        self.asm.emit_pop_rsi()
        self.asm.emit_pop_rdx()
        self.asm.emit_pop_rcx()
        self.asm.emit_pop_rbx()
        
        print("DEBUG: StringContains completed")
        return True
    
    
    def _emit_strlen(self):
        """
        Emit inline strlen(RDI).
        Expects: RDI = pointer to string (NULL-terminated)
        Returns: RAX = length (0 if NULL)
        Preserves: RDI
        """
        start_label = self.asm.create_label()
        end_label = self.asm.create_label()
        
        # Clear RAX (counter)
        self.asm.emit_bytes(0x48, 0x31, 0xC0)   # XOR RAX, RAX
        
        # NULL check
        self.asm.emit_test_rdi_rdi()
        self.asm.emit_jump_to_label(end_label, "JZ")  # If NULL, return 0
        
        # Save RDI
        self.asm.emit_push_rdi()
        
        self.asm.mark_label(start_label)
        self.asm.emit_bytes(0x80, 0x3F, 0x00)   # CMP BYTE [RDI], 0
        null_found = self.asm.create_label()
        self.asm.emit_jump_to_label(null_found, "JE")
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)   # INC RDI
        self.asm.emit_bytes(0x48, 0xFF, 0xC0)   # INC RAX
        self.asm.emit_jump_to_label(start_label, "JMP")
        
        self.asm.mark_label(null_found)
        # Restore RDI (only if we pushed it)
        self.asm.emit_pop_rdi()
        
        self.asm.mark_label(end_label)
        # Result in RAX
        return True
    
    def compile_string_substring(self, node):
        """Extract substring(str, start_index, end_index) - FIXED to use end instead of length"""
        if len(node.arguments) != 3:
            raise ValueError("StringSubstring requires string, start, end")
        
        print("DEBUG: Compiling StringSubstring (end-based semantics)")
        
        # Save registers we'll use
        self.asm.emit_push_rbx()
        self.asm.emit_push_r12()
        self.asm.emit_push_r13()
        self.asm.emit_push_r14()
        
        # Get arguments: R12=string, R13=start, R14=end
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX (string)
        
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_bytes(0x49, 0x89, 0xC5)  # MOV R13, RAX (start)
        
        self.compiler.compile_expression(node.arguments[2])
        self.asm.emit_bytes(0x49, 0x89, 0xC6)  # MOV R14, RAX (end)
        
        # Labels
        null_case = self.asm.create_label()
        empty_result = self.asm.create_label()
        done_label = self.asm.create_label()
        
        # NULL check on string
        self.asm.emit_bytes(0x4D, 0x85, 0xE4)  # TEST R12, R12
        self.asm.emit_jump_to_label(null_case, "JZ")
        
        # Bounds validation: start >= 0, end >= start
        self.asm.emit_bytes(0x4D, 0x85, 0xED)  # TEST R13, R13 (start >= 0)
        self.asm.emit_jump_to_label(empty_result, "JL")  # Jump if less than 0
        
        self.asm.emit_bytes(0x4D, 0x39, 0xEE)  # CMP R14, R13 (end >= start)
        self.asm.emit_jump_to_label(empty_result, "JL")  # Jump if end < start
        
        # Calculate actual length: length = end - start
        self.asm.emit_bytes(0x4C, 0x89, 0xF0)  # MOV RAX, R14 (end)
        self.asm.emit_bytes(0x4C, 0x29, 0xE8)  # SUB RAX, R13 (end - start)
        self.asm.emit_mov_rbx_rax()            # RBX = substring length
        
        # Skip if zero length
        self.asm.emit_bytes(0x48, 0x85, 0xDB)  # TEST RBX, RBX directly
        self.asm.emit_jump_to_label(empty_result, "JZ")
        
        # Allocate buffer (length + 1 for null terminator)
        self.asm.emit_mov_rsi_rbx()  # Length to RSI
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI (for null terminator)
        
        self.asm.emit_mov_rax_imm64(9)  # mmap syscall
        self.asm.emit_mov_rdi_imm64(0)
        # RSI already has size
        self.asm.emit_mov_rdx_imm64(3)  # PROT_READ | PROT_WRITE
        self.asm.emit_mov_r10_imm64(0x22)  # MAP_PRIVATE | MAP_ANONYMOUS
        self.asm.emit_bytes(0x49, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF)  # MOV R8, -1
        self.asm.emit_mov_r9_imm64(0)
        self.asm.emit_syscall()
        
        # Check allocation success
        self.asm.emit_bytes(0x48, 0x83, 0xF8, 0x00)  # CMP RAX, 0
        self.asm.emit_jump_to_label(empty_result, "JL")  # Failed allocation
        
        # RAX now contains the allocated buffer address
        self.asm.emit_mov_rdi_rax()  # Destination in RDI
        self.asm.emit_push_rdi()      # Save destination for return
        
        # Setup source pointer: source = string + start
        self.asm.emit_bytes(0x4C, 0x89, 0xE6)  # MOV RSI, R12 (string pointer)
        self.asm.emit_bytes(0x4C, 0x01, 0xEE)  # ADD RSI, R13 (add start offset)
        
        # Setup count (use calculated length, not end index)
        self.asm.emit_mov_rcx_rbx()  # Length in RCX for copy
        
        # Copy loop with bounds checking
        copy_loop = self.asm.create_label()
        copy_done = self.asm.create_label()
        
        self.asm.mark_label(copy_loop)
        # Check if we have bytes left to copy
        self.asm.emit_test_rcx_rcx()
        self.asm.emit_jump_to_label(copy_done, "JZ")
        
        # Load byte from source
        self.asm.emit_bytes(0x8A, 0x06)  # MOV AL, [RSI]
        
        # Check for null terminator in source
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL
        self.asm.emit_jump_to_label(copy_done, "JZ")
        
        # Store byte to destination
        self.asm.emit_bytes(0x88, 0x07)  # MOV [RDI], AL
        
        # Advance pointers
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_bytes(0x48, 0xFF, 0xC9)  # DEC RCX
        
        self.asm.emit_jump_to_label(copy_loop, "JMP")
        
        self.asm.mark_label(copy_done)
        # Null terminate the destination
        self.asm.emit_bytes(0xC6, 0x07, 0x00)  # MOV BYTE [RDI], 0
        
        # Return the buffer (was saved on stack)
        self.asm.emit_pop_rax()
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        self.asm.mark_label(empty_result)
        # Return empty string for invalid bounds
        empty_str = self.asm.add_string("")
        self.asm.emit_load_data_address('rax', empty_str)
        self.asm.emit_jump_to_label(done_label, "JMP")
        
        self.asm.mark_label(null_case)
        # Return empty string for null input
        empty_str2 = self.asm.add_string("")
        self.asm.emit_load_data_address('rax', empty_str2)
        
        self.asm.mark_label(done_label)
        # Restore registers
        self.asm.emit_pop_r14()
        self.asm.emit_pop_r13()
        self.asm.emit_pop_r12()
        self.asm.emit_pop_rbx()
        
        print("DEBUG: StringSubstring (end-based) completed")
        return True


    def compile_string_char_at(self, node):
        """Get ASCII code of character at a specific index in a string."""
        if len(node.arguments) != 2:
            raise ValueError("StringCharAt requires 2 arguments: string, index")

        print("DEBUG: Compiling StringCharAt")

        # Save registers
        self.asm.emit_push_rbx()
        self.asm.emit_push_rcx()

        # Compile index first
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_mov_rbx_rax() # Index in RBX

        # Compile string
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rcx_rax() # String pointer in RCX

        # NULL check for string
        self.asm.emit_test_rcx_rcx()
        is_null_label = self.asm.create_label()
        self.asm.emit_jump_to_label(is_null_label, "JZ")

        # Add index to string pointer
        self.asm.emit_bytes(0x48, 0x01, 0xD9)      # ADD RCX, RBX

        # Get the character, zero-extending into RAX
        self.asm.emit_bytes(0x48, 0x31, 0xC0)      # XOR RAX, RAX (clear RAX)
        self.asm.emit_bytes(0x8A, 0x01)            # MOV AL, [RCX]

        done_label = self.asm.create_label()
        self.asm.emit_jump_to_label(done_label, "JMP")

        # If string was NULL, return 0
        self.asm.mark_label(is_null_label)
        self.asm.emit_mov_rax_imm64(0)

        self.asm.mark_label(done_label)

        # Restore registers
        self.asm.emit_pop_rcx()
        self.asm.emit_pop_rbx()

        print("DEBUG: StringCharAt completed")
        return True

    def compile_string_extract_until(self, node): # v3 - Robust Implementation
        """Extracts a substring from a buffer from a start offset until a delimiter is found."""
        if len(node.arguments) != 3:
            raise ValueError("StringExtractUntil requires 3 arguments: buffer, offset, delimiter")

        print("DEBUG: Compiling StringExtractUntil (v3 - Robust)")

        # Save registers
        self.asm.emit_push_rbx()
        self.asm.emit_push_r12()
        self.asm.emit_push_r13()

        # 1. Evaluate arguments
        self.compiler.compile_expression(node.arguments[2]) # delimiter
        self.asm.emit_bytes(0x49, 0x89, 0xC5) # MOV R13, RAX

        self.compiler.compile_expression(node.arguments[1]) # offset
        self.asm.emit_mov_rbx_rax() # RBX = offset

        self.compiler.compile_expression(node.arguments[0]) # buffer
        self.asm.emit_add_rax_rbx() # RAX = search_start_ptr
        self.asm.emit_bytes(0x49, 0x89, 0xC4) # MOV R12, RAX (save search_start_ptr)

        # 2. Find the delimiter using the reliable helper
        self.asm.emit_mov_rdi_rax() # RDI = haystack (search_start_ptr)
        self.asm.emit_bytes(0x4C, 0x89, 0xEE) # MOV RSI, R13 (needle/delimiter)
        self._emit_strstr() # Result in RAX (pointer to match or NULL)

        # 3. Handle results
        not_found = self.asm.create_label()
        done = self.asm.create_label()

        self.asm.emit_test_rax_rax()
        self.asm.emit_jump_to_label(not_found, "JZ")

        # --- Delimiter Found ---
        # Calculate length = match_ptr (RAX) - search_start_ptr (R12)
        self.asm.emit_bytes(0x4C, 0x29, 0xE0) # SUB RAX, R12
        self.asm.emit_push_rax() # Save length

        # Allocate new buffer (length + 1 for null)
        self.asm.emit_bytes(0x48, 0xFF, 0xC0) # INC RAX
        self.asm.emit_mov_rsi_rax()
        self.asm.emit_mov_rax_imm64(9)
        self.asm.emit_mov_rdi_imm64(0)
        self.asm.emit_mov_rdx_imm64(3)
        self.asm.emit_mov_r10_imm64(0x22)
        self.asm.emit_bytes(0x49, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF) # MOV R8, -1
        self.asm.emit_mov_r9_imm64(0)
        self.asm.emit_syscall()
        self.asm.emit_push_rax() # Save new buffer pointer

        # Copy the substring: REP MOVSB
        self.asm.emit_mov_rdi_rax() # Dest = new buffer
        self.asm.emit_bytes(0x4C, 0x89, 0xE6) # MOV RSI, R12 (source = search_start_ptr)
        self.asm.emit_bytes(0x48, 0x8B, 0x4C, 0x24, 0x08) # MOV RCX, [RSP+8] (get saved length)
        self.asm.emit_bytes(0xF3, 0xA4) # REP MOVSB

        # Null terminate at the end of the copied data
        self.asm.emit_bytes(0xC6, 0x07, 0x00) # MOV BYTE [RDI], 0

        # Return new buffer pointer (and clean up stack)
        self.asm.emit_pop_rax() # Pop new buffer pointer
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x08) # Pop saved length
        self.asm.emit_jump_to_label(done, "JMP")

        # --- Delimiter Not Found ---
        self.asm.mark_label(not_found)
        self.asm.emit_mov_rax_imm64(0) # Return NULL if not found

        # --- Epilogue ---
        self.asm.mark_label(done)
        self.asm.emit_pop_r13()
        self.asm.emit_pop_r12()
        self.asm.emit_pop_rbx()
        return True

    def compile_string_index_of(self, node):
        if len(node.arguments) < 2 or len(node.arguments) > 3:
            raise ValueError("StringIndexOf requires 2-3 arguments: haystack, needle, [start_pos]")

        print("DEBUG: Compiling StringIndexOf")

        # Save registers
        self.asm.emit_push_rbx()
        self.asm.emit_push_rcx()
        self.asm.emit_push_rdx()
        self.asm.emit_push_rsi()
        self.asm.emit_push_rdi()
        self.asm.emit_push_r8()
        self.asm.emit_push_r9()

        # Get haystack first
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()  # Haystack in RDI
        self.asm.emit_push_rdi()     # Save original haystack pointer for index calculation

        # Get needle
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_bytes(0x49, 0x89, 0xC1)  # MOV R9, RAX (Needle in R9)

        # NEW: Handle optional start_pos argument
        if len(node.arguments) == 3:
            # Get start position
            self.compiler.compile_expression(node.arguments[2])
            # Add start_pos to haystack pointer
            self.asm.emit_bytes(0x48, 0x01, 0xC7)  # ADD RDI, RAX (advance haystack by start_pos)

        # Labels
        outer_loop = self.asm.create_label()
        inner_loop = self.asm.create_label()
        found = self.asm.create_label()
        not_found = self.asm.create_label()
        continue_outer = self.asm.create_label()
        done = self.asm.create_label()

        self.asm.mark_label(outer_loop)
        self.asm.emit_bytes(0x8A, 0x07)  # MOV AL, [RDI]
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL (end of haystack?)
        self.asm.emit_jump_to_label(not_found, "JZ")

        # Setup for inner loop
        self.asm.emit_bytes(0x49, 0x89, 0xF8)  # MOV R8, RDI (current haystack pos)
        self.asm.emit_bytes(0x4C, 0x89, 0xCE)  # MOV RSI, R9 (needle start)

        self.asm.mark_label(inner_loop)
        self.asm.emit_bytes(0x8A, 0x06)        # MOV AL, [RSI]
        self.asm.emit_bytes(0x41, 0x8A, 0x18)  # MOV BL, [R8]
        self.asm.emit_bytes(0x84, 0xC0)        # TEST AL, AL (end of needle?)
        self.asm.emit_jump_to_label(found, "JZ")
        self.asm.emit_bytes(0x38, 0xD8)        # CMP AL, BL
        self.asm.emit_jump_to_label(continue_outer, "JNE")
        self.asm.emit_bytes(0x49, 0xFF, 0xC0)  # INC R8
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_jump_to_label(inner_loop, "JMP")

        self.asm.mark_label(continue_outer)
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_jump_to_label(outer_loop, "JMP")

        self.asm.mark_label(found)
        self.asm.emit_pop_rbx()  # RBX = original haystack pointer
        self.asm.emit_mov_rax_rdi()
        self.asm.emit_bytes(0x48, 0x29, 0xD8)  # SUB RAX, RBX (RAX = index)
        self.asm.emit_jump_to_label(done, "JMP")

        self.asm.mark_label(not_found)
        self.asm.emit_pop_rbx()  # Clean stack
        self.asm.emit_mov_rax_imm64(-1)

        self.asm.mark_label(done)
        self.asm.emit_pop_r9()
        self.asm.emit_pop_r8()
        self.asm.emit_pop_rdi()
        self.asm.emit_pop_rsi()
        self.asm.emit_pop_rdx()
        self.asm.emit_pop_rcx()
        self.asm.emit_pop_rbx()

        print("DEBUG: StringIndexOf completed")
        return True


    def compile_string_trim(self, node):
        """Trim leading/trailing whitespace from a string."""
        if len(node.arguments) != 1:
            raise ValueError("StringTrim requires 1 argument: string")

        print("DEBUG: Compiling StringTrim")

        # Save registers
        self.asm.emit_push_rbx()
        self.asm.emit_push_rcx()
        self.asm.emit_push_rdx()
        self.asm.emit_push_rsi()
        self.asm.emit_push_rdi()

        # Get string pointer
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()  # RDI = original string

        # NULL check
        null_case = self.asm.create_label()
        trim_done_label = self.asm.create_label()
        self.asm.emit_test_rdi_rdi()
        self.asm.emit_jump_to_label(null_case, "JZ")

        # Find start (first non-whitespace)
        start_loop = self.asm.create_label()
        start_done = self.asm.create_label()
        self.asm.mark_label(start_loop)
        self.asm.emit_bytes(0x8A, 0x07)  # MOV AL, [RDI]
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL (end of string)
        self.asm.emit_jump_to_label(start_done, "JZ")
        self.asm.emit_bytes(0x3C, 0x20)  # CMP AL, ' '
        self.asm.emit_jump_to_label(start_done, "JA") # If > ' ', it's not whitespace
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_jump_to_label(start_loop, "JMP")
        self.asm.mark_label(start_done)
        self.asm.emit_mov_rsi_rdi()  # RSI = start of trimmed string

        # Find end (last non-whitespace)
        # First, find the end of the string
        self.asm.emit_mov_rdi_rsi()
        end_find_loop = self.asm.create_label()
        end_find_done = self.asm.create_label()
        self.asm.mark_label(end_find_loop)
        self.asm.emit_bytes(0x8A, 0x07)  # MOV AL, [RDI]
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL
        self.asm.emit_jump_to_label(end_find_done, "JZ")
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_jump_to_label(end_find_loop, "JMP")
        self.asm.mark_label(end_find_done)
        # RDI now points to the null terminator

        # Now, scan backwards from the end
        end_loop = self.asm.create_label()
        end_done = self.asm.create_label()
        self.asm.mark_label(end_loop)
        self.asm.emit_bytes(0x48, 0x39, 0xF7)  # CMP RDI, RSI (if end <= start, we're done)
        self.asm.emit_jump_to_label(end_done, "JBE")
        self.asm.emit_bytes(0x48, 0xFF, 0xCF)  # DEC RDI
        self.asm.emit_bytes(0x8A, 0x07)  # MOV AL, [RDI]
        self.asm.emit_bytes(0x3C, 0x20)  # CMP AL, ' '
        self.asm.emit_jump_to_label(end_done, "JA")
        self.asm.emit_jump_to_label(end_loop, "JMP")
        self.asm.mark_label(end_done)
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI to get correct length

        # Calculate length: RDI (end) - RSI (start)
        self.asm.emit_bytes(0x48, 0x89, 0xF9)  # MOV RCX, RDI
        self.asm.emit_bytes(0x48, 0x29, 0xF1)  # SUB RCX, RSI

        # Allocate new buffer
        self.asm.emit_push_rsi() # Save source pointer
        self.asm.emit_push_rcx() # Save length
        self.asm.emit_bytes(0x48, 0xFF, 0xC1) # INC RCX (for null terminator)
        self.asm.emit_mov_rsi_rcx()
        self.asm.emit_mov_rax_imm64(9)
        self.asm.emit_mov_rdi_imm64(0)
        self.asm.emit_mov_rdx_imm64(3)
        self.asm.emit_mov_r10_imm64(0x22)
        self.asm.emit_bytes(0x49, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF)
        self.asm.emit_mov_r9_imm64(0)
        self.asm.emit_syscall()

        # Copy the substring
        self.asm.emit_mov_rdi_rax() # Destination
        self.asm.emit_pop_rcx()     # Length
        self.asm.emit_pop_rsi()     # Source
        self.asm.emit_bytes(0xF3, 0xA4) # REP MOVSB

        # Null terminate
        self.asm.emit_bytes(0xC6, 0x07, 0x00) # MOV BYTE [RDI], 0
        self.asm.emit_jump_to_label(trim_done_label, "JMP") # Skip null case

        self.asm.mark_label(null_case)
        empty_str = self.asm.add_string("")
        self.asm.emit_load_data_address('rax', empty_str)

        self.asm.mark_label(trim_done_label)
        self.asm.emit_pop_rdi()
        self.asm.emit_pop_rsi()
        self.asm.emit_pop_rdx()
        self.asm.emit_pop_rcx()
        self.asm.emit_pop_rbx()

        print("DEBUG: StringTrim completed")
        return True

    def compile_string_replace(self, node):
        """Replace FIRST occurrence only - simple and reliable"""
        if len(node.arguments) != 3:
            raise ValueError("StringReplace requires 3 arguments: haystack, needle, replacement")
        
        print("DEBUG: Compiling StringReplace (SIMPLE implementation)")
        
        # Save registers
        self.asm.emit_push_rbx()
        self.asm.emit_push_r12()
        self.asm.emit_push_r13()
        self.asm.emit_push_r14()
        
        # Get arguments
        self.compiler.compile_expression(node.arguments[0])  # haystack
        self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX
        
        self.compiler.compile_expression(node.arguments[1])  # needle
        self.asm.emit_bytes(0x49, 0x89, 0xC5)  # MOV R13, RAX
        
        self.compiler.compile_expression(node.arguments[2])  # replacement
        self.asm.emit_bytes(0x49, 0x89, 0xC6)  # MOV R14, RAX
        
        # Find needle in haystack using strstr
        self.asm.emit_bytes(0x4C, 0x89, 0xE7)  # MOV RDI, R12 (haystack)
        self.asm.emit_bytes(0x4C, 0x89, 0xEE)  # MOV RSI, R13 (needle)
        self._emit_strstr()
        
        # If not found, return original haystack
        not_found = self.asm.create_label()
        self.asm.emit_test_rax_rax()
        self.asm.emit_jump_to_label(not_found, "JZ")
        
        # Found at RAX - save match position
        self.asm.emit_mov_rbx_rax()  # RBX = match position
        
        # Calculate lengths
        self.asm.emit_bytes(0x4C, 0x89, 0xE7); self._emit_strlen()  # strlen(haystack)
        self.asm.emit_push_rax()  # Save haystack_len
        
        self.asm.emit_bytes(0x4C, 0x89, 0xEF); self._emit_strlen()  # strlen(needle)
        self.asm.emit_push_rax()  # Save needle_len
        
        self.asm.emit_bytes(0x4C, 0x89, 0xF7); self._emit_strlen()  # strlen(replacement)
        self.asm.emit_push_rax()  # Save replacement_len
        # Stack: [replacement_len], [needle_len], [haystack_len]
        
        # Calculate new size = haystack_len - needle_len + replacement_len + 1
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)  # MOV RAX, [RSP] (replacement_len)
        self.asm.emit_bytes(0x48, 0x2B, 0x44, 0x24, 0x08)  # SUB RAX, [RSP+8] (needle_len)
        self.asm.emit_bytes(0x48, 0x03, 0x44, 0x24, 0x10)  # ADD RAX, [RSP+16] (haystack_len)
        self.asm.emit_bytes(0x48, 0xFF, 0xC0)  # INC RAX (null terminator)
        
        # Allocate new buffer
        self.asm.emit_bytes(0x48, 0x89, 0xC6)  # MOV RSI, RAX (size)
        self.asm.emit_mov_rax_imm64(9)
        self.asm.emit_mov_rdi_imm64(0)
        self.asm.emit_mov_rdx_imm64(3)
        self.asm.emit_mov_r10_imm64(0x22)
        self.asm.emit_bytes(0x49, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF)
        self.asm.emit_mov_r9_imm64(0)
        self.asm.emit_syscall()
        
        # RAX = new buffer, save it
        self.asm.emit_push_rax()  # Save result buffer
        # Stack: [result], [replacement_len], [needle_len], [haystack_len]
        
        # Copy: before_match + replacement + after_match
        
        # 1. Copy before match
        self.asm.emit_bytes(0x48, 0x8B, 0x3C, 0x24)  # MOV RDI, [RSP] (result)
        self.asm.emit_bytes(0x4C, 0x89, 0xE6)  # MOV RSI, R12 (haystack start)
        self.asm.emit_bytes(0x48, 0x89, 0xD9)  # MOV RCX, RBX (match pos)
        self.asm.emit_bytes(0x48, 0x29, 0xF1)  # SUB RCX, RSI (bytes before match)
        self.asm.emit_bytes(0xF3, 0xA4)  # REP MOVSB
        
        # 2. Copy replacement
        self.asm.emit_bytes(0x4C, 0x89, 0xF6)  # MOV RSI, R14 (replacement)
        self.asm.emit_bytes(0x48, 0x8B, 0x4C, 0x24, 0x08)  # MOV RCX, [RSP+8] (replacement_len)
        self.asm.emit_bytes(0xF3, 0xA4)  # REP MOVSB
        
        # 3. Copy after match
        self.asm.emit_bytes(0x48, 0x89, 0xDE)  # MOV RSI, RBX (match position)
        self.asm.emit_bytes(0x48, 0x03, 0x74, 0x24, 0x10)  # ADD RSI, [RSP+16] (skip needle)
        # Copy rest of string
        copy_rest = self.asm.create_label()
        self.asm.mark_label(copy_rest)
        self.asm.emit_bytes(0x8A, 0x06)  # MOV AL, [RSI]
        self.asm.emit_bytes(0x88, 0x07)  # MOV [RDI], AL
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL
        done = self.asm.create_label()
        self.asm.emit_jump_to_label(done, "JZ")
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_jump_to_label(copy_rest, "JMP")
        
        self.asm.mark_label(done)
        # Return result
        self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)  # MOV RAX, [RSP] (result)
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x20)  # ADD RSP, 32 (clean stack)
        
        end_label = self.asm.create_label()
        self.asm.emit_jump_to_label(end_label, "JMP")
        
        # Not found path
        self.asm.mark_label(not_found)
        self.asm.emit_bytes(0x4C, 0x89, 0xE0)  # MOV RAX, R12 (return original)
        
        self.asm.mark_label(end_label)
        # Restore registers
        self.asm.emit_pop_r14()
        self.asm.emit_pop_r13()
        self.asm.emit_pop_r12()
        self.asm.emit_pop_rbx()
        
        print("DEBUG: StringReplace done")
        return True

    


    def _emit_strstr(self):
        """
        Emits inline strstr. A simple substring search.
        Expects: RDI = haystack, RSI = needle.
        Returns: RAX = pointer to match, or 0 if not found.
        Clobbers: RAX, RBX, R8, R9. Does NOT preserve RDI/RSI.
        """
        outer_loop = self.asm.create_label()
        inner_loop = self.asm.create_label()
        found = self.asm.create_label()
        not_found = self.asm.create_label()
        continue_outer = self.asm.create_label()
        done = self.asm.create_label()

        self.asm.mark_label(outer_loop)
        # Check for end of haystack
        self.asm.emit_bytes(0x8A, 0x07)  # MOV AL, [RDI]
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL
        self.asm.emit_jump_to_label(not_found, "JZ")

        # Setup for inner loop
        self.asm.emit_bytes(0x49, 0x89, 0xF8)  # MOV R8, RDI (current haystack pos)
        self.asm.emit_bytes(0x49, 0x89, 0xF1)  # MOV R9, RSI (needle start)

        self.asm.mark_label(inner_loop)
        # Load chars
        self.asm.emit_bytes(0x41, 0x8A, 0x01)  # MOV AL, [R9] (needle char)
        self.asm.emit_bytes(0x41, 0x8A, 0x18)  # MOV BL, [R8] (haystack char)

        # If end of needle, we found a match
        self.asm.emit_bytes(0x84, 0xC0)  # TEST AL, AL
        self.asm.emit_jump_to_label(found, "JZ")

        # Compare chars
        self.asm.emit_bytes(0x38, 0xD8)  # CMP AL, BL
        self.asm.emit_jump_to_label(continue_outer, "JNE")

        # Chars match, advance pointers and continue inner loop
        self.asm.emit_bytes(0x49, 0xFF, 0xC0)  # INC R8
        self.asm.emit_bytes(0x49, 0xFF, 0xC1)  # INC R9
        self.asm.emit_jump_to_label(inner_loop, "JMP")

        self.asm.mark_label(continue_outer)
        # Mismatch, advance haystack pointer and restart outer loop
        self.asm.emit_bytes(0x48, 0xFF, 0xC7)  # INC RDI
        self.asm.emit_jump_to_label(outer_loop, "JMP")

        self.asm.mark_label(found)
        # Match found, RAX should point to the start of the match in the haystack
        # RDI holds this value from the start of the outer loop iteration.
        self.asm.emit_mov_rax_rdi()
        self.asm.emit_jump_to_label(done, "JMP")

        self.asm.mark_label(not_found)
        # Not found, return 0
        self.asm.emit_bytes(0x48, 0x31, 0xC0)  # XOR RAX, RAX

        self.asm.mark_label(done)
        return True

    def compile_string_split(self, node):
        """StringSplit - Correct implementation"""
        if len(node.arguments) != 2:
            raise ValueError("StringSplit requires 2 arguments: haystack, delimiter")
        
        print("DEBUG: Compiling StringSplit - Final fix")
        
        # Save callee-saved registers
        self.asm.emit_push_rbx()
        self.asm.emit_push_r12()  # PUSH R12 (tracked)
        self.asm.emit_push_r13()  # PUSH R13 (tracked)
        self.asm.emit_push_r14()  # PUSH R14 (tracked)
        self.asm.emit_push_r15()  # PUSH R15 (tracked)
        
        # Get arguments
        self.compiler.compile_expression(node.arguments[0])  # haystack
        self.asm.emit_bytes(0x49, 0x89, 0xC4)  # MOV R12, RAX
        
        self.compiler.compile_expression(node.arguments[1])  # delimiter
        self.asm.emit_bytes(0x49, 0x89, 0xC5)  # MOV R13, RAX
        
        # Get delimiter length ONCE and save in RBX
        self.asm.emit_bytes(0x4C, 0x89, 0xEF)  # MOV RDI, R13
        self._emit_strlen()
        self.asm.emit_mov_rbx_rax()  # RBX = delimiter length
        
        # Create result array
        self.asm.emit_mov_rax_imm64(9)
        self.asm.emit_mov_rdi_imm64(0)
        self.asm.emit_mov_rsi_imm64(144)
        self.asm.emit_mov_rdx_imm64(3)
        self.asm.emit_mov_r10_imm64(0x22)
        self.asm.emit_bytes(0x49, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF)  # MOV R8, -1
        self.asm.emit_mov_r9_imm64(0)
        self.asm.emit_syscall()
        
        self.asm.emit_bytes(0x49, 0x89, 0xC6)  # MOV R14, RAX (array)
        
        # Initialize array
        self.asm.emit_mov_rax_imm64(16)
        self.asm.emit_bytes(0x49, 0x89, 0x06)  # MOV [R14], RAX
        self.asm.emit_mov_rax_imm64(0)
        self.asm.emit_bytes(0x49, 0x89, 0x46, 0x08)  # MOV [R14+8], RAX
        
        # R15 = current position
        self.asm.emit_bytes(0x4D, 0x89, 0xE7)  # MOV R15, R12
        
        # Main loop
        loop_start = self.asm.create_label()
        add_final = self.asm.create_label()
        done = self.asm.create_label()
        
        self.asm.mark_label(loop_start)
        
        # Find delimiter
        self.asm.emit_push_rbx()  # FIX: Save RBX (delimiter length) before it's clobbered
        self.asm.emit_bytes(0x4C, 0x89, 0xFF)  # MOV RDI, R15
        self.asm.emit_bytes(0x4C, 0x89, 0xEE)  # MOV RSI, R13
        self._emit_strstr()
        self.asm.emit_pop_rbx()   # FIX: Restore RBX
        
        # Check if found
        self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        self.asm.emit_jump_to_label(add_final, "JZ")
        
        # Save delimiter position
        self.asm.emit_push_rax()
        
        # Calculate length (delimiter_pos - current_pos)
        self.asm.emit_mov_rcx_rax()
        self.asm.emit_bytes(0x4C, 0x29, 0xF9)  # SUB RCX, R15
        
        # Allocate buffer
        self.asm.emit_push_rcx() # Save original length
        self.asm.emit_mov_rdi_imm64(0)
        self.asm.emit_mov_rsi_rcx() # RSI = length
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI (for null terminator)
        self.asm.emit_mov_rdx_imm64(3)
        self.asm.emit_mov_r10_imm64(0x22)
        self.asm.emit_bytes(0x49, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF)
        self.asm.emit_mov_r9_imm64(0)
        self.asm.emit_mov_rax_imm64(9)
        self.asm.emit_syscall()
        
        # Copy segment
        self.asm.emit_mov_rdi_rax() # RDI = destination
        self.asm.emit_push_rdi()    # Save destination buffer address
        
        self.asm.emit_bytes(0x4C, 0x89, 0xFE)  # MOV RSI, R15
        self.asm.emit_bytes(0x48, 0x8B, 0x4C, 0x24, 0x08) # MOV RCX, [RSP+8] (get saved length)
        
        self.asm.emit_bytes(0xF3, 0xA4)  # REP MOVSB
        self.asm.emit_bytes(0xC6, 0x07, 0x00)  # null terminate
        
        # Add to array
        self.asm.emit_pop_rax()  # Get buffer address
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x08) # ADD RSP, 8 (clean up saved length)
        self.asm.emit_bytes(0x49, 0x8B, 0x4E, 0x08)  # MOV RCX, [R14+8]
        self.asm.emit_bytes(0x48, 0xC1, 0xE1, 0x03)  # SHL RCX, 3
        self.asm.emit_bytes(0x49, 0x8D, 0x4C, 0x0E, 0x10)  # LEA RCX, [R14+RCX+16]
        self.asm.emit_bytes(0x48, 0x89, 0x01)  # MOV [RCX], RAX
        self.asm.emit_bytes(0x49, 0xFF, 0x46, 0x08)  # INC [R14+8]
        
        # Move past delimiter: delimiter_pos + delimiter_length
        self.asm.emit_pop_rax()  # Get delimiter position
        self.asm.emit_bytes(0x48, 0x01, 0xD8)  # ADD RAX, RBX (add delimiter length)
        self.asm.emit_bytes(0x49, 0x89, 0xC7)  # MOV R15, RAX (update current position)
        
        self.asm.emit_jump_to_label(loop_start, "JMP")
        
        # Add final segment
        self.asm.mark_label(add_final)
        
        # Get remaining length
        self.asm.emit_bytes(0x4C, 0x89, 0xFF)  # MOV RDI, R15
        self._emit_strlen()
        self.asm.emit_mov_rcx_rax()
        
        # Always add the final segment, even if it's empty.
        # The previous "JZ" check was buggy.

        # Allocate final buffer
        self.asm.emit_push_rcx()  # Save length
        self.asm.emit_mov_rdi_imm64(0)
        self.asm.emit_mov_rsi_rcx()
        self.asm.emit_bytes(0x48, 0xFF, 0xC6)  # INC RSI
        self.asm.emit_mov_rdx_imm64(3)
        self.asm.emit_mov_r10_imm64(0x22)
        self.asm.emit_bytes(0x49, 0xC7, 0xC0, 0xFF, 0xFF, 0xFF, 0xFF)
        self.asm.emit_mov_r9_imm64(0)
        self.asm.emit_mov_rax_imm64(9)
        self.asm.emit_syscall()
        
        # Copy final segment
        self.asm.emit_mov_rdi_rax() # RDI = destination
        self.asm.emit_push_rdi()    # Save destination buffer address
        
        self.asm.emit_bytes(0x4C, 0x89, 0xFE)  # MOV RSI, R15
        self.asm.emit_bytes(0x48, 0x8B, 0x4C, 0x24, 0x08) # MOV RCX, [RSP+8] (get saved length)
        self.asm.emit_bytes(0xF3, 0xA4)  # REP MOVSB
        self.asm.emit_bytes(0xC6, 0x07, 0x00)  # null terminate
        
        # Add to array
        self.asm.emit_pop_rax()  # Get buffer address
        self.asm.emit_bytes(0x48, 0x83, 0xC4, 0x08) # ADD RSP, 8 (clean up saved length)
        self.asm.emit_bytes(0x49, 0x8B, 0x4E, 0x08)  # MOV RCX, [R14+8]
        self.asm.emit_bytes(0x48, 0xC1, 0xE1, 0x03)  # SHL RCX, 3
        self.asm.emit_bytes(0x49, 0x8D, 0x4C, 0x0E, 0x10)  # LEA RCX, [R14+RCX+16]
        self.asm.emit_bytes(0x48, 0x89, 0x01)  # MOV [RCX], RAX
        self.asm.emit_bytes(0x49, 0xFF, 0x46, 0x08)  # INC [R14+8]
        
        self.asm.emit_jump_to_label(done, "JMP")
        self.asm.mark_label(done)
        
        # Return array
        # CRITICAL FIX: Return R14+8 to skip capacity field
        # StringSplit creates: [capacity, count, elem0, elem1, ...]
        # ArrayGet expects:    [count, elem0, elem1, ...]
        # So we return R14+8 to make ArrayGet see the correct format
        self.asm.emit_bytes(0x4C, 0x89, 0xF0)  # MOV RAX, R14
        self.asm.emit_bytes(0x48, 0x83, 0xC0, 0x08)  # ADD RAX, 8
        
        # Restore registers
        self.asm.emit_pop_r15()  # POP R15 (tracked)
        self.asm.emit_pop_r14()  # POP R14 (tracked)
        self.asm.emit_pop_r13()  # POP R13 (tracked)
        self.asm.emit_pop_r12()  # POP R12 (tracked)
        self.asm.emit_pop_rbx()
        
        return True