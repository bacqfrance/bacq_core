"""
Noe Olivier -- July 2026

Defines functions to build the circuit using qiskit.
"""

import numpy as np

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit import ParameterVector
from qiskit.quantum_info import SparsePauliOp, Operator

from bacq_core.hardware.ibm_simulator import IBMSimulator, _IBM_SIMULATORS
from bacq_core.hardware.ibm_realdevice import IBMRealDevice, _IBM_REAL_DEVICES

def matrix_to_sparsepauliop(matrix):
    """
    Convert a numpy matrix into sparse Pauli operators.
    """
    return SparsePauliOp.from_operator(Operator(matrix))


def build_ansatz_circuit(num_qubits, name, num_layers=1):
    """
    Build the circuit for the ansatz layer(s).
    Returns parameterized qiskit circuit and number of parameters.
    """
    qreg = QuantumRegister(num_qubits, name="qreg")
    circuit = QuantumCircuit(qreg)

    match name:
        case "custom":
            num_params = num_qubits * num_layers
            params = ParameterVector("theta", num_params)

            idx = 0
            for q in range(0, num_qubits):
                    circuit.h(q)
            
            for _ in range(0, num_layers):
                for q in range(0, num_qubits):
                    circuit.ry(params[idx], q)
                    idx += 1

            if idx != num_params:
                raise ValueError(f"{idx} params set but {num_params} params provided.")

            pass

        case "ansatz_4":
            '''
            Based on circuit 4 from (S.Sim et al., 2019) : https://doi.org/10.1002/qute.201900070
            '''
            num_params = (3 * num_qubits - 1)* num_layers
            params = ParameterVector("theta", num_params)

            idx = 0
            for _ in range(num_layers):
                
                for q in range(num_qubits):
                    circuit.rx(params[idx], q)
                    idx += 1
                    circuit.rz(params[idx], q)
                    idx += 1
                
                for q in range(num_qubits - 1):
                    circuit.cu(theta=params[idx], phi=-np.pi/2, lam=np.pi/2, gamma=0, control_qubit=q, target_qubit=q+1, label="Rx")
                    idx += 1

            if idx != num_params:
                raise ValueError(f"{idx} params set but {num_params} params provided.")
            
            pass

        case _:
            pass

    return circuit, num_params


def apply_controlled_Al(Al, circuit, inv=False):
    """
    Adds a controlled Al operator to the input circuit.
    """
    qreg = circuit.qregs[0]
    anc = circuit.qregs[1]

    if inv == False:
        for q, pauli_op in enumerate(Al):

            if pauli_op == "X":
                circuit.cx(anc, qreg[q])

            elif pauli_op == "Y":
                circuit.cy(anc, qreg[q])

            elif pauli_op == "Z":
                circuit.cz(anc, qreg[q])
    else:
        for q, pauli_op in reversed(list(enumerate(Al))):

            if pauli_op == "X":
                circuit.cx(anc, qreg[q])

            elif pauli_op == "Y":
                circuit.cy(anc, qreg[q])

            elif pauli_op == "Z":
                circuit.cz(anc, qreg[q])

    return circuit


def apply_Ub(b, circuit, inv=False):
    """
    Builds circuit to encode |b> = Ub|b>.
    Here, Ub = H^n for b = (a,a,...,a)^T (assumes b uniform)
    """
    for q in range(len(circuit.qregs[0])):
        circuit.h(q)

    return circuit


def local_hadamard_test_circuit(num_qubits, ansatz, Al=None, Alp=None, j=None, b=[], part=None):
    """
    Construct circuit for local Hadamard test used for the computation of local cost function CL.
    """
    circuit = ansatz.copy()

    anc = QuantumRegister(1, name="anc")
    creg = ClassicalRegister(1, name="cpos")

    circuit.add_register(anc)
    circuit.add_register(creg)
    
    qreg = circuit.qregs[0]

    ## Hadamard on ancilla
    circuit.h(anc)

    ## Phase gate
    if part == "Im":
        circuit.p(-np.pi / 2, anc)

    ## Add controlled Al operation
    circuit = apply_controlled_Al(Al, circuit, inv=True)

    ## Add (Ub_dag Zj Ub) operation
    if len(b)>0 and j is not None:
        circuit = apply_Ub(b, circuit, inv=True)
        circuit.cz(anc, qreg[j])
        circuit = apply_Ub(b, circuit, inv=False)

    ## Apply controlled Alp_dag operation
    circuit = apply_controlled_Al(Alp, circuit, inv=False)

    ## Hadamard on ancilla
    circuit.h(anc)

    ## Measurement
    circuit.measure(anc, creg)

    return circuit


