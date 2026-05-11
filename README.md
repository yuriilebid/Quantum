# Drone route quantum demo

## What this is

A small **robotics-flavored** example: a “drone” picks the cheapest of **four micro-routes**, encoded as energies for the two-qubit computational basis states `|00>`, `|01>`, `|10>`, `|11>`.

- **Classical baseline:** pick the minimum cost instantly.
- **Hybrid quantum part:** a **2-qubit variational ansatz** minimizes `⟨H⟩` (same structure as VQE / QAOA-style workflows).

The script `drone_route_quantum_demo.py` implements this. Optional `--ibm` sends **one** `Estimator` job to IBM Quantum after local optimization (avoids hundreds of queued jobs during VQE).

## Honest framing for talks

On today’s **NISQ** hardware, for a toy problem this small, **classical methods are usually faster and more accurate**. A fair “advantage” story is not “quantum is faster on two qubits,” but:

1. Showing a real **quantum-in-the-loop** pipeline on hardware.
2. The same **combinatorial / optimization formulation** scales in research toward larger graphs and, in the long term, fault-tolerant systems.

Noise and decoherence shifting `⟨H⟩` on a real chip is a feature for a slide: **physics**, not failure of the idea.

## Hamiltonian (diagonal in the Z basis)

Given four energies `E_00, E_01, E_10, E_11` for the basis states, we build

`H = c₀ II + c₁ ZI + c₂ IZ + c₃ ZZ`

using Qiskit’s Pauli string convention: the **rightmost** character is qubit **0**.

Solving the linear system recovers `c₀ … c₃` so the eigenvalues on `|00>…|11>` match the four route costs.

## Index to bitstrings

Index `k ∈ {0,1,2,3}` maps to `|q₁ q₀>` as:

- `q₀ = k & 1`
- `q₁ = (k >> 1) & 1`

## IBM Quantum usage

1. Create an account at [IBM Quantum](https://quantum.ibm.com) and create an **API token** (Account → API token).
2. Export it: `export QISKIT_IBM_TOKEN='…'`
3. See which real devices your plan can use (names change by region/plan):

   ```bash
   .venv/bin/python drone_route_quantum_demo.py --list-backends
   ```

4. Run on hardware. By default the script uses **`--backend auto`**, which picks an **operational, non-simulator** system with at least **2 qubits** and the **shortest queue** (`least_busy`). You can still pin a name from the list:

   ```bash
   .venv/bin/python drone_route_quantum_demo.py --ibm
   .venv/bin/python drone_route_quantum_demo.py --ibm --backend ibm_sherbrooke
   ```

If you see `No backend matches the criteria` for a specific name (e.g. `ibm_kyiv`), that system is **not on your instance** or is unavailable — use `--list-backends` or `auto`.

Paid / multi-instance accounts can set the instance explicitly:

```bash
export QISKIT_IBM_INSTANCE='hub/group/project'   # or the CRN string from the IBM console
# or per run:
.venv/bin/python drone_route_quantum_demo.py --ibm --instance '…'
```

## Environment and Conda

If your prompt shows **both** `(.venv)` and `(base)`, `python` may still point at **Conda’s** interpreter (without Qiskit). Fix by:

- `conda deactivate` until `(base)` is gone, then activate the venv; or  
- Always call **`.venv/bin/python`** explicitly; or  
- Use **`./run_demo.sh`**, which invokes `.venv/bin/python` directly.

Install dependencies once:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Files

| File | Role |
|------|------|
| `drone_route_quantum_demo.py` | Main demo |
| `run_demo.sh` | Runs the demo with the project venv’s Python |
| `requirements.txt` | Python dependencies |

## Implementation notes

- On older Qiskit builds, the script falls back to `qiskit.primitives.estimator.Estimator` if `StatevectorEstimator` is not importable from `qiskit.primitives`.
- **Local VQE** uses `StatevectorEstimator` (noiseless exact expectation values).
- **IBM path** uses `generate_preset_pass_manager(backend=…)` and `EstimatorV2(mode=backend)` in **job mode** (no `Session`), which is usually simpler on free-tier access than session mode.
- The ansatz is `real_amplitudes` with linear entanglement (Qiskit circuit library).
