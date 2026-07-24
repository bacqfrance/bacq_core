"""
Noe Olivier -- July 2026
"""

from bacq_core.parameters import Parameter, ParameterSet

from .experiment import run
from .helpers_protocol import sequence_generator
from .evaluate import get_metric_success, get_score
from .view import benchmark_txt, benchmark_seq_txt


parameters = ParameterSet([
    Parameter(name="graph_type", constraint=str, description="Type of graph"),
    Parameter(name="n", constraint=int, description="Number of qubits", sequence=True),
    Parameter(name="d", constraint=int, description="Distance between the initial and destination nodes", sequence=True),
    Parameter(name="num_walk", constraint=int or list[int], description="Number of discrete-time quantum walk steps"),
    Parameter(name="num_aa", constraint=int or list[int], description="Number of amplitude amplification iterations"),
    Parameter(name="num_instances", constraint=int, description="Number of instances"),
    Parameter(name="num_batches", constraint=int, description="Number of batches"),    
    Parameter(name="num_shots_per_circuit", constraint=int, description="Number of shots per circuit run"),
])

sequence_parameters = ParameterSet([
    Parameter(name="graph_type", constraint=str, description="Type of graph"),
    Parameter(name="n_min", constraint=int, description="Number of qubits for the minimum size problem"),
    Parameter(name="d_min", constraint=int, description="Distance for the minimum size problem"),
    Parameter(name="n_max", constraint=int, description="Number of qubits for the maximum size problem"),
    Parameter(name="d_max", constraint=int, description="Distance for the maximum size problem"),
])
