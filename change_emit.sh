#!/bin/bash
# Run from /mnt/c/Users/Sean/Documents/AILangSH

# Replace X86_ with Emit_ in all Compile modules
# This is a simple prefix swap - function names stay the same

# Main compile file
sed -i 's/X86_/Emit_/g' Librarys/Compiler/Compile/Library.CCompileMain.ailang

# All module files
sed -i 's/X86_/Emit_/g' Librarys/Compiler/Compile/Modules/Library.CCompileArith.ailang
sed -i 's/X86_/Emit_/g' Librarys/Compiler/Compile/Modules/Library.CCompileBitwise.ailang
sed -i 's/X86_/Emit_/g' Librarys/Compiler/Compile/Modules/Library.CCompileCompare.ailang
sed -i 's/X86_/Emit_/g' Librarys/Compiler/Compile/Modules/Library.CCompileExpr.ailang
sed -i 's/X86_/Emit_/g' Librarys/Compiler/Compile/Modules/Library.CCompileFunc.ailang
sed -i 's/X86_/Emit_/g' Librarys/Compiler/Compile/Modules/Library.CCompileIO.ailang
sed -i 's/X86_/Emit_/g' Librarys/Compiler/Compile/Modules/Library.CCompileLogic.ailang
sed -i 's/X86_/Emit_/g' Librarys/Compiler/Compile/Modules/Library.CCompileMem.ailang
sed -i 's/X86_/Emit_/g' Librarys/Compiler/Compile/Modules/Library.CCompileStmt.ailang
sed -i 's/X86_/Emit_/g' Librarys/Compiler/Compile/Modules/Library.CCompileSystem.ailang

# Verify no X86_ calls remain in Compile/
echo "=== Checking for remaining X86_ calls ==="
/bin/grep -rn "X86_" Librarys/Compiler/Compile/
echo "=== Done (should show nothing except .backup files) ==="