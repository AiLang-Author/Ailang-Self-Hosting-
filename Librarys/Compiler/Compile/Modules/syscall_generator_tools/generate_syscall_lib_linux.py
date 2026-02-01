#!/usr/bin/env python3
"""
generate_syscall_lib.py

Generates AILang syscall wrapper library by importing from syscall_table.py.
Reuses the existing comprehensive syscall table as the single source of truth.

Usage:
    python3 generate_syscall_lib.py --output Library.SyscallWrappers.ailang
    python3 generate_syscall_lib.py --stdout
    python3 generate_syscall_lib.py --category FILE_IO  # Only file operations
    python3 generate_syscall_lib.py --list              # List all syscalls

Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
Licensed under the Sean Collins Software License (SCSL).
"""

import argparse
import sys
from pathlib import Path
from typing import List, Set, Optional

# Import the existing syscall table
from syscall_table_linux import (
    LINUX_X64_SYSCALLS, 
    SyscallDescriptor, 
    SyscallCategory,
    LinuxX86_64SyscallTable
)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Syscalls that don't return (noreturn)
NORETURN_SYSCALLS = {"exit", "exit_group"}

# Argument name to AILang type mapping
# Default is Integer, these are Address (pointers)
POINTER_ARGS = {
    "buf", "buffer", "ubuf", "kbuf",
    "filename", "pathname", "path", "name", "oldname", "newname",
    "oldpath", "newpath", "target", "linkpath",
    "statbuf", "stat", "statfs",
    "addr", "uaddr", "uaddr2", "shmaddr", "old_address", "new_address",
    "dirp", "dirent",
    "iov", "vec", "lvec", "rvec",
    "msg", "msgp", "mmsg",
    "tv", "tz", "tp", "req", "rem", "timeout", "utimes", "times",
    "act", "oldact", "set", "oldset", "uthese", "uinfo",
    "uss", "uoss", "sigmask",
    "fds", "readfds", "writefds", "exceptfds", "ufds",
    "events", "event",
    "pipefd", "fildes", "sv",
    "optval", "optlen",
    "argv", "envp", "uargs",
    "status", "wstatus", "infop",
    "rusage", "ru", "usage",
    "rlim", "new_rlim", "old_rlim",
    "u_info", "info", "buf", "ubuf",
    "attr", "uattr", "attr_uptr",
    "handle", "head", "head_ptr", "len_ptr",
    "ctxp", "iocbpp", "iocb", "result",
    "user_mask", "user_mask_ptr", "nmask",
    "list", "waiters",
    "pages", "nodes", "old_nodes", "new_nodes",
    "vec", "policy",
    "umod", "data", "argp",
    "u_name", "u_msg_ptr", "u_notification", "u_mqstat", "u_omqstat",
    "u_abs_timeout", "u_msg_prio",
    "segments", "cmdline_ptr",
    "rseq",
    "how",  # for open_how struct
}

# Categories to include by default (core functionality)
DEFAULT_CATEGORIES = {
    SyscallCategory.FILE_IO,
    SyscallCategory.MEMORY,
    SyscallCategory.PROCESS,
    SyscallCategory.NETWORK,
    SyscallCategory.TIME,
    SyscallCategory.SIGNAL,
    SyscallCategory.IPC,
    SyscallCategory.SYSTEM,
}

# Syscalls to skip (obsolete, unimplemented, or problematic)
SKIP_SYSCALLS = {
    "uselib",           # Obsolete
    "create_module",    # Obsolete  
    "get_kernel_syms",  # Obsolete
    "query_module",     # Obsolete
    "nfsservctl",       # Obsolete
    "getpmsg",          # Unimplemented
    "putpmsg",          # Unimplemented
    "afs_syscall",      # Unimplemented
    "tuxcall",          # Unimplemented
    "security",         # Unimplemented
    "vserver",          # Unimplemented
    "_sysctl",          # Obsolete
    "ustat",            # Obsolete
    "epoll_ctl_old",    # Obsolete
    "epoll_wait_old",   # Obsolete
}

# =============================================================================
# CODE GENERATOR
# =============================================================================

