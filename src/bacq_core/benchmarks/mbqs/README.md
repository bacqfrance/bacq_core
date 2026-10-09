# Many-Body Quantum Score (MBQS) Benchmark
This folder includes MBQS-specific scripts. The protocol definition (surge time), the theoretical correlations, the metric and the score are provided by the [`mbqs`](https://github.com/HaroldErbin/mbqs) package, developed by Harold Erbin.

Reference paper : (preprint) <https://arxiv.org/abs/2601.03461>

## The quench problem
A ring of $L$ spins $\frac{1}{2}$ is initialized in a product state $\ket{\psi}$ ($\ket{\downarrow \cdots \downarrow}$ or $\ket{+ \cdots +}$) and evolved with the transverse-field Ising Hamiltonian at the critical point $g = 1$ for a duration $t_*(L)$, the "surge time" at which the antipodal connected 2-point function is maximum.
The spins are then measured in the $z$ basis, and the connected 2-point functions $g^{(2)}_i = \braket{\sigma^z_0 \sigma^z_i} - \braket{\sigma^z_0}\braket{\sigma^z_i}$ are estimated for $i = 1, \ldots, \lfloor L/2 \rfloor$ (averaged over translations).

## Metrics definition and Score evaluation
The metric is the mean relative error with respect to the exact values at the surge time:

```math
P_2(L) = \frac{1}{\lfloor L/2 \rfloor} \sum_{i=1}^{\lfloor L/2 \rfloor} \left| \frac{g^{(2)\,\text{th}}_i - g^{(2)\,\text{exp}}_i}{g^{(2)\,\text{th}}_i} \right|
```

When the data are bitstrings (or correlations with errors), an error $\delta P_2$ is propagated from the statistical errors. The test for a system size $L$ with threshold $\epsilon$ is:
- *success* if $P_2 + \delta P_2 < \epsilon$,
- *undecided* if $P_2 \le \epsilon \le P_2 + \delta P_2$,
- *failed* if $P_2 > \epsilon$.

Only *success* is reported as `success: True`. In the score history, each system size also records the error $\delta P_2$ as `metric_err` (0 for correlations given without errors) and the three-valued outcome as `status` (`"success"`, `"undecided"` or `"failed"`).

The score $\text{MBQS}_\psi$ is the largest system size $L$ such that the test is a success for all sizes up to $L$ in the sequence.

## Code structure
Required files (see the QWS benchmark for their role): `__init__.py`, `evaluate.py`, `experiment.py`, `view.py`.

Additional benchmark-specific files:
- `helpers_protocol.py`: defines functions to ensure the MBQS protocol is well applied.
- `helpers_pulser.py`: defines functions to build the quench as a Pulser sequence for neutral atoms (Rydberg Hamiltonian mapped to the critical Ising Hamiltonian, ring register, global EOM pulse). It also defines and checks the device options accepted for neutral-atom devices (see below).

Hardware: `hardware/pulser_emulator.py` defines the `QutipEmulator` and `MPSBackend` (requires the `[mbqs-mps]` optional dependencies, see below) emulators.

## How to use within the BACQ library
Install the optional dependencies (requires Python 3.12):
```bash
pip install -e '.[mbqs]'
```
To also use the `MPSBackend` emulator (tensor networks, for larger $L$), install instead:
```bash
pip install -e '.[mbqs-mps]'
```
This pulls PyTorch, which on Linux defaults to the CUDA build (several GB); for a CPU-only install, add `--extra-index-url https://download.pytorch.org/whl/cpu`.

**Protocol parameters** (independent of the hardware):
- `state`: `"down"` or `"plus"` (only `"down"` can be run on neutral atoms for now),
- `L`: number of qubits ($2 \le L \le 50$, range of the tabulated data), or `L_min`/`L_max` as sequence parameters,
- `threshold`: threshold $\epsilon$ on the metric,
- `num_shots`: number of shots per system size.

**Device options** (optional, hardware-specific): given in the `"device_options"` entry of the input file, not in `"parameters"`, e.g.
```json
"device_options": {"a": 7.5}
```
For neutral-atom devices (Pulser emulators), the only device option is:
- `a`: interatomic distance on the ring, in µm (default 7.5). It fixes the Ising coupling $J \propto a^{-6}$, hence $\Omega$, $\delta$ and the pulse duration, but not the score, which only depends on $J t$. It determines which sizes fit within the device constraints: on `AnalogDevice`, $L \le 27$ for $a = 7.5$ µm (maximum sequence duration), $L \le 39$ for $a = 6$ µm (maximum distance to the center of the array), while for $a = 5.5$ µm the amplitude $\Omega = 2J$ exceeds the device maximum.

Any other device option raises an error. The device options actually used are recorded in the `"device_options"` entry of the experiment data file.

**Experiment data:** the `result` for one size (or each entry of `results`, keyed by `L`) contains either
- `"samples"`: measured bitstrings of length $L$ and their counts, e.g. `{"0000": 812, ...}`, or
- `"correlations"`: connected 2-point functions $g^{(2)}_i$ for $i = 1, \ldots, \lfloor L/2 \rfloor$, with keys written exactly as `"(0, i)"` (with a space after the comma), e.g. `{"(0, 1)": 0.41, "(0, 2)": 0.36}` for $L = 4$ or $5$, and optionally `"correlations_err"`: their statistical errors, with the same keys.

In a sequence, all system sizes must use the same kind of data (all `"samples"` or all `"correlations"`).

Experiments run with Pulser also record the hardware-specific settings actually used in a `"pulse"` entry (`a`, `J`, `Omega`, `delta`, `surge_time_ns`, `duration_ns`, `Jt`). The pulse duration `duration_ns` is the surge time `surge_time_ns` rounded to the nearest multiple of the channel clock period (4 ns on `AnalogDevice`), and `Jt` is computed from `duration_ns`.

**Run benchmark experiments on an emulator:**
1) ensure the `.json` input file contains `"benchmark": "mbqs"`.
2) ensure the `.json` input file includes `"device": "QutipEmulator"` (or `"MPSBackend"`).
3) **(optional)** set the interatomic distance with `"device_options": {"a": <value>}`.

