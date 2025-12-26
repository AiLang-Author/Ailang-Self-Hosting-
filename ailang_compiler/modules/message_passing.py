# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# ailang_compiler/modules/message_passing.py
"""
Message Passing Module for AILANG Compiler
Implements SendMessage and ReceiveMessage primitives
"""

import struct
from ailang_parser.ailang_ast import SendMessage, ReceiveMessage

class MessagePassing:
    """Handles message passing constructs"""
    
    def __init__(self, compiler_context):
        self.compiler = compiler_context
        self.asm = compiler_context.asm
        self.memory = compiler_context.memory
        
        # Message queue storage (simplified implementation)
        # In a real system, this would be inter-process or network-based
        self.message_queues = {}  # channel_name -> queue_var_name
        
    def compile_sendmessage(self, node: SendMessage):
        """
        Compile SendMessage construct.
        SendMessage.TargetChannel(param1-value1, param2-value2)
        
        For now, this is a simplified implementation that:
        1. Evaluates all parameters
        2. Stores them in a message structure
        3. "Sends" by storing in a queue variable
        """
        print(f"DEBUG: Compiling SendMessage to {node.target}")
        
        # Create or get the queue variable for this channel
        queue_var = f"__msgqueue_{node.target}"
        # Check in the compiler's variables dictionary directly
        if queue_var not in self.compiler.variables:
            # Allocate new variable
            self.compiler.stack_size += 8
            offset = self.compiler.stack_size
            self.compiler.variables[queue_var] = offset
            print(f"DEBUG: Allocated message queue {queue_var} at offset {offset}")
            
            # Initialize to 0 (empty queue marker)
            self.asm.emit_mov_rax_imm64(0)
            self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP-offset], RAX
            self.asm.emit_bytes(*struct.pack('<i', -offset))
        
        # For this simple implementation, we'll just store the last message
        # A real implementation would use a proper queue structure
        
        if node.parameters:
            # If there are parameters, combine them into a single value
            # For simplicity, we'll just store the first parameter's value
            first_param = list(node.parameters.values())[0]
            self.compiler.compile_expression(first_param)
            
            print(f"DEBUG: Storing message with {len(node.parameters)} parameters")
        else:
            # No parameters - send a simple signal (value 1)
            self.asm.emit_mov_rax_imm64(1)
            print("DEBUG: Sending signal message (no parameters)")
        
        # Store the message in the queue variable
        offset = self.compiler.variables[queue_var]
        self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP-offset], RAX
        self.asm.emit_bytes(*struct.pack('<i', -offset))
        
        print(f"DEBUG: Message sent to channel {node.target}")
        return True
    
    def compile_receivemessage(self, node: ReceiveMessage):
        """
        Compile ReceiveMessage construct.
        ReceiveMessage.ChannelType {
            // body statements
        }
        
        For now, this simulates receiving by:
        1. Checking if there's a message in the queue
        2. If yes, executing the body
        3. Clearing the message after processing
        """
        print(f"DEBUG: Compiling ReceiveMessage from {node.message_type}")
        
        # Get the queue variable for this channel
        queue_var = f"__msgqueue_{node.message_type}"
        
        # Ensure the queue variable exists
        if queue_var not in self.compiler.variables:
            # Allocate new variable
            self.compiler.stack_size += 8
            offset = self.compiler.stack_size
            self.compiler.variables[queue_var] = offset
            print(f"DEBUG: Allocated message queue {queue_var} at offset {offset}")
            
            # Initialize to 0 (no message)
            self.asm.emit_mov_rax_imm64(0)
            self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP-offset], RAX
            self.asm.emit_bytes(*struct.pack('<i', -offset))
        
        # Check if there's a message (non-zero value)
        offset = self.compiler.variables[queue_var]
        self.asm.emit_bytes(0x48, 0x8B, 0x85)  # MOV RAX, [RBP-offset]
        self.asm.emit_bytes(*struct.pack('<i', -offset))
        
        # Compare with 0
        self.asm.emit_bytes(0x48, 0x83, 0xF8, 0x00)  # CMP RAX, 0
        
        # Jump to end if no message
        no_message_label = self.asm.create_label()
        self.asm.emit_jump_to_label(no_message_label, "JE")
        
        # Message is available - execute the body
        print(f"DEBUG: Processing message body with {len(node.body)} statements")
        for stmt in node.body:
            self.compiler.compile_node(stmt)
        
        # Clear the message after processing (set to 0)
        self.asm.emit_mov_rax_imm64(0)
        offset = self.compiler.variables[queue_var]
        self.asm.emit_bytes(0x48, 0x89, 0x85)  # MOV [RBP-offset], RAX
        self.asm.emit_bytes(*struct.pack('<i', -offset))
        
        # Mark the no_message label
        self.asm.mark_label(no_message_label)
        
        print(f"DEBUG: ReceiveMessage from {node.message_type} completed")
        return True
    
    def compile_operation(self, node):
        """Route to appropriate message passing handler"""
        if isinstance(node, SendMessage):
            return self.compile_sendmessage(node)
        elif isinstance(node, ReceiveMessage):
            return self.compile_receivemessage(node)
        return False


# Integration function for the main compiler
def register_message_passing_in_compiler(compiler):
    """
    Register message passing module in the main compiler.
    Call this from ailang_compiler.py __init__ method.
    """
    from .message_passing import MessagePassing
    
    compiler.message_passing = MessagePassing(compiler)
    
    # Register in dispatch handlers
    if hasattr(compiler, 'dispatch_handlers'):
        compiler.dispatch_handlers['SendMessage'] = lambda n: compiler.message_passing.compile_sendmessage(n)
        compiler.dispatch_handlers['ReceiveMessage'] = lambda n: compiler.message_passing.compile_receivemessage(n)
        print("DEBUG: Registered SendMessage/ReceiveMessage in dispatch handlers")
    
    return compiler.message_passing