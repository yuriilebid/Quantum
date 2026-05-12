---
session_date: "2026-05-11"
repo: Quantum drone demos (CS5250)
host: MacBookAir
user: yuriilebid
shell: "(base) … Quantum %"
runs_total: 9
ibm:
  backend: ibm_fez
  instance_plan: open-instance / open
security:
  token_export_line: omitted_redacted
  note: "If this token was ever pasted into chat, email, or a repo, revoke it in IBM Quantum → Account → API token and create a new one."
---

# Structured presentation run log

Parsed from a terminal transcript. **Do not** add real `QISKIT_IBM_TOKEN` values to version control.

---

## Run 1 — `./run_demo.sh`

**Command**

```bash
./run_demo.sh
```

**Program:** `projects/two_qubit_micro_route/drone_route_quantum_demo.py` (via wrapper)

**Metrics**

| Field | Value |
|--------|--------|
| route_costs | [10.0, 3.0, 8.0, 12.0] |
| classical_optimum_index | 1 |
| classical_optimum_bitstring | \|q1 q0⟩ = \|01⟩ |
| classical_optimum_energy | 3.000000 |
| hamiltonian_pauli | SparsePauliOp II, ZI, IZ, ZZ coeffs 8.25, −1.75, 0.75, 2.75 |
| vqe_minimum_H | 3.000000 |
| vqe_angles | [2.7191, 0.9192, 3.5832, 1.3401, −2.8721, 2.7769] |
| gap_vs_classical | 3.145764e−09 |

**Raw output**

```text
=== Micro planning (robot / drone): cheapest of four routes ===
Route costs for |00>,|01>,|10>,|11>: [10.0, 3.0, 8.0, 12.0]
Classical optimum: index 1 (|q1 q0> = |01>), energy 3.000000
Diagonal Hamiltonian (Pauli): SparsePauliOp(['II', 'ZI', 'IZ', 'ZZ'],
              coeffs=[ 8.25+0.j, -1.75+0.j,  0.75+0.j,  2.75+0.j])

--- Local VQE (StatevectorEstimator, noiseless) ---
Minimum <H> after VQE: 3.000000
Ansatz parameters (angles): [ 2.7191  0.9192  3.5832  1.3401 -2.8721  2.7769]
Gap vs classical minimum: 3.145764e-09
```

---

## Run 2 — two-qubit demo + plots

**Command**

```bash
.venv/bin/python projects/two_qubit_micro_route/drone_route_quantum_demo.py --plot
```

**Metrics:** Same numerical results as Run 1.

**Artifacts**

- Figures directory: `projects/two_qubit_micro_route/quantum_demo_figures`

**Raw output**

```text
=== Micro planning (robot / drone): cheapest of four routes ===
Route costs for |00>,|01>,|10>,|11>: [10.0, 3.0, 8.0, 12.0]
Classical optimum: index 1 (|q1 q0> = |01>), energy 3.000000
Diagonal Hamiltonian (Pauli): SparsePauliOp(['II', 'ZI', 'IZ', 'ZZ'],
              coeffs=[ 8.25+0.j, -1.75+0.j,  0.75+0.j,  2.75+0.j])

--- Local VQE (StatevectorEstimator, noiseless) ---
Minimum <H> after VQE: 3.000000
Ansatz parameters (angles): [ 2.7191  0.9192  3.5832  1.3401 -2.8721  2.7769]
Gap vs classical minimum: 3.145764e-09

Saved figures under: /Users/yuriilebid/Desktop/CS5250/Quantum/projects/two_qubit_micro_route/quantum_demo_figures
```

---

## Run 3 — two-qubit demo + IBM (token missing)

**Command**

```bash
.venv/bin/python projects/two_qubit_micro_route/drone_route_quantum_demo.py --ibm
```

**Outcome:** Script exited with message to set `QISKIT_IBM_TOKEN` (token was empty).

**Raw output (excerpt)**

```text
--- Single <H> readout on IBM Quantum ---
Set QISKIT_IBM_TOKEN, e.g. export QISKIT_IBM_TOKEN='…' (Quantum Platform → Account → API token).
```

---

## Run 4 — set token (redacted)

**Command (do not store real secrets)**

```bash
export QISKIT_IBM_TOKEN='<REDACTED — set locally only>'
```

**Note:** `echo $QISKIT_IBM_TOKEN` showed empty before export; after export, IBM runs succeeded.

---

## Run 5 — two-qubit demo + IBM (success)

**Command**

```bash
.venv/bin/python projects/two_qubit_micro_route/drone_route_quantum_demo.py --ibm
```

**Metrics**

