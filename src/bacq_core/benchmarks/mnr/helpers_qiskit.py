"""
Harshit Verma -- October 2026

Defines functions to build the VQE circuits and the error mitigation using qiskit
(Hamiltonian variational ansatz, qubit selection, gate folding, Pauli twirling, ZNE).
"""

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import ParameterVector
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary
from qiskit.circuit.library import RXXGate, RYYGate, RZZGate
from qiskit.transpiler import Layout, PassManager, generate_preset_pass_manager
from qiskit.transpiler.passes import BasisTranslator
from qiskit_aer.noise import NoiseModel

_NOMINAL_FREQUENCY = 5.0e9
SEED_TRANSPILER = 42


def build_hva_circuit(num_qubits, num_layers):
    """
    Hamiltonian variational ansatz for the Heisenberg chain: Neel-type reference state, then per layer
    RXX/RYY/RZZ rotations on odd then even bonds (6 variational parameters per layer).
    """
    params = ParameterVector("theta", 6 * num_layers)
    qc = QuantumCircuit(num_qubits)

    for q in range(num_qubits):
        qc.x(q)
    for q in range(0, num_qubits, 2):
        qc.h(q)
        if q + 1 < num_qubits:
            qc.cx(q, q + 1)

    for layer in range(num_layers):
        p = 6 * layer
        for first, offset in ((1, 0), (0, 3)):
            for q in range(first, num_qubits - 1, 2):
                qc.append(RXXGate(params[p + offset]), [q, q + 1])
                qc.append(RYYGate(params[p + offset + 1]), [q, q + 1])
                qc.append(RZZGate(params[p + offset + 2]), [q, q + 1])

    return qc


def count_gates(circuit):
    """
    Number of gate operations Ng: single-qubit gates count once, two-qubit gates count twice.
    """
    return sum(2 if inst.operation.num_qubits >= 2 else 1 for inst in circuit.data)


def get_edge_errors(backend):
    """
    Native two-qubit gate and its error on each (undirected) coupling of the device.
    """
    gates = backend.properties().to_dict().get("gates", [])
    names = {g["gate"] for g in gates if len(g["qubits"]) == 2}
    native = next((name for name in ("cx", "ecr", "cz", "rzz") if name in names), next(iter(names)))

    edges = {}
    for g in gates:
        if g["gate"] == native and len(g["qubits"]) == 2:
            a, b = g["qubits"]
            edges[(a, b)] = edges[(b, a)] = g["parameters"][0]["value"]

    return native, edges


def select_qubit_chain(backend, num_qubits):
    """
    Connected chain of qubits with the lowest summed two-qubit error (greedy extension from every start qubit).

    Returns:
        .chain  -- dict, selected qubits, native two-qubit gate, chain and device-mean two-qubit errors
    """
    native, edges = get_edge_errors(backend)
    neighbours = {}
    for (a, b), err in edges.items():
        neighbours.setdefault(a, []).append((err, b))
    for a in neighbours:
        neighbours[a].sort()

    best_path, best_err = None, np.inf
    for start in neighbours:
        path, err = [start], 0.0
        while len(path) < num_qubits:
            step = next(((w, b) for w, b in neighbours[path[-1]] if b not in path), None)
            if step is None:
                break
            err += step[0]
            path.append(step[1])
        if len(path) == num_qubits and err < best_err:
            best_path, best_err = path, err

    if best_path is None:
        raise ValueError(f"No connected chain of {num_qubits} qubits found on the device.")

    return {
        "selected_qubits": best_path,
        "native_2q": native,
        "chain_2q_error": float(best_err),
        "mean_2q_error": float(np.mean(list(edges.values()))),
    }


def get_device_params(backend):
    """
    Calibration constants of the device entering the energetic model: relaxation rate gamma = 1/T1 (median),
    median single- and two-qubit gate times, median qubit frequency (nominal 5 GHz if not reported).
    """
    target = backend.target
    t1 = [q.t1 for q in target.qubit_properties if q.t1]
    freqs = [q.frequency for q in target.qubit_properties if q.frequency]

    def median_duration(name):
        try:
            durations = [p.duration for p in target[name].values() if p and p.duration]
        except KeyError:
            return None
        return float(np.median(durations)) if durations else None

    tau_2q = [median_duration(name) for name in target.operation_names
              if getattr(target.operation_from_name(name), "num_qubits", 0) == 2]

    return {
        "T1_s": float(np.median(t1)),
        "gamma_hz": float(1 / np.median(t1)),
        "tau_1q_s": median_duration("sx") or median_duration("x"),
        "tau_2q_s": min((t for t in tau_2q if t), default=None),
        "freq_hz": float(np.median(freqs)) if freqs else _NOMINAL_FREQUENCY,
        "freq_nominal": not freqs,
    }


