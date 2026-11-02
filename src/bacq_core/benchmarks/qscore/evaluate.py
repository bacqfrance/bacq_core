"""Expose QScore outcomes through BACQ's metric and score interface."""


_VALID_STATUSES = {"boundary", "above_limit", "below_initial"}


def get_metric_success(exp_data):
    """Return the QScore boundary (or bound) and whether it was resolved exactly."""
    result = exp_data["result"]
    status = result["status"]
    if status not in _VALID_STATUSES:
        raise ValueError(f"Unknown QScore result status: {status!r}.")
    value = result["value"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("QScore result value must be an integer.")
    return value, status == "boundary"


def get_score(exp_data_seq):
    """QScore performs its size sweep internally rather than as a BACQ sequence."""
    raise NotImplementedError(
        "QScore performs its own graph-size search; sequence scoring is not supported."
    )
