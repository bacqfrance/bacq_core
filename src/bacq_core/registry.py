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


def get_benchmark_module(benchmark_name):
    return benchmarks_registry[benchmark_name]
