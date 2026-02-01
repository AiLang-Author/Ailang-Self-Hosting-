#!/usr/bin/env python3
"""
generate_syscall_unified.py

Generates unified OS-abstracted syscall layer for AILang compiler.
Produces three files:
  1. Library.CSysOps.ailang      - Platform-neutral operation IDs
  2. Library.CSysAdapter.ailang  - OS_* adapter functions  
  3. Library.CSysAPI.ailang      - User-facing File*, Process*, Memory* API

Uses existing syscall_table_linux.py and syscall_table_haiku.py as source.

Usage:
    python3 generate_syscall_unified.py --output-dir Librarys/Compiler/CodeEmit/
    python3 generate_syscall_unified.py --stdout
    python3 generate_syscall_unified.py --list

Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
Licensed under the Sean Collins Software License (SCSL).
"""

import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import IntEnum

# =============================================================================
# UNIFIED SYSCALL MAPPING
# Maps platform-neutral operations to OS-specific implementations
# =============================================================================

class SysCategory(IntEnum):
    FILE = 1
    PROCESS = 2
    MEMORY = 3
    SOCKET = 4
    TIME = 5
    IPC = 6
    DIRECTORY = 7

@dataclass
class UnifiedSyscall:
    """Defines a platform-neutral syscall operation"""
    op_name: str              # e.g., "READ"
    api_name: str             # e.g., "FileRead"
    category: SysCategory
    description: str
    
    # Input arguments for the API function
    args: List[Tuple[str, str]]  # [(name, type), ...]
    
    # OS-specific mappings: how to call SystemCall for each OS
    # Format: {"os": {"num": "SYSCALL_NAME", "call_args": ["arg1", "arg2", ...]}}
    # call_args can include literals like "-1" for Haiku's position arg
    os_map: Dict[str, Dict]
    
    returns: bool = True
    return_type: str = "Integer"


# =============================================================================
# UNIFIED SYSCALL TABLE
# =============================================================================

