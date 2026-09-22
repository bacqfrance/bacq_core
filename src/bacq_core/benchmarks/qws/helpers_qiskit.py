"""
Noe Olivier -- March 2026

Defines functions to build the circuit using qiskit.
"""

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

def build_circuit_qiskit(num_qubits, num_dims, num_walk, num_aa, marked_state, barrier=False):
    """
    Construct a qiskit circuit for DTQW + AA algorithm

    Arguments:
        .num_qubits     -- int, number of (position) qubits
        .num_dims       -- int, graph dimension, number of (coin) qubits
        .num_walk       -- int, number of discrete-time quantum walk steps
        .num_aa         -- int, number of amplitude amplification iterations
        .marked_state   -- str, bitstring of the state to amplify
        .barrier	-- bool, apply qiskit barrier in compilation or not

    Returns:
        .circuit        -- qiskit circuit
    """
    num_pos_qubits = num_dims * num_qubits
    num_coin_qubits = num_dims

    circuit = create_dtqw_circuit(num_pos_qubits, num_coin_qubits, num_walk, barrier)
    circuit_A = circuit
    circuit_A_inv = circuit_A.inverse()
    circuit_oracle = create_AA_oracle(num_pos_qubits, num_coin_qubits, marked_state)
    circuit_reflexion = create_AA_oracle(num_pos_qubits, num_coin_qubits, '0'*num_pos_qubits)

    for ii in range(0, num_aa):
        if barrier:
            circuit = circuit.compose(circuit_oracle)
            circuit.barrier()
            circuit = circuit.compose(circuit_A_inv)
            circuit.barrier()
            circuit = circuit.compose(circuit_reflexion)
            circuit.barrier()
            circuit = circuit.compose(circuit_A)
            circuit.barrier()
        else:
            circuit = circuit.compose(circuit_oracle)
            circuit = circuit.compose(circuit_A_inv)
            circuit = circuit.compose(circuit_reflexion)
            circuit = circuit.compose(circuit_A)

    circuit.measure([k for k in range(num_pos_qubits)], [k for k in range(num_pos_qubits)])

    return circuit


def create_dtqw_circuit(num_pos_qubits, num_coin_qubits, num_walk, barrier):
    """
    Construct a circuit for the discrete-time quantum walk subroutine (Hadamard coin)

    Arguments:
        .num_pos_qubits     -- int, number of qubits for position encoding
        .num_coin_qubits    -- int, number of qubits for coin encoding
        .num_walk           -- int, number of steps of the quantum walk
        .barrier            -- bool, include barriers in circuit construction

    Returns:
        .circuit            -- qiskit circuit
    """
    if num_coin_qubits == 1:
        shift_circuit = get_shift_1D(num_pos_qubits, num_coin_qubits, barrier)
    elif num_coin_qubits == 2:
        shift_circuit = get_shift_2D(num_pos_qubits, num_coin_qubits, barrier)

    qreg_pos = QuantumRegister(num_pos_qubits, name="pos")
    qreg_coin = QuantumRegister(num_coin_qubits, name="c")
    creg_pos = ClassicalRegister(num_pos_qubits, name="cpos")
    circuit = QuantumCircuit(qreg_pos, qreg_coin, creg_pos)

    pos_qubits = [k for k in range(num_pos_qubits)]
    coin_qubits = [num_pos_qubits + k for k in range(num_coin_qubits)]
     
    ## Initial state
    for q in coin_qubits:
        circuit.h(q)
    circuit.s(coin_qubits[0])

    if barrier:
        circuit.barrier()

    step = 1
    while step < num_walk+1:

        if step > 1:
            circuit.h(qreg_coin)

            if barrier:
                circuit.barrier()

        circuit = circuit.compose(shift_circuit, qubits=pos_qubits+coin_qubits)

        if barrier:
            circuit.barrier()

        step += 1

    return circuit


def get_shift_1D(num_pos_qubits, num_coin_qubits, barrier):
    """
    Construct a circuit for the discrete-time quantum walk shift operator (1D).
    Circuit based on increment/decrement implementation from (B.L. Douglas and J.B. Wang, 2009) : https://doi.org/10.1103/PhysRevA.79.052335

    Arguments:
        .num_pos_qubits     -- int, number of qubits for position encoding
        .num_coin_qubits    -- int, number of qubits for coin encoding
        .barrier            -- bool, include barriers in circuit construction

    Returns:
        .circuit            -- qiskit circuit
    """
    if num_coin_qubits != 1:
        raise ValueError(f"ERROR CIRCUIT CONSTRUCTION: 1 coin qubit expected, {num_coin_qubits} given.")

    pos_qubits = [k for k in range(num_pos_qubits)]
    coin_qubits = [num_pos_qubits]

    qreg_pos = QuantumRegister(num_pos_qubits, name='x')
    qreg_coin = QuantumRegister(num_coin_qubits, name='c')
    circuit = QuantumCircuit(qreg_pos, qreg_coin, name="S")

    ## Increment
    for n in range(num_pos_qubits-1, -1, -1):
        cur_pos_qubits = [k for k in range(n)]
        ctrl_qubits = coin_qubits + cur_pos_qubits
        circuit.x(coin_qubits)
        circuit.mcx(ctrl_qubits, [n])
        circuit.x(coin_qubits)

    if barrier:
        circuit.barrier()

    ## Decrement
    for n in range(num_pos_qubits-1, -1, -1):
        cur_pos_qubits = [k for k in range(n)]
        ctrl_qubits = coin_qubits + cur_pos_qubits
        if cur_pos_qubits != []:
            circuit.x(cur_pos_qubits)
            circuit.mcx(ctrl_qubits, [n])
            circuit.x(cur_pos_qubits)
        else:
            circuit.mcx(ctrl_qubits, [n])

    return circuit


