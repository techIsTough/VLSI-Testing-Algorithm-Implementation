from enum import Enum

# Defines the types of gates the system supports
class GateType(Enum):
    AND = "and"
    OR = "or"
    NAND = "nand"
    NOR = "nor"
    NOT = "not"
    BRANCH = "branch"

# Represents a single gate in the circuit
class Gate:
    def __init__(self, outputName, gateType, inputNames):
        self.outputWire = outputName
        self.gateType = gateType
        self.inputWires = inputNames

# Holds all data for the loaded circuit
class Circuit:
    def __init__(self, name):
        self.circuitName = name
        self.primaryInputs = []
        self.primaryOutputs = []
        self.gateList = []
        self.sortedGates = []       # Stores gates in the order they have to be simulated
        self.isExpanded = False     # Flags if fanout branches have been isolated and split out

# Represents a single stuck-at fault on a specific wire
class Fault:
    def __init__(self, wireName, stuckAtValue):
        self.wireName = wireName
        self.stuckAtValue = stuckAtValue

    def __repr__(self):
        return f"{self.wireName}:s-a-{self.stuckAtValue}"