UNIFIED_SYSCALLS: List[UnifiedSyscall] = [
    # =========================================================================
    # FILE I/O
    # =========================================================================
    UnifiedSyscall(
        "READ", "FileRead", SysCategory.FILE,
        "Read from file descriptor",
        [("fd", "Integer"), ("buf", "Address"), ("count", "Integer")],
        {
            "linux": {"num": "READ", "call_args": ["fd", "buf", "count"]},
            "haiku": {"num": "READ", "call_args": ["fd", "-1", "buf", "count"]},
        }
    ),
    
    UnifiedSyscall(
        "WRITE", "FileWrite", SysCategory.FILE,
        "Write to file descriptor",
        [("fd", "Integer"), ("buf", "Address"), ("count", "Integer")],
        {
            "linux": {"num": "WRITE", "call_args": ["fd", "buf", "count"]},
            "haiku": {"num": "WRITE", "call_args": ["fd", "-1", "buf", "count"]},
        }
    ),
    
    UnifiedSyscall(
        "OPEN", "FileOpen", SysCategory.FILE,
        "Open file",
        [("path", "Address"), ("flags", "Integer"), ("mode", "Integer")],
        {
            "linux": {"num": "OPEN", "call_args": ["path", "flags", "mode"]},
            "haiku": {"num": "OPEN", "call_args": ["-1", "path", "flags", "mode"]},
        }
    ),
    
    UnifiedSyscall(
        "CLOSE", "FileClose", SysCategory.FILE,
        "Close file descriptor",
        [("fd", "Integer")],
        {
            "linux": {"num": "CLOSE", "call_args": ["fd"]},
            "haiku": {"num": "CLOSE", "call_args": ["fd"]},
        }
    ),
    
    UnifiedSyscall(
        "LSEEK", "FileSeek", SysCategory.FILE,
        "Seek in file",
        [("fd", "Integer"), ("offset", "Integer"), ("whence", "Integer")],
        {
            "linux": {"num": "LSEEK", "call_args": ["fd", "offset", "whence"]},
            "haiku": {"num": "SEEK", "call_args": ["fd", "offset", "whence"]},
        }
    ),
    
    UnifiedSyscall(
        "PREAD", "FilePread", SysCategory.FILE,
        "Read at offset",
        [("fd", "Integer"), ("buf", "Address"), ("count", "Integer"), ("offset", "Integer")],
        {
            "linux": {"num": "PREAD64", "call_args": ["fd", "buf", "count", "offset"]},
            "haiku": {"num": "READ", "call_args": ["fd", "offset", "buf", "count"]},
        }
    ),
    
    UnifiedSyscall(
        "PWRITE", "FilePwrite", SysCategory.FILE,
        "Write at offset",
        [("fd", "Integer"), ("buf", "Address"), ("count", "Integer"), ("offset", "Integer")],
        {
            "linux": {"num": "PWRITE64", "call_args": ["fd", "buf", "count", "offset"]},
            "haiku": {"num": "WRITE", "call_args": ["fd", "offset", "buf", "count"]},
        }
    ),
    
    UnifiedSyscall(
        "FSYNC", "FileSync", SysCategory.FILE,
        "Sync file to disk",
        [("fd", "Integer")],
        {
            "linux": {"num": "FSYNC", "call_args": ["fd"]},
            "haiku": {"num": "FSYNC", "call_args": ["fd", "0"]},  # 0 = full sync
        }
    ),
    
    UnifiedSyscall(
        "DUP", "FileDup", SysCategory.FILE,
        "Duplicate file descriptor",
        [("oldfd", "Integer")],
        {
            "linux": {"num": "DUP", "call_args": ["oldfd"]},
            "haiku": {"num": "DUP", "call_args": ["oldfd"]},
        }
    ),
    
    UnifiedSyscall(
        "DUP2", "FileDup2", SysCategory.FILE,
        "Duplicate fd to specific number",
        [("oldfd", "Integer"), ("newfd", "Integer")],
        {
            "linux": {"num": "DUP2", "call_args": ["oldfd", "newfd"]},
            "haiku": {"num": "DUP2", "call_args": ["oldfd", "newfd", "0"]},
        }
    ),
    
    # =========================================================================
    # DIRECTORY
    # =========================================================================
    UnifiedSyscall(
        "MKDIR", "DirCreate", SysCategory.DIRECTORY,
        "Create directory",
        [("path", "Address"), ("mode", "Integer")],
        {
            "linux": {"num": "MKDIR", "call_args": ["path", "mode"]},
            "haiku": {"num": "CREATE_DIR", "call_args": ["-1", "path", "mode"]},
        }
    ),
    
    UnifiedSyscall(
        "RMDIR", "DirRemove", SysCategory.DIRECTORY,
        "Remove directory",
        [("path", "Address")],
        {
            "linux": {"num": "RMDIR", "call_args": ["path"]},
            "haiku": {"num": "REMOVE_DIR", "call_args": ["-1", "path"]},
        }
    ),
    
    UnifiedSyscall(
        "UNLINK", "FileUnlink", SysCategory.DIRECTORY,
        "Delete file",
        [("path", "Address")],
        {
            "linux": {"num": "UNLINK", "call_args": ["path"]},
            "haiku": {"num": "UNLINK", "call_args": ["-1", "path"]},
        }
    ),
    
    UnifiedSyscall(
        "RENAME", "FileRename", SysCategory.DIRECTORY,
        "Rename file",
        [("oldpath", "Address"), ("newpath", "Address")],
        {
            "linux": {"num": "RENAME", "call_args": ["oldpath", "newpath"]},
            "haiku": {"num": "RENAME", "call_args": ["-1", "oldpath", "-1", "newpath"]},
        }
    ),
    
    UnifiedSyscall(
        "GETCWD", "DirGetCwd", SysCategory.DIRECTORY,
        "Get current working directory",
        [("buf", "Address"), ("size", "Integer")],
        {
            "linux": {"num": "GETCWD", "call_args": ["buf", "size"]},
            "haiku": {"num": "GETCWD", "call_args": ["buf", "size"]},
        }
    ),
    
    UnifiedSyscall(
        "CHDIR", "DirChange", SysCategory.DIRECTORY,
        "Change working directory",
        [("path", "Address")],
        {
            "linux": {"num": "CHDIR", "call_args": ["path"]},
            "haiku": {"num": "SETCWD", "call_args": ["-1", "path"]},
        }
    ),
    
    # =========================================================================
    # PROCESS
    # =========================================================================
    UnifiedSyscall(
        "EXIT", "ProcessExit", SysCategory.PROCESS,
        "Exit process",
        [("code", "Integer")],
        {
            "linux": {"num": "EXIT_GROUP", "call_args": ["code"]},
            "haiku": {"num": "EXIT_TEAM", "call_args": ["code"]},
        },
        returns=False
    ),
    
    UnifiedSyscall(
        "FORK", "ProcessFork", SysCategory.PROCESS,
        "Fork process",
        [],
        {
            "linux": {"num": "FORK", "call_args": []},
            "haiku": {"num": "FORK", "call_args": []},
        }
    ),
    
    UnifiedSyscall(
        "GETPID", "ProcessGetPid", SysCategory.PROCESS,
        "Get process ID",
        [],
        {
            "linux": {"num": "GETPID", "call_args": []},
            "haiku": {"num": "GET_CURRENT_TEAM", "call_args": []},
        }
    ),
    
    UnifiedSyscall(
        "KILL", "ProcessKill", SysCategory.PROCESS,
        "Send signal to process",
        [("pid", "Integer"), ("sig", "Integer")],
        {
            "linux": {"num": "KILL", "call_args": ["pid", "sig"]},
            "haiku": {"num": "SEND_SIGNAL", "call_args": ["pid", "sig", "0", "0"]},
        }
    ),
    
    # =========================================================================
    # MEMORY
    # =========================================================================
    UnifiedSyscall(
        "MMAP", "MemoryMap", SysCategory.MEMORY,
        "Map memory region",
        [("addr", "Address"), ("length", "Integer"), ("prot", "Integer"),
         ("flags", "Integer"), ("fd", "Integer"), ("offset", "Integer")],
        {
            "linux": {"num": "MMAP", "call_args": ["addr", "length", "prot", "flags", "fd", "offset"]},
            "haiku": {"num": "MAP_FILE", "call_args": ['"mmap"', "addr", "0", "length", "prot", "flags", "1", "fd", "offset"]},
        }
    ),
    
    UnifiedSyscall(
        "MUNMAP", "MemoryUnmap", SysCategory.MEMORY,
        "Unmap memory region",
        [("addr", "Address"), ("length", "Integer")],
        {
            "linux": {"num": "MUNMAP", "call_args": ["addr", "length"]},
            "haiku": {"num": "UNMAP_MEMORY", "call_args": ["addr", "length"]},
        }
    ),
    
    UnifiedSyscall(
        "MPROTECT", "MemoryProtect", SysCategory.MEMORY,
        "Change memory protection",
        [("addr", "Address"), ("length", "Integer"), ("prot", "Integer")],
        {
            "linux": {"num": "MPROTECT", "call_args": ["addr", "length", "prot"]},
            "haiku": {"num": "SET_MEMORY_PROTECTION", "call_args": ["addr", "length", "prot"]},
        }
    ),
    
    UnifiedSyscall(
        "BRK", "MemoryBrk", SysCategory.MEMORY,
        "Change data segment size",
        [("addr", "Address")],
        {
            "linux": {"num": "BRK", "call_args": ["addr"]},
            # Haiku doesn't have brk - would need different approach
            "haiku": {"num": "BRK", "call_args": ["addr"], "note": "May not be supported"},
        }
    ),
    
    # =========================================================================
    # SOCKET
    # =========================================================================
    UnifiedSyscall(
        "SOCKET", "SocketCreate", SysCategory.SOCKET,
        "Create socket",
        [("domain", "Integer"), ("type", "Integer"), ("protocol", "Integer")],
        {
            "linux": {"num": "SOCKET", "call_args": ["domain", "type", "protocol"]},
            "haiku": {"num": "SOCKET", "call_args": ["domain", "type", "protocol"]},
        }
    ),
    
    UnifiedSyscall(
        "BIND", "SocketBind", SysCategory.SOCKET,
        "Bind socket to address",
        [("fd", "Integer"), ("addr", "Address"), ("addrlen", "Integer")],
        {
            "linux": {"num": "BIND", "call_args": ["fd", "addr", "addrlen"]},
            "haiku": {"num": "BIND", "call_args": ["fd", "addr", "addrlen"]},
        }
    ),
    
    UnifiedSyscall(
        "LISTEN", "SocketListen", SysCategory.SOCKET,
        "Listen on socket",
        [("fd", "Integer"), ("backlog", "Integer")],
        {
            "linux": {"num": "LISTEN", "call_args": ["fd", "backlog"]},
            "haiku": {"num": "LISTEN", "call_args": ["fd", "backlog"]},
        }
    ),
    
    UnifiedSyscall(
        "ACCEPT", "SocketAccept", SysCategory.SOCKET,
        "Accept connection",
        [("fd", "Integer"), ("addr", "Address"), ("addrlen", "Address")],
        {
            "linux": {"num": "ACCEPT", "call_args": ["fd", "addr", "addrlen"]},
            "haiku": {"num": "ACCEPT", "call_args": ["fd", "addr", "addrlen", "0"]},
        }
    ),
    
    UnifiedSyscall(
        "CONNECT", "SocketConnect", SysCategory.SOCKET,
        "Connect socket",
        [("fd", "Integer"), ("addr", "Address"), ("addrlen", "Integer")],
        {
            "linux": {"num": "CONNECT", "call_args": ["fd", "addr", "addrlen"]},
            "haiku": {"num": "CONNECT", "call_args": ["fd", "addr", "addrlen"]},
        }
    ),
    
    UnifiedSyscall(
        "SEND", "SocketSend", SysCategory.SOCKET,
        "Send data on socket",
        [("fd", "Integer"), ("buf", "Address"), ("len", "Integer"), ("flags", "Integer")],
        {
            "linux": {"num": "SENDTO", "call_args": ["fd", "buf", "len", "flags", "0", "0"]},
            "haiku": {"num": "SEND", "call_args": ["fd", "buf", "len", "flags"]},
        }
    ),
    
    UnifiedSyscall(
        "RECV", "SocketRecv", SysCategory.SOCKET,
        "Receive data from socket",
        [("fd", "Integer"), ("buf", "Address"), ("len", "Integer"), ("flags", "Integer")],
        {
            "linux": {"num": "RECVFROM", "call_args": ["fd", "buf", "len", "flags", "0", "0"]},
            "haiku": {"num": "RECV", "call_args": ["fd", "buf", "len", "flags"]},
        }
    ),
    
    # =========================================================================
    # TIME
    # =========================================================================
    UnifiedSyscall(
        "NANOSLEEP", "TimeSleep", SysCategory.TIME,
        "Sleep for specified time",
        [("req", "Address"), ("rem", "Address")],
        {
            "linux": {"num": "NANOSLEEP", "call_args": ["req", "rem"]},
            "haiku": {"num": "SNOOZE_ETC", "call_args": ["0", "0", "0", "rem"]},
        }
    ),
    
    # =========================================================================
    # IPC
    # =========================================================================
    UnifiedSyscall(
        "PIPE", "PipeCreate", SysCategory.IPC,
        "Create pipe",
        [("pipefd", "Address")],
        {
            "linux": {"num": "PIPE", "call_args": ["pipefd"]},
            "haiku": {"num": "CREATE_PIPE", "call_args": ["pipefd", "0"]},
        }
    ),
]


