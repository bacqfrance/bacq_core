"""
Noe Olivier -- March 2026

Defines how to run an experiment for Quantum WalkScore
"""

from bacq_core.hardware.ibm_simulator import IBMSimulator
from bacq_core.hardware.ibm_realdevice import IBMRealDevice

from .helpers_qiskit import build_circuit_qiskit
from .helpers_instance import get_destination_states
from .helpers_protocol import check_parameters_value, compute_success_proba

def run(device, **params):
    """
    Run the protocol on the appropriate device and check parameters value.
    """
    graph_type = params["graph_type"]
    n = params["n"]
    d = params["d"]
    num_walk = params["num_walk"]
    num_aa = params["num_aa"]
    num_instances = params["num_instances"]
    num_shots = params["num_shots"]

    list_seq_params = params.get("seq_params", None)

    check_parameters_value(graph_type, n, d, num_walk, num_aa, num_instances, num_shots, list_seq_params)

    match device:
        case "BasicSimulator":
            hardware = IBMSimulator(device)
            results = run_qiskit(hardware, graph_type, n, d, num_walk, num_aa, num_instances, num_shots, list_seq_params)
        case "FakeMarrakesh":
            hardware = IBMSimulator(device)
            results = run_qiskit(hardware, graph_type, n, d, num_walk, num_aa, num_instances, num_shots, list_seq_params)
        case "ibm_sherbrooke":
            hardware = IBMRealDevice(device)
            results = run_qiskit(hardware, graph_type, n, d, num_walk, num_aa, num_instances, num_shots, list_seq_params)
        case "ibm_brisbane":
            hardware = IBMRealDevice(device)
            results = run_qiskit(hardware, graph_type, n, d, num_walk, num_aa, num_instances, num_shots, list_seq_params)
            
        case _:
            raise NotImplementedError(
                f"Benchmark QWS has not been implemented on {device=}."
            )

    return results


def run_qiskit(hardware, graph_type, n, d, num_walk, num_aa, num_instances, num_shots, list_seq_params=None):
    """
    Run experiment(s) on a qiskit simulator/emulator.

    Arguments:
        .hardware           -- IBMRealDevice or IBMSimulator
        .graph_type         -- str, type of graph
        .n                  -- int, number of qubits for the (first) experiment
        .d                  -- int, distance for the (first) experiment
        .num_walk           -- int or list[int], number of DTQW steps for each experiment
        .num_aa             -- int or list[int], number of AA iterations for each experiment
        .num_instances      -- int, number of instances for each experiment
        .num_shots          -- int, number of shots for each experiment
        .list_seq_params    -- list[dict], list of sequence parameters for each experiment

    Returns:
        .exp_data            -- dict, experiment(s) data to be stored in json file
    """
    if list_seq_params is None:
        
        destination_states, num_dims = get_destination_states(graph_type, n, d, num_instances)
        circuits = []
        for i in range(num_instances):
            circuit = build_circuit_qiskit(n, num_dims, num_walk, num_aa, destination_states[i])
            circuits.append(circuit)

        all_counts = hardware.compute(circuits, num_shots)

        tmp_result = {}
        for k, counts in enumerate(all_counts):
            state = destination_states[k]
            success_proba = compute_success_proba(counts, state, num_shots)
            if state not in tmp_result.keys():
                tmp_result[state] = [success_proba, 1]
            else:
                tmp_result[state][0] += success_proba
                tmp_result[state][1] += 1

        result = {state: tmp_result[state][0]/tmp_result[state][1] for state in tmp_result.keys()}

        exp_data = {
            "filetype": "experiment",
            "benchmark": "qws",
            "device": hardware.name,
            "parameters": {
                "graph_type": graph_type,
                "n": n,
                "d": d,
                "num_walk": num_walk,
                "num_aa": num_aa,
                "num_instances": num_instances,
                "num_shots": num_shots
            },
            "result": result
        }

        return exp_data

    else:

        n_walk = num_walk
        n_aa = num_aa
        results = {}

        for k, seq_params in enumerate(list_seq_params):
            
            n = seq_params["n"]
            d = seq_params["d"]


            if isinstance(num_walk, list):
                n_walk = num_walk[k]
            if isinstance(num_aa, list):
                n_aa = num_aa[k]

            #### TO CHECK: check get_dest_states is OK #######################
            destination_states, num_dims = get_destination_states(graph_type, n, d, num_instances)
            circuits = []

            for i in range(num_instances):
                circuit = build_circuit_qiskit(n, num_dims, n_walk, n_aa, destination_states[i])
                circuits.append(circuit)

            all_counts = hardware.compute(circuits, num_shots)

            tmp_result = {}
            for k, counts in enumerate(all_counts):
                state = destination_states[k]
                success_proba = compute_success_proba(counts, state, num_shots)
                if state not in tmp_result.keys():
                    tmp_result[state] = [success_proba, 1]
                else:
                    tmp_result[state][0] += success_proba
                    tmp_result[state][1] += 1

            pbm_size = '(' + str(n) +',' + str(d) + ')'
            results[pbm_size] = {state: tmp_result[state][0]/tmp_result[state][1] for state in tmp_result.keys()}
        
        exp_data_seq = {
            "filetype": "experiment_seq",
            "benchmark": "qws",
            "device": hardware.name,
            "parameters": {
                "graph_type": graph_type,
                "num_walk": num_walk,
                "num_aa": num_aa,
                "num_instances": num_instances,
                "num_shots": num_shots
            },
            "results": results
        }

        return exp_data_seq
