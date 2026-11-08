# BAROS Translational Governance and Scientific Assurance v2

Status: IMPLEMENTED IN SOFTWARE / NON-CLINICAL
Patient-care authority: **NONE**

## Purpose

BAROS now combines radiotherapy research functions with a validation control
plane designed to make scientific promotion explicit, falsifiable, and
reversible. The control plane does not determine that a scientific claim is
true. It determines whether the evidence supporting a proposed validation-state
transition is sufficiently identified, bounded, internally consistent, and
authorized to proceed.

This architecture incorporates Worldshepherd assurance work completed on
2026-09-17 in provenance, exact-effect authorization, contradiction
preservation, replay/rollback resistance, evidence dependency tracking,
identifiability, information-gain experiment design, and observability controls.

## A. Locked intended-use manifest

`IntendedUseManifest` binds each validation campaign to an exact:

- validation ID;
- indication and stage/risk group;
- modality and delivery technique;
- machine class;
- TPS and version;
- fractionation;
- comparator workflow;
- planning protocol;
- operator roles;
- primary/secondary endpoints;
- permitted human overrides; and
- explicit non-intended uses.

The manifest is canonicalized and SHA-256 digested. A change in indication,
TPS version, protocol, endpoint, or other locked field therefore produces a
new intended-use identity and cannot silently inherit the former evidence.

## B. Evidence Bill of Materials (EBOM)

`EvidenceEnvelope` binds:

- BAROS commit;
- intended-use digest;
- protocol and configuration digests;
- evidence classes;
- raw and analysis artifact hashes;
- environment identity;
- source custody;
- uncertainty statement;
- protocol deviations;
- unresolved contradictions;
- independent-review role;
- partner/external control status;
- explicit human-authorization status; and
- the permanent research-only patient-care boundary.

The envelope itself is content addressed.

## C. Contradiction/deviation quarantine

Evidence cannot support state promotion when unresolved contradictions or
protocol deviations remain. They are retained as blockers rather than averaged
away, omitted, or converted into a positive aggregate result.

Examples include:

- dose-grid/reference-frame disagreement;
- partner TPS output conflicting with BAROS assumptions;
- systematic measured-dose bias;
- protocol/configuration drift;
- model outputs inconsistent with independent calculation;
- analysis not reproducible from declared raw artifacts.

## D. Validation-state evidence compiler

The control plane encodes the BAROS G0-G9 sequence:

- G0 — requirements and traceability;
- G1 — component verification;
- G2 — end-to-end bounded research pipeline;
- G3 — independent numerical/model reference;
- G4 — DICOM-RT interoperability;
- G5 — external TPS/research-dose-engine recalculation;
- G6 — measured dose and deliverability;
- G7 — held-out retrospective validation;
- G8 — independent replication and peer review;
- G9 — prospective evidence and regulatory determination.

External gates require partner-controlled evidence and an independent-review
role. G7-G9 additionally require explicit human authorization.

These are minimum structural conditions, not a substitute for institutionally
defined clinical/scientific acceptance criteria.

## E. Exact-effect human authorization

A `GateTransitionRequest` is bound to:

- validation ID;
- exact current and requested gate;
- expected monotonic epoch;
- exact BAROS commit;
- intended-use digest;
- evidence-envelope digest;
- target research environment;
- one-use nonce; and
- expiry.

`GateAuthorization` binds the human approval to the exact request digest and
exact activation-effect digest. Changing evidence, commit, intended use,
environment, gate, or expected prior state invalidates the approval.

This is authorization binding and replay control. The current BAROS module does
not claim an external institutional digital-signature service or transparency
log; those remain deployable hardening layers.

## F. Durable replay / stale-state resistance

`SQLiteGateLedger` persists:

- current validation gate;
- monotonic epoch;
- last accepted effect digest;
- consumed nonce;
- consumed authorization ID;
- request/effect identities;
- consumption time.

Transitions are atomic and reject:

- reused nonce or authorization;
- stale gate;
- stale epoch;
- expired request/approval;
- evidence substitution;
- intended-use substitution;
- commit substitution;
- effect rebinding;
- gate skipping.

## G. Model identifiability

`assess_local_identifiability` evaluates a model sensitivity/Jacobian matrix
using singular-value decomposition.

It reports:

- observation count;
- parameter count;
- rank and nullity;
- singular values;
- condition number;
- locally identifiable / weakly identifiable state;
- weak parameter combinations/null-space directions.

