# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

#parse_low_level.py
"""Parser methods for low-level operations"""

from typing import List, Tuple
from ..lexer import TokenType
from ..ailang_ast import *

class ParserLowLevelMixin:
    """Mixin for low-level operation parsing methods"""
    
    # === NEW: Low-Level Parsing Methods ===

    def parse_interrupt_handler(self) -> InterruptHandler:
        """Parse interrupt handler declaration"""
        start_token = self.consume(TokenType.INTERRUPTHANDLER)
        self.consume(TokenType.DOT)
        handler_name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.LPAREN)
        
        # Parse interrupt vector
        vector = self.parse_expression()
        self.consume(TokenType.RPAREN)
        
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        
        # Parse handler body
        body = []
        while not self.match(TokenType.RBRACE):
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            self.skip_newlines()
        
        self.consume(TokenType.RBRACE)
        return InterruptHandler(
            handler_type="interrupt",
            vector=vector,
            handler_name=handler_name,
            body=body,
            line=start_token.line,
            column=start_token.column
        )

    def parse_device_driver(self) -> DeviceDriver:
        """Parse device driver declaration"""
        start_token = self.consume(TokenType.DEVICEDRIVER)
        self.consume(TokenType.DOT)
        driver_name = self.consume(TokenType.IDENTIFIER).value
        
        # Parse device type
        self.consume(TokenType.COLON)
        device_type = self.consume(TokenType.IDENTIFIER).value
        
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        
        # Parse driver operations
        operations = {}
        while not self.match(TokenType.RBRACE):
            self.skip_newlines()
            if self.match(TokenType.IDENTIFIER):
                op_name = self.consume(TokenType.IDENTIFIER).value
                self.consume(TokenType.COLON)
                operations[op_name] = self.parse_expression()
            else:
                self.advance()
            self.skip_newlines()
        
        self.consume(TokenType.RBRACE)
        return DeviceDriver(
            driver_name=driver_name,
            device_type=device_type,
            operations=operations,
            line=start_token.line,
            column=start_token.column
        )

    def parse_bootloader_code(self) -> BootloaderCode:
        """Parse bootloader code block"""
        start_token = self.consume(TokenType.BOOTLOADER)
        self.consume(TokenType.DOT)
        stage = self.consume(TokenType.IDENTIFIER).value
        
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        
        body = []
        while not self.match(TokenType.RBRACE):
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            self.skip_newlines()
        
        self.consume(TokenType.RBRACE)
        return BootloaderCode(
            stage=stage,
            body=body,
            line=start_token.line,
            column=start_token.column
        )

    def parse_kernel_entry(self) -> KernelEntry:
        """Parse kernel entry point"""
        start_token = self.consume(TokenType.KERNELENTRY)
        self.consume(TokenType.DOT)
        entry_name = self.consume(TokenType.IDENTIFIER).value
        
        # Optional parameters
        parameters = []
        if self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            while not self.match(TokenType.RPAREN):
                param_name = self.consume(TokenType.IDENTIFIER).value
                self.consume(TokenType.COLON)
                param_type = self.parse_type()
                parameters.append((param_name, param_type))
                if self.match(TokenType.COMMA):
                    self.consume(TokenType.COMMA)
                    self.skip_newlines()
            self.consume(TokenType.RPAREN)
        
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        
        body = []
        while not self.match(TokenType.RBRACE):
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            self.skip_newlines()
        
        self.consume(TokenType.RBRACE)
        return KernelEntry(
            entry_name=entry_name,
            parameters=parameters,
            body=body,
            line=start_token.line,
            column=start_token.column
        )

    # === NEW: Low-Level Statement Parsing Methods ===

    def parse_interrupt_control(self) -> InterruptControl:
        """Parse interrupt control statements"""
        start_token = self.current_token
        operation = "enable" if start_token.type == TokenType.ENABLEINTERRUPTS else "disable"
        self.advance()
        
        return InterruptControl(
            operation=operation,
            line=start_token.line,
            column=start_token.column
        )

    def parse_inline_assembly(self) -> InlineAssembly:
        """Parse inline assembly blocks"""
        start_token = self.consume(TokenType.INLINEASSEMBLY)
        self.consume(TokenType.LPAREN)
        
        # Parse assembly code string
        assembly_code = self.consume(TokenType.STRING).value
        
        # Optional inputs, outputs, clobbers
        inputs = []
        outputs = []
        clobbers = []
        volatile = False
        
        while self.match(TokenType.COMMA):
            self.consume(TokenType.COMMA)
            self.skip_newlines()
            
            if self.match(TokenType.IDENTIFIER):
                param_name = self.consume(TokenType.IDENTIFIER).value
                self.consume(TokenType.COLON)
                
                if param_name == "inputs":
                    inputs = self.parse_assembly_constraints()
                elif param_name == "outputs":
                    outputs = self.parse_assembly_constraints()
                elif param_name == "clobbers":
                    clobbers = self.parse_string_array()
                elif param_name == "volatile":
                    volatile = self.parse_expression().value if hasattr(self.parse_expression(), 'value') else True
        
        self.consume(TokenType.RPAREN)
        return InlineAssembly(
            assembly_code=assembly_code,
            inputs=inputs,
            outputs=outputs,
            clobbers=clobbers,
            volatile=volatile,
            line=start_token.line,
            column=start_token.column
        )

    def parse_assembly_constraints(self) -> List[Tuple[str, ASTNode]]:
        """Parse assembly input/output constraints"""
        constraints = []
        self.consume(TokenType.LBRACKET)
        
        while not self.match(TokenType.RBRACKET):
            constraint = self.consume(TokenType.STRING).value
            self.consume(TokenType.COLON)
            value = self.parse_expression()
            constraints.append((constraint, value))
            
            if self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                self.skip_newlines()
        
        self.consume(TokenType.RBRACKET)
        return constraints

    def parse_system_call(self) -> FunctionCall:
        """Parse system call statements as a function call for the compiler."""
        start_token = self.consume(TokenType.SYSCALL)
        self.consume(TokenType.LPAREN)
        
        # The first argument to our special function is the syscall number.
        call_number = self.parse_expression()
        
        # Collect all arguments for the FunctionCall node.
        all_args = [call_number]
        
        while self.match(TokenType.COMMA):
            self.consume(TokenType.COMMA)
            self.skip_newlines()
            all_args.append(self.parse_expression())
        
        self.consume(TokenType.RPAREN)
        # Return a FunctionCall node. The backend will need to be taught
        # to recognize "SystemCall" as a special, built-in function.
        return FunctionCall(
            function="SystemCall",
            arguments=all_args,
            line=start_token.line,
            column=start_token.column
        )

    # === NEW: Low-Level Function Parsing ===

    def parse_lowlevel_function(self) -> ASTNode:
        """Parse low-level system functions"""
        op_token = self.current_token
        op_name = op_token.value
        self.advance()
        self.consume(TokenType.LPAREN)
        self.skip_newlines()
        
        args = []
        while not self.match(TokenType.RPAREN):
            args.append(self.parse_expression())
            if self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                self.skip_newlines()
            elif not self.match(TokenType.RPAREN):
                self.skip_newlines()
        
        self.consume(TokenType.RPAREN)
        
        # Create specialized AST nodes for certain operations
        if op_name == "Dereference":
            return Dereference(
                pointer=args[0] if args else None,
                size_hint=args[1].value if len(args) > 1 and hasattr(args[1], 'value') else None,
                line=op_token.line,
                column=op_token.column
            )
        elif op_name == "AddressOf":
            return AddressOf(
                variable=args[0] if args else None,
                line=op_token.line,
                column=op_token.column
            )
        elif op_name == "SizeOf":
            return SizeOf(
                target=args[0] if args else None,
                line=op_token.line,
                column=op_token.column
            )
        elif op_name == "StoreValue":
            # StoreValue doesn't need a special AST node, but we keep it as FunctionCall
            # This ensures all arguments are passed through correctly
            return FunctionCall(
                function="StoreValue",
                arguments=args,
                line=op_token.line,
                column=op_token.column
            )                      
        elif op_name in ["PortRead", "PortWrite"]:
            return PortOperation(
                operation="read" if op_name == "PortRead" else "write",
                port=args[0] if args else None,
                size=args[1].value if len(args) > 1 and hasattr(args[1], 'value') else "byte",
                value=args[2] if len(args) > 2 else None,
                line=op_token.line,
                column=op_token.column
            )
        else:
            # Generic function call for other low-level operations
            return FunctionCall(function=op_name, arguments=args,
                               line=op_token.line, column=op_token.column)

    def parse_pool_operation(self) -> FunctionCall:
        """Parse pool memory operations like PoolResize, PoolMove, etc."""
        op_token = self.current_token
        operation = op_token.value  # Will be "PoolResize", "PoolMove", etc.
        self.advance()
        
        self.consume(TokenType.LPAREN, f"Expected '(' after {operation}")
        
        arguments = []
        self.skip_newlines()
        
        # Parse arguments
        while not self.match(TokenType.RPAREN):
            arguments.append(self.parse_expression())
            self.skip_newlines()
            
            if not self.match(TokenType.RPAREN):
                self.consume(TokenType.COMMA, f"Expected ',' or ')' in {operation} arguments")
                self.skip_newlines()
        
        self.consume(TokenType.RPAREN, f"Expected ')' after {operation} arguments")
        
        return FunctionCall(
            function=operation,
            arguments=arguments,
            line=op_token.line,
            column=op_token.column
        )

    def parse_vm_operation(self):
        """Parse virtual memory operations"""
        op_token = self.current_token
        operation = op_token.value
        self.advance()
        
        # Some VM operations may have parameters
        if self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            args = []
            while not self.match(TokenType.RPAREN):
                args.append(self.parse_expression())
                if self.match(TokenType.COMMA):
                    self.consume(TokenType.COMMA)
                    self.skip_newlines()
            self.consume(TokenType.RPAREN)
            
            return FunctionCall(
                function=operation,
                arguments=args,
                line=op_token.line,
                column=op_token.column
            )
        else:
            # VM operation without parameters
            return FunctionCall(
                function=operation,
                arguments=[],
                line=op_token.line,
                column=op_token.column
            )

    def parse_lowlevel_type(self) -> LowLevelType:
        """Parse low-level type literals"""
        token = self.current_token
        type_name = token.value
        self.advance()
        
        # Map type names to sizes and signedness
        type_info = {
            'Byte': (1, False), 'Word': (2, False), 'DWord': (4, False), 'QWord': (8, False),
            'UInt8': (1, False), 'UInt16': (2, False), 'UInt32': (4, False), 'UInt64': (8, False),
            'Int8': (1, True), 'Int16': (2, True), 'Int32': (4, True), 'Int64': (8, True)
        }
        
        size, signed = type_info.get(type_name, (1, False))
        
        return LowLevelType(
            type_name=type_name,
            size=size,
            signed=signed,
            line=token.line,
            column=token.column
        )