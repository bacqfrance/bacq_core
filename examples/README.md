## Input files
The benchmark evaluation requires one input file, which can be the description of a protocol or the description of numerical/experimental results of a benchmark protocol.

In particular, this `examples` folder contains all types of input files for the benchmark evaluation:
- `protocol_benchmarkname.json`: benchmark protocol for evaluating a single problem size instance,
- `protocol_seq_benchmarkname.json`: benchmark protocol for evaluating a series of problem sizes instances,
- `expdata_benchmarkname.json`: experimental result for a single problem size instance,
- `expdata_seq_benchmarkname.json`: experimental results for a series of problem sizes instances.

The files provided here correspond to example files for the QWS benchmark on *IBM basic_simulator*.

The MNR files are different in kind. `protocol_mnr.json` is the full protocol of BACQ deliverable D3.2 on the *FakeMarrakesh* emulator, which runs for hours to days. `expdata_mnr.json` (about 11 MB) holds the data of that campaign: the noiseless, raw and mitigated VQE trajectories of every seed, from which the evaluation fits its convergence model. It is not a quick demonstration run, since a short MNR run does not converge to meaningful results.

## Files requirements
**1) Protocol input files**

In order to run the experiment and evaluate a metric (and success criteria) on a specific problem size instance, we use the `filetype: protocol` input file.
```json
{
    "filetype": "protocol",
    "benchmark": "benchmarkname",
    "device": "devicename",
    "parameters": {
        "param_1": "val_1",
        "param_2": "val_2",
        "param_3": "val_3"
    }
}
```

In order to run experiments and evaluate a metric (and success criteria) for a series of problem size instances, and obtain the score of the benchmark, we use the `filetype: protocol_seq` input file.
```json
{
    "filetype": "protocol_seq",
    "benchmark": "benchmarkname",
    "device": "devicename",
    "parameters": {
        "param_2": "val_2",
        "param_3": "val_3"
    },
    "sequence_parameters": {
        "param_1_min": "val_min",
        "param_1_max": "val_max"
    }
}
```

**Note**: please have a look at the documentation of the specific benchmark for the set of required parameters and their acceptable values.

**2) Experiment data input files**

In order to evaluate a metric (and success criteria) on a specific problem size instance, based on already existing experimental data, we use the `filetype: experiment` input file.
```json
{
    "filetype": "experiment",
    "benchmark": "benchmarkname",
    "device": "devicename",
    "parameters": {
        "param_1": "val_1",
        "param_2": "val_2",
        "param_3": "val_3"
    },
    "result": "result"
}
```

In order to evaluate a metric (and success criteria) for a series of problem size instances based on already existing experimental data, and obtain the score of the benchmark, we use the `filetype: experiment_seq` input file.
```json
{
    "filetype": "experiment_seq",
    "benchmark": "benchmarkname",
    "device": "devicename",
    "parameters": {
        "param_2": "val_2",
        "param_3": "val_3"
    },
    "results": {
        "param_1_min": "res_1",
        "param ...": "res ...",
        "param_1_i": "res_i",
        "param ...": "res ...",
        "param_1_max": "res_N"
    }
}
```

**Note**: please have a look at the documentation of the specific benchmark for the format of `result`.

## How to use the input file
First, add your input file (e.g. `my_input_file.json`) in this `examples` directory (or adapt an existing one). \
Then, from the terminal
```bash
python3 /path/to/bacq_core/main.py my_input_file.json
```
