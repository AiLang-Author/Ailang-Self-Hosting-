#!/usr/bin/env python3
"""
generate_sysdispatch.py

Generates Library.CSysDispatch.ailang - the OS-portable syscall dispatch layer.
IMPORTS directly from syscall_table_linux.py and syscall_table_haiku.py.

This generates Sys_* functions for ALL syscalls in the Linux table,
with Haiku-specific handling where mappings exist.

Usage:
    python3 generate_sysdispatch.py --stdout
    python3 generate_sysdispatch.py -o ../Library.CSysDispatch.ailang
    python3 generate_sysdispatch.py --list
    python3 generate_sysdispatch.py --list --category FILE_IO

Location: Librarys/Compiler/Compile/Modules/syscall_generator_tools/

Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
Licensed under the Sean Collins Software License (SCSL).
"""

import argparse
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Import the existing syscall tables
from syscall_table_linux import LINUX_X64_SYSCALLS, SyscallCategory

try:
    from syscall_table_haiku import HAIKU_SYSCALLS
    HAS_HAIKU = True
except ImportError:
    print("Warning: syscall_table_haiku.py not found")
    HAS_HAIKU = False

# =============================================================================
# HAIKU MAPPING TABLE
# Defines how Linux syscalls map to Haiku, including arg transformations
# =============================================================================

@dataclass
class HaikuMapping:
    """How a Linux syscall maps to Haiku"""
    haiku_name: str           # Haiku syscall name (e.g., "_kern_read")
    haiku_num: int            # Haiku syscall number
    arg_transform: str        # "same", "insert_pos", "insert_dirfd", "custom"
    notes: str = ""

# Linux syscall name -> Haiku mapping
# Only syscalls that DIFFER or have Haiku equivalents need entries
HAIKU_MAP: Dict[str, HaikuMapping] = {
    # File I/O - Haiku adds position argument to read/write
    "read":   HaikuMapping("_kern_read",  140, "insert_pos", "Haiku adds pos arg, use -1 for current"),
    "write":  HaikuMapping("_kern_write", 142, "insert_pos", "Haiku adds pos arg, use -1 for current"),
    "open":   HaikuMapping("_kern_open",  104, "insert_dirfd", "Haiku adds dirfd arg, use -1 for CWD"),
    "close":  HaikuMapping("_kern_close", 149, "same"),
    "lseek":  HaikuMapping("_kern_seek",  111, "same"),
    "pread64":  HaikuMapping("_kern_read",  140, "same", "Haiku read already has position"),
    "pwrite64": HaikuMapping("_kern_write", 142, "same", "Haiku write already has position"),
    
    # File operations
    "fsync":    HaikuMapping("_kern_fsync", 109, "same"),
    "dup":      HaikuMapping("_kern_dup",   150, "same"),
    "dup2":     HaikuMapping("_kern_dup2",  151, "same"),
    "unlink":   HaikuMapping("_kern_unlink", 118, "insert_dirfd"),
    "rename":   HaikuMapping("_kern_rename", 119, "custom", "Haiku: (olddir, old, newdir, new)"),
    "mkdir":    HaikuMapping("_kern_create_dir", 113, "insert_dirfd"),
    "rmdir":    HaikuMapping("_kern_remove_dir", 114, "insert_dirfd"),
    
    # Process
    "exit":       HaikuMapping("_kern_exit_team", 41, "same"),
    "exit_group": HaikuMapping("_kern_exit_team", 41, "same"),
    "fork":       HaikuMapping("_kern_fork", 47, "same"),
    "getpid":     HaikuMapping("_kern_get_current_team", 43, "same"),
    
    # Memory - Haiku uses "areas" differently
    "mmap":     HaikuMapping("_kern_map_file", 220, "custom", "Haiku mmap is very different"),
    "munmap":   HaikuMapping("_kern_unmap_memory", 221, "same"),
    "mprotect": HaikuMapping("_kern_set_memory_protection", 222, "same"),
    
    # Sockets
    "socket":   HaikuMapping("_kern_socket", 165, "same"),
    "bind":     HaikuMapping("_kern_bind", 166, "same"),
    "listen":   HaikuMapping("_kern_listen", 169, "same"),
    "accept":   HaikuMapping("_kern_accept", 170, "same"),
    "connect":  HaikuMapping("_kern_connect", 168, "same"),
    "send":     HaikuMapping("_kern_send", 174, "same"),
    "recv":     HaikuMapping("_kern_recv", 171, "same"),
    
    # Pipe
    "pipe":     HaikuMapping("_kern_create_pipe", 121, "custom", "Haiku: (pipefd, flags)"),
    
    # Time
    "nanosleep": HaikuMapping("_kern_snooze_etc", 196, "custom", "Very different signature"),
}

