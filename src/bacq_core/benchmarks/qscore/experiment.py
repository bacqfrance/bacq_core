"""Run QScore using myQLM simulators."""

import math
import os
from numbers import Integral, Real
from tempfile import TemporaryDirectory
from pathlib import Path

from . import annealing
from .helpers_protocol import check_parameters_value


_QAOA_DEVICES = {"CLinalg", "MPS", "MyQLMEmulator"}
_SUPPORTED_DEVICES = _QAOA_DEVICES | {
    "QutipQPU",
    "AnalogQPU",
    "SQAQPU",
    "SimulatedAnnealing",
    "MPSTraj",
}


def _qaptiva_local():
    """True when QAPTIVA_LOCAL=true: import from qat.* on a Qaptiva machine."""
    return os.environ.get("QAPTIVA_LOCAL", "").strip().lower() == "true"


def _build_clinalg_qpu():
    from qat.clinalg import CLinalg
    from qat.vsolve.optimize import ScipyMinimizePlugin

    return ScipyMinimizePlugin(
        method="COBYLA",
        tol=1e-4,
        options={"maxiter": 300},
    ) | CLinalg()


def _build_qaptiva_variational_qpu(device, params=None):
    params = params or {}
    bond_dimension = params.get("mps_bond_dimension", 16)
    if (
        isinstance(bond_dimension, bool)
        or not isinstance(bond_dimension, Integral)
        or bond_dimension < 1
    ):
        raise ValueError("mps_bond_dimension must be a positive integer.")
    try:
        if _qaptiva_local():
            from qat.plugins import ScipyMinimizePlugin
            from qat.qpus import MPS
        else:
            from qlmaas.plugins import ScipyMinimizePlugin
            from qlmaas.qpus import MPS
    except ImportError as error:
        raise ImportError(
            f"{device} requires QLMaaS configuration and myQLM's QLMaaS QPUs."
        ) from error

    optimizer = ScipyMinimizePlugin(
        method="COBYLA",
        tol=1e-4,
        options={"maxiter": 300},
    )
    qpu_kwargs = {}
    if "mps_bond_dimension" in params or device == "MPS":
        qpu_kwargs["bond_dimension"] = int(bond_dimension)
    return optimizer | MPS(**qpu_kwargs)


def _build_qaptiva_mpstraj_qpu(params):
    steps = params.get("mpstraj_steps", 50)
    bond_dimension = params.get("mpstraj_bond_dimension", 32)
    for name, value in (("mpstraj_steps", steps), ("mpstraj_bond_dimension", bond_dimension)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer.")
    try:
        if _qaptiva_local():
            from qat.qpus import MPSTraj
        else:
            from qlmaas.qpus import MPSTraj
    except ImportError as error:
        raise ImportError(
            "MPSTraj requires a configured QLMaaS MPSTraj QPU."
        ) from error
    return MPSTraj(n_steps=steps, bond_dimension=bond_dimension, seed=params["seed"])


def _build_qaptiva_annealing_qpu(device, params):
    try:
        if _qaptiva_local():
            from qat.qpus import AnalogQPU, SQAQPU
        else:
            from qlmaas.qpus import AnalogQPU, SQAQPU
    except ImportError as error:
        raise ImportError(
            f"{device} requires QLMaaS configuration and myQLM's QLMaaS QPUs."
        ) from error

    if device == "AnalogQPU":
        steps = params.get("analog_steps", 50)
        if isinstance(steps, bool) or not isinstance(steps, Integral) or steps < 1:
            raise ValueError("analog_steps must be a positive integer.")
        return AnalogQPU(n_steps=int(steps))

    from qat.core.variables import Variable

    steps = params.get("sqa_steps", 50)
    trotters = params.get("sqa_trotters", 8)
    for name, value in (("sqa_steps", steps), ("sqa_trotters", trotters)):
        if isinstance(value, bool) or not isinstance(value, Integral) or value < 1:
            raise ValueError(f"{name} must be a positive integer.")
    tmax = params.get("sqa_tmax", annealing._ANNEALING_TIME)
    temp_min = params.get("sqa_temp_min", 0.1)
    temp_max = params.get("sqa_temp_max", 5.0)
    for name, value in (("sqa_tmax", tmax), ("sqa_temp_min", temp_min),
                        ("sqa_temp_max", temp_max)):
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"{name} must be a finite positive number.")
    if temp_max <= temp_min:
        raise ValueError("sqa_temp_max must be greater than sqa_temp_min.")
    time = Variable("t", float)
    tau = time / tmax
    temp_t = temp_min * tau + temp_max * (1 - tau)
    return SQAQPU(
        temp_t=temp_t,
        n_steps=int(steps),
        n_trotters=int(trotters),
    )


