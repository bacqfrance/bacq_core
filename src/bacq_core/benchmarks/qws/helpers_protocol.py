"""
Noe Olivier -- March 2026

Defines functions to ensure the QWS protocol is well applied.
"""

_MIN_NUM_SHOTS = 100
_MIN_NUM_INSTANCES = 1
_MIN_N = 2
_MIN_D = 1

_GRAPH_TYPES = ["cycle", "2D-torus"]

def sequence_generator(graph_type, n_min, d_min, n_max, d_max):
    '''
    '''
    if n_min < _MIN_N:
        raise ValueError(f"Sequence parameter {n_min=} must be at least equal to {_MIN_N}.")

    if n_max < n_min:
        raise ValueError(f"Sequence parameter {n_max=} must be at least equal to {n_min=}.")

    if d_min < _MIN_D:
        raise ValueError(f"Sequence parameter {d_min=} must be at least equal to {_MIN_D}.")

    if d_max < _MIN_D:
        raise ValueError(f"Sequence parameter {d_max=} must be at least equal to {_MIN_D}.")
    
    list_seq_params = []
    n = n_min 
    d = d_min

    match graph_type:

        case "cycle":
            
            while n < n_max:
                d_limit = 2**(n-1)

                while d <= d_limit:
                    list_seq_params.append({"n": n, "d": d})
                    d += 1

                n += 1
                d = 1
            
            while d <= d_max:
                list_seq_params.append({"n": n, "d": d})
                d += 1

        case "2D-torus":

            while n < n_max:
                d_limit = 2**n

                while d <= d_limit:
                    list_seq_params.append({"n": n, "d": d})
                    d += 1

                n += 1
                d = 1
            
            while d <= d_max:
                list_seq_params.append({"n": n, "d": d})
                d += 1

        case _:
            raise NotImplementedError(f"Parameter {graph_type=} is not implemented.\nSupported graphs: {_GRAPH_TYPES}")

    return list_seq_params


def compute_success_proba(counts, state, num_shots):
    '''
    '''
    num_shots_exp = sum(counts.values())
    if num_shots_exp != num_shots:
        raise ValueError(f"Reported counts does not have the reight number of shots.\n{num_shots=} vs reported_counts={num_shots_exp}")

    if state not in counts.keys():
        success_proba = 0
    else:
        success_proba = counts[state]/num_shots

    return success_proba


def check_parameters_value(graph_type, n, d, num_walk, num_aa, num_instances, num_shots, list_seq_params):
    '''
    '''
    check_num_instances(num_instances)
    check_num_shots(num_shots)

    if list_seq_params is None:
        check_n_d(graph_type, n, d)
        check_num_walk(num_walk, n, d)
        check_num_aa(num_aa)

    else:
        size = len(list_seq_params)

        for k in range(1, size+1):
            n = list_seq_params[k-1]["n"]
            d = list_seq_params[k-1]["d"]

            check_n_d(graph_type, n, d)

            if isinstance(num_walk, list):
                check_num_walk(num_walk, n, d, size=k)
            else:
                check_num_walk(num_walk, n, d)

            if isinstance(num_aa, list):
                check_num_aa(num_aa, size=k)
            else:
                check_num_aa(num_aa)


def check_num_instances(num_instances):
    '''
    '''
    if not isinstance(num_instances, int):
        raise TypeError('Parameter num_instances must be <int>.')

    if num_instances < _MIN_NUM_INSTANCES:
        raise ValueError(f'Parameter {num_instances=} not valid: > {_MIN_NUM_INSTANCES} required.')

    return num_instances

def check_num_shots(num_shots):
    '''
    ''' 
    if not isinstance(num_shots, int):
        raise TypeError('Parameter num_shots ust be <int>.')

    if num_shots < _MIN_NUM_SHOTS:
        raise ValueError(f'Parameter {num_shots=} not valid: > {_MIN_NUM_SHOTS} required.')


def check_n_d(graph_type, n, d):
    '''
    '''
    if not isinstance(n, int):
        raise TypeError('Parameter n must be <int>.')

    if n < _MIN_N:
        raise ValueError(f'Parameter {n=} not valid: > {_MIN_N} required.')

    if not isinstance(d, int):
        raise TypeError('Parameter d must be <int>.')

    if d < _MIN_D:
        raise ValueError(f'Parameter {d=} not valid: > {_MIN_D} required.')

    if not isinstance(graph_type, str):
        raise TypeError('Parameter graph_type must be <str>.')

    match graph_type:

        case "cycle":
            if d > 2**(n-1):
                raise ValueError(f"Problem size ({n},{d}) not valid for {graph_type} graphs: expected d < {2**(n-1)}.")

        case "2D-torus":
            if d > 2**n:
                raise ValueError(f"Problem size ({n},{d}) not valid for {graph_type} graphs: expected d < {2**n}.")
        
        case _:
            raise NotImplementedError(f"Parameter {graph_type=} is not implemented.\nSupported graphs: {_GRAPH_TYPES}")


def check_num_walk(num_walk, n, d, size=0):
    '''
    '''
    if size == 0:
        if not isinstance(num_walk, int):
            raise TypeError(f'Parameter num_walk is ({type(num_walk)}) but expected to be <int>.')
        
        if num_walk < d:
            raise ValueError(f"Problem size ({n},{d}): {num_walk=} must be greater or equal to {d}.")
    
    else:
        if len(num_walk) < size:
            raise ValueError(f"Parameter num_walk is a list of insufficient size ({len(num_walk)}): adjust size or use int.")

        if not isinstance(num_walk[size-1], int):
            raise TypeError("Parameter num_walk must be <int> or <list[int]>.")

        if num_walk[size-1] < d:
            raise ValueError(f"Problem size ({n},{d}): {num_walk[size-1]=} must be greater or equal to {d}.")


def check_num_aa(num_aa, size=0):
    '''
    '''
    if size == 0:
        if not isinstance(num_aa, int):
            raise TypeError(f'Parameter num_aa is ({type(num_aa)}) but expected to be <int>.')

    else:
        if len(num_aa) < size:
            raise ValueError(f"Parameter num_aa is a list of insufficient size ({len(num_aa)}): adjust size or use int.")

        if not isinstance(num_aa[size-1], int):
            raise TypeError("Parameter num_aa must be <int> or <list[int]>.")

