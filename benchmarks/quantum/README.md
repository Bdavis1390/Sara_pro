# Quantum benchmark ladder

These workloads exist to validate Worldshepherd's execution/evidence pipeline, not to claim useful quantum advantage.

## QRF-BELL-001

Artifact: `bell_qasm3.qasm`

Purpose:

- verify OpenQASM 3 ingestion/export;
- verify simulator/QPU backend classification;
- retain shot count, backend identity, calibration metadata and result digest;
- confirm strong correlations between the two measured bits;
- exercise classical null/reference comparison.

Acceptance sequence:

1. Parse/validate OpenQASM 3.
2. Run ideal simulation.
3. Run noisy simulation with named noise model.
4. Run a real QPU when credentials/provider access exist.
5. Repeat the QPU run.
6. If practical, run a second provider/backend.
7. Store each result through `QuantumRunEvidence`.

The expected Bell-state measurement support is concentrated in `00` and `11`; finite-shot and hardware noise mean exact equality is not required. Statistical acceptance must be specified before the run.

## Required evidence fields

- project_id
- experiment_id
- backend provider/name/class
- circuit digest
- transpiler/compiler version/settings
- shots
- calibration identifier/snapshot when exposed
- raw-result digest
- post-processing version
- uncertainty/acceptance statistic
- classical baseline identifier

## Next benchmarks

- `QRF-GHZ-002`: multi-qubit entanglement smoke test.
- `QRF-VQE-ALTI-003`: reduced Hamiltonian benchmark for WS-AlTi; must include DFT/classical reference.
- `QRF-QAOA-META-004`: fixed discrete metasurface tile-state problem versus a classical optimizer.
- `QRF-QAOA-LOG-005`: fixed autonomous-logistics instance versus MILP/CP-SAT.
- `QRF-RESOURCE-006`: fault-tolerant resource estimate for one selected workload.

No benchmark is promoted to an application claim solely because it ran on a QPU.