def _build_qutip_qpu(params):
    steps = params.get("qutip_steps", 100)
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        raise ValueError("qutip_steps must be a positive integer.")
    try:
        from qat.analog.qutip_qpu import QutipQPU
    except ImportError as error:
        raise ImportError(
            "QutipQPU requires myQLM's analog/Qutip simulator dependencies."
        ) from error
    return QutipQPU(n_steps=steps)


def _build_simulated_annealing_qpu(params, seed):
    from qat.core.variables import Variable
    from qat.simulated_annealing import SimulatedAnnealing

    steps = params.get("annealing_steps", 50)
    temperature_min = params.get("temperature_min", 0.1)
    temperature_max = params.get("temperature_max", 5.0)
    shots = params.get("shots", annealing._DEFAULT_SHOTS)
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        raise ValueError("annealing_steps must be a positive integer.")
    if isinstance(shots, bool) or not isinstance(shots, int) or shots < 1:
        raise ValueError("shots must be a positive integer.")
    if (
        isinstance(temperature_min, bool)
        or not isinstance(temperature_min, (int, float))
        or not math.isfinite(temperature_min)
        or temperature_min <= 0
    ):
        raise ValueError("temperature_min must be a finite positive number.")
    if (
        isinstance(temperature_max, bool)
        or not isinstance(temperature_max, (int, float))
        or not math.isfinite(temperature_max)
        or temperature_max <= temperature_min
    ):
        raise ValueError(
            "temperature_max must be finite and greater than temperature_min."
        )
    time = Variable("t", float)
    temperature = temperature_min * time + temperature_max * (1 - time)
    return SimulatedAnnealing(temp_t=temperature, n_steps=steps, seed=seed)


def _new_qscore(qpu, **kwargs):
    from qat.qscore.benchmark import QScore

    return QScore(qpu, **kwargs)


