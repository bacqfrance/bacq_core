# Metric-Noise-Resource (MNR) Benchmark: Energetic cost of VQE
This folder includes BACQ-EP-MNR-specific scripts.

Reference paper (algorithmic layer): (preprint) <https://arxiv.org/abs/2606.20153>
Reference report: BACQ deliverable D3.2, *Algorithmic efficiency optimization for VQE, and relation to energetic performance of digital quantum computers* (CNRS, 2026).
Reference code (full energetic stack, including the device campaigns): <https://github.com/hvermaQ/VQE>

## The Heisenberg spin chain
The benchmark estimates the ground-state energy of the isotropic Heisenberg spin-1/2 chain with open boundary conditions,

```math
H = \sum_{i=1}^{n-1} \left( X_iX_{i+1} + Y_iY_{i+1} + Z_iZ_{i+1} \right),
```

with the variational quantum eigensolver (VQE), using the Hamiltonian variational ansatz (6 parameters per layer) and the COBYLA optimizer.
The error of the algorithm is $\delta E = E_\text{VQE} - E_\text{gs}$, with $E_\text{gs}$ obtained by exact diagonalization.

## Metrics definition and Score evaluation
The benchmark relates the accuracy reachable on a device to the energy needed to reach it, through four layers:

1. **Algorithmic layer.** VQE is run on the device emulator over several ansatz depths and random initializations, without noise, with the device noise, and with error mitigation (zero-noise extrapolation by gate folding, and Pauli twirling). A phenomenological convergence model is fitted,
```math
E(N_g, N_{it}) = (1-\epsilon_\text{eff})^{N_g} \left[ \alpha\, e^{-\mu_0 N_{it} (N_g - N_g^{th})^{-\lambda}} + \beta\, e^{-\kappa N_g} + E_\text{gs} \right],
```
where $N_g$ is the number of gate operations (two-qubit gates count twice), $N_{it}$ the number of optimizer iterations, and $\epsilon_\text{eff}$ the effective depolarizing rate extracted from the mitigated noise floor.
2. **Classical layer.** The classical optimizer cost per iteration, $a L^b$ FLOPs for $L$ ansatz layers (measured with hardware performance counters, see reference code), is converted to Joules with the classical efficiency $\zeta_c$ (Green500).
3. **Hardware layer.** The dressed energy of a gate operation $E^*_\text{gate}$ is the minimal energy, over the line attenuation and the gate time, of driving a gate through a multi-stage dilution refrigerator, subject to the gate error $\epsilon_\text{eff}$ (superconducting full-stack model, dynamic energy only).
4. **Composition.** The total energy at a target accuracy is minimized over the operating point,
```math
E_\text{total}(\delta E) = \min_{N_g} N_{it}(N_g, \delta E) \left[ N_g N_\text{shots} N_\text{meas} E^*_\text{gate} + \frac{a L(N_g)^b}{\zeta_c} \right].
```

The benchmark reports two costs at a fixed accuracy: the total algorithmic cost (layer 1 only, hardware-agnostic) and the energy (layers 1 to 4).
The figure of merit is:
- $\delta E_\text{min}$, the minimal error reachable on the device,
- $\Delta_\text{min}$, the minimal algorithmic resource $\Delta = N_g N_{it}$ to reach the accuracy `floor_margin` $\times\, \delta E_\text{min}$, with its operating point $(N_{it}, N_g)$,
- $E_\text{min}$, the minimal total energy to reach the same accuracy, with its operating point $(N_{it}, N_g)$.

The minima are taken just above $\delta E_\text{min}$, since $N_{it}$, and with it the resource and the energy, diverges at the floor itself.
The resource-error and energy-error curves at `target_multipliers` $\times\, \delta E_\text{min}$ are also returned, to compare devices at common accuracies.
The least-resource and least-energy operating points differ when the classical optimizer cost is a significant share of the energy.

The optimal circuit depth $L^*$ is the circuit size $N_g^\text{opt}$ reaching $\delta E_\text{min}$, expressed in ansatz layers of the device.
If $L^* < 1$, the optimal circuit is shallower than the shallowest executable circuit: no algorithmic optimization is possible on the device, and neither $\Delta_\text{min}$ nor $E_\text{min}$ is evaluated (only $\epsilon_\text{eff}$ and $\delta E_\text{min}$ are reported).
No success criterion and no score are defined at the level of this benchmark (`success` is `None`): the figure of merit is reported as is, and its thresholding or aggregation is left to the context in which the benchmark is called.
The benchmark is defined for a single problem size, so it is run from `protocol` and `experiment` input files only.

### Parameters
Experiment parameters: `n`, `layers`, `num_seeds`, `max_iters`, `tol`, `num_shots`, `zne_scale_factors`, `num_twirls`.

Evaluation parameters (`meta`, they can be changed to re-evaluate existing experiment data): `mu_fit_window`, `alpha`, `energy_shots`, `classical_efficiency`, `flops_prefactor`, `flops_exponent`, `cryo_efficiency`, `stage_temperatures`, `attenuation_range_db`, `gate_time_range_ns`, `floor_margin`, `target_multipliers`.

The noiseless runs use the abstract (logical) circuit, while the raw and mitigated runs use the circuit transpiled onto the device.
Transpilation preserves the circuit unitary, so the noiseless energies of the transpiled circuit coincide with the logical ones to numerical precision ($\sim 10^{-14}$): only the gate count $N_g$, taken from the transpiled circuit, is device-specific.

