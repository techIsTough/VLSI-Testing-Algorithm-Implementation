from models import Circuit, Fault, GateType, Gate
from netlist import buildTopologicalOrder

# Addresses fanout stems within the circuit to allow for proper testing
def expandCircuitForFanouts(circuit):
    if circuit.isExpanded:
        return

    # Count how many gates use each wire as an input
    wireUsageSet = {}
    for gate in circuit.gateList:
        for inputWire in gate.inputWires:
            if inputWire not in wireUsageSet:
                wireUsageSet[inputWire] = []
            wireUsageSet[inputWire].append(gate)

    newGatesList = []
    
    # Check every wire to see if it's branching to multiple gates
    for wireName, receivingGates in wireUsageSet.items():
        if len(receivingGates) > 1:
            # Create a name for each branch and pass through its value
            for index, gate in enumerate(receivingGates):
                branchName = f"{wireName}_FO{index}"
                
                branchGate = Gate(branchName, GateType.BRANCH, [wireName])
                newGatesList.append(branchGate)
                
                # Make sure the destination gate reads from the new branch
                for inputIndex in range(len(gate.inputWires)):
                    if gate.inputWires[inputIndex] == wireName:
                        gate.inputWires[inputIndex] = branchName
                        break
    
    circuit.gateList.extend(newGatesList)
    # Re-sort the circuit because the structure changed
    buildTopologicalOrder(circuit)
    
    circuit.isExpanded = True
    print(f"    (!) Fanout Detected: Generated {len(newGatesList)} Branch(es).")

# Helper function for sorting fault objects
def getFaultSortKey(fault):
    # Sort by wire name then by the stuck-at value
    return (fault.wireName, fault.stuckAtValue)

# Main function to generate the collapsed fault list
def performFaultCollapsing(circuit):
    expandCircuitForFanouts(circuit)

    # Checkpoints are primary inputs and branch outputs
    checkpointWires = set(circuit.primaryInputs)
    for gate in circuit.gateList:
        if gate.gateType == GateType.BRANCH:
            checkpointWires.add(gate.outputWire)

    # Find all possible faults in the circuit
    allWires = set(circuit.primaryInputs) | set(circuit.primaryOutputs)
    for gate in circuit.gateList:
        allWires.add(gate.outputWire)
        allWires.update(gate.inputWires)
        
    faultUniverse = []
    for wire in allWires:
        faultUniverse.append((wire, 0))
        faultUniverse.append((wire, 1))

    # Make a dictionary to track which faults are grouped together
    parentSet = {item: item for item in faultUniverse}

    def findRoot(item):
        if parentSet[item] != item:
            parentSet[item] = findRoot(parentSet[item])
        return parentSet[item]

    def unionSets(item1, item2):
        root1 = findRoot(item1)
        root2 = findRoot(item2)
        if root1 != root2:
            parentSet[root2] = root1

    # Apply equivalence rules
    for gate in circuit.gateList:
        inputs = gate.inputWires
        output = gate.outputWire
        
        if gate.gateType == GateType.NOT:
            unionSets((inputs[0], 0), (output, 1))
            unionSets((inputs[0], 1), (output, 0))

        elif gate.gateType == GateType.AND:
            outputSA0 = (output, 0)
            for inp in inputs:
                unionSets((inp, 0), outputSA0)
        
        elif gate.gateType == GateType.NAND:
            outputSA1 = (output, 1)
            for inp in inputs:
                unionSets((inp, 0), outputSA1)

        elif gate.gateType == GateType.OR:
            outputSA1 = (output, 1)
            for inp in inputs:
                unionSets((inp, 1), outputSA1)

        elif gate.gateType == GateType.NOR:
            outputSA0 = (output, 0)
            for inp in inputs:
                unionSets((inp, 1), outputSA0)

    # Group equivalent faults together in a set
    faultGroups = {}
    for item in faultUniverse:
        root = findRoot(item)
        if root not in faultGroups:
            faultGroups[root] = []
        faultGroups[root].append(Fault(item[0], item[1]))

    classesToRemove = set()
    
    # Apply dominance rules to remove faults in favor of ones that are easier to test
    for gate in circuit.gateList:
        if gate.gateType in (GateType.BRANCH, GateType.NOT): 
            continue
            
        inputValue = None
        outputValue = None
        
        if gate.gateType == GateType.AND:
            inputValue = 1 
            outputValue = 1
        elif gate.gateType == GateType.NAND:
            inputValue = 1 
            outputValue = 0 
        elif gate.gateType == GateType.OR:
            inputValue = 0
            outputValue = 0
        elif gate.gateType == GateType.NOR:
            inputValue = 0
            outputValue = 1 

        # If output fault dominates input fault, remove the output fault class
        if inputValue is not None:
            outputFault = (gate.outputWire, outputValue)
            outputRoot = findRoot(outputFault)
            
            for input in gate.inputWires:
                inputFault = (input, inputValue)
                inputRoot = findRoot(inputFault)
                
                if outputRoot != inputRoot:
                    classesToRemove.add(outputRoot)

    finalFaultClasses = {}
    representativeFaults = []

    # Filter the groups to only keep checkpoint faults
    for root, elements in faultGroups.items():
        if root in classesToRemove:
            continue
            
        filteredElements = []
        for filtered in elements:
            if filtered.wireName in checkpointWires:
                filteredElements.append(filtered)

        if not filteredElements:
            continue

        # Sort to make sure the same equivalent fault is always displayed 
        filteredElements.sort(key=getFaultSortKey)
        representative = filteredElements[0]
        
        finalFaultClasses[(representative.wireName, representative.stuckAtValue)] = filteredElements
        representativeFaults.append(representative)

    representativeFaults.sort(key=getFaultSortKey)
    return finalFaultClasses, representativeFaults

# Prints the collapsed faults in the console
def displayFaultClasses(faultClasses):
    print("\n--- Fault Classes ---")
    sortedKeys = sorted(faultClasses.keys())
    
    for index, key in enumerate(sortedKeys, 1):
        group = faultClasses[key]
        groupString = ", ".join([str(f) for f in group])
        print(f"{index}. [{groupString}]")
    print("=================================\n")