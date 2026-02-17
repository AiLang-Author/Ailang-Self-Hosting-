# AILANG Process Management Syscalls - API Reference

**Version:** 1.0  
**Date:** Current  
**Module:** `process_ops.py`

## Overview

This document describes the process management primitives available in AILANG. These replace and extend the generic `SystemCall` interface with named, typed functions for common process operations.

**Key Change:** Process syscalls now use `Process` prefix to avoid naming collision with AILANG's flow control `Fork` primitive.

---

## Process Control Functions

### ProcessFork()

**Description:** Creates a new child process (fork syscall)

**Syscall Number:** 57

**Signature:**
```ailang
pid = ProcessFork()
```

**Arguments:** None

**Returns:**
- In parent process: Child process ID (positive integer)
- In child process: 0
- On error: -1

**Example:**
```ailang
pid = ProcessFork()
If pid == 0 Then
    PrintString("I am the child process")
    ProcessExit(0)
ElseIf pid > 0 Then
    PrintString("I am the parent, child PID: ")
    PrintNumber(pid)
    result = ProcessWait(pid, 0)
Else
    PrintString("Fork failed!")
End
```

**Notes:**
- Both parent and child continue execution after fork
- Child inherits parent's memory, file descriptors, etc.
- Child gets a copy-on-write duplicate of parent's address space

---

### ProcessGetPID()

**Description:** Get current process ID

**Syscall Number:** 39

**Signature:**
```ailang
pid = ProcessGetPID()
```

**Arguments:** None

**Returns:** Current process ID (positive integer)

**Example:**
```ailang
my_pid = ProcessGetPID()
PrintString("My process ID is: ")
PrintNumber(my_pid)
```

---

### ProcessGetTID()

**Description:** Get current thread ID

**Syscall Number:** 186

**Signature:**
```ailang
tid = ProcessGetTID()
```

**Arguments:** None

**Returns:** Current thread ID (positive integer)

**Example:**
```ailang
my_tid = ProcessGetTID()
PrintString("My thread ID is: ")
PrintNumber(my_tid)
```

**Notes:**
- In single-threaded programs, TID equals PID
- Useful for multi-threaded applications

---

### ProcessExit(status_code)

**Description:** Terminate the current process with a status code

**Syscall Number:** 60

**Signature:**
```ailang
ProcessExit(status_code)
```

**Arguments:**
- `status_code` (integer): Exit status (0 = success, non-zero = error)

**Returns:** Does not return (process terminates)

**Example:**
```ailang
If error_occurred Then
    ProcessExit(1)  // Exit with error status
Else
    ProcessExit(0)  // Exit successfully
End
```

**Notes:**
- 0 conventionally means success
- 1-255 are error codes (values > 255 are truncated)
- Parent can retrieve exit status with ProcessWait

---

### ProcessWait(pid, options)

**Description:** Wait for a child process to change state

**Syscall Number:** 61 (wait4)

**Signature:**
```ailang
result_pid = ProcessWait(pid, options)
```

**Arguments:**
- `pid` (integer): Process to wait for
  - `> 0`: Wait for specific child with this PID
  - `-1`: Wait for any child process
  - `0`: Wait for any child in same process group
  - `< -1`: Wait for any child in process group abs(pid)
- `options` (integer): Wait options
  - `0`: Block until child exits
  - `1`: WNOHANG - return immediately if no child exited
  - `2`: WUNTRACED - also return for stopped children

**Returns:**
- PID of child that changed state (positive)
- 0 if WNOHANG was used and no child exited
- -1 on error

**Example:**
```ailang
// Wait for specific child
pid = ProcessFork()
If pid > 0 Then
    // Parent waits for child
    exited_pid = ProcessWait(pid, 0)
    If exited_pid > 0 Then
        PrintString("Child exited")
    End
End

// Wait for any child with non-blocking
result = ProcessWait(-1, 1)  // WNOHANG
If result == 0 Then
    PrintString("No child has exited yet")
End
```

**Notes:**
- Blocking call by default (options = 0)
- Returns exit status in implementation (currently discarded)
- Use -1 to wait for any child in daemon/server patterns

---

### ProcessKill(pid, signal)

