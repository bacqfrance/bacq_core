"""MBQS regressions; requires the project's [mbqs] optional dependencies."""

import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from mbqs.scoring.score import TestSuccess
from mbqs.simulations.ising_tabulated import get_correlations

from bacq_core.benchmarks.mbqs import evaluate, experiment, helpers_protocol, helpers_pulser


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def exact_result(L, relative_error=None):
    correlations = {
        str(pair): float(value)
        for pair, value in get_correlations(L=L, state="down")["szsz_c"].items()
    }
    result = {"correlations": correlations}
    if relative_error is not None:
        result["correlations_err"] = {
            pair: relative_error * abs(value) for pair, value in correlations.items()
        }
    return result


def single_experiment(result, **parameters):
    return {
        "parameters": {
            "state": "down", "L": 3, "threshold": 0.1, "num_shots": 2,
            **parameters,
        },
        "result": result,
    }


class EvaluationTests(unittest.TestCase):
    def test_partial_uncertainties_are_preserved(self):
        for missing_error in ({}, {"correlations_err": None}):
            with self.subTest(missing_error=missing_error):
                results = {
                    "4": {**exact_result(4), **missing_error},
                    "3": exact_result(3, relative_error=0.2),
                }
                history, score = evaluate.compute_score(results, "down", 0.1)
                self.assertEqual(score, 0)
                self.assertEqual(list(history), ["3", "4"])
                self.assertAlmostEqual(history["3"]["metric_err"], 0.2)
                self.assertEqual(history["3"]["status"], "undecided")
                self.assertFalse(history["3"]["success"])
                self.assertEqual(history["4"]["metric_err"], 0.0)
                self.assertTrue(history["4"]["success"])
                stopped, score = evaluate.compute_score(results, "down", 0.1, stop_on_fail=True)
                self.assertEqual(list(stopped), ["3"])
                self.assertEqual(score, 0)

    def test_correlations_with_or_without_errors_still_succeed(self):
        for error in (None, 0.01):
            with self.subTest(error=error):
                results = {str(L): exact_result(L, error) for L in (3, 4)}
                history, score = evaluate.compute_score(results, "down", 0.1)
                self.assertEqual(score, 4)
                self.assertTrue(all(item["success"] for item in history.values()))

    def test_nonfinite_correlations_and_errors_are_rejected(self):
        for field in ("correlations", "correlations_err"):
            for invalid in (float("nan"), float("inf"), -float("inf"), True):
                with self.subTest(field=field, invalid=invalid):
                    result = exact_result(3)
                    result[field] = {"(0, 1)": invalid}
                    with self.assertRaises((TypeError, ValueError)):
                        evaluate.get_metric_success(single_experiment(result))
                    with self.assertRaises((TypeError, ValueError)):
                        evaluate.compute_score({"3": result}, "down", 0.1)

    def test_invalid_uncertainty_maps_are_rejected(self):
        for errors in ({}, {"(0, 1)": -0.1}, {"(0, 2)": 0.1}):
            with self.subTest(errors=errors), self.assertRaises(ValueError):
                evaluate.get_data({**exact_result(3), "correlations_err": errors}, 3)

    def test_invalid_imported_parameters_are_rejected(self):
        for parameters in (
            {"state": "unknown"}, {"L": 51}, {"L": True},
            {"threshold": float("nan")}, {"threshold": float("inf")},
            {"threshold": True}, {"threshold": 0}, {"num_shots": True},
        ):
            with self.subTest(parameters=parameters):
                exp = single_experiment(exact_result(3), **parameters)
                with self.assertRaises((TypeError, ValueError)):
                    evaluate.get_metric_success(exp)
                sequence = {
                    "parameters": {k: v for k, v in exp["parameters"].items() if k != "L"},
                    "results": {str(exp["parameters"]["L"]): exp["result"]},
                }
                with self.assertRaises((TypeError, ValueError)):
                    evaluate.get_score(sequence)

    def test_sample_totals_must_match_metadata_in_both_entry_points(self):
        exp = single_experiment({"samples": {"000": 2}}, num_shots=3)
        with self.assertRaisesRegex(ValueError, "number of shots"):
            evaluate.get_metric_success(exp)
        with self.assertRaisesRegex(ValueError, "number of shots"):
            evaluate.get_score({"parameters": exp["parameters"], "results": {"3": exp["result"]}})

    def test_invalid_sample_data_are_rejected(self):
        for samples in (
            {}, {"222": 2}, {"00": 2}, {123: 2}, {"000": -1, "111": 3},
            {"000": 2.0}, {"000": True, "111": 1}, {"000": 0}, {"000": 1},
        ):
            with self.subTest(samples=samples), self.assertRaises((TypeError, ValueError)):
                evaluate.get_data({"samples": samples}, 3)

    def test_two_samples_and_zero_count_entries_remain_valid(self):
        exp = single_experiment({"samples": {"000": 2, "111": 0}})
        metric, success = evaluate.get_metric_success(exp)
        self.assertEqual(metric, 1.0)
        self.assertFalse(success)

    def test_one_shot_metadata_remains_valid_for_correlations(self):
        exp = single_experiment(exact_result(3), num_shots=1)
        self.assertEqual(evaluate.get_metric_success(exp), (0.0, True))
        history, score = evaluate.get_score({"parameters": exp["parameters"], "results": {"3": exp["result"]}})
        self.assertEqual(score, 3)
        self.assertEqual(history["3"]["metric_err"], 0.0)

    def test_empty_and_ambiguous_results_are_rejected(self):
        for result in ({}, {"correlations": {}}, {"samples": {}},
                       {"samples": {"000": 2}, **exact_result(3)}):
            with self.subTest(result=result), self.assertRaises(ValueError):
                evaluate.get_data(result, 3)
        with self.assertRaisesRegex(ValueError, "sequence must not be empty"):
            evaluate.compute_score({}, "down", 0.1)

    def test_nonfinite_computed_metrics_and_uncertainties_are_rejected(self):
        for metric, error in ((float("nan"), 0), (float("inf"), 0),
                              (0, float("nan")), (0, float("inf"))):
            with self.subTest(metric=metric, error=error):
                scorer = SimpleNamespace(
                    metric=metric, metric_err=error, success=TestSuccess.SUCCESS,
                    correlations_errors=None, compute_metric=Mock(),
                    compute_score=Mock(return_value=(3, {3: {
                        "metric": metric, "metric_err": error, "success": TestSuccess.SUCCESS,
                    }})),
                )
                with patch.object(evaluate, "MBQS", return_value=scorer):
                    with self.assertRaisesRegex(ValueError, "must be finite"):
                        evaluate.get_metric_success(single_experiment(exact_result(3)))
                    with self.assertRaisesRegex(ValueError, "must be finite"):
                        evaluate.compute_score({"3": exact_result(3)}, "down", 0.1)

    def test_nonfinite_sample_errors_cannot_be_hidden_by_upstream_history(self):
        scorer = SimpleNamespace(
            correlations_errors={3: {(0, 1): float("nan")}}, compute_score=Mock(),
        )
        with patch.object(evaluate, "MBQS", return_value=scorer):
            with self.assertRaisesRegex(ValueError, "must be finite"):
                evaluate.compute_score({"3": {"samples": {"000": 2}}}, "down", 0.1)
        scorer.compute_score.assert_not_called()

    def test_supplied_examples_keep_their_results_and_are_not_mutated(self):
        single = json.loads((EXAMPLES / "expdata_mbqs.json").read_text())
        sequence = json.loads((EXAMPLES / "expdata_seq_mbqs.json").read_text())
        originals = copy.deepcopy((single, sequence))
        metric, success = evaluate.get_metric_success(single)
        self.assertAlmostEqual(metric, 0.2539535345848385)
        self.assertFalse(success)
        history, score = evaluate.get_score(sequence)
        self.assertEqual(score, 5)
        self.assertEqual(list(history), [str(L) for L in range(3, 9)])
        self.assertEqual((single, sequence), originals)
        json.dumps(history, allow_nan=False)


