"""
Define the IBMRealDevice device.

This makes use of a real IBM gate-based device, and returns only counts.
"""

from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime import Session, SamplerV2 as Sampler
from qiskit.transpiler import generate_preset_pass_manager


class IBMRealDevice:
    def __init__(self, name=""):
        '''Define hardware to access for experiments.'''
        match name:
            case "ibm_sherbrooke":
                pass
            case "ibm_brisbane":
                pass
            case _:
                raise NotImplementedError(
                    f"IBM access to {name=} is not yet available."
                )

        service = QiskitRuntimeService()
        self.device = service.backend(name)
        self.name = name

    def compute(self, circuits, num_shots):
        '''
        Run circuits on the device.

        Arguments:
            .circuits  : single/list of qiskit circuits)
            .num_shots : int, number of shots
        
        Returns:
            .all_counts : list of dict, each experimental results as counts 
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
            job = sampler.run(([(circuit_to_run, None, num_shots) for circuit_to_run in ltranspiled_circuits]))
    
        for k in range(len(transpiled_circuits)):
            counts = job.result()[k].data.cpos.get_counts()
            all_counts.append(counts)

        return all_counts