**Description:** Send a signal to a process

**Syscall Number:** 62

**Signature:**
```ailang
result = ProcessKill(pid, signal)
```

**Arguments:**
- `pid` (integer): Target process ID
- `signal` (integer): Signal number to send
  - `1`: SIGHUP (hangup)
  - `2`: SIGINT (interrupt, like Ctrl+C)
  - `9`: SIGKILL (force kill, cannot be caught)
  - `15`: SIGTERM (termination request, can be caught)
  - `18`: SIGCONT (continue if stopped)
  - `19`: SIGSTOP (stop process)

**Returns:**
- 0 on success
- -1 on error

**Example:**
```ailang
// Graceful shutdown
result = ProcessKill(child_pid, 15)  // SIGTERM
If result != 0 Then
    // If graceful failed, force kill
    ProcessKill(child_pid, 9)  // SIGKILL
End
```

**Notes:**
- SIGKILL (9) cannot be caught or ignored
- SIGTERM (15) allows process to clean up
- Negative pid sends signal to process group

---

### ProcessExec(program_path, argv_array)

**Description:** Execute a program, replacing current process image

**Syscall Number:** 59 (execve)

**Signature:**
```ailang
ProcessExec(program_path, argv_array)
```

**Arguments:**
- `program_path` (string): Path to executable file
- `argv_array` (pointer): Pointer to NULL-terminated array of string pointers
  - First element should be program name
  - Last element must be NULL (0)

**Returns:**
- Does not return on success (process is replaced)
- Returns -1 on error (executable not found, permission denied, etc.)

**Example:**
```ailang
// Execute /bin/ls -la
// Need to build argv array: ["/bin/ls", "-la", NULL]

argv = MemoryAllocate(24)  // 3 pointers * 8 bytes = 24
[argv + 0] = "/bin/ls"     // argv[0] - program name
[argv + 8] = "-la"         // argv[1] - first argument
[argv + 16] = 0            // argv[2] - NULL terminator

result = ProcessExec("/bin/ls", argv)

// If we reach here, exec failed
If result == -1 Then
    PrintString("Failed to execute program")
    ProcessExit(1)
End
```

**Notes:**
- On success, the current process is **completely replaced**
- File descriptors remain open unless marked close-on-exec
- Typically used after ProcessFork() to run a different program
- argv[0] conventionally contains the program name
- Environment variables not currently supported (envp = NULL)

---

## Inter-Process Communication (IPC)

### PipeCreate()

**Description:** Create a unidirectional pipe for IPC

**Syscall Number:** 22

**Signature:**
```ailang
pipe_handle = PipeCreate()
```

**Arguments:** None

**Returns:**
- Pointer to pipe structure containing:
  - `[handle + 0]`: Read file descriptor (8 bytes)
  - `[handle + 8]`: Write file descriptor (8 bytes)
- NULL (0) on error

**Example:**
```ailang
pipe = PipeCreate()
If pipe == 0 Then
    PrintString("Failed to create pipe")
    ProcessExit(1)
End

// Use pipe for parent-child communication
pid = ProcessFork()
If pid == 0 Then
    // Child writes to pipe
    message = "Hello from child"
    bytes_written = PipeWrite(pipe, message, 16)
    ProcessExit(0)
Else
    // Parent reads from pipe
    buffer = MemoryAllocate(100)
    bytes_read = PipeRead(pipe, buffer, 100)
    PrintString(buffer)
End
```

**Notes:**
- Data written to write end appears at read end
- Unidirectional: use two pipes for bidirectional communication
- Automatically shared across ProcessFork()
- Remember to close unused ends in parent/child

---

### PipeRead(pipe_handle, buffer, max_bytes)

**Description:** Read data from pipe's read end

**Syscall Number:** 0 (read)

**Signature:**
```ailang
bytes_read = PipeRead(pipe_handle, buffer, max_bytes)
```

**Arguments:**
- `pipe_handle` (pointer): Pipe from PipeCreate()
- `buffer` (pointer): Destination buffer for data
- `max_bytes` (integer): Maximum bytes to read

**Returns:**
- Number of bytes actually read (0 to max_bytes)
- 0 if write end is closed and no data remains
- -1 on error

