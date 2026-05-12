#!/usr/bin/env python3
"""Drone patrol sector scheduling as MaxCut + QAOA (heavy classical sim vs short hardware job).

See README in this folder for honest framing: this compares *many expensive statevector
simulations on a laptop* to *one compiled execution on a quantum processor*, not a proof
of asymptotic quantum speedup.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

import numpy as np
from qiskit import transpile
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import QAOAAnsatz
from qiskit.quantum_info import SparsePauliOp
from scipy.optimize import minimize

try:
    from qiskit_aer.primitives import EstimatorV2 as AerEstimatorV2
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Install qiskit-aer in the project venv:\n"
        "  .venv/bin/pip install -r requirements.txt\n"
        f"  ({exc})"
    ) from exc


def _run_log():
    p = Path(__file__).resolve().parent.parent
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
    import run_log  # noqa: PLC0415

    return run_log


def random_patrol_graph(n: int, edge_prob: float, rng: np.random.Generator) -> list[tuple[int, int, float]]:
    """Undirected weighted edges (i, j, w) with i < j — 'interference' between sectors."""
    edges: list[tuple[int, int, float]] = []
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() < edge_prob:
                edges.append((i, j, 1.0))
    if not edges:
        edges.append((0, 1, 1.0))
    return edges


def maxcut_hamiltonian(n: int, edges: list[tuple[int, int, float]]) -> SparsePauliOp:
    """Standard Ising / ZZ form so ⟨H⟩ on a computational basis state equals the cut weight."""
    coeffs: dict[str, float] = defaultdict(float)
    const = 0.0
    for i, j, w in edges:
        const += 0.5 * w
        s = list("I" * n)
        s[n - 1 - i] = "Z"
        s[n - 1 - j] = "Z"
        coeffs["".join(s)] -= 0.5 * w
    labels = [(k, v) for k, v in coeffs.items() if abs(v) > 1e-12]
    if abs(const) > 1e-12:
        labels.append(("I" * n, const))
    return SparsePauliOp.from_list(labels)


def maxcut_value(n: int, edges: list[tuple[int, int, float]], assignment: int) -> float:
    total = 0.0
    for i, j, w in edges:
        bi = (assignment >> i) & 1
        bj = (assignment >> j) & 1
        total += w * float(bi ^ bj)
    return total


def exhaustive_maxcut(
    n: int,
    edges: list[tuple[int, int, float]],
    chunk_bits: int = 20,
) -> tuple[float, int, float]:
    """Return (best_cut, best_assignment_mask, wall_seconds). Chunked over assignments."""
    t0 = time.perf_counter()
    best = -1.0
    best_a = 0
    total = 1 << n
    chunk = 1 << min(chunk_bits, n)
    ei = [e[0] for e in edges]
    ej = [e[1] for e in edges]
    ew = [e[2] for e in edges]
    for start in range(0, total, chunk):
        end = min(start + chunk, total)
        a = np.arange(start, end, dtype=np.uint64)
        cut = np.zeros(len(a), dtype=np.float64)
        for k in range(len(ei)):
            bi = (a >> ei[k]) & np.uint64(1)
            bj = (a >> ej[k]) & np.uint64(1)
            cut += ew[k] * (bi ^ bj).astype(np.float64)
        mx = float(cut.max())
        if mx > best:
            best = mx
            best_a = int(a[int(cut.argmax())])
    return best, best_a, time.perf_counter() - t0


def run_exhaustive_until_budget(
    n: int,
    edge_prob: float,
    rng: np.random.Generator,
    budget_sec: float,
) -> tuple[float, int, int, float]:
    """Repeat random graphs until wall time >= budget. Returns (best_cut, best_a, num_passes, seconds)."""
    t0 = time.perf_counter()
    global_best = -1.0
    global_a = 0
    passes = 0
    while time.perf_counter() - t0 < budget_sec:
        edges = random_patrol_graph(n, edge_prob, rng)
        c, a, _ = exhaustive_maxcut(n, edges)
        passes += 1
        if c > global_best:
            global_best, global_a = c, a
    return global_best, global_a, passes, time.perf_counter() - t0


def make_aer_energy_fn(
    isa: QuantumCircuit,
    obs_minimize: SparsePauliOp,
    eval_counter: list[int] | None = None,
) -> Callable[[np.ndarray], float]:
    est = AerEstimatorV2(options={"backend_options": {"method": "statevector"}})

    def energy(theta: np.ndarray) -> float:
        if eval_counter is not None:
            eval_counter[0] += 1
        qc = isa.assign_parameters(theta)
        job = est.run([(qc, obs_minimize)])
        return float(np.real(job.result()[0].data.evs))

    return energy


def run_aer_multistart_until_budget(
    n: int,
    edge_prob: float,
    qaoa_reps: int,
    rng: np.random.Generator,
    budget_sec: float,
    cobyla_maxiter: int,
) -> tuple[np.ndarray, float, list[tuple[int, int, float]], SparsePauliOp, SparsePauliOp, QuantumCircuit, int]:
    """VQE-style: minimize ⟨-H⟩ so we drive toward large cut."""
    edges = random_patrol_graph(n, edge_prob, rng)
    h = maxcut_hamiltonian(n, edges)
    h_neg = -h
    ansatz = QAOAAnsatz(h, reps=qaoa_reps)
    isa = transpile(ansatz, basis_gates=["rx", "ry", "rz", "cx"], optimization_level=1)
    evals_box = [0]
    energy_fn = make_aer_energy_fn(isa, h_neg, evals_box)

    t0 = time.perf_counter()
    best_theta = rng.uniform(-np.pi, np.pi, isa.num_parameters)
    best_e = energy_fn(best_theta)
    while time.perf_counter() - t0 < budget_sec:
        x0 = rng.uniform(-np.pi, np.pi, isa.num_parameters)
        res = minimize(energy_fn, x0, method="COBYLA", options={"maxiter": cobyla_maxiter})
        if res.fun < best_e:
            best_e, best_theta = float(res.fun), np.asarray(res.x, dtype=float)
    return best_theta, best_e, edges, h, h_neg, ansatz, evals_box[0]


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


def list_ibm_backends(instance: str | None, min_qubits: int) -> None:
    try:
        from qiskit.providers.exceptions import QiskitBackendNotFoundError
    except ImportError as e:
        raise SystemExit("Install dependencies: pip install -r requirements.txt\n" + str(e)) from e

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
    print(f"Operational IBM Quantum backends (non-simulator) with ≥{min_qubits} qubits:")
    for b in sorted(backs, key=lambda x: x.name):
        nq = getattr(b, "num_qubits", 0)
        if nq >= min_qubits:
            print(f"  {b.name}  ({nq} qubits)")


def _resolve_backend(service, backend_name: str, instance: str | None, min_qubits: int):
    from qiskit.providers.exceptions import QiskitBackendNotFoundError

    inst = instance if instance else os.environ.get("QISKIT_IBM_INSTANCE") or None
    if inst == "":
        inst = None
    name = backend_name.strip()
    if name.lower() == "auto":
        return service.least_busy(
            min_num_qubits=min_qubits,
            simulator=False,
            operational=True,
            instance=inst,
        )
    try:
        b = service.backend(name, instance=inst)
    except QiskitBackendNotFoundError as e:
        raise SystemExit(
            f"Backend {name!r} is not available to this account/instance.\n"
            "  Try:  --backend auto\n"
            "  Or:   --list-backends\n"
            "  Or set QISKIT_IBM_INSTANCE.\n"
        ) from e
    if getattr(b, "num_qubits", 0) < min_qubits:
        raise SystemExit(
            f"Backend {b.name} has {getattr(b, 'num_qubits', '?')} qubits; need at least {min_qubits}."
        )
    return b


def run_ibm_single_energy(
    h_obs: SparsePauliOp,
    ansatz: QuantumCircuit,
    theta: np.ndarray,
    backend_name: str,
    instance: str | None,
    min_qubits: int,
) -> tuple[float, str]:
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_ibm_runtime import EstimatorV2

    service = _ibm_runtime_service(instance)
    backend = _resolve_backend(service, backend_name, instance, min_qubits)
    pm = generate_preset_pass_manager(backend=backend, optimization_level=2)
    bound = ansatz.assign_parameters(theta)
    isa = pm.run(bound)
    obs = h_obs.apply_layout(isa.layout)
    estimator = EstimatorV2(mode=backend)
    job = estimator.run([(isa, obs)])
    evs = job.result()[0].data.evs
    return float(np.real(evs)), backend.name


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Drone patrol MaxCut: long classical (exhaustive or Aer multi-start) vs optional IBM ⟨H⟩."
    )
    parser.add_argument(
        "--classical-mode",
        choices=("aer-vqe", "exhaustive"),
        default="aer-vqe",
        help="aer-vqe: many Aer statevector ⟨−H⟩ evaluations until budget; exhaustive: exact max cut over 2^n.",
    )
    parser.add_argument(
        "--nodes",
        type=int,
        default=18,
        help="Patrol sectors (qubits) for QAOA / Aer mode. Needs a backend with at least this many qubits for --ibm.",
    )
    parser.add_argument(
        "--exhaustive-nodes",
        type=int,
        default=27,
        help="Graph size for --classical-mode exhaustive (keep ≤28 on a laptop unless you are patient).",
    )
    parser.add_argument("--edge-prob", type=float, default=0.35, help="Erdős–Rényi edge probability.")
    parser.add_argument("--seed", type=int, default=0, help="RNG seed.")
    parser.add_argument("--qaoa-reps", type=int, default=2, help="QAOA layers p.")
    parser.add_argument(
        "--classical-budget-sec",
        type=float,
        default=1800.0,
        help="Wall-clock budget for the classical phase (default 30 minutes).",
    )
    parser.add_argument(
        "--cobyla-maxiter",
        type=int,
        default=120,
        help="COBYLA maxiter per restart in aer-vqe mode.",
    )
    parser.add_argument(
        "--ibm",
        action="store_true",
        help="After classical phase, submit one EstimatorV2 job on IBM Quantum at the best angles.",
    )
    parser.add_argument("--backend", type=str, default="auto", help='IBM backend name or "auto".')
    parser.add_argument("--instance", type=str, default=None, help="Optional IBM instance CRN.")
    parser.add_argument(
        "--list-backends",
        action="store_true",
        help="List operational backends with enough qubits for --nodes, then exit.",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        metavar="PATH",
        help="Mirror stdout and stderr to this UTF-8 text file (terminal output unchanged).",
    )
    args = parser.parse_args()

    if args.log_file:
        _run_log().install(args.log_file)
    try:
        _main_body(args)
    finally:
        if args.log_file:
            _run_log().uninstall()


def _main_body(args: argparse.Namespace) -> None:
    rng = np.random.default_rng(args.seed)

    if args.list_backends:
        list_ibm_backends(args.instance, args.nodes)
        return

    if args.nodes < 2:
        raise SystemExit("--nodes must be at least 2.")

    print("=== Drone patrol sectors as MaxCut (interference edges) ===")
    print(f"Classical mode: {args.classical_mode}, budget: {args.classical_budget_sec:.0f}s")

    if args.classical_mode == "exhaustive":
        n = args.exhaustive_nodes
        if n > 30:
            print("Warning: n>30 exhaustive is usually impractical on a laptop.", file=sys.stderr)
        print(f"Exhaustive MaxCut on random graphs with n={n} sectors (2^{n} assignments each pass).")
        best_cut, best_a, passes, wall = run_exhaustive_until_budget(
            n, args.edge_prob, rng, args.classical_budget_sec
        )
        print(f"Passes completed: {passes}, wall time: {wall:.1f}s")
        print(f"Largest cut weight seen: {best_cut:.6f} (example assignment mask {best_a})")
        print(
            "\nExhaustive mode does not run QAOA/IBM in this script path "
            "(graph instance is not kept). Use --classical-mode aer-vqe with --ibm for hardware."
        )
        return

    # aer-vqe path (default)
    n = args.nodes
    t_classical = time.perf_counter()
    best_theta, best_neg_h, edges, _h, h_neg, ansatz, evals = run_aer_multistart_until_budget(
        n,
        args.edge_prob,
        args.qaoa_reps,
        rng,
        args.classical_budget_sec,
        args.cobyla_maxiter,
    )
    classical_wall = time.perf_counter() - t_classical

    c_ex, a_ex, _ = exhaustive_maxcut(n, edges)
    isa = transpile(ansatz, basis_gates=["rx", "ry", "rz", "cx"], optimization_level=1)
    e_check = make_aer_energy_fn(isa, h_neg)(best_theta)

    print(f"Sectors: {n}, |E|={len(edges)}, QAOA reps={args.qaoa_reps}")
    print(f"Classical Aer phase wall time: {classical_wall:.1f}s ({evals} Aer energy evaluations)")
    print(f"Best min ⟨−H⟩ found: {best_neg_h:.6f}  (sanity recheck: {e_check:.6f})")
    print(f"Exact max cut on this graph (exhaustive, same n): {c_ex:.6f} (assignment {a_ex})")
    print("Heuristic ⟨H⟩ at best angles (Aer):", f"{-e_check:.6f}")

    if args.ibm:
        print("\n--- Single ⟨−H⟩ readout on IBM Quantum (compiled once) ---")
        ev_hw, bname = run_ibm_single_energy(h_neg, ansatz, best_theta, args.backend, args.instance, n)
        print(f"Backend: {bname}")
        print(f"⟨−H⟩ on hardware: {ev_hw:.6f}  (≈ −⟨H⟩ if you compare to cut-weight language)")
        print(
            "\nFraming: the laptop spent minutes on repeated exact wavefunction simulation "
            "inside Aer; the processor evaluated one compiled circuit — queue time not counted."
        )


if __name__ == "__main__":
    main()
