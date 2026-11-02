"""Display strings for BACQ QScore results."""

benchmark_txt = """
***** BACQ-OP-QSCORE (myQLM emulator) *****

Device: {device}
Date experiment: {date}

Benchmark parameters:
- Initial graph size: {initial_size}
- Maximum graph size: {size_limit}
- QScore threshold (beta): {beta}
- Search method: {iterator}
- QAOA depth: {depth}
- Random seed: {seed}

Benchmark result:
- QScore boundary or bound: {metric}
- Boundary resolved exactly: {success}
"""

benchmark_seq_txt = """
***** BACQ-OP-QSCORE (myQLM emulator) *****

QScore performs its graph-size search internally. Use a single protocol input,
not a BACQ protocol sequence.
"""
