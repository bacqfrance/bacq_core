"""
Noe Olivier -- March 2026

Define how to evaluate a QWS experiment.
"""

import sys
from pathlib import Path


from qws.scoring import compute_metric, compute_success, compute_score


def get_metric(exp_data):
    """
    """
    metric = compute_metric(exp_data["result"], exp_data["parameters"]["graph_type"])
    
    return metric


def get_metric_success(exp_data):
    """
    """
    metric = get_metric(exp_data)
    success = compute_success(metric, exp_data["parameters"]["d"], exp_data["parameters"]["graph_type"])

    return metric, success


def get_score(exp_data):
    """
    """
    results = exp_data["results"]
    graph_type = exp_data["parameters"]["graph_type"]

    history, score = compute_score(results, graph_type, stop_on_fail=False)

    return history, score