# =============================================================================
# CODE GENERATORS
# =============================================================================

def generate_sysops() -> str:
    """Generate Library.CSysOps.ailang - Platform-neutral operation IDs"""
    
    output = '''// Library.CSysOps.ailang
// Platform-neutral syscall operation identifiers
// Auto-generated by generate_syscall_unified.py
//
// Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
// Licensed under the Sean Collins Software License (SCSL).
//
// These IDs are used internally by the OS adapter layer.
// User code should use the API functions (FileRead, ProcessExit, etc.)

// =============================================================================
// OPERATION IDS
// =============================================================================

FixedPool.SysOp {
'''
    
    for i, sc in enumerate(UNIFIED_SYSCALLS):
        output += f'    "{sc.op_name}": Initialize={i}\n'
    
    output += '''    "COUNT": Initialize=''' + str(len(UNIFIED_SYSCALLS)) + '''
}

// =============================================================================
// OS TARGET IDS
// =============================================================================

FixedPool.OS {
    "LINUX": Initialize=1, CanChange=False
    "HAIKU": Initialize=2, CanChange=False
    "BSD": Initialize=3, CanChange=False
    "WINDOWS": Initialize=4, CanChange=False
}
'''
    return output


def generate_adapter() -> str:
    """Generate Library.CSysAdapter.ailang - OS_* adapter functions"""
    
    output = '''// Library.CSysAdapter.ailang
// OS-specific syscall adapters
// Auto-generated by generate_syscall_unified.py
//
// Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
// Licensed under the Sean Collins Software License (SCSL).
//
// These functions handle OS-specific syscall signature differences.
// They read Emit.os to determine which syscall convention to use.

LibraryImport.Compiler.CodeEmit.CEmitCore
LibraryImport.Compiler.CodeEmit.CSysOps
LibraryImport.Compiler.CodeEmit.CSyscallTable
LibraryImport.Compiler.CodeEmit.CSyscallTableHaiku

'''
    
    # Group by category
    by_cat: Dict[SysCategory, List[UnifiedSyscall]] = {}
    for sc in UNIFIED_SYSCALLS:
        by_cat.setdefault(sc.category, []).append(sc)
    
    cat_names = {
        SysCategory.FILE: "FILE I/O",
        SysCategory.DIRECTORY: "DIRECTORY",
        SysCategory.PROCESS: "PROCESS",
        SysCategory.MEMORY: "MEMORY",
        SysCategory.SOCKET: "SOCKET",
        SysCategory.TIME: "TIME",
        SysCategory.IPC: "IPC",
    }
    
    for cat in SysCategory:
        if cat not in by_cat:
            continue
        
        output += f'''
// =============================================================================
// {cat_names.get(cat, cat.name)}
// =============================================================================

'''
        for sc in by_cat[cat]:
            output += generate_adapter_function(sc)
    
    return output


