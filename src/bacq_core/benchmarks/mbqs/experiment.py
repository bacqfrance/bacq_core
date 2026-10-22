"""
Grégoire Misguich -- October 2026

Defines how to run an experiment for the Many-Body Quantum Score
"""

from bacq_core.hardware.pulser_emulator import PulserEmulator, _PULSER_EMULATORS

from .helpers_pulser import build_sequence_pulser, check_device_options, _DEFAULT_A
from .helpers_protocol import check_parameters_value, check_counts, check_sample_num_shots


def run(device, **params):
    """
    Run the protocol on the appropriate device and check parameters value.

    The entries of params that are not protocol parameters are the device options
    (`device_options` entry of the input file).
    """
    state = params.pop("state")
    L = params.pop("L")
    threshold = params.pop("threshold")
    num_shots = params.pop("num_shots")

    list_seq_params = params.pop("seq_params", None)

    device_options = params

    check_parameters_value(state, L, threshold, num_shots, list_seq_params)

    if device in _PULSER_EMULATORS:
        check_device_options(device_options)
        a = device_options.get("a", _DEFAULT_A)

        hardware = PulserEmulator(device)
        results = run_pulser(hardware, state, L, threshold, num_shots, list_seq_params, a)
    else:
        raise NotImplementedError(
            f"Benchmark MBQS is not currently implemented on {device=} : consider adding a new device.\nCurrently available:\n{_PULSER_EMULATORS=}"
        )

    return results


def run_pulser(hardware, state, L, threshold, num_shots, list_seq_params=None, a=_DEFAULT_A):
    """
    Run experiment(s) on a Pulser emulator.

    The device options are recorded in the "device_options" entry of the experiment data,
    and the resulting neutral-atom settings in the "pulse" entry of each result.

    Arguments:
        .hardware           -- PulserEmulator
        .state              -- str, initial state
        .L                  -- int, number of qubits for the (first) experiment
        .threshold          -- float, threshold on the metric
        .num_shots          -- int, number of shots for each system size
        .list_seq_params    -- list[dict], list of sequence parameters for each experiment
        .a                  -- float, interatomic distance (µm), device option

    Returns:
        .exp_data            -- dict, experiment(s) data to be stored in json file
    """
    check_sample_num_shots(num_shots)
    if list_seq_params is None:
        sizes = [L]
    else:
        sizes = [seq_params["L"] for seq_params in list_seq_params]
    if not sizes:
        raise ValueError("The experiment sequence must not be empty.")

    sequences = []
    pulses = []
    for size in sizes:
        sequence, pulse = build_sequence_pulser(size, hardware.device_spec, state, a)
        sequences.append(sequence)
        pulses.append(pulse)

    all_counts = hardware.compute(sequences, num_shots)

    results = {}
    for size, counts, pulse in zip(sizes, all_counts, pulses, strict=True):
        check_counts(counts, size, num_shots)
        results[str(size)] = {"samples": counts, "pulse": pulse}

    parameters = {
        "state": state,
        "threshold": threshold,
        "num_shots": num_shots,
    }

    device_options = {"a": float(a)}

    if list_seq_params is None:

        exp_data = {
            "filetype": "experiment",
            "benchmark": "mbqs",
            "device": hardware.name,
            "device_options": device_options,
            "parameters": {**parameters, "L": L},
            "result": results[str(L)],
        }

        return exp_data

    else:

        exp_data_seq = {
            "filetype": "experiment_seq",
            "benchmark": "mbqs",
            "device": hardware.name,
            "device_options": device_options,
            "parameters": parameters,
            "results": results,
        }

        return exp_data_seq
