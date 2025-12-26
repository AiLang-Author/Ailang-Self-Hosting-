# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

#parse_statements.py
"""Parser methods for handling statements - FIXED for consistent flow control"""

from typing import Optional
from ..lexer import TokenType
from ..ailang_ast import *


class ParserStatementsMixin:
    """Mixin for statement parsing methods"""
    
    def parse_statement(self) -> Optional[ASTNode]:
        """Parse statement - using your ORIGINAL version with updated else clause"""
        self.skip_newlines()
        if self.match(TokenType.COMMENT, TokenType.DOC_COMMENT, TokenType.COM_COMMENT, TokenType.TAG_COMMENT):
            self.advance()
            return None
        if self.match(TokenType.RUNTASK):
            return self.parse_runtask()
        elif self.match(TokenType.PRINTMESSAGE):
            return self.parse_printmessage()
        # Check for Debug statements
        elif self.current_token and hasattr(self.current_token, "value") and self.current_token.value == "Debug":
            return self.parse_debug_block()
        elif self.current_token and hasattr(self.current_token, "value") and self.current_token.value == "DebugAssert":
            return self.parse_debug_assert()
        elif self.match(TokenType.DEBUGPERF):
            return self.parse_debug_perf()    
        elif self.match(TokenType.RETURNVALUE):
            return self.parse_returnvalue()
        elif self.match(TokenType.IFCONDITION):
            return self.parse_if()
        elif self.match(TokenType.WHILELOOP):
            return self.parse_while()
        elif self.match(TokenType.FOREVERY):
            return self.parse_forevery()
        elif self.match(TokenType.FORK):
            return self.parse_fork()
        elif self.match(TokenType.BRANCH):
            return self.parse_branch()
        elif self.match(TokenType.TRYBLOCK):
            return self.parse_try()
        elif self.match(TokenType.SENDMESSAGE):
            return self.parse_sendmessage()
        elif self.match(TokenType.RECEIVEMESSAGE):
            return self.parse_receivemessage()
        elif self.match(TokenType.EVERYINTERVAL):
            return self.parse_everyinterval()
        elif self.match(TokenType.WITHSECURITY):
            return self.parse_withsecurity()
        elif self.match(TokenType.BREAKLOOP):
            self.advance()
            return BreakLoop(line=self.current_token.line, column=self.current_token.column)
        elif self.match(TokenType.CONTINUELOOP):
            self.advance()
            return ContinueLoop(line=self.current_token.line, column=self.current_token.column)
        elif self.match(TokenType.HALTPROGRAM):
            return self.parse_haltprogram()
        # === NEW: Low-Level Statement Parsing ===
        elif self.match(TokenType.ENABLEINTERRUPTS):
            return self.parse_interrupt_control()
        elif self.match(TokenType.DISABLEINTERRUPTS):
            return self.parse_interrupt_control()
        elif self.match(TokenType.INLINEASSEMBLY):
            return self.parse_inline_assembly()
        # === NEW: Virtual Memory Statement Parsing ===
        elif self.match(TokenType.PAGETABLE, TokenType.VIRTUALMEMORY, TokenType.CACHE, 
                    TokenType.TLB, TokenType.MEMORYBARRIER):
            return self.parse_vm_operation()
        else:
            # Safety check for tokens that shouldn't start statements
            if self.current_token and self.current_token.type in (
                TokenType.RBRACE, TokenType.ELSEBLOCK, TokenType.EOF,
                TokenType.CATCHERROR, TokenType.FINALLYBLOCK):
                return None
            
            # UPDATED: Use postfix parser for left-hand side
            expr = self.parse_postfix_expression()
            
            # If the next token is '=', it's an assignment
            if self.match(TokenType.EQUALS):
                # Handle both simple identifiers and member access
                if isinstance(expr, Identifier):
                    # Simple assignment - keep as string for compatibility
                    self.consume(TokenType.EQUALS)
                    value = self.parse_expression()
                    return Assignment(
                        target=expr.name,  # String for compatibility
                        value=value,
                        line=expr.line,
                        column=expr.column
                    )
                elif isinstance(expr, MemberAccess):
                    # Member assignment - convert to dotted string for compatibility
                    self.consume(TokenType.EQUALS)
                    value = self.parse_expression()
                    
                    # Build dotted name from MemberAccess
                    dotted_name = self.build_dotted_name(expr)
                    
                    return Assignment(
                        target=dotted_name,  # String for compatibility
                        value=value,
                        line=expr.line,
                        column=expr.column
                    )
                else:
                    self.error(f"Invalid assignment target. Cannot assign to a {type(expr).__name__}.")
            
            # Otherwise, it's just an expression statement
            if expr:
                return expr
            
            # If parsing an expression returned nothing and we're not at EOF,
            # advance to avoid getting stuck
            if self.current_token and self.current_token.type != TokenType.EOF:
                self.advance()
            
            return None
        
    # Add this helper method to the class:
    def build_dotted_name(self, node: ASTNode) -> str:
        """
        Convert MemberAccess chain to dotted string for backward compatibility.
        Add this method to the StatementParserMixin class.
        """
        if isinstance(node, Identifier):
            return node.name
        elif isinstance(node, MemberAccess):
            base = self.build_dotted_name(node.obj)
            if isinstance(node.member, Identifier):
                member_name = node.member.name
            else:
                member_name = str(node.member)
            return f"{base}.{member_name}"
        else:
            # Fallback for unexpected node types
            return str(node)  
        

    def parse_runtask(self) -> RunTask:
        """Parse RunTask with function call syntax for consistency"""
        start_token = self.consume(TokenType.RUNTASK)
        self.consume(TokenType.LPAREN)  # Change from DOT to LPAREN
        
        # Get task name as string literal
        if self.match(TokenType.IDENTIFIER):
            task_name = self.consume(TokenType.IDENTIFIER).value
        else:
            self.error("RunTask requires a task name (identifier)")
        
        # No additional arguments for now - just close paren
        self.consume(TokenType.RPAREN)
        
        return RunTask(
            task_name=task_name, 
            arguments=[],
            line=start_token.line, 
            column=start_token.column
        )

    def parse_printmessage(self) -> PrintMessage:
        start_token = self.consume(TokenType.PRINTMESSAGE)
        self.consume(TokenType.LPAREN)
        message = self.parse_expression()
        self.consume(TokenType.RPAREN)
        return PrintMessage(message=message, line=start_token.line, column=start_token.column)

    def parse_returnvalue(self) -> ReturnValue:
        start_token = self.consume(TokenType.RETURNVALUE)
        self.consume(TokenType.LPAREN)
        value = self.parse_expression()
        self.consume(TokenType.RPAREN)
        return ReturnValue(value=value, line=start_token.line, column=start_token.column)

    def parse_if(self) -> If:
        """
        FIXED: Parse IfCondition with flat, consistent syntax:
        IfCondition condition ThenBlock: { ... } ElseBlock: { ... }
        """
        start_token = self.consume(TokenType.IFCONDITION)
        condition = self.parse_expression()
        self.skip_newlines()
        
        # Direct ThenBlock syntax - no extra wrapper brace
        self.consume(TokenType.THENBLOCK)
        self.consume(TokenType.COLON)
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        
        self.push_context("IfCondition.ThenBlock")
        then_body = []
        while not self.match(TokenType.RBRACE):
            stmt = self.parse_statement()
            if stmt:
                then_body.append(stmt)
            self.skip_newlines()
        self.consume(TokenType.RBRACE)  # Close ThenBlock
        self.pop_context()
        self.skip_newlines()
        
        # Optional ElseBlock at same level
        else_body = None
        if self.match(TokenType.ELSEBLOCK):
            self.consume(TokenType.ELSEBLOCK)
            self.consume(TokenType.COLON)
            self.consume(TokenType.LBRACE)
            self.skip_newlines()
            
            self.push_context("IfCondition.ElseBlock")
            else_body = []
            while not self.match(TokenType.RBRACE):
                stmt = self.parse_statement()
                if stmt:
                    else_body.append(stmt)
                self.skip_newlines()
            self.consume(TokenType.RBRACE)  # Close ElseBlock
            self.pop_context()
        
        # NO extra closing brace - the structure is flat!
        return If(condition=condition, then_body=then_body, else_body=else_body,
                line=start_token.line, column=start_token.column)

    
    def parse_while(self) -> While:
        """
        FIXED: Parse WhileLoop with simple, consistent syntax:
        WhileLoop condition { ... }
        
        No Body: wrapper - just the statements directly
        """
        start_token = self.consume(TokenType.WHILELOOP)
        condition = self.parse_expression()
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        
        self.push_context("WhileLoop")
        body = []
        while not self.match(TokenType.RBRACE):
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            self.skip_newlines()
        self.consume(TokenType.RBRACE)
        self.pop_context()
        
        return While(condition=condition, body=body,
                    line=start_token.line, column=start_token.column)

    def parse_forevery(self) -> ForEvery:
        """
        ForEvery with consistent syntax:
        ForEvery variable in collection { ... }
        """
        start_token = self.consume(TokenType.FOREVERY)
        variable = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.IN)
        collection = self.parse_expression()
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        self.push_context(f"ForEvery({variable})")
        body = []
        while not self.match(TokenType.RBRACE):
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            self.skip_newlines()
        self.consume(TokenType.RBRACE)
        self.pop_context()
        return ForEvery(variable=variable, collection=collection, body=body,
                        line=start_token.line, column=start_token.column)

    def parse_fork(self) -> Fork:
        """
        FIXED Fork construct with consistent syntax:
        Fork condition TrueBlock: { ... } FalseBlock: { ... }
        """
        start_token = self.consume(TokenType.FORK)
        condition = self.parse_expression()
        self.skip_newlines()
        
        # TrueBlock
        self.consume(TokenType.TRUEBLOCK)
        self.consume(TokenType.COLON)
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        
        self.push_context("Fork.TrueBlock")
        true_block = []
        while not self.match(TokenType.RBRACE):
            stmt = self.parse_statement()
            if stmt:
                true_block.append(stmt)
            self.skip_newlines()
        self.consume(TokenType.RBRACE)
        self.pop_context()
        self.skip_newlines()
        
        # FalseBlock
        self.consume(TokenType.FALSEBLOCK)
        self.consume(TokenType.COLON)
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        
        self.push_context("Fork.FalseBlock")
        false_block = []
        while not self.match(TokenType.RBRACE):
            stmt = self.parse_statement()
            if stmt:
                false_block.append(stmt)
            self.skip_newlines()
        self.consume(TokenType.RBRACE)
        self.pop_context()
        
        return Fork(condition=condition, true_block=true_block, false_block=false_block,
                    line=start_token.line, column=start_token.column)

    def parse_branch(self) -> Branch:
        """
        Branch with consistent syntax:
        Branch expression { Case value: { ... } Default: { ... } }
        """
        start_token = self.consume(TokenType.BRANCH)
        expression = self.parse_expression()
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        
        self.push_context("Branch")
        cases = []
        default = None
        
        while not self.match(TokenType.RBRACE):
            self.skip_newlines()
            
            if self.match(TokenType.CASE):
                self.consume(TokenType.CASE)
                
                # Parse case value
                if self.match(TokenType.NUMBER):
                    case_value = Number(value=self.current_token.value, 
                                    line=self.current_token.line, 
                                    column=self.current_token.column)
                    self.advance()
                elif self.match(TokenType.STRING):
                    case_value = String(value=self.current_token.value,
                                    line=self.current_token.line,
                                    column=self.current_token.column)
                    self.advance()
                elif self.match(TokenType.IDENTIFIER):
                    case_value = Identifier(name=self.current_token.value,
                                        line=self.current_token.line,
                                        column=self.current_token.column)
                    self.advance()
                else:
                    self.error("Case value must be a number, string, or identifier")
                
                self.consume(TokenType.COLON)
                self.skip_newlines()
                self.consume(TokenType.LBRACE)
                self.skip_newlines()
                
                self.push_context(f"Branch.Case({case_value})")
                case_body = []
                while not self.match(TokenType.RBRACE):
                    stmt = self.parse_statement()
                    if stmt:
                        case_body.append(stmt)
                    self.skip_newlines()
                self.consume(TokenType.RBRACE)
                self.pop_context()
                
                cases.append((case_value, case_body))
                
            elif self.match(TokenType.DEFAULT):
                self.consume(TokenType.DEFAULT)
                self.consume(TokenType.COLON)
                self.skip_newlines()
                self.consume(TokenType.LBRACE)
                self.skip_newlines()
                
                self.push_context("Branch.Default")
                default = []
                while not self.match(TokenType.RBRACE):
                    stmt = self.parse_statement()
                    if stmt:
                        default.append(stmt)
                    self.skip_newlines()
                self.consume(TokenType.RBRACE)
                self.pop_context()
            
            else:
                self.skip_newlines()
                if not self.match(TokenType.RBRACE):
                    self.error(f"Expected Case or Default in Branch, got {self.current_token.type.name if self.current_token else 'EOF'}")
        
        self.consume(TokenType.RBRACE)
        self.pop_context()
        
        return Branch(expression=expression, cases=cases, default=default,
                    line=start_token.line, column=start_token.column)

    def parse_try(self) -> Try:
        """
        TryBlock with consistent syntax
        """
        start_token = self.consume(TokenType.TRYBLOCK)
        self.consume(TokenType.COLON)
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        self.push_context("TryBlock")
        body = []
        while not self.match(TokenType.RBRACE):
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            self.skip_newlines()
        self.consume(TokenType.RBRACE)
        self.pop_context()
        self.skip_newlines()
        catch_clauses = []
        while self.match(TokenType.CATCHERROR):
            self.consume(TokenType.CATCHERROR)
            self.consume(TokenType.COLON)

            # Allow generic CatchError: {} as well as typed CatchError: Type {}
            error_type = None
            if not self.match(TokenType.LBRACE):
                error_type = self.parse_type()
            else:
                # For a generic catch, we can use a placeholder or a special "Any" type.
                from ..ailang_ast import TypeExpression
                error_type = TypeExpression(base_type="Any", line=self.current_token.line, column=self.current_token.column)

            self.skip_newlines()
            self.consume(TokenType.LBRACE)
            self.skip_newlines()
            self.push_context(f"CatchError.{error_type}")
            catch_body = []
            while not self.match(TokenType.RBRACE):
                stmt = self.parse_statement()
                if stmt:
                    catch_body.append(stmt)
                self.skip_newlines()
            self.consume(TokenType.RBRACE)
            self.pop_context()
            self.skip_newlines()
            catch_clauses.append((error_type, catch_body))
        finally_body = None
        if self.match(TokenType.FINALLYBLOCK):
            self.consume(TokenType.FINALLYBLOCK)
            self.consume(TokenType.COLON)
            self.skip_newlines()
            self.consume(TokenType.LBRACE)
            self.skip_newlines()
            self.push_context("FinallyBlock")
            finally_body = []
            while not self.match(TokenType.RBRACE):
                stmt = self.parse_statement()
                if stmt:
                    finally_body.append(stmt)
                self.skip_newlines()
            self.consume(TokenType.RBRACE)
            self.pop_context()
        return Try(body=body, catch_clauses=catch_clauses, finally_body=finally_body,
                  line=start_token.line, column=start_token.column)

    def parse_sendmessage(self) -> SendMessage:
        """
        Parse SendMessage with arrow syntax for parameters
        SendMessage.Target(param=>value, param2=>value2)
        """
        start_token = self.consume(TokenType.SENDMESSAGE)
        self.consume(TokenType.DOT)
        target = self.consume(TokenType.IDENTIFIER).value
        parameters = {}
        
        if self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            self.skip_newlines()
            
            while not self.match(TokenType.RPAREN):
                self.skip_newlines()
                if self.match(TokenType.RPAREN):
                    break
                    
                # Parse parameter name
                param_name = self.consume(TokenType.IDENTIFIER).value
                
                # Change from DASH to => arrow (EQUALS followed by GREATER_SIGN)
                self.consume(TokenType.EQUALS, "Expected '=>' after parameter name")
                self.consume(TokenType.GREATER_SIGN, "Expected '=>' after parameter name")
                
                # Parse parameter value
                param_value = self.parse_expression()
                parameters[param_name] = param_value
                
                if self.match(TokenType.COMMA):
                    self.consume(TokenType.COMMA)
                self.skip_newlines()
                
            self.consume(TokenType.RPAREN)
            
        return SendMessage(
            target=target, 
            parameters=parameters,
            line=start_token.line, 
            column=start_token.column
        )

    def parse_receivemessage(self) -> ReceiveMessage:
        """
        Parse ReceiveMessage with optional parameters for filtering
        ReceiveMessage.MessageType { body }
        or
        ReceiveMessage.MessageType(filter=>value) { body }
        """
        start_token = self.consume(TokenType.RECEIVEMESSAGE)
        self.consume(TokenType.DOT)
        message_type = self.consume(TokenType.IDENTIFIER).value
        
        # Optional parameters for message filtering (future enhancement)
        parameters = {}
        if self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            self.skip_newlines()
            
            while not self.match(TokenType.RPAREN):
                self.skip_newlines()
                if self.match(TokenType.RPAREN):
                    break
                    
                # Parse parameter name
                param_name = self.consume(TokenType.IDENTIFIER).value
                
                # Use => arrow for consistency (EQUALS followed by GREATER_SIGN)
                self.consume(TokenType.EQUALS, "Expected '=>' after parameter name")
                self.consume(TokenType.GREATER_SIGN, "Expected '=>' after parameter name")
                
                # Parse parameter value
                param_value = self.parse_expression()
                parameters[param_name] = param_value
                
                if self.match(TokenType.COMMA):
                    self.consume(TokenType.COMMA)
                self.skip_newlines()
                
            self.consume(TokenType.RPAREN)
        
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        self.push_context(f"ReceiveMessage.{message_type}")
        
        body = []
        while not self.match(TokenType.RBRACE):
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            self.skip_newlines()
            
        self.consume(TokenType.RBRACE)
        self.pop_context()
        
        # Note: ReceiveMessage AST node needs to be updated to include parameters field
        # For now, we'll just pass the standard fields
        return ReceiveMessage(
            message_type=message_type, 
            body=body,
            line=start_token.line, 
            column=start_token.column
        )

    def parse_everyinterval(self) -> EveryInterval:
        start_token = self.consume(TokenType.EVERYINTERVAL)
        interval_type = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.DASH)
        interval_value = self.consume(TokenType.NUMBER).value
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        self.push_context(f"EveryInterval({interval_type}-{interval_value})")
        body = []
        while not self.match(TokenType.RBRACE):
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            self.skip_newlines()
        self.consume(TokenType.RBRACE)
        self.pop_context()
        return EveryInterval(interval_type=interval_type, interval_value=interval_value,
                           body=body, line=start_token.line, column=start_token.column)

    def parse_withsecurity(self) -> WithSecurity:
        start_token = self.consume(TokenType.WITHSECURITY)
        self.consume(TokenType.LPAREN)
        self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.DASH)
        context = self.consume(TokenType.STRING).value
        self.consume(TokenType.RPAREN)
        self.skip_newlines()
        self.consume(TokenType.LBRACE)
        self.skip_newlines()
        self.push_context(f"WithSecurity({context})")
        body = []
        while not self.match(TokenType.RBRACE):
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            self.skip_newlines()
        self.consume(TokenType.RBRACE)
        self.pop_context()
        return WithSecurity(context=context, body=body,
                          line=start_token.line, column=start_token.column)

    def parse_haltprogram(self) -> HaltProgram:
        start_token = self.consume(TokenType.HALTPROGRAM)
        message = None
        if self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            if self.match(TokenType.STRING):
                message = self.consume(TokenType.STRING).value
            self.consume(TokenType.RPAREN)
        return HaltProgram(message=message, line=start_token.line, column=start_token.column)