def generate_adapter_function(sc: UnifiedSyscall) -> str:
    """Generate single OS_* adapter function"""
    
    func_name = f"OS_{sc.op_name.title().replace('_', '')}"
    
    # Input declarations
    inputs = ""
    for name, typ in sc.args:
        inputs += f"    Input: {name}: {typ}\n"
    
    # Output
    if sc.returns:
        output_decl = f"    Output: {sc.return_type}\n"
    else:
        output_decl = ""
    
    # Generate OS-specific branches
    branches = ""
    
    for os_name, os_info in sc.os_map.items():
        os_const = f"OS.{os_name.upper()}"
        syscall_num = os_info["num"]
        call_args = os_info["call_args"]
        
        # Build syscall table reference
        if os_name == "linux":
            num_ref = f"SysNum.{syscall_num}"
        elif os_name == "haiku":
            num_ref = f"HaikuSysNum.{syscall_num}"
        else:
            num_ref = f"{os_name.title()}SysNum.{syscall_num}"
        
        # Build SystemCall invocation
        if call_args:
            args_str = ", ".join(call_args)
            syscall_inv = f"SystemCall({num_ref}, {args_str})"
        else:
            syscall_inv = f"SystemCall({num_ref})"
        
        if sc.returns:
            branch_body = f'''result = {syscall_inv}
            ReturnValue(result)'''
        else:
            branch_body = f'''{syscall_inv}
            // Does not return'''
        
        branches += f'''        IfCondition EqualTo(Emit.os, {os_const}) ThenBlock: {{
            {branch_body}
        }}
'''
    
    return f'''// {func_name} - {sc.description}
Function.{func_name} {{
{inputs}{output_decl}    Body: {{
{branches}    }}
}}

'''


