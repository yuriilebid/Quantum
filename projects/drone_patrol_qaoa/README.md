# Drone patrol QAOA (MaxCut)

“Patrol sectors” are vertices; interference / reward for separating drones on an edge is a **MaxCut** edge. The cost Hamiltonian is the usual Ising form so, on a computational basis state, **⟨H⟩ equals the cut weight**. QAOA minimizes **⟨−H⟩** so good angles tend to favor large cuts.

## What is “fast quantum” here (important)

This script is honest about the comparison:

- **Long classical phase (`--classical-mode aer-vqe`, default):** your laptop runs **many** Aer **statevector** expectation evaluations while COBYLA searches angles. Each evaluation simulates the full wavefunction — that is why wall time can reach tens of minutes with `--classical-budget-sec 1800`.

- **Optional `--ibm`:** submits **one** compiled `EstimatorV2` job at the best angles. The **device execution** of that circuit is short; **queue time on IBM Quantum is not included** and can dominate in real life.

This is **not** a mathematical proof that quantum computers asymptotically beat the best classical algorithms for MaxCut. It **is** a realistic workflow story: heavy classical circuit simulation vs a single hardware expectation readout.

## Exhaustive mode

`--classical-mode exhaustive` uses a chunked scan over all `2^n` assignments (numpy). Runtime scales as **Θ(2^n · |E|)** per graph pass. Rough guide on a modern laptop: `n≈26` is on the order of tens of seconds per pass; `n≈27–28` minutes; beyond that grows quickly. The script repeats random graphs until `--classical-budget-sec` elapses. That mode does **not** keep a graph instance for QAOA/IBM (use `aer-vqe` for hardware).

## Examples

From the repo root (after `pip install -r requirements.txt`):

```bash
# Quick smoke test (~5–30s depending on CPU)
.venv/bin/python projects/drone_patrol_qaoa/drone_patrol_qaoa.py --nodes 14 --classical-budget-sec 8

# Default-ish long classical (~30 min) then optional IBM (needs token + enough qubits)
export QISKIT_IBM_TOKEN='…'
.venv/bin/python projects/drone_patrol_qaoa/drone_patrol_qaoa.py --nodes 18 --classical-budget-sec 1800 --ibm

# Long exact classical only (pick --exhaustive-nodes for your patience)
.venv/bin/python projects/drone_patrol_qaoa/drone_patrol_qaoa.py --classical-mode exhaustive --exhaustive-nodes 27 --classical-budget-sec 1800
```

Or `./run_patrol_qaoa.sh …` from the repo root.