This is specifically important for BAROS biological modeling. A fitted
alpha/beta, TCP, NTCP, imaging-derived, or adaptive parameter must not be treated
as independently learned merely because an optimizer returns a numerical value.
If the available observations cannot distinguish parameter combinations, the
non-identifiability is made explicit.

## H. Evidence-acquisition / experimental-design utility

`expected_information_gain` uses a linearized Gaussian information-gain
criterion:

    EIG = 0.5 log det(I + P H^T R^-1 H)

where P is prior parameter covariance, H is the experiment sensitivity matrix,
and R is observation-noise variance.

`rank_validation_experiments` compares candidate validation actions using:

    utility = information gain
              - cost penalty
              - risk penalty
              - irreversibility penalty

Unauthorized actions receive negative-infinite utility and cannot be selected
by the ranking logic.

For BAROS, this can support choosing which bench, TPS, phantom, imaging,
dosimetric, or retrospective experiment is most informative about unresolved
model/physics uncertainty without treating clinical risk as merely another
optimization objective.

## I. Observability–controllability hazard gate

`assess_observability_controllability` separately estimates how much of a
modeled state is observable and how much is controllable.

A low-observability / high-controllability state is explicitly flagged. This
maps directly to a BAROS safety principle:

> Do not permit strong optimization authority over biological/physical states
> that are poorly observed or weakly identifiable.

For a clinical translational configuration, this can become a hard reason to
reduce optimization authority, require more measurement, or prevent progression
until the relevant state becomes observable.

## J. Evidence dependency graph and blast-radius invalidation

`EvidenceDependencyGraph` makes claim ancestry explicit.

Nodes may represent:

- raw evidence;
- analyses;
- assumptions;
- models;
- configurations;
- authorizations; and
- claims.

A downstream claim is ineligible when a transitive dependency becomes invalid
or quarantined. The graph can calculate the blast radius of a changed artifact.

Examples:

- changing the TPS version can invalidate interoperability and downstream
  retrospective claims;
- revoking a calibration file can invalidate measured-dose analyses;
- discovering a model-assumption conflict can invalidate derived TCP/NTCP
  comparisons;
- contradictory source data can quarantine all dependent claims until resolved.

This prevents stale conclusions from surviving after their evidence base changes.

## K. Adversarial verification

The added test suite exercises positive and negative paths including:

- intended-use identity changes after configuration changes;
- external-gate rejection without partner custody/reviewer;
- contradiction quarantine;
- deviation blocking;
- missing measured-dose/deliverability evidence;
- skipped-gate rejection;
- exact-effect mutation after approval;
- expiry;
- persistent replay rejection after ledger reopen;
- stale-epoch rejection;
- clinical/external progression without human authorization;
- patient-care authority rejection;
- rank-deficient/non-identifiable model detection;
- information-gain ranking;
- unauthorized experiment exclusion;
- low-observability/high-control hazard detection;
- transitive claim invalidation;
- evidence/configuration blast-radius calculation;
- dependency-cycle rejection.

## L. Clinical integration boundary

The control plane is designed around, not in place of, the clinical environment.

A partner campaign would:

1. lock the intended use and protocol;
2. execute bounded BAROS software/model verification;
3. establish model identifiability and unresolved uncertainty;
4. choose the highest-value authorized validation experiments;
5. integrate with the partner TPS/research dose-engine boundary;
6. preserve partner-controlled raw TPS/measurement artifacts;
7. compile an evidence envelope;
8. preserve discrepancies/negative results;
9. assess claim dependencies and blast radius;
10. have the qualified institutional role review the exact evidence and next
    transition;
11. consume a one-use approval for the exact next gate;
12. advance only one gate at a time.

Clinical TPS recalculation, patient-specific QA, QMP judgment, physician
judgment, IRB/regulatory authority, and treatment decisions remain external
authorities.

## Claim boundary

Passing these software controls can support claims that a BAROS research
campaign is:

- configuration locked;
- provenance bound;
- contradiction preserving;
- replay/stale-state resistant at the implemented SQLite ledger boundary;
- explicit about parameter identifiability;
- capable of ranking authorized evidence-acquisition actions;
- protected against low-observability/high-control configurations; and
- dependency aware when evidence changes.

It cannot establish:

- physical dose accuracy;
- clinically valid TCP/NTCP parameters;
- patient safety or effectiveness;
- regulatory authorization;
- treatment readiness;
- permission for patient-care use.
