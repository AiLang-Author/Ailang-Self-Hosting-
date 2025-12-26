#!/usr/bin/env python3

# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

"""
Process Operations Module for AILANG Compiler
Provides process management syscalls: fork, exec, wait, pipes, etc.
"""

import sys
import os
import struct
from ailang_parser.ailang_ast import *

class ProcessOps:
    """Handles process management syscalls"""
    
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm
    
    def compile_operation(self, node):
        """Route to specific process operation handlers"""
        op_map = {
            'ProcessFork': self.compile_process_fork,
            'ProcessGetPID': self.compile_process_getpid,
            'ProcessGetTID': self.compile_process_gettid,
            'ProcessExit': self.compile_process_exit,
            'ProcessWait': self.compile_process_wait,
            'ProcessKill': self.compile_process_kill,
            'ProcessExec': self.compile_process_exec,
            'PipeCreate': self.compile_pipe_create,
            'PipeRead': self.compile_pipe_read,
            'PipeWrite': self.compile_pipe_write,
            'ProcessSleep': self.compile_process_sleep,
        }
        
        handler = op_map.get(node.function)
        if handler:
            handler(node)
            return True
        return False
    
    def compile_process_fork(self, node):
        """
        ProcessFork() -> pid
        Creates a new process (fork syscall)
        Returns: child PID in parent, 0 in child, -1 on error
        """
        print("DEBUG: Compiling ProcessFork")
        
        # fork syscall number is 57
        self.asm.emit_mov_rax_imm64(57)
        self.asm.emit_syscall()
        
        # RAX now contains: parent gets child PID, child gets 0
        # No need to push since caller expects result in expression context
        
        print("DEBUG: ProcessFork completed")
        return True
    
    def compile_process_getpid(self, node):
        """
        ProcessGetPID() -> pid
        Get current process ID
        """
        print("DEBUG: Compiling ProcessGetPID")
        
        # getpid syscall number is 39
        self.asm.emit_mov_rax_imm64(39)
        self.asm.emit_syscall()
        
        print("DEBUG: ProcessGetPID completed")
        return True
    
    def compile_process_gettid(self, node):
        """
        ProcessGetTID() -> tid
        Get current thread ID
        """
        print("DEBUG: Compiling ProcessGetTID")
        
        # gettid syscall number is 186
        self.asm.emit_mov_rax_imm64(186)
        self.asm.emit_syscall()
        
        print("DEBUG: ProcessGetTID completed")
        return True
    
    def compile_process_exit(self, node):
        """
        ProcessExit(status_code)
        Exit with given status code
        """
        print("DEBUG: Compiling ProcessExit")
        
        if len(node.arguments) != 1:
            raise ValueError("ProcessExit requires 1 argument: status_code")
        
        # Compile status code
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()
        
        # exit syscall number is 60
        self.asm.emit_mov_rax_imm64(60)
        self.asm.emit_syscall()
        
        print("DEBUG: ProcessExit completed")
        return True
    
    def compile_process_wait(self, node):
        """
        ProcessWait(pid, options) -> exited_pid
        Wait for child process to change state
        Arguments:
          pid: process ID to wait for (-1 for any child)
          options: wait options (0 for blocking wait)
        Returns: PID of exited child, or -1 on error
        """
        print("DEBUG: Compiling ProcessWait")
        
        if len(node.arguments) != 2:
            raise ValueError("ProcessWait requires 2 arguments: pid, options")
        
        # Allocate space for status on stack
        self.asm.emit_sub_rsp_imm8(8)
        
        # Compile options (arg 2) -> R10
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_mov_r10_rax()
        
        # Compile pid (arg 1) -> RDI
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()
        
        # RSI = pointer to status (on stack)
        self.asm.emit_mov_rsi_rsp()
        
        # RDX = NULL (rusage)
        self.asm.emit_xor_rdx_rdx()
        
        # wait4 syscall number is 61
        self.asm.emit_mov_rax_imm64(61)
        self.asm.emit_syscall()
        
        # Clean up stack
        self.asm.emit_add_rsp_imm8(8)
        
        # RAX has the returned PID (or -1 on error)
        
        print("DEBUG: ProcessWait completed")
        return True
    
    def compile_process_kill(self, node):
        """
        ProcessKill(pid, signal) -> result
        Send signal to process
        Arguments:
          pid: target process ID
          signal: signal number (e.g., 9 for SIGKILL, 15 for SIGTERM)
        Returns: 0 on success, -1 on error
        """
        print("DEBUG: Compiling ProcessKill")
        
        if len(node.arguments) != 2:
            raise ValueError("ProcessKill requires 2 arguments: pid, signal")
        
        # Compile signal (arg 2) -> RSI
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_mov_rsi_rax()
        
        # Compile pid (arg 1) -> RDI
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()
        
        # kill syscall number is 62
        self.asm.emit_mov_rax_imm64(62)
        self.asm.emit_syscall()
        
        print("DEBUG: ProcessKill completed")
        return True
    
    def compile_process_exec(self, node):
        """
        ProcessExec(program_path, argv_array) -> does not return on success
        Execute a program with arguments
        Arguments:
          program_path: path to executable (string)
          argv_array: pointer to array of string pointers (NULL-terminated)
        
        Note: This function does not return on success. On error, returns -1.
        
        Example usage in AILANG:
          // Allocate argv array (3 pointers + NULL = 4 * 8 = 32 bytes)
          argv = MemoryAllocate(32)
          [argv + 0] = program_name_string
          [argv + 8] = arg1_string
          [argv + 16] = arg2_string
          [argv + 24] = 0  // NULL terminator
          ProcessExec("/bin/ls", argv)
        """
        print("DEBUG: Compiling ProcessExec")
        
        if len(node.arguments) != 2:
            raise ValueError("ProcessExec requires 2 arguments: program_path, argv_array")
        
        # Compile argv array pointer (arg 2) -> RSI
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_mov_rsi_rax()
        
        # Compile program path (arg 1) -> RDI
        self.compiler.compile_expression(node.arguments[0])
        self.asm.emit_mov_rdi_rax()
        
        # RDX = NULL (no envp for now)
        self.asm.emit_xor_rdx_rdx()
        
        # execve syscall number is 59
        self.asm.emit_mov_rax_imm64(59)
        self.asm.emit_syscall()
        
        # If we reach here, exec failed - RAX contains error code (negative)
        
        print("DEBUG: ProcessExec completed")
        return True
    
    def compile_pipe_create(self, node):
        """
        PipeCreate() -> pipe_handle
        Create a pipe (returns pointer to [read_fd, write_fd])
        
        Returns: Pointer to 16-byte structure containing:
          [0-7]: read_fd (64-bit)
          [8-15]: write_fd (64-bit)
        """
        print("DEBUG: Compiling PipeCreate")
        
        # Allocate 16 bytes on heap for the pipe fds
        self.asm.emit_mov_rax_imm64(9)  # sys_mmap
        self.asm.emit_mov_rdi_imm64(0)  # addr = NULL
        self.asm.emit_mov_rsi_imm64(16)  # length = 16 bytes
        self.asm.emit_mov_rdx_imm64(3)  # PROT_READ | PROT_WRITE
        self.asm.emit_mov_r10_imm64(0x22)  # MAP_PRIVATE | MAP_ANONYMOUS
        self.asm.emit_mov_r8_imm64(0xFFFFFFFFFFFFFFFF)  # fd = -1
        self.asm.emit_mov_r9_imm64(0)  # offset = 0
        self.asm.emit_syscall()
        
        # Save buffer pointer
        self.asm.emit_push_rax()
        
        # Call pipe syscall
        # RDI = pointer to buffer (for the two fds)
        self.asm.emit_mov_rdi_rax()
        self.asm.emit_mov_rax_imm64(22)  # sys_pipe
        self.asm.emit_syscall()
        
        # Check for error
        self.asm.emit_test_rax_rax()
        error_label = self.asm.create_label()
        success_label = self.asm.create_label()
        self.asm.emit_js_label(error_label)  # Jump if negative
        
        # Success - return buffer pointer
        self.asm.emit_pop_rax()  # Get buffer pointer back
        self.asm.emit_jump_to_label(success_label, "JMP")
        
        # Error - return NULL
        self.asm.mark_label(error_label)
        self.asm.emit_add_rsp_imm8(8)  # Clean stack
        self.asm.emit_mov_rax_imm64(0)
        
        self.asm.mark_label(success_label)
        
        print("DEBUG: PipeCreate completed")
        return True
    
    def compile_pipe_read(self, node):
        """
        PipeRead(pipe_handle, buffer, max_bytes) -> bytes_read
        Read from pipe's read end
        Arguments:
          pipe_handle: pointer from PipeCreate
          buffer: destination buffer
          max_bytes: maximum bytes to read
        Returns: number of bytes read, or -1 on error
        """
        print("DEBUG: Compiling PipeRead")
        
        if len(node.arguments) != 3:
            raise ValueError("PipeRead requires 3 arguments: pipe_handle, buffer, max_bytes")
        
        # Compile max_bytes -> RDX
        self.compiler.compile_expression(node.arguments[2])
        self.asm.emit_mov_rdx_rax()
        
        # Compile buffer -> RSI
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_mov_rsi_rax()
        
        # Compile pipe_handle and get read_fd
        self.compiler.compile_expression(node.arguments[0])
        # Read fd is at [pipe_handle + 0]
        self.asm.emit_mov_rdi_deref_rax()
        
        # read syscall
        self.asm.emit_mov_rax_imm64(0)
        self.asm.emit_syscall()
        
        print("DEBUG: PipeRead completed")
        return True
    
    def compile_pipe_write(self, node):
        """
        PipeWrite(pipe_handle, buffer, num_bytes) -> bytes_written
        Write to pipe's write end
        Arguments:
          pipe_handle: pointer from PipeCreate
          buffer: source buffer
          num_bytes: number of bytes to write
        Returns: number of bytes written, or -1 on error
        """
        print("DEBUG: Compiling PipeWrite")
        
        if len(node.arguments) != 3:
            raise ValueError("PipeWrite requires 3 arguments: pipe_handle, buffer, num_bytes")
        
        # Compile num_bytes -> RDX
        self.compiler.compile_expression(node.arguments[2])
        self.asm.emit_mov_rdx_rax()
        
        # Compile buffer -> RSI
        self.compiler.compile_expression(node.arguments[1])
        self.asm.emit_mov_rsi_rax()
        
        # Compile pipe_handle and get write_fd
        self.compiler.compile_expression(node.arguments[0])
        # Write fd is at [pipe_handle + 8]
        self.asm.emit_mov_rdi_deref_rax_offset(8)
        
        # write syscall
        self.asm.emit_mov_rax_imm64(1)
        self.asm.emit_syscall()
        
        print("DEBUG: PipeWrite completed")
        return True
    
    def compile_process_sleep(self, node):
        """
        ProcessSleep(seconds) -> result
        Sleep for specified number of seconds
        Returns: 0 on success, -1 on error
        """
        print("DEBUG: Compiling ProcessSleep")
        
        if len(node.arguments) != 1:
            raise ValueError("ProcessSleep requires 1 argument: seconds")
        
        # Allocate timespec struct on stack (16 bytes)
        # struct timespec { tv_sec: 8 bytes, tv_nsec: 8 bytes }
        self.asm.emit_sub_rsp_imm8(16)
        
        # Compile seconds argument
        self.compiler.compile_expression(node.arguments[0])
        
        # Store seconds in [RSP] (tv_sec)
        self.asm.emit_mov_qword_ptr_rsp_rax()
        
        # Zero out nanoseconds at [RSP + 8] (tv_nsec)
        self.asm.emit_mov_qword_ptr_rsp_offset_imm64(8, 0)
        
        # nanosleep syscall
        self.asm.emit_mov_rdi_rsp()  # req = RSP
        self.asm.emit_xor_rsi_rsi()  # rem = NULL
        self.asm.emit_mov_rax_imm64(35)  # sys_nanosleep
        self.asm.emit_syscall()
        
        # Clean up stack
        self.asm.emit_add_rsp_imm8(16)
        
        print("DEBUG: ProcessSleep completed")
        return True