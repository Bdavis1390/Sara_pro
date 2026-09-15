# GD-13 — W-RMABM G4 Independent Evaluation Handoff

**Release posture:** UNCLASSIFIED / NON-CONFIDENTIAL / REVIEW REQUIRED BEFORE TRANSMISSION

## Purpose
This package requests independent reproduction of a bounded Worldshepherd software benchmark. It is not a request for product endorsement, operational certification, government acceptance, or assessment of any real missile-defense mission.

## Capability under evaluation
**Worldshepherd Resilient Mission Assurance & Battle Management Layer (W-RMABM)**

The evaluated material is a synthetic software prototype focused on:

- deterministic replay;
- source/provenance traceability;
- stale-data handling;
- bounded policy enforcement;
- identified-human authorization for advisory dissemination;
- fail-closed handling of prohibited consequential-action requests;
- tamper-evident challenge/result hashing;
- evaluator-owned evidence recording.

## Independent evaluation objective
An evaluator outside the Worldshepherd development process runs the frozen G4 protocol in an evaluator-controlled environment. The evaluator controls the challenge seed and records the exact source revision, environment, challenge digest, outputs, assertions, and result attestation.

A successful reproduction may support only this evidence statement:

`INDEPENDENTLY REPRODUCED — SYNTHETIC SOFTWARE BEHAVIOR ONLY`

It does **not** establish operational readiness, government validation, Golden Dome validation, missile-warning/tracking performance, fire-control performance, weapon-cueing capability, classified-system readiness, cybersecurity certification, deployment authorization, or compliance certification.

## Evaluator-controlled checks
The evaluator should execute the frozen protocol and independently record whether the following assertions pass:

1. **Challenge integrity** — the evaluator-selected seed produces a challenge with a recorded SHA-256 digest.
2. **Deterministic reproduction** — repeated execution of the same challenge produces the same bounded result and evidence digest.
3. **Seed independence** — a different evaluator-selected seed produces a distinct challenge binding without bypassing policy gates.
4. **Human authorization gate** — removal of identified human authority causes advisory dissemination to be held rather than authorized.
5. **Prohibited-action gate** — a prohibited consequential-action request is blocked by the software boundary.
6. **Tamper rejection** — modification of challenge material after hashing is detected and rejected before acceptance as a valid evaluation result.
7. **Evidence binding** — the final attestation binds the challenge, result, replay, decision counts, and evaluation metadata using cryptographic digests.

## Data boundary
The evaluation package intentionally excludes:

- real threat trajectories or target tracks;
- interceptor models or engagement geometry;
- fire-control, target-designation, weapon-cueing, launch, intercept, or engagement logic;
- classified data or Controlled Unclassified Information;
- export-controlled mission data;
- proprietary government or vendor interfaces;
- operational missile-warning or missile-tracking data;
- credentials, secrets, private keys, tokens, or personal contact data.

The synthetic benchmark uses generic two-dimensional surrogate observations solely to exercise software-assurance behavior.

## Evaluator evidence requested
The evaluator retains control over its environment and should return only evidence it is authorized to share. The preferred evidence record contains:

- evaluator organization or laboratory name;
- evaluator-controlled environment description;
- source commit/ref tested;
- challenge seed and challenge SHA-256;
- result/audit/replay/attestation SHA-256 values;
- pass/fail result for each mandatory assertion;
- deviations from the protocol, if any;
- evaluator statement that no Worldshepherd developer controlled the execution environment or selected the challenge seed;
- evaluator signature, attestation, or other institutionally appropriate evidence of authorship.

## Reproduction rule
Worldshepherd must not label G4 achieved from internal CI, developer-run execution, a demonstration observed by a third party, or an evaluator using a developer-controlled seed/environment.

G4 is achieved only when an independent evaluator executes the frozen protocol under evaluator control and records all mandatory assertions as passing.

## Failure is evidence
A failed or partial reproduction must be preserved as evidence. Worldshepherd should not suppress, rewrite, or relabel an unsuccessful independent result. Instead, the failure should be traced to a specific defect, assumption, environment mismatch, ambiguity, or protocol gap, corrected on a new revision, and re-evaluated under a newly frozen reference.

## Handoff sequence
1. Confirm the evaluator is willing and institutionally permitted to perform the reproduction.
2. Freeze and record the exact evaluation commit/ref.
3. Generate the review-gated external manifest and verify leakage checks.
4. Human-review the handoff bundle.
5. Transfer only the authorized unclassified/non-confidential material.
6. Evaluator executes the protocol independently.
7. Preserve evaluator evidence without changing its substance.
8. Update claims status only after the evidence is reviewed.

## Claims boundary
This handoff exists to increase falsifiability and evidence quality. It does not imply that any named government organization, defense contractor, FFRDC, UARC, university, laboratory, or commercial organization has reviewed, accepted, endorsed, funded, sponsored, validated, or agreed to evaluate Worldshepherd.