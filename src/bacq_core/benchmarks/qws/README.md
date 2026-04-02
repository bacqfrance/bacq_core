# Quantum WalkScore (QWS) Benchmark
This folder includes QWS-specific scripts.

## Code structure
Some files are required for all benchmarks so that these benchmarks can be successfully evaluated and experiments successfully conducted.
- `__init__.py`: defines benchmark-specific protocol parameters (here QWS) based on the benchmark-agnostic parameter class.
- `evaluate.py`: defines functions used to access metric and score computation from the package of the specific benchmark (here QWS).
- `experiment.py`: defines a global `run()` function, a global structure for experiment data, and ensures the benchmark-specific protocol (here QWS) is well applied.
- `view.py`: defines two global strings, formatted to display the results of the specific benchmark (here QWS).

Although their content vary depending on the protocol, these files are required within all benchmark folders, along with aforementioned variables and functions.

Additional benchmark-specific files are proposed:
- `helpers_instance.py`: defines functions to generate an accepted graph instance.
- `helpers_protocol.py`: defines functions to ensure the QWS protocol is well applied.
- `helpers_qiskit.py`: defines functions to build the algorithm circuit using qiskit.

Depending on the selected hardware platform, the end user is welcome to propose and additional file (i.e. helpers_nameplatform using myqlm, cirq, etc...) and develop the algorithm construction intended for a new platform and use it for the benchmark evaluation.

## How to use within the BACQ library
The protocol details are given in the associated package `qws`.

*[add link to repository]*

This folder proposes an implementation that allows for the direct evaluation of qiskit-available hardware, especially IBM QPU.

In order to run benchmark experiments on another platform, the end user can:
1) ensure the `.json` input file contains `"benchmark": "qws"`.
2) provide an additional file (i.e. `helpers_platform.py`) that construct a circuit using the expected platform language
3) provide (if necessary) a new file describing a global class that defines how jobs are submitted to the new QPU: i.e. `myprovider_realdevice.py` to be located in `src/bacq_core/hardware/`.
4) adapt the `experiment.py` file to enable access to the expected QPU:
	- `run()`: add access to new hardware
	- `run_newQPU()`: construct the corresponding funcion (adapted to the new QPU) based on the example proposed `run_qiskit()`

## Author
Noe OLIVIER, cortAIx Labs, Thales, France