# Syscalls that don't return
NORETURN = {"exit", "exit_group"}

# Pointer arguments (for type annotation)
POINTER_ARGS = {
    "buf", "buffer", "filename", "pathname", "path", "name",
    "oldname", "newname", "statbuf", "addr", "dirp", "iov",
    "msg", "tv", "tz", "tp", "req", "rem", "set", "oldset",
    "fds", "pipefd", "optval", "argv", "envp", "rusage",
}

# =============================================================================
# CODE GENERATION
# =============================================================================

def syscall_to_func_name(name: str) -> str:
    """Convert syscall name to AILang function name: read -> Sys_Read"""
    parts = name.split('_')
    return "Sys_" + ''.join(p.capitalize() for p in parts)

def syscall_to_const_name(name: str) -> str:
    """Convert syscall name to constant name: read -> READ"""
    return name.upper()

def get_arg_type(arg_name: str) -> str:
    """Determine AILang type for argument"""
    if arg_name in POINTER_ARGS:
        return "Address"
    return "Integer"

def generate_header() -> str:
    return '''// Library.CSysDispatch.ailang
// OS-Portable Syscall Dispatch Layer - AUTO-GENERATED
// Emits correct syscall sequences based on Emit.os target
// Location: Librarys/Compiler/Compile/Modules/Library.CSysDispatch.ailang
//
// Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
// Licensed under the Sean Collins Software License (SCSL).
//
// GENERATED BY: generate_sysdispatch.py
// DO NOT EDIT MANUALLY - Regenerate with:
//   cd Librarys/Compiler/Compile/Modules/syscall_generator_tools/
//   python3 generate_sysdispatch.py -o ../Library.CSysDispatch.ailang
//
// DESIGN: All OS dispatch happens at COMPILE TIME.
// No runtime conditionals in generated code.

LibraryImport.Compiler.CodeEmit.CEmitTypes
LibraryImport.Compiler.CodeEmit.CEmitCoreArch

'''

def generate_linux_table() -> str:
    """Generate Linux syscall constants from the actual table"""
    lines = ["// =============================================================================",
             "// LINUX SYSCALL NUMBERS (from syscall_table_linux.py)",
             "// =============================================================================",
             "FixedPool.LinuxSys {"]
    
    for num, sc in sorted(LINUX_X64_SYSCALLS.syscalls.items()):
        const = syscall_to_const_name(sc.name)
        lines.append(f'    "{const}": Initialize={num}')
    
    lines.append("}")
    return "\n".join(lines) + "\n"

def generate_haiku_table() -> str:
    """Generate Haiku syscall constants from mappings"""
    lines = ["\n// =============================================================================",
             "// HAIKU SYSCALL NUMBERS",
             "// =============================================================================",
             "FixedPool.HaikuSys {"]
    
    seen = set()
    for linux_name, mapping in sorted(HAIKU_MAP.items(), key=lambda x: x[1].haiku_num):
        const = syscall_to_const_name(linux_name)
        if const not in seen:
            lines.append(f'    "{const}": Initialize={mapping.haiku_num}')
            seen.add(const)
    
    lines.append("}")
    return "\n".join(lines) + "\n"

