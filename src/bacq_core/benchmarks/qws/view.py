"""
Noe Olivier -- July 2026

Defines how to display the QWS benchmark results.
"""

benchmark_txt = """
***** Quantum WalkScore (QWS) *****
   _____________________________

Device: {device}
Date experiment: {date}
   _____________________________

Benchmark parameters:
- Graph type: {graph_type}
- Problem size (n, d): ({n}, {d})
- Number of DTQW steps: {num_walk}
- Number of AA iterations: {num_aa}
- Number of instances: {num_instances}
- Number of batches: {num_batches}
- Number of shots: {num_shots}

Benchmark result:
- Metric: {metric:.3f}
- Success: {success}
___________________________________

"""

benchmark_seq_txt = """
***** Quantum WalkScore (QWS) *****
   _____________________________   

Device: {device}
Date experiments: {date}
   _____________________________

Benchmark parameters:
- Graph type: {graph_type}
- Number of instances: {num_instances}
- Number of batches: {num_batches}
- Number of shots: {num_shots}

Benchmark results:
"""