def syscall_to_ailang_name(name: str) -> str:
    """Convert syscall name to AILang function name: read -> SysRead"""
    # Handle special cases
    special = {
        "rt_sigaction": "RtSigaction",
        "rt_sigprocmask": "RtSigprocmask", 
        "rt_sigreturn": "RtSigreturn",
        "rt_sigpending": "RtSigpending",
        "rt_sigtimedwait": "RtSigtimedwait",
        "rt_sigqueueinfo": "RtSigqueueinfo",
        "rt_sigsuspend": "RtSigsuspend",
        "rt_tgsigqueueinfo": "RtTgsigqueueinfo",
        "pread64": "Pread64",
        "pwrite64": "Pwrite64",
        "getdents64": "Getdents64",
        "preadv2": "Preadv2",
        "pwritev2": "Pwritev2",
        "exit_group": "ExitGroup",
        "clock_gettime": "ClockGettime",
        "clock_settime": "ClockSettime",
        "clock_getres": "ClockGetres",
        "clock_nanosleep": "ClockNanosleep",
        "clock_adjtime": "ClockAdjtime",
        "io_setup": "IoSetup",
        "io_destroy": "IoDestroy",
        "io_getevents": "IoGetevents",
        "io_submit": "IoSubmit",
        "io_cancel": "IoCancel",
        "io_pgetevents": "IoPgetevents",
        "io_uring_setup": "IoUringSetup",
        "io_uring_enter": "IoUringEnter",
        "io_uring_register": "IoUringRegister",
    }
    
    if name in special:
        return "Sys" + special[name]
    
    # Default: capitalize each word
    parts = name.split("_")
    camel = "".join(p.capitalize() for p in parts)
    return "Sys" + camel

def arg_to_ailang_type(arg_name: str) -> str:
    """Determine AILang type from argument name"""
    # Check if it's a known pointer argument
    name_lower = arg_name.lower()
    
    # Direct matches
    if name_lower in POINTER_ARGS:
        return "Address"
    
    # Suffix matches
    pointer_suffixes = ("buf", "ptr", "addr", "path", "name", "vec", "fds")
    if any(name_lower.endswith(s) for s in pointer_suffixes):
        return "Address"
    
    # Prefix matches  
    pointer_prefixes = ("u_", "old_", "new_")
    if any(name_lower.startswith(p) for p in pointer_prefixes):
        # But not if it's clearly a value like "old_size"
        if not any(x in name_lower for x in ("size", "len", "count", "fd", "flags", "mode")):
            return "Address"
    
    return "Integer"

def generate_header(syscall_count: int, categories: Set[SyscallCategory]) -> str:
    """Generate file header"""
    cat_names = sorted(c.name for c in categories)
    return f'''// Library.SyscallWrappers.ailang
// Auto-generated syscall wrappers for Linux x86-64
// Generated by generate_syscall_lib.py from syscall_table.py
//
// Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
// Licensed under the Sean Collins Software License (SCSL).
//
// Platform: Linux x86-64
// Syscalls: {syscall_count}
// Categories: {", ".join(cat_names)}
//
// DO NOT EDIT MANUALLY - Regenerate with:
//   python3 generate_syscall_lib.py
//
// Usage:
//   result = SysRead(fd, buffer, count)
//   SysWrite(FD.STDOUT, message, len)
//   SysExitGroup(0)

LibraryImport.Compiler.CodeEmit.CSyscallTable

'''

def generate_category_header(category: SyscallCategory) -> str:
    """Generate category section header"""
    return f'''
// =============================================================================
// {category.name} SYSCALLS
// =============================================================================

'''

def generate_wrapper(sc: SyscallDescriptor) -> str:
    """Generate single syscall wrapper function from SyscallDescriptor"""
    
    func_name = syscall_to_ailang_name(sc.name)
    noreturn = sc.name in NORETURN_SYSCALLS
    syscall_key = sc.name.upper()
    
    # Build Input declarations
    inputs = ""
    for arg_name in sc.arg_names:
        arg_type = arg_to_ailang_type(arg_name)
        inputs += f"    Input: {arg_name}: {arg_type}\n"
    
    # Output declaration
    output = "" if noreturn else "    Output: Integer\n"
    
    # Build SystemCall arguments (always 6, pad with 0)
    if sc.num_args == 0:
        syscall_args = f"SysNum.{syscall_key}"
    else:
        args = list(sc.arg_names[:6])  # Max 6 args for syscall
        while len(args) < 6:
            args.append("0")
        syscall_args = f"SysNum.{syscall_key}, " + ", ".join(args)
    
    # Body
    if noreturn:
        body = f'''    Body: {{
        SystemCall({syscall_args})
        // Does not return
    }}'''
    else:
        body = f'''    Body: {{
        result = SystemCall({syscall_args})
        ReturnValue(result)
    }}'''
    
    # Comment with syscall number and description
    return f'''// {func_name} [{sc.number}] - {sc.description}
Function.{func_name} {{
{inputs}{output}{body}
}}

'''

