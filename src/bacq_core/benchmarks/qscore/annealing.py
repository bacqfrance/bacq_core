"""Run QScore's MaxCut size search with myQLM annealing QPUs."""

import math
import time
from numbers import Integral, Real

import networkx as nx
import numpy as np
from qat.opt import MaxCut
from qat.qscore.iterators import Driver

from .helpers_protocol import check_parameters_value


_NB_INSTANCES_PER_SIZE = 100
_ANNEALING_TIME = 1.0
_DEFAULT_SHOTS = 1024


def _state_bits(state, n_qubits):
    if isinstance(state, bool):
        raise TypeError("QPU sample state must not be a boolean.")
    if isinstance(state, Integral):
        integer_state = int(state)
        if integer_state < 0 or integer_state >= 1 << n_qubits:
            raise ValueError("QPU sample state is outside the graph's state space.")
        # QLM convention: qubit 0 is the most significant bit.
        return [(integer_state >> (n_qubits - 1 - index)) & 1 for index in range(n_qubits)]

    state_text = str(state).replace("|", "").replace(">", "").strip()
    if state_text.startswith("0b"):
        state_text = state_text[2:]
    if len(state_text) == n_qubits and set(state_text).issubset({"0", "1"}):
        return [int(bit) for bit in state_text]

    raise TypeError(f"Unsupported QPU sample state: {state!r}.")


def _cut_score(graph, state):
    bits = _state_bits(state, graph.number_of_nodes())
    return float(sum(bits[left] != bits[right] for left, right in graph.edges()))


def _mean_cut_score(graph, samples):
    """Compute the expected cut from a complete sampled distribution."""
    weighted_scores = []
    probabilities = []
    for sample in samples:
        probability = getattr(sample, "probability", None)
        if isinstance(probability, bool) or not isinstance(probability, Real):
            raise TypeError("QPU sample probability must be a real number.")
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("QPU sample probability must be finite and between 0 and 1.")
        probabilities.append(float(probability))
        weighted_scores.append(probability * _cut_score(graph, sample.state))
    if not probabilities:
        raise RuntimeError("Cannot compute a mean cut without samples.")
    total = math.fsum(probabilities)
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError(f"QPU sample probabilities must sum to 1; received {total}.")
    return float(math.fsum(weighted_scores) / total)


def _score_from_result(result, graph):
    value = getattr(result, "value", None)
    if value is not None:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError("QPU result value must be a real number or null.")
        if not math.isfinite(value):
            raise ValueError("QPU result value must be finite.")
        return float(-value)

    raw_data = getattr(result, "raw_data", None)
    if raw_data is None:
        raise RuntimeError("Annealing QPU result contains neither a value nor samples.")
    samples = list(raw_data)
    if not samples:
        raise RuntimeError("Annealing QPU returned no samples.")
    return _mean_cut_score(graph, samples)


def _make_job(
    problem, algorithm, shots, aqo_time=_ANNEALING_TIME, gamma_t=None
):
    if algorithm == "aqo":
        return problem.aqo_job(tmax=aqo_time, nbshots=0)
    if algorithm == "mpstraj":
        from qat.core import Observable, Schedule, Term
        from qat.core.variables import Variable

        problem_observable = problem.get_observable("terms")
        n_qubits = problem_observable.nbqbits
        # -sum(X) has |+...+> as ground state, as in MaxCut.aqo_job; with +sum(X)
        # the evolution would follow the highest-energy state to the minimum cut.
        mixing = Observable(
            n_qubits, pauli_terms=[Term(-1.0, "X", [index]) for index in range(n_qubits)]
        )
        tau = Variable("t", float) / aqo_time
        # MPSTraj needs numeric observable coefficients; keep time in the drive.
        schedule = Schedule(
            drive=[(1 - tau, mixing), (tau, problem_observable)], tmax=aqo_time
        )
        return schedule.to_job(
            job_type="SAMPLE", nbshots=shots, psi_0="+" * n_qubits
        )
    if algorithm == "sa":
        return problem.sqa_job(tmax=_ANNEALING_TIME, nbshots=shots)
    if algorithm == "sqa":
        if gamma_t is None:
            from qat.core.variables import Variable

            gamma_t = 1.0 - Variable("t", float)
        return problem.sqa_job(
            gamma_t=gamma_t,
            tmax=aqo_time,
            nbshots=shots,
        )
    raise ValueError(f"Unsupported annealing algorithm: {algorithm!r}.")


