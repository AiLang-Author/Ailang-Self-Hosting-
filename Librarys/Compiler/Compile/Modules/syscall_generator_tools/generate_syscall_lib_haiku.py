#!/usr/bin/env python3
"""
generate_syscall_lib_haiku.py

Generates AILang syscall wrapper library for Haiku OS.
Maps platform-neutral AILang Sys* functions to Haiku _kern_* syscalls.

Key differences from Linux:
- Haiku syscall numbers are ORDER-based (not fixed)
- Haiku uses _kern_read(fd, POS, buf, size) - note the position argument!
- Haiku has native "areas" for memory (not mmap)
- Haiku has "ports" for IPC (not just pipes)
- Haiku has "teams" (processes) and threads

Usage:
    python3 generate_syscall_lib_haiku.py --output Library.SyscallWrappersHaiku.ailang
    python3 generate_syscall_lib_haiku.py --stdout

Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
Licensed under the Sean Collins Software License (SCSL).
"""

import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

# Import the Haiku syscall table
try:
    from syscall_table_haiku import HAIKU_SYSCALLS, HaikuSyscallCategory
    HAS_TABLE = True
except ImportError:
    print("Warning: syscall_table_haiku.py not found, using inline numbers")
    HAS_TABLE = False

# =============================================================================
# ABSTRACTION MAPPING
# Maps AILang platform-neutral names to Haiku syscalls
# =============================================================================

@dataclass
class SyscallMapping:
    """Maps an AILang abstraction to a Haiku syscall"""
    ailang_name: str          # e.g., "SysRead"
    haiku_name: str           # e.g., "_kern_read"  
    haiku_number: int         # Syscall number (order in syscalls.h)
    args: List[Tuple[str, str]]  # [(ailang_name, ailang_type), ...]
    haiku_args: List[str]     # How to pass args to Haiku (may differ!)
    description: str = ""
    returns: bool = True
    category: str = "misc"
    notes: str = ""           # Important differences from Linux


def get_syscall_number(name: str) -> int:
    """Get syscall number from table, or use fallback"""
    if HAS_TABLE:
        sc = HAIKU_SYSCALLS.get_by_name(name)
        if sc:
            return sc.number
    # Fallback to hardcoded if table not available
    return FALLBACK_NUMBERS.get(name, -1)


# Fallback syscall numbers if table import fails
FALLBACK_NUMBERS = {
    "_kern_read": 140,
    "_kern_write": 142,
    "_kern_open": 104,
    "_kern_close": 149,
    "_kern_seek": 111,
    "_kern_fsync": 109,
    "_kern_dup": 150,
    "_kern_dup2": 151,
    "_kern_create_dir": 113,
    "_kern_remove_dir": 114,
    "_kern_unlink": 118,
    "_kern_rename": 119,
    "_kern_exit_team": 41,
    "_kern_fork": 47,
    "_kern_get_current_team": 43,
    "_kern_socket": 165,
    "_kern_bind": 166,
    "_kern_listen": 169,
    "_kern_accept": 170,
    "_kern_connect": 168,
    "_kern_send": 174,
    "_kern_recv": 171,
    "_kern_map_file": 220,
    "_kern_unmap_memory": 221,
    "_kern_set_memory_protection": 222,
    "_kern_create_pipe": 121,
    "_kern_snooze_etc": 196,
}


