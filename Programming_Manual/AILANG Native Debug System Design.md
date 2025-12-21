# AILANG Native Debug System Design
# Built-in debugging as a language primitive

debug_primitives:
  # Core Debug Blocks
  debug_block:
    syntax: |
      Debug("label", level=1) {
        // Debug code only compiled with -D flag
      }
    compilation:
      - With -D: Compiles inline with symbols
      - Without -D: Completely stripped from binary
      - With -D2: Includes level 1 and 2 debug blocks
  
  # Debug Assertions
  debug_assert:
    syntax: |
      DebugAssert(condition, "message")
      DebugAssertEqual(value1, value2, "message")
      DebugAssertRange(value, min, max, "message")
    behavior:
      - Development: Halts program with stack trace
      - Production: Compiled out entirely
  
  # Trace Points
  debug_trace:
    syntax: |
      DebugTrace.Entry("Function.Name", param1, param2)
      DebugTrace.Exit("Function.Name", return_value)
      DebugTrace.Point("label", variable)
    output:
      - Timestamp + thread/agent ID + location + values
      - Can be redirected to file/socket/memory buffer
  
  # Memory Debugging
  debug_memory:
    syntax: |
      DebugMemory.Dump(address, size, "label")
      DebugMemory.Watch(variable, "on_change")
      DebugMemory.Leak.Start()
      DebugMemory.Leak.Check()
      DebugMemory.Pattern(address, size, pattern)
    features:
      - Memory leak detection
      - Buffer overflow detection
      - Use-after-free detection
      - Memory pattern verification
  
  # Performance Debugging
  debug_performance:
    syntax: |
      DebugPerf.Start("operation_name")
      DebugPerf.End("operation_name")
      DebugPerf.CacheStats()
      DebugPerf.TLBStats()
      DebugPerf.BranchStats()
    metrics:
      - CPU cycles
      - Cache hits/misses
      - TLB hits/misses
      - Branch predictions
  
  # Breakpoints
  debug_breakpoint:
    syntax: |
      DebugBreak("label")
      DebugBreak.Conditional(expression, "label")
      DebugBreak.Count(n, "label")  // Break after n hits
      DebugBreak.Data(address)      // Hardware watchpoint
    implementation:
      - Inserts INT3 instruction (x86)
      - Can be enabled/disabled at runtime
  
  # State Inspection
  debug_inspect:
    syntax: |
      DebugInspect.Variables()      // All variables in scope
      DebugInspect.Stack()          // Current stack frame
      DebugInspect.Pools()          // All pool states
      DebugInspect.Agents()         // Agent states (Phase 2B)
    output:
      - Formatted human-readable output
      - Optional JSON/binary format for tools

compiler_integration:
  debug_flags:
    "-D": "Enable level 1 debug"
    "-D2": "Enable level 1-2 debug"
    "-D3": "Enable all debug levels"
    "-Dtrace": "Enable only trace points"
    "-Dassert": "Enable only assertions"
    "-Dmem": "Enable memory debugging"
    "-Dperf": "Enable performance profiling"
    "-Dall": "Enable everything"
  
  debug_sections:
    elf_layout:
      ".debug_ailang": "Debug symbol information"
      ".debug_trace": "Trace point locations"
      ".debug_assert": "Assertion metadata"
      ".debug_map": "Source to binary mapping"
  
  symbol_generation:
    - Function names preserved
    - Variable names preserved
    - Line number mapping
    - Source file references