**Example:**
```ailang
pipe = PipeCreate()
buffer = MemoryAllocate(256)

// After fork, in parent:
bytes_read = PipeRead(pipe, buffer, 256)
If bytes_read > 0 Then
    PrintString("Received: ")
    PrintString(buffer)
ElseIf bytes_read == 0 Then
    PrintString("Pipe closed")
Else
    PrintString("Read error")
End
```

**Notes:**
- Blocks until data available or write end closed
- Returns 0 when all writers have closed write end
- May return fewer bytes than requested

---

### PipeWrite(pipe_handle, buffer, num_bytes)

**Description:** Write data to pipe's write end

**Syscall Number:** 1 (write)

**Signature:**
```ailang
bytes_written = PipeWrite(pipe_handle, buffer, num_bytes)
```

**Arguments:**
- `pipe_handle` (pointer): Pipe from PipeCreate()
- `buffer` (pointer): Source data to write
- `num_bytes` (integer): Number of bytes to write

**Returns:**
- Number of bytes actually written
- -1 on error (e.g., read end closed = SIGPIPE)

**Example:**
```ailang
pipe = PipeCreate()
message = "Hello, pipe!"

// After fork, in child:
bytes_written = PipeWrite(pipe, message, 12)
If bytes_written != 12 Then
    PrintString("Write error or partial write")
End
```

**Notes:**
- May block if pipe buffer is full (typically 64KB)
- Writing to closed read end causes SIGPIPE (kills process by default)
- Atomic for writes ≤ PIPE_BUF (4096 bytes on Linux)

---

## Time Functions

### ProcessSleep(seconds)

**Description:** Sleep for specified number of seconds

**Syscall Number:** 35 (nanosleep)

**Signature:**
```ailang
result = ProcessSleep(seconds)
```

**Arguments:**
- `seconds` (integer): Number of seconds to sleep

**Returns:**
- 0 on success (slept full duration)
- -1 on error or interruption

**Example:**
```ailang
PrintString("Sleeping for 5 seconds...")
ProcessSleep(5)
PrintString("Awake!")

// In loop with delay
i = 0
While i < 10 Do
    PrintString("Tick")
    ProcessSleep(1)
    i = i + 1
End
```

**Notes:**
- Can be interrupted by signals (returns early)
- Actual sleep time may be slightly longer
- For sub-second precision, use SystemCall with nanosleep struct

---

## Common Patterns

### Fork-Exec Pattern (Running External Programs)

```ailang
pid = ProcessFork()
If pid == 0 Then
    // Child: execute new program
    argv = MemoryAllocate(16)
    [argv + 0] = "/usr/bin/cobol-program"
    [argv + 8] = 0  // NULL terminator
    
    ProcessExec("/usr/bin/cobol-program", argv)
    
    // Only reached if exec fails
    PrintString("Exec failed")
    ProcessExit(1)
ElseIf pid > 0 Then
    // Parent: wait for child
    result = ProcessWait(pid, 0)
    PrintString("Child finished")
Else
    PrintString("Fork failed")
End
```

### Parent-Child Communication via Pipe

```ailang
pipe = PipeCreate()

pid = ProcessFork()
If pid == 0 Then
    // Child: write to pipe
    message = "Data from child"
    PipeWrite(pipe, message, 15)
    ProcessExit(0)
Else
    // Parent: read from pipe
    buffer = MemoryAllocate(100)
    bytes = PipeRead(pipe, buffer, 100)
    PrintString("Received: ")
    PrintString(buffer)
    ProcessWait(pid, 0)
End
```

### Daemon Process with Multiple Children

```ailang
// Fork children
child_count = 5
i = 0
While i < child_count Do
    pid = ProcessFork()
    If pid == 0 Then
        // Child worker
        PrintString("Worker started")
        // Do work...
        ProcessSleep(10)
        ProcessExit(0)
    End
    i = i + 1
End

// Parent waits for all children
i = 0
While i < child_count Do
    pid = ProcessWait(-1, 0)  // Wait for any child
    PrintString("Child exited: ")
    PrintNumber(pid)
    i = i + 1
End
```