See `protocol_mbqs.json`, `protocol_seq_mbqs.json`, `expdata_mbqs.json` and `expdata_seq_mbqs.json` in `examples`. From the root of the repository, run for instance:
```bash
python3 src/bacq_core/main.py protocol_seq_mbqs.json   # run the experiments, then evaluate them
python3 src/bacq_core/main.py expdata_seq_mbqs.json    # evaluate existing experiment data
```
The input file is looked up in the `examples` folder, and the experiment data and results files are written in the current directory.

**Run benchmark experiments on a new Pulser emulator:**
1) ensure the `.json` input file contains `"benchmark": "mbqs"`.
2) ensure the `.json` input file includes `"device": <device_name>`.
3) add `<device_name>` to the list of available emulators in `hardware/pulser_emulator.py`, and the corresponding case in the `compute()` method.

**Run benchmark experiments on a device from a new provider:**
1) ensure the `.json` input file contains `"benchmark": "mbqs"`.
2) ensure the `.json` input file includes `"device": <device_name>`.
3) create a new file `hardware/newprovider_realdevice.py` on the example of existing files:
	-	include a list of available QPU (with `<device_name>`),
	-	include a new class (i.e. `NewProviderRealDevice()`),
	-	defines QPU access (authentification, etc.),
	-	defines a `compute()` method to manage job submissions, returning the measured bitstrings and counts for each job.
4) adapt the `experiment.py` file:
	-	in `run()`: initialize the hardware class for newly available QPU,
	-	**(if necessary)** define and check the device options accepted by this hardware, on the example of `check_device_options()` in `helpers_pulser.py`,
	-	**(if necessary)** create a new `run_newsoftwarestack()` function based on the `run_pulser()` example,
	-	**(if necessary)** create a new file `helpers_newsoftwarestack.py` to construct the quench using this new software stack while ensuring the protocol requirements are met (e.g. for a gate-based QPU, a Trotterized evolution with the critical Ising Hamiltonian up to the surge time given by `MBQSProtocol`).

In all cases, the bits of the measured bitstrings must follow the order of the qubits along the ring.

*Note*: Running experiments on real QPU requires that a QPU access can be established by the end-user.

## Authors
- `mbqs` package: Harold ERBIN
- Integration in BACQ: Grégoire MISGUICH
