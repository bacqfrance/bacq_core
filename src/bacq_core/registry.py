"""
List of all available benchmark protocols.
"""

from benchmarks import qws
from benchmarks import vqls
from benchmarks import mnr

benchmarks_registry = {
    "qws": qws,
    "vqls": vqls,
    "mnr": mnr,
}

# benchmarks relying on an optional external package (see pyproject.toml extras)
try:
    from benchmarks import mbqs
    benchmarks_registry["mbqs"] = mbqs
except ImportError as error:
    _MBQS_IMPORT_ERROR = error

try:
    from benchmarks import qscore
    benchmarks_registry["qscore"] = qscore
except ImportError as error:
    _QSCORE_IMPORT_ERROR = error


def get_benchmark_module(benchmark_name):
    if benchmark_name == "mbqs" and "mbqs" not in benchmarks_registry:
        raise ImportError(
            f"Benchmark mbqs requires the optional dependencies: pip install -e '.[mbqs]'\n({_MBQS_IMPORT_ERROR})"
        )
    if benchmark_name == "qscore" and "qscore" not in benchmarks_registry:
        raise ImportError(
            f"Benchmark qscore requires the optional dependencies: pip install -e '.[qscore]'\n({_QSCORE_IMPORT_ERROR})"
        )
    return benchmarks_registry[benchmark_name]
