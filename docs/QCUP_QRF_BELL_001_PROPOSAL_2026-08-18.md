# QCUP Project Proposal Package — QRF-BELL-001

**Prepared:** 2026-08-18  
**Project:** Worldshepherd Quantum Readiness Fabric (QRF)  
**Benchmark:** QRF-BELL-001  
**Status:** Proposal-ready draft; no allocation or hardware access implied  
**Program:** Oak Ridge Leadership Computing Facility (OLCF) Quantum Computing User Program (QCUP)

## 1. Program-fit constraints

This proposal is intentionally scoped to the published QCUP access and policy requirements:

- open, fundamental research only;
- no export-controlled, PHI, proprietary, or other controlled data in the proposed workload;
- project access is obtained through QCUP merit/feasibility review before user/vendor accounts;
- hardware credit/time requests are downstream of project approval;
- benchmark, verification, validation, proof-of-principle, and quantum-versus-classical comparison are treated as legitimate QCUP research modes.

The proposal does **not** request endorsement, certification, deployment approval, or a quantum-advantage finding.

## 2. PI / institutional eligibility item

**Proposed PI:** Brandon Ray Davis  
**Proposed organizational affiliation:** Worldshepherd / Brandon Davis Solutions  
**Institutional status:** **TO BE CONFIRMED WITH QCUP BEFORE FORM SUBMISSION.**

QCUP materials require a project PI and current program guidance states that prospective QCUP PIs must be faculty or staff at an institution. OLCF also maintains an Industry Principal Investigator Agreement. Worldshepherd will not represent its organizational status as satisfying QCUP institutional requirements until QCUP confirms the correct applicant category and agreement path.

## 3. Project title

**Evidence-Governed Cross-Provider Reproducibility of a Frozen Two-Qubit Bell-State Workload**

## 4. Executive summary

This project proposes a small, open, provider-neutral study of reproducibility and evidence custody for a frozen two-qubit Bell-state workload, `QRF-BELL-001`. The scientific objective is not to demonstrate quantum advantage; it is to characterize how a simple, fully specified circuit changes as it moves from ideal/noisy simulation to named physical quantum processors, while retaining sufficient provenance to support statistically defensible cross-provider comparison.

Worldshepherd has already implemented and CI-gated the classical/simulator baseline, immutable program/result identities, backend-normalization schema, statistical cross-backend reproduction logic, and fail-closed claims controls. The missing evidence is genuine hardware execution. QCUP is sought because it provides merit-reviewed access to multiple quantum systems and supports proof-of-principle, benchmarking, verification/validation, and quantum-versus-classical work.

The project would execute the same frozen Bell circuit on one or more QCUP quantum backends, beginning with the minimum hardware allocation practical for a statistically useful sampled distribution. Each run would retain provider/backend identity, job/run identity, shot count, sampled outcomes, timing/queue information when exposed, calibration/configuration context when available, and immutable source/result/configuration digests. Independent runs would be compared using predeclared total-variation-distance and Bhattacharyya-fidelity thresholds rather than requiring identical sampled results.

The intended output is an open, reproducible benchmark/evidence package describing what can and cannot be inferred from simple cross-provider QPU execution. Any hardware result remains external evidence subject to separate Worldshepherd technical review; no readiness or performance claim follows automatically from QCUP access or a successful run.

## 5. Public impact statement

This project studies how to make small quantum-computing results more reproducible and auditable across different hardware providers. It will test a common Bell-state workload under one evidence schema while explicitly separating simulator output, physical-hardware evidence, and claims about performance or advantage.

## 6. Scientific objectives

1. Execute one frozen quantum workload on named physical quantum hardware without changing the logical experiment after results are observed.
2. Retain sufficient metadata and immutable evidence identities to reproduce the analysis independently.
3. Quantify agreement between independent sampled hardware runs using predeclared statistical thresholds.
4. Compare physical results with ideal/noisy simulator baselines without relabeling simulation as hardware evidence.
5. Determine which provider-exposed metadata are sufficient or insufficient for cross-provider reproducibility and audit.
6. Produce a bounded negative-result record if the hardware results fail the predeclared reproduction thresholds.

## 7. Frozen workload

`QRF-BELL-001` is a two-qubit Bell-state benchmark:

1. initialize `|00>`;
2. apply Hadamard to qubit 0;
3. apply controlled-X from qubit 0 to qubit 1;
4. measure both qubits in the computational basis;
5. retain shot-resolved aggregate counts/probabilities.

The logical program is frozen before hardware submission. Provider-specific transpilation/routing is allowed only as required by the selected backend and must be recorded as part of backend/run provenance.

## 8. Existing baseline and controls

Worldshepherd currently retains:

