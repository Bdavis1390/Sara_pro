# Worldshepherd Recursive Improvement Producer Bridges v0.1

## Purpose

This document records the executable producer bridges that feed governed `ImprovementProposal` records into Worldshepherd Recursive Improvement (WS-RI).

The producer bridges are translation and routing layers only. They do not merge code, append configuration snapshots, deploy releases, actuate hardware, contact external parties, spend funds, submit proposals, or elevate scientific/readiness claims.

## Producer 1: WS-OMEGA -> WS-RI

`omega_to_improvement()` translates a `DiscoveryNode` into an `ImprovementProposal`.

Preserved lineage:

- OMEGA node ID;
- source references;
- discovery kind;
- discovery evidence state;
- falsification tests;
- downstream Worldshepherd routes.

Conservative evidence mapping:

| OMEGA evidence state | WS-RI baseline capability state |
| --- | --- |
| SOURCE_VERIFIED / CORROBORATED | SUPPORTED_BY_LITERATURE |
| SINGLE_SOURCE / HYPOTHESIS | HYPOTHESIS |
| SIMULATED | SIMULATED_ONLY |
| SPECULATIVE | SPECULATIVE_EXTENSION |
| CONFLICTING / UNVERIFIED | NOT_CURRENTLY_CLAIMED |

The translation never assigns a target maturity level. It adds source/evidence and red-team gates, plus all OMEGA falsification tests.

## Producer 2: PRE -> WS-RI

`pre_to_improvement()` translates a `RequirementDeltaRecord` into an `ImprovementProposal`.

Preserved lineage and context:

- PRE requirement-delta ID;
- source URL and topic reference;
- demand class;
- affected lanes;
- current capability status;
- missing capability;
- required experiment/demonstration;
- evidence targets;
- partner needs;
- PRE claims boundary.

Demand class remains demand evidence only:

- `CONFIRMED_DEMAND` does not prove Worldshepherd capability;
- `EMERGING_DEMAND` does not prove future solicitation language;
- `WORLDSHEPHERD_FORECAST` is explicitly a preparation signal and not evidence that an external customer requirement exists.

A source that is not PRE capture-ready raises the improvement risk level and remains blocked from consequential use until source resolution.

## Producer 3: Qualification Evidence / TEVV -> WS-RI

`evidence_to_improvement()` translates a `QualificationEvidenceRecord` into feedback for Worldshepherd change control.

Result handling:

| Qualification result | WS-RI behavior |
| --- | --- |
| PASS | scoped test-result candidate; no maturity promotion |
| FAIL | high-risk failure/remediation candidate |
| INCONCLUSIVE | uncertainty-resolution candidate |

The bridge preserves negative evidence and keeps the original qualification record unchanged. A failure adds a root-cause gate; an inconclusive result adds an uncertainty-resolution gate; all results receive evidence-review and regression gates.

Passing evidence remains bounded to the recorded test scope, environment, configuration, inputs, uncertainty, and capability status.

## Shared routing

`route_improvement()` emits a deterministic routing envelope. Depending on trigger and lifecycle state, routes can include:

- ECHO;
- WS-OMEGA;
- PRE;
- PRIME-TEVV;
- PRIME;
- OVERWATCH;
- RED-TEAM;
- PARTNER-SCREENING;
- CONFIG-CUSTODY.

Every routing envelope records:

```text
deployment_authorized=false
claim_promotion_performed=false
external_execution_performed=false
```

`CONFIG-CUSTODY` is excluded until the improvement is already `PROMOTED` through qualification, identified-human review, and an authorization reference.

## Configuration custody boundary

`build_promoted_configuration_snapshot()` may stage a `ConfigurationSnapshot` only for a promoted improvement record with:

- accepted human review;
- qualification references;
- authorization reference;
- identified actor.

The function returns a snapshot candidate. It does **not** append that snapshot to the custody ledger. Existing authorized change procedures remain responsible for any actual configuration transition.

## Feedback topology

```text
OMEGA discovery --------+
                        |
PRE requirement --------+--> WS-RI proposal
                        |       |
QE / TEVV result -------+       v
                         validation / red-team
                                |
                                v
                         human + PRIME gate
                                |
                 +--------------+--------------+
                 |                             |
              reject /                     promote
              quarantine                       |
                                               v
                                     custody/change candidate
                                               |
                                     authorized change path
                                               |
                                               v
                               ECHO / PRE / OMEGA feedback
```

## Claims boundary

Current code establishes producer translation, deterministic routing, validation-state gating, and configuration-snapshot staging as software candidates on the feature branch.

It does not establish autonomous self-modification, continuous operation, physical validation, certification, partner validation, mission effectiveness, external authorization, or deployment.

Exact-head protected CI remains the software evidence gate before any stronger implementation claim or merge.
