"""BACQ integration for QScore MaxCut on myQLM simulators."""

from bacq_core.parameters import Parameter, ParameterSet

from .experiment import run
from .evaluate import get_metric_success, get_score
from .helpers_protocol import sequence_generator
from .view import benchmark_txt, benchmark_seq_txt


parameters = ParameterSet([
    Parameter(name="initial_size", constraint=int, description="Smallest MaxCut graph size to benchmark"),
    Parameter(name="size_limit", constraint=int, description="Largest MaxCut graph size to benchmark"),
    Parameter(name="beta", constraint=float, description="QScore threshold ratio"),
    Parameter(name="iterator", constraint=str, description="Size search method: 'exhaustive' or 'dichotomic'"),
    Parameter(
        name="depth",
        constraint=int,
        description="QAOA ansatz depth (used by CLinalg; ignored by annealers)",
    ),
    Parameter(name="seed", constraint=int, description="Random seed for reproducible graph generation"),
])

sequence_parameters = ParameterSet([])
