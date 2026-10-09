"""
Harshit Verma -- October 2026

Defines how to run an experiment for BACQ-EP-MNR (energetic cost of VQE).

For each number of ansatz layers, VQE is run from several random initializations in three ways:
noiseless (statevector), raw (device noise model) and mitigated (device noise model + ZNE + twirling).
"""

import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from qiskit.primitives import StatevectorEstimator
from scipy.optimize import minimize

from bacq_core.hardware.ibm_simulator import IBMSimulator, _IBM_SIMULATORS
from bacq_core.hardware.ibm_realdevice import _IBM_REAL_DEVICES

from .helpers_instance import get_heisenberg_hamiltonian, get_ground_energy
from .helpers_protocol import check_parameters_value
from .helpers_qiskit import build_hva_circuit, count_gates, select_qubit_chain, get_device_params
from .helpers_qiskit import get_layout_pass_manager, get_basis_gates, get_basis_pass_manager
from .helpers_qiskit import estimate_mitigated_energy, SEED_TRANSPILER

_NOISELESS_SIMULATORS = ["AerSimulator"]


def run(device, **params):
    """
    Run the protocol on the appropriate device and check parameters value.
    """
    num_qubits = params["n"]
    layers = params["layers"]
    num_seeds = params["num_seeds"]
    max_iters = params["max_iters"]
    tol = params["tol"]
    num_shots = params["num_shots"]
    zne_scale_factors = params["zne_scale_factors"]
    num_twirls = params["num_twirls"]

    check_parameters_value(num_qubits, layers, num_seeds, max_iters, tol, num_shots, zne_scale_factors, num_twirls)

    if device in _IBM_SIMULATORS and device not in _NOISELESS_SIMULATORS:
        hardware = IBMSimulator(device)
        results = run_qiskit(hardware, num_qubits, layers, num_seeds, max_iters, tol, num_shots, zne_scale_factors, num_twirls)
    elif device in _IBM_REAL_DEVICES:
        raise NotImplementedError(
            f"Benchmark MNR is not implemented on real devices: one experiment requires ~10^5 circuit executions of ~10^3 shots. Use the device emulator instead."
        )
    else:
        raise NotImplementedError(
            f"Benchmark MNR requires a device noise model and calibration data, not available for {device=}.\nCurrently available:\n{[d for d in _IBM_SIMULATORS if d not in _NOISELESS_SIMULATORS]}"
        )

    return results


def run_qiskit(hardware, num_qubits, layers, num_seeds, max_iters, tol, num_shots, zne_scale_factors, num_twirls):
    """
    Run the VQE experiments on a qiskit emulator of an IBM device.

    Arguments:
        .hardware           -- IBMSimulator, with a device noise model
        .num_qubits         -- int, number of qubits
        .layers             -- list(int), numbers of ansatz layers
        .num_seeds          -- int, number of random initializations per number of layers
        .max_iters          -- int, maximum number of COBYLA iterations
        .tol                -- float, COBYLA tolerance
        .num_shots          -- int, number of shots per energy estimation
        .zne_scale_factors  -- list(int), noise scale factors for zero-noise extrapolation
        .num_twirls         -- int, number of Pauli-twirled instances per scale factor

    Returns:
        .exp_data           -- dict, experiment data to be stored in json file
    """
    backend = hardware.device
    chain = select_qubit_chain(backend, num_qubits)
    layout_pm = get_layout_pass_manager(backend, num_qubits, chain["selected_qubits"])
    basis_gates = get_basis_gates(backend)
    hamiltonian = get_heisenberg_hamiltonian(num_qubits)

    print(f"Device {hardware.name}: qubits {chain['selected_qubits']}, native 2Q gate {chain['native_2q']}, "
          f"chain 2Q error {chain['chain_2q_error']:.3g} (device mean {chain['mean_2q_error']:.3g})")

    runs = {}
    for num_layers in layers:
        circuit = build_hva_circuit(num_qubits, num_layers)
        circuit_device = layout_pm.run(circuit)
        observable_device = hamiltonian.apply_layout(circuit_device.layout)

        tasks = {
            "noiseless": (circuit, hamiltonian),
            "raw": (circuit_device, observable_device),
            "mitigated": (circuit_device, observable_device),
        }
        run = {"Ng": count_gates(circuit_device)}

        for mode, (circ, obs) in tasks.items():
            start = time.time()
            args = [(mode, seed, hardware.name, circ, obs, basis_gates, max_iters, tol, num_shots, zne_scale_factors, num_twirls)
                    for seed in range(num_seeds)]
            with ProcessPoolExecutor(max_workers=min(num_seeds, os.cpu_count())) as pool:
                seed_runs = list(pool.map(run_seed, args))

            run[mode] = {
                "finals": [final for final, _ in seed_runs],
                "histories": [history for _, history in seed_runs],
                "runtime_s": time.time() - start,
            }

        print(f"layers = {num_layers} : Ng = {run['Ng']}, E_noiseless = {np.mean(run['noiseless']['finals']):.4f}, "
              f"E_raw = {np.mean(run['raw']['finals']):.4f}, E_mitigated = {np.mean(run['mitigated']['finals']):.4f} \tdone.")

        runs[str(num_layers)] = run

    result = {
        **chain,
        "seed_transpiler": SEED_TRANSPILER,
        "ground_energy": get_ground_energy(num_qubits),
        "device_params": get_device_params(backend),
        "layers": runs,
    }

    exp_data = {
        "filetype": "experiment",
        "benchmark": "mnr",
        "device": hardware.name,
        "parameters": {
            "n": num_qubits,
            "layers": layers,
            "num_seeds": num_seeds,
            "max_iters": max_iters,
            "tol": tol,
            "num_shots": num_shots,
            "zne_scale_factors": zne_scale_factors,
            "num_twirls": num_twirls,
        },
        "result": result,
    }

    return exp_data


def run_seed(args):
    """
    One VQE run (COBYLA) from a seeded random initialization.

    Returns:
        .(final, history) -- best energy found, and energy at each iteration
    """
    mode, seed, device, circuit, observable, basis_gates, max_iters, tol, num_shots, zne_scale_factors, num_twirls = args

    rng = np.random.default_rng(seed)
    init_params = 2 * np.pi * rng.random(circuit.num_parameters)

    if mode == "noiseless":
        estimator = StatevectorEstimator()
        def energy(params):
            job = estimator.run([(circuit.assign_parameters(params), observable)])
            return float(np.squeeze(job.result()[0].data.evs))

    elif mode == "raw":
        hardware = IBMSimulator(device)
        def energy(params):
            return hardware.estimate([(circuit.assign_parameters(params), observable)], num_shots)[0]

    else:
        hardware = IBMSimulator(device)
        basis_pm = get_basis_pass_manager(basis_gates)
        def energy(params):
            return estimate_mitigated_energy(hardware, basis_pm, circuit.assign_parameters(params), observable,
                                             zne_scale_factors, num_twirls, num_shots, rng)

    history = []
    def cost(params):
        e = energy(params)
        history.append(e)
        return e

    res = minimize(cost, init_params, method="COBYLA", bounds=[(0, 2 * np.pi)] * len(init_params),
                   options={"maxiter": max_iters, "tol": tol})

    return float(res.fun), history
