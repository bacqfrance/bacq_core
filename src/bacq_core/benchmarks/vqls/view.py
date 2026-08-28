"""
Noe Olivier -- July 2026

Defines how to display the QWS benchmark results.
"""

benchmark_txt = """
***** BACQ-LS-VQLS (Variational Quantum Linear Solver) *****
   _____________________________

Device: {device}
Date experiment: {date}
   _____________________________

Benchmark parameters:
- Problem size (nb qubits): {n}
- Classical optimizer: {optimizer}
- Max iterations: {max_iters}
- Tolerance: {tol}
- Ansatz: {ansatz}
- Number of layers: {num_layers}
- Number of shots (cost evaluation): {num_shots}
- Number of shots (solution estimation): {num_shots_solution}

Benchmark result:
- Metric: {metric:.3f}
- Success: {success}
___________________________________

"""

benchmark_seq_txt = """
***** BACQ-LS-VQLS (Variational Quantum Linear Solver) *****
   _____________________________   

Device: {device}
Date experiments: {date}
   _____________________________

Benchmark parameters:
- Classical optimizer: {optimizer}
- Ansatz: {ansatz}
- Number of shots (cost evaluation): {num_shots}
- Number of shots (solution estimation): {num_shots_solution}

Benchmark results:
"""
