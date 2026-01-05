#!/usr/bin/env python3
"""
CEmit Duplicate Function Remover
Safely removes duplicate function definitions from AILANG files.
"""

import os
import re
import shutil
from pathlib import Path

CEMIT_PATH = Path("Librarys/Compiler/CodeEmit/X86")

# Functions to REMOVE from CEmitX86Reg.ailang (they exist in specialized modules)
REMOVE_FROM_REG = [
    # Stack operations -> CEmitX86Stack.ailang
    "X86_PushRax", "X86_PushRbx", "X86_PushRbp", "X86_PushR11",
    "X86_PopRbp", "X86_PopR11", "X86_Prologue", "X86_Epilogue",
    # Jump operations -> CEmitX86Jump.ailang  
    "X86_Jmp", "X86_Jl", "X86_Jg", "X86_Jge",
    # Compare/Set operations -> CEmitX86Cmp.ailang
    "X86_CmpRaxRbx", "X86_CmpRaxImm32", "X86_TestRaxRax",
    "X86_Sete", "X86_Setne", "X86_Setg", "X86_Setge", "X86_ShlRcxImm8",
    # Arithmetic operations -> CEmitX86Arith.ailang
    "X86_SubRaxRbx", "X86_SubRaxImm32", "X86_ImulRaxRbx", 
    "X86_IdivRbx", "X86_Cqo", "X86_NegRax",
    # Logic operations -> CEmitX86Logic.ailang
    "X86_OrRaxRbx", "X86_XorRaxRbx", "X86_NotRax", "X86_ShlRaxCl",
    # Memory operations -> CEmitX86Mem.ailang
    "X86_MovRaxDerefRbx",
]

# Other cleanup: (file, function_to_remove)
OTHER_REMOVALS = [
    ("Library.CEmitX86Stack.ailang", "X86_Ret"),  # Keep in CEmitX86Jump
    ("Library.CEmitX86String.ailang", "X86_MovDerefRbxAl"),  # Keep in CEmitX86Mem
    ("Library.CEmitX86Cmp.ailang", "X86_AddRaxRcx"),  # Keep in CEmitX86Arith
    ("Library.CEmitX86Cmp.ailang", "X86_AddRaxImm8"),  # Keep in CEmitX86Arith
]

def remove_function(content: str, func_name: str) -> tuple[str, bool]:
    """Remove a Function.NAME { ... } block from content."""
    # Pattern to match Function.NAME followed by { and everything until matching }
    pattern = rf'^Function\.{re.escape(func_name)}\s*\{{'
    
    lines = content.split('\n')
    result = []
    i = 0
    removed = False
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this line starts the function we want to remove
        if re.match(pattern, line.strip() if line.strip() else ''):
            # Found the function, now find the matching closing brace
            brace_count = 0
            found_open = False
            
            while i < len(lines):
                for char in lines[i]:
                    if char == '{':
                        brace_count += 1
                        found_open = True
                    elif char == '}':
                        brace_count -= 1
                
                i += 1
                
                # If we've seen at least one { and now back to 0, we're done
                if found_open and brace_count == 0:
                    removed = True
                    # Skip any trailing empty lines
                    while i < len(lines) and lines[i].strip() == '':
                        i += 1
                    break
        else:
            result.append(line)
            i += 1
    
    return '\n'.join(result), removed

def process_file(filepath: Path, functions_to_remove: list[str], dry_run: bool = False):
    """Remove specified functions from a file."""
    if not filepath.exists():
        print(f"  [SKIP] {filepath} does not exist")
        return
    
    content = filepath.read_text()
    original_content = content
    removed_count = 0
    
    for func in functions_to_remove:
        content, was_removed = remove_function(content, func)
        if was_removed:
            removed_count += 1
            print(f"  [REMOVED] {func}")
        else:
            # Check if it exists at all
            if f"Function.{func}" in original_content:
                print(f"  [WARN] {func} found but removal failed - check manually")
    
    if removed_count > 0:
        if dry_run:
            print(f"  [DRY RUN] Would remove {removed_count} functions from {filepath.name}")
        else:
            filepath.write_text(content)
            print(f"  [DONE] Removed {removed_count} functions from {filepath.name}")
    else:
        print(f"  [SKIP] No functions to remove from {filepath.name}")

def main():
    import sys
    dry_run = '--dry-run' in sys.argv
    
    print("=" * 60)
    print("CEmit Duplicate Function Remover")
    print("=" * 60)
    
    if dry_run:
        print("[DRY RUN MODE - No changes will be made]")
    
    # Create backup
    backup_path = Path(str(CEMIT_PATH) + ".bak")
    if not backup_path.exists():
        print(f"\nCreating backup at {backup_path}...")
        shutil.copytree(CEMIT_PATH, backup_path)
        print("Backup created.")
    else:
        print(f"\nBackup already exists at {backup_path}")
    
    # Process CEmitX86Reg.ailang
    print(f"\n[1/2] Processing Library.CEmitX86Reg.ailang...")
    print(f"      Removing {len(REMOVE_FROM_REG)} duplicate functions...")
    reg_file = CEMIT_PATH / "Library.CEmitX86Reg.ailang"
    process_file(reg_file, REMOVE_FROM_REG, dry_run)
    
    # Process other files
    print(f"\n[2/2] Processing other files...")
    for filename, func in OTHER_REMOVALS:
        filepath = CEMIT_PATH / filename
        print(f"      {filename}: removing {func}")
        process_file(filepath, [func], dry_run)
    
    print("\n" + "=" * 60)
    print("Cleanup complete!")
    print("=" * 60)
    print("\nRun ./dupe.sh to verify no duplicates remain.")
    print(f"\nTo restore from backup: rm -rf {CEMIT_PATH} && mv {backup_path} {CEMIT_PATH}")

if __name__ == "__main__":
    main()