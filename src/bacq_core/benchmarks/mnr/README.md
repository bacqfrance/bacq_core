# Metric-Noise-Resource (MNR) Benchmark: Energetic cost of VQE
This folder includes BACQ-EP-MNR-specific scripts.

Reference paper (algorithmic layer): (preprint) <https://arxiv.org/abs/2606.20153>
Reference report: BACQ deliverable D3.2, *Algorithmic efficiency optimization for VQE, and relation to energetic performance of digital quantum computers* (CNRS, 2026).
Reference code (full energetic stack, including the device campaigns): <https://github.com/hvermaQ/VQE>

## The problem
The benchmark estimates the ground-state energy of the isotropic Heisenberg spin-1/2 chain with open boundary conditions,

```math
H = \sum_{i=1}^{n-1} \left( X_iX_{i+1} + Y_iY_{i+1} + Z_iZ_{i+1} \right),
```

with the variational quantum eigensolver (VQE), using the Hamiltonian variational ansatz (6 parameters per layer) and the COBYLA optimizer.
The error of the algorithm is $\delta E = E_\text{VQE} - E_\text{gs}$, with $E_\text{gs}$ obtained by exact diagonalization.

## Metric definition
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

The figure of merit is the pair:
- $\delta E_\text{min}$, the minimal error reachable on the device,
- $E_\text{min}$, the minimal total energy to reach the accuracy `floor_margin` $\times\, \delta E_\text{min}$.

The energy-error curve at `target_multipliers` $\times\, \delta E_\text{min}$ is also returned, to compare devices at common accuracies.

The optimal circuit depth $L^*$ is the circuit size $N_g^\text{opt}$ reaching $\delta E_\text{min}$, expressed in ansatz layers of the device.
If $L^* < 1$, the optimal circuit is shallower than the shallowest executable circuit: no algorithmic optimization is possible on the device, and the energetic figure of merit is not evaluated (only $\epsilon_\text{eff}$ and $\delta E_\text{min}$ are reported).
No success criterion and no score are defined yet: `success` is `None`.

## Parameters
Experiment parameters: `n`, `layers`, `num_seeds`, `max_iters`, `tol`, `num_shots`, `zne_scale_factors`, `num_twirls`.

Evaluation parameters (`meta`, they can be changed to re-evaluate existing experiment data): `mu_fit_window`, `alpha`, `energy_shots`, `classical_efficiency`, `flops_prefactor`, `flops_exponent`, `cryo_efficiency`, `stage_temperatures`, `attenuation_range_db`, `gate_time_range_ns`, `floor_margin`, `target_multipliers`.

The noiseless runs use the abstract (logical) circuit, while the raw and mitigated runs use the circuit transpiled onto the device.
Transpilation preserves the circuit unitary, so the noiseless energies of the transpiled circuit coincide with the logical ones to numerical precision ($\sim 10^{-14}$): only the gate count $N_g$, taken from the transpiled circuit, is device-specific.

The convergence rate of each trajectory is fitted over its first `mu_fit_window` $\times L$ iterations (the full trajectory if `null`), as deeper circuits converge more slowly; D3.2 uses 25 for the Hamiltonian variational ansatz.
The amplitude $\alpha$ is fitted from the trajectories if `alpha` is `null`, or fixed to the given value (D3.2 keeps the fiducial $\alpha = 2$).

The device calibration (relaxation rate $1/T_1$, gate times, qubit frequency) is read from the device and stored in the experiment data.
When the device does not report the qubit frequency, a nominal 5 GHz is used (`freq_nominal: true`).

## Code structure
- `__init__.py`: defines the protocol parameters.
- `evaluate.py`: fits the convergence model and composes the energetic figure of merit (layers 1, 2 and 4).
- `experiment.py`: defines the global `run()` function and the structure of experiment data.
- `view.py`: defines the formatted display of results.
- `helpers_instance.py`: Heisenberg Hamiltonian, exact ground energy, number of measurement groups.
- `helpers_energy.py`: energetic model of the superconducting quantum computer (layer 3).
- `helpers_protocol.py`: checks the protocol parameters.
- `helpers_qiskit.py`: ansatz circuit, qubit-chain selection, gate folding, Pauli twirling, zero-noise extrapolation.

## How to use within the BACQ library
Experiments run on the emulator of an IBM device (noise model and calibration data of a fake backend), e.g. `"device": "FakeMarrakesh"`.
They are not implemented on real devices: one experiment requires of the order of $10^5$ circuit executions of $10^3$ shots.
The noiseless `AerSimulator` is not accepted, since the benchmark needs a device noise model.

**Run the benchmark experiments** (several hours to days, depending on the number of CPU cores; seeds run in parallel):
```bash
python3 src/bacq_core/main.py protocol_mnr.json
```

**Evaluate existing experiment data** (seconds):
```bash
python3 src/bacq_core/main.py expdata_mnr.json
```

## Scope and limitations
- One problem size, one Hamiltonian, one ansatz, one optimizer.
- The hardware layer models a superconducting processor only, and its dynamic energy only (static loads of the control electronics and of the refrigerator are excluded). Energies are therefore lower bounds.
- Two-qubit gates are charged twice the energy of a single-qubit gate, consistently with their weight in $N_g$.
- The minimum of the hardware layer may lie at a bound of `attenuation_range_db` or `gate_time_range_ns`: the reported control parameters indicate it.

## Author
Harshit VERMA, CNRS, MajuLab, Singapore
