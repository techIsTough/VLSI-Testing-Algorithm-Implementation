from models import Circuit, GateType, Fault

# Runs a full circuit simulation with the convenient option to go straight to fault simulation
def simulate(circuit, primaryInputValues, fault=None):
    wireValues = {}
    
    # Initialize primary inputs
    for inputName in circuit.primaryInputs:
        value = int(primaryInputValues.get(inputName, 0))
        
        # If there's a fault on a primary input, force the stuck-at value
        if fault and inputName == fault.wireName:
            value = fault.stuckAtValue
        wireValues[inputName] = value

    # Evaluate gates in topological order
    for gate in circuit.sortedGates:
        gateInputValues = [wireValues[wire] for wire in gate.inputWires]
        gateOutputValue = evaluateGateLogic(gate.gateType, gateInputValues)
        
        # If there's a fault on this gate's output, force the stuck-at value
        if fault and gate.outputWire == fault.wireName:
            gateOutputValue = fault.stuckAtValue
        
        wireValues[gate.outputWire] = gateOutputValue

    # Return only the values of the primary outputs
    return {outputName: wireValues[outputName] for outputName in circuit.primaryOutputs}

# Simulates a list of faults to see which ones affect the output
def getDetectedFaults(circuit, inputVector, faultList):
    detected = []
    # Evaluate the correct output from the good circuit
    goodOutput = simulate(circuit, inputVector, fault=None)
    
    for fault in faultList:
        # Simulate with the fault
        faultyOutput = simulate(circuit, inputVector, fault=fault)
        
        # If the output is different from the good circuit, the fault is detected
        if faultyOutput != goodOutput:
            detected.append(fault)
            
    return detected

# Calculates the binary output for a specific gate based on its inputs an the concept of controlling values
def evaluateGateLogic(gateType, inputValues):
    if gateType == GateType.AND:
        # If there's a 0, the output is 0
        for v in inputValues:
            if v == 0:
                return 0
        return 1

    if gateType == GateType.NAND:
        # If there's a 0, the output is 1
        for v in inputValues:
            if v == 0:
                return 1
        return 0

    if gateType == GateType.OR:
        # If there's a 1, the output is 1
        for v in inputValues:
            if v == 1:
                return 1
        return 0

    if gateType == GateType.NOR:
        # If there's a 1, the output is 0
        for v in inputValues:
            if v == 1:
                return 0
        return 1

    if gateType == GateType.NOT:
        return 1 - inputValues[0]
    
    # For fanout branches, just pass the value through
    if gateType == GateType.BRANCH:
        return inputValues[0]
    
    raise ValueError(f"Unsupported gate type: {gateType}")