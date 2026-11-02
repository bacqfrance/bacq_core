"""Offline QLMaaS contract checks; never authenticate or submit to a server."""

from pathlib import Path
import socket
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import networkx as nx

from bacq_core.benchmarks.qscore import annealing, experiment


PARAMETERS = {
    "initial_size": 3, "size_limit": 3, "beta": 0.2,
    "iterator": "exhaustive", "depth": 1, "seed": 42,
}


class RemoteContractTests(unittest.TestCase):
    def setUp(self):
        guard = patch.object(socket.socket, "connect",
                             side_effect=AssertionError("Network disabled in offline test"))
        guard.start()
        self.addCleanup(guard.stop)

    def test_mpstraj_job_matches_reference_schedule_sample_construction(self):
        from numbers import Number

        import numpy as np
        from qat.core import Observable, Schedule, Term
        from qat.core.variables import Variable
        from qat.opt import MaxCut

        problem = MaxCut(nx.path_graph(3))
        tmax = 12.0
        job = annealing._make_job(problem, "mpstraj", shots=7, aqo_time=tmax)
        tau = Variable("t", float) / tmax
        mixing = Observable(3, pauli_terms=[Term(-1.0, "X", [i]) for i in range(3)])
        expected = Schedule(
            drive=[(1 - tau, mixing), (tau, problem.get_observable("terms"))],
            tmax=tmax,
        ).to_job(job_type="SAMPLE", nbshots=7, psi_0="+++")
        self.assertIsNone(job.circuit)
        self.assertIsNone(job.observable)
        self.assertEqual(job.type, expected.type)
        self.assertEqual(job.psi_0, "+++")
        self.assertEqual(job.nbshots, 7)
        self.assertEqual(job.schedule.tmax, tmax)
        self.assertEqual(str(job.schedule), str(expected.schedule))
        for _, observable in job.schedule.drive:
            self.assertIsInstance(observable.constant_coeff, Number)
            for term in observable.terms:
                self.assertIsInstance(term.coeff, Number)
                abs(term.coeff)
        for time in (0.0, tmax / 2, tmax):
            actual_matrix = sum(
                coefficient(t=time) * observable.to_matrix()
                for coefficient, observable in job.schedule.drive
            )
            expected_matrix = (
                (1 - time / tmax) * mixing.to_matrix()
                + (time / tmax) * problem.get_observable("terms").to_matrix()
            )
            np.testing.assert_allclose(
                actual_matrix.toarray(), expected_matrix.toarray()
            )

    def test_mpstraj_mixer_matches_maxcut_aqo_job(self):
        from qat.opt import MaxCut

        problem = MaxCut(nx.erdos_renyi_graph(5, 0.5, seed=42))
        job = annealing._make_job(problem, "mpstraj", shots=7, aqo_time=5.0)
        reference = problem.aqo_job(tmax=5.0, nbshots=0)
        self.assertEqual(job.psi_0, reference.psi_0)
        self.assertEqual(str(job.schedule.drive[0][1]), str(reference.schedule.drive[0][1]))

    def test_myqlm_emulator_uses_configured_default_qpu(self):
        from bacq_core.hardware import myqlm_emulator

        default_qpu = MagicMock(name="default myQLM QPU")
        with patch("qat.qpus.get_default_qpu", return_value=default_qpu) as factory:
            result = myqlm_emulator.build_backend()
        factory.assert_called_once_with()
        self.assertIs(result, default_qpu)

    def test_qscore_runs_on_myqlm_default_qpu(self):
        import qat.qscore.benchmark as benchmark

        previous_instances = benchmark._NB_INSTANCES_PER_SIZE
        benchmark._NB_INSTANCES_PER_SIZE = 1
        self.addCleanup(
            setattr, benchmark, "_NB_INSTANCES_PER_SIZE", previous_instances
        )
        result = experiment.run(
            "MyQLMEmulator",
            initial_size=3,
            size_limit=3,
            beta=0.2,
            iterator="exhaustive",
            depth=1,
            seed=42,
        )
        self.assertEqual(result["device"], "MyQLMEmulator")
        self.assertIn(3, result["result"]["evaluations"])
        self.assertEqual(len(result["result"]["raw_data"][3]), 1)

    def test_mpstraj_imports_only_remote_mpstraj_and_forwards_parameters(self):
        qpus = ModuleType("qlmaas.qpus")
        qpus.MPSTraj = MagicMock()
        package = ModuleType("qlmaas")
        package.__path__ = []
        params = {**PARAMETERS, "mpstraj_steps": 40, "mpstraj_bond_dimension": 6,
                  "mpstraj_tmax": 12.0, "shots": 7}
        with (
            patch.dict("sys.modules", {"qlmaas": package, "qlmaas.qpus": qpus}),
            patch.object(annealing, "run", return_value={}) as run,
        ):
            result = experiment.run("MPSTraj", **params)
        qpus.MPSTraj.assert_called_once_with(n_steps=40, bond_dimension=6, seed=42)
        self.assertEqual(run.call_args.args, (qpus.MPSTraj.return_value, "mpstraj"))
        self.assertEqual(run.call_args.kwargs["aqo_time"], 12.0)
        self.assertEqual(run.call_args.kwargs["shots"], 7)
        for name in ("mpstraj_steps", "mpstraj_bond_dimension", "mpstraj_tmax", "shots"):
            self.assertEqual(result["parameters"][name], params[name])

    def test_mps_uses_reference_remote_optimizer_and_bond_dimension(self):
        qpus = ModuleType("qlmaas.qpus")
        qpus.MPS = MagicMock()
        plugins = ModuleType("qlmaas.plugins")
        plugins.ScipyMinimizePlugin = MagicMock()
        package = ModuleType("qlmaas")
        package.__path__ = []
        with (
            patch.dict(
                "sys.modules",
                {
                    "qlmaas": package,
                    "qlmaas.qpus": qpus,
                    "qlmaas.plugins": plugins,
                },
            ),
        ):
            experiment._build_qaptiva_variational_qpu(
                "MPS", {"mps_bond_dimension": 16}
            )
        qpus.MPS.assert_called_once_with(bond_dimension=16)
        plugins.ScipyMinimizePlugin.assert_called_once_with(
            method="COBYLA", tol=1e-4, options={"maxiter": 300}
        )
        plugins.ScipyMinimizePlugin.return_value.__or__.assert_called_once_with(
            qpus.MPS.return_value
        )

    def test_reference_annealing_qpu_parameters_and_schedules(self):
        qpus = ModuleType("qlmaas.qpus")
        qpus.AnalogQPU = MagicMock()
        qpus.SQAQPU = MagicMock()
        package = ModuleType("qlmaas")
        package.__path__ = []
        with patch.dict("sys.modules", {"qlmaas": package, "qlmaas.qpus": qpus}):
            experiment._build_qaptiva_annealing_qpu(
                "AnalogQPU", {"analog_steps": 50}
            )
            experiment._build_qaptiva_annealing_qpu(
                "SQAQPU",
                {
                    "sqa_steps": 50,
                    "sqa_trotters": 8,
                    "sqa_temp_min": 0.1,
                    "sqa_temp_max": 5.0,
                    "sqa_tmax": 1.0,
                },
            )
        qpus.AnalogQPU.assert_called_once_with(n_steps=50)
        qpus.SQAQPU.assert_called_once()
        sqa_kwargs = qpus.SQAQPU.call_args.kwargs
        self.assertEqual((sqa_kwargs["n_steps"], sqa_kwargs["n_trotters"]), (50, 8))
        self.assertIsNotNone(sqa_kwargs["temp_t"])

    def test_qaptiva_local_imports_qat_qpus_and_plugins_not_qlmaas(self):
        qpus = ModuleType("qat.qpus")
        for name in ("MPS", "MPSTraj", "AnalogQPU", "SQAQPU"):
            setattr(qpus, name, MagicMock(name=name))
        plugins = ModuleType("qat.plugins")
        plugins.ScipyMinimizePlugin = MagicMock()
        sqa_params = {"sqa_steps": 50, "sqa_trotters": 8, "sqa_temp_min": 0.1,
                      "sqa_temp_max": 5.0, "sqa_tmax": 1.0}
        with (
            patch.dict("os.environ", {"QAPTIVA_LOCAL": "true"}),
            patch.dict("sys.modules", {
                "qat.qpus": qpus, "qat.plugins": plugins,
                "qlmaas": None, "qlmaas.qpus": None, "qlmaas.plugins": None,
            }),
        ):
            experiment._build_qaptiva_variational_qpu("MPS", {"mps_bond_dimension": 16})
            experiment._build_qaptiva_mpstraj_qpu(PARAMETERS)
            experiment._build_qaptiva_annealing_qpu("AnalogQPU", {"analog_steps": 50})
            experiment._build_qaptiva_annealing_qpu("SQAQPU", sqa_params)
        qpus.MPS.assert_called_once_with(bond_dimension=16)
        qpus.MPSTraj.assert_called_once_with(n_steps=50, bond_dimension=32, seed=42)
        qpus.AnalogQPU.assert_called_once_with(n_steps=50)
        qpus.SQAQPU.assert_called_once()

    def test_invalid_mpstraj_constructor_parameters_fail_offline(self):
        for name in ("mpstraj_steps", "mpstraj_bond_dimension"):
            for value in (True, 0, -1, 2.5):
                with self.subTest(name=name, value=value), self.assertRaisesRegex(ValueError, name):
                    experiment._build_qaptiva_mpstraj_qpu({**PARAMETERS, name: value})

    def test_missing_mpstraj_import_has_explicit_error(self):
        with (
            patch.dict("sys.modules", {"qlmaas.qpus": None}),
            self.assertRaisesRegex(ImportError, "configured QLMaaS MPSTraj"),
        ):
            experiment._build_qaptiva_mpstraj_qpu(PARAMETERS)

    def test_real_async_result_resolution_is_inside_annealing_timer(self):
        from qat.qlmaas import QLMaaSConnection
        from qat.qlmaas.result import AsyncResult

        clock = [10.0]
        resolved = SimpleNamespace(
            value=None, raw_data=[SimpleNamespace(state=0b010, probability=1.0)]
        )
        pending = AsyncResult("offline", MagicMock(spec=QLMaaSConnection))

        def complete(_self):
            clock[0] = 15.0
            return resolved

        with (
            patch.object(AsyncResult, "join", complete),
            patch.object(annealing, "_NB_INSTANCES_PER_SIZE", 1),
            patch.object(annealing.time, "perf_counter", side_effect=lambda: clock[0]),
            patch("networkx.generators.erdos_renyi_graph", return_value=nx.path_graph(3)),
        ):
            report = annealing.run(
                SimpleNamespace(submit=lambda _job: pending), "mpstraj",
                initial_size=3, size_limit=3, beta=0.2, iterator="exhaustive",
                seed=42, shots=7, aqo_time=12.0,
            )
        self.assertEqual(report["raw_data"][3][0]["score"], 2.0)
        self.assertEqual(report["raw_data"][3][0]["duration_seconds"], 5.0)
        self.assertEqual(report["evaluations"][3]["instance_duration_sum"], 5.0)

    def test_real_async_result_resolution_is_inside_qaoa_timer(self):
        import qat.qscore.benchmark as benchmark
        from qat.qlmaas import QLMaaSConnection
        from qat.qlmaas.result import AsyncResult

        clock = [10.0]
        pending = AsyncResult("offline", MagicMock(spec=QLMaaSConnection))

        def complete(_self):
            clock[0] = 15.0
            return SimpleNamespace(value=-2.0)

        with (
            TemporaryDirectory() as directory,
            patch.object(AsyncResult, "join", complete),
            patch.object(benchmark, "_NB_INSTANCES_PER_SIZE", 1),
            patch.object(benchmark.time, "perf_counter", side_effect=lambda: clock[0]),
        ):
            report = benchmark.QScore(
                SimpleNamespace(submit=lambda _job: pending), initial_size=3,
                size_limit=3, iterator="exhaustive", seed=42,
                output=str(Path(directory) / "out.csv"),
                rawdata=str(Path(directory) / "out.raw"),
            ).run()
        self.assertEqual(report["raw_data"][3][0]["score"], 2.0)
        self.assertEqual(report["raw_data"][3][0]["duration_seconds"], 5.0)

    def test_mpstraj_schedule_executes_locally_as_an_exact_distribution(self):
        from qat.analog.qutip_qpu import QutipQPU
        from qat.opt import MaxCut

        graph = nx.path_graph(3)
        job = annealing._make_job(MaxCut(graph), "mpstraj", shots=16, aqo_time=2.0)
        # Local QutipQPU accepts SAMPLE only with nbshots=0 (exact probabilities).
        job.nbshots = 0
        result = QutipQPU(n_steps=30).submit(job)
        self.assertTrue(result.raw_data)
        score = annealing._score_from_result(result, graph)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, graph.number_of_edges())
        # A correct adiabatic schedule beats the random-cut mean of edges / 2.
        self.assertGreater(score, graph.number_of_edges() / 2)
        self.assertLess(
            score, max(annealing._cut_score(graph, sample.state) for sample in result)
        )

    def test_remote_resolution_failure_propagates_instead_of_saving_a_score(self):
        from qat.qlmaas import QLMaaSConnection
        from qat.qlmaas.result import AsyncResult

        pending = AsyncResult("offline-failure", MagicMock(spec=QLMaaSConnection))
        with (
            patch.object(AsyncResult, "join", side_effect=RuntimeError("Remote job failed")),
            patch.object(annealing, "_NB_INSTANCES_PER_SIZE", 1),
            self.assertRaisesRegex(RuntimeError, "Remote job failed"),
        ):
            annealing.run(
                SimpleNamespace(submit=lambda _job: pending), "mpstraj",
                initial_size=3, size_limit=3, beta=0.2, iterator="exhaustive",
                seed=42, shots=7, aqo_time=12.0,
            )
