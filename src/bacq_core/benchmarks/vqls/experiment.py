"""
Noe Olivier -- July 2026

Defines how to run an experiment for VQLS Benchmark
"""

import numpy as np
from scipy.optimize import minimize

from bacq_core.hardware.ibm_simulator import IBMSimulator, _IBM_SIMULATORS
from bacq_core.hardware.ibm_realdevice import IBMRealDevice, _IBM_REAL_DEVICES

from .helpers_qiskit import matrix_to_sparsepauliop, build_ansatz_circuit
from .helpers_qiskit import evaluate_local_cost
from .helpers_qiskit import get_opt_circuit, complete_counts_dict

from .helpers_instance import get_matrix_A, get_normalized_vector_b
from .helpers_protocol import check_parameters_value


def run(device, **params):
    """
    Run the protocol on the appropriate device and check parameters value.
    """
    num_qubits = params["n"]
    optimizer = params["optimizer"]
    max_iters = params["max_iters"]
    tol = params["tol"]
    ansatz = params["ansatz"]
    num_layers = params["num_layers"]
    num_shots = params["num_shots"]
    num_shots_solution = params["num_shots_solution"]

    list_seq_params = params.get("seq_params", None)

    check_parameters_value(num_qubits, optimizer, max_iters, tol, ansatz, num_layers, num_shots, num_shots_solution, list_seq_params)

    if device in _IBM_REAL_DEVICES:
        hardware = IBMRealDevice(device)
        results = run_qiskit(hardware, num_qubits, optimizer, max_iters, tol, ansatz, num_layers, num_shots, num_shots_solution, list_seq_params)
    elif device in _IBM_SIMULATORS:
        hardware = IBMSimulator(device)
        results = run_qiskit(hardware, num_qubits, optimizer, max_iters, tol, ansatz, num_layers, num_shots, num_shots_solution, list_seq_params)
    else:
        raise NotImplementedError(
            f"Benchmark VQLS is not currently implemented on {device=} : consider adding a new device.\nCurrently available:\n{_IBM_REAL_DEVICES=}\n{_IBM_SIMULATORS=}"
        )

    return results


def run_qiskit(hardware, num_qubits, optimizer, max_iters, tol, ansatz, num_layers, num_shots, num_shots_solution, list_seq_params=None):
    """
    Run experiment(s) on a qiskit simulator/emulator or IBM device.

    Arguments:
        .hardware           -- IBMRealDevice or IBMSimulator
        .num_qubits         -- int, number of qubits for the (first) experiment
        .optimizer          -- str, name of classical optimizer method
        .max_iters          -- int, maximum number of classical optimization iterations
        .tol                -- float, tolerance for optimization termination
        .ansatz             -- str, name of ansatz to consider
        .num_layers         -- int, number of ansatz layers
        .num_shots          -- int, number of shots for each circuit run in training
        .num_shots_solution -- int, number of shots for solution evaluation circuit
        .list_seq_params    -- list[dict], list of sequence parameters for each experiment

    Returns:
        .exp_data            -- dict, experiment(s) data to be stored in json file
    """
    if list_seq_params is None:
        
        ## Generate problem instance
        A_matrix = get_matrix_A(num_qubits)
        A_operator = matrix_to_sparsepauliop(A_matrix)
        b_vector = get_normalized_vector_b(num_qubits, V=2, uniform=True)
        
        ## Generate ansatz and parameters
        ansatz_circuit, num_params = build_ansatz_circuit(num_qubits, name=ansatz, num_layers=num_layers)
        init_params = 2 * np.pi * np.random.random(num_params)

        optimization_data = {
            "prev_params": None,
            "iters": 0,
            "cost_history": [],
        }

        ## Perform classical optimization
        res = minimize(
            evaluate_local_cost,
            init_params,
            args=(ansatz_circuit, A_operator, b_vector, hardware, optimization_data, num_shots),
            method=optimizer,
            tol=tol,
            options={"maxiter": max_iters},
        )

        opt_res = {
            "message": res.message,
            "success": res.success.item(),
            "status": res.status,
            "fun": res.fun.item(),
            "x": res.x.tolist(),
            "nfev": res.nfev,
            "maxcv": res.maxcv.item()
        }

        ## Evaluate quantum solution state
        opt_params = optimization_data["prev_params"]
        opt_circuit = get_opt_circuit(ansatz_circuit)
        counts = hardware.compute(opt_circuit, num_shots_solution, params=opt_params)
        counts = complete_counts_dict(counts[0], num_qubits)

        result = {
            "opt_res": opt_res,
            "counts": counts,
            "cost_history": optimization_data["cost_history"]
        }

        print(f"n = {num_qubits} : matrix size {A_matrix.shape} \tdone.")

        exp_data = {
            "filetype": "experiment",
            "benchmark": "vqls",
            "device": hardware.name,
            "parameters": {
                "n": num_qubits,
                "optimizer": optimizer,
                "max_iters": max_iters,
                "tol": tol,
                "ansatz": ansatz,
                "num_layers": num_layers,
                "num_shots": num_shots,
                "num_shots_solution": num_shots_solution
            },
            "result": result
        }

        return exp_data

    else:

        n_layers = num_layers
        m_iters = max_iters
        results = {}

        for k, seq_params in enumerate(list_seq_params):
            
            num_qubits = seq_params["n"]

            if isinstance(num_layers, list):
                n_layers = num_layers[k]
            if isinstance(max_iters, list):
                m_iters = max_iters[k]

            ## Generate problem instance
            A_matrix = get_matrix_A(num_qubits)
            A_operator = matrix_to_sparsepauliop(A_matrix)
            b_vector = get_normalized_vector_b(num_qubits, V=2, uniform=True)

            ## Generate ansatz and parameters
            ansatz_circuit, num_params = build_ansatz_circuit(num_qubits, name=ansatz, num_layers=n_layers)
            init_params = 2 * np.pi * np.random.random(num_params)

            optimization_data = {
                "prev_params": None,
                "iters": 0,
                "cost_history": [],
            }

            ## Perform classical optimization
            res = minimize(
                evaluate_local_cost,
                init_params,
                args=(ansatz_circuit, A_operator, b_vector, hardware, optimization_data, num_shots),
                method=optimizer,
                tol=tol,
                options={"maxiter": m_iters},
            )

            opt_res = {
                "message": res.message,
                "success": res.success.item(),
                "status": res.status,
                "fun": res.fun.item(),
                "x": res.x.tolist(),
                "nfev": res.nfev,
                "maxcv": res.maxcv.item()
            }

            ## Evaluate quantum solution state
            opt_params = optimization_data["prev_params"]
            opt_circuit = get_opt_circuit(ansatz_circuit)
            counts = hardware.compute(opt_circuit, num_shots_solution, params=opt_params)
            counts = complete_counts_dict(counts[0], num_qubits)
            
            result = {
                "opt_res": opt_res,
                "counts": counts,
                "cost_history": optimization_data["cost_history"]
            }

            print(f"n = {num_qubits} : matrix size {A_matrix.shape} \tdone.")

            results[num_qubits] = result
        
        exp_data_seq = {
            "filetype": "experiment_seq",
            "benchmark": "vqls",
            "device": hardware.name,
            "parameters": {
                "optimizer": optimizer,
                "max_iters": max_iters,
                "tol": tol,
                "ansatz": ansatz,
                "num_layers": num_layers,
                "num_shots": num_shots,
                "num_shots_solution": num_shots_solution
            },
            "results": results
        }

        return exp_data_seq
