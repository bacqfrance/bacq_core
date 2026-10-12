"""
Harshit Verma -- October 2026

Defines how to run an experiment for BACQ-EP-MNR (energetic cost of VQE).

For each number of ansatz layers, VQE is run from several random initializations in three ways:
noiseless (statevector), raw (device noise) and mitigated (device noise + ZNE + twirling).
The raw and mitigated runs optimize under the device noise, on an emulator or on the device itself.
"""

import json
import os
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from qiskit.primitives import StatevectorEstimator
from scipy.optimize import minimize

from bacq_core.hardware.ibm_simulator import IBMSimulator, _IBM_SIMULATORS
from bacq_core.hardware.ibm_realdevice import IBMRealDevice, _IBM_REAL_DEVICES

from .helpers_instance import get_heisenberg_hamiltonian, get_ground_energy, get_num_measurement_groups
from .helpers_protocol import check_parameters_value
from .helpers_qiskit import build_hva_circuit, count_gates, select_qubit_chain, get_device_params
from .helpers_qiskit import get_layout_pass_manager, get_basis_gates, get_basis_pass_manager
from .helpers_qiskit import estimate_mitigated_energy, SEED_TRANSPILER

_NOISELESS_SIMULATORS = ["AerSimulator"]

## Device evaluations of the D3.2 campaign on FakeMarrakesh (6 layers, 20 seeds), for the cost warning
_FULL_CAMPAIGN_EVALUATIONS = {"raw": 36707, "mitigated": 39190}


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

    if device in _IBM_REAL_DEVICES:
        warn_device_cost(device, layers, num_seeds, zne_scale_factors, num_twirls, num_shots, num_qubits)
        hardware = IBMRealDevice(device)
    elif device in _IBM_SIMULATORS and device not in _NOISELESS_SIMULATORS:
        hardware = IBMSimulator(device)
    else:
        raise NotImplementedError(
            f"Benchmark MNR requires a device noise model and calibration data, not available for {device=}.\nCurrently available:\n"
            f"{[d for d in _IBM_SIMULATORS if d not in _NOISELESS_SIMULATORS]}\n{_IBM_REAL_DEVICES=}"
        )

    results = run_qiskit(hardware, num_qubits, layers, num_seeds, max_iters, tol, num_shots, zne_scale_factors, num_twirls)

    return results


def get_hardware(device):
    """
    Hardware class of a device name (instantiated in each worker process).
    """
    return IBMRealDevice(device) if device in _IBM_REAL_DEVICES else IBMSimulator(device)


def warn_device_cost(device, layers, num_seeds, zne_scale_factors, num_twirls, num_shots, num_qubits):
    """
    Warns that the protocol optimizes under the device noise, one device job per optimizer iteration.
    The scale is that of the D3.2 campaign, rescaled to the requested numbers of layers and seeds.
    """
    num_meas = get_num_measurement_groups(num_qubits)
    scale = len(layers) * num_seeds / (6 * 20)
    evaluations = {mode: count * scale for mode, count in _FULL_CAMPAIGN_EVALUATIONS.items()}
    circuits = num_meas * (evaluations["raw"] + evaluations["mitigated"] * len(zne_scale_factors) * num_twirls)

    warnings.warn(
        f"MNR protocol on the real device {device}: the raw and mitigated VQE runs optimize on the device, "
        f"with one job per optimizer iteration. At the scale of the D3.2 campaign this is about "
        f"{sum(evaluations.values()):.2g} sequential jobs, {circuits:.2g} circuit executions and {circuits * num_shots:.2g} shots "
        f"(of the order of 100 hours of QPU time for 6 layers and 20 seeds).",
        stacklevel=3,
    )


def run_qiskit(hardware, num_qubits, layers, num_seeds, max_iters, tol, num_shots, zne_scale_factors, num_twirls):
    """
    Run the VQE experiments on a qiskit emulator of an IBM device, or on the IBM device itself.

    Arguments:
        .hardware           -- IBMSimulator (with a device noise model) or IBMRealDevice
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

    parameters = {
        "n": num_qubits,
        "layers": layers,
        "num_seeds": num_seeds,
        "max_iters": max_iters,
        "tol": tol,
        "num_shots": num_shots,
        "zne_scale_factors": zne_scale_factors,
        "num_twirls": num_twirls,
    }
    checkpoint = f"checkpoint_mnr_{hardware.name}.json"
    runs = load_checkpoint(checkpoint, parameters, chain)

    for num_layers in layers:
        if str(num_layers) in runs:
            print(f"layers = {num_layers} : read from {checkpoint}.")
            continue

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
            run[mode] = run_seeds(mode, num_seeds, hardware.name, circ, obs, basis_gates,
                                  max_iters, tol, num_shots, zne_scale_factors, num_twirls)

        print(f"layers = {num_layers} : Ng = {run['Ng']}, E_noiseless = {np.mean(run['noiseless']['finals']):.4f}, "
              f"E_raw = {np.mean(run['raw']['finals']):.4f}, E_mitigated = {np.mean(run['mitigated']['finals']):.4f} \tdone.")

        runs[str(num_layers)] = run
        save_checkpoint(checkpoint, parameters, chain, runs)

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
        "parameters": parameters,
        "result": result,
    }

    if os.path.exists(checkpoint):
        os.remove(checkpoint)

    return exp_data


def run_seeds(mode, num_seeds, device, circuit, observable, basis_gates, max_iters, tol, num_shots, zne_scale_factors, num_twirls):
    """
    VQE runs from all random initializations, in parallel.
    """
    start = time.time()
    args = [(mode, seed, device, circuit, observable, basis_gates, max_iters, tol, num_shots, zne_scale_factors, num_twirls)
            for seed in range(num_seeds)]
    with ProcessPoolExecutor(max_workers=min(num_seeds, os.cpu_count())) as pool:
        seed_runs = list(pool.map(run_seed, args))

    return {
        "finals": [final for final, _ in seed_runs],
        "histories": [history for _, history in seed_runs],
        "runtime_s": time.time() - start,
    }


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
        hardware = get_hardware(device)
        def energy(params):
            return hardware.estimate([(circuit.assign_parameters(params), observable)], num_shots)[0]

    else:
        hardware = get_hardware(device)
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


def load_checkpoint(path, parameters, chain):
    """
    Completed layers of an interrupted run with the same parameters and qubit chain, if any.
    """
    if not os.path.exists(path):
        return {}

    with open(path) as f:
        saved = json.load(f)

    if saved["parameters"] != parameters or saved["selected_qubits"] != chain["selected_qubits"]:
        raise ValueError(f"Checkpoint {path} was produced with other parameters or qubits: remove it to start again.")

    return saved["layers"]


def save_checkpoint(path, parameters, chain, runs):
    """
    Saves the completed layers, so that an interrupted run (e.g. a failed device job) resumes from there.
    """
    with open(path, "w") as f:
        json.dump({"parameters": parameters, "selected_qubits": chain["selected_qubits"], "layers": runs}, f)
