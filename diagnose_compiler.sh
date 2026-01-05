#!/bin/bash
# diagnose_compiler.sh - Scan for potential memory/logic issues in AILang compiler

echo "=========================================="
echo "AILang Compiler Diagnostic Scanner"
echo "=========================================="

COMPILER_DIR="Librarys/Compiler"

echo ""
echo "=== 1. XArray Operations Balance ==="
echo "XPush calls:"
/usr/bin/grep -rc "XPush" $COMPILER_DIR --include="*.ailang" 2>/dev/null | /usr/bin/grep -v ":0$"
echo ""
echo "XPop calls:"
/usr/bin/grep -rc "XPop" $COMPILER_DIR --include="*.ailang" 2>/dev/null | /usr/bin/grep -v ":0$"
echo ""
echo "XClear calls:"
/usr/bin/grep -rc "XClear" $COMPILER_DIR --include="*.ailang" 2>/dev/null | /usr/bin/grep -v ":0$"
echo ""
echo "XDestroy calls:"
/usr/bin/grep -rc "XDestroy" $COMPILER_DIR --include="*.ailang" 2>/dev/null | /usr/bin/grep -v ":0$"

echo ""
echo "=== 2. Allocate/Deallocate Balance ==="
echo "Allocate calls:"
/usr/bin/grep -rc "Allocate(" $COMPILER_DIR --include="*.ailang" 2>/dev/null | /usr/bin/grep -v ":0$"
echo ""
echo "Deallocate calls:"
/usr/bin/grep -rc "Deallocate(" $COMPILER_DIR --include="*.ailang" 2>/dev/null | /usr/bin/grep -v ":0$"

echo ""
echo "=== 3. WhileLoop without BreakLoop (potential infinite loops) ==="
for f in $(/usr/bin/find $COMPILER_DIR -name "*.ailang" 2>/dev/null); do
    whiles=$(/usr/bin/grep -c "WhileLoop" "$f" 2>/dev/null)
    breaks=$(/usr/bin/grep -c "BreakLoop" "$f" 2>/dev/null)
    if [ "$whiles" -gt 0 ] && [ "$breaks" -eq 0 ]; then
        echo "  $f: $whiles WhileLoop(s), 0 BreakLoop"
    fi
done

echo ""
echo "=== 4. Recursive Function Calls (potential stack overflow) ==="
echo "Functions that might call themselves:"
for f in $(/usr/bin/find $COMPILER_DIR -name "*.ailang" 2>/dev/null); do
    # Get function names defined in file
    funcs=$(/usr/bin/grep -o "^Function\.[A-Za-z_]*" "$f" 2>/dev/null | sed 's/^Function\.//')
    for func in $funcs; do
        # Check if function name appears again inside the file (potential self-call)
        count=$(/usr/bin/grep -c "$func(" "$f" 2>/dev/null)
        if [ "$count" -gt 1 ]; then
            echo "  $f: $func (defined and called $count times)"
        fi
    done
done 2>/dev/null | head -20

echo ""
echo "=== 5. Scope Save/Restore Balance ==="
echo "Scope_SaveAndClear calls:"
/usr/bin/grep -rn "Scope_SaveAndClear" $COMPILER_DIR --include="*.ailang" 2>/dev/null
echo ""
echo "Scope_Restore calls:"
/usr/bin/grep -rn "Scope_Restore" $COMPILER_DIR --include="*.ailang" 2>/dev/null

echo ""
echo "=== 6. Compile_Init calls (should be called before compilation) ==="
/usr/bin/grep -rn "Compile_Init()" $COMPILER_DIR --include="*.ailang" 2>/dev/null

echo ""
echo "=== 7. Large Magic Numbers (might indicate pointer/size confusion) ==="
/usr/bin/grep -rn "[0-9]\{7,\}" $COMPILER_DIR --include="*.ailang" 2>/dev/null | head -10

echo ""
echo "=== 8. XArray.XSize calls (tracing where size is checked) ==="
/usr/bin/grep -rn "XArray.XSize" $COMPILER_DIR --include="*.ailang" 2>/dev/null

echo ""
echo "=== 9. Compile.variables usage ==="
/usr/bin/grep -rn "Compile\.variables" $COMPILER_DIR --include="*.ailang" 2>/dev/null

echo ""
echo "=== 10. Potential uninitialized variable access ==="
echo "Dereference calls (might deref uninitialized pointer):"
/usr/bin/grep -rc "Dereference(" $COMPILER_DIR --include="*.ailang" 2>/dev/null | /usr/bin/grep -v ":0$"

echo ""
echo "=========================================="
echo "Diagnostic scan complete"
echo "=========================================="