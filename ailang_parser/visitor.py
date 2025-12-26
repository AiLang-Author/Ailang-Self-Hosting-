# Copyright (c) 2025 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
#
# Licensed under the Sean Collins Software License (SCSL). See the LICENSE file in the root directory of this project
# for the full terms and conditions, including restrictions on forking, corporate use, and permissions for private/teaching purposes.

# visitor.py
from ailang_ast import (
    ASTNode, Program, Library, Pool, ResourceItem, Loop, SubRoutine, Function, 
    RunTask, PrintMessage, ReturnValue, If, While, ForEvery, Assignment, 
    MathExpression, FunctionCall, Identifier, Number, String, Boolean,
    ArrayLiteral, TypeExpression, Try, SendMessage, ReceiveMessage,
    EveryInterval, WithSecurity, BreakLoop, ContinueLoop, HaltProgram, Lambda, 
    Combinator, MacroBlock, MacroDefinition, SecurityContext, SecurityLevel, 
    ConstrainedType, Constant, Apply, RunMacro, MapLiteral, SubPool, 
    AcronymDefinitions, RecordTypeDefinition, MemberAccess, Fork, Branch,
    # Low-level nodes
    InterruptHandler, DeviceDriver, Dereference, AddressOf, SizeOf, InterruptControl, SystemCall,
    SystemCall, InlineAssembly, BootloaderCode ,  KernelEntry 
)

class ASTVisitor:
    """Base class for AST visitors"""
    
    def visit(self, node: ASTNode):
        """Visit a node"""
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node: ASTNode):
        """Called if no explicit visitor method exists for a node"""
        raise NotImplementedError(f"No visitor method for {type(node).__name__}")
    
    def visit_MemberAccess(self, node: MemberAccess):
        """Default visitor for MemberAccess"""
        raise NotImplementedError("Subclass must implement visit_MemberAccess")

