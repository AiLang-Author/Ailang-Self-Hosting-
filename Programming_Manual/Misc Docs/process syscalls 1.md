# Process Operations - Quick Integration Guide

## File: `ailang_compiler/ailang_compiler.py`

### Change 1: Add Import (Line ~33)

**After this line:**
```python
from ailang_compiler.modules.network_ops import NetworkOps
```

**Add:**
```python
from ailang_compiler.modules.process_ops import ProcessOps
```

---

### Change 2: Initialize Module (Line ~135)

**Find this code:**
```python
self.network_ops = NetworkOps(self)

# Initialize library inliner AFTER hash_ops
self.library_inliner = LibraryInliner(self)
```

**Change to:**
```python
self.network_ops = NetworkOps(self)

# ADD THIS:
self.process_ops = ProcessOps(self)
print("DEBUG: Initialized process operations module")

# Initialize library inliner AFTER hash_ops
self.library_inliner = LibraryInliner(self)
```

---

### Change 3: Add to Dispatch (Line ~220)

**Find this code:**
```python
dispatch_modules = [
    self.function_dispatch,  # Handle CallIndirect, AddressOf first
    self.math_ops,          # Try math operations next
    self.arithmetic,        # Then basic arithmetic
    self.fileio, self.strings,
    self.lowlevel, self.hash_ops, self.network_ops,
    self.virtual_memory, self.atomics
]
```

**Change to:**
```python
dispatch_modules = [
    self.process_ops,        # ADD THIS FIRST - syscalls have priority
    self.function_dispatch,  # Handle CallIndirect, AddressOf first
    self.math_ops,          # Try math operations next
    self.arithmetic,        # Then basic arithmetic
    self.fileio, self.strings,
    self.lowlevel, self.hash_ops, self.network_ops,
    self.virtual_memory, self.atomics
]
```

---

### Change 4: Fix Exit Conflict (Line ~280)

**Find this code:**
```python
# Exit (existing code)
if base_name == 'Exit':
    self.asm.emit_mov_rax_imm64(60)
    self.asm.emit_xor_edi_edi()
    self.asm.emit_syscall()
    return
```

**Change to:**
```python
# Exit (existing code) - bare Exit with no arguments
# ProcessExit is handled by process_ops module and takes an argument
if base_name == 'Exit' and (not hasattr(node, 'arguments') or len(node.arguments) == 0):
    # Legacy Exit() with no status code - exits with 0
    self.asm.emit_mov_rax_imm64(60)
    self.asm.emit_xor_edi_edi()
    self.asm.emit_syscall()
    return
```

---

## New Files to Add

### File: `ailang_compiler/compiler_modules/process_ops.py`
Copy the cleaned `process_ops.py` from the artifact

### File: `ailang_compiler/assembler/modules/registers.py`
Add the new assembler methods from the assembler additions artifact

---

## Testing the Integration

Create `test_process.ail`:

```ailang
Program TestProcess

Main
    PrintString("Testing ProcessFork...")
    
    pid = ProcessFork()
    
    If pid == 0 Then
        PrintString("Child process running")
        ProcessSleep(1)
        PrintString("Child exiting")
        ProcessExit(0)
    ElseIf pid > 0 Then
        PrintString("Parent process, child PID: ")
        PrintNumber(pid)
        
        PrintString("Parent waiting for child...")
        result = ProcessWait(pid, 0)
        
        PrintString("Child has exited")
    Else
        PrintString("Fork failed!")
    End
    
    PrintString("Test complete")
End
```

Compile and run:
```bash
python ailang.py test_process.ail
./test_process
```

**Expected output:**
```
Testing ProcessFork...
Parent process, child PID: [some number]
Parent waiting for child...
Child process running
Child exiting
Child has exited
Test complete
```

---

## Function Compatibility Matrix

| Old Style | New Style | Status |
|-----------|-----------|--------|
| `SystemCall(57)` | `ProcessFork()` | ✅ Both work |
| `Exit` | `ProcessExit(0)` | ✅ Both work |
| N/A | `ProcessWait(pid, 0)` | ✅ New |
| N/A | `ProcessKill(pid, 15)` | ✅ New |
| N/A | `ProcessExec(path, argv)` | ✅ New |
| N/A | `PipeCreate()` | ✅ New |
| N/A | `ProcessSleep(5)` | ✅ New |

---

## Common Issues and Solutions

### Issue: "Unknown function: ProcessFork"
**Solution:** Make sure `self.process_ops` is in dispatch_modules list

### Issue: "ProcessExit conflicts with Exit"
**Solution:** Apply Change 4 above to add the argument check

### Issue: "AttributeError: emit_mov_rdi_deref_rax"
**Solution:** Add the new assembler methods to registers.py

### Issue: "Module 'process_ops' not found"
**Solution:** Make sure process_ops.py is in ailang_compiler/compiler_modules/

---

## Files Modified Summary

1. ✏️ `ailang_compiler/ailang_compiler.py` - 4 changes
2. ➕ `ailang_compiler/compiler_modules/process_ops.py` - new file
3. ➕ `ailang_compiler/assembler/modules/registers.py` - append methods

---

## Priority for COBOL Project

For the COBOL transpiler, you specifically need:

1. **ProcessExec** - Launch compiled COBOL programs ⭐⭐⭐
2. **ProcessFork + ProcessWait** - Manage subprogram execution ⭐⭐⭐
3. **Pipe functions** - IPC between programs ⭐⭐
4. **ProcessKill** - Graceful shutdown ⭐

The integration above gives you all of these.