# Haiku syscall numbers (from order in syscalls.h)
# These MUST match the order in the header file!
class HaikuSysNum:
    """Haiku syscall numbers - determined by order in syscalls.h"""
    # System
    IS_COMPUTER_ON = 0
    GENERIC_SYSCALL = 1
    GETRLIMIT = 2
    SETRLIMIT = 3
    SHUTDOWN = 4
    GET_SAFEMODE_OPTION = 5
    WAIT_FOR_OBJECTS = 6
    EVENT_QUEUE_CREATE = 7
    EVENT_QUEUE_SELECT = 8
    EVENT_QUEUE_WAIT = 9
    
    # Mutex (10-14)
    MUTEX_LOCK = 10
    MUTEX_UNBLOCK = 11
    MUTEX_SWITCH_LOCK = 12
    MUTEX_SEM_ACQUIRE = 13
    MUTEX_SEM_RELEASE = 14
    
    # Semaphores (15-27)
    CREATE_SEM = 15
    DELETE_SEM = 16
    SWITCH_SEM = 17
    SWITCH_SEM_ETC = 18
    ACQUIRE_SEM = 19
    ACQUIRE_SEM_ETC = 20
    RELEASE_SEM = 21
    RELEASE_SEM_ETC = 22
    GET_SEM_COUNT = 23
    GET_SEM_INFO = 24
    GET_NEXT_SEM_INFO = 25
    SET_SEM_OWNER = 26
    
    # POSIX realtime sem (27-32)
    REALTIME_SEM_OPEN = 27
    REALTIME_SEM_CLOSE = 28
    REALTIME_SEM_UNLINK = 29
    REALTIME_SEM_GET_VALUE = 30
    REALTIME_SEM_POST = 31
    REALTIME_SEM_WAIT = 32
    
    # XSI sem (33-35)
    XSI_SEMGET = 33
    XSI_SEMCTL = 34
    XSI_SEMOP = 35
    
    # XSI msg (36-39)
    XSI_MSGCTL = 36
    XSI_MSGGET = 37
    XSI_MSGRCV = 38
    XSI_MSGSND = 39
    
    # Team/Thread - starting around 40
    LOAD_IMAGE = 40
    EXIT_TEAM = 41
    KILL_TEAM = 42
    GET_CURRENT_TEAM = 43
    WAIT_FOR_TEAM = 44
    WAIT_FOR_CHILD = 45
    EXEC = 46
    FORK = 47
    # ... continues with thread functions
    
    # VFS - file operations start around 95
    MOUNT = 95
    UNMOUNT = 96
    READ_FS_INFO = 97
    WRITE_FS_INFO = 98
    NEXT_DEVICE = 99
    SYNC = 100
    ENTRY_REF_TO_PATH = 101
    NORMALIZE_PATH = 102
    OPEN_ENTRY_REF = 103
    OPEN = 104
    OPEN_DIR_ENTRY_REF = 105
    OPEN_DIR = 106
    OPEN_PARENT_DIR = 107
    FCNTL = 108
    FSYNC = 109
    FLOCK = 110
    SEEK = 111
    CREATE_DIR_ENTRY_REF = 112
    CREATE_DIR = 113
    REMOVE_DIR = 114
    READ_LINK = 115
    CREATE_SYMLINK = 116
    CREATE_LINK = 117
    UNLINK = 118
    RENAME = 119
    CREATE_FIFO = 120
    CREATE_PIPE = 121
    ACCESS = 122
    SELECT = 123
    POLL = 124
    
    # FD operations - around 140+
    READ = 140
    READV = 141
    WRITE = 142
    WRITEV = 143
    IOCTL = 144
    READ_DIR = 145
    REWIND_DIR = 146
    READ_STAT = 147
    WRITE_STAT = 148
    CLOSE = 149
    DUP = 150
    DUP2 = 151
    
    # Socket - around 165+
    SOCKET = 165
    BIND = 166
    SHUTDOWN_SOCKET = 167
    CONNECT = 168
    LISTEN = 169
    ACCEPT = 170
    RECV = 171
    RECVFROM = 172
    RECVMSG = 173
    SEND = 174
    SENDTO = 175
    SENDMSG = 176
    GETSOCKOPT = 177
    SETSOCKOPT = 178
    GETPEERNAME = 179
    GETSOCKNAME = 180
    
    # Time - around 190+
    SET_REAL_TIME_CLOCK = 190
    SYSTEM_TIME = 195
    SNOOZE_ETC = 196
    
    # Area (memory) - around 210+
    CREATE_AREA = 210
    DELETE_AREA = 211
    AREA_FOR = 212
    MAP_FILE = 220
    UNMAP_MEMORY = 221
    SET_MEMORY_PROTECTION = 222
    SYNC_MEMORY = 223


# =============================================================================
# ABSTRACTION LAYER MAPPINGS
# =============================================================================

