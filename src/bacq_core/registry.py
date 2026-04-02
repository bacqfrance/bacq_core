"""
List of all available benchmark protocols.
"""

from benchmarks import qws

benchmarks_registry = {
    "qws": qws,
}


def get_benchmark_module(benchmark_name):
    return benchmarks_registry[benchmark_name]
