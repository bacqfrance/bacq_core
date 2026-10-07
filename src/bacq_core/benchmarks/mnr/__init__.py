"""
Harshit Verma -- October 2026
"""

from bacq_core.parameters import Parameter, ParameterSet

from .experiment import run
from .evaluate import get_metric_success, get_score
from .view import benchmark_txt


parameters = ParameterSet([
    ## VQE experiment
    Parameter(name="n", constraint=int, description="Number of qubits (spin sites of the Heisenberg chain)"),
    Parameter(name="layers", constraint=list[int], description="Numbers of ansatz layers to run"),
    Parameter(name="num_seeds", constraint=int, description="Number of random initial parameter sets per number of layers"),
    Parameter(name="max_iters", constraint=int, description="Maximum number of COBYLA iterations"),
    Parameter(name="tol", constraint=float, description="COBYLA tolerance for optimization termination"),
    Parameter(name="num_shots", constraint=int, description="Number of shots per energy estimation on the device"),
    Parameter(name="zne_scale_factors", constraint=list[int], description="Odd noise scale factors for zero-noise extrapolation by gate folding"),
    Parameter(name="num_twirls", constraint=int, description="Number of Pauli-twirled circuit instances per noise scale factor"),
    ## Evaluation (no experiment needed to change them)
    Parameter(name="mu_fit_window", constraint=int, description="Iterations per ansatz layer used to fit the convergence rate (null: full trajectory)", meta=True),
    Parameter(name="alpha", constraint=float, description="Amplitude alpha of the convergence transient (null: fitted from the trajectories)", meta=True),
    Parameter(name="energy_shots", constraint=int, description="Number of shots per measurement group in the energy accounting", meta=True),
    Parameter(name="classical_efficiency", constraint=float, description="Classical compute efficiency [FLOP/J] (Green500)", meta=True),
    Parameter(name="flops_prefactor", constraint=float, description="Prefactor a of the optimizer cost per iteration a * L^b [FLOP]", meta=True),
    Parameter(name="flops_exponent", constraint=float, description="Exponent b of the optimizer cost per iteration a * L^b", meta=True),
    Parameter(name="cryo_efficiency", constraint=float, description="Refrigeration efficiency as a fraction of the Carnot limit", meta=True),
    Parameter(name="stage_temperatures", constraint=list[float], description="Fridge stage temperatures, qubit to room [K]", meta=True),
    Parameter(name="attenuation_range_db", constraint=list[float], description="Range [min, max] of the total line attenuation [dB]", meta=True),
    Parameter(name="gate_time_range_ns", constraint=list[float], description="Range [min, max] of the single-qubit gate time [ns]", meta=True),
    Parameter(name="floor_margin", constraint=float, description="Target accuracy of the figure of merit, as a multiple of the error floor", meta=True),
    Parameter(name="target_multipliers", constraint=list[float], description="Target accuracies of the energy-error curve, as multiples of the error floor", meta=True),
])
