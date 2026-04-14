"""
Define the IBMRealDevice device.

This makes use of a real IBM gate-based device, and returns only counts.
"""

from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime import Session, SamplerV2 as Sampler
from qiskit.transpiler import generate_preset_pass_manager

_IBM_REAL_DEVICES = [
    "ibm_fez",
    "ibm_marrakesh",
    "ibm_kingston",
    "ibm_boston",
    "ibm_pittsburgh",
    "ibm_miami",
]


class IBMRealDevice:
    def __init__(self, name=""):
        '''
        Define hardware to access for experiments.
        '''

        if name not in _IBM_REAL_DEVICES:
            raise NotImplementedError(
                f"IBM access to {name=} is not available.\nConsider adding {name} to 'hardware/ibm_realdevice.py' or choose a device from {_IBM_REAL_DEVICES}."
            )

        service = QiskitRuntimeService()
        self.device = service.backend(name)
        self.name = name

    def compute(self, circuits, num_shots, use_session=True):
        '''
        Run circuits on the device.

        Arguments:
            .circuits   : single/list of qiskit circuits)
            .num_shots  : int, number of shots
            .use_session: bool, execute code using Session or not
        
        Returns:
            .all_counts : list of dict, each experimental results as counts 
        '''
        all_counts = []
        pm = generate_preset_pass_manager(backend=self.device, optimization_level=1)

        if not isinstance(circuits, list):
            circuits = [circuits]

        transpiled_circuits = [pm.run(circ) for circ in circuits]
        
        if not use_session:
            sampler = Sampler(mode=self.device)
            job = sampler.run(transpiled_circuits, shots=num_shots)
        else:
            with Session(backend=self.device) as session:
                sampler = Sampler(mode=session)
                job = sampler.run(transpiled_circuits, shots=num_shots)
    
        for k in range(len(transpiled_circuits)):
            counts = job.result()[k].data.cpos.get_counts()
            all_counts.append(counts)

        return all_counts
