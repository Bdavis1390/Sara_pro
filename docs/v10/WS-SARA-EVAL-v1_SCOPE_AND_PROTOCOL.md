# WS-SARA-EVAL-v1 — Core Evaluator Scope and Protocol

**V10 gate:** V10-2 / V10-3 support

**Source-code baseline:** `1c7be6c51ffd475f124e951f6c8c76208460b895`

**Release posture:** UNCLASSIFIED / NON-CONFIDENTIAL / REVIEW REQUIRED BEFORE EXTERNAL RELEASE

## Purpose

Define a bounded independent reproduction target for the Worldshepherd core SARA / PRIME SENTINEL software baseline without promoting unmerged candidate work or physical capability claims.

This evaluator package is distinct from the W-RMABM G4 package. W-RMABM external evaluation is tracked separately and may be used as independent evidence for its tested synthetic mission-assurance scope. This document governs the reusable core-platform lane.

## Included baseline

The frozen source baseline is the exact main commit above. It includes the merged PRIME SENTINEL durable issuance ledger v1.5 and the SARA verified-local deployment material present at that commit.

## Excluded from this baseline

- unmerged ECHO v1.6 candidate work / PR #153;
- unmerged W-RMABM G4 preparation / PR #116;
- unmerged XTEND, Sentinel, physics, vehicle, materials, RF, propulsion, or other candidate branches;
- any customer, partner, government, certification, compliance, classified-readiness, or physical-performance claim not separately established.

## Existing local deployment boundary

The frozen deployment documentation exposes a localhost-only SARA interface by default at `127.0.0.1:9530`, with documented health, liveness, readiness, relay, audit, registry, and self-test surfaces. External scanning, arbitrary command execution, third-party activation, self-expanding network behavior, and broadcast behavior are outside the verified local boundary.

The application audit is operational evidence, not immutable or independently verified storage.

## Evaluator control principle

The evaluator must control the test environment and retain its own original evidence. Worldshepherd may provide installation instructions, the frozen source identity, and bounded challenge categories, but must not choose the evaluator's final challenge values or rewrite failed evidence after execution.

## Minimum evaluator environment record

Record before execution:

- repository and exact source baseline SHA;
- evaluator-controlled checkout or supplied reviewed bundle identity;
- OS and architecture;
- Python/runtime version;
- Docker/Compose version if used;
- dependency-lock or installed-package fingerprint;
- execution date/time;
- evaluator identifier or organization-controlled reference;
- network boundary used for the test;
- SHA-256 manifest for the evaluator's received bundle and produced evidence.

## Required core runs

### C1 — Clean deployment and health/readiness

Acceptance:
- installation/deployment completes from the reviewed instructions;
- localhost publication remains bounded as documented;
- health/liveness/readiness surfaces behave consistently with the frozen baseline;
- no external activation is required.

### C2 — Authorization separation

Acceptance:
- administrative operations require the documented administrative authorization path;
- a non-administrative/operator context cannot silently obtain administrative audit or registry authority;
- denial is retained as evidence where the frozen implementation records it.

### C3 — Registry and audit traceability

Acceptance:
- a bounded authorized registry mutation can be traced to the expected retained evidence;
- resulting audit/evidence records can be retrieved through the documented interface;
- evaluator records hashes of relevant output artifacts.

### C4 — PRIME issuance durability / idempotency

Acceptance is limited to behavior actually implemented by the frozen v1.5 source. Evaluator must test documented same-request retry behavior, restart persistence, conflict rejection, and reconciliation/integrity surfaces without inferring exactly-once transport, HSM/KMS custody, WORM storage, or external attestation.

### C5 — Negative / malformed / unauthorized cases

Evaluator selects bounded malformed or unauthorized cases from the documented API/input contracts.

Acceptance:
- malformed or unauthorized input is not silently promoted into a successful governed action;
- observed behavior and error class are retained;
- any discrepancy is recorded rather than discarded.

### C6 — Restart / recovery

Where supported by the frozen deployment package, evaluator restarts the relevant local service(s) and records whether documented persisted state, readiness, and recovery behavior match the frozen implementation.

## Evidence retention

For every run retain:

1. source baseline SHA;
2. evaluator environment fingerprint;
3. command/run identity or equivalent procedural record;
4. input/challenge identity;
5. output hashes;
6. pass/fail result for each assertion;
7. evaluator-authored discrepancy notes;
8. original failed evidence if a run fails;
9. any retest as a new linked record, never as a replacement for the failure.

## Pass rule

This core evaluator lane may be labeled **INDEPENDENTLY REPRODUCED — BOUNDED SOFTWARE BEHAVIOR ONLY** only after an evaluator outside the Worldshepherd development process executes the reviewed protocol in an evaluator-controlled environment and records all mandatory assertions for the agreed scope as passing.

Internal CI, a Worldshepherd-controlled machine, a founder-authored scorecard without external execution, or the existence of this protocol cannot satisfy V10-3.

## Claims boundary

A pass does not establish production certification, customer/government acceptance, CMMC/NIST/DFARS conformity, classified suitability, immutable audit storage, HSM/KMS custody, operational effectiveness, physical platform capability, or any broader untested Worldshepherd technology claim.
