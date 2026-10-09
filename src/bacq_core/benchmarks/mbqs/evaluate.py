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

from mbqs import MBQS
from mbqs.json_utils import json_decode_keys
from mbqs.scoring.score import TestSuccess

# Theoretical correlations at the surge time are taken from the `mbqs` tabulated data.
_METHOD = "tabulated"


def get_data(result, L):
    """
    Get the data (samples or correlations) and the errors on correlations from a result.
    """
    if "samples" in result:
        samples = result["samples"]

        # MBQS takes L from the bitstrings length and ignores the declared L
        if any(len(bitstring) != L for bitstring in samples.keys()):
            raise ValueError(f"Reported bitstrings do not all have length {L=}.")

        return samples, None

    if "correlations" in result:
        # MBQS identifies correlations by <float> values: JSON integers (e.g. 0) are converted
        correlations = {k: float(v) for k, v in json_decode_keys(result["correlations"]).items()}

        correlations_err = result.get("correlations_err", None)
        if correlations_err is not None:
            correlations_err = {k: float(v) for k, v in json_decode_keys(correlations_err).items()}

        return correlations, correlations_err

    raise ValueError("Result must contain either 'samples' or 'correlations'.")


def get_metric_success(exp_data):
    """
    """
    params = exp_data["parameters"]

    data, data_errors = get_data(exp_data["result"], params["L"])

    scorer = MBQS(data, data_errors, state=params["state"], L=params["L"], threshold=float(params["threshold"]))
    scorer.compute_metric(method=_METHOD)

    # an undecided test (metric below threshold but within error bar) counts as a failure
    return float(scorer.metric), scorer.success is TestSuccess.SUCCESS


def get_score(exp_data):
    """
    """
    params = exp_data["parameters"]

    return compute_score(exp_data["results"], params["state"], params["threshold"], stop_on_fail=False)


def compute_score(results, state, threshold, stop_on_fail=False):
    """
    Evaluates MBQS, i.e. largest system size L successfully passed before first failure, and stores historical results.
    """
    data = {}
    data_errors = {}
    for L in sorted(int(key) for key in results.keys()):
        data[L], data_errors[L] = get_data(results[str(L)], L)

    if any(err is None for err in data_errors.values()):
        data_errors = None

    scorer = MBQS(data, data_errors, state=state, threshold=float(threshold))
    score, mbqs_history = scorer.compute_score(method=_METHOD, stop_on_fail=stop_on_fail)

    history = {}
    for L, values in mbqs_history.items():
        history[str(L)] = {
            "metric": float(values["metric"]),
            "metric_err": float(values.get("metric_err", 0.0)),
            "success": values["success"] is TestSuccess.SUCCESS,
            "status": str(values["success"]),
        }

    return history, score