def generate_arg_shuffle(transform: str, num_args: int) -> List[str]:
    """Generate argument shuffle code for Haiku using generic Emit_MovRegReg"""
    lines = []
    
    if transform == "insert_pos":
        # read/write: insert -1 for position after fd
        # Current: RDI=fd, RSI=buf, RDX=len
        # Need:    RDI=fd, RSI=-1,  RDX=buf, R10=len
        if num_args >= 3:
            lines.append("            // Shuffle: insert -1 for position")
            lines.append("            Emit_MovRegReg(Reg.R10, Reg.RDX)  // len -> R10")
            lines.append("            Emit_MovRegReg(Reg.RDX, Reg.RSI)  // buf -> RDX")
            lines.append("            Emit_MovRsiImm64(-1)              // pos = -1")
    
    elif transform == "insert_dirfd":
        # open: insert -1 for dirfd at start
        # Current: RDI=path, RSI=flags, RDX=mode
        # Need:    RDI=-1,   RSI=path,  RDX=flags, R10=mode
        if num_args >= 3:
            lines.append("            // Shuffle: insert -1 for dirfd")
            lines.append("            Emit_MovRegReg(Reg.R10, Reg.RDX)  // mode -> R10")
            lines.append("            Emit_MovRegReg(Reg.RDX, Reg.RSI)  // flags -> RDX")
            lines.append("            Emit_MovRegReg(Reg.RSI, Reg.RDI)  // path -> RSI")
            lines.append("            Emit_MovRdiImm64(-1)              // dirfd = -1")
        elif num_args == 2:
            lines.append("            // Shuffle: insert -1 for dirfd")
            lines.append("            Emit_MovRegReg(Reg.RDX, Reg.RSI)  // arg2 -> RDX")
            lines.append("            Emit_MovRegReg(Reg.RSI, Reg.RDI)  // arg1 -> RSI")
            lines.append("            Emit_MovRdiImm64(-1)              // dirfd = -1")
        elif num_args == 1:
            lines.append("            // Shuffle: insert -1 for dirfd")
            lines.append("            Emit_MovRegReg(Reg.RSI, Reg.RDI)  // arg1 -> RSI")
            lines.append("            Emit_MovRdiImm64(-1)              // dirfd = -1")
    
    return lines

def generate_syscall_function(sc) -> str:
    """Generate a Sys_* function for a Linux syscall"""
    
    func_name = syscall_to_func_name(sc.name)
    const_name = syscall_to_const_name(sc.name)
    noreturn = sc.name in NORETURN
    
    # NOTE: No Input declarations - these are emit-time functions
    # Caller sets up registers (RDI, RSI, RDX, R10, R8, R9) before calling
    # The function just emits the syscall number and SYSCALL instruction
    inputs = ""
    # Document expected registers in comment instead
    if sc.arg_names:
        reg_names = ["RDI", "RSI", "RDX", "R10", "R8", "R9"]
        arg_comment = ", ".join(f"{reg_names[i]}={sc.arg_names[i]}" 
                                for i in range(min(len(sc.arg_names), 6)))
    else:
        arg_comment = "none"
    
    # Check if Haiku mapping exists
    haiku_map = HAIKU_MAP.get(sc.name)
    
    lines = [f'''
// =============================================================================
// {func_name} - {sc.description}
// Linux syscall {sc.number}: {sc.name}({", ".join(sc.arg_names)})
// Registers: {arg_comment}
// =============================================================================
Function.{func_name} {{
    Body: {{
        // --- LINUX ---
        IfCondition EqualTo(Emit.os, OS.LINUX) ThenBlock: {{
            Emit_MovRaxImm64(LinuxSys.{const_name})
            Emit_SysInstr()
        }}''']
    
    # Haiku block
    if haiku_map:
        lines.append(f'''        // --- HAIKU ---
        IfCondition EqualTo(Emit.os, OS.HAIKU) ThenBlock: {{''')
        
        if haiku_map.notes:
            lines.append(f'            // {haiku_map.notes}')
        
        # Add shuffle code if needed
        shuffle = generate_arg_shuffle(haiku_map.arg_transform, sc.num_args)
        if shuffle:
            lines.extend(shuffle)
        
        if haiku_map.arg_transform == "custom":
            lines.append(f'            // TODO: Custom mapping needed for {sc.name}')
            lines.append(f'            Emit_MovRaxImm64(HaikuSys.{const_name})')
        else:
            lines.append(f'            Emit_MovRaxImm64(HaikuSys.{const_name})')
        
        lines.append('            Emit_SysInstr()')
        lines.append('        }')
    else:
        # No Haiku mapping - emit Linux-only warning or stub
        lines.append(f'''        // --- HAIKU: No direct mapping ---
        IfCondition EqualTo(Emit.os, OS.HAIKU) ThenBlock: {{
            // TODO: {sc.name} has no Haiku equivalent
            Emit_MovRaxImm64(-1)  // Return error
        }}''')
    
    lines.append('    }')
    lines.append('}')
    
    return "\n".join(lines)


