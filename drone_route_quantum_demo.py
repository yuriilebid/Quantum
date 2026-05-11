#!/usr/bin/env python3
"""Two-qubit route-cost demo (classical vs VQE). See README.md for documentation."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

try:
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import real_amplitudes
    from qiskit.quantum_info import SparsePauliOp
except ModuleNotFoundError as exc:
    if exc.name == "qiskit" or (exc.name or "").startswith("qiskit"):
        print(
            "The `qiskit` package is not available for this Python interpreter.\n"
            f"  Executable: {sys.executable}\n"
            "  Install into the project venv:\n"
            "    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt\n"
            "  Run with:\n"
            "    .venv/bin/python drone_route_quantum_demo.py\n"
            "  If both Conda (base) and a venv are active, run `conda deactivate` first — "
            "otherwise `python` may point at Conda without qiskit.\n"
            "  See README.md.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    raise

try:
    from qiskit.primitives import StatevectorEstimator
except ImportError:
    from qiskit.primitives.estimator import Estimator as StatevectorEstimator


def route_costs_to_hamiltonian(energies: list[float]) -> SparsePauliOp:
    if len(energies) != 4:
        raise ValueError("Exactly four route costs are required.")
    e = np.array(energies, dtype=float)
    m = np.array(
        [
            [1, 1, 1, 1],
            [1, 1, -1, -1],
            [1, -1, 1, -1],
            [1, -1, -1, 1],
        ],
        dtype=float,
    )
    c0, c1, c2, c3 = np.linalg.solve(m, e)
    return SparsePauliOp.from_list(
        [
            ("II", float(c0)),
            ("ZI", float(c1)),
            ("IZ", float(c2)),
            ("ZZ", float(c3)),
        ]
    )


def classical_min_route(energies: list[float]) -> tuple[int, float]:
    k = int(np.argmin(energies))
    return k, float(energies[k])


def bitstrings_for_index(k: int) -> tuple[int, int]:
    return (k >> 1) & 1, k & 1


@dataclass
class VQEState:
    hamiltonian: SparsePauliOp
    ansatz: QuantumCircuit
    estimator: object


def make_vqe_energy_fn(state: VQEState):
    def energy(theta: np.ndarray) -> float:
        job = state.estimator.run([(state.ansatz, state.hamiltonian, theta.tolist())])
        return float(job.result()[0].data.evs)

    return energy


def run_local_vqe(h: SparsePauliOp, ansatz: QuantumCircuit, x0: np.ndarray) -> tuple[np.ndarray, float]:
    est = StatevectorEstimator()
    state = VQEState(h, ansatz, est)
    energy_fn = make_vqe_energy_fn(state)
    res = minimize(energy_fn, x0, method="COBYLA", options={"maxiter": 200})
    return res.x, float(res.fun)


def _ibm_runtime_service(instance: str | None):
    from qiskit_ibm_runtime import QiskitRuntimeService

    token = os.environ.get("QISKIT_IBM_TOKEN")
    if not token:
        raise SystemExit(
            "Set QISKIT_IBM_TOKEN, e.g. export QISKIT_IBM_TOKEN='…' "
            "(Quantum Platform → Account → API token)."
        )
    inst = instance if instance else os.environ.get("QISKIT_IBM_INSTANCE") or None
    if inst == "":
        inst = None
    return QiskitRuntimeService(
        channel="ibm_quantum_platform",
        token=token,
        instance=inst,
    )


def list_ibm_backends(instance: str | None) -> None:
    try:
        from qiskit.providers.exceptions import QiskitBackendNotFoundError
    except ImportError as e:
        raise SystemExit(
            "Install dependencies: pip install -r requirements.txt\n" + str(e)
        ) from e

    service = _ibm_runtime_service(instance)
    try:
        backs = service.backends(simulator=False, operational=True)
    except QiskitBackendNotFoundError:
        backs = []
    if not backs:
        print(
            "No operational real backends returned. Check your plan on the IBM Quantum website, "
            "or set QISKIT_IBM_INSTANCE to your hub/group/project CRN if you use a paid instance.",
            file=sys.stderr,
        )
        return
    print("Operational IBM Quantum backends (non-simulator) for this account:")
    for b in sorted(backs, key=lambda x: x.name):
        nq = getattr(b, "num_qubits", "?")
        print(f"  {b.name}  ({nq} qubits)")


def _resolve_backend(service, backend_name: str, instance: str | None):
    from qiskit.providers.exceptions import QiskitBackendNotFoundError

    inst = instance if instance else os.environ.get("QISKIT_IBM_INSTANCE") or None
    if inst == "":
        inst = None

    name = backend_name.strip()
    if name.lower() == "auto":
        return service.least_busy(
            min_num_qubits=2,
            simulator=False,
            operational=True,
            instance=inst,
        )
    try:
        return service.backend(name, instance=inst)
    except QiskitBackendNotFoundError as e:
        raise SystemExit(
            f"Backend {name!r} is not available to this account/instance.\n"
            "  Try:  --backend auto   (pick least busy with ≥2 qubits)\n"
            "  Or:   --list-backends  (print names you can use with --backend …)\n"
            "  Or set QISKIT_IBM_INSTANCE if your access is tied to a specific hub/group/project.\n"
            "  See README.md."
        ) from e


def run_ibm_single_energy(
    h: SparsePauliOp,
    ansatz: QuantumCircuit,
    theta: np.ndarray,
    backend_name: str,
    instance: str | None,
) -> tuple[float, str]:
    try:
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        from qiskit_ibm_runtime import EstimatorV2
    except ImportError as e:
        raise SystemExit(
            "Install dependencies: pip install -r requirements.txt\n" + str(e)
        ) from e

    service = _ibm_runtime_service(instance)
    backend = _resolve_backend(service, backend_name, instance)

    pm = generate_preset_pass_manager(backend=backend, optimization_level=2)
    bound = ansatz.assign_parameters(theta)
    isa = pm.run(bound)
    obs = h.apply_layout(isa.layout)

    estimator = EstimatorV2(mode=backend)
    job = estimator.run([(isa, obs)])
    evs = job.result()[0].data.evs
    return float(np.real(evs)), backend.name


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Two-qubit drone-style route choice as a ground-state / energy-minimization demo."
    )
    parser.add_argument(
        "--ibm",
        action="store_true",
        help="After local VQE, submit a single Estimator job to IBM Quantum.",
    )
    parser.add_argument(
        "--backend",
        type=str,
        default="auto",
        help='IBM Quantum backend name, or "auto" for least busy operational device with ≥2 qubits.',
    )
    parser.add_argument(
        "--instance",
        type=str,
        default=None,
        help="Optional IBM Quantum instance (hub/group/project CRN). "
        "Can also be set via QISKIT_IBM_INSTANCE.",
    )
    parser.add_argument(
        "--list-backends",
        action="store_true",
        help="List operational non-simulator backends for this account, then exit.",
    )
    args = parser.parse_args()

    if args.list_backends:
        list_ibm_backends(args.instance)
        return

    route_costs = [10.0, 3.0, 8.0, 12.0]
    h = route_costs_to_hamiltonian(route_costs)
    k_min, e_min = classical_min_route(route_costs)
    q1, q0 = bitstrings_for_index(k_min)

    print("=== Micro planning (robot / drone): cheapest of four routes ===")
    print(f"Route costs for |00>,|01>,|10>,|11>: {route_costs}")
    print(f"Classical optimum: index {k_min} (|q1 q0> = |{q1}{q0}>), energy {e_min:.6f}")
    print(f"Diagonal Hamiltonian (Pauli): {h}")

    ansatz = real_amplitudes(num_qubits=2, reps=2, entanglement="linear", insert_barriers=False)
    rng = np.random.default_rng(42)
    x0 = rng.uniform(-np.pi, np.pi, ansatz.num_parameters)

    theta_best, e_vqe = run_local_vqe(h, ansatz, x0)
    print("\n--- Local VQE (StatevectorEstimator, noiseless) ---")
    print(f"Minimum <H> after VQE: {e_vqe:.6f}")
    print(f"Ansatz parameters (angles): {np.round(theta_best, 4)}")

    gap = abs(e_vqe - e_min)
    print(f"Gap vs classical minimum: {gap:.6e}")

    if args.ibm:
        print("\n--- Single <H> readout on IBM Quantum ---")
        try:
            e_hw, resolved_backend = run_ibm_single_energy(
                h, ansatz, theta_best, args.backend, args.instance
            )
        except Exception as exc:
            print("IBM Runtime error:", exc, file=sys.stderr)
            raise
        print(f"Backend: {resolved_backend}")
        print(f"<H> on hardware: {e_hw:.6f}")
        print(f"Bias vs exact minimum: {abs(e_hw - e_min):.6f}")
        print(
            "\nFor slides: noise and decoherence shift the expectation; the workflow is the "
            "same family used for larger planning problems, where scalable quantum heuristics "
            "are researched — not “speedup” on two qubits."
        )


if __name__ == "__main__":
    main()
