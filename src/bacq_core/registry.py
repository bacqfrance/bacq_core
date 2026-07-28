"""
List of all available benchmark protocols.
"""

from benchmarks import qws
from benchmarks import vqls

benchmarks_registry = {
    "qws": qws,
    "vqls": vqls,
}


def get_benchmark_module(benchmark_name):
    return benchmarks_registry[benchmark_name]