# Maps our platform-neutral API to Haiku syscalls
MAPPINGS: List[SyscallMapping] = [
    # =========================================================================
    # FILE I/O - Note: Haiku read/write take a POSITION argument!
    # =========================================================================
    SyscallMapping(
        "SysRead", "_kern_read", HaikuSysNum.READ,
        [("fd", "Integer"), ("buf", "Address"), ("count", "Integer")],
        ["fd", "-1", "buf", "count"],  # -1 = use current position
        "Read from file descriptor",
        category="file",
        notes="Haiku adds position arg; use -1 for current position"
    ),
    
    SyscallMapping(
        "SysWrite", "_kern_write", HaikuSysNum.WRITE,
        [("fd", "Integer"), ("buf", "Address"), ("count", "Integer")],
        ["fd", "-1", "buf", "count"],  # -1 = use current position
        "Write to file descriptor",
        category="file",
        notes="Haiku adds position arg; use -1 for current position"
    ),
    
    SyscallMapping(
        "SysPread", "_kern_read", HaikuSysNum.READ,
        [("fd", "Integer"), ("buf", "Address"), ("count", "Integer"), ("offset", "Integer")],
        ["fd", "offset", "buf", "count"],
        "Read at position",
        category="file"
    ),
    
    SyscallMapping(
        "SysPwrite", "_kern_write", HaikuSysNum.WRITE,
        [("fd", "Integer"), ("buf", "Address"), ("count", "Integer"), ("offset", "Integer")],
        ["fd", "offset", "buf", "count"],
        "Write at position",
        category="file"
    ),
    
    SyscallMapping(
        "SysOpen", "_kern_open", HaikuSysNum.OPEN,
        [("path", "Address"), ("flags", "Integer"), ("mode", "Integer")],
        ["-1", "path", "flags", "mode"],  # -1 = AT_FDCWD equivalent
        "Open file",
        category="file",
        notes="Haiku open takes dirfd as first arg; -1 for CWD"
    ),
    
    SyscallMapping(
        "SysClose", "_kern_close", HaikuSysNum.CLOSE,
        [("fd", "Integer")],
        ["fd"],
        "Close file descriptor",
        category="file"
    ),
    
    SyscallMapping(
        "SysLseek", "_kern_seek", HaikuSysNum.SEEK,
        [("fd", "Integer"), ("offset", "Integer"), ("whence", "Integer")],
        ["fd", "offset", "whence"],
        "Seek in file",
        category="file"
    ),
    
    SyscallMapping(
        "SysFsync", "_kern_fsync", HaikuSysNum.FSYNC,
        [("fd", "Integer")],
        ["fd", "0"],  # 0 = sync data and metadata
        "Sync file to disk",
        category="file",
        notes="Haiku takes dataOnly bool; 0=full sync"
    ),
    
    SyscallMapping(
        "SysDup", "_kern_dup", HaikuSysNum.DUP,
        [("oldfd", "Integer")],
        ["oldfd"],
        "Duplicate file descriptor",
        category="file"
    ),
    
    SyscallMapping(
        "SysDup2", "_kern_dup2", HaikuSysNum.DUP2,
        [("oldfd", "Integer"), ("newfd", "Integer")],
        ["oldfd", "newfd", "0"],  # flags=0
        "Duplicate fd to specific number",
        category="file"
    ),
    
    # =========================================================================
    # DIRECTORY
    # =========================================================================
    SyscallMapping(
        "SysMkdir", "_kern_create_dir", HaikuSysNum.CREATE_DIR,
        [("path", "Address"), ("mode", "Integer")],
        ["-1", "path", "mode"],
        "Create directory",
        category="dir"
    ),
    
    SyscallMapping(
        "SysRmdir", "_kern_remove_dir", HaikuSysNum.REMOVE_DIR,
        [("path", "Address")],
        ["-1", "path"],
        "Remove directory",
        category="dir"
    ),
    
    SyscallMapping(
        "SysUnlink", "_kern_unlink", HaikuSysNum.UNLINK,
        [("path", "Address")],
        ["-1", "path"],
        "Delete file",
        category="dir"
    ),
    
    SyscallMapping(
        "SysRename", "_kern_rename", HaikuSysNum.RENAME,
        [("oldpath", "Address"), ("newpath", "Address")],
        ["-1", "oldpath", "-1", "newpath"],
        "Rename file",
        category="dir"
    ),
    
    SyscallMapping(
        "SysGetcwd", "_kern_getcwd", HaikuSysNum.SEEK + 30,  # Approximate
        [("buf", "Address"), ("size", "Integer")],
        ["buf", "size"],
        "Get current working directory",
        category="dir"
    ),
    
    # =========================================================================
    # PROCESS / TEAM
    # =========================================================================
    SyscallMapping(
        "SysExit", "_kern_exit_team", HaikuSysNum.EXIT_TEAM,
        [("code", "Integer")],
        ["code"],
        "Exit process (team)",
        returns=False,
        category="process",
        notes="Haiku calls processes 'teams'"
    ),
    
    SyscallMapping(
        "SysExitGroup", "_kern_exit_team", HaikuSysNum.EXIT_TEAM,
        [("code", "Integer")],
        ["code"],
        "Exit process (same as SysExit on Haiku)",
        returns=False,
        category="process"
    ),
    
    SyscallMapping(
        "SysFork", "_kern_fork", HaikuSysNum.FORK,
        [],
        [],
        "Fork process",
        category="process"
    ),
    
    SyscallMapping(
        "SysGetpid", "_kern_get_current_team", HaikuSysNum.GET_CURRENT_TEAM,
        [],
        [],
        "Get process (team) ID",
        category="process"
    ),
    
    SyscallMapping(
        "SysKill", "_kern_send_signal", HaikuSysNum.FORK + 50,  # Approximate
        [("pid", "Integer"), ("sig", "Integer")],
        ["pid", "sig", "0", "0"],  # userValue=0, flags=0
        "Send signal to process",
        category="process",
        notes="Haiku send_signal has more args"
    ),
    
    # =========================================================================
    # SOCKET
    # =========================================================================
    SyscallMapping(
        "SysSocket", "_kern_socket", HaikuSysNum.SOCKET,
        [("domain", "Integer"), ("type", "Integer"), ("protocol", "Integer")],
        ["domain", "type", "protocol"],
        "Create socket",
        category="socket"
    ),
    
    SyscallMapping(
        "SysBind", "_kern_bind", HaikuSysNum.BIND,
        [("fd", "Integer"), ("addr", "Address"), ("addrlen", "Integer")],
        ["fd", "addr", "addrlen"],
        "Bind socket to address",
        category="socket"
    ),
    
    SyscallMapping(
        "SysListen", "_kern_listen", HaikuSysNum.LISTEN,
        [("fd", "Integer"), ("backlog", "Integer")],
        ["fd", "backlog"],
        "Listen on socket",
        category="socket"
    ),
    
    SyscallMapping(
        "SysAccept", "_kern_accept", HaikuSysNum.ACCEPT,
        [("fd", "Integer"), ("addr", "Address"), ("addrlen", "Address")],
        ["fd", "addr", "addrlen", "0"],  # flags=0
        "Accept connection",
        category="socket"
    ),
    
    SyscallMapping(
        "SysConnect", "_kern_connect", HaikuSysNum.CONNECT,
        [("fd", "Integer"), ("addr", "Address"), ("addrlen", "Integer")],
        ["fd", "addr", "addrlen"],
        "Connect socket",
        category="socket"
    ),
    
    SyscallMapping(
        "SysSend", "_kern_send", HaikuSysNum.SEND,
        [("fd", "Integer"), ("buf", "Address"), ("len", "Integer"), ("flags", "Integer")],
        ["fd", "buf", "len", "flags"],
        "Send data on socket",
        category="socket"
    ),
    
    SyscallMapping(
        "SysRecv", "_kern_recv", HaikuSysNum.RECV,
        [("fd", "Integer"), ("buf", "Address"), ("len", "Integer"), ("flags", "Integer")],
        ["fd", "buf", "len", "flags"],
        "Receive data from socket",
        category="socket"
    ),
    
    # =========================================================================
    # MEMORY - Haiku uses "areas" not mmap!
    # =========================================================================
    SyscallMapping(
        "SysMmap", "_kern_map_file", HaikuSysNum.MAP_FILE,
        [("addr", "Address"), ("length", "Integer"), ("prot", "Integer"),
         ("flags", "Integer"), ("fd", "Integer"), ("offset", "Integer")],
        ['"mmap_region"', "addr", "0", "length", "prot", "flags", "1", "fd", "offset"],
        "Map file to memory (via Haiku map_file)",
        category="memory",
        notes="Haiku uses areas; this maps through map_file syscall"
    ),
    
    SyscallMapping(
        "SysMunmap", "_kern_unmap_memory", HaikuSysNum.UNMAP_MEMORY,
        [("addr", "Address"), ("length", "Integer")],
        ["addr", "length"],
        "Unmap memory region",
        category="memory"
    ),
    
    SyscallMapping(
        "SysMprotect", "_kern_set_memory_protection", HaikuSysNum.SET_MEMORY_PROTECTION,
        [("addr", "Address"), ("length", "Integer"), ("prot", "Integer")],
        ["addr", "length", "prot"],
        "Change memory protection",
        category="memory"
    ),
    
    # =========================================================================
    # TIME
    # =========================================================================
    SyscallMapping(
        "SysNanosleep", "_kern_snooze_etc", HaikuSysNum.SNOOZE_ETC,
        [("req", "Address"), ("rem", "Address")],
        ["0", "0", "0", "rem"],  # Haiku snooze is different!
        "Sleep (via Haiku snooze_etc)",
        category="time",
        notes="Haiku snooze_etc has different signature; wrapper needed"
    ),
    
    # =========================================================================
    # PIPE
    # =========================================================================
    SyscallMapping(
        "SysPipe", "_kern_create_pipe", HaikuSysNum.CREATE_PIPE,
        [("pipefd", "Address")],
        ["pipefd", "0"],  # flags=0
        "Create pipe",
        category="ipc"
    ),
]


