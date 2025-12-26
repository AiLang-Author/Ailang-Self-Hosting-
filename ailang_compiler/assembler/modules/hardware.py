# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_compiler/assembler/modules/hardware.py
"""Hardware access operations - port I/O, MSR, control registers"""

import struct

class HardwareOperations:
    """Hardware register and port I/O operations"""
    
    # === CONTROL REGISTER ACCESS ===
    
    def emit_read_cr(self, cr_number: int):
        """MOV RAX, CRn - Read control register"""
        if cr_number == 0:
            self.emit_bytes(0x0F, 0x20, 0xC0)  # MOV RAX, CR0
        elif cr_number == 2:
            self.emit_bytes(0x0F, 0x20, 0xD0)  # MOV RAX, CR2
        elif cr_number == 3:
            self.emit_bytes(0x0F, 0x20, 0xD8)  # MOV RAX, CR3
        elif cr_number == 4:
            self.emit_bytes(0x0F, 0x20, 0xE0)  # MOV RAX, CR4
        elif cr_number == 8:
            self.emit_bytes(0x0F, 0x20, 0xC0)  # MOV RAX, CR8 (actually TPR)
        else:
            raise ValueError(f"Invalid control register: CR{cr_number}")
        
        print(f"DEBUG: MOV RAX, CR{cr_number}")
    
    def emit_write_cr(self, cr_number: int):
        """MOV CRn, RAX - Write control register"""
        if cr_number == 0:
            self.emit_bytes(0x0F, 0x22, 0xC0)  # MOV CR0, RAX
        elif cr_number == 2:
            self.emit_bytes(0x0F, 0x22, 0xD0)  # MOV CR2, RAX
        elif cr_number == 3:
            self.emit_bytes(0x0F, 0x22, 0xD8)  # MOV CR3, RAX
        elif cr_number == 4:
            self.emit_bytes(0x0F, 0x22, 0xE0)  # MOV CR4, RAX
        elif cr_number == 8:
            self.emit_bytes(0x0F, 0x22, 0xC0)  # MOV CR8, RAX
        else:
            raise ValueError(f"Invalid control register: CR{cr_number}")
        
        print(f"DEBUG: MOV CR{cr_number}, RAX")
    
    # === MODEL-SPECIFIC REGISTERS ===
    
    def emit_read_msr(self):
        """RDMSR - Read model-specific register (ECX contains MSR number)"""
        self.emit_bytes(0x0F, 0x32)
        print("DEBUG: RDMSR")
    
    def emit_write_msr(self):
        """WRMSR - Write model-specific register"""
        self.emit_bytes(0x0F, 0x30)
        print("DEBUG: WRMSR")
    
    # === PORT I/O OPERATIONS ===
    
    def emit_in_al_dx(self):
        """IN AL, DX - Read byte from port in DX"""
        self.emit_bytes(0xEC)
        print("DEBUG: IN AL, DX")
    
    def emit_in_ax_dx(self):
        """IN AX, DX - Read word from port in DX"""
        self.emit_bytes(0x66, 0xED)
        print("DEBUG: IN AX, DX")
    
    def emit_in_eax_dx(self):
        """IN EAX, DX - Read dword from port in DX"""
        self.emit_bytes(0xED)
        print("DEBUG: IN EAX, DX")
    
    def emit_out_dx_al(self):
        """OUT DX, AL - Write byte to port in DX"""
        self.emit_bytes(0xEE)
        print("DEBUG: OUT DX, AL")
    
    def emit_out_dx_ax(self):
        """OUT DX, AX - Write word to port in DX"""
        self.emit_bytes(0x66, 0xEF)
        print("DEBUG: OUT DX, AX")
    
    def emit_out_dx_eax(self):
        """OUT DX, EAX - Write dword to port in DX"""
        self.emit_bytes(0xEF)
        print("DEBUG: OUT DX, EAX")
    
    def emit_port_read(self, port: int, size: str):
        """High-level port read operation"""
        # Load port number into DX
        self.emit_bytes(0x66, 0xBA)  # MOV DX, imm16
        self.emit_bytes(*struct.pack('<H', port))
        
        if size == "byte":
            self.emit_in_al_dx()
            # Zero-extend AL to RAX
            self.emit_bytes(0x48, 0x0F, 0xB6, 0xC0)  # MOVZX RAX, AL
        elif size == "word":
            self.emit_in_ax_dx()
            # Zero-extend AX to RAX
            self.emit_bytes(0x48, 0x0F, 0xB7, 0xC0)  # MOVZX RAX, AX
        elif size == "dword":
            self.emit_in_eax_dx()
            # Zero-extend EAX to RAX (automatic in 64-bit mode)
        else:
            raise ValueError(f"Invalid port I/O size: {size}")
        
        print(f"DEBUG: Port read from {hex(port)} ({size})")
    
    def emit_port_write(self, port: int, size: str):
        """High-level port write operation (value in RAX)"""
        # Load port number into DX
        self.emit_bytes(0x66, 0xBA)  # MOV DX, imm16
        self.emit_bytes(*struct.pack('<H', port))
        
        if size == "byte":
            self.emit_out_dx_al()
        elif size == "word":
            self.emit_out_dx_ax()
        elif size == "dword":
            self.emit_out_dx_eax()
        else:
            raise ValueError(f"Invalid port I/O size: {size}")
        
        print(f"DEBUG: Port write to {hex(port)} ({size})")