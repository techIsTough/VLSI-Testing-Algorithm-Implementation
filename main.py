import os
import sys
import copy

from netlist import readNetlist
from faults import performFaultCollapsing, displayFaultClasses
from simulate import simulate, getDetectedFaults
from podem import generateTestVector
from models import Fault, Circuit

BASE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
BENCHMARK_DIRECTORY = os.path.join(BASE_DIRECTORY, "benchmarks")

def main():
    currentCircuit = None
    collapsedFaults = None
    faultClasses = None

    while True:
        print("--- VLSI Testing Final Project ---")
        print("[0] Read the input net-list")
        print("[1] Perform fault collapsing")
        print("[2] List fault classes")
        print("[3] Simulate")
        print("[5] Generate tests (PODEM)")
        print("[7] Exit")

        choice = input("Selection: ").strip()

        if choice == "0":
            currentCircuit = loadCircuitMenu()
            if currentCircuit:
                # Reset previous results when new circuit is loaded
                collapsedFaults = None
                faultClasses = None
                printCircuitDetails(currentCircuit)

        elif choice == "1":
            requireCircuitLoaded(currentCircuit)
            print("Performing Fault Collapsing.")
            
            # Collapse faults and save the results
            faultClasses, representatives = performFaultCollapsing(currentCircuit)
            collapsedFaults = representatives
            print("Fault Collapsing Complete.")
            print(f"Total Collapsed Fault Classes: {len(faultClasses)}\n")

        elif choice == "2":
            requireCircuitLoaded(currentCircuit)
            if faultClasses is None:
                print("Error: Run option 1 first.\n")
            else:
                displayFaultClasses(faultClasses)

        elif choice == "3":
            requireCircuitLoaded(currentCircuit)
            inputVector = readInputVector(currentCircuit)
            
            # Run simulation on good circuit first
            goodOutputs = simulate(currentCircuit, inputVector, fault=None)
            print(f"\nGood Circuit Output(s): {goodOutputs}")
            
            print("\nProceed Immediately to Fault Simulation?")
            print("y: Apply input test vector to each member of collapsed fault list (must execute option 1)")
            print("n: Skip")
            subChoice = input("Selection (y/n): ").strip().lower()
            print("\n")

            if subChoice == "y":
                if collapsedFaults is None:
                    print("Error: Fault collapsing (Option 1) must be run first.\n")
                else:
                    print(f"Simulating against {len(collapsedFaults)} collapsed faults...")
                    detected = getDetectedFaults(currentCircuit, inputVector, collapsedFaults)
                    
                    if not detected:
                        print("Result: No faults detected by this vector.\n")
                    else:
                        print(f"Result: {len(detected)} fault(s) detected.")
                        print("Detected Faults: ", end="")
                        print(", ".join(str(f) for f in detected))
                        print("\n")

            elif subChoice == "n":
                pass
            else:
                print("Invalid Input.")
                return

        elif choice == "5":
            requireCircuitLoaded(currentCircuit)
            
            print("\nPODEM Mode:")
            print("s: Target a Single Specified Fault")
            print("a: Apply to All Members of Collapsed Fault List")
            subChoice = input("Selection (s/a): ").strip().lower()
            
            if subChoice == "s":
                validWires = [g.outputWire for g in currentCircuit.gateList] + currentCircuit.primaryInputs
                print(f"Known Wires: {validWires}")
                
                # Validation for wire name
                while True:
                    wireName = input("Fault Wire Name: ").strip()
                    if wireName in validWires:
                        break
                    print(f"Error: Wire '{wireName}' not found in circuit. Provide a valid input.")

                # Validation for stuck-at value
                while True:
                    try:
                        saInput = input("Stuck-At Value (0 or 1): ").strip()
                        sa = int(saInput)
                        if sa in (0, 1):
                            break
                        print("Error: Value must be 0 or 1.")
                    except ValueError:
                        print("Error: Invalid number. Please enter 0 or 1.")
                    
                target = Fault(wireName, sa)
                print(f"Running PODEM for {target}.")
                tv = generateTestVector(currentCircuit, target)
                
                if tv is None:
                    print("No test found. Fault may be redundant or undetectable.\n")
                else:
                    print("Test Vector Found:", tv)
                    goodRes = simulate(currentCircuit, tv, fault=None)
                    faultRes = simulate(currentCircuit, tv, fault=target)
                    print("Good Output =", goodRes, "| Faulty Output =", faultRes, "\n")
            
            elif subChoice == "a":
                if collapsedFaults is None:
                    print("Error: Fault collapsing (Option 1) must be run first.\n")
                else:
                    print(f"\nRunning ATPG on {len(collapsedFaults)} SSA faults.")
                    detectable = []
                    undetectable = []
                    
                    for f in collapsedFaults:
                        tv = generateTestVector(currentCircuit, f)
                        if tv:
                            detectable.append((f, tv))
                        else:
                            undetectable.append(f)
                    
                    print(f"\n--- Detectable Faults and Vectors ---")
                    for f, tv in detectable:
                        vecStr = "".join(str(tv[pi]) for pi in currentCircuit.primaryInputs)
                        print(f"{f} --> Vector: {vecStr}")
                        
                    print(f"\n--- Undetectable Faults ---")
                    if undetectable:
                        for f in undetectable:
                            print(str(f))
                    else:
                        print("None")
                    print("=================================\n")
            else:
                print("Invalid Input.")
                return

        elif choice == "7":
            print("Exiting...")
            break

        else:
            print("Invalid Input.")
            return

