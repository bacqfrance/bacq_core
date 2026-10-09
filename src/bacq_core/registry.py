"""
List of all available benchmark protocols.
"""

from benchmarks import qws
from benchmarks import vqls

benchmarks_registry = {
    "qws": qws,
    "vqls": vqls,
}

# benchmarks relying on an optional external package (see pyproject.toml extras)
try:
    from benchmarks import mbqs
    benchmarks_registry["mbqs"] = mbqs
except ImportError as error:
    _MBQS_IMPORT_ERROR = error


def get_benchmark_module(benchmark_name):
    if benchmark_name == "mbqs" and "mbqs" not in benchmarks_registry:
        raise ImportError(
            f"Benchmark mbqs requires the optional dependencies: pip install -e '.[mbqs]'\n({_MBQS_IMPORT_ERROR})"
        )
    return benchmarks_registry[benchmark_name]