def get_layout_pass_manager(backend, num_qubits, selected_qubits, seed_transpiler=SEED_TRANSPILER):
    """
    Transpilation onto the fixed physical qubits of the selected chain.
    The transpiler seed is fixed, since the gate count Ng of the transpiled circuit enters the benchmark.
    """
    qr = QuantumRegister(num_qubits, "q")
    layout = Layout({qr[i]: q for i, q in enumerate(selected_qubits)})

    return generate_preset_pass_manager(
        backend=backend, optimization_level=3, layout_method="trivial",
        initial_layout=layout, qubits_initially_zero=True, seed_transpiler=seed_transpiler,
    )


def get_basis_gates(backend):
    """
    Basis gates of the device noise model (used after folding and twirling).
    """
    return sorted(set(NoiseModel.from_backend(backend).basis_gates) | {"id", "barrier"})


def get_basis_pass_manager(basis_gates):
    """
    Translation back to the device basis, without any other optimization (keeps folded gates).
    """
    return PassManager([BasisTranslator(SessionEquivalenceLibrary, list(basis_gates))])


def fold_gates(circuit, scale_factor):
    """
    Gate folding G -> G (G^dag G)^k amplifying the noise by an odd scale factor 2k+1.
    """
    k = (scale_factor - 1) // 2
    folded = QuantumCircuit(*circuit.qregs, *circuit.cregs)

    for inst in circuit.data:
        folded.append(inst)
        if inst.operation.name in ("barrier", "measure", "reset", "delay"):
            continue
        for _ in range(k):
            folded.append(inst.operation.inverse(), inst.qubits, inst.clbits)
            folded.append(inst.operation, inst.qubits, inst.clbits)

    return folded


_PAULI_BITS = {0: (0, 0), 1: (1, 0), 2: (1, 1), 3: (0, 1)}
_PAULI_INDEX = {bits: k for k, bits in _PAULI_BITS.items()}
_PAULI_GATE = {1: "x", 2: "y", 3: "z"}
_ECR_CONJUGATE = {
    (0, 0): (0, 0), (0, 1): (1, 2), (0, 2): (1, 1), (0, 3): (0, 3),
    (1, 0): (1, 0), (1, 1): (0, 2), (1, 2): (0, 1), (1, 3): (1, 3),
    (2, 0): (3, 3), (2, 1): (2, 1), (2, 2): (2, 2), (2, 3): (3, 0),
    (3, 0): (2, 3), (3, 1): (3, 1), (3, 2): (3, 2), (3, 3): (2, 0),
}


def conjugate_paulis(gate, p_c, p_t):
    """
    Paulis (q_c, q_t) such that (q_c x q_t) G (p_c x p_t) = G for the native two-qubit gate G.
    """
    (c_x, c_z), (t_x, t_z) = _PAULI_BITS[p_c], _PAULI_BITS[p_t]

    if gate == "cx":
        return _PAULI_INDEX[(c_x, c_z ^ t_z)], _PAULI_INDEX[(t_x ^ c_x, t_z)]
    if gate == "cz":
        return _PAULI_INDEX[(c_x, c_z ^ t_x)], _PAULI_INDEX[(t_x, t_z ^ c_x)]

    return _ECR_CONJUGATE[(p_c, p_t)]


def twirl_gates(circuit, rng):
    """
    Pauli twirling of the native two-qubit gates (cx, cz, ecr): the circuit unitary is unchanged,
    coherent two-qubit errors are converted into a stochastic Pauli channel.
    """
    twirled = QuantumCircuit(*circuit.qregs, *circuit.cregs)

    for inst in circuit.data:
        name = inst.operation.name
        if name not in ("cx", "cz", "ecr"):
            twirled.append(inst)
            continue

        q0, q1 = inst.qubits
        p_c, p_t = int(rng.integers(4)), int(rng.integers(4))
        q_c, q_t = conjugate_paulis(name, p_c, p_t)

        for pauli, qubit in ((p_c, q0), (p_t, q1)):
            if pauli:
                getattr(twirled, _PAULI_GATE[pauli])(qubit)
        twirled.append(inst)
        for pauli, qubit in ((q_c, q0), (q_t, q1)):
            if pauli:
                getattr(twirled, _PAULI_GATE[pauli])(qubit)

    return twirled


def estimate_mitigated_energy(hardware, basis_pm, circuit, observable, scale_factors, num_twirls, num_shots, rng):
    """
    Zero-noise extrapolated energy: the energy is estimated at each noise scale factor (averaged over
    Pauli-twirled instances), then linearly extrapolated to zero noise (Eq. 23 for scale factors {1, 3}).
    """
    pubs = []
    for c in scale_factors:
        folded = fold_gates(circuit, c)
        pubs += [(basis_pm.run(twirl_gates(folded, rng)), observable) for _ in range(num_twirls)]

    values = np.array(hardware.estimate(pubs, num_shots)).reshape(len(scale_factors), num_twirls).mean(axis=1)
    slope, intercept = np.polyfit(scale_factors, values, 1)

    return float(intercept)
