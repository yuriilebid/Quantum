# Quantum drone demos (CS5250)

Two small **drone-themed** quantum optimization demos, split into separate folders.

## Layout

| Path | What it is |
|------|----------------|
| [`projects/two_qubit_micro_route/drone_route_quantum_demo.py`](projects/two_qubit_micro_route/drone_route_quantum_demo.py) | **Two-qubit** “pick the cheapest of four micro-routes” as a diagonal Pauli Hamiltonian + local VQE; optional **one** IBM `Estimator` job. |
| [`projects/drone_patrol_qaoa/drone_patrol_qaoa.py`](projects/drone_patrol_qaoa/drone_patrol_qaoa.py) | **Larger MaxCut / QAOA** “patrol sectors” graph: long **Aer statevector** classical search (budget wall time) vs optional **one** hardware ⟨−H⟩ readout. See [`projects/drone_patrol_qaoa/README.md`](projects/drone_patrol_qaoa/README.md) for honest timing claims. |
| [`run_demo.sh`](run_demo.sh) | Runs the two-qubit demo with `.venv/bin/python`. |
| [`run_patrol_qaoa.sh`](run_patrol_qaoa.sh) | Runs the patrol QAOA script. |
| [`requirements.txt`](requirements.txt) | Dependencies (`qiskit`, `qiskit-aer`, `qiskit-ibm-runtime`, …). |

Figures from the two-qubit demo live under [`projects/two_qubit_micro_route/quantum_demo_figures/`](projects/two_qubit_micro_route/quantum_demo_figures/).

Both demos accept **`--log-file PATH`**: stdout and stderr are mirrored to that UTF-8 text file while still printing to the terminal (each run overwrites the file).

---

## Two-qubit micro-route demo

A “drone” picks the cheapest of **four** routes, encoded as energies for `|00⟩…|11⟩`.

- **Classical baseline:** minimum over four numbers.
- **Hybrid part:** a **2-qubit** variational ansatz minimizes `⟨H⟩` (VQE-style).
- Optional `--ibm` sends **one** `Estimator` job after local optimization.

### Honest framing (NISQ)

For a toy **two-qubit** problem, classical is usually faster and more accurate. A fair story is **quantum-in-the-loop** on hardware and the **same optimization template** scaling to harder routing / scheduling research—not “speedup at two qubits.”

### Hamiltonian (diagonal in Z)

Given four route costs, build `H = c₀ II + c₁ ZI + c₂ IZ + c₃ ZZ` (rightmost Pauli character = qubit **0**).

### IBM Quantum

1. [IBM Quantum](https://quantum.ibm.com) → API token → `export QISKIT_IBM_TOKEN='…'`
2. List backends:  
   `.venv/bin/python projects/two_qubit_micro_route/drone_route_quantum_demo.py --list-backends`
3. Run:  
   `./run_demo.sh --ibm`  
   or pin `--backend ibm_sherbrooke` (names vary by account).

`QISKIT_IBM_INSTANCE` is optional for paid / multi-instance accounts.

### Environment and Conda

If both `(.venv)` and `(base)` show in your prompt, `python` may still be Conda’s. Prefer **`.venv/bin/python`**, **`./run_demo.sh`**, or `conda deactivate` until `(base)` is gone.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Plots (two-qubit demo)

```bash
.venv/bin/python projects/two_qubit_micro_route/drone_route_quantum_demo.py --plot
.venv/bin/python projects/two_qubit_micro_route/drone_route_quantum_demo.py --ibm --plot
```

Default figure directory: `projects/two_qubit_micro_route/quantum_demo_figures/`.

| File | Content |
|------|--------|
| `route_costs.png` | Four route costs; classical minimum highlighted |
| `vqe_energy_trace.png` | ⟨H⟩ vs COBYLA step (noiseless) |
| `ansatz_optimal.png` | Circuit at optimized angles |
| `energy_comparison.png` | Classical vs VQE vs IBM (if `--ibm`) |

### Implementation notes

- Local VQE uses `StatevectorEstimator` when available.
- IBM path: `generate_preset_pass_manager` + `EstimatorV2(mode=backend)` in job mode.
- Two-qubit ansatz: `real_amplitudes` with linear entanglement.

---

## Patrol QAOA (larger)

See [`projects/drone_patrol_qaoa/README.md`](projects/drone_patrol_qaoa/README.md). Quick smoke test:

```bash
.venv/bin/python projects/drone_patrol_qaoa/drone_patrol_qaoa.py --nodes 14 --classical-budget-sec 8
```