def get_shift_2D(num_pos_qubits, num_coin_qubits, barrier):
    """
    Construct a circuit for the discrete-time quantum walk shift operator (2D)

    Arguments:
        .num_pos_qubits     -- int, number of qubits for position encoding
        .num_coin_qubits    -- int, number of qubits for coin encoding
        .barrier            -- bool, include barriers in circuit construction

    Returns:
        .circuit            -- qiskit circuit
    """
    if num_pos_qubits%2 != 0:
        raise ValueError(f"ERROR CIRCUIT CONSTRUCTION: nb x qubits != nb y qubits ({num_pos_qubits} divided by 2).")
    if num_coin_qubits != 2:
        raise ValueError(f"ERROR CIRCUIT CONSTRUCTION: 2 coin qubits expected, {num_coin_qubits} given.")

    num_qubits_x = num_pos_qubits//2
    num_qubits_y = num_pos_qubits - num_qubits_x

    pos_x_qubits = [k for k in range(num_qubits_x)]
    pos_y_qubits = [num_qubits_x + k for k in range(num_qubits_y)]
    coin_qubits = [num_pos_qubits + k for k in range(num_coin_qubits)]

    qreg_pos_x = QuantumRegister(num_qubits_x, name="x")
    qreg_pos_y = QuantumRegister(num_qubits_y, name="y")
    qreg_coin = QuantumRegister(num_coin_qubits, name="c")
    circuit = QuantumCircuit(qreg_pos_x, qreg_pos_y, qreg_coin, name="S")

    ## coin |11) : decrement y
    for n in range(num_qubits_y-1, -1, -1):
        pos_ctrl_qubits = pos_y_qubits[:n]
        ctrl_qubits = coin_qubits + pos_ctrl_qubits
        if pos_ctrl_qubits != []:
            circuit.x(pos_ctrl_qubits)
            circuit.mcx(ctrl_qubits, pos_y_qubits[n])
            circuit.x(pos_ctrl_qubits)
        else:
            circuit.mcx(ctrl_qubits, pos_y_qubits[n])

    if barrier:
        circuit.barrier()

    ## coin |10) : increment y
    circuit.x(coin_qubits[0])
    for n in range(num_qubits_y-1, -1, -1):
        ctrl_qubits = coin_qubits + pos_y_qubits[:n]
        circuit.mcx(ctrl_qubits, pos_y_qubits[n])

    if barrier:
        circuit.barrier()

    ## coin |00) : increment x
    circuit.x(coin_qubits[1])
    for n in range(num_qubits_x-1, -1, -1):
        ctrl_qubits =coin_qubits + pos_x_qubits[:n]
        circuit.mcx(ctrl_qubits, pos_x_qubits[n])

    if barrier:
        circuit.barrier()

    ## coin |01) : decrement x
    circuit.x(coin_qubits[0])
    for n in range(num_qubits_x-1, -1, -1):
        pos_ctrl_qubits = pos_x_qubits[:n]
        ctrl_qubits = coin_qubits + pos_ctrl_qubits
        if pos_ctrl_qubits != []:
            circuit.x(pos_ctrl_qubits)
            circuit.mcx(ctrl_qubits, pos_x_qubits[n])
            circuit.x(pos_ctrl_qubits)
        else:
            circuit.mcx(ctrl_qubits, pos_x_qubits[n])

    if barrier:
        circuit.barrier()

    ## coin |11) : return to normal
    circuit.x(coin_qubits[1])

    return circuit


def create_AA_oracle(num_pos_qubits, num_coin_qubits, marked_state):
    """
    Construct a circuit for the amplitude amplification oracle

    Arguments:
        .num_pos_qubits     -- int, number of qubits for position encoding
        .num_coin_qubits    -- int, number of qubits for coin encoding
        .marked_state       -- str, bitstring representing the marked state

    Returns:
        .oracle            -- qiskit circuit
    """
    pos_qubits = [k for k in range(num_pos_qubits)]
    coin_qubits = [num_pos_qubits + k for k in range(num_coin_qubits)]

    oracle = QuantumCircuit(num_pos_qubits + num_coin_qubits)
    target_qubits = []
    for k in range(num_pos_qubits):
        if marked_state[k] == '0':
            target_qubits.append(num_pos_qubits-1 - k)

    if target_qubits != []:
        oracle.x(target_qubits)
        oracle.mcp(np.pi, pos_qubits[:-1], pos_qubits[-1])
        oracle.x(target_qubits)
    else:
        oracle.mcp(np.pi, pos_qubits[:-1], pos_qubits[-1])

    return oracle