# Displays available benchmarks and handles file selection
def loadCircuitMenu():
    if not os.path.exists(BENCHMARK_DIRECTORY):
        print("Invalid Input.")
        sys.exit()
        
    files = sorted(f for f in os.listdir(BENCHMARK_DIRECTORY) if f.endswith((".ckt", ".txt")))
    
    if not files:
        print("Invalid Input.")
        sys.exit()

    print("\nAvailable Benchmark Circuits:")
    for i, name in enumerate(files, 1):
        print(f"[{i}] {name}")

    choice = input("Enter index or filename: ").strip()

    path = None
    if choice.isdigit():
        index = int(choice)
        if 1 <= index <= len(files):
            path = os.path.join(BENCHMARK_DIRECTORY, files[index - 1])
    else:
        cand = os.path.join(BENCHMARK_DIRECTORY, choice)
        if os.path.exists(cand):
            path = cand
            
    if path:
        try:
            return readNetlist(path)
        except Exception:
            print("Invalid Input.")
            sys.exit()
    else:
        print("Invalid Input.")
        sys.exit()

# Makes sure a circuit is loaded before running operations
def requireCircuitLoaded(circuit):
    if circuit is None:
        print("Error: Please load a circuit first (Option 0).")
        raise RuntimeError("No circuit")

# Prompts the user for a binary input vector
def readInputVector(circuit):
    print(f"Circuit Inputs: {circuit.primaryInputs}")
    
    while True:
        print("Enter primary input values as a binary sequence (1011, 01010 10, etc.) matching the order above.")
        s = input("Vector: ").strip()
        
        if len(s) != len(circuit.primaryInputs):
            print(f"Error: Expected {len(circuit.primaryInputs)} bit(s), got {len(s)}. Provide a valid input.\n")
            continue
            
        isBinary = True
        for char in s:
            if char not in ("0", "1"):
                isBinary = False
                break
        
        if not isBinary:
            print("Error: Input must contain only '0' and '1'. Please try again.\n")
            continue
            
        break
    
    vals = {}
    for i, pi in enumerate(circuit.primaryInputs):
        vals[pi] = int(s[i])
    return vals

def printCircuitDetails(circuit):
    print("\n--- Circuit Loaded ---")
    print(f"Path: {circuit.circuitName}")
    print(f"Primary Inputs: {circuit.primaryInputs}")
    print(f"Primary Outputs: {circuit.primaryOutputs}")
    print(f"Gate Count: {len(circuit.gateList)}")
    print("=================================\n")

if __name__ == "__main__":
    main()