# =============================================================================
# CODE GENERATOR
# =============================================================================

def generate_header() -> str:
    return '''// Library.SyscallWrappersHaiku.ailang
// Auto-generated syscall wrappers for Haiku OS x86-64
// Generated by generate_syscall_lib_haiku.py
//
// Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
// Licensed under the Sean Collins Software License (SCSL).
//
// IMPORTANT NOTES:
// - Haiku syscall numbers are determined by ORDER in syscalls.h
// - Haiku _kern_read/_kern_write take a POSITION argument!
// - Haiku uses "teams" (processes), "areas" (memory regions), "ports" (IPC)
// - This file maps platform-neutral Sys* functions to Haiku _kern_* syscalls
//
// DO NOT EDIT MANUALLY - Regenerate with:
//   python3 generate_syscall_lib_haiku.py

LibraryImport.Compiler.CodeEmit.CSyscallTableHaiku

'''

def generate_category_header(cat: str) -> str:
    titles = {
        "file": "FILE I/O",
        "dir": "DIRECTORY",
        "process": "PROCESS (TEAM)",
        "socket": "SOCKET",
        "memory": "MEMORY (AREAS)",
        "time": "TIME",
        "ipc": "IPC (PIPES/PORTS)",
    }
    title = titles.get(cat, cat.upper())
    return f'''
// =============================================================================
// {title}
// =============================================================================

'''

