"""
Noe Olivier -- July 2026

Defines functions to ensure the QWS protocol is well applied.
"""

_MIN_NUM_SHOTS = 1000
_MIN_NUM_SHOTS_SOLUTION = 1000
_MIN_NUM_LAYERS = 1
_MIN_NUM_QUBITS = 2

def sequence_generator(n_min, n_max):
    """
    Generate the list of sequence parameters, i.e. problem sizes.
    """
    if n_min < _MIN_NUM_QUBITS:
        raise ValueError(f"Sequence parameter {n_min=} must be at least equal to {_MIN_NUM_QUBITS}.")

    if n_max < n_min:
        raise ValueError(f"Sequence parameter {n_max=} must be at least equal to {n_min=}.")

    list_seq_params = []
    n = n_min 

    while n <= n_max:
        list_seq_params.append({"n": n})
        n += 1

    return list_seq_params


def check_parameters_value(num_qubits, optimizer, max_iters, tol, ansatz, num_layers, num_shots, num_shots_solution, list_seq_params):
    """
    Checks that input parameters value are protocol-valid.
    """
    check_optimizer(optimizer)
    check_tol(tol)
    check_ansatz(ansatz)
    check_num_shots(num_shots, num_shots_solution)

    if list_seq_params is None:
        check_num_qubits(num_qubits)
        check_max_iters(max_iters)
        check_num_layers(num_layers)

    else:
        size = len(list_seq_params)

        for k in range(1, size+1):
            n = list_seq_params[k-1]["n"]

            check_num_qubits(n)

            if isinstance(max_iters, list):
                check_max_iters(max_iters, size=k)
            else:
                check_max_iters(max_iters)

            if isinstance(num_layers, list):
                check_num_layers(num_layers, size=k)
            else:
                check_num_layers(num_layers)


def check_optimizer(optimizer):
    """
    Checks type of input optimizer parameter.
    """
    if not isinstance(optimizer, str):
        raise TypeError('Parameter optimizer must be <str>. See scipy.optimize.minimize() for accepted methods.')


def check_tol(tol):
    """
    Checks type of input tol parameter.
    """
    if tol != None:
        if not isinstance(tol, float):
            raise TypeError('Parameter tol must be <float> or None.')


def check_ansatz(ansatz):
    """
    Checks type of input ansatz parameter.
    """
    if not isinstance(ansatz, str):
        raise TypeError('Parameter ansatz must be <str>.')


def check_num_shots(num_shots, num_shots_solution):
    """
    Checks type and value of input number of shots for training and solution evaluation.
    """
    if not isinstance(num_shots, int):
        raise TypeError('Parameter num_shots must be <int>.')
    if not isinstance(num_shots_solution, int):
        raise TypeError('Parameter num_shots_solution must be <int>.')

    if num_shots < _MIN_NUM_SHOTS:
        raise ValueError(f'Parameter {num_shots=} not valid: >= {_MIN_NUM_SHOTS} required.')
    if num_shots_solution < _MIN_NUM_SHOTS_SOLUTION:
        raise ValueError(f'Parameter {num_shots_solution=} not valid: >= {_MIN_NUM_SHOTS_SOLUTION} required.')


def check_num_qubits(num_qubits):
    """
    Checks type and value of input number of qubits.
    """
    if not isinstance(num_qubits, int):
        raise TypeError('Parameter num_qubits must be <int>.')

    if num_qubits < _MIN_NUM_QUBITS:
        raise ValueError(f'Parameter {num_qubits=} not valid: >= {_MIN_NUM_QUBITS} required.')


def check_max_iters(max_iters, size=0):
    """
    Checks type and value of input maximum number of optimization iterations.
    """
    if size == 0:
        if max_iters != None:
            if not isinstance(max_iters, int):
                raise TypeError(f'Parameter max_iters is {type(max_iters)} but expected to be <int> or None.')

    else:
        if len(max_iters) < size:
            raise ValueError(f'Parameter max_iters is a list of insufficient size ({len(max_iters)}): adjust size or use <int>.')

        if not isinstance(max_iters[size-1], int):
            raise TypeError('Parameter max_iters must be <int> or <list[int]>.')


def check_num_layers(num_layers, size=0):
    """
    Checks type and value of input number of ansatz layers.
    """
    if size == 0:
        if not isinstance(num_layers, int):
            raise TypeError(f'Parameter num_layers is {type(num_layers)} but expected to be <int>.')

    else:
        if len(num_layers) < size:
            raise ValueError(f'Parameter num_layers is a list of insufficient size ({len(num_layers)}): adjust size or use <int>.')

        if not isinstance(num_layers[size-1], int):
            raise TypeError('Parameter num_layers must be <int> or <list[int]>.')
