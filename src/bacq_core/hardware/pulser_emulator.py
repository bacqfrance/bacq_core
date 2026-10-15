"""
Define the PulserEmulator device.

This emulates a neutral-atom analog device with Pulser, and returns only counts.
"""

from pulser.devices import AnalogDevice
from pulser_simulation import QutipEmulator

_PULSER_EMULATORS = [
    "QutipEmulator",
    "MPSBackend",
]


class PulserEmulator:
    def __init__(self, name="QutipEmulator", noise_model=None):
        """
        Define emulator selected for experiments.

        Arguments:
            .name           -- str, name of the emulator
            .noise_model    -- pulser.NoiseModel or None (noiseless emulation)
        """
        if name not in _PULSER_EMULATORS:
            raise NotImplementedError(
                f"Pulser emulator {name} is not available. Consider adding {name} to 'hardware/pulser_emulator.py' or choose an emulator from {_PULSER_EMULATORS}."
            )

        self.device_spec = AnalogDevice
        self.noise_model = noise_model
        self.name = name


    def compute(self, sequences, num_shots, dt=0.01, n_trajectories=10):
        """
        Run sequences on the emulator.

        Arguments:
            .sequences      -- single/list of pulser sequences
            .num_shots      -- int, number of shots per sequence
            .dt             -- float, time step (µs) for MPSBackend
            .n_trajectories -- int, number of trajectories for noisy emulation

        Returns:
            .all_counts -- list(dict), each experimental results as counts
        """
        all_counts = []

        if not isinstance(sequences, list):
            sequences = [sequences]

        for sequence in sequences:
            match self.name:
                case "QutipEmulator":
                    counts = self._run_qutip(sequence, num_shots, n_trajectories)
                case "MPSBackend":
                    counts = self._run_mps(sequence, num_shots, dt, n_trajectories)

            all_counts.append({bitstring: int(count) for bitstring, count in counts.items()})

        return all_counts


    def _run_qutip(self, sequence, num_shots, n_trajectories):
        """
        Exact state-vector (or Monte-Carlo with noise) emulation with qutip.
        """
        options = {}
        if self.noise_model is not None:
            options = {"noise_model": self.noise_model, "n_trajectories": n_trajectories}

        emulator = QutipEmulator.from_sequence(sequence, **options)
        result = emulator.run()

        return result.sample_final_state(N_samples=num_shots)


    def _run_mps(self, sequence, num_shots, dt, n_trajectories):
        """
        Tensor-network emulation with emu-mps (optional dependency).
        """
        import logging
        from emu_mps import BitStrings, MPSBackend, MPSConfig

        bitstrings = BitStrings(evaluation_times=[1.0], num_shots=num_shots)

        options = {}
        if self.noise_model is not None:
            options = {"noise_model": self.noise_model, "n_trajectories": n_trajectories}

        config = MPSConfig(
            dt=1000 * dt,
            observables=[bitstrings],
            max_bond_dim=256,
            precision=1e-3,
            log_level=logging.WARN,
            **options,
        )

        result = MPSBackend(sequence, config=config).run()

        return result.get_result(bitstrings, 1.0)
