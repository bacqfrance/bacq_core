"""
Noe Olivier -- July 2026

Define how to evaluate a VQLS experiment.
"""
import sys
import numpy as np

from .helpers_instance import get_matrix_A, get_normalized_vector_b


def get_metric(exp_data):
    """
    """
    result = exp_data["result"]
    num_shots_solution = exp_data["parameters"]["num_shots_solution"]

    return compute_metric(result, num_shots_solution)


def compute_metric(result, num_shots_solution):
    """
    Computes VQLS metric, i.e. state fidelity.
    """
    counts = result["counts"]
    num_qubits = len(next(iter(counts)))

    ## Construct classical reference solution vector
    A_matrix = get_matrix_A(num_qubits)
    b_vector = get_normalized_vector_b(num_qubits, V=2, uniform=True)
    sol_classical = np.linalg.solve(A_matrix, b_vector)
    sol_classical = sol_classical / np.linalg.norm(sol_classical)

    ## Construct quantum solution vector
    sol_quantum = np.zeros(2**num_qubits)
    for k in range(len(sol_quantum)):
        bitstring = "{0:b}".format(k).zfill(num_qubits)
        sol_quantum[k] = np.sqrt(counts[bitstring] / num_shots_solution)
    
    ## Compute fidelity
    metric_fidelity = np.abs(np.dot(sol_quantum, sol_classical))**2    
    
    return float(metric_fidelity)


def get_metric_success(exp_data):
    """
    """
    metric = get_metric(exp_data)
    success = compute_success(metric, exp_data["result"]["opt_res"])

    return metric, success


def compute_success(metric, opt_res):
    """
    Compares observed fidelity with benchmark threshold fidelity criteria (arbitrary).
    """
    fidelity_threshold = 0.95

    if not opt_res["success"]:
        return False

    return metric >= fidelity_threshold


def get_score(exp_data):
    """
    """
    results = exp_data["results"]
    num_shots_solution = exp_data["parameters"]["num_shots_solution"]

    return compute_score(results, num_shots_solution, stop_on_fail=False)


def compute_score(results, num_shots_solution, stop_on_fail=False):
    """
    Evaluates BACQ-LS-VQLS, i.e. largest problem size successfully solved before first failure, and stores historical results.
    """
    history = {}
    failure = False
    score = 0

    for key, result in results.items():
        metric = compute_metric(result, num_shots_solution)
        success = compute_success(metric, result["opt_res"])

        history[key] = {
            "metric": metric,
            "success": success,
        }

        if success is False:
            failure = True
            if stop_on_fail is True:
                break

        if success is True and failure is False:
            score = key

    return history, score
