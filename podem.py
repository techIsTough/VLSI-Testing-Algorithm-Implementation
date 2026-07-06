from models import Circuit, GateType, Fault

# Constants for 5 value logic
VAL_X = "X"      # Unknown
VAL_D = "D"      # good: 1, faulty: 0
VAL_DB = "DBar"  # good: 0, faulty: 1

# Starting point for generating a test vector using PODEM
def generateTestVector(circuit, fault):
    wireAssignments = initializeAssignments(circuit)
    
    # Try to find a test vector recursively
    if PODEM(circuit, fault, wireAssignments):
        # Convert the symbolic assignments to a binary test vector
        testVector = {}
        for primaryInput in circuit.primaryInputs:
            logicSymbol = wireAssignments[primaryInput]
            
            # Convert D/DBar to binary 1/0 and treat X as 0
            if logicSymbol in (VAL_D, VAL_DB): 
                logicSymbol = "1" if logicSymbol == VAL_D else "0"
            if logicSymbol == VAL_X: 
                logicSymbol = "0"
            
            testVector[primaryInput] = int(logicSymbol)
        return testVector
    return None

# Main recursive function that implements PODEM
def PODEM(circuit, fault, wireAssignments):
    # Check if the fault has successfully propagated to a primary output
    if checkErrorAtPO(circuit, wireAssignments):
        return True

    # Check if the D-frontier is empty meaning the fault cannot be propagated further
    if isTestImpossible(circuit, fault, wireAssignments):
        return False

    # Determine the next logic assignment needed to activate or propagate the fault
    objectiveWire, objectiveValue = getObjective(circuit, fault, wireAssignments)
    
    # If no objective can be found, the path is blocked so backtrack
    if objectiveWire is None:
        return False

    # Trace back from the objective line to a primary input
    primaryInput, piValue = performBacktrace(circuit, objectiveWire, objectiveValue, wireAssignments)
    
    # If backtrace fails to find a controllable input, backtrack
    if primaryInput is None:
        return False

    # Save the current state of assignments before trying a new value
    savedState = wireAssignments.copy()

    # Try setting the primary input to the determined value
    wireAssignments[primaryInput] = piValue
    
    # Update logic values and check for success
    if performImplication(circuit, fault, wireAssignments):
        if PODEM(circuit, fault, wireAssignments):
            return True

    # If that didn't work, reverse the decision
    wireAssignments.clear()
    wireAssignments.update(savedState)
    
    reversedValue = invertBit(piValue)
    wireAssignments[primaryInput] = reversedValue
    
    # Update logic values with the opposite input and check for success
    if performImplication(circuit, fault, wireAssignments):
        if PODEM(circuit, fault, wireAssignments):
            return True

    # If neither value worked, restore state to X and return failure
    wireAssignments.clear()
    wireAssignments.update(savedState)
    wireAssignments[primaryInput] = VAL_X
    return False

# Determines the next objective for the algorithm, either activating the fault or pushing it through a gate
def getObjective(circuit, fault, wireAssignments):
    targetWire = fault.wireName
    stuckValue = fault.stuckAtValue
    currentWireValue = wireAssignments[targetWire]

    ## If the fault site is still X, we must try to set it to the opposite of the stuck value
    if currentWireValue == VAL_X:
        desiredValue = "1" if stuckValue == 0 else "0"
        return targetWire, desiredValue

    # Select a gate from the D-frontier
    dFrontierGates = getDFrontier(circuit, wireAssignments)
    
    for gate in dFrontierGates:
        # Find an input on this gate that's currently unknown
        for inputWire in gate.inputWires:
            if wireAssignments[inputWire] == VAL_X:
                # Set this input to the non-controlling value to let the fault pass
                controllingValue = getControllingValue(gate.gateType)
                nonControllingValue = invertBit(controllingValue)
                return inputWire, nonControllingValue
            
    return None, None

# Traces backwards from a specific objective wire to find a primary input to control
def performBacktrace(circuit, currentWire, desiredValue, wireAssignments):
    # Loop until reaching a primary input
    while currentWire not in circuit.primaryInputs:
        # Find the gate that drives the current wire
        drivingGate = None
        for gate in circuit.gateList:
            if gate.outputWire == currentWire:
                drivingGate = gate
                break
        
        if drivingGate is None: return None, None

        # If the gate is inverted, we need to invert the value we are looking for
        if isInvertingGate(drivingGate.gateType):
            desiredValue = invertBit(desiredValue)
            
        # Select an input of this gate that's currently X
        nextWire = None
        for inputWire in drivingGate.inputWires:
            if wireAssignments[inputWire] == VAL_X:
                nextWire = inputWire
                break
        
        # If no inputs are X, the path can't be controlled
        if nextWire is None:
            return None, None

        currentWire = nextWire

    return currentWire, desiredValue

# Updates the circuit states based on new assignments. Checks for conflicts and handles fault injection
def performImplication(circuit, fault, wireAssignments):
    # Handle faults on primary inputs explicitly since they aren't computed by gates
    if wireAssignments[fault.wireName] != VAL_X:
        currentAssignment = wireAssignments[fault.wireName]
        if fault.stuckAtValue == 0 and currentAssignment == "1":
            wireAssignments[fault.wireName] = VAL_D
        elif fault.stuckAtValue == 1 and currentAssignment == "0":
            wireAssignments[fault.wireName] = VAL_DB

    # Handle faults on internal gates and fanout branches
    while True:
        hasChanged = False
        for gate in circuit.sortedGates:
            
            # Calculate the normal output based on current inputs
            inputSymbols = [wireAssignments[w] for w in gate.inputWires]
            goodOutput = evaluateGateFiveValued(gate.gateType, inputSymbols)
            
            # Check if this gate is the fault site
            if gate.outputWire == fault.wireName:
                pair = convertSymbolToPair(goodOutput)
                goodMachineValue = pair[0]
                
                if goodMachineValue is not None:
                    finalValue = convertPairToSymbol(goodMachineValue, fault.stuckAtValue)
                else:
                    finalValue = VAL_X
            else:
                finalValue = goodOutput

            if finalValue == VAL_X: continue
            
            # Update the wire assignment if it's new or check for conflicts
            currentWireValue = wireAssignments[gate.outputWire]
            if currentWireValue == VAL_X:
                wireAssignments[gate.outputWire] = finalValue
                hasChanged = True
            elif checkConflict(currentWireValue, finalValue):
                return False 
                
        if not hasChanged: return True

