"""QScore integration tests; requires the project's [qscore] extra."""

import json
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import networkx as nx

from bacq_core.benchmarks.qscore import (
    annealing,
    evaluate,
    experiment,
    helpers_protocol,
)


VALID_PARAMETERS = {
    "initial_size": 2,
    "size_limit": 4,
    "beta": 0.2,
    "iterator": "dichotomic",
    "depth": 1,
    "seed": 42,
}

VALID_REPORT = {
    "status": "boundary",
    "value": 3,
    "beta": 0.2,
    "evaluations": {},
    "raw_data": {},
}


class ProtocolTests(unittest.TestCase):
    def test_valid_parameters(self):
        helpers_protocol.check_parameters_value(**VALID_PARAMETERS)

    def test_null_seed_is_valid(self):
        params = {**VALID_PARAMETERS, "seed": None}
        helpers_protocol.check_parameters_value(**params)

    def test_invalid_numeric_and_search_parameters_are_rejected(self):
        invalid_cases = (
            ("initial_size", 1, ValueError),
            ("initial_size", True, ValueError),
            ("size_limit", 1, ValueError),
            ("size_limit", True, TypeError),
            ("beta", 0, ValueError),
            ("beta", 1, ValueError),
            ("beta", float("nan"), TypeError),
            ("beta", float("inf"), TypeError),
            ("beta", True, TypeError),
            ("iterator", "unknown", ValueError),
            ("iterator", None, ValueError),
            ("depth", 0, ValueError),
            ("depth", True, ValueError),
            ("seed", True, TypeError),
            ("seed", "42", TypeError),
            ("seed", -1, ValueError),
        )
        for name, value, error in invalid_cases:
            with self.subTest(parameter=name, value=value):
                params = {**VALID_PARAMETERS, name: value}
                with self.assertRaises(error):
                    helpers_protocol.check_parameters_value(**params)

    def test_size_limit_must_not_be_less_than_initial_size(self):
        params = {**VALID_PARAMETERS, "initial_size": 4, "size_limit": 3}
        with self.assertRaisesRegex(ValueError, "size_limit"):
            helpers_protocol.check_parameters_value(**params)

    def test_qscore_does_not_accept_bacq_sequence_protocols(self):
        with self.assertRaisesRegex(NotImplementedError, "protocol_seq"):
            helpers_protocol.sequence_generator()


class EvaluationTests(unittest.TestCase):
    def test_boundary_and_bounds_map_to_bacq_metric_and_success(self):
        cases = (
            ("boundary", True),
            ("above_limit", False),
            ("below_initial", False),
        )
        for status, success in cases:
            with self.subTest(status=status):
                data = {"result": {**VALID_REPORT, "status": status}}
                self.assertEqual(evaluate.get_metric_success(data), (3, success))

    def test_unknown_status_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown QScore result status"):
            evaluate.get_metric_success(
                {"result": {**VALID_REPORT, "status": "unknown"}}
            )

    def test_non_integer_metric_is_rejected(self):
        for value in (True, 3.0, "3"):
            with self.subTest(value=value), self.assertRaises(TypeError):
                evaluate.get_metric_success(
                    {"result": {**VALID_REPORT, "value": value}}
                )

    def test_sequence_scoring_is_not_supported(self):
        with self.assertRaisesRegex(NotImplementedError, "graph-size search"):
            evaluate.get_score({})


