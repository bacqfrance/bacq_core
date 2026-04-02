"""
Define the IBMSimulator device.

This emulates an IBM gate-based device, and returns only counts.
"""

from qiskit.providers.basic_provider import BasicSimulator
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import Session, SamplerV2 as Sampler


class IBMSimulator:
    def __init__(self, name="BasicSimulator"):
        '''Define simulator selected for experiments.'''
        match name:
            case "BasicSimulator":
                self.device = BasicSimulator()
            case "FakeMarrakesh":
                self.device = FakeMarrakesh()
            case _:
                raise NotImplementedError(
                    f"IBM simulator {name=} is not yet available. Consider using 'BasicSimulator'."
                )
        self.name = name

    def compute(self, circuits, num_shots):
        '''
        Run circuits on the device.

        Arguments:
            .circuits  -- single/list of qiskit circuits)
            .num_shots -- int, number of shots
        
        Returns:
            .all_counts -- list of dict, each experimental results as counts 
        '''
        all_counts = []
        pm = generate_preset_pass_manager(backend=self.device, optimization_level=1)

        if not isinstance(circuits, list):
            circuits = [circuits]

        transpiled_circuits = []
        for circuit in circuits:
            transpiled_circuits.append(pm.run(circuit))

        with Session(backend=self.device) as session:
            sampler = Sampler(mode=session)
            job = sampler.run(([(circuit_to_run, None, num_shots) for circuit_to_run in transpiled_circuits]))
    
        for k in range(len(transpiled_circuits)):
            counts = job.result()[k].data.cpos.get_counts()
            all_counts.append(counts)

        return all_counts