def generate_api() -> str:
    """Generate Library.CSysAPI.ailang - User-facing API"""
    
    output = '''// Library.CSysAPI.ailang
// User-facing platform-neutral syscall API
// Auto-generated by generate_syscall_unified.py
//
// Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
// Licensed under the Sean Collins Software License (SCSL).
//
// This is the API that user code should use.
// These functions delegate to OS_* adapters which handle OS differences.
//
// Example usage:
//   fd = FileOpen(filename, flags, mode)
//   bytes = FileRead(fd, buffer, count)
//   FileClose(fd)
//   ProcessExit(0)

LibraryImport.Compiler.CodeEmit.CSysAdapter

'''
    
    # Group by category
    by_cat: Dict[SysCategory, List[UnifiedSyscall]] = {}
    for sc in UNIFIED_SYSCALLS:
        by_cat.setdefault(sc.category, []).append(sc)
    
    cat_names = {
        SysCategory.FILE: "FILE I/O",
        SysCategory.DIRECTORY: "DIRECTORY",
        SysCategory.PROCESS: "PROCESS",
        SysCategory.MEMORY: "MEMORY",
        SysCategory.SOCKET: "SOCKET",
        SysCategory.TIME: "TIME",
        SysCategory.IPC: "IPC",
    }
    
    for cat in SysCategory:
        if cat not in by_cat:
            continue
        
        output += f'''
// =============================================================================
// {cat_names.get(cat, cat.name)}
// =============================================================================

'''
        for sc in by_cat[cat]:
            output += generate_api_function(sc)
    
    return output


