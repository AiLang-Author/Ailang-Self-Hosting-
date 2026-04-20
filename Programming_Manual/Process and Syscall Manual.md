# AILang Process & Syscall API Reference

## Overview

AILang exposes Linux syscalls through two mechanisms:

1. **Named process functions** — typed wrappers for common process
   operations (`ProcessFork`, `ProcessExit`, etc.)
2. **`SystemCall(n, ...)`** — direct syscall for anything not covered
   by named functions

Both compile to the same syscall instruction sequence. Named functions
exist for readability and type safety; `SystemCall` exists for
everything else.

---

## SystemCall Primitive

```ailang
result = SystemCall(syscall_number, arg1, arg2, arg3, arg4, arg5, arg6)
```

Arguments map to Linux x86-64 ABI registers:

| Argument | Register |
|----------|----------|
| syscall_number | RAX |
| arg1 | RDI |
| arg2 | RSI |
| arg3 | RDX |
| arg4 | R10 |
| arg5 | R8 |
| arg6 | R9 |

Maximum 6 arguments (after the syscall number). Result is returned in
RAX. Unused argument registers are zeroed before the syscall.

```ailang
// Direct read() syscall — fd=0 (stdin), buf, 4096 bytes
n = SystemCall(0, 0, buf, 4096)

// Direct write() syscall — fd=1 (stdout), buf, n bytes
SystemCall(1, 1, buf, n)

// Direct exit() syscall
SystemCall(60, 0)
```

---

## Process Control

### `ProcessFork`

```ailang
pid = ProcessFork()
```

Creates a child process. Returns the child's PID in the parent, `0`
in the child, `-1` on error. Wraps syscall 57 (Linux) / `_kern_fork`
(Haiku).

```ailang
pid = ProcessFork()
IfCondition EqualTo(pid, 0) ThenBlock: {
    // Child process
    PrintMessage("child running\n")
    ProcessExit(0)
} ElseBlock: {
    IfCondition GreaterThan(pid, 0) ThenBlock: {
        // Parent process
        result = ProcessWait(pid, 0)
    } ElseBlock: {
        // Fork failed
        WriteStderr("fork failed\n")
        ProcessExit(1)
    }
}
```

---

### `ProcessExit`

```ailang
ProcessExit(status_code)
```

Terminates the current process. Does not return. `status_code` is the
exit value visible to the parent via `ProcessWait`. `0` = success,
non-zero = error. Wraps syscall 60.

```ailang
IfCondition NotEqual(result, 0) ThenBlock: {
    ProcessExit(1)
}
ProcessExit(0)
```

---

### `ProcessWait`

```ailang
exited_pid = ProcessWait(pid, options)
```

Waits for a child process to change state.

| `pid` value | Meaning |
|-------------|---------|
| `> 0` | Wait for this specific child |
| `-1` | Wait for any child |
| `0` | Wait for any child in same process group |
| `< -1` | Wait for any child in process group `Abs(pid)` |

| `options` value | Meaning |
|-----------------|---------|
| `0` | Block until child exits |
| `1` | WNOHANG — return immediately if no child has exited |
| `2` | WUNTRACED — also return for stopped children |

Returns the PID of the child that changed state, `0` if WNOHANG and
no child exited, `-1` on error. Wraps syscall 61 (wait4).

```ailang
// Wait for specific child
exited = ProcessWait(child_pid, 0)

// Non-blocking poll for any child
result = ProcessWait(-1, 1)
IfCondition EqualTo(result, 0) ThenBlock: {
    // no child has exited yet
}
```

---

### `ProcessGetPID`

```ailang
pid = ProcessGetPID()
```

Returns the current process ID. Wraps syscall 39.

---

### `ProcessGetTID`

```ailang
tid = ProcessGetTID()
```

Returns the current thread ID. In single-threaded programs, TID equals
PID. Wraps syscall 186.

---

### `ProcessKill`

```ailang
result = ProcessKill(pid, signal)
```

Sends `signal` to process `pid`. Returns `0` on success, `-1` on
error. Wraps syscall 62.

Common signal values:

| Value | Name | Meaning |
|-------|------|---------|
| 1 | SIGHUP | Hangup |
| 2 | SIGINT | Interrupt (Ctrl+C equivalent) |
| 9 | SIGKILL | Force kill — cannot be caught or ignored |
| 15 | SIGTERM | Graceful termination request |
| 18 | SIGCONT | Continue if stopped |
| 19 | SIGSTOP | Stop process |

```ailang
// Graceful shutdown first, force if needed
result = ProcessKill(child_pid, 15)
IfCondition NotEqual(result, 0) ThenBlock: {
    ProcessKill(child_pid, 9)
}
```

---

### `ProcessExec`

```ailang
ProcessExec(program_path, argv_ptr)
```

Replaces the current process image with the program at `program_path`.
Does not return on success. Returns `-1` on failure (file not found,
not executable, etc.). Wraps syscall 59 (execve).

`argv_ptr` is a pointer to a NULL-terminated array of `Address` values:
- `argv_ptr[0]` — program name (by convention, the path)
- `argv_ptr[1..n]` — arguments
- `argv_ptr[n+1]` — `0` (NULL terminator)

```ailang
// Build argv: ["/bin/ls", "-la", NULL]
argv = Allocate(24)               // 3 pointers × 8 bytes
StoreValue(argv, "/bin/ls")
StoreValue(Add(argv, 8), "-la")
StoreValue(Add(argv, 16), 0)      // NULL terminator

result = ProcessExec("/bin/ls", argv)
// Only reached if exec failed
WriteStderr("exec failed\n")
ProcessExit(1)
```

