"""
Define the IBMRealDevice device.

This makes use of a real IBM gate-based device, and returns counts.
"""

from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime import Batch, Session, SamplerV2 as Sampler
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
        """
        Define hardware to access for experiments.
        """
        if name not in _IBM_REAL_DEVICES:
            raise NotImplementedError(
                f"IBM access to {name=} is not available.\nConsider adding {name} to 'hardware/ibm_realdevice.py' or choose a device from {_IBM_REAL_DEVICES}."
            )

        service = QiskitRuntimeService()
        self.device = service.backend(name)
        self.name = name


    def compute(self, circuits, num_shots, params=[], use_session=False, optimization_level=1):
        """
        Run circuits on the device.

        Arguments:
            .circuits       -- single/list of qiskit circuits
            .num_shots      -- int, number of shots per circuit
            .params         -- list(float), circuit(s) parameters
            .use_session    -- bool, execute code using Session or not
            .optimization_level -- int, qiskit transpilation optimization level for preset manager
        
        Returns:
            .all_counts -- list(dict), each experimental results as counts 
        """
        all_counts = []
        pm = generate_preset_pass_manager(backend=self.device, optimization_level=optimization_level)

        if not isinstance(circuits, list):
            circuits = [circuits]

        if len(params) > 0:
            transpiled_circuits = [(pm.run(circ), params) for circ in circuits]
        else:
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
        
        
    def compute_batches(self, circuit_batches, num_shots, params=[], optimization_level=1):
        """
        Run circuits as batches on the device.

        Arguments:
            .circuit_batches    -- list(list of qiskit circuits), possibly parameterized
            .num_shots          -- int, number of shots
            .params             -- list(float), circuit(s) parameters
            .optimization_level -- int, qiskit transpilation optimization level for preset manager
        
        Returns:
            .all_counts -- list(list(dict)), batches of experimental results as counts
        """
        all_counts = []
        num_batches = len(circuit_batches)

        pm = generate_preset_pass_manager(backend=self.device, optimization_level=optimization_level)

        all_pubs = []
        for idx in range(num_batches):
            pubs_circuits = [pm.run(circ) for circ in circuit_batches[idx]]
            if len(params) > 0:
                pubs_circuits = [(circ, params) for circ in pubs_circuits]
            all_pubs.append(pubs_circuits)

        jobs = []
        with Batch(backend=self.device) as batch:
            sampler = Sampler(mode=batch)
            for idx in range(num_batches):
                job = sampler.run(pubs=all_pubs[idx], shots=num_shots)
                jobs.append(job)

        for idx in range(num_batches):
            counts_batch = []
            for k in range(len(circuit_batches[idx])):
                counts = jobs[idx].result()[k].data.cpos.get_counts()
                counts_batch.append(counts)
            all_counts.append(counts_batch)

        return all_counts
