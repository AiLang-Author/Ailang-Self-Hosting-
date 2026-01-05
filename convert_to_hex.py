#!/usr/bin/env python3
"""
convert_to_hex.py
Converts Emit_Byte(decimal) to Emit_Byte(0xHH) in CEmitX86 files

Usage:
    python3 convert_to_hex.py --dry-run   # Preview changes
    python3 convert_to_hex.py             # Actually convert

Run from AILangSH root directory.
"""

import re
import sys
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv or "-n" in sys.argv

def decimal_to_hex_emit_byte(match):
    """Convert Emit_Byte(decimal) to Emit_Byte(0xHH)"""
    num = int(match.group(1))
    if 0 <= num <= 255:
        return f"Emit_Byte(0x{num:02X})"
    return match.group(0)  # Leave unchanged if out of byte range

def decimal_to_hex_emit_word(match):
    """Convert Emit_Word(decimal) to Emit_Word(0xHHHH)"""
    num = int(match.group(1))
    if 0 <= num <= 65535:
        return f"Emit_Word(0x{num:04X})"
    return match.group(0)

def decimal_to_hex_emit_dword(match):
    """Convert Emit_DWord(decimal) to Emit_DWord(0xHHHHHHHH)"""
    num = int(match.group(1))
    if 0 <= num <= 4294967295:
        return f"Emit_DWord(0x{num:08X})"
    return match.group(0)

def convert_file(filepath):
    """Convert a single file"""
    content = Path(filepath).read_text()
    original = content
    
    # Convert Emit_Byte(decimal)
    content = re.sub(r'Emit_Byte\((\d+)\)', decimal_to_hex_emit_byte, content)
    
    # Convert Emit_Word(decimal) - optional, uncomment if needed
    # content = re.sub(r'Emit_Word\((\d+)\)', decimal_to_hex_emit_word, content)
    
    # Convert Emit_DWord(decimal) - optional, uncomment if needed  
    # content = re.sub(r'Emit_DWord\((\d+)\)', decimal_to_hex_emit_dword, content)
    
    if content != original:
        # Count changes
        changes = len(re.findall(r'Emit_Byte\(0x[0-9A-F]+\)', content))
        
        if DRY_RUN:
            print(f"  Would convert: {filepath.name} ({changes} Emit_Byte calls)")
            # Show first few changes
            for m in list(re.finditer(r'Emit_Byte\(0x[0-9A-F]+\)', content))[:3]:
                print(f"    e.g. {m.group()}")
        else:
            Path(filepath).write_text(content)
            print(f"  Converted: {filepath.name} ({changes} Emit_Byte calls)")
        return True
    else:
        print(f"  Unchanged: {filepath.name}")
        return False

def main():
    print("=" * 50)
    if DRY_RUN:
        print("DRY RUN - No files will be modified")
    print("Converting Emit_Byte(decimal) to Emit_Byte(0xHH)")
    print("=" * 50)
    
    x86_dir = Path("Librarys/Compiler/CodeEmit/X86")
    
    if not x86_dir.exists():
        print(f"ERROR: Directory not found: {x86_dir}")
        print("Make sure you're running from the AILangSH root directory")
        return 1
    
    files = list(x86_dir.glob("*.ailang"))
    print(f"\nFound {len(files)} files in {x86_dir}\n")
    
    converted = 0
    for f in sorted(files):
        if convert_file(f):
            converted += 1
    
    print(f"\n{'=' * 50}")
    if DRY_RUN:
        print(f"DRY RUN: Would convert {converted} files.")
        print(f"Run without --dry-run to apply changes.")
    else:
        print(f"Done! Converted {converted} files.")
        print(f"\nNext steps:")
        print(f"  1. python3 main.py ailang_console.ailang")
        print(f"  2. ./ailang_console_exec ailang_console.ailang -o compiler.x")
        print(f"  3. ./compiler.x ailang_console.ailang -o compiler2.x")
        print(f"  4. cmp compiler.x compiler2.x")
    print(f"{'=' * 50}")
    
    return 0

if __name__ == "__main__":
    exit(main())