def run(
    qpu,
    algorithm,
    *,
    initial_size,
    size_limit,
    beta,
    iterator,
    seed,
    shots=_DEFAULT_SHOTS,
    aqo_time=_ANNEALING_TIME,
    gamma_t=None,
):
    """Execute the QScore size search with AQO, SA, SQA or analog SAMPLE jobs."""
    if not isinstance(algorithm, str) or algorithm not in {"aqo", "sa", "sqa", "mpstraj"}:
        raise ValueError(f"Unsupported annealing algorithm: {algorithm!r}.")
    check_parameters_value(initial_size, size_limit, beta, iterator, 1, seed)
    if algorithm in {"sa", "sqa", "mpstraj"} and (
        isinstance(shots, bool) or not isinstance(shots, Integral) or shots < 1
    ):
        raise ValueError("shots must be a positive integer.")
    if (
        isinstance(aqo_time, bool)
        or not isinstance(aqo_time, Real)
        or not math.isfinite(aqo_time)
        or aqo_time <= 0
    ):
        raise ValueError("aqo_time must be a finite positive number.")
    all_data = {}
    evaluations = {}
    next_seed = seed if seed is not None else int(np.random.randint(100000))

    def evaluate_size(size):
        nonlocal next_seed
        instances = []
        scores = []

        for _ in range(_NB_INSTANCES_PER_SIZE):
            current_seed = next_seed
            next_seed += 1
            graph = nx.generators.erdos_renyi_graph(size, 0.5, seed=current_seed)
            graph_seed = current_seed
            if algorithm in {"aqo", "mpstraj"} and graph.number_of_edges() == 0:
                retry_seed = current_seed
                for _ in range(10):
                    retry_seed += 1
                    graph = nx.generators.erdos_renyi_graph(
                        size, 0.5, seed=retry_seed
                    )
                    if graph.number_of_edges():
                        graph_seed = retry_seed
                        break
                else:
                    raise RuntimeError(
                        f"Could not generate a non-empty graph of size {size}."
                    )

            next_seed = max(next_seed, graph_seed + 1)
            problem = MaxCut(graph)
            job = _make_job(
                problem,
                algorithm,
                shots,
                aqo_time=aqo_time,
                gamma_t=gamma_t,
            )
            started = time.perf_counter()
            result = qpu.submit(job)
            if callable(getattr(result, "join", None)):
                result = result.join()
            score = _score_from_result(result, graph)
            duration = time.perf_counter() - started
            scores.append(score)
            instances.append(
                {"seed": graph_seed, "score": score, "duration_seconds": duration}
            )

        average_score = float(np.mean(scores) - size * (size - 1) / 8)
        random_best_score = float(0.178 * size ** 1.5)
        ratio = average_score / random_best_score
        all_data[size] = instances
        evaluations[size] = {
            "average_score": average_score,
            "random_best_score": random_best_score,
            "ratio": ratio,
            "success": ratio > beta,
            "instance_duration_sum": sum(row["duration_seconds"] for row in instances),
        }
        print(
            f"{algorithm.upper()} n={size}: score={average_score:.2f}, "
            f"random best={random_best_score:.2f}, ratio={ratio:.3f}"
        )
        return ratio - beta

    success, _, info = Driver(
        evaluate_size, iterator, initial_size, size_limit
    ).run()
    if success:
        status, value = "boundary", info
    elif info[0]:
        status, value = "above_limit", info[1]
    else:
        status, value = "below_initial", info[1]

    return {
        "status": status,
        "value": int(value),
        "beta": float(beta),
        "evaluations": evaluations,
        "raw_data": all_data,
    }
