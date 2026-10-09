"""
Harshit Verma -- October 2026

Defines functions to ensure the BACQ-EP-MNR protocol is well applied.
"""

_MIN_NUM_QUBITS = 3
_MIN_NUM_DEPTHS = 3
_MIN_NUM_SEEDS = 2
_MIN_NUM_SHOTS = 1000


def check_parameters_value(num_qubits, layers, num_seeds, max_iters, tol, num_shots, zne_scale_factors, num_twirls):
    """
    Checks that input parameters value are protocol-valid.
    """
    check_num_qubits(num_qubits)
    check_layers(layers)
    check_num_seeds(num_seeds)
    check_optimizer(max_iters, tol)
    check_num_shots(num_shots)
    check_mitigation(zne_scale_factors, num_twirls)


def check_num_qubits(num_qubits):
    """
    Checks type and value of input number of qubits.
    """
    if not isinstance(num_qubits, int):
        raise TypeError('Parameter n must be <int>.')
    if num_qubits < _MIN_NUM_QUBITS:
        raise ValueError(f'Parameter n={num_qubits} not valid: >= {_MIN_NUM_QUBITS} required.')


def check_layers(layers):
    """
    Checks the list of ansatz depths: the convergence model needs several depths to be fitted.
    """
    if not isinstance(layers, list) or not all(isinstance(layer, int) and layer >= 1 for layer in layers):
        raise TypeError('Parameter layers must be <list[int]> of positive integers.')
    if len(set(layers)) < _MIN_NUM_DEPTHS:
        raise ValueError(f'Parameter {layers=} not valid: at least {_MIN_NUM_DEPTHS} distinct depths required.')


def check_num_seeds(num_seeds):
    """
    Checks type and value of input number of random initializations.
    """
    if not isinstance(num_seeds, int):
        raise TypeError('Parameter num_seeds must be <int>.')
    if num_seeds < _MIN_NUM_SEEDS:
        raise ValueError(f'Parameter {num_seeds=} not valid: >= {_MIN_NUM_SEEDS} required.')


def check_optimizer(max_iters, tol):
    """
    Checks type and value of the COBYLA stopping criteria.
    """
    if not isinstance(max_iters, int) or max_iters < 1:
        raise TypeError('Parameter max_iters must be a positive <int>.')
    if not isinstance(tol, float) or tol <= 0:
        raise TypeError('Parameter tol must be a positive <float>.')


def check_num_shots(num_shots):
    """
    Checks type and value of input number of shots.
    """
    if not isinstance(num_shots, int):
        raise TypeError('Parameter num_shots must be <int>.')
    if num_shots < _MIN_NUM_SHOTS:
        raise ValueError(f'Parameter {num_shots=} not valid: >= {_MIN_NUM_SHOTS} required.')


def check_mitigation(zne_scale_factors, num_twirls):
    """
    Checks the zero-noise extrapolation and Pauli-twirling parameters.
    """
    if not isinstance(zne_scale_factors, list) or not all(isinstance(c, int) and c >= 1 and c % 2 == 1 for c in zne_scale_factors):
        raise TypeError('Parameter zne_scale_factors must be <list[int]> of odd integers >= 1.')
    if len(set(zne_scale_factors)) < 2:
        raise ValueError(f'Parameter {zne_scale_factors=} not valid: at least 2 distinct scale factors required.')
    if not isinstance(num_twirls, int) or num_twirls < 1:
        raise TypeError('Parameter num_twirls must be a positive <int>.')