- ideal and noisy Qiskit/Aer execution;
- immutable workload/program/result/configuration digests;
- a provider-neutral gate-model execution record;
- credential-gated IBM and IonQ adapters;
- statistical cross-backend reproduction using distinct result identities;
- total variation distance (TVD) and Bhattacharyya fidelity comparison;
- a requirement that statistically independent runs use distinct immutable result records;
- structural ingest followed by identified-human technical review;
- a separate canonical state-change decision;
- a 97/100 mission-readiness threshold that cannot be crossed by software completion alone.

These internal controls are not presented as physical quantum evidence.

## 9. Proposed QCUP methodology

### Phase A — feasibility / emulator justification

- verify the frozen circuit on the QCUP-recommended simulator/mock backend;
- document expected shot count and requested credit/time basis;
- verify provider-specific submission/transpilation requirements;
- freeze the hardware-run configuration before submission.

### Phase B — first physical run

- execute the frozen workload on one QCUP physical backend;
- retain backend/provider, job ID, timestamps, shots, result counts/probabilities, and available calibration/configuration context;
- compute immutable digests for normalized program, run metadata, and result record;
- compare against the frozen simulator baseline.

### Phase C — repeatability

- repeat on the same backend at a separately identified run time;
- preserve a distinct result identity;
- evaluate TVD and Bhattacharyya fidelity under predeclared thresholds;
- retain failures and anomalous distributions rather than discarding them.

### Phase D — cross-provider reproduction, if allocation permits

- execute the same frozen logical workload on a second QCUP provider/backend;
- normalize provider-specific metadata into the same evidence schema;
- compare independent sampled distributions under the same predeclared statistical policy;
- report both agreement and disagreement without post-hoc threshold changes.

## 10. Minimum requested resource envelope

The workload uses only two logical qubits and a shallow Bell-state circuit. Requested hardware usage should therefore be the **smallest allocation QCUP considers practical** for statistically meaningful shot sampling and one repeat. The project does not request long exclusive reservations.

If QCUP requires provider-specific resource justification, Worldshepherd will provide simulator/dry-run results and requested shots/jobs in the format required by the selected system before any hardware allocation request.

## 11. Why QCUP resources are required

The unresolved scientific question is specifically about **physical QPU reproducibility and provider metadata**, which cannot be answered with simulators alone. QCUP provides merit-reviewed access to multiple quantum platforms and supports benchmarking, verification/validation, proof-of-principle work, and quantum/classical comparison. A QCUP route also allows the study to remain an open research effort rather than binding the evidence model to a single vendor's self-service access path.

## 12. Open-research and data statement

The proposed workload contains no export-controlled, PHI, classified, proprietary customer, or other controlled data. The Bell circuit, statistical method, evidence schema, and benchmark results are intended to be publishable/open subject to QCUP/OLCF policies and normal review.

No Worldshepherd proprietary materials formulation, defense solicitation data, personal data, or controlled mission dataset is required for this project.

## 13. Expected outputs

- frozen logical workload and digest;
- provider-specific compiled/transpiled representation where releasable;
- run/job/backend metadata;
- sampled distribution and immutable result digest;
- simulator-to-hardware comparison;
- same-backend repeatability analysis;
- second-provider comparison if allocated;
- queue/runtime/cost or credit-use information where exposed;
- negative/anomalous evidence record;
- reproducibility summary and limitations;
- source references and QCUP acknowledgement as required.

## 14. Success criteria

A successful project is **not** defined as obtaining a particular Bell fidelity. Success is defined as completing the frozen protocol with adequate provenance and reaching a scientifically defensible conclusion about reproducibility, including a negative conclusion if the sampled results do not meet the predeclared agreement thresholds.

## 15. Claims boundary

This project does not seek or imply:

- quantum advantage;
- hardware ownership;
- certification or endorsement by ORNL/OLCF/QCUP or any vendor;
- deployment or mission authorization;
- proof that a simple Bell benchmark generalizes to larger workloads;
- a readiness-score promotion without separate evidence ingest and technical review.

## 16. Immediate intake questions for QCUP

1. Is Worldshepherd / Brandon Davis Solutions eligible to serve as the applicant institution under QCUP, and if so should the **Industry Principal Investigator Agreement** path be used?
2. Is this two-qubit reproducibility/benchmarking scope scientifically sufficient for a standalone QCUP project, or should it be expanded to a small benchmark family?
3. Which QCUP backend(s) are most appropriate for a first and second independent physical-provider comparison?
4. What simulator/dry-run and resource-estimation evidence should accompany the initial allocation request?
5. Are there additional open-data, publication, or reporting requirements that should be incorporated before submission?

---

**Operational status:** OLCF support ticket `OLCFHELP-27387` directed the feasibility request to `qcup@ornl.gov`. The proposal scope was then sent directly to QCUP on 2026-08-18. This file is the proposal-ready technical package pending QCUP feedback and confirmation of the proper PI/institution agreement path.