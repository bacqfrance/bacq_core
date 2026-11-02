"""Validation for the BACQ QScore protocol."""

import math


def check_parameters_value(initial_size, size_limit, beta, iterator, depth, seed):
    """Validate parameters before starting the QScore workload."""
    if isinstance(initial_size, bool) or not isinstance(initial_size, int) or initial_size < 2:
        raise ValueError("initial_size must be an integer greater than or equal to 2.")
    if isinstance(size_limit, bool) or not isinstance(size_limit, int):
        raise TypeError("size_limit must be an integer.")
    if size_limit < initial_size:
        raise ValueError("size_limit must be greater than or equal to initial_size.")
    if isinstance(beta, bool) or not isinstance(beta, (int, float)) or not math.isfinite(beta):
        raise TypeError("beta must be a finite number.")
    if not 0 < beta < 1:
        raise ValueError("beta must be greater than 0 and less than 1.")
    if not isinstance(iterator, str) or iterator not in {"exhaustive", "dichotomic"}:
        raise ValueError("iterator must be 'exhaustive' or 'dichotomic'.")
    if isinstance(depth, bool) or not isinstance(depth, int) or depth < 1:
        raise ValueError("depth must be a positive integer.")
    if seed is not None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("seed must be an integer or null.")
        if seed < 0:
            raise ValueError("seed must be non-negative.")


def sequence_generator(**_parameters):
    """QScore sweeps graph sizes internally and is run as one BACQ protocol."""
    raise NotImplementedError(
        "QScore performs its own graph-size search; use a BACQ 'protocol' input, not 'protocol_seq'."
    )
