"""
Defines the general logic to run a benchmark.
"""

import json
from datetime import datetime
from registry import get_benchmark_module


def check_protocol_parameters(benchmark, parameters, sequence_parameters=None):
    """
    Checks that all required input parameters for a given benchmark protocol are given.
    """
    benchmark_module = get_benchmark_module(benchmark)

    if sequence_parameters is None:
        print(f"Parameters required for the benchmark {benchmark}:")
        for parameter in benchmark_module.parameters.values():
            print(f"- {parameter.name}: {parameter.description}")
        print()

        assert set(parameters.keys()) == set(
            param.name for param in benchmark_module.parameters.values()
            )

    else:
        print(f"Parameters required for the benchmark {benchmark}:")
        for parameter in benchmark_module.parameters.values():
            if parameter.sequence is False:
                print(f"- {parameter.name}: {parameter.description}")
        print()

        assert set(parameters.keys()) == set(
            param.name for param in benchmark_module.parameters.values() if param.sequence is False
            )

        print(f"Sequence parameters for the benchmark {benchmark}:")
        for parameter in benchmark_module.sequence_parameters.values():
            print(f"- {parameter.name}: {parameter.description}")
        print()

        assert set(sequence_parameters.keys()) == set(
            param.name for param in benchmark_module.sequence_parameters.values()
            )


def run_benchmark(benchmark, device, parameters, exp_data=None):
    """
    Runs the benchmark for a single experiment.

    Arguments:
        .benchmark      -- str, name of the benchmark protoool
        .device         -- str, name of the device
        .parameters     -- dict, contains all protocol parameters and values
        .exp_data       -- dict, content experiment data (if 'experiment' as input file)

    Returns:
        .benchmark_data     -- dict, content of the output benchmark 'result' file
    """
    benchmark_module = get_benchmark_module(benchmark)
    date = datetime.now().strftime("%Y-%m-%d_%Hh%M")

    meta_params = {
        k: v for k, v in parameters.items() if benchmark_module.parameters[k].meta is True
    }
    exp_params = {
        k: v for k, v in parameters.items() if benchmark_module.parameters[k].meta is False
    }

    if exp_data is None:

        exp_data = benchmark_module.run(device, **exp_params)

        exp_data["date"] = date
        exp_filename = "expdata_" + exp_data["benchmark"] + "_" + exp_data["device"] + "_" + exp_data["date"]
        with open(exp_filename + '.json', 'w') as f:
            json.dump(exp_data, f, indent=4)

    metric, success = benchmark_module.get_metric_success(exp_data, **meta_params)

    benchmark_data = {
        "filetype": "benchmark_data",
        "metadata": {
            "benchmark": benchmark,
            "device": device,
            "date": exp_data.get("date", date),
        },
        "results": {
            "metric": metric,
            "success": success,
        },
        "parameters": parameters,
    }

    return benchmark_data


def run_benchmark_sequence(benchmark, device, parameters, exp_data_seq=None, sequence_parameters=None):
    """
    Runs the benchmark for a series of experiments.

    Arguments:
        .benchmark              -- str, name of the benchmark protoool
        .device                 -- str, name of the device
        .parameters             -- dict, contains all protocol parameters and values
        .exp_data_seq           -- dict, content experiments data (if 'experiment_seq' as input file)
        .sequence_parameters    -- dict, contains variable parameters (if 'protocol_seq' as input file)

    Returns:
        .benchmark_seq_data     -- dict, content of the output benchmark 'results' file
    """
    benchmark_module = get_benchmark_module(benchmark)
    date = datetime.now().strftime("%Y-%m-%d_%Hh%M")

    exp_params = {
        k: v for k, v in parameters.items() if benchmark_module.parameters[k].meta is False
    }

    if exp_data_seq is None:
        list_seq_params = benchmark_module.sequence_generator(**sequence_parameters)

        exp_params = {**exp_params, **list_seq_params[0], "seq_params": list_seq_params}
        exp_data_seq = benchmark_module.run(device, **exp_params)

        exp_data_seq["date"] = date

        exp_seq_filename = "expdata_seq_" + exp_data_seq["benchmark"] + "_" + exp_data_seq["device"] + "_" + exp_data_seq["date"]
        with open(exp_seq_filename + '.json', 'w') as f:
            json.dump(exp_data_seq, f,indent=4)
        
        pass

    history, score = benchmark_module.get_score(exp_data_seq)
    benchmark_seq_data = {
        "filetype": "benchmark_seq_data",
        "metadata": {
            "benchmark": benchmark,
            "device": device,
            "date": exp_data_seq.get("date", date),
        },
        "results": {
            "history": history,
            "score": score,
        },
        "parameters": parameters,
    }

    return benchmark_seq_data


def display_text(benchmark, data):
    """
    Display the benchmark result.

    Arguments:
        .benchmark  -- str, name of the benchmark protocol
        .data       -- dict, contains benchmark result

    Returns:
        .text   -- str, formatted result text
    """
    benchmark_module = get_benchmark_module(benchmark)

    text_dict = {**data["metadata"], **data["results"], **data["parameters"]}
    text = benchmark_module.benchmark_txt.format(**text_dict)
    
    return text


def display_text_seq(benchmark, data):
    """
    Display the benchmark results.

    Arguments:
        .benchmark  -- str, name of the benchmark protocol
        .data       -- dict, contains benchmark results

    Returns:
        .text   -- str, formatted results text
    """
    benchmark_module = get_benchmark_module(benchmark)

    text = benchmark_module.benchmark_seq_txt.format(**data["metadata"], **data["parameters"])

    for key, result in data["results"]["history"].items():
        text += f"""
       - (n,d) = {key}: metric = {result['metric']:.3f} (test: {result['success']})
        """

    text += f"""
    Score = {data["results"]["score"]}
    """

    return text
