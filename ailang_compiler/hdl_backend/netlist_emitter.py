# ailang_compiler/netlist_emitter.py
class NetlistEmitter:
    def __init__(self):
        self.gates = []
        self.wires = []
        self.regs = []
        self.label_map = {}  # label -> gate ID
        self.wire_counter = 0
        self.gate_counter = 0

    def add_gate(self, gate_type, inputs, output):
        gate_id = f"G{self.gate_counter}"
        self.gates.append({
            'id': gate_id,
            'type': gate_type,
            'inputs': inputs,
            'output': output
        })
        self.gate_counter += 1
        return gate_id

    def add_wire(self, from_id, to_id):
        wire_id = f"W{self.wire_counter}"
        self.wires.append({
            'id': wire_id,
            'from': from_id,
            'to': to_id
        })
        self.wire_counter += 1
        return wire_id

    def add_reg(self, name, init_value=0):
        reg_id = f"R_{name}"
        self.regs.append({
            'id': reg_id,
            'init': init_value
        })
        return reg_id

    def add_label(self, name):
        label_gate = self.add_gate('LABEL', [], name)  # Placeholder for jumps
        self.label_map[name] = label_gate

    def emit_netlist_json(self):
        return {
            'gates': self.gates,
            'wires': self.wires,
            'regs': self.regs
        }

# In ailang_compiler.py __init__:
self.mode = mode  # e.g., 'x86' or 'netlist'
if self.mode == 'netlist':
    self.netlist = NetlistEmitter()
else:
    self.asm = X64Assembler(self.elf)

# Example in arithmetic_ops.py Add method:
if self.compiler.mode == 'netlist':
    output_wire = self.compiler.netlist.add_wire(input1, input2)  # Simplified
    self.compiler.netlist.add_gate('ADD', [input1, input2], output_reg)
else:
    # Original asm code

# In compile():
if self.mode == 'netlist':
    netlist = self.netlist.emit_netlist_json()
    # Dump to file or return
    return netlist
else:
    # Original ELF gen
    
    # ailang_compiler/netlist_emitter.py (Expanded with WhileLoop/FSM support)

class NetlistEmitter:
    def __init__(self):
        self.gates = []
        self.wires = []
        self.regs = []
        self.label_map = {}  # label -> gate ID
        self.wire_counter = 0
        self.gate_counter = 0
        self.fsm_counter = 0  # For loops/FSMs

    def add_gate(self, gate_type, inputs, output):
        gate_id = f"G{self.gate_counter}"
        self.gates.append({
            'id': gate_id,
            'type': gate_type,
            'inputs': inputs,
            'output': output
        })
        self.gate_counter += 1
        return gate_id

    def add_wire(self, from_id, to_id):
        wire_id = f"W{self.wire_counter}"
        self.wires.append({
            'id': wire_id,
            'from': from_id,
            'to': to_id
        })
        self.wire_counter += 1
        return wire_id

    def add_reg(self, name, init_value=0):
        reg_id = f"R_{name}"
        self.regs.append({
            'id': reg_id,
            'init': init_value
        })
        return reg_id

    def add_label(self, name):
        label_gate = self.add_gate('LABEL', [], name)  # Placeholder for jumps
        self.label_map[name] = label_gate

    def add_fsm(self, cond_inputs, body_gates, counter_init=0):
        fsm_id = f"FSM_{self.fsm_counter}"
        counter_reg = self.add_reg(f"{fsm_id}_counter", counter_init)
        
        # CMP for loop condition
        cond_gate = self.add_gate('CMP', cond_inputs, f"{fsm_id}_cond")
        
        # MUX for continue/exit (jump logic)
        mux_gate = self.add_gate('MUX', [f"{fsm_id}_cond", 'continue_path', 'exit_path'], f"{fsm_id}_next")
        
        # Add body gates (e.g., ADD/MUL from loop body)
        body_outputs = []
        for gate in body_gates:
            gate_id = self.add_gate(gate['type'], gate['inputs'], gate['output'])
            body_outputs.append(gate['output'])
        
        # Feedback wire: MUX out to counter (for iteration)
        self.add_wire(mux_gate, counter_reg)
        
        # Optional: Wire body out back to cond for stateful loops
        if body_outputs:
            self.add_wire(body_outputs[-1], cond_gate)  # Last body out to cond input
        
        self.fsm_counter += 1
        return fsm_id

    def emit_netlist_json(self):
        return {
            'gates': self.gates,
            'wires': self.wires,
            'regs': self.regs
        }

# In ailang_compiler.py AiLang.AllocateGates (updated for WhileLoop)
def AiLang_AllocateGates(ops):
    gates = []
    for op in ops:
        if op['type'] == 'WHILELOOP':
            # Decompose to FSM
            cond_inputs = op.get('cond_inputs', ['var_i', 'const_10'])  # From AST cond, e.g., LessThan(i, 10)
            body_gates = op.get('body_gates', [  # From loop body AST
                {'type': 'ADD', 'inputs': ['var_a', 'var_b'], 'output': 'var_c'}
            ])
            fsm = netlist.add_fsm(cond_inputs, body_gates)
            gates.append({'type': 'FSM', 'id': fsm})
        # Other cases (e.g., ADD -> add_gate('ADD', ...))
        elif op['type'] == 'OPERATION':
            # Example
            gates.append({'type': 'ADD', 'id': netlist.add_gate('ADD', op['inputs'], op['output'])})
    return gates

# Sample test (integrates with your harnesses)
netlist = NetlistEmitter()
ops = [{'type': 'WHILELOOP', 'cond_inputs': ['i', '10'], 'body_gates': [{'type': 'ADD', 'inputs': ['a', 'b'], 'output': 'c'}]}]
gates = AiLang_AllocateGates(ops)
json_netlist = netlist.emit_netlist_json()
print(json_netlist)