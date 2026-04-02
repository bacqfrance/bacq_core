## Code structure
This folder includes the source code of the package.

Folder `benchmarks`: includes a list of benchmark-specific folders that contains scripts to 
- initialise protocol parameters,
- check the validity of input parameters,
- construct problem instances,
- design accepted quantum algorithms,
- run experiments on accepted devices
- compute metric/success/score from the independent benchmark repository,
- display benchmark results.

Folder `hardware`: includes scripts that define how to access real QPU, emulators or simulators based on the hardware provider, and how the jobs are run on the platform (e.g. one job for one circuit, or one job for a series of circuit).

**Note:** access to real QPU is done by the end user, no runtime is provided via the usage of this package.

The Python scripts in this folder are independent of the benchmark to evaluate. They propose a structure defined by:
- `main.py`: entry-point script, to run a complete benchmark evaluation based on a json input file located in `../../examples`,
- `parameters.py`: defines an abstract class for protocol parameters which is general to all benchmarks,
- `registry.py`: lists and provides access to the different available benchmark modules in `benchmarks`,
- `runner.py`: describes how to run the computations (and experiments) based on the input data, and defines the format of the benchmark results.

## How to use
To run a specific benchmark protocol on a specific device based on the input file `protocol_seq_benchmarkname.json`, the end user can execute the command line (assuming they are located in the current directory):
```bash
python3 main.py protocol_seq_benchmarkname.json
```