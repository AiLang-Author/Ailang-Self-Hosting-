# Library.ThreadTrampoline(ailang)

## NAME

`Library.ThreadTrampoline` — POSIX-style threading with futex mutex

## SYNOPSIS

```ailang
LibraryImport.ThreadTrampoline
```

> Self-contained. No other imports required — uses its own private
> 4 MB heap, not `Library.Arena`.

---

## DESCRIPTION

`Library.ThreadTrampoline` provides kernel threads via Linux `clone()`
with shared address space (`CLONE_VM`). Threads share all memory with
the parent process. Synchronization is provided by a futex-based mutex.

The library is fully self-contained by design — it allocates its own
4 MB `mmap` heap with a bump allocator and free list. This means it
can be used in low-level contexts where `Library.Arena` is not yet
initialized, and avoids any allocator contention between threads.

**Supported operations:** spawn, join, yield, sleep, self-query,
alive-check, mutex create/lock/unlock/trylock/destroy.

**Platform:** Linux x86-64 only. Syscall numbers are hardcoded for
the Linux ABI. Haiku support is not implemented.

---

## INITIALIZATION

### `Thread_Init`

```ailang
RunTask(Thread_Init)
```

Must be called once before any other threading function. Initializes
the private heap, thread registry, spawn mailbox, and computes the
`clone()` flag set. Call from the main thread before spawning.

```ailang
SubRoutine.Main {
    Thread_Init()
    // ... spawn threads
}
RunTask(Main)
```

---

## THREAD LIFECYCLE

### `Thread_Spawn`

```ailang
tid = Thread_Spawn(entry_func, user_data)
```

Spawns a new thread that calls `entry_func(user_data)`. Returns the
thread ID (positive integer) on success, `0` on failure.

`entry_func` must have the signature:

```ailang
Function.MyWorker {
    Input:  cookie: Integer
    Output: Integer
    Body: {
        // ... do work ...
        ReturnValue(result)
    }
}
```

The return value of `entry_func` becomes the thread's exit code,
retrievable via `Thread_Join`.

Pass the function address with `AddressOf`:

```ailang
tid = Thread_Spawn(AddressOf(MyWorker), 42)
```

**Limits:** Maximum 64 concurrent threads (`ThrConst.MAX_THREADS`).
Each thread gets a 64 KB stack (`ThrConst.STACK_SIZE`) with a 4 KB
guard page below it. Stack overflows hit the guard page and segfault
rather than silently corrupting memory.

**Thread safety:** `Thread_Spawn` is serialized via a spin lock
(`ThrRegistry.spawn_lock`). Concurrent spawn calls from multiple
threads are safe but will serialize.

---

### `Thread_Join`

```ailang
exit_code = Thread_Join(tid)
```

Blocks until the thread with the given `tid` exits. Returns the
thread's exit code (the value it passed to `ReturnValue`). Returns
`-1` if the `tid` is unknown.

Internally uses `futex(FUTEX_WAIT)` — the calling thread sleeps in
the kernel rather than spinning. After join, the thread's stack is
freed and its registry slot is returned to the free list.

```ailang
tid = Thread_Spawn(AddressOf(Worker_Double), 21)
ec  = Thread_Join(tid)    // → 42
```

---

### `Thread_Self`

```ailang
tid = Thread_Self()
```

Returns the calling thread's TID via `gettid()` syscall (186).
Works correctly from any thread including the main thread.

---

### `Thread_IsAlive`

```ailang
alive = Thread_IsAlive(tid)
```

Returns `1` if the thread is in `RUNNING` state, `0` otherwise
(unknown tid, `CREATED`, `EXITED`, or `DETACHED`).

---

### `Thread_Count`

```ailang
count = Thread_Count()
```

Returns the number of currently registered (non-cleaned-up) threads.
Decrements when `Thread_Join` completes cleanup.

---

### `Thread_Yield`

```ailang
result = Thread_Yield()
```

Yields the processor via `sched_yield()` syscall (24). Returns `0`
on success. Use in spin-wait loops to avoid burning CPU:

