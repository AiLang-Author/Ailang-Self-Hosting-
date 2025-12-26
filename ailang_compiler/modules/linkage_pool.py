# linkage_pool.py - Scalable version supporting unlimited LinkagePool parameters + STRING SUPPORT
# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.

"""
LinkagePool: Shared parameter blocks for inter-function/inter-program communication
ENHANCED: Support for unlimited LinkagePool parameters using stack-based storage
NEW: Support for STRING fields in LinkagePools
"""

import struct
from ailang_parser.ailang_ast import *

class LinkagePoolManager:
    """Manages LinkagePool declarations and access"""
    
    # Direction flags (stored in high bits)
    DIR_INPUT  = 0x10000000  # Read-only
    DIR_OUTPUT = 0x20000000  # Write-only
    DIR_INOUT  = 0x30000000  # Read-write
    DIR_MASK   = 0xF0000000
    
    def __init__(self, compiler):
        self.compiler = compiler
        self.asm = compiler.asm
        
        # LinkagePool definitions: pool_name -> {field_name -> (offset, direction)}
        self.linkage_pools = {}
        
        # NEW: Track field TYPES: pool_name -> {field_name -> 'int' or 'string'}
        self.field_types = {}
        
        # Runtime linkage blocks: pool_name -> R14 offset
        self.active_blocks = {}
        
        # Pool size tracking
        self.pool_sizes = {}
        
        # Track parameter locations for current function
        self.param_stack_offsets = {}  # param_name -> stack offset from RBP
        
    def compile_linkage_pool(self, node, pre_pass_only=False):
        """
        Compile LinkagePool declaration WITH STRING TYPE DETECTION
        """
        try:
            pool_name = f"LinkagePool.{node.name}"
            print(f"DEBUG: Processing LinkagePool {pool_name}")
            
            if pool_name not in self.linkage_pools:
                self.linkage_pools[pool_name] = {}
                self.field_types[pool_name] = {}  # NEW: Track field types
            
            offset = 0
            for item in node.body:
                if not hasattr(item, 'key'):
                    continue
                    
                field_name = item.key
                direction = self.DIR_INOUT  # Default to read-write
                field_type = 'int'  # Default to integer
                
                # Parse attributes
                if hasattr(item, 'attributes'):
                    for attr in item.attributes:
                        # Detect string fields by Initialize value
                        if attr.key == 'Initialize':
                            init_value = attr.value
                            
                            # If Initialize="" or Initialize="something", it's a string
                            if isinstance(init_value, String):
                                field_type = 'string'
                                print(f"DEBUG: Field '{field_name}' detected as STRING (String node)")
                            elif hasattr(init_value, 'value') and isinstance(init_value.value, str):
                                # Check if it's actually an empty string or has content
                                if init_value.value == "" or len(init_value.value) > 0:
                                    field_type = 'string'
                                    print(f"DEBUG: Field '{field_name}' detected as STRING (value='{init_value.value}')")
                            else:
                                field_type = 'int'
                                print(f"DEBUG: Field '{field_name}' detected as INTEGER")
                        
                        # Parse direction
                        if attr.key == 'Direction':
                            dir_str = attr.value.value if hasattr(attr.value, 'value') else str(attr.value)
                            if dir_str == 'Input':
                                direction = self.DIR_INPUT
                            elif dir_str == 'Output':
                                direction = self.DIR_OUTPUT
                            elif dir_str == 'InOut':
                                direction = self.DIR_INOUT
                
                # Store field info with direction and type
                self.linkage_pools[pool_name][field_name] = (offset, direction)
                self.field_types[pool_name][field_name] = field_type
                
                print(f"DEBUG: LinkagePool field {field_name} at offset {offset}, type={field_type}, direction={hex(direction)}")
                offset += 8  # 8 bytes per field (integer or string pointer)
            
            # Store total size
            self.pool_sizes[pool_name] = offset
            print(f"DEBUG: LinkagePool {pool_name} total size: {offset} bytes")
            
            if pre_pass_only:
                return True
            
            return True
            
        except Exception as e:
            print(f"ERROR: LinkagePool compilation failed: {str(e)}")
            raise
    
    def compile_function_with_linkage(self, node):
        """
        Handle ALL LinkagePool parameters for this function.
        Returns list of parameter indices we handled.
        """
        handled_indices = []
        param_regs = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']
        
        # Process ALL parameters to find LinkagePool ones
        for i, param_tuple in enumerate(node.input_params):
            param_name = param_tuple[0]
            param_type = param_tuple[1] if len(param_tuple) > 1 else None
            
            if not param_type:
                continue
                
            # Get type string
            if hasattr(param_type, 'base_type'):
                param_type_str = param_type.base_type
            else:
                param_type_str = str(param_type)
            
            # Is this a LinkagePool parameter?
            if not param_type_str.startswith('LinkagePool.'):
                continue
            
            # YES - we own this parameter completely
            handled_indices.append(i)
            
            # Allocate stack space for this parameter
            self.compiler.stack_size += 8
            offset = self.compiler.stack_size
            self.compiler.variables[param_name] = offset
            
            # Track the type
            if not hasattr(self.compiler, 'parameter_types'):
                self.compiler.parameter_types = {}
            self.compiler.parameter_types[param_name] = param_type_str

            # Also track in linkage module for field access
            if not hasattr(self, 'current_linkage_params'):
                self.current_linkage_params = {}
            self.current_linkage_params[param_name] = (param_type_str, offset)

            
            print(f"DEBUG: LinkagePool param '{param_name}' ({param_type_str}) at offset {offset}")
            
            # Store parameter from register to stack
            if i < 6:
                # Get parameter from register
                if param_regs[i] == 'rdi':
                    self.asm.emit_mov_rax_rdi()
                elif param_regs[i] == 'rsi':
                    self.asm.emit_mov_rax_rsi()
                elif param_regs[i] == 'rdx':
                    self.asm.emit_bytes(0x48, 0x89, 0xD0)  # MOV RAX, RDX
                elif param_regs[i] == 'rcx':
                    self.asm.emit_mov_rax_rcx()
                elif param_regs[i] == 'r8':
                    self.asm.emit_bytes(0x4C, 0x89, 0xC0)  # MOV RAX, R8
                elif param_regs[i] == 'r9':
                    self.asm.emit_bytes(0x4C, 0x89, 0xC8)  # MOV RAX, R9
                
                # Store to stack
                self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP-offset], RAX
                self.asm.emit_bytes(*struct.pack('<i', -offset))
                print(f"DEBUG: Stored {param_name} from {param_regs[i]} to [RBP-{offset}]")
            else:
                # Copy from caller's stack to local stack
                source_offset = 16 + 8 * (i - 6)  # Account for return address and saved RBP
                
                # MOV RAX, [RBP + source_offset]
                self.asm.emit_bytes(0x48, 0x8B, 0x85)
                self.asm.emit_bytes(*struct.pack('<i', source_offset))
                
                # MOV [RBP - offset], RAX
                self.asm.emit_bytes(0x48, 0x89, 0x85)
                self.asm.emit_bytes(*struct.pack('<i', -offset))
                
                print(f"DEBUG: Copied {param_name} from [RBP+{source_offset}] to [RBP-{offset}]")
            
            # Register with scope manager if available
            if hasattr(self.compiler, 'scope_mgr'):
                self.compiler.scope_mgr.add_parameter(param_name, offset)
        
        return handled_indices  # Tell user_functions which parameters we handled
    
    def is_string_field(self, pool_name, field_name):
        """Check if a LinkagePool field is a string type"""
        if pool_name in self.field_types:
            return self.field_types[pool_name].get(field_name) == 'string'
        return False
    
    def calculate_total_pool_requirements(self):
        """
        Calculate total memory needed for LinkagePools based on static analysis
        """
        # Count AllocateLinkage calls in the AST
        allocate_count = 0
        pools_used = set()
        
        def scan_node(node):
            nonlocal allocate_count, pools_used
            if hasattr(node, 'function') and node.function == 'AllocateLinkage':
                allocate_count += 1
                # Try to determine which pool
                if node.arguments and hasattr(node.arguments[0], 'name'):
                    pools_used.add(node.arguments[0].name)
            
            # Scan all child nodes
            for attr in dir(node):
                if not attr.startswith('_'):
                    child = getattr(node, attr)
                    if hasattr(child, '__dict__'):
                        scan_node(child)
                    elif isinstance(child, list):
                        for item in child:
                            if hasattr(item, '__dict__'):
                                scan_node(item)
        
        # Scan the entire AST if available
        if hasattr(self.compiler, 'ast'):
            scan_node(self.compiler.ast)
        
        # Calculate based on what we found
        total_size = 0
        
        if pools_used:
            # We know which pools are used
            for pool_name in pools_used:
                if pool_name in self.pool_sizes:
                    # Assume each pool might be allocated 3x (loops, functions)
                    total_size += self.pool_sizes[pool_name] * 3
        else:
            # Fallback: assume all defined pools used 2x each
            for pool_name, size in self.pool_sizes.items():
                total_size += size * 2
        
        # Add 50% safety margin
        total_size = int(total_size * 1.5)
        
        # Minimum 4KB (one page), maximum 1MB (unless overridden)
        total_size = max(4096, min(total_size, 1024*1024))
        
        print(f"DEBUG: Calculated LinkagePool requirements:")
        print(f"  Pools defined: {len(self.pool_sizes)}")
        print(f"  AllocateLinkage calls found: {allocate_count}")
        print(f"  Pools used: {pools_used or 'all'}")
        print(f"  Calculated size: {total_size} bytes ({total_size/1024:.1f} KB)")
        
        return total_size

    def allocate_linkage_block(self, pool_name):
        """
        Allocate linkage block AND INITIALIZE STRING FIELDS
        """
        if pool_name not in self.pool_sizes:
            raise Exception(f"LinkagePool {pool_name} not defined")

        size = self.pool_sizes[pool_name]
        print(f"DEBUG: Allocating linkage block for {pool_name}, size={size}")

        # Call HeapAlloc(size) - returns address in RAX
        self.asm.emit_mov_rdi_imm64(size)

        # CALL HeapAlloc
        if 'HeapAlloc' in self.compiler.subroutines:
            label = self.compiler.subroutines['HeapAlloc']
            self.asm.emit_call_to_label(label)
        else:
            # Fallback: use static buffer allocation
            print("WARNING: HeapAlloc not found, using static .data buffer allocation")
            
            if not hasattr(self, '_linkage_buffer_offset'):
                self._linkage_buffer_offset = len(self.asm.data)
                
                # Check for user override via pragma or constant
                buffer_size = None
                
                # Look for: Constant.LINKAGE_BUFFER_SIZE = 1048576  (1MB)
                if hasattr(self.compiler, 'constants'):
                    buffer_size = self.compiler.constants.get('LINKAGE_BUFFER_SIZE')
                
                # If no override, calculate intelligently
                if buffer_size is None:
                    buffer_size = self.calculate_total_pool_requirements()
                else:
                    print(f"DEBUG: Using user-specified LINKAGE_BUFFER_SIZE: {buffer_size} bytes")
                
                self.asm.data.extend(b'\x00' * buffer_size)
                self._linkage_buffer_size = buffer_size
                
                print(f"DEBUG: Allocated LinkagePool buffer: {buffer_size} bytes ({buffer_size/1024:.1f} KB)")
                
            if not hasattr(self, '_linkage_current'):
                self._linkage_current = 0

            current = self._linkage_current
            self._linkage_current += ((size + 15) // 16) * 16  # Align to 16 bytes
            
            if self._linkage_current > self._linkage_buffer_size:
                raise Exception(f"Static linkage buffer overflow: needed {self._linkage_current} bytes, have {self._linkage_buffer_size}")

            # Load the address of the allocated block
            alloc_addr_offset = self._linkage_buffer_offset + current
            self.asm.emit_load_data_address('rax', alloc_addr_offset)
        
        # NEW: INITIALIZE STRING FIELDS
        if pool_name in self.field_types:
            print(f"DEBUG: Initializing string fields for {pool_name}")
            # Save the block pointer
            self.asm.emit_push_rax()  # Save block pointer on stack
            
            for field_name, field_type in self.field_types[pool_name].items():
                if field_type == 'string':
                    field_offset, _ = self.linkage_pools[pool_name][field_name]
                    
                    print(f"DEBUG: Initializing string field '{field_name}' at offset {field_offset}")
                    
                    # Allocate empty string in data section
                    empty_str_offset = len(self.asm.data)
                    self.asm.data.extend(b'\x00')  # Empty null-terminated string
                    
                    # Load empty string address into RBX
                    self.asm.emit_load_data_address('rbx', empty_str_offset)
                    
                    # Get block pointer from stack (without popping)
                    # MOV RAX, [RSP]
                    self.asm.emit_bytes(0x48, 0x8B, 0x04, 0x24)
                    
                    # Store string pointer to field: [RAX + offset] = RBX
                    if field_offset == 0:
                        self.asm.emit_bytes(0x48, 0x89, 0x18)  # MOV [RAX], RBX
                    elif field_offset < 128:
                        self.asm.emit_bytes(0x48, 0x89, 0x58, field_offset)  # MOV [RAX+offset], RBX
                    else:
                        self.asm.emit_bytes(0x48, 0x89, 0x98)
                        self.asm.emit_bytes(*struct.pack('<i', field_offset))
                    
                    print(f"DEBUG: Initialized '{field_name}' with empty string pointer at data offset {empty_str_offset}")
            
            # Restore block pointer to RAX
            self.asm.emit_pop_rax()
        
        return True
    
    def compile_allocate_linkage(self, node):
        """
        Compile AllocateLinkage(LinkagePool.TypeName)
        Returns pointer to allocated block in RAX
        """
        if not node.arguments or len(node.arguments) == 0:
            raise Exception("AllocateLinkage requires a pool type argument")
        
        # Get pool type from argument
        pool_arg = node.arguments[0]
        if hasattr(pool_arg, 'name'):
            pool_type = pool_arg.name
        elif isinstance(pool_arg, str):
            pool_type = pool_arg
        else:
            pool_type = str(pool_arg)
        
        print(f"DEBUG: AllocateLinkage for {pool_type}")
        
        # Allocate the linkage block (with string initialization)
        self.allocate_linkage_block(pool_type)
        
        # Track that the result (in RAX) is a pointer to this type
        if not hasattr(self.compiler, 'pending_type'):
            self.compiler.pending_type = None
        print(f"DEBUG: Setting pending_type on compiler object id {id(self.compiler)}")
        self.compiler.pending_type = pool_type
        print(f"DEBUG: Verified pending_type set: {self.compiler.pending_type}")
        
        return True
    
    def compile_free_linkage(self, node):
        """
        Compile FreeLinkage(pool_variable)
        For now, just a no-op since we're using static allocation
        """
        print(f"DEBUG: FreeLinkage (no-op)")
        # Set RAX to 0 to indicate success
        self.asm.emit_mov_rax_imm64(0)
        return True
    
    def load_linkage_field_from_stack(self, param_name, pool_name, field_name, dest_reg='rax'):
        """
        Load a field from a LinkagePool parameter stored on the stack
        """
        if pool_name not in self.linkage_pools:
            raise Exception(f"LinkagePool {pool_name} not defined")
        
        if field_name not in self.linkage_pools[pool_name]:
            raise Exception(f"Field {field_name} not in LinkagePool {pool_name}")
        
        # Get the stack offset where this parameter's pointer is stored
        if param_name not in self.param_stack_offsets:
            if hasattr(self.compiler, 'current_linkage_params') and param_name in self.compiler.current_linkage_params:
                _, stack_offset = self.compiler.current_linkage_params[param_name]
            else:
                raise Exception(f"LinkagePool parameter {param_name} not found in current function")
        else:
            stack_offset = self.param_stack_offsets[param_name]
        
        field_offset, direction = self.linkage_pools[pool_name][field_name]
        
        print(f"DEBUG: Loading {pool_name}.{field_name} from param {param_name} at [RBP{stack_offset}]+{field_offset}")
        
        # Load the linkage pointer from stack to R11
        self.asm.emit_bytes(0x4C, 0x8B, 0x5D if stack_offset >= -128 else 0x9D)
        if stack_offset >= -128:
            self.asm.emit_bytes(stack_offset & 0xFF)
        else:
            self.asm.emit_bytes(*struct.pack('<i', stack_offset))
        
        # Load the field value from the linkage block
        if field_offset == 0:
            self.asm.emit_bytes(0x49, 0x8B, 0x03)  # MOV RAX, [R11]
        elif field_offset < 128:
            self.asm.emit_bytes(0x49, 0x8B, 0x43, field_offset)  # MOV RAX, [R11+offset]
        else:
            self.asm.emit_bytes(0x49, 0x8B, 0x83)
            self.asm.emit_bytes(*struct.pack('<i', field_offset))
        
        print(f"DEBUG: Loaded {pool_name}.{field_name} to RAX")
        return True
    
    def store_linkage_field_to_stack(self, param_name, pool_name, field_name, src_reg='rax'):
        """
        Store a field to a LinkagePool parameter stored on the stack
        """
        if pool_name not in self.linkage_pools:
            raise Exception(f"LinkagePool {pool_name} not defined")
        
        if field_name not in self.linkage_pools[pool_name]:
            raise Exception(f"Field {field_name} not in LinkagePool {pool_name}")
        
        # Get the stack offset
        if param_name not in self.param_stack_offsets:
            if hasattr(self.compiler, 'current_linkage_params') and param_name in self.compiler.current_linkage_params:
                _, stack_offset = self.compiler.current_linkage_params[param_name]
            else:
                raise Exception(f"LinkagePool parameter {param_name} not found in current function")
        else:
            stack_offset = self.param_stack_offsets[param_name]
        
        field_offset, direction = self.linkage_pools[pool_name][field_name]
        
        print(f"DEBUG: Storing to {pool_name}.{field_name} for param {param_name} at [RBP{stack_offset}]+{field_offset}")
        
        # Save value in R10
        self.asm.emit_bytes(0x49, 0x89, 0xC2)  # MOV R10, RAX
        
        # Load linkage pointer to R11
        self.asm.emit_bytes(0x4C, 0x8B, 0x5D if stack_offset >= -128 else 0x9D)
        if stack_offset >= -128:
            self.asm.emit_bytes(stack_offset & 0xFF)
        else:
            self.asm.emit_bytes(*struct.pack('<i', stack_offset))
        
        # Store value to field
        if field_offset == 0:
            self.asm.emit_bytes(0x4D, 0x89, 0x13)  # MOV [R11], R10
        elif field_offset < 128:
            self.asm.emit_bytes(0x4D, 0x89, 0x53, field_offset)
        else:
            self.asm.emit_bytes(0x4D, 0x89, 0x93)
            self.asm.emit_bytes(*struct.pack('<i', field_offset))
        
        print(f"DEBUG: Stored RAX to {pool_name}.{field_name}")
        return True
    
    def handle_field_access(self, base_name, field_name, context='expression'):
        """
        Central handler for ALL LinkagePool field access
        """
        print(f"\n=== LINKAGE FIELD ACCESS DEBUG ===")
        print(f"  Base: {base_name}, Field: {field_name}, Context: {context}")
        
        # Determine pool type
        pool_type = None
        
        if base_name in self.compiler.acronym_map:
            pool_type = self.compiler.acronym_map[base_name]
        elif hasattr(self.compiler, 'var_types') and base_name in self.compiler.var_types:
            pool_type = self.compiler.var_types[base_name]
        elif hasattr(self.compiler.user_functions, 'current_function'):
            func_name = self.compiler.user_functions.current_function
            if func_name and func_name in self.compiler.user_functions.user_functions:
                func_info = self.compiler.user_functions.user_functions[func_name]
                param_types = func_info.get('param_types', {})
                if base_name in param_types:
                    pool_type = param_types[base_name]
        
        if not pool_type or pool_type not in self.linkage_pools:
            print(f"  ERROR: Not a LinkagePool type: {pool_type}")
            return False
        
        if field_name not in self.linkage_pools[pool_type]:
            print(f"  ERROR: Field '{field_name}' not in pool '{pool_type}'")
            return False
        
        # Check if parameter or local variable
        if hasattr(self.compiler, 'parameter_types') and base_name in self.compiler.parameter_types:
            base_offset = self.compiler.variables[base_name]
            is_parameter = True
        else:
            is_parameter = False
            if base_name in self.compiler.variables:
                base_offset = self.compiler.variables[base_name]
            else:
                print(f"  ERROR: '{base_name}' not found")
                return False
        
        field_offset, direction = self.linkage_pools[pool_type][field_name]
        
        # Generate assembly
        if context == 'expression':
            self._generate_field_load(base_offset, field_offset, is_parameter)
        elif context == 'assignment':
            self._generate_field_store(base_offset, field_offset, is_parameter)
        
        return True

    def _generate_field_load(self, base_offset, field_offset, is_parameter):
        """Generate assembly to load a LinkagePool field into RAX"""
        # Load LinkagePool pointer
        self.asm.emit_bytes(0x48, 0x8B, 0x85)
        self.asm.emit_bytes(*struct.pack('<i', -base_offset))
        
        # Null check
        self.asm.emit_bytes(0x48, 0x85, 0xC0)  # TEST RAX, RAX
        skip_label = self.asm.create_label()
        self.asm.emit_jump_to_label(skip_label, "JNZ")
        
        # If null, return 0
        self.asm.emit_xor_eax_eax()
        end_label = self.asm.create_label()
        self.asm.emit_jump_to_label(end_label, "JMP")
        
        self.asm.mark_label(skip_label)
        
        # Load field
        if field_offset == 0:
            self.asm.emit_bytes(0x48, 0x8B, 0x00)  # MOV RAX, [RAX]
        elif field_offset < 128:
            self.asm.emit_bytes(0x48, 0x8B, 0x40, field_offset)
        else:
            self.asm.emit_bytes(0x48, 0x8B, 0x80)
            self.asm.emit_bytes(*struct.pack('<i', field_offset))
        
        self.asm.mark_label(end_label)

    def _generate_field_store(self, base_offset, field_offset, is_parameter):
        """Generate assembly to store RAX into a LinkagePool field"""
        # Save value in R10
        self.asm.emit_bytes(0x49, 0x89, 0xC2)  # MOV R10, RAX
        
        # Load LinkagePool pointer into R11
        self.asm.emit_bytes(0x4C, 0x8B, 0x9D)
        self.asm.emit_bytes(*struct.pack('<i', -base_offset))
        
        # Store R10 to [R11 + field_offset]
        if field_offset == 0:
            self.asm.emit_bytes(0x4D, 0x89, 0x13)
        elif field_offset < 128:
            self.asm.emit_bytes(0x4D, 0x89, 0x53, field_offset)
        else:
            self.asm.emit_bytes(0x4D, 0x89, 0x93)
            self.asm.emit_bytes(*struct.pack('<i', field_offset))