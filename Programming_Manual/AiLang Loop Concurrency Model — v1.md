# AiLang Loop Concurrency Model — v1.1

## 0. Scope
This document specifies the **Loop Concurrency Model** for AiLang:
- Entities
- Messaging
- Scheduling
- Ownership
- Synchronization
- Timeouts and failure
- Determinism

It is language-level and implementation-independent. It does **not** define OS threads, kernel preemption, or distributed semantics.

---

## 1. Terms

- **Loop** — Executable unit with owned state and a mailbox. Variants: `LoopMain`, `LoopActor`, `LoopStart`, `LoopShadow`, `SubRoutine`.  
- **Message** — Value transferred between loops by copy or move (never shared).  
- **Mailbox** — FIFO queue per loop with bounded capacity.  
- **Continuation** — Suspended computation resumed by the scheduler.

---

## 2. Loop Types

| Loop Type      | Description                                                   |
|----------------|---------------------------------------------------------------|
| **SubRoutine** | No concurrency; callable via `RunTask`. No mailbox.           |
| **LoopMain**   | Primary event loop; owns the main coordination context.       |
| **LoopActor**  | Isolated state + message handler (`LoopReceive`).             |
| **LoopStart**  | Runs once before `LoopMain` to initialize resources.          |
| **LoopShadow** | Background loop (`LoopContinue`/`LoopYield`).                 |

---

## 3. Messaging Semantics

### 3.1 Send / Receive / Reply
- **Send**: `LoopSend(target, msg)` enqueues `msg` into `target`’s mailbox. Non-blocking.  
- **Receive**: `LoopReceive x { case … }` dequeues and pattern-matches one message.  
- **Reply**: `LoopReply(value)` sends `value` back to the implicit reply channel for the current message.

### 3.2 Delivery Guarantees
- **At-most-once** delivery.  
- **Per-sender FIFO**: messages from the same sender arrive in order.  
- **No sharing**: moved values MUST NOT be used by the sender after transfer.

### 3.3 Backpressure & Capacity
- Each mailbox has capacity `N` (default is implementation-defined).  
- On overflow, the runtime applies a **pressure policy**:  
  - `"reject"` (drop message, default)  
  - `"block"` (cooperative wait)  
  - `"adaptive"` (LoopFlow rate negotiation)  

Example:
```ailang
LoopFlow.Send(consumer, data, pressure: "adaptive")
4. Scheduling
Cooperative within a worker thread; work-stealing MAY distribute loops across workers.

A loop yields when:

it executes LoopYield

its message handler returns

it blocks on LoopJoin, LoopSelect, or timeouts

Fairness
Implementations SHOULD provide local fairness: each runnable loop eventually runs.

Deterministic Replay
With the replay flag, the scheduler records (timestamp, source, payload hash) for each delivery and MUST replay them in the same order given identical inputs.

5. Control Primitives
LoopContinue — Run repeatedly until interrupted.

LoopYield([delay]) — Cooperative yield; optional delay.

LoopSequence — Step-wise sequential execution.

LoopTransaction — Atomic block with OnFailure rollback.

Example:

ailang
Copy code
LoopTransaction {
  Step1: ...
  Step2: ...
} OnFailure {
  PrintMessage("Transaction rolled back")
}
6. Lifecycle
LoopSpawn(Type, init?) — Create and start a loop.

LoopJoin(loop, timeout?) — Cooperatively wait for completion.

LoopInterrupt(loop, signal) — Request cancellation; observed at yield/message boundaries.

7. Errors, Time & Selection
LoopCatch { … } OnError e { … } — Error boundary.

LoopTimeout(ms) { … } OnTimeout { … } — Executes with a deadline.

LoopSelect { … } — Wait on multiple channels or timeout.

Example:

ailang
Copy code
LoopSelect {
  case Ch1: Handle1()
  case Ch2: Handle2()
  timeout 500: HandleTimeout()
}
8. Synchronization
LoopBarrier — Waits for N participants; runs OnComplete once.

9. Memory Model & Ownership
Exactly one loop owns a datum at a time.

Ownership transfer is explicit via messages.

Borrowed references are read-only and MUST NOT escape scope.

No global mutable state; wrap globals in pools.

Large messages SHOULD use move semantics or buffer pools.

10. Performance Guidance (Non-Normative)
Prefer batching (LoopFlow) for high-rate producers.

Co-locate chatty actors to reduce cross-core traffic.

Use NUMA hints where available.

Appendix A — Edge Cases
Mailbox Full

Default "reject": send fails; no partial enqueue.

"block": sender yields until space available.

"adaptive": producer slows/chunks.

Reply Without Sender

Compile-time error or runtime panic. Never silent.

Timeout vs Interrupt

If both trigger, interrupt wins.

Transaction in Handler

On failure, OnFailure executes, no message loss/duplication.

Appendix B — Conformance Checklist
 Per-sender FIFO preserved

 At-most-once delivery

 LoopJoin is cooperative

 Timeout fires exactly once

 Ownership transfer enforced

 Replay mode deterministic

Appendix C — Examples
Actor Counter
ailang
Copy code
LoopActor.Counter {
  count = 0
  LoopReceive m {
    case "inc": count = Add(count, 1)
    case "get": LoopReply(count)
  }
}

LoopMain.App {
  a = LoopSpawn(LoopActor.Counter)
  LoopSend(a, "inc")
  r = LoopSend(a, "get")
  PrintNumber(r)
}
Producer / Consumer with Backpressure
ailang
Copy code
producer = LoopSpawn(LoopActor.Producer)
consumer = LoopSpawn(LoopActor.Consumer)

LoopFlow.Send(consumer, data_chunk, pressure: "adaptive")