def generate_api_function(sc: UnifiedSyscall) -> str:
    """Generate single user-facing API function"""
    
    adapter_name = f"OS_{sc.op_name.title().replace('_', '')}"
    
    # Input declarations
    inputs = ""
    arg_names = []
    for name, typ in sc.args:
        inputs += f"    Input: {name}: {typ}\n"
        arg_names.append(name)
    
    # Output
    if sc.returns:
        output_decl = f"    Output: {sc.return_type}\n"
    else:
        output_decl = ""
    
    # Call to adapter
    if arg_names:
        adapter_call = f"{adapter_name}({', '.join(arg_names)})"
    else:
        adapter_call = f"{adapter_name}()"
    
    if sc.returns:
        body = f'''        result = {adapter_call}
        ReturnValue(result)'''
    else:
        body = f'''        {adapter_call}'''
    
    return f'''// {sc.api_name} - {sc.description}
Function.{sc.api_name} {{
{inputs}{output_decl}    Body: {{
{body}
    }}
}}

'''


def list_operations():
    """Print all unified operations"""
    
    print("\nUnified Syscall Operations:")
    print("=" * 80)
    
    by_cat: Dict[SysCategory, List[UnifiedSyscall]] = {}
    for sc in UNIFIED_SYSCALLS:
        by_cat.setdefault(sc.category, []).append(sc)
    
    for cat in SysCategory:
        if cat not in by_cat:
            continue
        
        print(f"\n  {cat.name}:")
        for sc in by_cat[cat]:
            args = ", ".join(f"{n}: {t}" for n, t in sc.args)
            ret = f" -> {sc.return_type}" if sc.returns else ""
            print(f"    {sc.api_name}({args}){ret}")
            for os_name, os_info in sc.os_map.items():
                print(f"      {os_name}: {os_info['num']}({', '.join(os_info['call_args'])})")
    
    print(f"\nTotal operations: {len(UNIFIED_SYSCALLS)}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate unified OS-abstracted syscall layer for AILang"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=".",
        help="Output directory for generated files"
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print all files to stdout"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all operations"
    )
    parser.add_argument(
        "--ops-only",
        action="store_true",
        help="Generate only CSysOps.ailang"
    )
    parser.add_argument(
        "--adapter-only",
        action="store_true",
        help="Generate only CSysAdapter.ailang"
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Generate only CSysAPI.ailang"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_operations()
        return
    
    # Determine what to generate
    # If none of the *_only flags are set, generate all
    if args.ops_only or args.adapter_only or args.api_only:
        gen_ops = args.ops_only
        gen_adapter = args.adapter_only
        gen_api = args.api_only
    else:
        gen_ops = True
        gen_adapter = True
        gen_api = True
    
    # Generate files
    files = []
    
    if gen_ops:
        files.append(("Library.CSysOps.ailang", generate_sysops()))
    
    if gen_adapter:
        files.append(("Library.CSysAdapter.ailang", generate_adapter()))
    
    if gen_api:
        files.append(("Library.CSysAPI.ailang", generate_api()))
    
    # Output
    if args.stdout:
        for filename, content in files:
            print(f"// {'='*70}")
            print(f"// {filename}")
            print(f"// {'='*70}")
            print(content)
            print()
    else:
        import os
        os.makedirs(args.output_dir, exist_ok=True)
        
        for filename, content in files:
            path = os.path.join(args.output_dir, filename)
            with open(path, 'w') as f:
                f.write(content)
            print(f"Generated {path}")
        
        print(f"\nTotal operations: {len(UNIFIED_SYSCALLS)}")
        print("Files generated:")
        print("  - Library.CSysOps.ailang    (operation IDs)")
        print("  - Library.CSysAdapter.ailang (OS adapters)")
        print("  - Library.CSysAPI.ailang    (user API)")


if __name__ == "__main__":
    main()