# Returns true if the fault value has reached a primary output
def checkErrorAtPO(circuit, wireAssignments):
    for primaryOutput in circuit.primaryOutputs:
        if wireAssignments[primaryOutput] in (VAL_D, VAL_DB):
            return True
    return False

# Determines if the search should stop because the fault can no longer be propagated
def isTestImpossible(circuit, fault, wireAssignments):
    faultStatus = wireAssignments[fault.wireName]
    isFaultActivated = (faultStatus == VAL_D or faultStatus == VAL_DB)
    
    # If the fault is active but there are no gates ready to propagate it because the D-Frontier is empty
    if isFaultActivated:
        dFrontier = getDFrontier(circuit, wireAssignments)
        if not dFrontier:
            return True
    return False

# Identifies gates where the fault is ready to be propagated
def getDFrontier(circuit, wireAssignments):
    frontierGates = []
    for gate in circuit.gateList:
        if wireAssignments[gate.outputWire] == VAL_X:
            hasFaultInput = False
            for inputWire in gate.inputWires:
                if wireAssignments[inputWire] in (VAL_D, VAL_DB):
                    hasFaultInput = True
                    break
            if hasFaultInput:
                frontierGates.append(gate)
    return frontierGates

# Returns the value that forces a gate's output to a certain state
def getControllingValue(gateType):
    if gateType in (GateType.AND, GateType.NAND): return "0"
    if gateType in (GateType.OR, GateType.NOR): return "1"
    return "0"

def isInvertingGate(gateType):
    return gateType in (GateType.NAND, GateType.NOR, GateType.NOT)

def invertBit(bit):
    return "1" if bit == "0" else "0"

# Helper to split a 5 value symbol into a good, faulty pair
def convertSymbolToPair(symbol):
    if symbol == "0": return 0, 0
    if symbol == "1": return 1, 1
    if symbol == VAL_D: return 1, 0
    if symbol == VAL_DB: return 0, 1
    if symbol == VAL_X: return None, None
    raise ValueError(f"Invalid symbol {symbol}")

# Helper to combine a good, faulty pair back into a 5 value symbol
def convertPairToSymbol(goodValue, faultyValue):
    if goodValue is None and faultyValue is None: return VAL_X
    if goodValue == 0 and faultyValue == 0: return "0"
    if goodValue == 1 and faultyValue == 1: return "1"
    if goodValue == 1 and faultyValue == 0: return VAL_D
    if goodValue == 0 and faultyValue == 1: return VAL_DB
    return VAL_X

# Evaluates standard boolean logic 
def evaluateBooleanGate(gateType, inputValues):
    if gateType == GateType.BRANCH:
        return inputValues[0]
    if gateType == GateType.AND:
        if 0 in inputValues: return 0
        if None in inputValues: return None
        return 1
    if gateType == GateType.OR:
        if 1 in inputValues: return 1
        if None in inputValues: return None
        return 0
    if gateType == GateType.NAND:
        intermediateResult = evaluateBooleanGate(GateType.AND, inputValues)
        return None if intermediateResult is None else 1 - intermediateResult
    if gateType == GateType.NOR:
        intermediateResult = evaluateBooleanGate(GateType.OR, inputValues)
        return None if intermediateResult is None else 1 - intermediateResult
    if gateType == GateType.NOT:
        intermediateResult = inputValues[0]
        return None if intermediateResult is None else 1 - intermediateResult
    raise ValueError(f"Unsupported gate type {gateType}")

# Evaluates a gate using 5 value logic by splitting it into good, faulty parts
def evaluateGateFiveValued(gateType, inputSymbols):
    goodValues = []
    faultyValues = []
    for symbol in inputSymbols:
        goodComponent, faultyComponent = convertSymbolToPair(symbol)
        goodValues.append(goodComponent)
        faultyValues.append(faultyComponent)
    goodOutput = evaluateBooleanGate(gateType, goodValues)
    faultyOutput = evaluateBooleanGate(gateType, faultyValues)
    return convertPairToSymbol(goodOutput, faultyOutput)

# Creates the starting dictionary for all wires set to X
def initializeAssignments(circuit):
    assignments = {}
    allWires = set(circuit.primaryInputs) | set(circuit.primaryOutputs)
    for gate in circuit.gateList:
        allWires.add(gate.outputWire)
        allWires.update(gate.inputWires)
    for wire in allWires:
        assignments[wire] = VAL_X
    return assignments

# Checks if two values contradict eachother
def checkConflict(valueA, valueB):
    if valueA == VAL_X or valueB == VAL_X or valueA == valueB: return False
    goodA, faultyA = convertSymbolToPair(valueA)
    goodB, faultyB = convertSymbolToPair(valueB)
    if goodA is not None and goodB is not None and goodA != goodB: return True
    if faultyA is not None and faultyB is not None and faultyA != faultyB: return True
    return False