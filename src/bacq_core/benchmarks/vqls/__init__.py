"""
Noe Olivier -- July 2026
"""

from bacq_core.parameters import Parameter, ParameterSet

from .experiment import run
from .helpers_protocol import sequence_generator
from .evaluate import get_metric_success, get_score
from .view import benchmark_txt, benchmark_seq_txt


parameters = ParameterSet([
    Parameter(name="n", constraint=int, description="Number of qubits", sequence=True),
    Parameter(name="optimizer", constraint=str, description="Name of classical optimizer"),
    Parameter(name="max_iters", constraint=int, description="Maximum number of classical optimization iterations (optional)"),
    Parameter(name="tol", constraint=float, description="Tolerance for optimization termination (optional)"),
    Parameter(name="ansatz", constraint=str, description="Name of ansatz"),
    Parameter(name="num_layers", constraint=int, description="Number of ansatz layers"),
    Parameter(name="num_shots", constraint=int, description="Number of shots per circuit run for cost evaluation"),    
    Parameter(name="num_shots_solution", constraint=int, description="Number of shots for quantum solution estimation"),
])

sequence_parameters = ParameterSet([
    Parameter(name="n_min", constraint=int, description="Number of qubits for the minimum size problem"),
    Parameter(name="n_max", constraint=int, description="Number of qubits for the maximum size problem"),
])