def generate_file(categories: Optional[List[SyscallCategory]] = None) -> str:
    """Generate complete CSysDispatch.ailang"""
    
    parts = [generate_header(), generate_linux_table(), generate_haiku_table()]
    
    # Group syscalls by category
    by_cat: Dict[SyscallCategory, List] = {}
    for num, sc in sorted(LINUX_X64_SYSCALLS.syscalls.items()):
        if categories and sc.category not in categories:
            continue
        by_cat.setdefault(sc.category, []).append(sc)
    
    # Generate functions by category
    cat_names = {
        SyscallCategory.FILE_IO: "FILE I/O",
        SyscallCategory.PROCESS: "PROCESS",
        SyscallCategory.MEMORY: "MEMORY",
        SyscallCategory.NETWORK: "NETWORK",
        SyscallCategory.IPC: "IPC",
        SyscallCategory.TIME: "TIME",
        SyscallCategory.SIGNAL: "SIGNAL",
        SyscallCategory.SYSTEM: "SYSTEM",
        SyscallCategory.SECURITY: "SECURITY",
    }
    
    for cat in SyscallCategory:
        if cat not in by_cat:
            continue
        
        parts.append(f'''
// #############################################################################
// {cat_names.get(cat, cat.name)}
// #############################################################################
''')
        for sc in sorted(by_cat[cat], key=lambda x: x.number):
            parts.append(generate_syscall_function(sc))
    
    return "\n".join(parts)


def list_syscalls(category: Optional[str] = None):
    """Print syscall listing"""
    
    print("\nLinux x86-64 Syscalls -> Haiku Mapping Status:")
    print("=" * 90)
    print(f"{'#':<4} {'Linux Name':<20} {'Haiku':<25} {'Transform':<12} {'Status'}")
    print("-" * 90)
    
    for num, sc in sorted(LINUX_X64_SYSCALLS.syscalls.items()):
        if category:
            try:
                cat = SyscallCategory[category]
                if sc.category != cat:
                    continue
            except KeyError:
                pass
        
        haiku = HAIKU_MAP.get(sc.name)
        if haiku:
            haiku_name = haiku.haiku_name
            transform = haiku.arg_transform
            status = "✓ Mapped"
        else:
            haiku_name = "-"
            transform = "-"
            status = "Linux only"
        
        print(f"{num:<4} {sc.name:<20} {haiku_name:<25} {transform:<12} {status}")
    
    total = len(LINUX_X64_SYSCALLS.syscalls)
    mapped = len(HAIKU_MAP)
    print(f"\nTotal: {total} syscalls, {mapped} have Haiku mappings")
    print("\nCategories:", ", ".join(c.name for c in SyscallCategory))


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate Library.CSysDispatch.ailang from syscall tables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 generate_sysdispatch.py --list
    python3 generate_sysdispatch.py --list --category FILE_IO
    python3 generate_sysdispatch.py --stdout
    python3 generate_sysdispatch.py -o ../Library.CSysDispatch.ailang
    python3 generate_sysdispatch.py --category FILE_IO -o CSysDispatchFileIO.ailang
        """
    )
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout")
    parser.add_argument("--list", action="store_true", help="List all syscalls")
    parser.add_argument("--category", "-c", help="Filter by category (e.g., FILE_IO, PROCESS)")
    
    args = parser.parse_args()
    
    if args.list:
        list_syscalls(args.category)
        return
    
    # Parse category filter
    categories = None
    if args.category:
        try:
            categories = [SyscallCategory[args.category]]
        except KeyError:
            print(f"Unknown category: {args.category}")
            print("Valid categories:", ", ".join(c.name for c in SyscallCategory))
            return
    
    output = generate_file(categories)
    
    if args.stdout:
        print(output)
    elif args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        total = len(LINUX_X64_SYSCALLS.syscalls)
        mapped = len(HAIKU_MAP)
        print(f"Generated {args.output}")
        print(f"  Total syscalls: {total}")
        print(f"  Haiku mappings: {mapped}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()