---

### `ProcessSleep`

```ailang
result = ProcessSleep(seconds)
```

Sleeps for `seconds` seconds. Returns `0` on success, `-1` if
interrupted by a signal. Wraps syscall 35 (nanosleep).

```ailang
i = 0
WhileLoop LessThan(i, 5) {
    PrintMessage("tick\n")
    ProcessSleep(1)
    i = Add(i, 1)
}
```

---

## Pipes (IPC)

### `PipeCreate`

```ailang
pipe_handle = PipeCreate()
```

Creates a unidirectional pipe. Returns a pointer to an 8-byte-pair
structure, or `0` on failure. Wraps syscall 22.

```
pipe_handle + 0:  read file descriptor  (8 bytes)
pipe_handle + 8:  write file descriptor (8 bytes)
```

Data written to the write end appears at the read end. Unidirectional
— use two pipes for bidirectional communication. Pipe is shared across
`ProcessFork` automatically.

```ailang
pipe = PipeCreate()
IfCondition EqualTo(pipe, 0) ThenBlock: {
    WriteStderr("pipe failed\n")
    ProcessExit(1)
}
```

---

### `PipeRead`

```ailang
bytes_read = PipeRead(pipe_handle, buffer, max_bytes)
```

Reads up to `max_bytes` from the pipe's read end into `buffer`. Blocks
until data is available or all write ends are closed. Returns number
of bytes read, `0` if write end is closed and no data remains, `-1`
on error.

---

### `PipeWrite`

```ailang
bytes_written = PipeWrite(pipe_handle, buffer, num_bytes)
```

Writes `num_bytes` from `buffer` to the pipe's write end. May block if
the pipe buffer is full (~64 KB on Linux). Returns number of bytes
written, `-1` on error. Writing to a pipe with no readers causes SIGPIPE.

---

## Fork-Exec Pattern

The standard pattern for running an external program:

```ailang
pid = ProcessFork()
IfCondition EqualTo(pid, 0) ThenBlock: {
    // Child: build argv and exec
    argv = Allocate(16)
    StoreValue(argv, "/usr/bin/wc")
    StoreValue(Add(argv, 8), 0)

    ProcessExec("/usr/bin/wc", argv)

    // Only reached on exec failure
    WriteStderr("exec failed\n")
    ProcessExit(1)
} ElseBlock: {
    IfCondition GreaterThan(pid, 0) ThenBlock: {
        // Parent: wait for child
        ProcessWait(pid, 0)
    }
}
```

---

## Parent-Child Pipe Communication

```ailang
pipe = PipeCreate()

pid = ProcessFork()
IfCondition EqualTo(pid, 0) ThenBlock: {
    // Child: write to pipe
    msg = "hello from child"
    PipeWrite(pipe, msg, StringLength(msg))
    ProcessExit(0)
} ElseBlock: {
    // Parent: read from pipe
    buf = Allocate(256)
    n = PipeRead(pipe, buf, 255)
    SetByte(buf, n, 0)    // NUL-terminate
    PrintMessage(buf)
    ProcessWait(pid, 0)
    Deallocate(buf, 256)
}
```

---

## Syscall Reference Table

| Function | Syscall (Linux) | RAX | RDI | RSI | RDX | R10 |
|----------|----------------|-----|-----|-----|-----|-----|
| `ProcessFork` | 57 | 57 | — | — | — | — |
| `ProcessGetPID` | 39 | 39 | — | — | — | — |
| `ProcessGetTID` | 186 | 186 | — | — | — | — |
| `ProcessExit` | 60 | 60 | status | — | — | — |
| `ProcessWait` | 61 | 61 | pid | \*status | NULL | options |
| `ProcessKill` | 62 | 62 | pid | signal | — | — |
| `ProcessExec` | 59 | 59 | path | argv | NULL | — |
| `PipeCreate` | 22 | 22 | \*fds | — | — | — |
| `PipeRead` | 0 | 0 | fd | buf | count | — |
| `PipeWrite` | 1 | 1 | fd | buf | count | — |
| `ProcessSleep` | 35 | 35 | \*req | NULL | — | — |

---

## Platform Notes

The compiler targets Linux and Haiku. Syscall numbers differ between
platforms — the compiler's `CSysDispatch` module handles translation
automatically. `ProcessFork` on Haiku calls `_kern_fork`; on Linux it
calls syscall 57. User code does not need to handle this difference.

Haiku gaps (no equivalent syscall):
- `clone` — no direct mapping
- `vfork` — no direct mapping
- `execve` — mapped via `_kern_exec` with different argument layout

---

## Error Handling

All process functions follow Unix convention:
- **Success:** return value `≥ 0`
- **Error:** return value `= -1`

| Function | Common error causes |
|----------|-------------------|
| `ProcessFork` | Process limit reached, out of memory |
| `ProcessWait` | No child processes, invalid PID |
| `ProcessKill` | Permission denied, process not found |
| `ProcessExec` | File not found, not executable, bad format |
| `PipeCreate` | File descriptor limit reached |
| `PipeRead` | Bad fd, interrupted by signal |
| `PipeWrite` | Broken pipe (read end closed), interrupted |

---

## See Also

`AILang Language Introduction`,
`Memory Management Reference Manual`,
`Library.Arena`

---

## Copyright

Copyright (c) 2025–2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
