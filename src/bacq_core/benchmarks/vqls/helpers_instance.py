"""
Noe Olivier -- July 2026

Defines functions to construct the linear system problem instance.
"""

import numpy as np


def get_matrix_A(num_qubits):
    """
    Returns the 1D Poisson matrix from finite differences discretization.
    """
    A = np.zeros((2**num_qubits, 2**num_qubits))
    i = np.arange(2**num_qubits)
    A[i, i] = 2
    A[i[:-1], i[1:]] = -1
    A[i[1:], i[:-1]] = -1

    return A


def get_vector_b(num_qubits, V, uniform=False):
    """
    Return the b vector for the discretized 1D Poisson equation.
    """
    if V == 0:
        raise ValueError(f"Vector b cannot be the zero vector: consider another value for V, or a uniform b.")
    if uniform:
        return np.ones(2**num_qubits) * V
    else:
        b = np.zeros(2**num_qubits)
        b[0] = V
    return b


def get_normalized_vector_b(num_qubits, V, uniform=False):
    """
    Constructs the normalized b vector.
    """
    b = get_vector_b(num_qubits, V, uniform)
    return b / np.linalg.norm(b)
