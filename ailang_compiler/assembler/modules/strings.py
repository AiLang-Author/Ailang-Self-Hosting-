# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_compiler/assembler/modules/strings.py
"""String handling and printing operations"""

import struct

class StringOperations:
    """String storage and printing operations"""
    
    def add_string(self, s: str) -> int:
        """Add string to data section, return offset"""
        try:
            if s in self.strings:
                print(f"DEBUG: String '{s}' already in data section at offset {self.strings[s]}")
                return self.strings[s]
            
            offset = len(self.data)
            self.strings[s] = offset
            self.data.extend(s.encode('utf-8'))
            self.data.append(0)  # Null terminator
            print(f"DEBUG: Added string '{s}' to data section at offset {offset}")
            return offset
        except Exception as e:
            print(f"ERROR: Failed to add string '{s}': {str(e)}")
            raise
    
    def emit_print_string(self, s: str):
        """Emit code to print a string exactly as provided"""
        try:
            # Store the string in data section
            offset = self.add_string(s)
            byte_length = len(s.encode('utf-8'))
            
            print(f"DEBUG: Printing string '{s[:30]}...', offset {offset}, length {byte_length}")
            
            # Print the string
            self.emit_mov_rax_imm64(1)  # sys_write
            self.emit_mov_rdi_imm64(1)  # stdout
            self.emit_load_data_address('rsi', offset)
            self.emit_mov_rdx_imm64(byte_length)
            self.emit_syscall()
            
            # Add newline if the string doesn't end with one
            if not s.endswith('\n'):
                newline_offset = self.add_string("\n")
                self.emit_mov_rax_imm64(1)  # sys_write
                self.emit_mov_rdi_imm64(1)  # stdout
                self.emit_load_data_address('rsi', newline_offset)
                self.emit_mov_rdx_imm64(1)
                self.emit_syscall()
                print(f"Added newline after string")
            
        except Exception as e:
            print(f"ERROR in emit_print_string: {e}")
            raise
    
    def emit_print_system_string(self, s: str):
        """Emit code to print a system/debug string - bypasses any pool mechanism"""
        try:
            # Direct string storage and printing for system messages
            offset = self.add_string(s)
            byte_length = len(s.encode('utf-8'))
            
            # Save all registers to avoid interference
            self.emit_push_rax()
            self.emit_push_rdi()
            self.emit_push_rsi()
            self.emit_push_rdx()
            
            # Print the string
            self.emit_mov_rax_imm64(1)  # sys_write
            self.emit_mov_rdi_imm64(1)  # stdout
            self.emit_load_data_address('rsi', offset)
            self.emit_mov_rdx_imm64(byte_length)
            self.emit_syscall()
            
            # Restore registers
            self.emit_pop_rdx()
            self.emit_pop_rsi()
            self.emit_pop_rdi()
            self.emit_pop_rax()

    
            
        except Exception as e:
            print(f"ERROR in emit_print_system_string: {e}")
            raise
    
    def emit_print_string_raw(self, s: str):
        """Emit code to print a string without adding to data section"""
        try:
            offset = self.add_string(s)
            byte_length = len(s.encode('utf-8'))
        
            self.emit_mov_rax_imm64(1)
            self.emit_mov_rdi_imm64(1)
            data_addr = self.data_base_address + offset
            self.emit_mov_rsi_imm64(data_addr)
            self.emit_mov_rdx_imm64(byte_length)
            self.emit_syscall()
            print(f"DEBUG: Printed raw string '{s}', byte length {byte_length}")
        except Exception as e:
            print(f"ERROR: Failed to print raw string '{s}': {str(e)}")
            raise
    
    def emit_print_number(self):
        """Print number in RAX with proper sign handling"""
        print("DEBUG: Number printing with sign checking")
        
        # Save all registers we'll use
        self.emit_push_rax()
        self.emit_push_rbx()
        self.emit_push_rdx()
        self.emit_push_rsi()
        self.emit_push_rdi()
        
        # Check if negative
        self.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        positive_label = self.create_label()
        self.emit_jump_to_label(positive_label, "JNS")  # Jump if not signed (positive)
        
        # Negative number - print minus sign first
        self.emit_push_rax()  # Save the negative value
        
        # Print '-' character
        self.emit_mov_rax_imm64(1)  # sys_write
        self.emit_mov_rdi_imm64(1)  # stdout  
        minus_offset = self.add_string("-")
        self.emit_load_data_address('rsi', minus_offset)
        self.emit_mov_rdx_imm64(1)  # length = 1
        self.emit_syscall()
        
        # Negate the value to make it positive
        self.emit_pop_rax()  # Get value back
        self.emit_bytes(0x48, 0xF7, 0xD8)  # NEG RAX (negate)
        
        self.mark_label(positive_label)
        
        # Now RAX has positive value - continue with digit conversion
        # Allocate buffer on stack
        self.emit_bytes(0x48, 0x83, 0xEC, 0x20)  # SUB RSP, 32
        
        # Point RSI to end of buffer
        self.emit_bytes(0x48, 0x8D, 0x74, 0x24, 0x1F)  # LEA RSI, [RSP+31]
        self.emit_bytes(0xC6, 0x06, 0x00)  # MOV BYTE [RSI], 0 (null terminator)
        
        # Restore RAX from stack (saved at beginning)
        self.emit_bytes(0x48, 0x8B, 0x44, 0x24, 0x40)  # MOV RAX, [RSP+64]
        
        # Check if already positive (from above) or needs another check
        self.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        already_positive = self.create_label()
        self.emit_jump_to_label(already_positive, "JNS")
        self.emit_bytes(0x48, 0xF7, 0xD8)  # NEG RAX if still negative
        self.mark_label(already_positive)
        
        # Set divisor to 10
        self.emit_bytes(0x48, 0xBB, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)  # MOV RBX, 10
        
        # Check if zero
        self.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        self.emit_bytes(0x75, 0x08)  # JNE +8 (skip zero case)
        
        # Zero case
        self.emit_bytes(0x48, 0xFF, 0xCE)  # DEC RSI
        self.emit_bytes(0xC6, 0x06, 0x30)  # MOV BYTE [RSI], '0'
        self.emit_bytes(0xEB, 0x14)  # JMP to print section
        
        # Conversion loop (for non-zero)
        self.emit_bytes(0x48, 0x31, 0xD2)  # XOR RDX, RDX
        self.emit_bytes(0x48, 0xF7, 0xF3)  # DIV RBX (RAX/10, remainder in RDX)
        self.emit_bytes(0x48, 0x83, 0xC2, 0x30)  # ADD RDX, '0'
        self.emit_bytes(0x48, 0xFF, 0xCE)  # DEC RSI
        self.emit_bytes(0x88, 0x16)  # MOV [RSI], DL
        self.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        self.emit_bytes(0x75, 0xEC)  # JNE -20 (loop back)
        
        # Print section - calculate length
        self.emit_bytes(0x48, 0x8D, 0x54, 0x24, 0x1F)  # LEA RDX, [RSP+31]
        self.emit_bytes(0x48, 0x29, 0xF2)  # SUB RDX, RSI (length)
        
        # Write syscall
        self.emit_bytes(0x48, 0xB8, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)  # MOV RAX, 1
        self.emit_bytes(0x48, 0xBF, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)  # MOV RDI, 1
        self.emit_bytes(0x0F, 0x05)  # SYSCALL
        
        # Clean up stack
        self.emit_bytes(0x48, 0x83, 0xC4, 0x20)  # ADD RSP, 32
        
        # Restore registers
        self.emit_pop_rdi()
        self.emit_pop_rsi()
        self.emit_pop_rdx()
        self.emit_pop_rbx()
        self.emit_pop_rax()
        
    def emit_clear_direction_flag(self):
        """CLD - Clear direction flag for forward string ops"""
        self.emit_bytes(0xFC)
        print("DEBUG: CLD")

    def emit_rep_compare_bytes(self):
        """REPE CMPSB - Compare bytes in [RSI] and [RDI] while equal"""
        # REPE prefix is F3, CMPSB is A6
        self.emit_bytes(0xF3, 0xA6)
        print("DEBUG: REPE CMPSB")

    def emit_rep_scan_byte(self):
        """REPNE SCASB - Scan for byte in AL in [RDI] while not equal"""
        # REPNE prefix is F2, SCASB is AE
        self.emit_bytes(0xF2, 0xAE)
        print("DEBUG: REPNE SCASB")