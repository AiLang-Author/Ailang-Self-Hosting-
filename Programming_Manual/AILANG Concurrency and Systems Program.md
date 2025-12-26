# AILANG Concurrency and Systems Programming Manual

## Table of Contents
1. [Overview](#overview)
2. [Actor Model Programming](#actor-model-programming)
3. [Task Management and Scheduling](#task-management-and-scheduling)
4. [Concurrent Execution Patterns](#concurrent-execution-patterns)
5. [Inter-Actor Communication](#inter-actor-communication)
6. [Systems Programming Primitives](#systems-programming-primitives)
7. [Real-Time and Scheduling](#real-time-and-scheduling)
8. [Memory Synchronization](#memory-synchronization)
9. [Performance and Optimization](#performance-and-optimization)
10. [Real-World Applications](#real-world-applications)

## Overview

AILANG provides a sophisticated concurrency model based on the Actor pattern, combined with systems programming capabilities for low-level control and real-time applications. The language enables safe, scalable concurrent programming while maintaining direct hardware access for performance-critical systems.

### Concurrency Philosophy
- **Actor Model**: Isolated actors with message passing
- **No Shared State**: Each actor maintains its own state
- **Cooperative Scheduling**: Explicit yielding for deterministic behavior
- **Systems Integration**: Direct system calls and hardware access
- **Deterministic Execution**: Predictable behavior for real-time systems

### Key Features
- **LoopActor**: Independent execution contexts
- **Message Passing**: Safe inter-actor communication
- **Task Management**: SubRoutine system for reusable logic
- **Scheduling Primitives**: Cooperative multitasking
- **Systems Access**: Low-level hardware and OS integration

## Actor Model Programming

### Actor Declaration and Structure

**Basic Actor Syntax:**
```ailang
// NOTE: LoopActor blocks are parsed but not executed (scheduler not implemented)
// Use SubRoutine pattern below for working equivalent
LoopActor.ActorName {
    // Actor initialization
    local_state = initial_value
    
    // Actor main logic
    WhileLoop actor_condition {
        // Process messages/work
        // Update local state
    }

// Working equivalent using SubRoutine:
/*
SubRoutine.ActorNameLogic {
    // Actor logic here
}
// Call with: RunTask(ActorNameLogic)
*/
    
    // Actor cleanup
}
```

**Simple Actor Example:**
```ailang
// NOTE: LoopActor blocks are parsed but not executed (scheduler not implemented)
// Use SubRoutine pattern below for working equivalent
LoopActor.Counter {
    count = 0
    running = 1
    
    WhileLoop EqualTo(running, 1) {
        count = Add(count, 1)
        PrintMessage("Counter:")
        PrintNumber(count)
        
        // Exit condition
        IfCondition GreaterEqual(count, 10) ThenBlock {
            running = 0
        }

// Working equivalent using SubRoutine:
/*
SubRoutine.CounterLogic {
    // Actor logic here
}
// Call with: RunTask(CounterLogic)
*/
    }
    
    PrintMessage("Counter actor finished")
}
```

### Actor Lifecycle Management

**Actor States:**
```ailang
// Actors can be in different states:
// - READY: Available for execution
// - RUNNING: Currently executing
// - BLOCKED: Waiting for resources
// - SUSPENDED: Temporarily halted
// - DEAD: Finished execution
```

**Actor Management Functions:**
```ailang
// LoopSpawn not yet functional - use manual scheduling
// handle = LoopSpawn(actor_name)  // TODO: Implement scheduler          // Create actor instance
LoopSuspend(handle)                     // Suspend actor execution
LoopResume(handle)                      // Resume suspended actor
state = LoopGetState(handle)            // Get current actor state
current = LoopGetCurrent()              // Get current actor handle
LoopSetPriority(handle, priority)       // Set scheduling priority
```

**Complete Actor Management Example:**
```ailang
// Define a worker actor
// NOTE: LoopActor blocks are parsed but not executed (scheduler not implemented)
// Use SubRoutine pattern below for working equivalent
LoopActor.WorkerActor {
    task_count = 0
    max_tasks = 5
    
    PrintMessage("Worker actor started")
    
    WhileLoop LessThan(task_count, max_tasks) {
        PrintMessage("Processing task:")
        PrintNumber(task_count)
        
        // Simulate work
        work_units = 0
        WhileLoop LessThan(work_units, 3) {
            work_units = Add(work_units, 1)
        }

// Working equivalent using SubRoutine:
/*
SubRoutine.WorkerActorLogic {
    // Actor logic here
}
// Call with: RunTask(WorkerActorLogic)
*/
        
        task_count = Add(task_count, 1)
        
        // Yield to other actors periodically
        IfCondition EqualTo(Modulo(task_count, 2), 0) ThenBlock {
            LoopYield()
        }
    }
    
    PrintMessage("Worker actor complete")
}

// Spawn and manage the actor
worker_// LoopSpawn not yet functional - use manual scheduling
// handle = LoopSpawn("WorkerActor")  // TODO: Implement scheduler
IfCondition NotEqual(worker_handle, 0) ThenBlock {
    PrintMessage("Worker spawned successfully")
    
    // Check actor state
    state = LoopGetState(worker_handle)
    PrintMessage("Worker state:")
    PrintNumber(state)
    
    // Let actor run
    LoopYield()
}
```

### Multiple Actor Coordination

**Producer-Consumer Pattern:**
```ailang
// Shared state (in real implementation, use message passing)
FixedPool.SharedBuffer {
    "items": Initialize=0        // Array for items
    "count": Initialize=0        // Current item count
    "capacity": Initialize=10    // Buffer capacity
    "producer_done": Initialize=0
}

// NOTE: LoopActor blocks are parsed but not executed (scheduler not implemented)
// Use SubRoutine pattern below for working equivalent
LoopActor.Producer {
    PrintMessage("Producer started")
    
    // Initialize shared buffer
    SharedBuffer.items = ArrayCreate(SharedBuffer.capacity)
    
    produced = 0
    max_items = 8
    
    WhileLoop LessThan(produced, max_items) {
        // Wait if buffer is full
        WhileLoop GreaterEqual(SharedBuffer.count, SharedBuffer.capacity) {
            LoopYield()  // Let consumer run
        }

// Working equivalent using SubRoutine:
/*
SubRoutine.ProducerLogic {
    // Actor logic here
}
// Call with: RunTask(ProducerLogic)
*/
        
        // Produce item
        item_value = Multiply(produced, 10)
        ArraySet(SharedBuffer.items, SharedBuffer.count, item_value)
        SharedBuffer.count = Add(SharedBuffer.count, 1)
        
        PrintMessage("Produced item:")
        PrintNumber(item_value)
        
        produced = Add(produced, 1)
        LoopYield()  // Let consumer process
    }
    
    SharedBuffer.producer_done = 1
    PrintMessage("Producer finished")
}

// NOTE: LoopActor blocks are parsed but not executed (scheduler not implemented)
// Use SubRoutine pattern below for working equivalent
LoopActor.Consumer {
    PrintMessage("Consumer started")
    
    consumed = 0
    
    WhileLoop EqualTo(SharedBuffer.producer_done, 0) {
        // Wait for items
        WhileLoop And(EqualTo(SharedBuffer.count, 0), 
                     EqualTo(SharedBuffer.producer_done, 0)) {
            LoopYield()  // Let producer run
        }

// Working equivalent using SubRoutine:
/*
SubRoutine.ConsumerLogic {
    // Actor logic here
}
// Call with: RunTask(ConsumerLogic)
*/
        
        // Consume item if available
        IfCondition GreaterThan(SharedBuffer.count, 0) ThenBlock {
            SharedBuffer.count = Subtract(SharedBuffer.count, 1)
            item = ArrayGet(SharedBuffer.items, SharedBuffer.count)
            
            PrintMessage("Consumed item:")
            PrintNumber(item)
            
            consumed = Add(consumed, 1)
        }
        
        LoopYield()  // Be cooperative
    }
    
    // Consume remaining items
    WhileLoop GreaterThan(SharedBuffer.count, 0) {
        SharedBuffer.count = Subtract(SharedBuffer.count, 1)
        item = ArrayGet(SharedBuffer.items, SharedBuffer.count)
        PrintMessage("Final consumed:")
        PrintNumber(item)
        consumed = Add(consumed, 1)
    }
    
    PrintMessage("Consumer finished, total consumed:")
    PrintNumber(consumed)
}

// Spawn both actors
producer_// LoopSpawn not yet functional - use manual scheduling
// handle = LoopSpawn("Producer")  // TODO: Implement scheduler
consumer_// LoopSpawn not yet functional - use manual scheduling
// handle = LoopSpawn("Consumer")  // TODO: Implement scheduler

// Run cooperative scheduler
scheduler_running = 1
WhileLoop EqualTo(scheduler_running, 1) {
    LoopYield()  // Execute next actor
    
    // Check if both are done (simplified)
    IfCondition And(EqualTo(SharedBuffer.producer_done, 1),
                   EqualTo(SharedBuffer.count, 0)) ThenBlock {
        scheduler_running = 0
    }
}

PrintMessage("All actors completed")
```

## Task Management and Scheduling

### SubRoutine System

**SubRoutine Declaration:**
```ailang
SubRoutine.TaskName {
    // Reusable logic
    // Can access global variables
    // Can call other subroutines
}

// Execute with RunTask
RunTask(TaskName)
```

**SubRoutine Examples:**
```ailang
// Utility subroutines
SubRoutine.LogMessage {
    PrintMessage("[LOG] System operation completed")
}

SubRoutine.IncrementCounter {
    global_counter = Add(global_counter, 1)
}

SubRoutine.ValidateSystem {
    IfCondition EqualTo(system_ready, 1) ThenBlock {
        PrintMessage("System validation passed")
    } ElseBlock {
        PrintMessage("System validation failed")
        error_count = Add(error_count, 1)
    }
}

// Complex subroutine with parameters (using global state)
SubRoutine.ProcessData {
    // Expects: input_data, operation_type
    IfCondition EqualTo(operation_type, 1) ThenBlock {
        // Type 1 processing
        result_data = Multiply(input_data, 2)
    } ElseBlock {
        // Type 2 processing  
        result_data = Add(input_data, 100)
    }
    
    RunTask(LogMessage)
}

// Usage
global_counter = 0
error_count = 0
system_ready = 1

RunTask(ValidateSystem)
RunTask(IncrementCounter)
RunTask(IncrementCounter)

PrintMessage("Counter value:")
PrintNumber(global_counter)

// Process data
input_data = 15
operation_type = 1
RunTask(ProcessData)
PrintMessage("Processed result:")
PrintNumber(result_data)
```

### Cooperative Scheduling

**Manual Scheduling:**
```ailang
Function.CooperativeScheduler {
    Input: max_cycles: Integer
    Output: Integer
    Body: {
        cycle_count = 0
        
        WhileLoop LessThan(cycle_count, max_cycles) {
            // Give each actor a time slice
            LoopYield()
            
            cycle_count = Add(cycle_count, 1)
            
            // Optional: Check for completion conditions
            IfCondition AllActorsComplete() ThenBlock {
                ReturnValue(cycle_count)
            }
        }
        
        ReturnValue(cycle_count)
    }
}

// Usage
cycles_run = CooperativeScheduler(100)
PrintMessage("Scheduler ran for cycles:")
PrintNumber(cycles_run)
```

**Priority-Based Scheduling:**
```ailang
FixedPool.SchedulerState {
    "high_priority_queue": Initialize=0
    "normal_priority_queue": Initialize=0  
    "low_priority_queue": Initialize=0
    "current_priority": Initialize=1
}

Function.PriorityScheduler {
    Body: {
        // Initialize priority queues
        SchedulerState.high_priority_queue = ArrayCreate(10)
        SchedulerState.normal_priority_queue = ArrayCreate(20)
        SchedulerState.low_priority_queue = ArrayCreate(30)
        
        running = 1
        
        WhileLoop EqualTo(running, 1) {
            // Schedule high priority first
            IfCondition GreaterThan(GetQueueSize(SchedulerState.high_priority_queue), 0) ThenBlock {
                SchedulerState.current_priority = 3
                RunNextActor(SchedulerState.high_priority_queue)
            } ElseBlock {
                // Then normal priority
                IfCondition GreaterThan(GetQueueSize(SchedulerState.normal_priority_queue), 0) ThenBlock {
                    SchedulerState.current_priority = 2
                    RunNextActor(SchedulerState.normal_priority_queue)
                } ElseBlock {
                    // Finally low priority
                    IfCondition GreaterThan(GetQueueSize(SchedulerState.low_priority_queue), 0) ThenBlock {
                        SchedulerState.current_priority = 1
                        RunNextActor(SchedulerState.low_priority_queue)
                    } ElseBlock {
                        // No actors to run
                        running = 0
                    }
                }
            }
            
            // Prevent infinite loops
            LoopYield()
        }
    }
}
```

## Concurrent Execution Patterns

### LoopMain - Primary Execution Context

**Main Event Loop:**
```ailang
LoopMain.Application {
    PrintMessage("Application main loop started")
    
    // Initialize application state
    app_running = 1
    frame_count = 0
    
    // Main application loop
    WhileLoop EqualTo(app_running, 1) {
        // Process frame
        ProcessFrame(frame_count)
        
        // Update frame counter
        frame_count = Add(frame_count, 1)
        
        // Yield to other actors
        LoopYield()
        
        // Check exit condition
        IfCondition GreaterEqual(frame_count, 100) ThenBlock {
            app_running = 0
        }
    }
    
    PrintMessage("Application main loop finished")
}

SubRoutine.ProcessFrame {
    // Expects: frame_count as global
    PrintMessage("Processing frame:")
    PrintNumber(frame_count)
    
    // Simulate frame processing work
    work = 0
    WhileLoop LessThan(work, 3) {
        work = Add(work, 1)
    }
}
```

### LoopStart - Initialization Context

**System Initialization:**
```ailang
// NOTE: LoopStart blocks don't auto-execute
LoopStart.SystemInit {
    PrintMessage("System initialization starting...")
    
    // Initialize global systems
    system_memory = Allocate(65536)  // 64KB system buffer
    system_ready = 0
    error_count = 0
    
    // Initialize subsystems
    RunTask(InitializeMemoryManager)
    RunTask(InitializeFileSystem)
    RunTask(InitializeNetwork)
    
    // Mark system as ready
    system_ready = 1
    
    PrintMessage("System initialization complete")
}
// Put initialization code in main flow or use:
// RunTask(InitializationSubroutine)

SubRoutine.InitializeMemoryManager {
    PrintMessage("  Memory manager initialized")
    // Setup memory pools, allocators, etc.
}

SubRoutine.InitializeFileSystem {
    PrintMessage("  File system initialized")
    // Mount file systems, check disk space, etc.
}

SubRoutine.InitializeNetwork {
    PrintMessage("  Network stack initialized") 
    // Initialize network interfaces, protocols, etc.
}
```

### LoopShadow - Background Processing

**Background Monitoring:**
```ailang
// NOTE: LoopShadow blocks don't execute (like LoopActor)
LoopShadow.SystemMonitor {
    PrintMessage("Background system monitor started")
    
    monitor_cycles = 0
    max_cycles = 20
    
    WhileLoop LessThan(monitor_cycles, max_cycles) {
        // Monitor system health
        RunTask(CheckMemoryUsage)
        RunTask(CheckCPULoad)
        RunTask(CheckDiskSpace)
        
        monitor_cycles = Add(monitor_cycles, 1)
        
        // Background tasks run less frequently
        LoopYield()
        LoopYield()  // Extra yield for lower priority
    }
// Use SubRoutine for background tasks
    
    PrintMessage("Background monitor finished")
}

SubRoutine.CheckMemoryUsage {
    // Simulated memory check
    memory_used = 75  // Percentage
    IfCondition GreaterThan(memory_used, 80) ThenBlock {
        PrintMessage("  WARNING: High memory usage")
    }
}

SubRoutine.CheckCPULoad {
    // Simulated CPU check  
    cpu_load = 45  // Percentage
    IfCondition GreaterThan(cpu_load, 90) ThenBlock {
        PrintMessage("  WARNING: High CPU load")
    }
}

SubRoutine.CheckDiskSpace {
    // Simulated disk check
    disk_free = 20  // Percentage free
    IfCondition LessThan(disk_free, 10) ThenBlock {
        PrintMessage("  WARNING: Low disk space")
    }
}
```

## Inter-Actor Communication

### Message Passing Simulation

**Message Queue Implementation:**
```ailang
FixedPool.MessageSystem {
    "message_queue": Initialize=0
    "queue_head": Initialize=0
    "queue_tail": Initialize=0
    "queue_size": Initialize=0
    "max_messages": Initialize=50
}

Function.InitializeMessageSystem {
    Output: Integer
    Body: {
        MessageSystem.message_queue = ArrayCreate(MessageSystem.max_messages)
        MessageSystem.queue_head = 0
        MessageSystem.queue_tail = 0
        MessageSystem.queue_size = 0
        ReturnValue(1)
    }
}

Function.SendMessage {
    Input: recipient_id: Integer, message_type: Integer, data: Integer
    Output: Integer
    Body: {
        // Check if queue is full
        IfCondition GreaterEqual(MessageSystem.queue_size, MessageSystem.max_messages) ThenBlock {
            PrintMessage("Message queue full!")
            ReturnValue(0)  // Failure
        }
        
        // Encode message: [recipient, type, data]
        message = Add(Add(Multiply(recipient_id, 1000000), 
                         Multiply(message_type, 1000)), data)
        
        // Add to queue
        ArraySet(MessageSystem.message_queue, MessageSystem.queue_tail, message)
        MessageSystem.queue_tail = Modulo(Add(MessageSystem.queue_tail, 1), 
                                         MessageSystem.max_messages)
        MessageSystem.queue_size = Add(MessageSystem.queue_size, 1)
        
        ReturnValue(1)  // Success
    }
}

Function.ReceiveMessage {
    Input: actor_id: Integer
    Output: Integer
    Body: {
        // Check if queue is empty
        IfCondition EqualTo(MessageSystem.queue_size, 0) ThenBlock {
            ReturnValue(0)  // No messages
        }
        
        // Look for messages for this actor
        i = MessageSystem.queue_head
        messages_checked = 0
        
        WhileLoop LessThan(messages_checked, MessageSystem.queue_size) {
            message = ArrayGet(MessageSystem.message_queue, i)
            recipient = Divide(message, 1000000)
            
            IfCondition EqualTo(recipient, actor_id) ThenBlock {
                // Extract message data
                remainder = Modulo(message, 1000000)
                message_type = Divide(remainder, 1000)
                data = Modulo(remainder, 1000)
                
                // Remove from queue (simplified - just mark as 0)
                ArraySet(MessageSystem.message_queue, i, 0)
                MessageSystem.queue_size = Subtract(MessageSystem.queue_size, 1)
                
                // Return encoded message type and data
                ReturnValue(Add(Multiply(message_type, 1000), data))
            }
            
            i = Modulo(Add(i, 1), MessageSystem.max_messages)
            messages_checked = Add(messages_checked, 1)
        }
        
        ReturnValue(0)  // No messages for this actor
    }
}

// Actors using message system
// NOTE: LoopActor blocks are parsed but not executed (scheduler not implemented)
// Use SubRoutine pattern below for working equivalent
LoopActor.Sender {
    actor_id = 1
    
    PrintMessage("Sender actor started")
    
    // Send several messages
    SendMessage(2, 100, 42)    // To actor 2, type 100, data 42
    SendMessage(2, 101, 84)    // To actor 2, type 101, data 84
    SendMessage(3, 200, 99)    // To actor 3, type 200, data 99
    
    PrintMessage("Sender sent all messages")
}

// Working equivalent using SubRoutine:
/*
SubRoutine.SenderLogic {
    // Actor logic here
}
// Call with: RunTask(SenderLogic)
*/

// NOTE: LoopActor blocks are parsed but not executed (scheduler not implemented)
// Use SubRoutine pattern below for working equivalent
LoopActor.Receiver {
    actor_id = 2
    
    PrintMessage("Receiver actor started")
    
    messages_received = 0
    max_messages = 2
    
    WhileLoop LessThan(messages_received, max_messages) {
        message = ReceiveMessage(actor_id)
        
        IfCondition NotEqual(message, 0) ThenBlock {
            message_type = Divide(message, 1000)
            data = Modulo(message, 1000)
            
            PrintMessage("Received message type:")
            PrintNumber(message_type)
            PrintMessage("With data:")
            PrintNumber(data)
            
            messages_received = Add(messages_received, 1)
        }

// Working equivalent using SubRoutine:
/*
SubRoutine.ReceiverLogic {
    // Actor logic here
}
// Call with: RunTask(ReceiverLogic)
*/ ElseBlock {
            // No messages, yield and try again
            LoopYield()
        }
    }
    
    PrintMessage("Receiver finished")
}

// Initialize and run
InitializeMessageSystem()

// Spawn actors
sender_// LoopSpawn not yet functional - use manual scheduling
// handle = LoopSpawn("Sender")  // TODO: Implement scheduler
receiver_// LoopSpawn not yet functional - use manual scheduling
// handle = LoopSpawn("Receiver")  // TODO: Implement scheduler

// Run scheduler
scheduler_steps = 0
WhileLoop LessThan(scheduler_steps, 20) {
    LoopYield()
    scheduler_steps = Add(scheduler_steps, 1)
}
```

## Systems Programming Primitives

### Low-Level System Access

**Hardware Register Access (Conceptual):**
```ailang
// Note: These are conceptual - actual implementation depends on target system
Function.ReadSystemRegister {
    Input: register_id: Integer
    Output: Integer
    Body: {
        // In real implementation, this would use inline assembly
        // or system calls to read hardware registers
        
        // Simulated register values
        IfCondition EqualTo(register_id, 1) ThenBlock {
            ReturnValue(0x12345678)  // CPU ID
        } ElseBlock {
            IfCondition EqualTo(register_id, 2) ThenBlock {
                ReturnValue(0x87654321)  // Status register
            } ElseBlock {
                ReturnValue(0)  // Unknown register
            }
        }
    }
}

Function.WriteSystemRegister {
    Input: register_id: Integer, value: Integer
    Output: Integer
    Body: {
        // In real implementation, this would write to hardware
        PrintMessage("Writing to register:")
        PrintNumber(register_id)
        PrintMessage("Value:")
        PrintNumber(value)
        
        ReturnValue(1)  // Success
    }
}

// System information gathering
cpu_id = ReadSystemRegister(1)
status_reg = ReadSystemRegister(2)

PrintMessage("CPU ID:")
PrintNumber(cpu_id)
PrintMessage("Status Register:")
PrintNumber(status_reg)

// Configure system
WriteSystemRegister(3, 0x1000)  // Set configuration register
```

### Memory Management Integration

**System-Level Memory Management:**
```ailang
Function.SystemMemoryManager {
    Body: {
        // Initialize memory pools for different purposes
        
        // Kernel memory pool
        kernel_pool = Allocate(1048576)  // 1MB for kernel
        IfCondition EqualTo(kernel_pool, 0) ThenBlock {
            PrintMessage("FATAL: Cannot allocate kernel memory")
            HaltSystem()
        }
        
        // User space pool
        user_pool = Allocate(4194304)    // 4MB for user space
        
        // Device driver pool
        driver_pool = Allocate(524288)   // 512KB for drivers
        
        // Set up memory regions
        SetupMemoryRegion(kernel_pool, 1048576, 1)  // Type 1: Kernel
        SetupMemoryRegion(user_pool, 4194304, 2)    // Type 2: User
        SetupMemoryRegion(driver_pool, 524288, 3)   // Type 3: Driver
        
        PrintMessage("System memory manager initialized")
    }
}

Function.SetupMemoryRegion {
    Input: base_address: Address, size: Integer, region_type: Integer
    Output: Integer
    Body: {
        PrintMessage("Memory region setup:")
        PrintMessage("  Base:")
        PrintNumber(base_address)
        PrintMessage("  Size:")
        PrintNumber(size)
        PrintMessage("  Type:")
        PrintNumber(region_type)
        
        // In real implementation, this would set up page tables,
        // protection bits, etc.
        
        ReturnValue(1)
    }
}

Function.HaltSystem {
    Body: {
        PrintMessage("System halted")
        // In real implementation, this would halt the CPU
    }
}

// Initialize system memory
SystemMemoryManager()
```

### Interrupt Simulation

**Interrupt Handler Framework:**
```ailang
FixedPool.InterruptSystem {
    "interrupt_table": Initialize=0
    "interrupt_count": Initialize=0
    "pending_interrupts": Initialize=0
    "interrupt_enabled": Initialize=1
}

Function.InitializeInterruptSystem {
    Output: Integer
    Body: {
        InterruptSystem.interrupt_table = ArrayCreate(256)  // 256 interrupt vectors
        InterruptSystem.pending_interrupts = ArrayCreate(32)  // Pending queue
        InterruptSystem.interrupt_count = 0
        
        // Set up common interrupt handlers
        SetInterruptHandler(0, TimerInterrupt)
        SetInterruptHandler(1, KeyboardInterrupt)
        SetInterruptHandler(2, NetworkInterrupt)
        
        PrintMessage("Interrupt system initialized")
        ReturnValue(1)
    }
}

Function.SetInterruptHandler {
    Input: interrupt_number: Integer, handler_id: Integer
    Output: Integer
    Body: {
        ArraySet(InterruptSystem.interrupt_table, interrupt_number, handler_id)
        ReturnValue(1)
    }
}

Function.TriggerInterrupt {
    Input: interrupt_number: Integer
    Output: Integer
    Body: {
        IfCondition EqualTo(InterruptSystem.interrupt_enabled, 0) ThenBlock {
            // Interrupts disabled, queue for later
            ArraySet(InterruptSystem.pending_interrupts, 
                    InterruptSystem.interrupt_count, interrupt_number)
            InterruptSystem.interrupt_count = Add(InterruptSystem.interrupt_count, 1)
            ReturnValue(0)
        }
        
        // Get handler
        handler_id = ArrayGet(InterruptSystem.interrupt_table, interrupt_number)
        IfCondition NotEqual(handler_id, 0) ThenBlock {
            ProcessInterrupt(handler_id, interrupt_number)
            ReturnValue(1)
        }
        
        ReturnValue(0)  // No handler
    }
}

Function.ProcessInterrupt {
    Input: handler_id: Integer, interrupt_number: Integer
    Output: Integer
    Body: {
        PrintMessage("Processing interrupt:")
        PrintNumber(interrupt_number)
        
        IfCondition EqualTo(handler_id, TimerInterrupt) ThenBlock {
            RunTask(HandleTimerInterrupt)
        } ElseBlock {
            IfCondition EqualTo(handler_id, KeyboardInterrupt) ThenBlock {
                RunTask(HandleKeyboardInterrupt)
            } ElseBlock {
                IfCondition EqualTo(handler_id, NetworkInterrupt) ThenBlock {
                    RunTask(HandleNetworkInterrupt)
                }
            }
        }
        
        ReturnValue(1)
    }
}

// Interrupt handler constants
TimerInterrupt = 100
KeyboardInterrupt = 101
NetworkInterrupt = 102

// Interrupt handler subroutines
SubRoutine.HandleTimerInterrupt {
    PrintMessage("  Timer interrupt handled")
    // Update system clock, schedule tasks, etc.
}

SubRoutine.HandleKeyboardInterrupt {
    PrintMessage("  Keyboard interrupt handled")
    // Read keyboard input, update input buffer
}

SubRoutine.HandleNetworkInterrupt {
    PrintMessage("  Network interrupt handled")
    // Process network packets, update buffers
}

// Usage
InitializeInterruptSystem()

// Simulate interrupts
TriggerInterrupt(0)  // Timer
TriggerInterrupt(1)  // Keyboard
TriggerInterrupt(2)  // Network
```

## Real-Time and Scheduling

### Deadline-Based Scheduling

**Real-Time Task Management:**
```ailang
FixedPool.RealTimeScheduler {
    "task_queue": Initialize=0
    "current_time": Initialize=0
    "max_tasks": Initialize=20
    "active_tasks": Initialize=0
}

Function.InitializeRealTimeScheduler {
    Output: Integer
    Body: {
        RealTimeScheduler.task_queue = ArrayCreate(RealTimeScheduler.max_tasks)
        RealTimeScheduler.current_time = 0
        RealTimeScheduler.active_tasks = 0
        
        PrintMessage("Real-time scheduler initialized")
        ReturnValue(1)
    }
}

Function.ScheduleTask {
    Input: task_id: Integer, deadline: Integer, priority: Integer
    Output: Integer
    Body: {
        IfCondition GreaterEqual(RealTimeScheduler.active_tasks, 
                                RealTimeScheduler.max_tasks) ThenBlock {
            PrintMessage("Task queue full!")
            ReturnValue(0)
        }
        
        // Encode task: [task_id, deadline, priority]
        encoded_task = Add(Add(Multiply(task_id, 1000000),
                              Multiply(deadline, 1000)), priority)
        
        ArraySet(RealTimeScheduler.task_queue, RealTimeScheduler.active_tasks, encoded_task)
        RealTimeScheduler.active_tasks = Add(RealTimeScheduler.active_tasks, 1)
        
        PrintMessage("Scheduled task:")
        PrintNumber(task_id)
        PrintMessage("Deadline:")
        PrintNumber(deadline)
        
        ReturnValue(1)
    }
}

Function.ExecuteScheduledTasks {
    Output: Integer
    Body: {
        executed_tasks = 0
        
        i = 0
        WhileLoop LessThan(i, RealTimeScheduler.active_tasks) {
            task = ArrayGet(RealTimeScheduler.task_queue, i)
            task_id = Divide(task, 1000000)
            remainder = Modulo(task, 1000000)
            deadline = Divide(remainder, 1000)
            priority = Modulo(remainder, 1000)
            
            // Check if deadline is met
            IfCondition LessEqual(deadline, RealTimeScheduler.current_time) ThenBlock {
                PrintMessage("Executing overdue task:")
                PrintNumber(task_id)
                
                ExecuteTask(task_id, priority)
                executed_tasks = Add(executed_tasks, 1)
                
                // Remove from queue (simplified)
                ArraySet(RealTimeScheduler.task_queue, i, 0)
            } ElseBlock {
                // Check if task should run now based on priority
                time_to_deadline = Subtract(deadline, RealTimeScheduler.current_time)
                IfCondition And(LessEqual(time_to_deadline, priority),
                               GreaterThan(priority, 5)) ThenBlock {
                    PrintMessage("Executing high priority task:")
                    PrintNumber(task_id)
                    
                    ExecuteTask(task_id, priority)
                    executed_tasks = Add(executed_tasks, 1)
                    
                    ArraySet(RealTimeScheduler.task_queue, i, 0)
                }
            }
            
            i = Add(i, 1)
        }
        
        ReturnValue(executed_tasks)
    }
}

Function.ExecuteTask {
    Input: task_id: Integer, priority: Integer
    Output: Integer
    Body: {
        // Route to specific task handlers
        IfCondition EqualTo(task_id, 1) ThenBlock {
            RunTask(CriticalSystemTask)
        } ElseBlock {
            IfCondition EqualTo(task_id, 2) ThenBlock {
                RunTask(NetworkProcessingTask)
            } ElseBlock {
                IfCondition EqualTo(task_id, 3) ThenBlock {
                    RunTask(UserInterfaceTask)
                } ElseBlock {
                    PrintMessage("Unknown task ID:")
                    PrintNumber(task_id)
                }
            }
        }
        
        ReturnValue(1)
    }
}

SubRoutine.CriticalSystemTask {
    PrintMessage("  Critical system task executed")
    // Handle critical system operations
}

SubRoutine.NetworkProcessingTask {
    PrintMessage("  Network processing task executed") 
    // Process network data
}

SubRoutine.UserInterfaceTask {
    PrintMessage("  User interface task executed")
    // Update user interface
}

// Usage
InitializeRealTimeScheduler()

// Schedule tasks with different deadlines and priorities
ScheduleTask(1, 10, 9)  // Critical task, deadline=10, priority=9
ScheduleTask(2, 15, 5)  // Network task, deadline=15, priority=5  
ScheduleTask(3, 20, 3)  // UI task, deadline=20, priority=3

// Simulate time progression and task execution
time_steps = 25
WhileLoop LessThan(RealTimeScheduler.current_time, time_steps) {
    PrintMessage("Time:")
    PrintNumber(RealTimeScheduler.current_time)
    
    executed = ExecuteScheduledTasks()
    PrintMessage("Tasks executed:")
    PrintNumber(executed)
    
    RealTimeScheduler.current_time = Add(RealTimeScheduler.current_time, 2)
}
```

## Memory Synchronization

### Atomic Operations Simulation

**Lock-Free Data Structures:**
```ailang
FixedPool.AtomicCounter {
    "value": Initialize=0
    "lock": Initialize=0
}

Function.AtomicIncrement {
    Input: counter_address: Address
    Output: Integer
    Body: {
        // Simulate atomic increment
        // In real implementation, this would use hardware atomic instructions
        
        // Busy wait for lock
        WhileLoop NotEqual(AtomicCounter.lock, 0) {
            // Spin wait (yield to prevent infinite loop in simulation)
            LoopYield()
        }
        
        // Acquire lock
        AtomicCounter.lock = 1
        
        // Critical section
        old_value = AtomicCounter.value
        AtomicCounter.value = Add(AtomicCounter.value, 1)
        
        // Release lock
        AtomicCounter.lock = 0
        
        ReturnValue(old_value)
    }
}

Function.AtomicRead {
    Output: Integer
    Body: {
        // Atomic read (usually doesn't need locking for aligned reads)
        value = AtomicCounter.value
        ReturnValue(value)
    }
}

// Test atomic operations with multiple actors
// NOTE: LoopActor blocks are parsed but not executed (scheduler not implemented)
// Use SubRoutine pattern below for working equivalent
LoopActor.AtomicTester1 {
    PrintMessage("Atomic tester 1 started")
    
    iterations = 0
    WhileLoop LessThan(iterations, 5) {
        old_val = AtomicIncrement(0)  // Address not used in simulation
        PrintMessage("Actor 1 incremented, old value:")
        PrintNumber(old_val)
        
        iterations = Add(iterations, 1)
        LoopYield()  // Let other actors run
    }

// Working equivalent using SubRoutine:
/*
SubRoutine.AtomicTester1Logic {
    // Actor logic here
}
// Call with: RunTask(AtomicTester1Logic)
*/
    
    PrintMessage("Atomic tester 1 finished")
}

// NOTE: LoopActor blocks are parsed but not executed (scheduler not implemented)
// Use SubRoutine pattern below for working equivalent
LoopActor.AtomicTester2 {
    PrintMessage("Atomic tester 2 started")
    
    iterations = 0
    WhileLoop LessThan(iterations, 5) {
        old_val = AtomicIncrement(0)
        PrintMessage("Actor 2 incremented, old value:")
        PrintNumber(old_val)
        
        iterations = Add(iterations, 1)
        LoopYield()
    }

// Working equivalent using SubRoutine:
/*
SubRoutine.AtomicTester2Logic {
    // Actor logic here
}
// Call with: RunTask(AtomicTester2Logic)
*/
    
    PrintMessage("Atomic tester 2 finished")
}

// Run atomic test
tester1_// LoopSpawn not yet functional - use manual scheduling
// handle = LoopSpawn("AtomicTester1")  // TODO: Implement scheduler
tester2_// LoopSpawn not yet functional - use manual scheduling
// handle = LoopSpawn("AtomicTester2")  // TODO: Implement scheduler

// Run for several cycles
cycles = 0
WhileLoop LessThan(cycles, 20) {
    LoopYield()
    cycles = Add(cycles, 1)
}

final_value = AtomicRead()
PrintMessage("Final atomic counter value:")
PrintNumber(final_value)
PrintMessage("Expected: 10")
```

## Performance and Optimization

### Actor Pool Management

**Actor Pooling for Performance:**
```ailang
FixedPool.ActorPool {
    "pool": Initialize=0
    "pool_size": Initialize=20
    "active_count": Initialize=0
    "free_list": Initialize=0
    "next_free": Initialize=0
}

Function.InitializeActorPool {
    Output: Integer
    Body: {
        ActorPool.pool = ArrayCreate(ActorPool.pool_size)
        ActorPool.free_list = ArrayCreate(ActorPool.pool_size)
        
        // Initialize free list
        i = 0
        WhileLoop LessThan(i, ActorPool.pool_size) {
            ArraySet(ActorPool.free_list, i, i)
            i = Add(i, 1)
        }
        
        ActorPool.next_free = ActorPool.pool_size
        ActorPool.active_count = 0
        
        PrintMessage("Actor pool initialized")
        ReturnValue(1)
    }
}

Function.AllocateActor {
    Output: Integer
    Body: {
        IfCondition EqualTo(ActorPool.next_free, 0) ThenBlock {
            PrintMessage("Actor pool exhausted!")
            ReturnValue(-1)
        }
        
        // Get free slot
        ActorPool.next_free = Subtract(ActorPool.next_free, 1)
        slot = ArrayGet(ActorPool.free_list, ActorPool.next_free)
        
        ActorPool.active_count = Add(ActorPool.active_count, 1)
        
        PrintMessage("Allocated actor slot:")
        PrintNumber(slot)
        
        ReturnValue(slot)
    }
}

Function.FreeActor {
    Input: slot: Integer
    Output: Integer
    Body: {
        IfCondition GreaterEqual(ActorPool.next_free, ActorPool.pool_size) ThenBlock {
            PrintMessage("Free list overflow!")
            ReturnValue(0)
        }
        
        // Return to free list
        ArraySet(ActorPool.free_list, ActorPool.next_free, slot)
        ActorPool.next_free = Add(ActorPool.next_free, 1)
        ActorPool.active_count = Subtract(ActorPool.active_count, 1)
        
        PrintMessage("Freed actor slot:")
        PrintNumber(slot)
        
        ReturnValue(1)
    }
}

// Usage
InitializeActorPool()

// Allocate several actors
actor1 = AllocateActor()
actor2 = AllocateActor()
actor3 = AllocateActor()

PrintMessage("Active actors:")
PrintNumber(ActorPool.active_count)

// Free some actors
FreeActor(actor2)
FreeActor(actor1)

PrintMessage("Active actors after free:")
PrintNumber(ActorPool.active_count)

// Reallocate (should reuse freed slots)
actor4 = AllocateActor()
PrintMessage("Reallocated actor (reused slot):")
PrintNumber(actor4)
```

## Working Implementation Patterns

### Currently Working Pattern: SubRoutine-based Concurrency
```ailang
// Define "actors" as SubRoutines
SubRoutine.Worker1 {
    // Worker logic
    PrintMessage("Worker1 executing")
}

SubRoutine.Worker2 {
    // Worker logic  
    PrintMessage("Worker2 executing")
}

// Use LoopMain for scheduler (LoopMain WORKS - executes inline)
LoopMain.Scheduler {
    cycles = 0
    WhileLoop LessThan(cycles, 10) {
        // Round-robin scheduling
        IfCondition EqualTo(Modulo(cycles, 2), 0) ThenBlock {
            RunTask(Worker1)
        } ElseBlock {
            RunTask(Worker2)
        }
        cycles = Add(cycles, 1)
    }
}
```

## Real-World Applications

### Web Server Architecture

**Concurrent Web Server Simulation:**
```ailang
FixedPool.WebServer {
    "connection_pool": Initialize=0
    "active_connections": Initialize=0
    "max_connections": Initialize=10
    "requests_processed": Initialize=0
}

Function.InitializeWebServer {
    Output: Integer
    Body: {
        WebServer.connection_pool = ArrayCreate(WebServer.max_connections)
        WebServer.active_connections = 0
        WebServer.requests_processed = 0
        
        PrintMessage("Web server initialized")
        PrintMessage("Max connections:")
        PrintNumber(WebServer.max_connections)
        
        ReturnValue(1)
    }
}

// NOTE: LoopActor blocks are parsed but not executed (scheduler not implemented)
// Use SubRoutine pattern below for working equivalent
LoopActor.ConnectionListener {
    PrintMessage("Connection listener started")
    
    simulated_requests = 15  // Simulate 15 incoming connections
    request_id = 1
    
    WhileLoop LessThan(request_id, simulated_requests) {
        IfCondition LessThan(WebServer.active_connections, WebServer.max_connections) ThenBlock {
            // Accept connection
            connection_slot = WebServer.active_connections
            ArraySet(WebServer.connection_pool, connection_slot, request_id)
            WebServer.active_connections = Add(WebServer.active_connections, 1)
            
            PrintMessage("Accepted connection:")
            PrintNumber(request_id)
            
            // Spawn worker to handle request
            SpawnWorker(request_id, connection_slot)
        }

// Working equivalent using SubRoutine:
/*
SubRoutine.ConnectionListenerLogic {
    // Actor logic here
}
// Call with: RunTask(ConnectionListenerLogic)
*/ ElseBlock {
            PrintMessage("Connection rejected - server full")
        }
        
        request_id = Add(request_id, 1)
        LoopYield()  // Let workers process
    }
    
    PrintMessage("Connection listener finished")
}

Function.SpawnWorker {
    Input: request_id: Integer, slot: Integer
    Output: Integer
    Body: {
        // In real implementation, would spawn actual worker actor
        PrintMessage("Worker spawned for request:")
        PrintNumber(request_id)
        
        // Simulate processing
        ProcessHTTPRequest(request_id, slot)
        
        ReturnValue(1)
    }
}

Function.ProcessHTTPRequest {
    Input: request_id: Integer, slot: Integer
    Output: Integer
    Body: {
        PrintMessage("Processing HTTP request:")
        PrintNumber(request_id)
        
        // Simulate request processing time
        work_units = 0
        processing_time = Modulo(request_id, 3)  // Variable processing time
        
        WhileLoop LessEqual(work_units, processing_time) {
            work_units = Add(work_units, 1)
            LoopYield()  // Cooperative processing
        }
        
        // Complete request
        WebServer.requests_processed = Add(WebServer.requests_processed, 1)
        WebServer.active_connections = Subtract(WebServer.active_connections, 1)
        
        PrintMessage("Request completed:")
        PrintNumber(request_id)
        
        ReturnValue(1)
    }
}

// NOTE: LoopActor blocks are parsed but not executed (scheduler not implemented)
// Use SubRoutine pattern below for working equivalent
LoopActor.ServerMonitor {
    PrintMessage("Server monitor started")
    
    monitor_cycles = 0
    max_cycles = 25
    
    WhileLoop LessThan(monitor_cycles, max_cycles) {
        PrintMessage("Server status - Active:")
        PrintNumber(WebServer.active_connections)
        PrintMessage("Processed:")
        PrintNumber(WebServer.requests_processed)
        
        monitor_cycles = Add(monitor_cycles, 1)
        LoopYield()
        LoopYield()  // Monitor runs less frequently
    }

// Working equivalent using SubRoutine:
/*
SubRoutine.ServerMonitorLogic {
    // Actor logic here
}
// Call with: RunTask(ServerMonitorLogic)
*/
    
    PrintMessage("Server monitor finished")
}

// Initialize and run web server
InitializeWebServer()

// Spawn server components
listener_// LoopSpawn not yet functional - use manual scheduling
// handle = LoopSpawn("ConnectionListener")  // TODO: Implement scheduler
monitor_// LoopSpawn not yet functional - use manual scheduling
// handle = LoopSpawn("ServerMonitor")  // TODO: Implement scheduler

// Run server
server_cycles = 0
WhileLoop LessThan(server_cycles, 50) {
    LoopYield()
    server_cycles = Add(server_cycles, 1)
}

PrintMessage("Web server simulation complete")
PrintMessage("Final stats - Processed:")
PrintNumber(WebServer.requests_processed)
```

### Operating System Kernel Simulation

**Microkernel Architecture:**
```ailang
// NOTE: LoopStart blocks don't auto-execute
LoopStart.KernelInit {
    PrintMessage("Kernel initialization starting...")
    
    // Initialize core kernel subsystems
    RunTask(InitializeMemoryManager)
    RunTask(InitializeProcessManager)  
    RunTask(InitializeDeviceManager)
    RunTask(InitializeFileSystem)
    
    kernel_ready = 1
    PrintMessage("Kernel initialization complete")
}
// Put initialization code in main flow or use:
// RunTask(InitializationSubroutine)

SubRoutine.InitializeMemoryManager {
    PrintMessage("  Memory manager: OK")
    memory_manager_ready = 1
}

SubRoutine.InitializeProcessManager {
    PrintMessage("  Process manager: OK")
    process_manager_ready = 1
}

SubRoutine.InitializeDeviceManager {
    PrintMessage("  Device manager: OK")
    device_manager_ready = 1
}

SubRoutine.InitializeFileSystem {
    PrintMessage("  File system: OK")
    filesystem_ready = 1
}

// NOTE: LoopActor blocks are parsed but not executed (scheduler not implemented)
// Use SubRoutine pattern below for working equivalent
LoopActor.ProcessScheduler {
    PrintMessage("Process scheduler started")
    
    // Simulate process scheduling
    process_queue = ArrayCreate(10)
    active_processes = 0
    
    // Add some processes to queue
    ArraySet(process_queue, 0, 101)  // Process ID 101
    ArraySet(process_queue, 1, 102)  // Process ID 102
    ArraySet(process_queue, 2, 103)  // Process ID 103
    active_processes = 3
    
    scheduler_cycles = 0
    max_cycles = 10
    
    WhileLoop LessThan(scheduler_cycles, max_cycles) {
        current_process = scheduler_cycles % active_processes
        pid = ArrayGet(process_queue, current_process)
        
        PrintMessage("Scheduling process:")
        PrintNumber(pid)
        
        // Give process time slice
        ExecuteProcess(pid)
        
        scheduler_cycles = Add(scheduler_cycles, 1)
        LoopYield()
    }

// Working equivalent using SubRoutine:
/*
SubRoutine.ProcessSchedulerLogic {
    // Actor logic here
}
// Call with: RunTask(ProcessSchedulerLogic)
*/
    
    PrintMessage("Process scheduler finished")
}

Function.ExecuteProcess {
    Input: process_id: Integer
    Output: Integer
    Body: {
        // Simulate process execution
        PrintMessage("  Executing process:")
        PrintNumber(process_id)
        
        // Process does some work
        work = 0
        WhileLoop LessThan(work, 2) {
            work = Add(work, 1)
        }
        
        ReturnValue(1)
    }
}

// NOTE: LoopActor blocks are parsed but not executed (scheduler not implemented)
// Use SubRoutine pattern below for working equivalent
LoopActor.DeviceDriver {
    PrintMessage("Device driver started")
    
    device_interrupts = 0
    max_interrupts = 5
    
    WhileLoop LessThan(device_interrupts, max_interrupts) {
        PrintMessage("Handling device interrupt:")
        PrintNumber(device_interrupts)
        
        // Process device I/O
        RunTask(ProcessDeviceIO)
        
        device_interrupts = Add(device_interrupts, 1)
        LoopYield()
    }

// Working equivalent using SubRoutine:
/*
SubRoutine.DeviceDriverLogic {
    // Actor logic here
}
// Call with: RunTask(DeviceDriverLogic)
*/
    
    PrintMessage("Device driver finished")
}

SubRoutine.ProcessDeviceIO {
    PrintMessage("  Device I/O processed")
    // Handle hardware device communication
}

LoopMain.KernelMain {
    PrintMessage("Kernel main loop started")
    
    // Wait for initialization
    WhileLoop EqualTo(kernel_ready, 0) {
        LoopYield()
    }
    
    PrintMessage("Kernel fully operational")
    
    // Main kernel loop
    kernel_cycles = 0
    max_kernel_cycles = 20
    
    WhileLoop LessThan(kernel_cycles, max_kernel_cycles) {
        // Handle system calls, interrupts, etc.
        RunTask(ProcessSystemCalls)
        
        kernel_cycles = Add(kernel_cycles, 1)
        LoopYield()
    }
    
    PrintMessage("Kernel main loop finished")
}

SubRoutine.ProcessSystemCalls {
    // Handle pending system calls from user processes
    // (Simulated)
}

// Global kernel state
kernel_ready = 0
memory_manager_ready = 0
process_manager_ready = 0
device_manager_ready = 0
filesystem_ready = 0

// Spawn kernel components
scheduler_// LoopSpawn not yet functional - use manual scheduling
// handle = LoopSpawn("ProcessScheduler")  // TODO: Implement scheduler
driver_// LoopSpawn not yet functional - use manual scheduling
// handle = LoopSpawn("DeviceDriver")  // TODO: Implement scheduler

// Run kernel
kernel_runtime = 0
WhileLoop LessThan(kernel_runtime, 40) {
    LoopYield()
    kernel_runtime = Add(kernel_runtime, 1)
}

PrintMessage("Kernel simulation complete")
```

This comprehensive manual provides everything needed to build sophisticated concurrent and systems-level applications in AILANG, from basic actor patterns to complex operating system simulations. The language's unique combination of actor-model concurrency with low-level systems access makes it ideal for embedded systems, real-time applications, and systems programming tasks.



# AILANG Concurrency - Implementation Status

## Current State (as of testing)

### ✅ WORKING Features

#### LoopMain
- **Status**: Fully functional
- **Behavior**: Executes inline in main program flow
- **Use case**: Can be used to implement schedulers, event loops, main program logic
```ailang
LoopMain.Application {
    // This code executes directly
    PrintMessage("This will run")
}
```

#### SubRoutine / RunTask
- **Status**: Fully functional
- **Behavior**: Callable code blocks
- **Use case**: Reusable logic, can simulate actors
```ailang
SubRoutine.Worker {
    // Reusable logic
}
RunTask(Worker)  // Executes the subroutine
```

#### FixedPool
- **Status**: Fully functional
- **Behavior**: Structured data storage
- **Use case**: Shared state, message passing simulation

### ⚠️ PARSED BUT NOT EXECUTED

#### LoopActor
- **Status**: Parsed, compiled as subroutine with skip jump, never executes
- **Issue**: Skip jump prevents execution, no runtime scheduler to invoke
- **Workaround**: Use SubRoutines to simulate actors
```ailang
// NOTE: LoopActor blocks are parsed but not executed (scheduler not implemented)
// Use SubRoutine pattern below for working equivalent
LoopActor.MyActor {
    // This code is compiled but never runs
    // Needs scheduler implementation
}

// Working equivalent using SubRoutine:
/*
SubRoutine.MyActorLogic {
    // Actor logic here
}
// Call with: RunTask(MyActorLogic)
*/
```

#### LoopStart
- **Status**: Parsed, stored but not executed
- **Issue**: No initialization hook to run these blocks
- **Workaround**: Put initialization code directly in main flow or LoopMain

#### LoopShadow  
- **Status**: Parsed, compiled with skip jump, never executes
- **Issue**: Similar to LoopActor - unreachable code
- **Workaround**: Use SubRoutines for background tasks

#### LoopSpawn
- **Status**: Function exists but implementation incomplete
- **Issue**: May not properly spawn actors
- **Workaround**: Manual scheduling with SubRoutines

### 📝 Implementation Notes

The concurrency primitives are architecturally sound but need a scheduler implementation to activate them. The compiler generates proper code structures:

1. **LoopActor** compiles to labeled subroutines with skip jumps
2. **LoopMain** executes inline (working as designed)
3. **LoopStart/LoopShadow** are recognized but lack execution triggers

### 🔧 Recommended Patterns

Until full actor support is implemented, use these patterns:

#### Pattern 1: SubRoutine-based Actors
```ailang
// Define "actors" as SubRoutines
SubRoutine.Actor1 {
    // Actor logic
}

SubRoutine.Actor2 {
    // Actor logic
}

// Scheduler in LoopMain
LoopMain.Scheduler {
    cycles = 0
    WhileLoop LessThan(cycles, 10) {
        IfCondition EqualTo(Modulo(cycles, 2), 0) ThenBlock {
            RunTask(Actor1)
        } ElseBlock {
            RunTask(Actor2)
        }
        cycles = Add(cycles, 1)
    }
}
```

#### Pattern 2: Message Passing with FixedPool
```ailang
FixedPool.Messages {
    "queue": Initialize=0
    "head": Initialize=0
    "tail": Initialize=0
}

// Simulate message passing between SubRoutine "actors"
```

### 🚧 Future Work Needed

1. **Scheduler Runtime**: Implement a scheduler that can invoke LoopActor subroutines
2. **Remove Skip Jumps**: Or add mechanism to jump into actor code
3. **LoopSpawn Implementation**: Complete the spawn function to return valid handles
4. **LoopStart Hook**: Add initialization phase before main execution
5. **LoopYield Support**: Implement cooperative yielding between actors

### 📢 Patches Welcome!

The foundation is solid - the compiler generates the right structures. What's needed is the runtime scheduler to orchestrate execution. Key areas for contribution:

- Scheduler implementation (can be in AILANG itself using LoopMain)
- Runtime support for actor handle management
- Yield/resume mechanism implementation
- Message passing infrastructure

The primitives are there, they just need to be wired together!