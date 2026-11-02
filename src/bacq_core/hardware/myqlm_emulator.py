"""Build a QPU from myQLM's configured default simulator."""


def build_backend():
    """Return the QPU selected by myQLM's default-QPU configuration."""
    from qat.qpus import get_default_qpu

    return get_default_qpu()