def generate_wrapper(m: SyscallMapping) -> str:
    """Generate single syscall wrapper"""
    
    # Input declarations
    inputs = ""
    for name, typ in m.args:
        inputs += f"    Input: {name}: {typ}\n"
    
    # Output
    output = "    Output: Integer\n" if m.returns else ""
    
    # Build syscall arguments
    # Haiku may need different arg passing than the abstraction
    haiku_args = ", ".join(m.haiku_args) if m.haiku_args else ""
    syscall_call = f"HaikuSysNum.{m.haiku_name.upper().replace('_KERN_', '')}"
    
    if haiku_args:
        full_call = f"SystemCall({syscall_call}, {haiku_args})"
    else:
        full_call = f"SystemCall({syscall_call})"
    
    # Body
    if m.returns:
        body = f'''    Body: {{
        result = {full_call}
        ReturnValue(result)
    }}'''
    else:
        body = f'''    Body: {{
        {full_call}
        // Does not return
    }}'''
    
    # Comment with notes if any
    notes = f"\n// Note: {m.notes}" if m.notes else ""
    
    return f'''// {m.ailang_name} - {m.description}{notes}
// Maps to: {m.haiku_name} (syscall {m.haiku_number})
Function.{m.ailang_name} {{
{inputs}{output}{body}
}}

'''

