"""
Harshit Verma -- October 2026

Defines how to display the BACQ-EP-MNR benchmark results.
"""

benchmark_txt = """
***** BACQ-EP-MNR (Energetic cost of VQE) *****
   _____________________________

Device: {device}
Date experiment: {date}
   _____________________________

Benchmark parameters:
- Problem: Heisenberg chain, {n} qubits, Hamiltonian variational ansatz
- Layers: {layers}
- Seeds per layer: {num_seeds}
- Classical optimizer: COBYLA (max iterations {max_iters}, tolerance {tol})
- Number of shots: {num_shots}
- Error mitigation: ZNE (scale factors {zne_scale_factors}) + Pauli twirling ({num_twirls} instances)
- Classical efficiency: {classical_efficiency:.3g} FLOP/J
- Refrigeration efficiency: {cryo_efficiency} x Carnot

Benchmark result:
- Effective noise: eps_eff = {metric[eps_eff]:.3g} (unmitigated: {metric[eps_raw]:.3g})
- {metric[message]}
- Convergence model ({metric[fit_settings]}): alpha = {metric[fit][alpha]:.3g}, mu0 = {metric[fit][mu0]:.3g}, lambda = {metric[fit][lam]:.3f}, Ng_th = {metric[fit][Ng_th]:.0f}
- Minimal error: dE_min = {metric[dE_min]:.3f}{metric[energy_report]}
- Success: {success}
___________________________________

"""

energy_txt = """
- Minimal energy at {floor_margin} x dE_min: E_min = {metric[E_min_J]:.3g} J ({metric[E_min_Wh]:.3g} Wh)
- Operating point: Nit = {metric[Nit]:.0f}, Ng = {metric[Ng]:.0f}
- Classical share of E_min: {metric[classical_share]:.1%}
- Energy per gate: {metric[gate][gate_energy]:.3g} J ({metric[gate][attenuation_db]:.1f} dB, {metric[gate][gate_time_ns]:.1f} ns)"""