| Field | Value |
|--------|--------|
| vqe_minimum_H | 3.000000 |
| classical_minimum | 3.000000 |
| ibm_backend | ibm_fez |
| H_hardware | 3.189838 |
| bias_vs_exact_minimum | 0.189838 |

**Warnings (stderr):** QiskitRuntimeService instance discovery (open-instance, open plan).

**Raw output (excerpt)**

```text
Backend: ibm_fez
<H> on hardware: 3.189838
Bias vs exact minimum: 0.189838

For slides: noise and decoherence shift the expectation; the workflow is the same family used for larger planning problems, where scalable quantum heuristics are researched — not "speedup" on two qubits.
```

---

## Run 6 — two-qubit demo + IBM + plot

**Command**

```bash
.venv/bin/python projects/two_qubit_micro_route/drone_route_quantum_demo.py --ibm --plot
```

**Metrics**

| Field | Value |
|--------|--------|
| H_hardware | 3.181989 |
| bias_vs_exact_minimum | 0.181989 |
| ibm_backend | ibm_fez |

**Artifacts:** Same figure directory as Run 2.

---

## Run 7 — patrol QAOA (short Aer budget)

**Command**

```bash
.venv/bin/python projects/drone_patrol_qaoa/drone_patrol_qaoa.py --nodes 14 --classical-budget-sec 15
```

**Metrics**

| Field | Value |
|--------|--------|
| classical_mode | aer-vqe |
| budget_requested_s | 15 |
| wall_time_classical_s | 17.6 |
| sectors_n | 14 |
| edges_E | 27 |
| qaoa_reps | 2 |
| aer_energy_evaluations | 649 |
| best_min_neg_H | −18.522809 |
| exact_max_cut | 21.000000 |
| exact_assignment | 126 |
| heuristic_H_at_best_angles_Aer | 18.522809 |

---

## Run 8 — patrol QAOA (long Aer budget)

**Command**

```bash
.venv/bin/python projects/drone_patrol_qaoa/drone_patrol_qaoa.py --nodes 18 --classical-budget-sec 1000
```

**Metrics**

| Field | Value |
|--------|--------|
| budget_requested_s | 1000 |
| wall_time_classical_s | 1011.0 |
| sectors_n | 18 |
| edges_E | 47 |
| aer_energy_evaluations | 5203 |
| best_min_neg_H | −30.557068 |
| exact_max_cut | 34.000000 |
| exact_assignment | 79134 |
| heuristic_H_at_best_angles_Aer | 30.557068 |

---

## Run 9 — patrol QAOA + IBM

**Command**

```bash
.venv/bin/python projects/drone_patrol_qaoa/drone_patrol_qaoa.py --nodes 18 --classical-budget-sec 10 --ibm
```

**Metrics**

| Field | Value |
|--------|--------|
| budget_requested_s | 10 |
| wall_time_classical_s | 17.0 |
| aer_energy_evaluations | 121 |
| best_min_neg_H | −24.755126 |
| exact_max_cut | 34.000000 |
| exact_assignment | 79134 |
| heuristic_H_Aer | 24.755126 |
| ibm_backend | ibm_fez |
| neg_H_hardware | −23.830050 |

**Note:** Exact max cut (34) is for the **same** 18-node graph instance; Aer/IBM ⟨H⟩ / ⟨−H⟩ are **expectations** of the QAOA state, not guaranteed to match the cut of a single bitstring.

---

## JSON summary (copy-friendly)

```json
{
  "runs": [
    {"id": 1, "script": "two_qubit", "flags": [], "E_classical": 3.0, "E_vqe": 3.0},
    {"id": 2, "script": "two_qubit", "flags": ["--plot"], "E_classical": 3.0, "E_vqe": 3.0},
    {"id": 3, "script": "two_qubit", "flags": ["--ibm"], "error": "missing_token"},
    {"id": 5, "script": "two_qubit", "flags": ["--ibm"], "backend": "ibm_fez", "H_hw": 3.189838, "bias": 0.189838},
    {"id": 6, "script": "two_qubit", "flags": ["--ibm", "--plot"], "H_hw": 3.181989, "bias": 0.181989},
    {"id": 7, "script": "patrol", "flags": ["--nodes", "14", "--classical-budget-sec", "15"], "n": 14, "|E|": 27, "aer_evals": 649, "max_cut": 21},
    {"id": 8, "script": "patrol", "flags": ["--nodes", "18", "--classical-budget-sec", "1000"], "n": 18, "|E|": 47, "aer_evals": 5203, "max_cut": 34},
    {"id": 9, "script": "patrol", "flags": ["--nodes", "18", "--classical-budget-sec", "10", "--ibm"], "neg_H_hw": -23.83005, "backend": "ibm_fez"}
  ]
}
```
