"""
Grégoire Misguich -- October 2026

Defines functions to ensure the MBQS protocol is well applied.
"""

from math import isfinite

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
        if not list_seq_params:
            raise ValueError("The experiment sequence must not be empty.")
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
    if isinstance(L, bool) or not isinstance(L, int):
        raise TypeError("Parameter L must be <int>.")

    if not _MIN_L <= L <= _MAX_L:
        raise ValueError(f"Parameter {L=} not valid: {_MIN_L} <= L <= {_MAX_L} required.")


def check_threshold(threshold):
    """
    Checks type and value of input threshold.
    """
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise TypeError("Parameter threshold must be <float>.")

    if not isfinite(threshold) or threshold <= 0:
        raise ValueError(f"Parameter {threshold=} not valid: finite and > 0 required.")


def check_num_shots(num_shots):
    """
    Checks type and value of input number of shots.
    """
    if isinstance(num_shots, bool) or not isinstance(num_shots, int):
        raise TypeError("Parameter num_shots must be <int>.")

    if num_shots < _MIN_NUM_SHOTS:
        raise ValueError(f"Parameter {num_shots=} not valid: >= {_MIN_NUM_SHOTS} required.")


def check_sample_num_shots(num_shots):
    """Require enough samples to estimate statistical uncertainties."""
    check_num_shots(num_shots)
    if num_shots < 2:
        raise ValueError("Sample data require at least 2 shots to estimate uncertainties.")


def check_counts(counts, L, num_shots):
    """
    Validate measured bitstrings and counts, including the total number of shots.

    Use num_shots=None when the declared shot count is unavailable.
    """
    check_L(L)
    if not isinstance(counts, dict):
        raise TypeError("Samples must be a dictionary of bitstrings and counts.")
    if not counts:
        raise ValueError("Samples must not be empty.")
    if any(not isinstance(bitstring, str) for bitstring in counts):
        raise TypeError("Sample bitstrings must be strings.")
    if any(len(bitstring) != L for bitstring in counts):
        raise ValueError(f"Reported bitstrings do not all have length {L=}.")
    if any(set(bitstring) - {"0", "1"} for bitstring in counts):
        raise ValueError("Sample bitstrings must contain only '0' and '1'.")
    if any(isinstance(count, bool) or not isinstance(count, int) for count in counts.values()):
        raise TypeError("Sample counts must be integers, not booleans.")
    if any(count < 0 for count in counts.values()):
        raise ValueError("Sample counts must be nonnegative.")

    num_shots_exp = sum(counts.values())
    check_sample_num_shots(num_shots_exp)
    if num_shots is not None:
        check_sample_num_shots(num_shots)
    if num_shots is not None and num_shots_exp != num_shots:
        raise ValueError(f"Reported counts does not have the right number of shots.\n{num_shots=} vs reported_counts={num_shots_exp}")


def check_correlations(correlations, errors=False):
    """Validate correlation values or their statistical uncertainties."""
    name = "correlations_err" if errors else "correlations"
    if not isinstance(correlations, dict):
        raise TypeError(f"{name} must be a dictionary.")
    if not correlations:
        raise ValueError(f"{name} must not be empty.")
    values = correlations.values()
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
        raise TypeError(f"{name} values must be numbers, not booleans.")
    if any(not isfinite(value) for value in values):
        raise ValueError(f"{name} values must be finite.")
    if errors and any(value < 0 for value in values):
        raise ValueError("Correlation uncertainties must be nonnegative.")