implementation_details:
  ast_nodes:
    - DebugBlock(label, level, body)
    - DebugAssert(condition, message)
    - DebugTrace(type, label, values)
    - DebugBreak(type, condition)
  
  lexer_tokens:
    - DEBUG
    - DEBUGASSERT
    - DEBUGTRACE
    - DEBUGBREAK
    - DEBUGMEMORY
    - DEBUGPERF
    - DEBUGINSPECT
  
  compiler_module:
    location: "ailang_compiler/modules/debug_ops.py"
    key_methods: |
      def compile_debug_block(self, node):
          if not self.debug_enabled:
              return  # Strip from binary
          
          # Emit debug entry marker
          self.emit_debug_marker(node.label)
          
          # Compile debug body
          self.compile_node(node.body)
          
          # Emit debug exit marker
          self.emit_debug_exit()
      
      def compile_debug_assert(self, node):
          if not self.debug_assertions:
              return
          
          # Evaluate condition
          self.compile_expression(node.condition)
          
          # Jump if true (assertion passed)
          pass_label = self.create_label()
          self.asm.emit_jump_if_true(pass_label)
          
          # Assertion failed - emit diagnostic
          self.emit_assertion_failure(node)
          
          self.mark_label(pass_label)

usage_examples:
  basic_debugging: |
    Function.Calculate {
        Input: x:, y:
        Body: {
            DebugTrace.Entry("Calculate", x, y)
            
            Debug("Input validation", level=1) {
                PrintMessage("Validating inputs")
                DebugAssertRange(x, 0, 100, "x out of range")
                DebugAssertRange(y, 0, 100, "y out of range")
            }
            
            result = Add(x, y)
            
            Debug("Result check", level=2) {
                PrintMessage("Result computed:")
                PrintNumber(result)
                DebugMemory.Dump(AddressOf(result), 8, "result memory")
            }
            
            DebugTrace.Exit("Calculate", result)
            ReturnValue(result)
        }
    }
  
  performance_profiling: |
    Function.HeavyComputation {
        Body: {
            DebugPerf.Start("matrix_multiply")
            
            // Computation here
            result = MatrixMultiply(a, b)
            
            DebugPerf.End("matrix_multiply")
            
            Debug("Performance Stats", level=3) {
                DebugPerf.CacheStats()
                DebugPerf.TLBStats()
            }
            
            ReturnValue(result)
        }
    }
  
  memory_debugging: |
    Function.ProcessBuffer {
        Input: buffer:
        Body: {
            DebugMemory.Leak.Start()
            
            // Allocate temporary buffer
            temp = Allocate(1024)
            
            Debug("Buffer state", level=2) {
                DebugMemory.Dump(buffer, 64, "input buffer")
                DebugMemory.Pattern(temp, 1024, 0xDEADBEEF)
            }
            
            // Process...
            
            Deallocate(temp)
            DebugMemory.Leak.Check()  // Verify no leaks
        }
    }

runtime_support:
  debug_output:
    destinations:
      - Console (default)
      - File (with rotation)
      - Network socket
      - Shared memory buffer
      - System log (syslog/journal)
    
    formatting:
      - Human-readable text
      - JSON structured
      - Binary protocol
      - CSV for analysis
  
  debug_control:
    runtime_enable: |
      // Can enable/disable at runtime
      DebugControl.Enable("trace")
      DebugControl.Disable("memory")
      DebugControl.SetLevel(2)
    
    conditional_debug: |
      // Debug only under conditions
      DebugControl.EnableIf(user_is_developer)
      DebugControl.EnableFor("Function.Problematic")

tooling_integration:
  vscode_extension:
    features:
      - Inline debug value display
      - Conditional breakpoint UI
      - Performance overlay
      - Memory visualization
  
  debug_server:
    protocol: "Debug Adapter Protocol (DAP)"
    features:
      - Remote debugging
      - Live variable inspection
      - Hot reload of debug settings
  
  analysis_tools:
    - Trace analyzer
    - Performance profiler UI
    - Memory leak detector
    - Cache behavior visualizer

advantages_over_existing:
  vs_printf_debugging:
    - Structured, not string-based
    - Zero overhead when disabled
    - Type-safe debug output
    - Integrated with language semantics
  
  vs_gdb:
    - No external debugger needed
    - Debug logic in source code
    - Hardware-aware (cache, TLB stats)
    - Agent/pool aware (AILANG specific)
  
  vs_valgrind:
    - Built into binary, not external
    - Lower overhead
    - AILANG memory model aware
    - Real-time, not post-mortem
