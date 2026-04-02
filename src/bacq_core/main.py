"""
Main script to conduct a benchmark protocol.
"""

from pathlib import Path
import argparse
import os
import sys
import json
from runner import run_benchmark, run_benchmark_sequence, check_protocol_parameters, display_text, display_text_seq


json_path = str((Path(__file__).parent.parent.parent).resolve()) + '/examples'

if json_path not in sys.path:
    sys.path.insert(1, json_path)


def arg_parser():
    """
    Define arguments given in command line.
    """
    description = "Command line for BACQ benchmark runs."

    parser = argparse.ArgumentParser(prog="bacq", description=description)

    parser.add_argument("input_file", help=f"""
        Read json file that is either:
           1) protocol file: benchmark protocol parameters for run on hardware and score computation.
           2) experiment file: benchmark experiment data for score computation.
        """)

    return parser

def main(args):
    """
    Runs the benchmark protocol from the relevant input file.
    """
    code = os.EX_OK

    input_file = Path(json_path) / args.input_file

    with open(input_file) as f:
        input_data = json.load(f)

    filetype = input_data["filetype"]
    benchmark = input_data["benchmark"]
    device = input_data["device"]
    parameters = input_data["parameters"]
    sequence_parameters = input_data.get("sequence_parameters", None)

    match filetype:
        case "protocol":
            check_protocol_parameters(benchmark, parameters)
            benchmark_data = run_benchmark(benchmark, device, parameters)

            benchmark_filename = 'result_' + benchmark_data['metadata']['benchmark'] + '_' + benchmark_data['metadata']['device'] + '_' + benchmark_data['metadata']['date']
            with open(benchmark_filename + '.json', 'w') as f:
                json.dump(benchmark_data, f, indent=4)

            text = display_text(benchmark, benchmark_data)
            print(text)
            pass

        case "protocol_seq":
            check_protocol_parameters(benchmark, parameters, sequence_parameters)
            benchmark_seq_data = run_benchmark_sequence(benchmark, device, parameters, sequence_parameters=sequence_parameters)

            benchmark_seq_filename = 'results_' + benchmark_seq_data['metadata']['benchmark'] + '_' + benchmark_seq_data['metadata']['device'] + '_' + benchmark_seq_data['metadata']['date']
            with open(benchmark_seq_filename + '.json', 'w') as f:
                json.dump(benchmark_seq_data, f, indent=4)

            text = display_text_seq(benchmark, benchmark_seq_data)
            print(text)
            pass

        case "experiment":
            benchmark_data = run_benchmark(benchmark, device, parameters, exp_data=input_data)

            benchmark_filename = 'result_' + benchmark_data['metadata']['benchmark'] + '_' + benchmark_data['metadata']['device'] + '_' + benchmark_data['metadata']['date']
            with open(benchmark_filename + '.json', 'w') as f:
                json.dump(benchmark_data, f, indent=4)

            text = display_text(benchmark, benchmark_data)
            print(text)
            pass

        case "experiment_seq":
            benchmark_seq_data = run_benchmark_sequence(benchmark, device, parameters, exp_data_seq=input_data)

            benchmark_seq_filename = 'results_' + benchmark_seq_data['metadata']['benchmark'] + '_' + benchmark_seq_data['metadata']['device'] + '_' + benchmark_seq_data['metadata']['date']
            with open(benchmark_seq_filename + '.json', 'w') as f:
                json.dump(benchmark_seq_data, f, indent=4)

            text = display_text_seq(benchmark, benchmark_seq_data)
            print(text)
            pass

        case _:
            raise NotImplementedError(
                f"Input {filetype = } is not accepted. Expected 'protocol', 'protocol_seq', 'experiment' or 'experiment_seq'."
                )

    return code


if __name__ == "__main__":

    parser = arg_parser()
    args = parser.parse_args(sys.argv[1:])

    code = main(args)
    sys.exit(code)
