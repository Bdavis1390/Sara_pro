# Worldshepherd Backline Validation Plan — QBL v0.1

Date: 2026-09-12
Status: LAB PREPARATION / NOT YET EXECUTED
Owner lane: SARA / PRIME SENTINEL / ECHO SENTINEL LINK / OVERWATCH

## Purpose

Establish a claims-controlled validation path for Xanadu/AMD Backline as a candidate low-latency heterogeneous compute substrate beneath Worldshepherd governance. Backline is not a replacement for SARA, PRIME, ECHO, or OVERWATCH.

## Authoritative upstream baseline

The initial QBL-G1 laboratory baseline follows the public PennyLane/Backline local CPU-to-CPU Steane QEC demonstration and the official Backline installation guide.

Pinned initial upstream versions from the official Backline Tier-1 instructions:

- Backline: `v0.1.0b1`
- Catalyst: `v0.16.0b1`
- PennyLane/PennyLane Lightning beta line: `v0.46.0b1`
- Transport for QBL-G1: `memcpy`
- Quantum device for QBL-G1: `lightning.qubit`
- QEC code: `steane`

Upstream sources:

- https://github.com/PennyLaneAI/backline/blob/main/INSTALL.md
- https://www.pennylane.ai/demos/backline
- https://github.com/PennyLaneAI/demos/blob/master/demonstrations_v2/backline/demo.py

## Claims boundary

Until Worldshepherd executes and records a gate successfully:

- `BACKLINE_SOFTWARE`: IMPLEMENTED_EXTERNALLY / OPEN_SOURCE
- `WORLDSHEPHERD_BACKLINE_INTEGRATION`: REQUIRES_LAB_VALIDATION
- `WORLDSHEPHERD_SUB_3US_PERFORMANCE`: NOT CURRENTLY CLAIMED
- `HARDWARE_QPU_INTEGRATION`: NOT CURRENTLY CLAIMED
- `QUANTUM_ADVANTAGE`: NOT CURRENTLY CLAIMED

Vendor-published latency results remain external benchmarks and must never be promoted to Worldshepherd measurements.

## Architectural rule

Governance remains outside the deterministic microsecond hot loop.

1. SARA prepares and submits an approved job.
2. PRIME authorizes the experiment, allowed code/configuration, and target hardware before execution.
3. Backline/Catalyst executes the quantum-classical workload.
4. ECHO records exact source/version/configuration hashes and result provenance.
5. OVERWATCH records timing distributions, failures, environment state, and evidence links.

No networked policy lookup or human approval dependency may be inserted into a latency-critical QEC feedback loop.

## Validation ladder

### QBL-G0 — Source and environment custody

Pass criteria:

- upstream versions pinned;
- source URLs and commit/tag identifiers recorded;
- Python/Catalyst/Backline environment isolated from the system Python;
- decoder library path recorded;
- hardware and OS inventory captured;
- claims boundary recorded before execution.

### QBL-G1 — Local CPU-to-CPU Steane QEC

Use PennyLane Lightning as the simulated QPU, a local CPU controller, a local CPU coprocessor, the Catalyst Steane decoder library, and Backline `memcpy` transport.

Pass criteria:

- environment imports `pennylane`, `Controller`, `Coprocessor`, and `Backline`;
- official-equivalent logical GHZ workload compiles and executes;
- returned samples satisfy the GHZ invariant: each shot is either all-zero or all-one;
- at least 10 repeated post-compile executions complete without runtime failure;
- exact command, environment metadata, stdout/stderr, and hashes are preserved.

QBL-G1 does **not** establish physical-QPU performance, RDMA performance, quantum advantage, or microsecond transport performance.

### QBL-G2 — Repeatable host-side benchmark harness

Measure cold call and warm repeated calls separately. Report at minimum:

- count;
- minimum;
- median;
- p95;
- p99;
- maximum;
- mean;
- standard deviation;
- GHZ validation failures.

The initial Python harness measures the caller-observed end-to-end function invocation. It is not a substitute for transport-level or hardware timestamping and must be labeled accordingly.

### QBL-G3 — Governed Worldshepherd wrapper

Add bounded SARA job preparation, PRIME pre-authorization, ECHO provenance, and OVERWATCH telemetry around QBL-G1/QBL-G2 while keeping the execution hot loop free of governance round trips.

Pass criteria include exact policy/config hashes, reproducible job IDs, evidence preservation, replay, and no material benchmark regression attributable to instrumentation outside the hot loop.

### QBL-G4 — Remote CPU-to-GPU / RDMA

Requires qualified remote GPU server and RDMA-capable transport. Preserve upstream hardware/software prerequisites and quantify transport, kernel, and total latency separately.

### QBL-G5 — FPGA/RDMA

Requires qualified FPGA/RDMA hardware. Capture deterministic latency and jitter with transport/hardware timestamps where available. Vendor benchmark numbers remain comparison-only.

### QBL-G6 — Physical QPU or quantum sensor

Requires external or partner hardware. Promote claims only after a reproducible interface demonstration and preserved evidence package.

## Initial execution environment

Preferred Worldshepherd path: isolated container or virtual environment. Do not replace or upgrade the host system Python to satisfy Backline.

For the official Tier-1 wheel path, the upstream guide currently specifies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pennylane-catalyst==0.16.0b1 \
  -f https://github.com/PennyLaneAI/pennylane/releases/expanded_assets/v0.46.0b1 \
  -f https://github.com/PennyLaneAI/pennylane-lightning/releases/expanded_assets/v0.46.0b1 \
  -f https://github.com/PennyLaneAI/catalyst/releases/expanded_assets/v0.16.0b1
```

Then clone Backline at the pinned beta tag for source custody:

```bash
git clone --branch v0.1.0b1 https://github.com/PennyLaneAI/backline.git ~/backline
```

The Catalyst decoder library expected by QBL-G1 is:

```text
$CATALYST_ROOT/runtime/build/lib/libsteane_coprocessor_cpu.so
```

## Evidence package

Each executed run should produce a unique run directory outside version control until reviewed. Minimum manifest fields:

- run ID and UTC timestamp;
- git branch/commit for Sara_pro experiment code;
- upstream tags/commits;
- Python and package versions;
- OS/kernel/CPU inventory;
- command line;
- environment variables relevant to Catalyst/Backline;
- SHA-256 for decoder library and experiment scripts;
- stdout/stderr;
- benchmark JSON;
- result classification and gate decision.

Sensitive host identifiers, credentials, secrets, private IPs, or partner-controlled information must not be committed to the public repository.

## Promotion rule

A gate may move from `REQUIRES_LAB_VALIDATION` to `PROVEN INTERNALLY` only after its pass criteria are met with reproducible evidence. External partner validation and independent replication remain separate evidence states.