```ailang
WhileLoop EqualTo(some_flag, 0) {
    Thread_Yield()
}
```

---

### `Thread_Sleep`

```ailang
result = Thread_Sleep(ms)
```

Sleeps for `ms` milliseconds using `nanosleep()` syscall (35).
Returns `0` on success, `-1` if interrupted by a signal.

```ailang
Thread_Sleep(200)    // sleep 200ms
```

If called from a registered thread, reuses the 16-byte `timespec`
buffer embedded in the thread's info block (`ThrOfs.TS_BUF`) to
avoid an allocation. If called from an unregistered thread (e.g.
main before `Thread_Init`), allocates from the private heap.

---

## MUTEX

Futex-based mutex with three states: `0` = unlocked, `1` = locked
(no waiters), `2` = locked (waiters sleeping in kernel). This is the
standard Linux two-phase mutex — fast path is a single
`AtomicCompareSwap` with no syscall; slow path sleeps via
`futex(FUTEX_WAIT_PRIVATE)`.

### `Mutex_Create`

```ailang
m = Mutex_Create()
```

Allocates an 8-byte mutex from the private heap. Returns the mutex
address. Store it somewhere accessible to all threads that need it
(a `FixedPool` field works well).

```ailang
FixedPool.Shared {
    "mutex": Initialize=0
}

// In main, before spawning:
Shared.mutex = Mutex_Create()
```

---

### `Mutex_Lock`

```ailang
result = Mutex_Lock(m)
```

Acquires the mutex. Blocks if already held. Returns `1` on success.
Fast path: one `AtomicCompareSwap`, no syscall. Slow path: sleeps
via `futex(FUTEX_WAIT_PRIVATE)`.

---

### `Mutex_Unlock`

```ailang
result = Mutex_Unlock(m)
```

Releases the mutex. If there are waiters (`state == 2`), wakes one
via `futex(FUTEX_WAKE_PRIVATE)`. Returns `1`.

---

### `Mutex_TryLock`

```ailang
result = Mutex_TryLock(m)
```

Non-blocking lock attempt. Returns `1` if acquired, `0` if already
held. Never blocks.

---

### `Mutex_Destroy`

```ailang
result = Mutex_Destroy(m)
```

Currently a no-op — mutex memory is reclaimed when the private heap
is released at process exit. Returns `1`.

---

## THREAD STATES

| State | Value | Meaning |
|-------|-------|---------|
| `CREATED` | 0 | Allocated, not yet running |
| `RUNNING` | 1 | Active |
| `EXITED` | 2 | Returned from entry function |
| `DETACHED` | 3 | Reserved for future use |

---

## THREADINFO LAYOUT

Each thread has a 96-byte info block in the private heap:

| Offset | Field | Description |
|--------|-------|-------------|
| 0 | `TID` | Kernel thread ID |
| 8 | `STATE` | Current state |
| 16 | `STACK_BASE` | Base address of mmap'd stack |
| 24 | `STACK_SIZE` | Stack size (default 64 KB) |
| 32 | `ENTRY_FUNC` | Entry function address |
| 40 | `USER_DATA` | Cookie passed to entry function |
| 48 | `EXIT_CODE` | Return value from entry function |
| 56 | `TID_FUTEX` | Futex word for join wait |
| 64 | `DETACHED` | Detach flag (reserved) |
| 72 | `NEXT` | Free list link |
| 80 | `TS_BUF` | 16-byte nanosleep timespec buffer |

---

## IMPORTANT NOTES

### Arena is not thread-safe

`Library.Arena` uses global `FixedPool` state with no locking.
Do not call `Allocate()` / `Deallocate()` from worker threads.
Use the private heap (`ThrHeap_Alloc`) or pre-allocate before
spawning:

```ailang
// WRONG — Arena not thread-safe
Function.BadWorker {
    Input: cookie: Integer
    Output: Integer
    Body: {
        buf = Allocate(256)    // race condition
        ReturnValue(0)
    }
}

// RIGHT — pre-allocate before spawn
buf = Allocate(256)
tid = Thread_Spawn(AddressOf(GoodWorker), buf)
```

