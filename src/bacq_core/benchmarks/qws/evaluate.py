"""
Noe Olivier -- July 2026

Define how to evaluate a QWS experiment.
"""
import sys

def get_metric(exp_data):
    """
    """
    result = exp_data["result"]
    graph_type = exp_data["parameters"]["graph_type"]
    
    return compute_metric(result, graph_type)


def compute_metric(result, graph_type):
    """
    Computes QWS metric, i.e. mean success probability achieved on all instances of a problem size.
    """
    mean_list = [sum(result[state])/len(result[state]) for state in result.keys()]
    metric = sum(mean_list)/len(mean_list)
    
    return metric


def get_metric_success(exp_data):
    """
    """
    metric = get_metric(exp_data)
    success = compute_success(metric, exp_data["parameters"]["d"], exp_data["parameters"]["graph_type"])

    return metric, success


def compute_success(metric, distance, graph_type):
    """
    Compares experimental QWS metric with QWS threshold probability.
    """
    if graph_type in ["cycle", "2D-torus"]:
        if distance <= 2:
            p_threshold = 1/3
        else:
            p_threshold = 1/5 + 1/(2**distance)

    else:
        raise ValueError(f"Parameter {graph_type=} is not valid. Expected 'cycle' or '2D-torus'.")

    return metric >= p_threshold


def get_score(exp_data):
    """
    """
    results = exp_data["results"]
    graph_type = exp_data["parameters"]["graph_type"]

    return compute_score(results, graph_type, stop_on_fail=False)


def compute_score(results, graph_type, stop_on_fail=False):
    """
    Evaluates QWS, i.e. largest problem size successfully solved before first failure, and stores historical results.
    """
    history = {}
    failure = False
    score = 0

    for key, result in results.items():
        n, d = get_n_d_from_pbmsize(key)

        metric = compute_metric(result, graph_type)
        success = compute_success(metric, d, graph_type)

        history[key] = {
            "metric": metric,
            "success": success,
        }

        if success is False:
            failure = True
            if stop_on_fail is True:
                break

        if success is True and failure is False:
            score = compute_qws(graph_type, n, d)

    return history, score


def compute_qws(graph_type, n, d):
    """
    Computes QWS value from n and d.
    """
    if graph_type == "cycle":
        qws = 2**(n-1) + d

    elif graph_type == "2D-torus":
        qws = 2**n + d

    else:
        raise ValueError(f"Parameter {graph_type=} is not valid. Expected 'cycle' or '2D-torus'.")

    return qws

def get_n_d_from_pbmsize(pbmsize):
    """
    Extract int(n) & int(d) from '(n,d)'.
    """
    n = ""
    d = ""
    k_n = 0
    k_d = 0

    for char in pbmsize:
        if char == ")":
            k_d = 0

        if k_d == 1:
            d += char

        if char == ",":
            k_n = 0
            k_d = 1

        if k_n == 1:
            n += char

        if char == "(":
            k_n = 1
    
    return int(n), int(d)
