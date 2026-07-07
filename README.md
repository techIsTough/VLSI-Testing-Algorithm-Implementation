# VLSI Testing Algorithm Implementation

This project is a Python tool for analyzing digital logic circuits. It can parse benchmark circuits, reduce the size of stuck-at fault lists, simulate circuit behavior, and automatically generate test patterns using the PODEM algorithm. 

The program relies strictly on Python's standard libraries, meaning you do not need to install any external dependencies to run it.

## Features
* **Netlist Parsing:** Reads circuit configuration files line-by-line and organizes gates in a proper topological execution order.
* **Fault Collapsing:** Automatically isolates circuit fanout branches. It then uses standard equivalence and dominance logic rules to filter out redundant stuck-at faults.
* **Logic Simulation:** Runs standard good-circuit evaluations or inserts forced stuck-at faults to see how they impact primary circuit outputs.
* **PODEM ATPG:** Implements the classic 5-value logic system (0, 1, X, D, DBar) to trace back paths and build test vectors for targeted faults.

## Code Structure
The codebase is split into six main files to keep the structure clear and organized:
* `main.py`: Houses the interactive main menu interface, handles input validation, and links all project operations together.
* `models.py`: Defines the core object structures for Circuits, Gates, and Faults.
* `netlist.py`: Handles file processing to read benchmark files and sorts gates based on input readiness.
* `faults.py`: Manages the logic for circuit expansion and collapsing identical fault classes.
* `simulate.py`: Simulates good and faulty wire values using basic gate logic tracking.
* `podem.py`: Contains the main recursive PODEM search and backtrace functions.

## How to Run

### Setup
1. Unzip the project folder onto your computer.
2. Place all `.ckt` or `.txt` benchmark circuit files directly inside the `benchmarks/` directory.
3. Open your terminal and navigate to the project directory.

### Execution
* **On Windows PowerShell or Command Prompt:** Run the program by typing:
  ```powershell
  python main.py
