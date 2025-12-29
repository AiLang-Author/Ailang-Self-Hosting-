#!/bin/bash
# Test compile modules in isolation
# Tracks build failures vs runtime failures

echo "========================================"
echo "COMPILE MODULE ISOLATION TESTS"
echo "========================================"
echo ""

FAILED_BUILD=""
FAILED_RUN=""
PASSED=""

# Test 1: Baseline - no compile modules
cat > test_baseline.ailang << 'EOF'
LibraryImport.XArrays

SubRoutine.Main {
    PrintMessage("BASELINE OK\n")
}

RunTask(Main)
EOF

echo "=== TEST 1: Baseline (no compile modules) ==="
if python3 main.py test_baseline.ailang 2>&1 | tail -5; then
    if [ -f test_baseline_exec ]; then
        if ./test_baseline_exec; then
            PASSED="$PASSED baseline"
        else
            FAILED_RUN="$FAILED_RUN baseline"
            echo ">>> RUNTIME FAILURE: baseline"
        fi
    else
        FAILED_BUILD="$FAILED_BUILD baseline"
        echo ">>> BUILD FAILURE: baseline (no exec created)"
    fi
else
    FAILED_BUILD="$FAILED_BUILD baseline"
    echo ">>> BUILD FAILURE: baseline"
fi
echo ""

# Test 2: Just CCompileTypes
cat > test_types.ailang << 'EOF'
LibraryImport.XArrays
LibraryImport.Compiler.Compile.Modules.CCompileTypes

SubRoutine.Main {
    PrintMessage("CCOMPILETYPES OK\n")
}

RunTask(Main)
EOF

echo "=== TEST 2: CCompileTypes only ==="
if python3 main.py test_types.ailang 2>&1 | tail -5; then
    if [ -f test_types_exec ]; then
        if ./test_types_exec; then
            PASSED="$PASSED types"
        else
            FAILED_RUN="$FAILED_RUN types"
            echo ">>> RUNTIME FAILURE: types"
        fi
    else
        FAILED_BUILD="$FAILED_BUILD types"
        echo ">>> BUILD FAILURE: types (no exec created)"
    fi
else
    FAILED_BUILD="$FAILED_BUILD types"
    echo ">>> BUILD FAILURE: types"
fi
echo ""

# Test 3: CCompileFunc (with its dependencies)
cat > test_func.ailang << 'EOF'
LibraryImport.XArrays
LibraryImport.Compiler.Frontend.AST.CASTTypes
LibraryImport.Compiler.Frontend.AST.CASTCore
LibraryImport.Compiler.CodeEmit.CEmitTypes
LibraryImport.Compiler.CodeEmit.CEmitCore
LibraryImport.Compiler.CodeEmit.CEmitCoreArch
LibraryImport.Compiler.Compile.Modules.CCompileTypes
LibraryImport.Compiler.Compile.Modules.CCompileFunc

SubRoutine.Main {
    PrintMessage("CCOMPILEFUNC OK\n")
}

RunTask(Main)
EOF

echo "=== TEST 3: CCompileFunc ==="
if python3 main.py test_func.ailang 2>&1 | tail -5; then
    if [ -f test_func_exec ]; then
        if ./test_func_exec; then
            PASSED="$PASSED func"
        else
            FAILED_RUN="$FAILED_RUN func"
            echo ">>> RUNTIME FAILURE: func"
        fi
    else
        FAILED_BUILD="$FAILED_BUILD func"
        echo ">>> BUILD FAILURE: func (no exec created)"
    fi
else
    FAILED_BUILD="$FAILED_BUILD func"
    echo ">>> BUILD FAILURE: func"
fi
echo ""

# Test 4: CCompileExpr (with its dependencies)
cat > test_expr.ailang << 'EOF'
LibraryImport.XArrays
LibraryImport.Compiler.Frontend.AST.CASTTypes
LibraryImport.Compiler.Frontend.AST.CASTCore
LibraryImport.Compiler.CodeEmit.CEmitTypes
LibraryImport.Compiler.CodeEmit.CEmitCore
LibraryImport.Compiler.CodeEmit.CEmitCoreArch
LibraryImport.Compiler.Compile.Modules.CCompileTypes
LibraryImport.Compiler.Compile.Modules.CCompileExpr

SubRoutine.Main {
    PrintMessage("CCOMPILEEXPR OK\n")
}

RunTask(Main)
EOF

echo "=== TEST 4: CCompileExpr ==="
if python3 main.py test_expr.ailang 2>&1 | tail -5; then
    if [ -f test_expr_exec ]; then
        if ./test_expr_exec; then
            PASSED="$PASSED expr"
        else
            FAILED_RUN="$FAILED_RUN expr"
            echo ">>> RUNTIME FAILURE: expr"
        fi
    else
        FAILED_BUILD="$FAILED_BUILD expr"
        echo ">>> BUILD FAILURE: expr (no exec created)"
    fi
else
    FAILED_BUILD="$FAILED_BUILD expr"
    echo ">>> BUILD FAILURE: expr"
fi
echo ""

# Test 5: Both together
cat > test_both.ailang << 'EOF'
LibraryImport.XArrays
LibraryImport.Compiler.Frontend.AST.CASTTypes
LibraryImport.Compiler.Frontend.AST.CASTCore
LibraryImport.Compiler.CodeEmit.CEmitTypes
LibraryImport.Compiler.CodeEmit.CEmitCore
LibraryImport.Compiler.CodeEmit.CEmitCoreArch
LibraryImport.Compiler.Compile.Modules.CCompileTypes
LibraryImport.Compiler.Compile.Modules.CCompileFunc
LibraryImport.Compiler.Compile.Modules.CCompileExpr

SubRoutine.Main {
    PrintMessage("BOTH OK\n")
}

RunTask(Main)
EOF

echo "=== TEST 5: Both CCompileFunc and CCompileExpr ==="
if python3 main.py test_both.ailang 2>&1 | tail -5; then
    if [ -f test_both_exec ]; then
        if ./test_both_exec; then
            PASSED="$PASSED both"
        else
            FAILED_RUN="$FAILED_RUN both"
            echo ">>> RUNTIME FAILURE: both"
        fi
    else
        FAILED_BUILD="$FAILED_BUILD both"
        echo ">>> BUILD FAILURE: both (no exec created)"
    fi
else
    FAILED_BUILD="$FAILED_BUILD both"
    echo ">>> BUILD FAILURE: both"
fi
echo ""

echo "========================================"
echo "SUMMARY"
echo "========================================"
echo "PASSED:      $PASSED"
echo "BUILD FAIL:  $FAILED_BUILD"
echo "RUN FAIL:    $FAILED_RUN"
echo "========================================"
echo ""
echo "Test files preserved: test_*.ailang, test_*_exec"