"""
Grégoire Misguich -- October 2026

Defines functions to ensure the MBQS protocol is well applied.
"""

_STATES = ["down", "plus"]

# Range of system sizes covered by the tabulated free-fermion data of `mbqs`.
# Larger sizes need the free-fermion solver, which is not implemented in `mbqs` yet.
_MIN_L = 2
_MAX_L = 50

_MIN_NUM_SHOTS = 1


def sequence_generator(L_min, L_max):
    """
    Generate the list of sequence parameters, i.e. problem sizes.
    """
    check_L(L_min)
    check_L(L_max)

    if L_max < L_min:
        raise ValueError(f"Sequence parameter {L_max=} must be at least equal to {L_min=}.")

    return [{"L": L} for L in range(L_min, L_max + 1)]


def check_parameters_value(state, L, threshold, num_shots, list_seq_params=None):
    """
    Checks that input parameters value are protocol-valid.
    """
    check_state(state)
    check_threshold(threshold)
    check_num_shots(num_shots)

    if list_seq_params is None:
        check_L(L)
    else:
        for seq_params in list_seq_params:
            check_L(seq_params["L"])


def check_state(state):
    """
    Checks type and value of input initial state.
    """
    if not isinstance(state, str):
        raise TypeError("Parameter state must be <str>.")

    if state not in _STATES:
        raise ValueError(f"Parameter {state=} not valid: expected one of {_STATES}.")


def check_L(L):
    """
    Checks type and value of input system size.
    """
    if not isinstance(L, int):
        raise TypeError("Parameter L must be <int>.")

    if not _MIN_L <= L <= _MAX_L:
        raise ValueError(f"Parameter {L=} not valid: {_MIN_L} <= L <= {_MAX_L} required.")


def check_threshold(threshold):
    """
    Checks type and value of input threshold.
    """
    if not isinstance(threshold, (int, float)):
        raise TypeError("Parameter threshold must be <float>.")

    if threshold <= 0:
        raise ValueError(f"Parameter {threshold=} not valid: > 0 required.")


def check_num_shots(num_shots):
    """
    Checks type and value of input number of shots.
    """
    if not isinstance(num_shots, int):
        raise TypeError("Parameter num_shots must be <int>.")

    if num_shots < _MIN_NUM_SHOTS:
        raise ValueError(f"Parameter {num_shots=} not valid: >= {_MIN_NUM_SHOTS} required.")


def check_counts(counts, L, num_shots):
    """
    Checks that measured bitstrings match the system size and the number of shots.
    """
    if any(len(bitstring) != L for bitstring in counts.keys()):
        raise ValueError(f"Reported bitstrings do not all have length {L=}.")

    num_shots_exp = sum(counts.values())
    if num_shots_exp != num_shots:
        raise ValueError(f"Reported counts does not have the right number of shots.\n{num_shots=} vs reported_counts={num_shots_exp}")