def evaluate_local_cost(params, ansatz, A_operator, b_vector, hardware, optdata, num_shots=10000):
    """
    Constructs all circuits required for computation of local cost CL and evaluate CL on given hardware.
    """
    circuits_norm_real = []
    circuits_norm_imag = []
    circuits_mu_real = []
    circuits_mu_imag = []

    num_qubits = int(np.log2(len(b_vector)))

    ## Generate all circuits
    for l in range(0, len(A_operator.paulis)):
        Al = str(A_operator.paulis[l])
        
        for lp in range(0, len(A_operator.paulis)):
            Alp = str(A_operator.paulis[lp])
            clp = A_operator.coeffs[lp]

            circuit_norm_real = local_hadamard_test_circuit(num_qubits, ansatz, Al=Al, Alp=Alp, j=None, b=[], part="Re")
            circuit_norm_imag = local_hadamard_test_circuit(num_qubits, ansatz, Al=Al, Alp=Alp, j=None, b=[], part="Im")

            circuits_norm_real.append(circuit_norm_real)
            circuits_norm_imag.append(circuit_norm_imag)

            for j in range(0, num_qubits):
                circuit_mu_real = local_hadamard_test_circuit(num_qubits, ansatz, Al=Al, Alp=Alp, j=j, b=b_vector, part="Re")
                circuit_mu_imag = local_hadamard_test_circuit(num_qubits, ansatz, Al=Al, Alp=Alp, j=j, b=b_vector, part="Im")

                circuits_mu_real.append(circuit_mu_real)
                circuits_mu_imag.append(circuit_mu_imag)

    ## Run circuits in batches
    circuit_batches = [circuits_norm_real, circuits_norm_imag, circuits_mu_real, circuits_mu_imag]
    all_counts = hardware.compute_batches(circuit_batches, num_shots, params=params)

    ## Combine evaluation results to compute CL
    mu_sum = 0.0
    psi_norm = 0.0
    
    for l in range(0, len(A_operator.paulis)):
        cl = A_operator.coeffs[l]

        for lp in range(0, len(A_operator.paulis)):
            clp = A_operator.coeffs[lp]
            index_norm = lp + l * len(A_operator.paulis)

            for j in range(0, num_qubits):
                index_mu = j + lp * num_qubits + l * len(A_operator.paulis) * num_qubits

                ## Recover mu component value
                counts_real = all_counts[2][index_mu]
                counts_imag = all_counts[3][index_mu]

                counts_real = complete_counts_dict(counts_real, 1)
                counts_imag = complete_counts_dict(counts_imag, 1)

                mu_real = (counts_real["0"] - counts_real["1"])/num_shots
                mu_imag = (counts_imag["0"] - counts_imag["1"])/num_shots

                mu_sum += cl * np.conj(clp) * (mu_real + 1.0j * mu_imag)

            ## Recover psi norm component value
            counts_real = all_counts[0][index_norm]
            counts_imag = all_counts[1][index_norm]

            counts_real = complete_counts_dict(counts_real, 1)
            counts_imag = complete_counts_dict(counts_imag, 1)

            norm_real = (counts_real["0"] - counts_real["1"])/num_shots
            norm_imag = (counts_imag["0"] - counts_imag["1"])/num_shots

            psi_norm += cl * np.conj(clp) * (norm_real + 1.0j * norm_imag)

    mu_sum = abs(mu_sum)
    psi_norm = abs(psi_norm)

    ## Compute local cost CL
    cost = 0.5 - 0.5 * mu_sum / (num_qubits * psi_norm)

    ## Update optdata
    optdata["prev_params"] = params
    optdata["iters"] += 1
    optdata["cost_history"].append(cost)

    return cost


def get_opt_circuit(ansatz):
    """
    Constructs circuit for evaluation of solution state |x>
    """
    circuit = ansatz.copy()
    num_qubits = circuit.num_qubits
    
    creg = ClassicalRegister(num_qubits, name="cpos")
    circuit.add_register(creg)
    
    qreg = circuit.qregs[0]
    circuit.measure(qreg, creg)

    return circuit


def complete_counts_dict(counts, num_qubits):
    """
    Fills the counts dictionary with all non-sampled states.
    """
    for k in range(2 ** num_qubits):
        bitstring = "{0:b}".format(k).zfill(num_qubits)
        
        if bitstring not in counts.keys():
            counts[bitstring] = 0

    return counts