### PrintMessage / PrintNumber are not thread-safe

`write()` syscalls from multiple threads can interleave. Either
protect output with a mutex or avoid printing from worker threads
entirely. The test harness intentionally avoids output from workers
for this reason.

### FixedPool variables are shared

Because threads share address space (`CLONE_VM`), all `FixedPool`
variables are visible to all threads. This is intentional — it is
the primary communication mechanism. Protect shared mutable state
with a mutex.

---

## CONSTANTS

```ailang
ThrConst.MAX_THREADS    // 64     — max concurrent threads
ThrConst.STACK_SIZE     // 65536  — 64 KB per thread stack
ThrConst.GUARD_SIZE     // 4096   — guard page below each stack
ThrHeap.size            // 4194304 — 4 MB private heap
```

`MAX_THREADS` and `ThrHeap.size` are matched constraints. At 96 bytes
per threadinfo block plus 64 KB stack per thread, 64 threads consumes
roughly `64 × (96 + 65536)` ≈ 4.2 MB — which is right at the heap
ceiling. Raising `MAX_THREADS` without also raising `ThrHeap.size`
will cause silent heap exhaustion at spawn time. If you genuinely need
more than 64 threads, increase both together.

In practice most programs run 4–10 threads. Workloads that need
hundreds of concurrent execution contexts typically use a thread pool
with a work queue rather than one thread per task — in which case
64 worker threads is more than sufficient regardless of task count.

---

## COMPLETE EXAMPLE

```ailang
LibraryImport.ThreadTrampoline

FixedPool.State {
    "mutex":   Initialize=0
    "counter": Initialize=0
}

Function.Worker {
    Input:  n: Integer
    Output: Integer
    Body: {
        Mutex_Lock(State.mutex)
        State.counter = Add(State.counter, n)
        Mutex_Unlock(State.mutex)
        ReturnValue(n)
    }
}

SubRoutine.Main {
    Thread_Init()
    State.mutex = Mutex_Create()

    tid1 = Thread_Spawn(AddressOf(Worker), 10)
    tid2 = Thread_Spawn(AddressOf(Worker), 20)
    tid3 = Thread_Spawn(AddressOf(Worker), 30)

    Thread_Join(tid1)
    Thread_Join(tid2)
    Thread_Join(tid3)

    PrintMessage("counter: ")
    PrintNumber(State.counter)    // → 60
    PrintMessage("\n")
}

RunTask(Main)
```

---

## RING BUFFER MAILBOX PATTERN

For most real workloads the right architecture is **not** one thread
per task. It is a small fixed pool of worker threads reading from a
shared ring buffer mailbox. This is how grep keeps memory and thread
pressure near zero while processing millions of lines — the reader
fills slots, the worker drains them, and neither side allocates.

### Why this matters

Naive threading: spawn a thread per unit of work → thread count grows
with load → memory grows with thread count → OS scheduler thrashes.

Ring buffer pattern: fixed thread count regardless of load → memory
stays flat → scheduler sees a constant number of runnable threads.

### Structure

```
Producer thread(s)          Worker thread(s)
      │                           │
      ▼                           ▼
 ┌─────────────────────────────────────┐
 │         Ring Buffer Mailbox         │
 │  [slot0][slot1][slot2]...[slot7]    │
 │   head ──────────────────► tail     │
 │   count tracks occupancy           │
 └─────────────────────────────────────┘
```

The mailbox lives in a `FixedPool` — globally visible to all threads
via `CLONE_VM`, zero allocation in the hot path, single-instruction
access per field.

### Minimal implementation