class ASTPrinter(ASTVisitor):
    """Pretty print AST for debugging"""
    
    def __init__(self, indent_size: int = 2):
        self.indent_size = indent_size
        self.indent_level = 0
    
    def visit_MemberAccess(self, node: MemberAccess) -> str:
        """Pretty print member access"""
        obj_str = self.visit(node.obj)
        if isinstance(node.member, Identifier):
            member_str = node.member.name
        else:
            member_str = self.visit(node.member)
        return f"{obj_str}.{member_str}"
    
    
    def indent(self) -> str:
        return ' ' * (self.indent_level * self.indent_size)
    
    def visit_Program(self, node: Program) -> str:
        result = "Program:\n"
        self.indent_level += 1
        for decl in node.declarations:
            result += self.indent() + self.visit(decl) + "\n"
        self.indent_level -= 1
        return result
    
    def visit_Library(self, node: Library) -> str:
        result = f"LibraryImport.{node.name}:\n"
        self.indent_level += 1
        for item in node.body:
            result += self.indent() + self.visit(item) + "\n"
        self.indent_level -= 1
        return result
    
    def visit_Pool(self, node: Pool) -> str:
        result = f"{node.pool_type}.{node.name}:\n"
        self.indent_level += 1
        for item in node.body:
            result += self.indent() + self.visit(item) + "\n"
        self.indent_level -= 1
        return result
    
    def visit_SubPool(self, node: SubPool) -> str:
        result = f"SubPool.{node.name}:\n"
        self.indent_level += 1
        for key, item in node.items.items():
            result += self.indent() + self.visit(item) + "\n"
        self.indent_level -= 1
        return result
    
    def visit_ResourceItem(self, node: ResourceItem) -> str:
        attrs = ', '.join(f"{k}-{self.visit(v)}" for k, v in node.attributes.items())
        value = self.visit(node.value) if node.value else "None"
        return f'"{node.key}": {value} {attrs}'
    
    def visit_Loop(self, node: Loop) -> str:
        result = f"{node.loop_type}.{node.name}:\n"
        self.indent_level += 1
        for stmt in node.body:
            result += self.indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        if node.end_name:
            result += self.indent() + f"LoopEnd.{node.end_name}\n"
        return result
    
    def visit_SubRoutine(self, node: SubRoutine) -> str:
        result = f"SubRoutine.{node.name}:\n"
        self.indent_level += 1
        for stmt in node.body:
            result += self.indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        return result
    
    def visit_Function(self, node: Function) -> str:
        params = ', '.join(f"{name}: {self.visit(type)}" for name, type in node.input_params)
        result = f"Function.{node.name}({params})"
        if node.output_type:
            result += f" -> {self.visit(node.output_type)}"
        result += ":\n"
        self.indent_level += 1
        for stmt in node.body:
            result += self.indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        return result
    
    def visit_Lambda(self, node: Lambda) -> str:
        params = ', '.join(node.params)
        return f"Lambda({params}) {{ {self.visit(node.body)} }}"
    
    def visit_Combinator(self, node: Combinator) -> str:
        return f"Combinator.{node.name} = {self.visit(node.definition)}"
    
    def visit_MacroBlock(self, node: MacroBlock) -> str:
        result = f"MacroBlock.{node.name}:\n"
        self.indent_level += 1
        for macro in node.macros.values():
            result += self.indent() + self.visit(macro) + "\n"
        self.indent_level -= 1
        return result
    
    def visit_MacroDefinition(self, node: MacroDefinition) -> str:
        params = ', '.join(node.params)
        return f"Macro.{node.name}({params}) = {self.visit(node.body)}"
    
    def visit_SecurityContext(self, node: SecurityContext) -> str:
        result = f"SecurityContext.{node.name}:\n"
        self.indent_level += 1
        for level in node.levels.values():
            result += self.indent() + self.visit(level) + "\n"
        self.indent_level -= 1
        return result
    
    def visit_SecurityLevel(self, node: SecurityLevel) -> str:
        result = f"Level.{node.name}:\n"
        self.indent_level += 1
        result += self.indent() + f"Allowed: {node.allowed_operations}\n"
        result += self.indent() + f"Denied: {node.denied_operations}\n"
        if node.memory_limit:
            result += self.indent() + f"MemoryLimit: {self.visit(node.memory_limit)}\n"
        if node.cpu_quota:
            result += self.indent() + f"CPUQuota: {self.visit(node.cpu_quota)}\n"
        self.indent_level -= 1
        return result
    
    def visit_ConstrainedType(self, node: ConstrainedType) -> str:
        return f"ConstrainedType.{node.name} = {self.visit(node.base_type)} Where {{ {self.visit(node.constraints)} }}"
    
    def visit_Constant(self, node: Constant) -> str:
        return f"Constant.{node.name} = {self.visit(node.value)}"
    
    def visit_RunTask(self, node: RunTask) -> str:
        args = ', '.join(f"{name}-{self.visit(value)}" for name, value in node.arguments)
        return f"RunTask.{node.task_name}({args})"
    
    def visit_PrintMessage(self, node: PrintMessage) -> str:
        return f"PrintMessage({self.visit(node.message)})"
    
    def visit_ReturnValue(self, node: ReturnValue) -> str:
        return f"ReturnValue({self.visit(node.value)})"
    
    def visit_If(self, node: If) -> str:
        result = f"IfCondition {self.visit(node.condition)} ThenBlock {{\n"
        self.indent_level += 1
        for stmt in node.then_body:
            result += self.indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        result += self.indent() + "}"
        if node.else_body:
            result += " ElseBlock {\n"
            self.indent_level += 1
            for stmt in node.else_body:
                result += self.indent() + self.visit(stmt) + "\n"
            self.indent_level -= 1
            result += self.indent() + "}"
        return result
        
    def visit_Fork(self, node: Fork) -> str:
        """Pretty print a Fork node."""
        result = f"Fork {self.visit(node.condition)} {{\n"
        
        # True block
        self.indent_level += 1
        for stmt in node.true_block:
            result += self.indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        
        result += self.indent() + "} {\n"
        
        # False block
        self.indent_level += 1
        for stmt in node.false_block:
            result += self.indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        
        result += self.indent() + "}"
        return result

    def visit_Branch(self, node: Branch) -> str:
        """Pretty print a Branch node."""
        result = f"Branch {self.visit(node.expression)} {{\n"
        self.indent_level += 1

        for case_value, case_body in node.cases:
            result += self.indent() + f"Case {self.visit(case_value)} {{\n"
            self.indent_level += 1
            for stmt in case_body:
                result += self.indent() + self.visit(stmt) + "\n"
            self.indent_level -= 1
            result += self.indent() + "}\n"

        if node.default:
            result += self.indent() + "Default {\n"
            self.indent_level += 1
            for stmt in node.default:
                result += self.indent() + self.visit(stmt) + "\n"
            self.indent_level -= 1
            result += self.indent() + "}\n"

        self.indent_level -= 1
        result += self.indent() + "}"
        return result

    def visit_While(self, node: While) -> str:
        result = f"WhileLoop {self.visit(node.condition)} {{\n"
        self.indent_level += 1
        for stmt in node.body:
            result += self.indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        result += self.indent() + "}"
        return result
    
    def visit_ForEvery(self, node: ForEvery) -> str:
        result = f"ForEvery {node.variable} in {self.visit(node.collection)} {{\n"
        self.indent_level += 1
        for stmt in node.body:
            result += self.indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        result += self.indent() + "}"
        return result
    
    def visit_Try(self, node: Try) -> str:
        result = "TryBlock:\n"
        self.indent_level += 1
        for stmt in node.body:
            result += self.indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        for error_type, catch_body in node.catch_clauses:
            result += self.indent() + f"CatchError.{self.visit(error_type)}:\n"
            self.indent_level += 1
            for stmt in catch_body:
                result += self.indent() + self.visit(stmt) + "\n"
            self.indent_level -= 1
        if node.finally_body:
            result += self.indent() + "FinallyBlock:\n"
            self.indent_level += 1
            for stmt in node.finally_body:
                result += self.indent() + self.visit(stmt) + "\n"
            self.indent_level -= 1
        return result
    
    def visit_SendMessage(self, node: SendMessage) -> str:
        params = ', '.join(f"{k}-{self.visit(v)}" for k, v in node.parameters.items())
        return f"SendMessage.{node.target}({params})"
    
    def visit_ReceiveMessage(self, node: ReceiveMessage) -> str:
        result = f"ReceiveMessage.{node.message_type} {{\n"
        self.indent_level += 1
        for stmt in node.body:
            result += self.indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        result += self.indent() + "}"
        return result
    
    def visit_EveryInterval(self, node: EveryInterval) -> str:
        result = f"EveryInterval {node.interval_type}-{node.interval_value} {{\n"
        self.indent_level += 1
        for stmt in node.body:
            result += self.indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        result += self.indent() + "}"
        return result
    
    def visit_WithSecurity(self, node: WithSecurity) -> str:
        result = f"WithSecurity({node.context}) {{\n"
        self.indent_level += 1
        for stmt in node.body:
            result += self.indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        result += self.indent() + "}"
        return result
    
    def visit_Assignment(self, node: Assignment) -> str:
        """Print assignment"""
        return f"{node.target} = {self.visit(node.value)}"  # target is still string
    
    def visit_BreakLoop(self, node: BreakLoop) -> str:
        return "BreakLoop"
    
    def visit_ContinueLoop(self, node: ContinueLoop) -> str:
        return "ContinueLoop"
    
    def visit_HaltProgram(self, node: HaltProgram) -> str:
        return f"HaltProgram({node.message or ''})"
    
    def visit_MathExpression(self, node: MathExpression) -> str:
        return f"({self.visit(node.expression)})"
    
    def visit_FunctionCall(self, node: FunctionCall) -> str:
        """Print function call - handles both old and new style"""
        if isinstance(node.function, str):
            # Old style - function is a string
            func_str = node.function
        else:
            # New style - function is an AST node
            func_str = self.visit(node.function)
        
        args = ', '.join(self.visit(arg) for arg in node.arguments)
        return f"{func_str}({args})"
    
    def visit_Apply(self, node: Apply) -> str:
        args = ', '.join(self.visit(arg) for arg in node.arguments)
        return f"Apply({self.visit(node.function)}, {args})"
    
    def visit_RunMacro(self, node: RunMacro) -> str:
        args = ', '.join(self.visit(arg) for arg in node.arguments)
        return f"RunMacro.{node.macro_path}({args})"
    
    def visit_Identifier(self, node: Identifier) -> str:
        return node.name
    
    def visit_Number(self, node: Number) -> str:
        return str(node.value)
    
    def visit_String(self, node: String) -> str:
        return f'"{node.value}"'
    
    def visit_Boolean(self, node: Boolean) -> str:
        return 'True' if node.value else 'False'
    
    def visit_ArrayLiteral(self, node: ArrayLiteral) -> str:
        elements = ', '.join(self.visit(elem) for elem in node.elements)
        return f"[{elements}]"
    
    def visit_MapLiteral(self, node: MapLiteral) -> str:
        pairs = ', '.join(f"{self.visit(k)}: {self.visit(v)}" for k, v in node.pairs)
        return f"{{{pairs}}}"
    
    def visit_TypeExpression(self, node: TypeExpression) -> str:
        if node.parameters:
            params = ', '.join(self.visit(p) for p in node.parameters)
            return f"{node.base_type}[{params}]"
        return node.base_type
        
    def visit_AcronymDefinitions(self, node: AcronymDefinitions) -> str:
        """Pretty print acronym definitions"""
        result = "AcronymDefinitions {\n"
        self.indent_level += 1
        
        for acronym, full_name in node.definitions.items():
            result += self.indent() + f"{acronym} = {full_name}\n"
        
        self.indent_level -= 1
        result += self.indent() + "}"
        return result

    def visit_RecordTypeDefinition(self, node) -> str:
        return f"{node.name} = {self.visit(node.record_type)}"

    # --- Low-Level Node Visitors ---

    def visit_InterruptHandler(self, node: InterruptHandler) -> str:
        """Pretty print an InterruptHandler node."""
        vector_str = self.visit(node.vector)
        result = f"InterruptHandler.{node.handler_name}(vector={vector_str}) {{\n"
        self.indent_level += 1
        for stmt in node.body:
            result += self.indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        result += self.indent() + "}"
        return result
    
    def visit_DeviceDriver(self, node: DeviceDriver) -> str:
        """Pretty print a DeviceDriver node."""
        result = f"DeviceDriver.{node.driver_name}: {node.device_type} {{\n"
        self.indent_level += 1
        for op_name, op_node in node.operations.items():
            result += self.indent() + f"{op_name}: {self.visit(op_node)}\n"
        self.indent_level -= 1
        result += self.indent() + "}"
        return result
    
    def visit_Dereference(self, node: Dereference) -> str:
        """Pretty print a Dereference node."""
        size_hint = f", hint={node.size_hint}" if node.size_hint else ""
        return f"Dereference(*{self.visit(node.pointer)}{size_hint})"

    def visit_AddressOf(self, node: AddressOf) -> str:
        """Pretty print an AddressOf node."""
        return f"AddressOf(&{self.visit(node.variable)})"

    def visit_SizeOf(self, node: SizeOf) -> str:
        """Pretty print a SizeOf node."""
        return f"SizeOf({self.visit(node.target)})"

    def visit_InterruptControl(self, node: InterruptControl) -> str:
        """Pretty print an InterruptControl node."""
        # The operation is 'enable' or 'disable', so we can make the output match the keyword
        return "EnableInterrupts" if node.operation == "enable" else "DisableInterrupts"

    def visit_SystemCall(self, node: SystemCall) -> str:
        """Pretty print a SystemCall node."""
        call_num_str = self.visit(node.call_number)
        args_str = ', '.join(self.visit(arg) for arg in node.arguments)
        return f"SystemCall({call_num_str}, args=[{args_str}])"
    
    def visit_InlineAssembly(self, node: InlineAssembly) -> str:
        """Pretty print an InlineAssembly node."""
        parts = [f'"{node.assembly_code}"']
        
        if node.inputs:
            inputs_str = ', '.join(f'"{constraint}": {self.visit(val)}' for constraint, val in node.inputs)
            parts.append(f"inputs: [{inputs_str}]")
            
        if node.outputs:
            outputs_str = ', '.join(f'"{constraint}": {self.visit(val)}' for constraint, val in node.outputs)
            parts.append(f"outputs: [{outputs_str}]")

        if node.clobbers:
            clobbers_str = ', '.join(f'"{c}"' for c in node.clobbers)
            parts.append(f"clobbers: [{clobbers_str}]")
            
        if node.volatile:
            parts.append("volatile: True")

        return f"InlineAssembly({', '.join(parts)})"
    
    def visit_BootloaderCode(self, node: BootloaderCode) -> str:
        """Pretty print a BootloaderCode node."""
        result = f"BootloaderCode.{node.stage} {{\n"
        self.indent_level += 1
        for stmt in node.body:
            result += self.indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        result += self.indent() + "}"
        return result
    
    def visit_KernelEntry(self, node: KernelEntry) -> str:
        """Pretty print a KernelEntry node."""
        params_str = ', '.join(f"{name}: {self.visit(ptype)}" for name, ptype in node.parameters)
        result = f"KernelEntry.{node.entry_name}({params_str}) {{\n"
        self.indent_level += 1
        for stmt in node.body:
            result += self.indent() + self.visit(stmt) + "\n"
        self.indent_level -= 1
        result += self.indent() + "}"
        return result