---

## Error Handling

All syscalls follow Unix convention:
- **Success:** Return value ≥ 0
- **Error:** Return value = -1

**Common Error Scenarios:**

| Function | Error Condition | Likely Cause |
|----------|----------------|--------------|
| ProcessFork | Returns -1 | Process limit reached, out of memory |
| ProcessWait | Returns -1 | No child processes, invalid PID |
| ProcessKill | Returns -1 | Permission denied, process doesn't exist |
| ProcessExec | Returns at all | File not found, not executable, invalid format |
| PipeCreate | Returns 0 (NULL) | File descriptor limit reached |
| PipeRead | Returns -1 | Bad file descriptor, interrupted |
| PipeWrite | Returns -1 | Broken pipe (read end closed), interrupted |

---

## Implementation Notes

### Assembler Methods Required

The following assembler methods are used by process_ops.py:

```python
# Register moves
emit_mov_rdi_rax()
emit_mov_rsi_rax()
emit_mov_rdx_rax()
emit_mov_r10_rax()

# Memory operations
emit_mov_rdi_deref_rax()           # MOV RDI, [RAX]
emit_mov_rdi_deref_rax_offset(n)   # MOV RDI, [RAX + n]
emit_mov_qword_ptr_rsp_rax()       # MOV [RSP], RAX

# Stack operations
emit_sub_rsp_imm8(n)
emit_add_rsp_imm8(n)
emit_push_rax()
emit_pop_rax()

# Zero registers
emit_xor_rdx_rdx()
emit_xor_rsi_rsi()

# Syscall
emit_syscall()

# Control flow
emit_test_rax_rax()
emit_js_label(label)
```

### Syscall Reference Table

| Function | Syscall # | RAX | RDI | RSI | RDX | R10 | R8 | R9 |
|----------|-----------|-----|-----|-----|-----|-----|----|----|
| ProcessFork | 57 | 57 | - | - | - | - | - | - |
| ProcessGetPID | 39 | 39 | - | - | - | - | - | - |
| ProcessGetTID | 186 | 186 | - | - | - | - | - | - |
| ProcessExit | 60 | 60 | status | - | - | - | - | - |
| ProcessWait | 61 | 61 | pid | *status | NULL | options | - | - |
| ProcessKill | 62 | 62 | pid | signal | - | - | - | - |
| ProcessExec | 59 | 59 | path | argv | NULL | - | - | - |
| PipeCreate | 22 | 22 | *fds | - | - | - | - | - |
| PipeRead | 0 | 0 | fd | buf | count | - | - | - |
| PipeWrite | 1 | 1 | fd | buf | count | - | - | - |
| ProcessSleep | 35 | 35 | *req | NULL | - | - | - | - |

---

## Migration from Old SystemCall Interface

**Old way (generic):**
```ailang
result = SystemCall(57)  // fork
```

**New way (typed):**
```ailang
result = ProcessFork()
```

**Benefits:**
- Named functions are self-documenting
- Type checking at compile time
- Better error messages
- Consistent argument order
- Avoids magic numbers

---

## Testing Checklist

- [ ] ProcessFork creates child process correctly
- [ ] ProcessFork returns 0 in child, PID in parent
- [ ] ProcessWait correctly waits for child exit
- [ ] ProcessKill can terminate processes
- [ ] ProcessExec replaces process image
- [ ] PipeCreate returns valid pipe handle
- [ ] PipeRead/PipeWrite transfer data correctly
- [ ] Pipe communication works across fork
- [ ] ProcessSleep delays for correct duration
- [ ] Error conditions return -1 as expected

---

## Future Enhancements

Potential additions for future versions:

1. **ProcessExecEnv** - execve with environment variables
2. **ProcessSetPriority** - nice/setpriority syscalls  
3. **ProcessGetCPUTime** - getrusage for profiling
4. **PipeCreateNonBlocking** - O_NONBLOCK pipes
5. **ProcessSignalHandler** - sigaction for custom handlers
6. **ProcessDup2** - dup2 for file descriptor redirection

---

**Document Version:** 1.0  
**Last Updated:** Current session  
**Maintained by:** AILANG Compiler Team