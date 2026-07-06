from models import Circuit, Gate, GateType

# Maps text strings from the input file to internal GateType enums
gateTypeMap = {
    "and": GateType.AND,
    "or": GateType.OR,
    "nand": GateType.NAND,
    "nor": GateType.NOR,
    "not": GateType.NOT,
    "buf": GateType.BRANCH,
    "branch": GateType.BRANCH,
}

# Reads the file line by line and creates the Circuit object
def readNetlist(filePath):
    with open(filePath, "r") as fileHandle:
        plainLines = fileHandle.readlines()

    circuit = Circuit(name=filePath)

    for line in plainLines:
        line = line.strip()
        # Skip empty lines
        if not line:
            continue

        # Skip comment lines
        if line.startswith("$"):
            continue

        lowerCaseLine = line.lower()

        # Parse primary inputs
        if "primary input" in lowerCaseLine:
            name = line.split()[0]
            if name not in circuit.primaryInputs:
                circuit.primaryInputs.append(name)
            continue

        # Parse primary outputs
        if "primary output" in lowerCaseLine:
            name = line.split()[0]
            if name not in circuit.primaryOutputs:
                circuit.primaryOutputs.append(name)
            continue

        # Skip header lines in the file
        if "output" in lowerCaseLine and "type" in lowerCaseLine and "inputs" in lowerCaseLine:
            continue

        # Parse standard gate definition header
        lineElements = line.split()
        if len(lineElements) < 3:
            continue

        outputName = lineElements[0]
        gateTypeString = lineElements[1].lower()
        inputNames = lineElements[2:]

        if gateTypeString not in gateTypeMap:
            raise ValueError(f"Unknown gate type '{gateTypeString}' in line: {line}")

        circuit.gateList.append(Gate(outputName, gateTypeMap[gateTypeString], inputNames))

    # Sort the gates so they can be simulated in proper order
    buildTopologicalOrder(circuit)
    return circuit

# Organizes gates so that a gate is only calculated after its inputs are ready
def buildTopologicalOrder(circuit):
    # Tracks which wires have a known value starting with primary inputs
    allWires = set(circuit.primaryInputs)
    sortedList = []
    
    # Make a copy of the list so items can be removed as they are processed
    remainingGates = list(circuit.gateList) 

    # Keep looping until all gates are placed in the sorted list
    while remainingGates:
        progressMade = False
        
        # Look for a gate whose inputs are all currently known
        for gate in remainingGates:
            inputsReady = True
            for wire in gate.inputWires:
                if wire not in allWires:
                    inputsReady = False
                    break
            
            # If inputs are ready, add gate to list and mark its output as known
            if inputsReady:
                sortedList.append(gate)
                allWires.add(gate.outputWire)
                remainingGates.remove(gate)
                progressMade = True
                # Restart the search to ensure correct ordering
                break 

        # If no gate could be picked, there's a loop or missing input
        if not progressMade:
            raise ValueError("Cycle or unresolved dependency in netlist.")

    circuit.sortedGates = sortedList