# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

#parse_declarations.py
"""Parser methods for handling declarations"""

from typing import Optional
from ..lexer import TokenType
from ..ailang_ast import *
from .parse_error import ParseError

class ParserDeclarationsMixin:
    """Mixin for declaration parsing methods"""
    
    def parse_declaration(self) -> Optional[ASTNode]:
        if self.match(TokenType.LIBRARYIMPORT):
            return self.parse_library()
        elif self.match(TokenType.IDENTIFIER) and self.current_token.value == "AcronymDefinitions":
            return self.parse_acronym_definitions()
        elif self.match(TokenType.LINKAGEPOOL):
            return self.parse_linkage_pool()
        elif self.match(TokenType.FIXEDPOOL, TokenType.DYNAMICPOOL, TokenType.TEMPORALPOOL,
                       TokenType.NEURALPOOL, TokenType.KERNELPOOL, TokenType.ACTORPOOL,
                       TokenType.SECURITYPOOL, TokenType.CONSTRAINEDPOOL, TokenType.FILEPOOL):
            return self.parse_pool()
        elif self.match(TokenType.LOOPMAIN, TokenType.LOOPACTOR, TokenType.LOOPSTART,
                       TokenType.LOOPSHADOW):
            return self.parse_loop()
        elif self.match(TokenType.SUBROUTINE):
            return self.parse_subroutine()
        elif self.match(TokenType.FUNCTION):
            return self.parse_function()
        elif self.match(TokenType.COMBINATOR):
            return self.parse_combinator()
        elif self.match(TokenType.MACROBLOCK):
            return self.parse_macro_block()
        elif self.match(TokenType.SECURITYCONTEXT):
            return self.parse_security_context()
        elif self.match(TokenType.CONSTRAINEDTYPE):
            return self.parse_constrained_type()
        elif self.match(TokenType.CONSTANT):
            return self.parse_constant()
        # === NEW: Low-Level Declaration Parsing ===
        elif self.match(TokenType.INTERRUPTHANDLER):
            return self.parse_interrupt_handler()
        elif self.match(TokenType.DEVICEDRIVER):
            return self.parse_device_driver()
        elif self.match(TokenType.BOOTLOADER):
            return self.parse_bootloader_code()
        elif self.match(TokenType.KERNELENTRY):
            return self.parse_kernel_entry()
        else:
            stmt = self.parse_statement()
            if stmt:
                return stmt
            if self.current_token:
                self.error(f"Unexpected token '{self.current_token.value}' at top level")
            return None

    def parse_library(self) -> Library:
        self.push_context("library")
        start_token = self.consume(TokenType.LIBRARYIMPORT)
        self.consume(TokenType.DOT)
        name = self.parse_dotted_name()
        
        body = []  # Default to an empty body for simple imports
        self.skip_newlines()

        #  Check for an optional body ---
        if self.match(TokenType.LBRACE):
            self.consume(TokenType.LBRACE)
            self.skip_newlines()
            
            while not self.match(TokenType.RBRACE):
                # This is your original logic for parsing the body's contents
                self.skip_newlines()
                if self.match(TokenType.EOF):
                    self.error("Unclosed library body, reached end of file.")
                
                # You can add more declaration types here as needed
                if self.match(TokenType.LIBRARYIMPORT):
                    body.append(self.parse_library())
                elif self.match(TokenType.FUNCTION):
                    body.append(self.parse_function())
                elif self.match(TokenType.CONSTANT):
                    body.append(self.parse_constant())
                else:
                    self.advance() # Move past unexpected tokens to avoid getting stuck
                
                self.skip_newlines()

            self.consume(TokenType.RBRACE)
        

        self.pop_context()
        return Library(name=name, body=body, line=start_token.line, column=start_token.column)

    def parse_pool(self) -> Pool:
        pool_type_token = self.current_token
        pool_type = pool_type_token.value
        self.advance() # Consumes the pool type (e.g., DynamicPool)
        self.push_context(f"{pool_type}")

        #  Consume the DOT token between the type and the name ---
        self.consume(TokenType.DOT)
        
        
        name = self.parse_dotted_name()
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        body = []
        while not self.match(TokenType.RBRACE):
            self.skip_newlines()
            if self.match(TokenType.STRING):
                item = self.parse_resource_item()
                body.append(item)
            else:
                if not self.match(TokenType.RBRACE):
                    self.error(f"Expected string key for resource item, got {self.current_token.type.name}")
            self.skip_newlines()
        self.consume(TokenType.RBRACE)
        self.pop_context()
        return Pool(pool_type=pool_type, name=name, body=body,
                    line=pool_type_token.line, column=pool_type_token.column)

    def parse_subpool(self) -> SubPool:
        start_token = self.consume(TokenType.SUBPOOL)
        self.consume(TokenType.DOT)
        name = self.consume(TokenType.IDENTIFIER).value
        self.push_context(f"SubPool.{name}")
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        items = {}
        while not self.match(TokenType.RBRACE):
            self.skip_newlines()
            if self.match(TokenType.STRING):
                item = self.parse_resource_item()
                items[item.key] = item
            else:
                self.advance()
            self.skip_newlines()
        self.consume(TokenType.RBRACE)
        self.pop_context()
        return SubPool(name=name, items=items, line=start_token.line, column=start_token.column)

    def parse_resource_item(self) -> ResourceItem:
        key = self.consume(TokenType.STRING).value
        self.consume(TokenType.COLON)
        value = None
        attributes = {}

        # Handle attributes consistently with '=' ---
        # This loop handles one or more comma-separated attributes.
        has_attributes = True
        while has_attributes:
            # The attribute name is always an identifier-like keyword
            attr_token = self.current_token
            if not self.match(TokenType.INITIALIZE, TokenType.ELEMENTTYPE, TokenType.CANCHANGE, TokenType.CANBENULL, TokenType.MAXIMUMLENGTH, TokenType.MINIMUMLENGTH, TokenType.RANGE):
                self.error(f"Expected a pool attribute keyword (like Initialize, ElementType), but got {attr_token.type.name}")

            attr_name = self.consume(attr_token.type).value
            self.consume(TokenType.EQUALS) # All attributes now use '='

            if attr_name == 'Initialize':
                value = self.parse_primary()
            elif attr_name == 'ElementType':
                attributes[attr_name] = self.parse_type()
            elif attr_name == 'Range':
                attributes[attr_name] = self.parse_array_literal()
            else: # For CanChange, CanBeNull, MaximumLength, etc.
                attributes[attr_name] = self.parse_primary()

            if self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                self.skip_newlines()
            else:
                has_attributes = False
        
        return ResourceItem(key=key, value=value, attributes=attributes,
                            line=self.current_token.line, column=self.current_token.column)

    def parse_loop(self) -> ASTNode:  # Note: return type is ASTNode, not Loop
        loop_type_token = self.current_token
        loop_type = loop_type_token.value
        self.advance()
        self.push_context(f"{loop_type}")
        self.consume(TokenType.DOT)
        name = self.consume(TokenType.IDENTIFIER).value
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
        self.skip_newlines()
        
        self.pop_context()
        
        # Create the  AST node type based on loop_type
        if loop_type == 'LoopActor':
            return LoopActor(name=name, body=body, 
                            line=loop_type_token.line, column=loop_type_token.column)
        elif loop_type == 'LoopMain':
            return LoopMain(name=name, body=body,
                        line=loop_type_token.line, column=loop_type_token.column)
        elif loop_type == 'LoopStart':
            return LoopStart(name=name, body=body,
                            line=loop_type_token.line, column=loop_type_token.column)
        elif loop_type == 'LoopShadow':
            return LoopShadow(name=name, body=body,
                            line=loop_type_token.line, column=loop_type_token.column)
        else:
            # Fallback for any other loop types
            end_name = None
            if self.match(TokenType.LOOPEND):
                self.consume(TokenType.LOOPEND)
                self.consume(TokenType.DOT)
                end_name = self.consume(TokenType.IDENTIFIER).value
            return Loop(loop_type=loop_type, name=name, body=body, end_name=end_name,
                    line=loop_type_token.line, column=loop_type_token.column)

    def parse_subroutine(self) -> SubRoutine:
        start_token = self.consume(TokenType.SUBROUTINE)
        self.consume(TokenType.DOT)
        name = self.parse_dotted_name()
        self.push_context(f"SubRoutine.{name}")
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
        self.pop_context()
        return SubRoutine(name=name, body=body, line=start_token.line, column=start_token.column)

    def parse_function(self) -> Function:
        start_token = self.consume(TokenType.FUNCTION)
        self.consume(TokenType.DOT)
        name = self.parse_dotted_name()
        self.push_context(f"Function.{name}")
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        input_params = []
        output_type = None
        body = []
        while not self.match(TokenType.RBRACE):
            self.skip_newlines()
            if self.match(TokenType.INPUT):
                self.consume(TokenType.INPUT)
                self.consume(TokenType.COLON)
                if self.match(TokenType.LPAREN):
                    self.consume(TokenType.LPAREN)
                    while not self.match(TokenType.RPAREN):
                        param_name = self.consume(TokenType.IDENTIFIER).value
                        param_type = "Any"  # Default type
                        if self.match(TokenType.COLON):
                            self.consume(TokenType.COLON)
                            param_type = self.parse_type()

                        # === ADD THIS SECTION ===
                        # Check if we have access to acronym_map through compiler
                        acronym_map = None
                        if hasattr(self, 'compiler') and hasattr(self.compiler, 'acronym_map'):
                            acronym_map = self.compiler.acronym_map # Access acronym_map from compiler
                        elif hasattr(self, 'acronym_map'):
                            acronym_map = self.acronym_map

                        # Check for conflicts
                        if acronym_map and param_name in acronym_map:
                            print(f"WARNING at line {self.current_token.line}: Parameter '{param_name}' conflicts with acronym!")
                            print(f"  Acronym expands to: {acronym_map[param_name]}")
                            print(f"  Suggest using: {param_name.lower()}_param or {param_name}~ to force expansion")
                        # === END ADDITION ===

                        input_params.append((param_name, param_type))
                        if self.match(TokenType.COMMA):
                            self.consume(TokenType.COMMA)
                            self.skip_newlines()
                    self.consume(TokenType.RPAREN)
                else:
                    param_name = self.consume(TokenType.IDENTIFIER).value
                    param_type = "Any"  # Default type
                    if self.match(TokenType.COLON):
                        self.consume(TokenType.COLON)
                        param_type = self.parse_type()

                    # === ADD THIS SECTION FOR SINGLE PARAM CASE ===
                    # Check if we have access to acronym_map through compiler
                    acronym_map = None
                    if hasattr(self, 'compiler') and hasattr(self.compiler, 'acronym_map'):
                        acronym_map = self.compiler.acronym_map
                    elif hasattr(self, 'acronym_map'):
                        acronym_map = self.acronym_map

                    # Check for conflicts
                    if acronym_map and param_name in acronym_map:
                        print(f"WARNING at line {self.current_token.line}: Parameter '{param_name}' conflicts with acronym!")
                        print(f"  Acronym expands to: {acronym_map[param_name]}")
                        print(f"  Suggest using: {param_name.lower()}_param or {param_name}~ to force expansion")
                    # === END ADDITION ===

                    input_params.append((param_name, param_type))
            elif self.match(TokenType.OUTPUT):
                self.consume(TokenType.OUTPUT)
                self.consume(TokenType.COLON)
                output_type = self.parse_type()
            elif self.match(TokenType.BODY):
                self.consume(TokenType.BODY)
                self.consume(TokenType.COLON)
                self.skip_newlines()
                self.consume(TokenType.LBRACE)
                self.skip_newlines()
                while not self.match(TokenType.RBRACE):
                    stmt = self.parse_statement()
                    if stmt:
                        body.append(stmt)
                    self.skip_newlines()
                self.consume(TokenType.RBRACE)
            else:
                self.advance()
            self.skip_newlines()
        self.consume(TokenType.RBRACE)
        self.pop_context()
        return Function(name=name, input_params=input_params, output_type=output_type,
                        body=body, line=start_token.line, column=start_token.column)

    def parse_lambda(self) -> Lambda:
        start_token = self.consume(TokenType.LAMBDA)
        self.consume(TokenType.LPAREN)
        params = []
        while not self.match(TokenType.RPAREN):
            params.append(self.consume(TokenType.IDENTIFIER).value)
            if self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                self.skip_newlines()
        self.consume(TokenType.RPAREN)
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        body = self.parse_expression()
        self.skip_newlines()
        self.consume(TokenType.RBRACE)
        return Lambda(params=params, body=body, line=start_token.line, column=start_token.column)

    def parse_combinator(self) -> Combinator:
        start_token = self.consume(TokenType.COMBINATOR)
        self.consume(TokenType.DOT)
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.EQUALS)
        self.skip_newlines()
        definition = self.parse_expression()
        return Combinator(name=name, definition=definition,
                         line=start_token.line, column=start_token.column)

    def parse_macro_block(self) -> MacroBlock:
        start_token = self.consume(TokenType.MACROBLOCK)
        self.consume(TokenType.DOT)
        name = self.parse_dotted_name()
        self.push_context(f"MacroBlock.{name}")
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        macros = {}
        while not self.match(TokenType.RBRACE):
            self.skip_newlines()
            if self.match(TokenType.MACRO):
                macro = self.parse_macro_definition()
                macros[macro.name] = macro
            else:
                self.advance()
            self.skip_newlines()
        self.consume(TokenType.RBRACE)
        self.pop_context()
        return MacroBlock(name=name, macros=macros,
                         line=start_token.line, column=start_token.column)

    def parse_macro_definition(self) -> MacroDefinition:
        start_token = self.consume(TokenType.MACRO)
        self.consume(TokenType.DOT)
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.LPAREN)
        params = []
        while not self.match(TokenType.RPAREN):
            params.append(self.consume(TokenType.IDENTIFIER).value)
            if self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                self.skip_newlines()
        self.consume(TokenType.RPAREN)
        self.consume(TokenType.EQUALS)
        self.skip_newlines()
        body = self.parse_expression()
        return MacroDefinition(name=name, params=params, body=body,
                             line=start_token.line, column=start_token.column)

    def parse_security_context(self) -> SecurityContext:
        start_token = self.consume(TokenType.SECURITYCONTEXT)
        self.consume(TokenType.DOT)
        name = self.consume(TokenType.IDENTIFIER).value
        self.push_context(f"SecurityContext.{name}")
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        levels = {}
        while not self.match(TokenType.RBRACE):
            self.skip_newlines()
            if self.match(TokenType.LEVEL):
                level = self.parse_security_level()
                levels[level.name] = level
            else:
                self.advance()
            self.skip_newlines()
        self.consume(TokenType.RBRACE)
        self.pop_context()
        return SecurityContext(name=name, levels=levels,
                             line=start_token.line, column=start_token.column)

    def parse_security_level(self) -> SecurityLevel:
        self.consume(TokenType.LEVEL)
        self.consume(TokenType.DOT)
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.EQUALS)
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        allowed_operations = []
        denied_operations = []
        memory_limit = None
        cpu_quota = None
        while not self.match(TokenType.RBRACE):
            self.skip_newlines()
            if self.match(TokenType.ALLOWEDOPERATIONS):
                self.consume(TokenType.ALLOWEDOPERATIONS)
                self.consume(TokenType.COLON)
                allowed_operations = self.parse_string_array()
            elif self.match(TokenType.DENIEDOPERATIONS):
                self.consume(TokenType.DENIEDOPERATIONS)
                self.consume(TokenType.COLON)
                denied_operations = self.parse_string_array()
            elif self.match(TokenType.MEMORYLIMIT):
                self.consume(TokenType.MEMORYLIMIT)
                self.consume(TokenType.COLON)
                memory_limit = self.parse_expression()
            elif self.match(TokenType.CPUQUOTA):
                self.consume(TokenType.CPUQUOTA)
                self.consume(TokenType.COLON)
                cpu_quota = self.parse_expression()
            else:
                self.advance()
            if self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
            self.skip_newlines()
        self.consume(TokenType.RBRACE)
        return SecurityLevel(name=name, allowed_operations=allowed_operations,
                             denied_operations=denied_operations,
                             memory_limit=memory_limit, cpu_quota=cpu_quota,
                             line=self.current_token.line, column=self.current_token.column)

    def parse_constrained_type(self) -> ConstrainedType:
        start_token = self.consume(TokenType.CONSTRAINEDTYPE)
        self.consume(TokenType.DOT)
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.EQUALS)
        base_type = self.parse_type()
        self.consume(TokenType.WHERE)
        self.consume(TokenType.LBRACE)
        constraints = self.parse_expression()
        self.consume(TokenType.RBRACE)
        return ConstrainedType(name=name, base_type=base_type, constraints=constraints,
                               line=start_token.line, column=start_token.column)

    def parse_constant(self) -> Constant:
        start_token = self.consume(TokenType.CONSTANT)
        self.consume(TokenType.DOT)
        name = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.EQUALS)
        value = self.parse_expression()
        return Constant(name=name, value=value,
                        line=start_token.line, column=start_token.column)

    def parse_acronym_definitions(self) -> AcronymDefinitions:
        """
        Parse AcronymDefinitions block
        
        AcronymDefinitions {
            SHORT: "LongName"
            I2: "Input2"
            O1: "Output1"
        }
        """
        start_token = self.current_token
        self.consume(TokenType.IDENTIFIER)  # Consume "AcronymDefinitions"
        
        print(f"DEBUG: Parsing AcronymDefinitions")
        
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        
        mappings = {}
        
        while not self.match(TokenType.RBRACE):
            # Parse: SHORT: "LongName"
            acronym = self.consume(TokenType.IDENTIFIER).value
            self.consume(TokenType.COLON)
            full_name = self.consume(TokenType.STRING).value
            
            mappings[acronym] = full_name
            print(f"DEBUG: Acronym mapping: {acronym} -> {full_name}")
            
            self.skip_newlines()
        
        self.consume(TokenType.RBRACE)
        
        return AcronymDefinitions(
            mappings=mappings,
            line=start_token.line,
            column=start_token.column
        )
    
    def parse_linkage_pool(self) -> LinkagePoolDecl:
        """
        Parse LinkagePool declaration
        
        LinkagePool.Name {
            "field1": Initialize=0, Direction=Input
            "field2": Initialize=0, Direction=Output
        }
        """
        start_token = self.consume(TokenType.LINKAGEPOOL)
        self.consume(TokenType.DOT)
        
        pool_name = self.parse_dotted_name()
        
        print(f"DEBUG: Parsing LinkagePool.{pool_name}")
        
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        
        body = []
        
        while not self.match(TokenType.RBRACE):
            # Parse pool entry: "field_name": Initialize=0, Direction=Input
            key = self.consume(TokenType.STRING).value
            self.consume(TokenType.COLON)
            
            # Parse attributes - SAME PATTERN AS parse_pool()
            attributes = []
            has_attributes = True
            
            while has_attributes:
                # Check for known attribute keywords
                if not self.match(TokenType.INITIALIZE, TokenType.DIRECTION, 
                                TokenType.CANCHANGE, TokenType.CANBENULL):
                    self.error(f"Expected attribute keyword (Initialize, Direction, CanChange, etc.)")
                
                attr_token = self.current_token
                attr_name = self.consume(attr_token.type).value
                self.consume(TokenType.EQUALS)  # Use EQUALS, not ASSIGN
                
                # Parse attribute value based on type
                if attr_name == 'Initialize':
                    attr_value = self.parse_primary()
                elif attr_name == 'Direction':
                    # Direction values are INPUT, OUTPUT, INOUT keywords
                    if self.match(TokenType.INPUT):
                        attr_value = Identifier(name="Input", 
                                            line=self.current_token.line,
                                            column=self.current_token.column)
                        self.advance()
                    elif self.match(TokenType.OUTPUT):
                        attr_value = Identifier(name="Output",
                                            line=self.current_token.line,
                                            column=self.current_token.column)
                        self.advance()
                    elif self.match(TokenType.INOUT):
                        attr_value = Identifier(name="InOut",
                                            line=self.current_token.line,
                                            column=self.current_token.column)
                        self.advance()
                    else:
                        self.error("Expected Input, Output, or InOut for Direction")
                else:  # CanChange, CanBeNull, etc.
                    attr_value = self.parse_primary()
                
                attributes.append(Attribute(
                    key=attr_name,
                    value=attr_value,
                    line=attr_token.line,
                    column=attr_token.column
                ))
                
                # Check for comma (more attributes) or newline (end of entry)
                if self.match(TokenType.COMMA):
                    self.consume(TokenType.COMMA)
                    self.skip_newlines()
                else:
                    has_attributes = False
            
            entry = PoolEntry(
                key=key,
                attributes=attributes,
                line=start_token.line,
                column=start_token.column
            )
            body.append(entry)
            
            self.skip_newlines()
        
        self.consume(TokenType.RBRACE)
        
        return LinkagePoolDecl(
            name=pool_name,
            body=body,
            line=start_token.line,
            column=start_token.column
        )