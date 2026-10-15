"""
Grégoire Misguich -- October 2026

Defines how to display the MBQS benchmark results.
"""

benchmark_txt = """
***** Many-Body Quantum Score (MBQS) *****
   ____________________________________

Device: {device}
Date experiment: {date}
   ____________________________________

Benchmark parameters:
- Initial state: {state}
- Problem size L: {L}
- Threshold: {threshold}
- Number of shots: {num_shots}

Benchmark result:
- Metric P2(L): {metric:.3f}
- Success: {success}
__________________________________________

"""

benchmark_seq_txt = """
***** Many-Body Quantum Score (MBQS) *****
   ____________________________________

Device: {device}
Date experiments: {date}
   ____________________________________

Benchmark parameters:
- Initial state: {state}
- Threshold: {threshold}
- Number of shots: {num_shots}

Benchmark results:
"""