class ExperimentTests(unittest.TestCase):
    def _run_with_mocks(self, report=VALID_REPORT):
        composed_qpu = MagicMock(name="composed QPU")
        qscore = MagicMock(name="QScore instance")
        qscore.run.return_value = report

        with (
            patch.object(
                experiment, "_build_clinalg_qpu", return_value=composed_qpu
            ) as build_qpu,
            patch.object(experiment, "_new_qscore", return_value=qscore) as qscore_factory,
        ):
            result = experiment.run("CLinalg", **VALID_PARAMETERS)

        return (
            result,
            composed_qpu,
            qscore,
            build_qpu,
            qscore_factory,
        )

    def test_runs_qscore_with_clinalg_and_returns_bacq_experiment(self):
        (
            result,
            composed_qpu,
            qscore,
            build_qpu,
            qscore_factory,
        ) = self._run_with_mocks()

        self.assertEqual(result["filetype"], "experiment")
        self.assertEqual(result["benchmark"], "qscore")
        self.assertEqual(result["device"], "CLinalg")
        self.assertEqual(result["result"], VALID_REPORT)
        self.assertEqual(result["parameters"], VALID_PARAMETERS)
        build_qpu.assert_called_once_with()
        qscore_factory.assert_called_once()
        self.assertIs(qscore_factory.call_args.args[0], composed_qpu)
        qscore.run.assert_called_once_with()

    def test_qscore_output_files_use_temporary_directory(self):
        _, _, _, _, qscore_factory = self._run_with_mocks()
        kwargs = qscore_factory.call_args.kwargs
        self.assertTrue(kwargs["output"].endswith("/qscore.csv"))
        self.assertTrue(kwargs["rawdata"].endswith("/qscore.raw"))
        self.assertIn("bacq-qscore-", kwargs["output"])
        self.assertEqual(kwargs["initial_size"], VALID_PARAMETERS["initial_size"])
        self.assertEqual(kwargs["size_limit"], VALID_PARAMETERS["size_limit"])
        self.assertEqual(kwargs["seed"], VALID_PARAMETERS["seed"])
        self.assertFalse(Path(kwargs["output"]).parent.exists())

    def test_clinalg_composes_optimizer_with_emulator(self):
        emulator = MagicMock(name="CLinalg instance")
        optimizer = MagicMock(name="optimizer")
        composed_qpu = MagicMock(name="composed QPU")
        optimizer.__or__.return_value = composed_qpu
        with (
            patch("qat.clinalg.CLinalg", return_value=emulator) as clinalg,
            patch(
                "qat.vsolve.optimize.ScipyMinimizePlugin",
                return_value=optimizer,
            ) as plugin,
        ):
            result = experiment._build_clinalg_qpu()

        self.assertIs(result, composed_qpu)
        clinalg.assert_called_once_with()
        plugin.assert_called_once_with(
            method="COBYLA", tol=1e-4, options={"maxiter": 300}
        )
        optimizer.__or__.assert_called_once_with(emulator)

    def test_other_devices_are_not_supported(self):
        with patch.object(experiment, "_new_qscore") as qscore_factory:
            with self.assertRaisesRegex(NotImplementedError, "CLinalg"):
                experiment.run("PyLinalg", **VALID_PARAMETERS)
        qscore_factory.assert_not_called()

    def test_remote_variational_devices_use_qscore_core(self):
        for device in ("MPS",):
            with self.subTest(device=device):
                qpu = MagicMock(name=f"{device} QPU")
                qscore = MagicMock(name="QScore instance")
                qscore.run.return_value = VALID_REPORT
                with (
                    patch.object(
                        experiment,
                        "_build_qaptiva_variational_qpu",
                        return_value=qpu,
                    ) as build_qpu,
                    patch.object(
                        experiment, "_new_qscore", return_value=qscore
                    ) as qscore_factory,
                ):
                    result = experiment.run(device, **VALID_PARAMETERS)

                self.assertEqual(result["device"], device)
                self.assertEqual(result["result"], VALID_REPORT)
                build_qpu.assert_called_once_with(device, VALID_PARAMETERS)
                self.assertIs(qscore_factory.call_args.args[0], qpu)
                qscore.run.assert_called_once_with()

    def test_remote_annealers_select_matching_search_algorithms(self):
        for device, algorithm in (
            ("AnalogQPU", "aqo"),
            ("SQAQPU", "sqa"),
        ):
            with self.subTest(device=device):
                qpu = MagicMock(name=f"{device} QPU")
                with (
                    patch.object(
                        experiment,
                        "_build_qaptiva_annealing_qpu",
                        return_value=qpu,
                    ),
                    patch.object(
                        experiment.annealing,
                        "run",
                        return_value=VALID_REPORT,
                    ) as run_annealing,
                ):
                    result = experiment.run(device, **VALID_PARAMETERS)

                self.assertEqual(result["device"], device)
                self.assertEqual(result["result"], VALID_REPORT)
                self.assertEqual(run_annealing.call_args.args[:2], (qpu, algorithm))
                self.assertEqual(
                    run_annealing.call_args.kwargs["aqo_time"],
                    5.0 if device == "AnalogQPU" else annealing._ANNEALING_TIME,
                )

    def test_invalid_parameters_do_not_start_qscore(self):
        params = {**VALID_PARAMETERS, "depth": 0}
        with patch.object(experiment, "_new_qscore") as qscore_factory:
            with self.assertRaises(ValueError):
                experiment.run("CLinalg", **params)
        qscore_factory.assert_not_called()

    def test_incompatible_qscore_result_api_has_clear_error(self):
        old_api_report = {"status": "boundary"}
        qscore = MagicMock()
        qscore.run.return_value = old_api_report
        with patch.object(experiment, "_new_qscore", return_value=qscore):
            with self.assertRaisesRegex(RuntimeError, "structured run results"):
                experiment.run("CLinalg", **VALID_PARAMETERS)

    def test_small_qscore_run_executes_on_real_clinalg_emulator(self):
        with patch("qat.qscore.benchmark._NB_INSTANCES_PER_SIZE", 1):
            result = experiment.run(
                "CLinalg",
                initial_size=2,
                size_limit=2,
                beta=0.2,
                iterator="exhaustive",
                depth=1,
                seed=42,
            )

        self.assertEqual(result["filetype"], "experiment")
        self.assertEqual(result["benchmark"], "qscore")
        self.assertEqual(result["device"], "CLinalg")
        self.assertIn(result["result"]["status"], {"above_limit", "below_initial"})
        self.assertEqual(len(result["result"]["raw_data"][2]), 1)
        instance = result["result"]["raw_data"][2][0]
        self.assertGreaterEqual(instance["duration_seconds"], 0.0)
        self.assertEqual(
            result["result"]["evaluations"][2]["instance_duration_sum"],
            instance["duration_seconds"],
        )
        json.dumps(result)

    def test_qaoa_saves_measured_instance_and_per_size_submission_durations(self):
        from tempfile import TemporaryDirectory
        import qat.qscore.benchmark as qscore_benchmark

        qpu = MagicMock()
        qpu.submit.return_value = SimpleNamespace(value=-2.0)
        with (
            TemporaryDirectory() as directory,
            patch.object(qscore_benchmark, "_NB_INSTANCES_PER_SIZE", 2),
            patch.object(qscore_benchmark, "generate_maxcut_job"),
            patch.object(
                qscore_benchmark.time, "perf_counter",
                side_effect=[10.0, 12.0, 20.0, 23.0],
            ),
        ):
            report = qscore_benchmark.QScore(
                qpu, initial_size=2, size_limit=2, beta=0.2,
                iterator="exhaustive", seed=42,
                output=str(Path(directory) / "qscore.csv"),
                rawdata=str(Path(directory) / "qscore.raw"),
            ).run()
        self.assertEqual(
            [row["duration_seconds"] for row in report["raw_data"][2]], [2.0, 3.0]
        )
        self.assertEqual(report["evaluations"][2]["instance_duration_sum"], 5.0)

    def test_qutip_qpu_uses_aqo_jobs(self):
        qpu = MagicMock(name="QutipQPU")
        qpu.submit.return_value = SimpleNamespace(value=-1.5, raw_data=[])
        params = {
            **VALID_PARAMETERS,
            "initial_size": 2,
            "size_limit": 2,
            "iterator": "exhaustive",
            "qutip_steps": 12,
            "qutip_tmax": 7.5,
        }
        with (
            patch.object(experiment, "_build_qutip_qpu", return_value=qpu) as build_qpu,
            patch.object(annealing, "_NB_INSTANCES_PER_SIZE", 1),
            patch.object(annealing.time, "perf_counter", side_effect=[10.0, 12.5]),
        ):
            result = experiment.run("QutipQPU", **params)

        build_qpu.assert_called_once_with(params)
        job = qpu.submit.call_args.args[0]
        self.assertIsNotNone(job.schedule)
        self.assertEqual(job.schedule.tmax, 7.5)
        self.assertEqual(result["device"], "QutipQPU")
        self.assertEqual(result["parameters"]["qutip_steps"], 12)
        self.assertEqual(result["parameters"]["qutip_tmax"], 7.5)
        self.assertEqual(result["result"]["raw_data"][2][0]["duration_seconds"], 2.5)
        self.assertEqual(
            result["result"]["evaluations"][2]["instance_duration_sum"], 2.5
        )
        self.assertIn(result["result"]["status"], {"boundary", "above_limit", "below_initial"})
        self.assertEqual(len(result["result"]["raw_data"][2]), 1)
        json.dumps(result)

    def test_qutip_default_evolution_time_passes_size_five_on_real_emulator(self):
        params = {
            **VALID_PARAMETERS,
            "initial_size": 5,
            "size_limit": 5,
            "iterator": "exhaustive",
        }
        # The previous tmax=1.0 produced ratio=0.159 and stopped at size 5.
        for tmax, expected_success in ((None, True), (1.0, False)):
            with self.subTest(tmax=tmax):
                overrides = {} if tmax is None else {"qutip_tmax": tmax}
                with patch.object(annealing, "_NB_INSTANCES_PER_SIZE", 100):
                    result = experiment.run("QutipQPU", **params, **overrides)
                evaluation = result["result"]["evaluations"][5]
                self.assertEqual(
                    result["parameters"]["qutip_tmax"],
                    5.0 if tmax is None else tmax,
                )
                self.assertEqual(len(result["result"]["raw_data"][5]), 100)
                self.assertEqual(evaluation["success"], expected_success)
                if expected_success:
                    self.assertGreater(evaluation["ratio"], 0.55)
                    self.assertLess(evaluation["ratio"], 0.65)
                    self.assertEqual(result["result"]["status"], "above_limit")
                else:
                    self.assertAlmostEqual(evaluation["ratio"], 0.1585, places=3)
                    self.assertEqual(result["result"]["status"], "below_initial")

    def test_invalid_aqo_evolution_time_is_rejected_before_submission(self):
        qpu = MagicMock(name="QutipQPU")
        for tmax in (True, None, "5", 0, -1, float("nan"), float("inf")):
            with (
                self.subTest(tmax=tmax),
                patch.object(experiment, "_build_qutip_qpu", return_value=qpu),
                self.assertRaisesRegex(ValueError, "aqo_time"),
            ):
                experiment.run("QutipQPU", **VALID_PARAMETERS, qutip_tmax=tmax)
        qpu.submit.assert_not_called()

    def test_annealing_sample_state_maps_to_maxcut_score(self):
        graph = nx.Graph([(0, 1), (1, 2)])
        result = SimpleNamespace(
            value=None,
            raw_data=[SimpleNamespace(state=0b101, probability=1.0)],
        )
        self.assertEqual(annealing._score_from_result(result, graph), 2.0)

    def test_annealing_scores_probability_weighted_mean_not_best_sample(self):
        graph = nx.path_graph(3)
        result = SimpleNamespace(
            value=None,
            raw_data=[
                SimpleNamespace(state=0b000, probability=0.75),
                SimpleNamespace(state=0b101, probability=0.25),
            ],
        )
        self.assertEqual(annealing._score_from_result(result, graph), 0.5)

    def test_annealing_observable_value_takes_precedence_over_samples(self):
        result = SimpleNamespace(
            value=-0.75, raw_data=[SimpleNamespace(state=0b101, probability=1.0)]
        )
        self.assertEqual(annealing._score_from_result(result, nx.path_graph(3)), 0.75)

    def test_sampled_devices_save_expected_cut_scores_and_metadata(self):
        samples = [
            SimpleNamespace(state=0b101, probability=0.25),
            SimpleNamespace(state=0b000, probability=0.75),
        ]
        qpu = SimpleNamespace(
            submit=lambda _job: SimpleNamespace(value=None, raw_data=samples)
        )
        for device, builder in (
            ("MPSTraj", "_build_qaptiva_mpstraj_qpu"),
            ("SimulatedAnnealing", "_build_simulated_annealing_qpu"),
            ("SQAQPU", "_build_qaptiva_annealing_qpu"),
        ):
            with (
                self.subTest(device=device),
                patch.object(experiment, builder, return_value=qpu),
                patch.object(annealing, "_NB_INSTANCES_PER_SIZE", 1),
                patch("networkx.generators.erdos_renyi_graph",
                      return_value=nx.path_graph(3)),
            ):
                payload = experiment.run(
                    device, **{**VALID_PARAMETERS, "initial_size": 3, "size_limit": 3}
                )
            self.assertEqual(payload["parameters"]["score_method"], "expected_cut")
            self.assertEqual(payload["result"]["raw_data"][3][0]["score"], 0.5)
            self.assertAlmostEqual(
                payload["result"]["evaluations"][3]["ratio"],
                (0.5 - 0.75) / (0.178 * 3**1.5),
            )

    def test_mean_cut_rejects_invalid_probabilities(self):
        for probability in (None, True, "1", -0.1, 1.1, float("nan"), float("inf")):
            with self.subTest(probability=probability):
                with self.assertRaises((TypeError, ValueError)):
                    annealing._mean_cut_score(
                        nx.path_graph(3),
                        [SimpleNamespace(state=0b101, probability=probability)],
                    )
        for probabilities in ([], [0.0], [0.5], [0.75, 0.75]):
            with self.subTest(probabilities=probabilities):
                with self.assertRaises((RuntimeError, ValueError)):
                    annealing._mean_cut_score(
                        nx.path_graph(3),
                        [SimpleNamespace(state=0, probability=p) for p in probabilities],
                    )

    def test_mean_cut_normalizes_roundoff_only(self):
        samples = [SimpleNamespace(state=0b101, probability=0.9999999)]
        self.assertEqual(annealing._mean_cut_score(nx.path_graph(3), samples), 2.0)

    def test_sample_states_use_qlm_qubit_order(self):
        from qat.lang.AQASM import Program, X
        from qat.qpus import PyLinalg

        program = Program()
        qubits = program.qalloc(3)
        program.apply(X, qubits[0])
        sample = next(iter(PyLinalg().submit(program.to_circ().to_job())))
        graph = nx.Graph([(0, 1)])
        graph.add_node(2)
        for state in (sample.state, sample.state.int, str(sample.state), 0b100):
            with self.subTest(state=state):
                self.assertEqual(annealing._state_bits(state, 3), [1, 0, 0])
                self.assertEqual(annealing._cut_score(graph, state), 1.0)
        self.assertEqual(annealing._cut_score(nx.Graph([(0, 1), (1, 2)]), 0b001), 1.0)

    def test_annealing_rejects_out_of_range_sample_states(self):
        for state in (-1, 0b100):
            with self.subTest(state=state), self.assertRaisesRegex(
                ValueError, "state space"
            ):
                annealing._state_bits(state, 2)

    def test_annealing_rejects_non_finite_energy(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, "must be finite"
            ):
                annealing._score_from_result(SimpleNamespace(value=value), nx.Graph())

    def test_annealing_validates_algorithm_and_shots_before_submission(self):
        qpu = MagicMock(name="annealing QPU")
        for algorithm, shots in (
            ("unknown", 1),
            ([], 1),
            ("sqa", 0),
            ("sa", True),
        ):
            with self.subTest(algorithm=algorithm, shots=shots):
                with self.assertRaises(ValueError):
                    annealing.run(
                        qpu,
                        algorithm,
                        initial_size=2,
                        size_limit=2,
                        beta=0.2,
                        iterator="exhaustive",
                        seed=42,
                        shots=shots,
                    )
        qpu.submit.assert_not_called()

    def test_sqa_job_has_linear_transverse_field_schedule(self):
        from qat.core.variables import Variable

        problem = MagicMock(name="MaxCut problem")
        annealing._make_job(problem, "sqa", shots=7)

        kwargs = problem.sqa_job.call_args.kwargs
        self.assertEqual(kwargs["tmax"], annealing._ANNEALING_TIME)
        self.assertEqual(kwargs["nbshots"], 7)
        self.assertEqual(
            str(kwargs["gamma_t"]),
            str(1.0 - Variable("t", float)),
        )

    def test_sqa_job_accepts_reference_transverse_field_schedule(self):
        from qat.core.variables import Variable

        problem = MagicMock(name="MaxCut problem")
        gamma_t = 0.1 * (Variable("t", float) / 2.0) + 1.0 * (
            1 - Variable("t", float) / 2.0
        )
        annealing._make_job(
            problem, "sqa", shots=1024, aqo_time=2.0, gamma_t=gamma_t
        )
        kwargs = problem.sqa_job.call_args.kwargs
        self.assertEqual(kwargs["tmax"], 2.0)
        self.assertEqual(kwargs["nbshots"], 1024)
        self.assertEqual(str(kwargs["gamma_t"]), str(gamma_t))

    def test_qutip_qpu_is_constructed_with_requested_steps(self):
        with patch("qat.analog.qutip_qpu.QutipQPU") as qutip_class:
            qpu = experiment._build_qutip_qpu({"qutip_steps": 12})
        qutip_class.assert_called_once_with(n_steps=12)
        self.assertIs(qpu, qutip_class.return_value)

    def test_simulated_annealing_runs_real_small_maxcut_job(self):
        with patch.object(annealing, "_NB_INSTANCES_PER_SIZE", 1):
            result = experiment.run(
                "SimulatedAnnealing",
                initial_size=2,
                size_limit=2,
                beta=0.2,
                iterator="exhaustive",
                depth=1,
                seed=42,
                annealing_steps=10,
                shots=5,
            )

        self.assertEqual(result["device"], "SimulatedAnnealing")
        self.assertEqual(result["parameters"]["annealing_steps"], 10)
        self.assertEqual(result["parameters"]["shots"], 5)
        self.assertIn(
            result["result"]["status"],
            {"boundary", "above_limit", "below_initial"},
        )
        self.assertEqual(len(result["result"]["raw_data"][2]), 1)
        self.assertIsInstance(result["result"]["raw_data"][2][0]["score"], float)
        json.dumps(result)


if __name__ == "__main__":
    unittest.main()