class ExperimentTests(unittest.TestCase):
    def test_numeric_parameter_validation(self):
        for check in (helpers_protocol.check_threshold, helpers_pulser.check_a):
            for value in (float("nan"), float("inf"), -float("inf"), 0, -1, True):
                with self.subTest(check=check.__name__, value=value):
                    with self.assertRaises((TypeError, ValueError)):
                        check(value)

    def test_single_shot_and_empty_sequences_fail_before_execution(self):
        hardware = Mock()
        with patch.object(experiment, "build_sequence_pulser") as build:
            with self.assertRaisesRegex(ValueError, "at least 2 shots"):
                experiment.run_pulser(hardware, "down", 3, 0.1, 1)
            with self.assertRaisesRegex(ValueError, "sequence must not be empty"):
                experiment.run_pulser(hardware, "down", 3, 0.1, 2, [])
            build.assert_not_called()
            hardware.compute.assert_not_called()

    def test_backend_must_return_exactly_one_result_per_size(self):
        for counts in ([], [{"000": 2}], [{"000": 2}, {"0000": 2}, {"00000": 2}]):
            hardware = SimpleNamespace(device_spec=None, compute=Mock(return_value=counts))
            with self.subTest(counts=counts):
                with patch.object(experiment, "build_sequence_pulser", return_value=(object(), {})):
                    with self.assertRaises(ValueError):
                        experiment.run_pulser(hardware, "down", 3, 0.1, 2, [{"L": 3}, {"L": 4}])

    def test_valid_backend_response_keeps_output_schema(self):
        hardware = SimpleNamespace(
            name="test", device_spec=None,
            compute=Mock(return_value=[{"000": 2}, {"0000": 2}]),
        )
        with patch.object(experiment, "build_sequence_pulser", return_value=(object(), {})):
            result = experiment.run_pulser(hardware, "down", 3, 0.1, 2, [{"L": 3}, {"L": 4}])
        self.assertEqual(result["filetype"], "experiment_seq")
        self.assertEqual(result["device_options"], {"a": 7.5})
        self.assertEqual(result["results"], {
            "3": {"samples": {"000": 2}, "pulse": {}},
            "4": {"samples": {"0000": 2}, "pulse": {}},
        })


if __name__ == "__main__":
    unittest.main()
