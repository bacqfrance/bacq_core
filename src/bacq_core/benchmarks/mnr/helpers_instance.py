"""
Harshit Verma -- October 2026

Defines functions to construct the spin-chain problem instance.
"""

import numpy as np
from qiskit.quantum_info import SparsePauliOp


def get_heisenberg_hamiltonian(num_qubits):
    """
    Returns the isotropic Heisenberg spin-1/2 chain with open boundary conditions,
    H = sum_i (X_i X_{i+1} + Y_i Y_{i+1} + Z_i Z_{i+1}).
    """
    paulis, coeffs = [], []
    for i in range(num_qubits - 1):
        for p in ("XX", "YY", "ZZ"):
            paulis.append("I" * i + p + "I" * (num_qubits - i - 2))
            coeffs.append(1.0)

    return SparsePauliOp(paulis, coeffs)


def get_ground_energy(num_qubits):
    """
    Returns the exact ground-state energy of the Heisenberg chain (exact diagonalization).
    """
    H = get_heisenberg_hamiltonian(num_qubits).to_matrix()
    return float(np.linalg.eigvalsh(H)[0])


def get_num_measurement_groups(num_qubits):
    """
    Returns the number of qubit-wise commuting Pauli groups (XX, YY, ZZ) measured per energy evaluation.
    """
    return len(get_heisenberg_hamiltonian(num_qubits).group_commuting(qubit_wise=True))