def generate_file(
    categories: Optional[Set[SyscallCategory]] = None,
    include_all: bool = False,
    specific_syscalls: Optional[Set[str]] = None
) -> str:
    """Generate complete wrapper library"""
    
    table = LINUX_X64_SYSCALLS
    
    if categories is None:
        categories = DEFAULT_CATEGORIES
    
    # Collect syscalls to generate
    syscalls_to_gen: List[SyscallDescriptor] = []
    
    for sc in table.syscalls.values():
        # Skip blacklisted
        if sc.name in SKIP_SYSCALLS:
            continue
        
        # Filter by specific list if provided
        if specific_syscalls and sc.name not in specific_syscalls:
            continue
        
        # Filter by category unless include_all
        if not include_all and sc.category not in categories:
            continue
        
        # Skip syscalls with >6 args (can't do in one syscall instruction)
        if sc.num_args > 6:
            continue
        
        syscalls_to_gen.append(sc)
    
    # Sort by category then number
    syscalls_to_gen.sort(key=lambda x: (x.category.value, x.number))
    
    # Generate output
    used_categories = {sc.category for sc in syscalls_to_gen}
    output = generate_header(len(syscalls_to_gen), used_categories)
    
    current_category = None
    for sc in syscalls_to_gen:
        if sc.category != current_category:
            current_category = sc.category
            output += generate_category_header(current_category)
        output += generate_wrapper(sc)
    
    return output

def list_syscalls(category: Optional[SyscallCategory] = None):
    """Print syscall listing"""
    table = LINUX_X64_SYSCALLS
    
    if category:
        syscalls = table.list_by_category(category)
        print(f"\n{category.name} syscalls ({len(syscalls)}):")
    else:
        syscalls = list(table.syscalls.values())
        print(f"\nAll syscalls ({len(syscalls)}):")
    
    print("=" * 70)
    
    for sc in sorted(syscalls, key=lambda x: x.number):
        skip = " [SKIP]" if sc.name in SKIP_SYSCALLS else ""
        args = ", ".join(sc.arg_names) if sc.arg_names else ""
        print(f"{sc.number:3d}  {sc.name}({args}){skip}")
        print(f"     {sc.description}")

# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate AILang syscall wrappers from syscall_table.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 generate_syscall_lib.py --stdout
  python3 generate_syscall_lib.py -o Library.SyscallWrappers.ailang
  python3 generate_syscall_lib.py --all          # Include ALL syscalls
  python3 generate_syscall_lib.py --category FILE_IO
  python3 generate_syscall_lib.py --list
  python3 generate_syscall_lib.py --list --category MEMORY
        """
    )
    parser.add_argument(
        "--output", "-o",
        default="Library.SyscallWrappers.ailang",
        help="Output file path"
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print to stdout instead of file"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include ALL syscalls (not just default categories)"
    )
    parser.add_argument(
        "--category", "-c",
        action="append",
        choices=[c.name for c in SyscallCategory],
        help="Include specific category (can repeat)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List syscalls instead of generating"
    )
    
    args = parser.parse_args()
    
    # Determine categories
    if args.category:
        categories = {SyscallCategory[c] for c in args.category}
    else:
        categories = DEFAULT_CATEGORIES
    
    # List mode
    if args.list:
        if args.category:
            for cat_name in args.category:
                list_syscalls(SyscallCategory[cat_name])
        else:
            list_syscalls()
        return
    
    # Generate
    output = generate_file(
        categories=categories,
        include_all=args.all
    )
    
    if args.stdout:
        print(output)
    else:
        with open(args.output, 'w') as f:
            f.write(output)
        
        # Count what we generated
        count = output.count("Function.Sys")
        print(f"Generated {args.output}")
        print(f"  Syscall wrappers: {count}")
        if args.all:
            print(f"  Mode: ALL syscalls")
        elif args.category:
            print(f"  Categories: {', '.join(args.category)}")
        else:
            print(f"  Categories: default ({len(DEFAULT_CATEGORIES)})")

if __name__ == "__main__":
    main()