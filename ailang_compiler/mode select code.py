# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# Update ailang_compiler/ailang_compiler.py for dual-mode VM operations

# 1. ADD IMPORTS (around line 15):
from ailang_compiler.modules.virtual_memory import VirtualMemoryOps  # Kernel mode
from ailang_compiler.modules.virtual_memory_usermode import VirtualMemoryOpsUserMode  # User mode

# 2. UPDATE the AILANGToX64Compiler class __init__ method:

class AILANGToX64Compiler:
    """Main compiler orchestrator for AILANG to x86-64 compilation"""
    
    def __init__(self, vm_mode="user"):  # ADD vm_mode parameter
        self.asm = X64Assembler()
        self.elf = ELFGenerator()
        self.variables = {}  # Variable name -> stack offset
        self.stack_size = 0  # Total stack size
        self.label_counter = 0  # For unique labels
        self.max_depth = 0  # Track recursion depth
        self.acronym_table = {}
        self.file_handles = {}  # file_handle_name -> file_descriptor_variable
        self.file_buffer_size = 65536  # Default 64KB buffer
        self.open_files = {}  # Track open files
        
        # VM Mode Selection
        self.vm_mode = vm_mode.lower()
        print(f"DEBUG: VM Mode: {self.vm_mode.upper()}")
        
        # Initialize modules with dependency injection
        self.arithmetic = ArithmeticOps(self)
        self.fileio = FileIOOps(self)
        self.control_flow = ControlFlow(self)
        self.memory = MemoryManager(self)
        self.strings = StringOps(self)
        self.expressions = ExpressionCompiler(self)
        self.codegen = CodeGenerator(self)
        self.lowlevel = LowLevelOps(self)
        
        # VM OPERATIONS MODULE SELECTION
        if self.vm_mode == "kernel":
            self.virtual_memory = VirtualMemoryOps(self)
            print("DEBUG: Using KERNEL MODE VM operations (privileged instructions)")
        else:  # Default to user mode
            self.virtual_memory = VirtualMemoryOpsUserMode(self)
            print("DEBUG: Using USER MODE VM operations (safe for testing)")

# 3. ADD CONVENIENCE METHODS for easy mode switching:

    def set_vm_mode(self, mode):
        """Switch VM mode at runtime"""
        old_mode = self.vm_mode
        self.vm_mode = mode.lower()
        
        if self.vm_mode == "kernel":
            self.virtual_memory = VirtualMemoryOps(self)
            print(f"DEBUG: Switched from {old_mode.upper()} to KERNEL MODE VM operations")
        else:
            self.virtual_memory = VirtualMemoryOpsUserMode(self)
            print(f"DEBUG: Switched from {old_mode.upper()} to USER MODE VM operations")
    
    def is_kernel_mode(self):
        """Check if running in kernel mode"""
        return self.vm_mode == "kernel"
    
    def is_user_mode(self):
        """Check if running in user mode"""
        return self.vm_mode == "user"

# 4. UPDATE the main.py compile function to accept mode parameter:

def compile_ailang_to_executable(source_code: str, output_file: str = "program", vm_mode: str = "user"):
    """Compile AILANG source directly to executable with VM mode selection"""
    
    # Debug: Show current working directory
    cwd = os.getcwd()
    print(f"📂 Current directory: {cwd}")
    print(f"🔧 VM Mode: {vm_mode.upper()}")
    
    # Parse AILANG
    parser = AILANGCompiler()
    ast = parser.compile(source_code)
    
    # Compile to machine code with specified VM mode
    compiler = AILANGToX64Compiler(vm_mode=vm_mode)
    executable = compiler.compile(ast)
    
    # Use absolute path to ensure we know where it goes
    if not os.path.isabs(output_file):
        output_file = os.path.join(cwd, output_file)
    
    # Write executable
    print(f"📁 Writing to: {output_file}")
    
    try:
        with open(output_file, 'wb') as f:
            f.write(executable)
        print(f"✅ Wrote {len(executable)} bytes")
    except Exception as e:
        print(f"❌ Error writing file: {e}")
        return False
    
    # Make executable
    try:
        os.chmod(output_file, 0o755)
        print(f"✅ Made executable")
    except Exception as e:
        print(f"⚠️  Warning: Could not set executable permission: {e}")
    
    # Verify file exists
    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file)
        print(f"✅ Compiled to {output_file} ({file_size} bytes)")
        print(f"📍 Full path: {output_file}")
        print(f"🚀 Run with: {output_file}")
    else:
        print(f"❌ ERROR: File {output_file} was not created!")
    
    return True