def _run_annealing(device, params):
    evolution_time = annealing._ANNEALING_TIME
    if device == "QutipQPU":
        qpu = _build_qutip_qpu(params)
        algorithm = "aqo"
        evolution_time = params.get("qutip_tmax", 5.0)
    elif device == "MPSTraj":
        qpu = _build_qaptiva_mpstraj_qpu(params)
        algorithm = "mpstraj"
        evolution_time = params.get("mpstraj_tmax", 5.0)
    elif device in {"AnalogQPU", "SQAQPU"}:
        qpu = _build_qaptiva_annealing_qpu(device, params)
        algorithm = "aqo" if device == "AnalogQPU" else "sqa"
        evolution_time = (
            params.get("analog_tmax", 5.0)
            if device == "AnalogQPU"
            else params.get("sqa_tmax", annealing._ANNEALING_TIME)
        )
    else:
        qpu = _build_simulated_annealing_qpu(params, params["seed"])
        algorithm = "sa"
    gamma_t = None
    if device == "SQAQPU":
        from qat.core.variables import Variable

        gamma_min = params.get("sqa_gamma_min", 0.1)
        gamma_max = params.get("sqa_gamma_max", 1.0)
        for name, value in (("sqa_gamma_min", gamma_min), ("sqa_gamma_max", gamma_max)):
            if (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError(f"{name} must be a finite positive number.")
        time = Variable("t", float)
        tau = time / evolution_time
        gamma_t = gamma_min * tau + gamma_max * (1 - tau)
    return annealing.run(
        qpu,
        algorithm,
        initial_size=params["initial_size"],
        size_limit=params["size_limit"],
        beta=params["beta"],
        iterator=params["iterator"],
        seed=params["seed"],
        shots=params.get("shots", annealing._DEFAULT_SHOTS),
        aqo_time=evolution_time,
        gamma_t=gamma_t,
    )


def run(device, **params):
    """Run QScore with its QAOA core or one of the supported annealers."""
    if device not in _SUPPORTED_DEVICES:
        raise NotImplementedError(
            f"Unsupported QScore device {device!r}. "
            f"Choose one of {sorted(_SUPPORTED_DEVICES)}."
        )

    initial_size = params["initial_size"]
    size_limit = params["size_limit"]
    beta = params["beta"]
    iterator = params["iterator"]
    depth = params["depth"]
    seed = params["seed"]
    check_parameters_value(initial_size, size_limit, beta, iterator, depth, seed)

    if device in _QAOA_DEVICES:
        if device == "MPS":
            bond_dimension = params.get("mps_bond_dimension", 16)
            if (
                isinstance(bond_dimension, bool)
                or not isinstance(bond_dimension, Integral)
                or bond_dimension < 1
            ):
                raise ValueError("mps_bond_dimension must be a positive integer.")
        if device == "CLinalg":
            qpu = _build_clinalg_qpu()
        elif device == "MyQLMEmulator":
            from bacq_core.hardware.myqlm_emulator import build_backend

            qpu = build_backend()
        else:
            qpu = _build_qaptiva_variational_qpu(device, params)
        with TemporaryDirectory(prefix="bacq-qscore-") as output_dir:
            output_path = Path(output_dir)
            report = _new_qscore(
                qpu,
                initial_size=initial_size,
                size_limit=size_limit,
                beta=beta,
                iterator=iterator,
                depth=depth,
                output=str(output_path / "qscore.csv"),
                rawdata=str(output_path / "qscore.raw"),
                seed=seed,
            ).run()

        required_report_fields = {
            "status", "value", "beta", "evaluations", "raw_data"
        }
        if not isinstance(report, dict) or not required_report_fields.issubset(report):
            raise RuntimeError(
                "The installed qat-qscore version does not expose structured "
                "run results. Install the updated myqlm-compatibility-updates branch."
            )
    else:
        report = _run_annealing(device, params)

    run_parameters = {
        "initial_size": initial_size,
        "size_limit": size_limit,
        "beta": float(beta),
        "iterator": iterator,
        "depth": depth,
        "seed": seed,
    }
    if device in {"MPSTraj", "SimulatedAnnealing", "SQAQPU"}:
        run_parameters["score_method"] = "expected_cut"
    if device == "QutipQPU":
        run_parameters["qutip_steps"] = params.get("qutip_steps", 100)
        run_parameters["qutip_tmax"] = params.get("qutip_tmax", 5.0)
    elif device == "MPSTraj":
        run_parameters.update(
            mpstraj_steps=params.get("mpstraj_steps", 50),
            mpstraj_bond_dimension=params.get("mpstraj_bond_dimension", 32),
            mpstraj_tmax=params.get("mpstraj_tmax", 5.0),
            shots=params.get("shots", annealing._DEFAULT_SHOTS),
        )
    elif device == "SimulatedAnnealing":
        run_parameters.update(
            annealing_steps=params.get("annealing_steps", 50),
            shots=params.get("shots", annealing._DEFAULT_SHOTS),
            temperature_min=params.get("temperature_min", 0.1),
            temperature_max=params.get("temperature_max", 5.0),
        )
    elif device == "SQAQPU":
        run_parameters.update(
            shots=params.get("shots", annealing._DEFAULT_SHOTS),
            sqa_steps=params.get("sqa_steps", 50),
            sqa_trotters=params.get("sqa_trotters", 8),
            sqa_temp_min=params.get("sqa_temp_min", 0.1),
            sqa_temp_max=params.get("sqa_temp_max", 5.0),
            sqa_gamma_min=params.get("sqa_gamma_min", 0.1),
            sqa_gamma_max=params.get("sqa_gamma_max", 1.0),
            sqa_tmax=params.get("sqa_tmax", annealing._ANNEALING_TIME),
        )
    elif device == "AnalogQPU":
        run_parameters.update(
            analog_steps=params.get("analog_steps", 50),
            analog_tmax=params.get("analog_tmax", 5.0),
        )
    elif device == "MPS":
        run_parameters["mps_bond_dimension"] = params.get(
            "mps_bond_dimension", 16
        )

    return {
        "filetype": "experiment",
        "benchmark": "qscore",
        "device": device,
        "parameters": run_parameters,
        "result": report,
    }
