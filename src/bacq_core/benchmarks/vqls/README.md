# Variational Quantum Linear Solver (VQLS) Benchmark
This folder includes VQLS-specific scripts.

## The 1D-Poisson equation
For benchmarking purposes, we consider the steady-state hea equation which can be described by the 1D Laplace equation, with Dirichlet boundary conditions, such that

```math
\forall x\in [0,L], \quad -\nabla^2u(x) = V \quad \text{ with } \quad u(0) = u(L) = 0.
```

Upon discretization of the domain into a grid of $N$ cells using the finite difference method, this problem corresponds to solving the linear system $Ax = b$ with

```math
A(i,j) = 2 \quad \text{ if } i=j,
```
```math
A(i,j) = -1 \quad \text{ if } |i-j|=1,
```
```math
A(i,j) = 2 \quad \text{ otherwise}
```

and

```math
b(i) = V \quad \forall i.
```

The criteria for success on a problem instance of size $n$, i.e. a matrix $A$ of size $2^n\times 2^n$, is:

"Finding $x_\text{quantum}$ such that $1-F = 1-|\langle x_\text{quantum}|x_\text{sol}\rangle| \leq \varepsilon$."

In this protocol, $\varepsilon$ is arbitrarily set to 0.05.

## Metrics definition and Score evaluation
The metric is therefore the fidelity (or rather $\sqrt{F}$, representing geometrical distance) between the observed quantum state resulting from solving the linear system with VQLS, and the state corresponding to the theoretical classical solution.

The overall score is defined as the largest problem size $n$ for which the criteria for success is successfully met before a first failure.

## Code structure
Some files are required for all benchmarks so that these benchmarks can be successfully evaluated and experiments successfully conducted.
- `__init__.py`: defines benchmark-specific protocol parameters (here VQLS) based on the benchmark-agnostic parameter class.
- `evaluate.py`: defines functions used to access metric and score computation from the package of the specific benchmark (here VQLS).
- `experiment.py`: defines a global `run()` function, a global structure for experiment data, and ensures the benchmark-specific protocol (here VQLS) is well applied.
- `view.py`: defines two global strings, formatted to display the results of the specific benchmark (here VQLS).

Although their content vary depending on the protocol, these files are required within all benchmark folders, along with aforementioned variables and functions.

Additional benchmark-specific files are proposed:
- `helpers_instance.py`: defines functions to generate the relevant matrix instance.
- `helpers_protocol.py`: defines functions to ensure the VQLS protocol is well applied.
- `helpers_qiskit.py`: defines functions to build the algorithm circuits using qiskit.

Depending on the selected hardware platform, the end user is welcome to propose and additional file (i.e. helpers_nameplatform using myqlm, cirq, etc...) and develop the algorithm construction intended for a new platform and use it for the benchmark evaluation.

## How to use within the BACQ library
This folder proposes an implementation that allows for the direct evaluation of qiskit-available hardware, especially IBM QPU.

**Run benchmark experiments on already implemented QPU:**
1) ensure the `.json` input file contains `"benchmark": "vqls"`.
2) ensure the `.json` input file includes `"device": {device_name}`.

**Run benchmark experiments on a new IBM device:**
1) ensure the `.json` input file contains `"benchmark": "vqls"`.
2) ensure the `.json` input file includes `"device": {device_name}`.
3) add `{device_name}` to the list of available IBM devices in `hardware/ibm_realdevice.py` (or `hardware/ibm_simulator.py`).

**Run benchmark experiments on a device from a new provider:**
1) ensure the `.json` input file contains `"benchmark": "vqls"`.
2) ensure the `.json` input file includes `"device": {device_name}`.
3) create a new file `hardware/newprovider_realdevice.py` on the example of existing files:
	-	include a list of available QPU (with `{device_name}`),
	-	include a new class (i.e. `NewProviderRealDevice()`),
	-	defines QPU access (authentification, etc.),
	-	defines a `compute()` method to manage job submissions.
4) adapt the `experiment.py` file:
	-	in `run()`: initialize the hardware class for newly available QPU,
	-	**(if necessary)** create a new `run_newsoftwarestack()` function based on the `run_qiskit()` example,
	-	**(if necessary)** create a new file `helpers_newsoftwarestack.py` to construct the algorithm using this new software stack while ensuring the protocol requirements are met.


*Note*: Running experiments on real QPU requires that a QPU access can be established by the end-user.

## Author
Noe OLIVIER, cortAIx Labs, Thales, France