```ailang
FixedPool.Mailbox {
    "head":  Initialize=0
    "tail":  Initialize=0
    "count": Initialize=0
    "mutex": Initialize=0
    "slot0": Initialize=0
    "slot1": Initialize=0
    "slot2": Initialize=0
    "slot3": Initialize=0
    "slot4": Initialize=0
    "slot5": Initialize=0
    "slot6": Initialize=0
    "slot7": Initialize=0
}

SubRoutine.Mailbox_Init {
    Mailbox.mutex = Mutex_Create()
}

SubRoutine.Mailbox_Send {
    // Input: send_value
    Mutex_Lock(Mailbox.mutex)
    IfCondition LessThan(Mailbox.count, 8) ThenBlock: {
        tail_pos = Mailbox.tail
        Branch tail_pos {
            Case 0: { Mailbox.slot0 = send_value }
            Case 1: { Mailbox.slot1 = send_value }
            Case 2: { Mailbox.slot2 = send_value }
            Case 3: { Mailbox.slot3 = send_value }
            Case 4: { Mailbox.slot4 = send_value }
            Case 5: { Mailbox.slot5 = send_value }
            Case 6: { Mailbox.slot6 = send_value }
            Case 7: { Mailbox.slot7 = send_value }
        }
        Mailbox.tail  = Modulo(Add(tail_pos, 1), 8)
        Mailbox.count = Add(Mailbox.count, 1)
    }
    Mutex_Unlock(Mailbox.mutex)
}

SubRoutine.Mailbox_Receive {
    // Output: received  (-1 if empty)
    received = -1
    Mutex_Lock(Mailbox.mutex)
    IfCondition GreaterThan(Mailbox.count, 0) ThenBlock: {
        head_pos = Mailbox.head
        Branch head_pos {
            Case 0: { received = Mailbox.slot0 }
            Case 1: { received = Mailbox.slot1 }
            Case 2: { received = Mailbox.slot2 }
            Case 3: { received = Mailbox.slot3 }
            Case 4: { received = Mailbox.slot4 }
            Case 5: { received = Mailbox.slot5 }
            Case 6: { received = Mailbox.slot6 }
            Case 7: { received = Mailbox.slot7 }
        }
        Mailbox.head  = Modulo(Add(head_pos, 1), 8)
        Mailbox.count = Subtract(Mailbox.count, 1)
    }
    Mutex_Unlock(Mailbox.mutex)
}
```

### Worker loop pattern

```ailang
Function.Worker {
    Input:  cookie: Integer
    Output: Integer
    Body: {
        WhileLoop EqualTo(1, 1) {
            RunTask(Mailbox_Receive)
            IfCondition EqualTo(received, -1) ThenBlock: {
                // Nothing ready — yield and retry
                Thread_Yield()
                ContinueLoop
            }
            IfCondition EqualTo(received, -2) ThenBlock: {
                // Sentinel: shutdown signal
                BreakLoop
            }
            // Process the message
            ProcessItem(received)
        }
        ReturnValue(0)
    }
}
```

### Shutdown

Send one sentinel value per worker thread to unblock their loops:

```ailang
SubRoutine.Mailbox_Shutdown {
    // Send -2 sentinel once per worker
    i = 0
    WhileLoop LessThan(i, num_workers) {
        send_value = -2
        RunTask(Mailbox_Send)
        i = Add(i, 1)
    }
}
```

### Properties

- **FIFO ordering** — messages dequeued in send order
- **Bounded** — fixed 8-slot capacity, no allocation on send
- **Overflow-safe** — send to a full mailbox is a no-op (or spin,
  depending on your backpressure strategy)
- **Zero hot-path allocation** — `FixedPool` fields, mutex is
  pre-allocated at init
- **Flat memory** — 3 + 8 = 11 `FixedPool` fields total regardless
  of message volume

### Capacity

8 slots is enough for most producer/consumer pairs. If the producer
consistently outpaces the consumer the right fix is adding workers,
not enlarging the mailbox. A larger mailbox just hides the imbalance.

For higher capacity, declare more slots and change the `Branch` range
and `Modulo` divisor to match. The pattern scales linearly — 16 slots,
32 slots, etc.

---

## SEE ALSO

`AILang Language Introduction`,
`Memory Management Reference Manual`,
`Library.Arena`

---

## VERSION

Initial release. Self-contained by design — no Arena dependency,
no HashMap, no LinkagePool. Private 4 MB heap avoids allocator
contention between threads.

## COPYRIGHT

Copyright (c) 2025–2026 Sean Collins, 2 Paws Machine and Engineering.
Licensed under the Sean Collins Software License (SCSL).