def generate_file() -> str:
    """Generate complete Haiku wrapper library"""
    
    output = generate_header()
    
    # Group by category
    by_cat: Dict[str, List[SyscallMapping]] = {}
    for m in MAPPINGS:
        by_cat.setdefault(m.category, []).append(m)
    
    # Output in order
    for cat in ["file", "dir", "process", "socket", "memory", "time", "ipc"]:
        if cat in by_cat:
            output += generate_category_header(cat)
            for m in by_cat[cat]:
                output += generate_wrapper(m)
    
    return output

def generate_syscall_table() -> str:
    """Generate the Haiku syscall number table for AILang"""
    
    return '''// Library.CSyscallTableHaiku.ailang
// Haiku x86-64 Syscall Number Table
// Auto-generated - syscall numbers are ORDER-BASED from syscalls.h
//
// Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
// Licensed under the Sean Collins Software License (SCSL).

// IMPORTANT: These numbers MUST match the order in Haiku's
// headers/private/system/syscalls.h
// If Haiku changes the order, these numbers change!

FixedPool.HaikuSysNum {
    // System
    "IS_COMPUTER_ON": Initialize=0
    "GENERIC_SYSCALL": Initialize=1
    "GETRLIMIT": Initialize=2
    "SETRLIMIT": Initialize=3
    
    // Team/Thread (approximate positions)
    "EXIT_TEAM": Initialize=41
    "KILL_TEAM": Initialize=42
    "GET_CURRENT_TEAM": Initialize=43
    "FORK": Initialize=47
    
    // VFS
    "OPEN": Initialize=104
    "SEEK": Initialize=111
    "CREATE_DIR": Initialize=113
    "REMOVE_DIR": Initialize=114
    "UNLINK": Initialize=118
    "RENAME": Initialize=119
    "CREATE_PIPE": Initialize=121
    
    // FD
    "READ": Initialize=140
    "WRITE": Initialize=142
    "CLOSE": Initialize=149
    "DUP": Initialize=150
    "DUP2": Initialize=151
    "FSYNC": Initialize=109
    
    // Socket
    "SOCKET": Initialize=165
    "BIND": Initialize=166
    "CONNECT": Initialize=168
    "LISTEN": Initialize=169
    "ACCEPT": Initialize=170
    "RECV": Initialize=171
    "SEND": Initialize=174
    
    // Memory
    "MAP_FILE": Initialize=220
    "UNMAP_MEMORY": Initialize=221
    "SET_MEMORY_PROTECTION": Initialize=222
    
    // Time
    "SNOOZE_ETC": Initialize=196
}
'''


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate AILang syscall wrappers for Haiku OS"
    )
    parser.add_argument(
        "--output", "-o",
        default="Library.SyscallWrappersHaiku.ailang",
        help="Output file path"
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print to stdout"
    )
    parser.add_argument(
        "--table",
        action="store_true",
        help="Also generate syscall number table"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all mappings"
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("AILang -> Haiku Syscall Mappings:")
        print("=" * 70)
        for m in MAPPINGS:
            print(f"  {m.ailang_name:20} -> {m.haiku_name}")
            if m.notes:
                print(f"    Note: {m.notes}")
        print(f"\nTotal mappings: {len(MAPPINGS)}")
        return
    
    # Generate wrappers
    output = generate_file()
    
    if args.stdout:
        print(output)
    else:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Generated {args.output}")
        print(f"  Wrappers: {len(MAPPINGS)}")
    
    # Generate table if requested
    if args.table and not args.stdout:
        table_output = generate_syscall_table()
        table_path = "Library.CSyscallTableHaiku.ailang"
        with open(table_path, 'w') as f:
            f.write(table_output)
        print(f"  Table: {table_path}")


if __name__ == "__main__":
    main()