The convergence rate of each trajectory is fitted over its first `mu_fit_window` $\times L$ iterations (the full trajectory if `null`), as deeper circuits converge more slowly; D3.2 uses 25 for the Hamiltonian variational ansatz.
The amplitude $\alpha$ is fitted from the trajectories if `alpha` is `null`, or fixed to the given value (D3.2 keeps the fiducial $\alpha = 2$, as do the example files, which therefore reproduce the D3.2 figures of merit).

The device calibration (relaxation rate $1/T_1$, gate times, qubit frequency) is read from the device and stored in the experiment data.
When the device does not report the qubit frequency, a nominal 5 GHz is used (`freq_nominal: true`).

### Scope and limitations
- One problem size, one Hamiltonian, one ansatz, one optimizer.
- The hardware layer models a superconducting processor only, and its dynamic energy only (static loads of the control electronics and of the refrigerator are excluded). Energies are therefore lower bounds.
- Two-qubit gates are charged twice the energy of a single-qubit gate, consistently with their weight in $N_g$.
- The minimum of the hardware layer may lie at a bound of `attenuation_range_db` or `gate_time_range_ns`: the reported control parameters indicate it.

## Code structure
Some files are required for all benchmarks so that these benchmarks can be successfully evaluated and experiments successfully conducted.
- `__init__.py`: defines benchmark-specific protocol parameters (here MNR) based on the benchmark-agnostic parameter class.
- `evaluate.py`: defines functions used to access metric computation from the package of the specific benchmark (here MNR): it fits the convergence model, finds the least algorithmic resource and composes the energetic figure of merit (layers 1, 2 and 4).
- `experiment.py`: defines a global `run()` function, a global structure for experiment data, and ensures the benchmark-specific protocol (here MNR) is well applied.
- `view.py`: defines the global string formatted to display the results of the specific benchmark (here MNR).

Additional benchmark-specific files are proposed:
- `helpers_instance.py`: defines the Heisenberg Hamiltonian, its exact ground energy and its number of measurement groups.
- `helpers_energy.py`: defines the energetic model of the superconducting quantum computer (layer 3).
- `helpers_protocol.py`: defines functions to ensure the MNR protocol is well applied.
- `helpers_qiskit.py`: defines functions to build the ansatz circuit, select the qubit chain, and apply gate folding, Pauli twirling and zero-noise extrapolation using qiskit.

## How to use within the BACQ library
This folder proposes an implementation on qiskit emulators of IBM devices, which carry the noise model and calibration data of the device (fake backends): `FakeMarrakesh` and `FakeNighthawk`, and on IBM devices (`hardware/ibm_realdevice.py`).
On a device, the runtime error mitigation is switched off (resilience level 0, no twirling), so that the benchmark protocol alone sets the mitigation.

The protocol is costly on a device, since the raw and mitigated VQE runs optimize under the device noise with one job per optimizer iteration: the D3.2 campaign (6 layers, 20 seeds) amounts to about $8\times10^4$ sequential jobs, $2\times10^6$ circuit executions and $2\times10^9$ shots, of the order of 100 hours of QPU time. A warning is issued when it is run on a real device.
An interrupted run resumes from the last completed number of layers, saved in `checkpoint_mnr_<device>.json`.
The noiseless `AerSimulator` is not accepted, since the benchmark needs a device noise model.
Qiskit notes that the error properties of `FakeNighthawk` are not intended to represent typical Nighthawk values.

**Run benchmark experiments on already implemented emulators** (several hours to days, depending on the number of CPU cores; seeds run in parallel):
1) ensure the `.json` input file contains `"benchmark": "mnr"`.
2) ensure the `.json` input file includes `"device": <device_name>`, e.g. `"FakeMarrakesh"`.
3) from a terminal
```bash
python3 src/bacq_core/main.py protocol_mnr.json
```

**Evaluate existing experiment data** (seconds):
```bash
python3 src/bacq_core/main.py expdata_mnr.json
```

**Run benchmark experiments on a new IBM emulator:**
1) ensure the `.json` input file contains `"benchmark": "mnr"`.
2) ensure the `.json` input file includes `"device": <device_name>`.
3) add `<device_name>` to the list of available IBM simulators in `hardware/ibm_simulator.py`.

**Run benchmark experiments on a device from a new provider:**
1) ensure the `.json` input file contains `"benchmark": "mnr"`.
2) ensure the `.json` input file includes `"device": <device_name>`.
3) create a new file `hardware/newprovider_simulator.py` on the example of `hardware/ibm_simulator.py`:
	-	include a list of available emulators (with `<device_name>`),
	-	include a new class (i.e. `NewProviderSimulator()`) exposing the device noise model and calibration data,
	-	defines an `estimate()` method returning the expectation values of transpiled circuits.
4) adapt the `experiment.py` file:
	-	in `run()`: initialize the hardware class for the newly available emulator,
	-	**(if necessary)** create a new `run_newsoftwarestack()` function based on the `run_qiskit()` example,
	-	**(if necessary)** create a new file `helpers_newsoftwarestack.py` to construct the algorithm using this new software stack while ensuring the protocol requirements are met.

*Note*: the hardware layer of the energetic figure of merit models a superconducting processor. For another modality, $\delta E_\text{min}$ and $\Delta_\text{min}$ remain valid, while $E_\text{min}$ requires a hardware energy model of its own in `helpers_energy.py`.

## Author
Harshit VERMA, CNRS, MajuLab, Singapore
