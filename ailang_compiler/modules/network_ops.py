#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Network Operations Module for AILANG Compiler
Implements TCP socket operations - CLEANED UP VERSION
"""

import sys
import os
from ailang_parser.ailang_ast import *

class NetworkOps:
    """Handles network/socket operations"""
    
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm
        
    def compile_operation(self, node):
        """Route network operations to specific handlers"""
        try:
            if isinstance(node, FunctionCall):
                function_name = node.function
                
                if function_name == 'SocketCreate':
                    return self.compile_socket_create(node)
                elif function_name == 'SocketBind':
                    return self.compile_socket_bind(node)
                elif function_name == 'SocketListen':
                    return self.compile_socket_listen(node)
                elif function_name == 'SocketAccept':
                    return self.compile_socket_accept(node)
                elif function_name == 'SocketRead':
                    return self.compile_socket_read(node)
                elif function_name == 'SocketWrite':
                    return self.compile_socket_write(node)
                elif function_name == 'SocketClose':
                    return self.compile_socket_close(node)
                elif function_name == 'SocketConnect':
                    return self.compile_socket_connect(node)
                elif function_name == 'SocketSetOption':
                    return self.compile_socket_set_option(node)
                elif function_name == 'System.GetProcessID':
                    return self.compile_get_process_id(node)
                else:
                    return False
            
            return False
            
        except Exception as e:
            print(f"ERROR: Network operation compilation failed: {str(e)}")
            raise
    
    def compile_socket_create(self, node):
        """Create a TCP socket - socket(AF_INET, SOCK_STREAM, 0)"""
        print("DEBUG: Compiling SocketCreate")
        
        self.asm.emit_mov_rax_imm64(41)      # socket syscall
        self.asm.emit_mov_rdi_imm64(2)       # AF_INET
        self.asm.emit_mov_rsi_imm64(1)       # SOCK_STREAM
        self.asm.emit_mov_rdx_imm64(0)       # protocol = 0
        self.asm.emit_syscall()
        
        print("DEBUG: SocketCreate completed")
        return True
    
    def compile_socket_bind(self, node):
        """Bind socket to address and port - bind(sockfd, addr, addrlen)"""
        print("DEBUG: Compiling SocketBind")
        
        if len(node.arguments) < 3:
            print("ERROR: SocketBind requires socket, address, port")
            self.asm.emit_mov_rax_imm64(-1)
            return True
        
        # Get socket fd
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()
        
        # Build sockaddr_in on stack (16 bytes)
        self.asm.emit_sub_rsp_imm8(16)
        # Track the stack allocation (2 QWORDs = 2 pushes equivalent)
        self.compiler.track_push("SocketBind alloc 16 bytes")
        self.compiler.track_push("SocketBind alloc 16 bytes")
        
        # Set family (AF_INET = 2) at [RSP]
        self.asm.emit_mov_word_ptr_rsp(2)
        
        # Get port and convert to network byte order
        self.compiler.compile_expression(node.arguments[2])
        self.asm.emit_xchg_ah_al()  # Swap bytes for network order
        self.asm.emit_mov_word_ptr_rsp_offset(2)  # Store at [RSP+2]
        
        # Get IP address
        self.compiler.compile_expression(node.arguments[1])
        
        # Check if it's 0 (INADDR_ANY) - don't swap
        self.asm.emit_test_rax_rax()
        no_swap_label = self.asm.create_label()
        self.asm.emit_jump_to_label(no_swap_label, "JZ")
        
        # For non-zero IP, convert to network byte order
        self.asm.emit_bswap_eax()
        
        self.asm.mark_label(no_swap_label)
        self.asm.emit_mov_dword_ptr_rsp_offset(4)  # Store at [RSP+4]
        
        # Zero padding at [RSP+8] (8 bytes)
        self.asm.emit_mov_qword_ptr_rsp_offset_imm64(8, 0)
        
        # Set up bind syscall
        self.asm.emit_mov_rax_imm64(49)  # bind syscall
        self.asm.emit_mov_rsi_rsp()      # RSI = pointer to sockaddr_in
        self.asm.emit_mov_rdx_imm64(16)  # RDX = sizeof(sockaddr_in)
        self.asm.emit_syscall()
        
        # Clean up stack
        self.asm.emit_add_rsp_imm8(16)
        # Track the cleanup
        self.compiler.track_pop("SocketBind cleanup 16 bytes")
        self.compiler.track_pop("SocketBind cleanup 16 bytes")
        
        print("DEBUG: SocketBind completed")
        return True
    
    def compile_socket_connect(self, node):
        """Connect socket to address and port - connect(sockfd, addr, addrlen)"""
        print("DEBUG: Compiling SocketConnect")

        if len(node.arguments) < 3:
            print("ERROR: SocketConnect requires socket, address, port")
            self.asm.emit_mov_rax_imm64(-1)
            return True

        # Get socket fd
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()

        # Build sockaddr_in on stack (16 bytes)
        self.asm.emit_sub_rsp_imm8(16)
        # Track the stack allocation (2 QWORDs = 2 pushes equivalent)
        self.compiler.track_push("SocketConnect alloc 16 bytes")
        self.compiler.track_push("SocketConnect alloc 16 bytes")

        # Set family (AF_INET = 2) at [RSP]
        self.asm.emit_mov_word_ptr_rsp(2)

        # Get port and convert to network byte order
        self.compiler.compile_expression(node.arguments[2])
        self.asm.emit_xchg_ah_al()  # Swap bytes
        self.asm.emit_mov_word_ptr_rsp_offset(2)  # Store at [RSP+2]

        # Get IP address
        self.compiler.compile_expression(node.arguments[1])

        # Check if it's 0 (INADDR_ANY) - don't swap
        self.asm.emit_test_rax_rax()
        no_swap_label = self.asm.create_label()
        self.asm.emit_jump_to_label(no_swap_label, "JZ")

        # For non-zero IP, convert to network byte order
        self.asm.emit_bswap_eax()

        self.asm.mark_label(no_swap_label)
        self.asm.emit_mov_dword_ptr_rsp_offset(4)  # Store at [RSP+4]

        # Zero padding at [RSP+8]
        self.asm.emit_mov_qword_ptr_rsp_offset_imm64(8, 0)

        # Set up connect syscall
        self.asm.emit_mov_rax_imm64(42)  # connect syscall
        self.asm.emit_mov_rsi_rsp()      # RSI = pointer to sockaddr_in
        self.asm.emit_mov_rdx_imm64(16)  # RDX = sizeof(sockaddr_in)
        self.asm.emit_syscall()

        # Clean up stack
        self.asm.emit_add_rsp_imm8(16)
        # Track the cleanup
        self.compiler.track_pop("SocketConnect cleanup 16 bytes")
        self.compiler.track_pop("SocketConnect cleanup 16 bytes")

        print("DEBUG: SocketConnect completed")
        return True

    def compile_socket_listen(self, node):
        """Listen for connections - listen(sockfd, backlog)"""
        print("DEBUG: Compiling SocketListen")
        
        if not node.arguments:
            print("ERROR: SocketListen requires socket")
            self.asm.emit_mov_rax_imm64(-1)
            return True
        
        # Get socket fd
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()
        
        # Get backlog, or use default of 5
        if len(node.arguments) > 1:
            self.compiler.compile_expression(node.arguments[1])
            self.asm.emit_mov_rsi_rax()
        else:
            self.asm.emit_mov_rsi_imm64(5)
        
        # listen syscall
        self.asm.emit_mov_rax_imm64(50)
        self.asm.emit_syscall()
        
        print("DEBUG: SocketListen completed")
        return True
    
    def compile_socket_accept(self, node):
        """Accept connection - accept(sockfd, addr, addrlen)"""
        print("DEBUG: Compiling SocketAccept")
        
        if not node.arguments:
            print("ERROR: SocketAccept requires socket")
            self.asm.emit_mov_rax_imm64(-1)
            return True
        
        # Get socket fd
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()
        
        # accept syscall
        self.asm.emit_mov_rax_imm64(43)
        self.asm.emit_xor_rsi_rsi()  # addr = NULL
        self.asm.emit_xor_rdx_rdx()  # addrlen = NULL
        self.asm.emit_syscall()
        
        print("DEBUG: SocketAccept completed")
        return True
    
    def compile_socket_read(self, node):
        """Read from socket - read(fd, buffer, count)"""
        print("DEBUG: Compiling SocketRead")
        
        if len(node.arguments) < 3:
            print("ERROR: SocketRead requires socket, buffer, count")
            self.asm.emit_mov_rax_imm64(-1)
            return True
        
        # Get socket fd
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()
        
        # Get buffer
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_mov_rsi_rax()
        
        # Get count
        self.compiler.compile_expression(node.arguments[2])
        self.asm.emit_mov_rdx_rax()
        
        # read syscall
        self.asm.emit_mov_rax_imm64(0)
        self.asm.emit_syscall()
        
        print("DEBUG: SocketRead completed")
        return True
    
    def compile_socket_write(self, node):
        """Write to socket - write(fd, buffer, count)"""
        print("DEBUG: Compiling SocketWrite")
        
        if len(node.arguments) < 3:
            print("ERROR: SocketWrite requires socket, buffer, count")
            self.asm.emit_mov_rax_imm64(-1)
            return True
        
        # Get socket fd
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()
        
        # Get buffer
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_mov_rsi_rax()
        
        # Get count
        self.compiler.compile_expression(node.arguments[2])
        self.asm.emit_mov_rdx_rax()
        
        # write syscall
        self.asm.emit_mov_rax_imm64(1)
        self.asm.emit_syscall()
        
        print("DEBUG: SocketWrite completed")
        return True
    
    def compile_socket_close(self, node):
        """Close socket - close(fd)"""
        print("DEBUG: Compiling SocketClose")
        
        if not node.arguments:
            print("ERROR: SocketClose requires socket")
            self.asm.emit_mov_rax_imm64(-1)
            return True
        
        # Get socket fd
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()
        
        # close syscall
        self.asm.emit_mov_rax_imm64(3)
        self.asm.emit_syscall()
        
        print("DEBUG: SocketClose completed")
        return True

    def compile_socket_set_option(self, node):
        """Set socket options - setsockopt(sockfd, level, optname, optval, optlen)"""
        print("DEBUG: Compiling SocketSetOption")
        
        if len(node.arguments) < 4:
            print("ERROR: SocketSetOption requires socket, level, option, value")
            self.asm.emit_mov_rax_imm64(-1)
            return True
        
        # Allocate space for option value on stack
        self.asm.emit_sub_rsp_imm8(8)
        # Track the stack allocation (1 QWORD = 1 push equivalent)
        self.compiler.track_push("SocketSetOption alloc 8 bytes")
        
        # Get and store the option value
        self.compiler.compile_expression(node.arguments[3])
        self.asm.emit_mov_qword_ptr_rsp_rax()
        
        # Get socket fd
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()
        
        # Get level
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_mov_rsi_rax()
        
        # Get option name
        self.compiler.compile_expression(node.arguments[2])
        self.asm.emit_mov_rdx_rax()
        
        # Set optval pointer and optlen
        self.asm.emit_mov_r10_rsp()  # optval = pointer to stack
        self.asm.emit_mov_r8_imm64(4)  # optlen = 4 bytes
        
        # setsockopt syscall
        self.asm.emit_mov_rax_imm64(54)
        self.asm.emit_syscall()
        
        # Clean up stack
        self.asm.emit_add_rsp_imm8(8)
        # Track the cleanup
        self.compiler.track_pop("SocketSetOption cleanup 8 bytes")
        
        print("DEBUG: SocketSetOption completed")
        return True
    
    def compile_get_process_id(self, node):
        """Get current process ID"""
        print("DEBUG: Compiling System.GetProcessID")
        
        self.asm.emit_mov_rax_imm64(39)  # getpid syscall
        self.asm.emit_syscall()
        
        print("DEBUG: System.GetProcessID completed")
        return True