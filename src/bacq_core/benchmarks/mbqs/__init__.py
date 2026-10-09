"""
Grégoire Misguich -- October 2026

Many-Body Quantum Score (MBQS): quench of the critical transverse-field Ising chain
on a ring. Protocol definition, metric and score come from the `mbqs` package
by Harold Erbin (https://github.com/HaroldErbin/mbqs).
"""

from bacq_core.parameters import Parameter, ParameterSet

from .experiment import run
from .helpers_protocol import sequence_generator
from .evaluate import get_metric_success, get_score
from .view import benchmark_txt, benchmark_seq_txt


parameters = ParameterSet([
    Parameter(name="state", constraint=str, description="Initial state: 'down' or 'plus'"),
    Parameter(name="L", constraint=int, description="Number of qubits on the ring", sequence=True),
    Parameter(name="threshold", constraint=float, description="Threshold epsilon on the metric P2(L)"),
    Parameter(name="num_shots", constraint=int, description="Number of shots per system size"),
])

sequence_parameters = ParameterSet([
    Parameter(name="L_min", constraint=int, description="Number of qubits for the minimum size problem"),
    Parameter(name="L_max", constraint=int, description="Number of qubits for the maximum size problem"),
])
