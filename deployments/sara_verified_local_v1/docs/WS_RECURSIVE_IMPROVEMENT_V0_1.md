# Worldshepherd Recursive Improvement Protocol v0.1

## Purpose

Worldshepherd Recursive Improvement (WS-RI) converts discoveries, failures, anomalies, requirement deltas, test results, research findings, partner feedback, security events, opportunities, and operator feedback into governed proposals for improving Worldshepherd itself.

WS-RI is deliberately **not** a self-modifying execution engine. It is an auditable bridge between Worldshepherd's discovery/evidence systems and the existing human/PRIME authorization boundary.

The governing sequence is:

```text
OBSERVE
  -> CROSS-REFERENCE
  -> DEFINE IMPROVEMENT DELTA
  -> VALIDATE
  -> HUMAN REVIEW / PRIME AUTHORIZATION
  -> PROMOTE RECORD OR REJECT / QUARANTINE
  -> IMPLEMENT THROUGH AN AUTHORIZED CHANGE PATH
  -> MEASURE
  -> FEED RESULTS BACK INTO ECHO / PRE / OMEGA
```

Promotion of an improvement record means the change is accepted as a governed improvement candidate/baseline decision. It does **not** itself deploy code, actuate hardware, contact a partner, submit a proposal, spend funds, or elevate a scientific or readiness claim.

## Why this layer is needed

Worldshepherd already contains complementary mechanisms:

- **WS-OMEGA** recursively generates observations, hypotheses, contradictions, experiments, partner candidates, opportunities, standards gaps, prior-art checks, and risks while failing closed on claim promotion and external execution.
- **PRE** records requirement deltas and keeps source status separate from capability maturity.
- **Qualification Evidence** records test configuration, result, uncertainty, negative evidence, operator, review, and supersession state.
- **ECHO** preserves provenance and evidence custody.
- **PRIME SENTINEL** remains the authorization boundary for consequential execution.
- **OVERWATCH / RED-TEAM / TEVV** provide monitoring, contradiction, risk, and verification routes.

What was missing was a canonical record whose subject is explicitly: **"Worldshepherd should change in this way because of this evidence, with these risks and these validation gates."**

WS-RI supplies that record without creating a parallel assurance system.

## Canonical improvement record

`ImprovementProposal` records:

- stable improvement ID;
- trigger kind;
- source references;
- affected Worldshepherd lanes;
- baseline artifacts and capability state;
- proposed change;
- target capability status, if any;
- expected benefit;
- assumptions;
- risks and risk level;
- required validation tests;
- success metrics;
- retained negative evidence;
- reversibility;
- generator and creation timestamp;
- lifecycle state;
- identified-human review;
- qualification references;
- authorization reference.

The object carries explicit false fields for self-authorized claim promotion and external execution. Setting either true fails validation.

## Lifecycle

```text
PROPOSED
   |
   v
VALIDATING ----------------------+
   |                              |
   | any required FAIL            | missing / inconclusive
   v                              |
QUARANTINED <---------------------+
   |
   | new evidence / revised proposal
   v
PROPOSED / VALIDATING

VALIDATING
   |
   | all required tests PASS
   v
HUMAN_REVIEW_REQUIRED
   |                    |
   | reject             | accept + qualification refs
   v                    | + authorization ref
REJECTED                 v
                       PROMOTED
                          |
                          | later stronger baseline
                          v
                      SUPERSEDED
```

No automated path leads directly from a generated proposal to `PROMOTED`.

## Validation semantics

`assess_improvement()` is fail-closed:

1. Any required test `FAIL` -> `QUARANTINED`.
2. Any required test missing or `INCONCLUSIVE` -> `VALIDATING`.
3. Only complete PASS coverage -> `HUMAN_REVIEW_REQUIRED`.
4. The assessment always records `claim_promotion_performed=false`.
5. The assessment always records `external_execution_performed=false`.

`record_human_decision()` can promote the record only when:

- the record is already in `HUMAN_REVIEW_REQUIRED`;
- an identified reviewer is present;
- a review rationale is present;
- qualification evidence references are present;
- an authorization reference is present.

The function records governance state only; execution remains outside this module.

## Claims and evidence rules

WS-RI inherits the strictest existing Worldshepherd claims boundary:

- A prediction is preparation, not evidence of capability.
- Software implementation is not evidence of physical performance.
- Literature support is not internal validation.
- Simulation is not physical validation.
- Partner marketing material or outreach is not partner validation.
- Administrative controls do not establish external certification, authorization, clearance, CMMC status, NIST 800-171 conformity, or operational readiness.
- Failed, anomalous, contradictory, revoked, and superseded evidence must remain traceable.
- Cross-domain reuse is a hypothesis until the reused capability passes the receiving lane's own validation gates.

## Integration routes

Recommended producer routes into WS-RI:

| Producer | Improvement trigger examples |
| --- | --- |
| WS-OMEGA | contradiction, negative space, experiment, risk, cross-domain discovery |
| PRE | requirement delta, recurring demand, standards gap |
| TEVV / QE | pass, fail, uncertainty shift, regression |
| ECHO | provenance conflict, stale evidence, custody anomaly |
| PRIME | authorization-policy gap, denied action pattern |
| OVERWATCH | operational anomaly, reliability degradation |
| Partner screening | validated external feedback or integration constraint |
| Security | vulnerability, configuration drift, control failure |
| Human operator | correction, new objective, observed workflow deficiency |

Recommended downstream routes from an accepted improvement record:

```text
software change -> branch / tests / CI / review / authorized merge
model change    -> benchmark / ablation / TEVV / review
physical design -> simulation / coupon or prototype test / independent measurement / review
claims change   -> evidence graph / claims-boundary review / human approval
opportunity     -> PRE / partner screening / capture review
security        -> containment / verification / authorized remediation
```

## Executable OMEGA -> WS-RI bridge

`improvement_routing.py` now provides the first executable bridge from recursive discovery into the improvement lifecycle.

`omega_to_improvement()` translates a `DiscoveryNode` into an `ImprovementProposal` while preserving the OMEGA node ID and source references as lineage. It maps discovery type to an improvement trigger and maps discovery evidence state to a conservative baseline capability state. It deliberately does not assign a target maturity level.

The conservative evidence mapping is:

| OMEGA evidence state | WS-RI baseline capability state |
| --- | --- |
| SOURCE_VERIFIED / CORROBORATED | SUPPORTED_BY_LITERATURE |
| SINGLE_SOURCE / HYPOTHESIS | HYPOTHESIS |
| SIMULATED | SIMULATED_ONLY |
| SPECULATIVE | SPECULATIVE_EXTENSION |
| CONFLICTING / UNVERIFIED | NOT_CURRENTLY_CLAIMED |

This mapping is intentionally non-promotional. A verified source can establish that external evidence exists; it cannot establish that Worldshepherd has physically demonstrated or internally proven the capability.

Every OMEGA-derived proposal receives at least two qualification gates:

- a source/evidence gate;
- a red-team gate.

Any OMEGA falsification tests and caller-specified additional tests are added to those required gates.

`route_improvement()` returns a deterministic routing envelope only. It can route records toward ECHO, WS-OMEGA, PRE, PRIME-TEVV, PRIME, OVERWATCH, RED-TEAM, partner screening, and configuration custody according to trigger and lifecycle state. It explicitly records:

- `deployment_authorized=false`;
- `claim_promotion_performed=false`;
- `external_execution_performed=false`.

Configuration custody is excluded until the improvement record reaches `PROMOTED` through the existing validation and human/authorization gates.

## Configuration-custody staging boundary

`build_promoted_configuration_snapshot()` connects an accepted WS-RI record to the existing append-only configuration custody model.

The function requires:

- `state=PROMOTED`;
- accepted identified-human review;
- qualification references;
- an authorization reference;
- an identified actor.

It then returns a `ConfigurationSnapshot` whose reason records the improvement ID, authorization reference, and qualification references.

The function **does not append the snapshot to the ledger**. It therefore does not merge code, change the deployed configuration, deploy a release, actuate hardware, or perform an external action. Existing configuration-custody and authorized change paths remain the execution boundary.

This separation creates the following traceable sequence:

```text
OMEGA DISCOVERY
  -> WS-RI PROPOSAL
  -> QUALIFICATION / RED-TEAM
  -> HUMAN + PRIME AUTHORIZATION
  -> PROMOTED RECORD
  -> CONFIGURATION SNAPSHOT CANDIDATE
  -> AUTHORIZED CUSTODY APPEND / CHANGE PROCESS
  -> OBSERVATION / ECHO / OMEGA FEEDBACK
```

## Initial standing doctrine encoded by WS-RI

For every materially relevant new input, Worldshepherd should ask:

1. What existing requirements, claims, designs, tests, partners, opportunities, and risks does this touch?
2. Does it support, contradict, supersede, or leave prior evidence unchanged?
3. Is there a reusable cross-domain capability here?
4. What exact improvement is proposed?
5. What assumptions could make that improvement wrong?
6. What falsification or qualification tests are required?
7. What negative evidence must be preserved?
8. Is the proposed change reversible?
9. What human/PRIME authorization is required before promotion or execution?
10. After implementation, what measurement feeds the result back into the next cycle?

## Current implementation claim

The v0.1 branch implements the **recursive improvement schema, deterministic validation-state logic, OMEGA-to-WS-RI translation, deterministic downstream routing, and promoted-record configuration-custody staging**.

Unit tests cover fail-closed boundaries, quarantine behavior, human-review gating, promotion-record requirements, rejection, supersession, conservative evidence-state translation, non-inflation of capability maturity, routing gates, and configuration lineage staging.

This does not establish:

- autonomous self-modification of a deployed Worldshepherd host;
- continuous scheduler operation;
- automatic merging or deployment;
- physical validation of any technology;
- autonomous external communication or action;
- certification or government authorization;
- improved mission performance until the affected lane is separately tested.

Those remain separate evidence and authorization gates.
