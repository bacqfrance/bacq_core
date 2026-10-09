"""
Grégoire Misguich -- October 2026

Defines functions to build the MBQS quench as a Pulser sequence (neutral atoms).
Adapted from `notebooks/analog_rydberg_pulser.ipynb` in the `mbqs` repository.
"""

import pulser
from mbqs import MBQSProtocol, RydbergMapping
from mbqs.simulations.lattice import ring_coordinates

# Device options accepted for neutral-atom devices (`device_options` entry of the input file)
_DEVICE_OPTIONS = ["a"]

# Default interatomic distance (µm) on the ring, when the device option `a` is not given.
# It fixes the Ising coupling J, hence the amplitude, detuning and duration of the pulse,
# but not the score (which only depends on J t). Value of the `mbqs` Pulser notebook,
# valid for AnalogDevice.
_DEFAULT_A = 7.5


def check_device_options(device_options):
    """
    Checks names and values of the device options for neutral-atom devices.
    """
    unknown_options = [name for name in device_options if name not in _DEVICE_OPTIONS]
    if unknown_options:
        raise ValueError(f"Device options {unknown_options} not valid for neutral-atom devices: expected options among {_DEVICE_OPTIONS}.")

    if "a" in device_options:
        check_a(device_options["a"])


def check_a(a):
    """
    Checks type and value of the interatomic distance.
    """
    if not isinstance(a, (int, float)):
        raise TypeError("Device option a must be <float>.")

    if a <= 0:
        raise ValueError(f"Device option {a=} not valid: > 0 required.")


def build_sequence_pulser(L, device, state="down", a=_DEFAULT_A):
    """
    Build the Pulser sequence of the quench at the critical point for a ring of L atoms.

    Arguments:
        .L          -- int, number of atoms
        .device     -- pulser device specification (e.g. pulser.devices.AnalogDevice)
        .state      -- str, initial state
        .a          -- float, interatomic distance (µm)

    Returns:
        .sequence   -- pulser.Sequence
        .pulse      -- dict, physical parameters of the quench
    """
    if state != "down":
        raise NotImplementedError(
            f"Initial {state=} is not implemented on neutral atoms: only 'down' (all atoms in the ground state) is available."
        )

    mapping = RydbergMapping(L=L, a=a)
    protocol = MBQSProtocol(state=state, L=L, J=mapping.J)

    # Pulser durations are integers in ns, multiples of the channel clock period
    # (otherwise Pulser silently rounds them up)
    surge_time_ns = 1000 * protocol.surge_time
    clock_period = device.channels["rydberg_global"].clock_period
    duration = clock_period * round(surge_time_ns / clock_period)

    register = ring_register(device, L, a)

    sequence = pulser.Sequence(register, device)
    sequence.declare_channel("ising", "rydberg_global")
    sequence.enable_eom_mode("ising", amp_on=mapping.Omega, detuning_on=mapping.delta)
    sequence.add_eom_pulse("ising", duration=duration, phase=0.0)

    pulse = {
        "a": float(a),
        "J": float(mapping.J),
        "Omega": float(mapping.Omega),
        "delta": float(mapping.delta),
        "surge_time_ns": float(surge_time_ns),
        "duration_ns": duration,
        "Jt": float(mapping.J * duration / 1000),
    }

    return sequence, pulse


def ring_register(device, L, a):
    """
    Build a register of L atoms equally spaced on a ring, with interatomic distance a.
    """
    coords = ring_coordinates(L, a)
    register = pulser.Register.from_coordinates(coords, prefix="q")

    if device.requires_layout:
        register = register.with_automatic_layout(device, layout_slug=f"RingLayout({L}, {a}µm)")

    return register
