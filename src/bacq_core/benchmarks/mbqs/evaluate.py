"""
Grégoire Misguich -- October 2026

Define how to evaluate a MBQS experiment, using the `MBQS` scorer of the `mbqs` package.

The result for one system size is either
    {"samples": {"bitstring": count, ...}}
or
    {"correlations": {"(0, 1)": value, ...}, "correlations_err": {"(0, 1)": error, ...}}
where "correlations_err" is optional and correlations are the connected 2-point
functions <sz_0 sz_i>_c for i = 1, ..., L // 2.
"""

from math import isfinite

from mbqs import MBQS
from mbqs.json_utils import json_decode_keys
from mbqs.scoring.score import TestSuccess

from .helpers_protocol import (
    check_correlations,
    check_counts,
    check_L,
    check_num_shots,
    check_parameters_value,
    check_state,
    check_threshold,
)

# Theoretical correlations at the surge time are taken from the `mbqs` tabulated data.
_METHOD = "tabulated"


def get_data(result, L):
    """
    Get the data (samples or correlations) and the errors on correlations from a result.
    """
    check_L(L)
    if not isinstance(result, dict):
        raise TypeError("Result must be a dictionary.")
    if ("samples" in result) == ("correlations" in result):
        raise ValueError("Result must contain exactly one of 'samples' or 'correlations'.")

    if "samples" in result:
        samples = result["samples"]

        # MBQS takes L from the bitstrings length and ignores the declared L
        check_counts(samples, L, None)

        return samples, None

    if "correlations" in result:
        check_correlations(result["correlations"])
        # MBQS identifies correlations by <float> values: JSON integers (e.g. 0) are converted
        correlations = {k: float(v) for k, v in json_decode_keys(result["correlations"]).items()}

        correlations_err = result.get("correlations_err", None)
        if correlations_err is not None:
            check_correlations(correlations_err, errors=True)
            correlations_err = {k: float(v) for k, v in json_decode_keys(correlations_err).items()}
            if correlations_err.keys() != correlations.keys():
                raise ValueError("correlations_err must have the same pairs as correlations.")

        return correlations, correlations_err


def _check_metric_values(metric, metric_err):
    """Do not report a successful test after a numerical failure."""
    if not isfinite(metric) or not isfinite(metric_err):
        raise ValueError("Computed metric and uncertainty must be finite.")
    if metric_err < 0:
        raise ValueError("Computed metric uncertainty must be nonnegative.")


def get_metric_success(exp_data):
    """
    """
    params = exp_data["parameters"]
    check_parameters_value(params["state"], params["L"], params["threshold"], params["num_shots"])

    data, data_errors = get_data(exp_data["result"], params["L"])
    if "samples" in exp_data["result"]:
        check_counts(data, params["L"], params["num_shots"])

    scorer = MBQS(data, data_errors, state=params["state"], L=params["L"], threshold=float(params["threshold"]))
    scorer.compute_metric(method=_METHOD)
    _check_metric_values(scorer.metric, scorer.metric_err)

    # an undecided test (metric below threshold but within error bar) counts as a failure
    return float(scorer.metric), scorer.success is TestSuccess.SUCCESS


def get_score(exp_data):
    """
    """
    params = exp_data["parameters"]
    check_num_shots(params["num_shots"])
    for L, result in exp_data["results"].items():
        if "samples" in result:
            check_counts(result["samples"], int(L), params["num_shots"])

    return compute_score(exp_data["results"], params["state"], params["threshold"], stop_on_fail=False)


def compute_score(results, state, threshold, stop_on_fail=False):
    """
    Evaluates MBQS, i.e. largest system size L successfully passed before first failure, and stores historical results.
    """
    check_state(state)
    check_threshold(threshold)
    if not results:
        raise ValueError("The result sequence must not be empty.")
    data = {}
    data_errors = {}
    for L in sorted(int(key) for key in results.keys()):
        data[L], data_errors[L] = get_data(results[str(L)], L)

    if all(err is None for err in data_errors.values()):
        data_errors = None

    scorer = MBQS(data, data_errors, state=state, threshold=float(threshold))
    # MBQS omits NaN uncertainties from its history; check the underlying values too.
    if scorer.correlations_errors is not None:
        for errors in scorer.correlations_errors.values():
            if errors is not None:
                check_correlations(errors, errors=True)
    score, mbqs_history = scorer.compute_score(method=_METHOD, stop_on_fail=stop_on_fail)

    history = {}
    for L, values in mbqs_history.items():
        _check_metric_values(values["metric"], values.get("metric_err", 0.0))
        history[str(L)] = {
            "metric": float(values["metric"]),
            "metric_err": float(values.get("metric_err", 0.0)),
            "success": values["success"] is TestSuccess.SUCCESS,
            "status": str(values["success"]),
        }

    return history, score
