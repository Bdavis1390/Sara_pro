# Worldshepherd Evidence Crosswalk for Curious NerdworX Capture

**Status date:** 2026-10-05
**Purpose:** map current Worldshepherd evidence to proposal claims without inflating maturity.

## Crosswalk

| Proposal need | Worldshepherd evidence source | Allowed claim posture | Missing gate |
|---|---|---|---|
| Governed orchestration | `runtime/README.md`, `deployments/sara_verified_local_v1/`, `scripts/sara.sh` | IMPLEMENTED IN SOFTWARE; bounded local behavior can be cited where tests exist | Independent clean-clone reproduction / external integration when required |
| Human authorization / bounded automation | SARA/PRIME code and tests; governance docs | IMPLEMENTED IN SOFTWARE for tested paths | Partner/customer acceptance in representative environment |
| Evidence provenance / lineage | ECHO and restriction-provenance docs; release evidence | IMPLEMENTED IN SOFTWARE / PROVEN INTERNALLY for bounded artifacts | Independent custody / external witness where required |
| Replay / rollback / recovery evidence | recovery workflows, exact-head CI, deterministic replay artifacts | PROVEN INTERNALLY for tested configuration | External evaluator reproduction |
| NIST SP 800-171 preparation | SSP-precursor workflow, security docs, control mapping | IMPLEMENTED IN SOFTWARE for the precursor/mapping behavior that is actually tested; no compliance claim implied | Real system-boundary closure, self-assessment, SPRS and external requirements |
| SBOM / software supply-chain evidence | SBOM linkage and release-index artifacts | IMPLEMENTED IN SOFTWARE where artifact generation is tested | Customer-specific ingestion / contractual acceptance |
| Distributed C2 / DDIL assurance | SARA/PRIME/ECHO architecture + mission-assurance research | IMPLEMENTED IN SOFTWARE for generic governance patterns; REQUIRES PARTNER VALIDATION for operational C2 | Representative mission integration |
| Space mission assurance | WS-FLIGHT-style provenance / anomaly / shadow-mode harnesses and related research | PROVEN INTERNALLY for synthetic/local harness behaviors | Interface access, HIL and/or flight validation |
| Quantum / cryptographic evidence available in-repo | `docs/QCRYPTO_BTC_MIGRATION_V0_1_2026-09-30.md`, `research/qcrypto_tsv/v3_6/`, evaluator-handoff/reproducibility machinery | IMPLEMENTED IN SOFTWARE or PROVEN INTERNALLY only where an exact file/test supports the bounded statement; QBI-specific quantum benchmarking remains proposed work | Add exact QBI-relevant benchmark artifacts/tests, then independent benchmark / hardware-provider data as applicable |
| Opportunity intelligence | PRE schemas, requirements-delta workflows, capture artifacts | IMPLEMENTED IN SOFTWARE for existing schemas/tools; opportunity facts still require source verification | Official-source verification per opportunity |
| Partner integration | adapter, handoff, claims-boundary and evaluator-manifest work | IMPLEMENTED IN SOFTWARE for handoff machinery | Partner-owned system integration and acceptance |
| Physical systems claims | research docs for RF/materials/propulsion/robotics/etc. | SUPPORTED BY LITERATURE / SIMULATED ONLY / HYPOTHESIS as applicable | Lab or partner validation |

## Opportunity mapping

### SCAR AOI 03

**Route constraint:** treat provider-led teaming as the executable path unless Curious NerdworX independently verifies the solicitation's direct-offeror clearance/FCL gates and all other eligibility requirements.

**Worldshepherd contribution that can be defended now**
- bounded JAM/mission-assurance adapter concept;
- authorization and evidence boundary;
- replay / duplicate / timing / lineage checks;
- evaluator-ready integration evidence;
- multi-provider configuration and evidence custody patterns.

**Partner-owned / government-dependent**
- mature antenna-as-a-service network;
- government JAM endpoint;
- Offeror Library CUI;
- service-level performance;
- operational TRL claims for the integrated network.

### Army xTechSearch

Strongest candidate product boundaries:

1. **Governed Autonomous Sustainment Evidence Layer**
   Human-approved machine workflows, degraded-state operation, provenance, replay, and recovery.

2. **Authenticated Sensor-to-Decision Chain**
   Evidence lineage, stale/replay detection, confidence and policy gating around partner sensors.

3. **Evidence-to-Execution Assurance Gateway**
   Converts requirements and approvals into bounded actions with immutable-ish audit and reproducible evidence.

Selection rule: submit one product with one customer pain point and measurable acceptance criteria.

### DARPA Influence Benchmarks

Defensible contribution:
- governed multi-agent experimentation;
- complete action/event provenance;
- reproducible market scenarios;
- policy / authorization controls;
- deception / adaptation event capture;
- deterministic replay;
- evidence packages suitable for independent analysis.

Missing gate:
- opportunity-specific benchmark implementation and quantitative baselines.

### Space Safari

Defensible contribution:
- read-only / shadow-mode mission-assurance layer;
- event/telemetry lineage;
- stale-data, duplicate/replay, clock-drift and state-divergence checks;
- machine-readable evidence reconstruction.

Not currently claimed:
- spacecraft bus;
- launch system;
- flight-qualified avionics;
- Handle 2.0 compatibility;
- vehicle-prime experience.

### DARPA QBI IV&V

Defensible contribution from the current repository:
- exact configuration capture;
- provenance;
- claims/evidence separation;
- reproducible software/evaluator handoff machinery;
- concrete QCRYPTO artifacts where exact repository evidence supports the claim.

Proposed work, not current evidence:
- QBI-specific quantum benchmark suite;
- provider/hardware-specific validation harnesses;
- quantum performance or numerical claims not tied to an exact committed artifact/test.

Missing gate:
- commit the QBI-relevant benchmark implementation and tests, then validate against evaluator-selected workloads and external hardware/provider data.

## Proposal language rule

Prefer:

> "Worldshepherd currently implements and internally tests the bounded software behavior described below. The proposed effort advances that capability into the customer's representative environment under predeclared acceptance criteria."

Avoid:

> "Worldshepherd is certified, operationally proven, flight-qualified, fielded, or independently validated"

unless the exact claim is separately supported.

## Evidence package minimum

Every serious submission should produce:

1. requirement-to-response matrix;
2. claim-state table;
3. exact repository commit;
4. test list and pass/fail results;
5. configuration and dependency inventory;
6. known limitations;
7. risk register;
8. customer/partner dependencies;
9. next validation gate;
10. human approval record for final submission.

This package should be retained even when the proposal is not selected, so each pursuit improves the next one.
