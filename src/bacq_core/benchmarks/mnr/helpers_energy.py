"""
Harshit Verma -- October 2026

Defines the energetic model of a superconducting quantum computer (BACQ D3.2, Sec. 5),
used to convert the algorithmic resources of VQE into Joules.

The control line descends a multi-stage dilution refrigerator. Attenuators suppress the
thermal photons reaching the qubit (lower gate error) but dissipate the drive power at
their own temperature, which costs refrigeration work (higher energy per gate).
"""

import numpy as np
from scipy import constants


def get_photon_energy(qubit_frequency):
    """
    Returns the qubit photon energy hbar*omega [J], with omega = 2*pi*f.
    """
    return constants.hbar * 2 * np.pi * qubit_frequency


def get_thermal_occupation(temperature, photon_energy):
    """
    Returns the Bose-Einstein occupation n_BE(T) at the qubit frequency.
    """
    return 1.0 / np.expm1(photon_energy / (constants.k * temperature))


def get_stage_attenuations(stage_temperatures, total_attenuation_db, photon_energy):
    """
    Distributes a total attenuation budget across the stages (coldest to warmest) following the
    reference-value rule of Krinner et al. (EPJ Quantum Technol. 6, 2 (2019)): each upper stage
    takes A_i = n_BE(T_{i+1}) / n_BE(T_i), and the base stage takes the remainder.

    Returns:
        .attenuations -- list(float), linear attenuations, or None if the budget is below the upper-stage requirement
    """
    T = stage_temperatures
    upper_db = [
        10 * np.log10(get_thermal_occupation(T[i + 1], photon_energy) / get_thermal_occupation(T[i], photon_energy))
        for i in range(1, len(T) - 1)
    ]
    base_db = total_attenuation_db - sum(upper_db)

    if base_db <= 0:
        return None

    return [10 ** (db / 10) for db in (base_db, *upper_db)]


def get_stage_terms(stage_temperatures, attenuations, photon_energy, cryo_efficiency):
    """
    Returns the thermal occupation seen by the qubit (Eq. 30) and the Carnot-weighted
    dissipation sum S of the drive line (Eq. 32).

    The drive power reaching the qubit stage is eventually dissipated as heat at that stage too,
    so the base increment is A_1 - 0 (Fellous-Asiani et al., PRX Quantum 4, 040319 (2023), Eq. B9).
    """
    T = stage_temperatures
    cum = np.cumprod([1.0, *attenuations])
    dissipated = np.diff(cum[1:], prepend=0.0)

    n_bar = get_thermal_occupation(T[0], photon_energy)
    carnot_sum = 0.0
    for i in range(1, len(T)):
        n_bar += (get_thermal_occupation(T[i], photon_energy) - get_thermal_occupation(T[i - 1], photon_energy)) / cum[i]
        carnot_sum += (T[-1] - T[i - 1]) / T[i - 1] * dissipated[i - 1]

    return n_bar, carnot_sum / cryo_efficiency


def get_optimal_gate_energy(gate_error, gamma, qubit_frequency, stage_temperatures, cryo_efficiency,
                            attenuation_range_db, gate_time_range_ns, resolution_db=0.01):
    """
    Minimal dressed energy of a gate operation subject to a target gate error (Eq. 34).

    The gate error gamma * tau_1 * (1 + n_bar(A)) is linear in the gate time tau_1, so the
    iso-fidelity line is solved exactly for tau_1 at each total attenuation A, and the energy
    E_1 = hbar*omega * pi^2 / (4 * gamma * tau_1) * S(A) is minimized over A.

    Arguments:
        .gate_error             -- float, target gate error (effective depolarizing rate eps_eff)
        .gamma                  -- float, spontaneous-emission rate 1/T1 [Hz]
        .qubit_frequency        -- float, qubit frequency [Hz]
        .stage_temperatures     -- list(float), fridge stage temperatures, coldest (qubit) to warmest [K]
        .cryo_efficiency        -- float, refrigeration efficiency as a fraction of the Carnot limit
        .attenuation_range_db   -- list(float), [min, max] total attenuation budget [dB]
        .gate_time_range_ns     -- list(float), [min, max] single-qubit gate time [ns]

    Returns:
        .optimum -- dict, minimal energy per gate [J] and the control parameters attaining it, or None if unreachable
    """
    photon_energy = get_photon_energy(qubit_frequency)
    tau_min, tau_max = (t * 1e-9 for t in gate_time_range_ns)

    optimum = None
    for total_db in np.arange(attenuation_range_db[0], attenuation_range_db[1] + resolution_db, resolution_db):
        attenuations = get_stage_attenuations(stage_temperatures, total_db, photon_energy)
        if attenuations is None:
            continue

        n_bar, carnot_sum = get_stage_terms(stage_temperatures, attenuations, photon_energy, cryo_efficiency)
        tau = gate_error / (gamma * (1 + n_bar))
        if not tau_min <= tau <= tau_max:
            continue

        energy = photon_energy * np.pi**2 / (4 * gamma * tau) * carnot_sum
        if optimum is None or energy < optimum["gate_energy"]:
            optimum = {
                "gate_energy": float(energy),
                "attenuation_db": float(total_db),
                "gate_time_ns": float(tau * 1e9),
                "thermal_occupation": float(n_bar),
            }

    return optimum
