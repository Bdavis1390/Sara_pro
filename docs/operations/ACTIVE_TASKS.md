# Worldshepherd active-task operating model

Worldshepherd has exactly **three** top-level active tasks.

All detailed issues, pull requests, experiments, opportunities, outreach threads, compliance gates, and research lanes route to **one primary umbrella** below. Detailed child issues remain open when they carry useful evidence, history, acceptance criteria, or deadlines; they are not separate top-level priorities.

This rule exists to prevent activity volume from masquerading as execution priority.

## ACTIVE 1/3 — Platform & Assurance

GitHub umbrella: **#281**

Primary output: trustworthy software/system behavior.

Includes SARA, PRIME, ECHO, OVERWATCH, identity/security, authorization, custody, replay, DDIL/recovery, reproducibility, evaluator packages, CI/release evidence, SBOM/dependency evidence, claims controls, public-repository security boundaries, governance, licensing/open-source-scope decisions, and software-facing compliance-readiness evidence.

Current spearhead: **PR #279 external-review readiness**.

### Exit signals

- clean-room reviewer path reproduces the stated behavior;
- high-severity trust-boundary defects are either fixed or explicitly bounded;
- unauthorized/tampered/replayed/malformed states fail closed within the stated threat model;
- external technical reproduction or falsification exists;
- licensing/governance language matches objective legal/IP status;
- architecture is simplified when existing standards/components can replace bespoke machinery.

## ACTIVE 2/3 — Science & Validation

GitHub umbrella: **#282**

Primary output: measured scientific/domain evidence.

Includes materials, RF/metasurfaces, propulsion, anomalous-force metrology, sensing/APNT measurements, quantum hardware evidence, robotics/HIL, aerospace, HELIOS-LINK, TIDELENS, AEROSHEPHERD, BAROS, calibrated instrumentation, uncertainty, raw-data custody, repeatability, negative controls, simulation-to-measurement closure, laboratory review, and independent physical/domain replication.

### Exit signals

- at least one Worldshepherd-specific article/dataset crosses from protocol/simulation to calibrated measurement;
- raw/native data, calibration, article identity, configuration, uncertainty and negative results are retained;
- claims advance only to the maturity actually established;
- independent or partner-controlled review/replication closes stronger evidence gates.

## ACTIVE 3/3 — Growth & Externalization

GitHub umbrella: **#283**

Primary output: external review, relationship, transition, award, contract, adoption, or revenue.

Includes Linus Torvalds/Linux Foundation/AAIF engagement, NIST community routes, DoD and civilian-agency capture, SBIR/STTR/DIU/DARPA/NAVWAR/NAVSEA opportunities, partner/co-prime strategy, NVIDIA/Anduril/primes/labs/universities, first paid pilot, pricing/commercialization, proposal deadlines, outreach/follow-up, data-room/IP/legal diligence, and transition/follow-on paths.

### Exit signals

- technical outreach uses one clear ask and one evidence-backed artifact;
- substantive reviewer/partner findings are routed back into ACTIVE 1/3 or 2/3;
- qualified opportunities progress on evidence, eligibility and deadline reality rather than prestige;
- an executed paid pilot or award is distinguished from pipeline, interest or outreach;
- partnership/adoption language is used only when objective agreement/evidence exists.

## Routing decision

Every new item gets one primary parent:

```text
Is the main deliverable software/security/reproducibility/governance?
  -> ACTIVE 1/3

Is the main deliverable a measurement/test article/scientific or domain result?
  -> ACTIVE 2/3

Is the main deliverable a reviewer/partner/customer/opportunity/proposal/award/adoption/revenue outcome?
  -> ACTIVE 3/3
```

A child can support another umbrella, but it still has one primary parent. Cross-links are dependencies, not additional top-level tasks.

## Claims-control invariant

No umbrella can promote evidence belonging to another umbrella by association:

- green CI does not prove physical performance;
- a lab protocol does not prove a measured result;
- outreach does not equal independent validation;
- partner interest does not equal partnership;
- an opportunity ceiling does not equal revenue;
- literature does not validate a Worldshepherd-specific article;
- a public repository does not imply an open-source license;
- internal evidence does not become certification or government authorization.

## Current cross-umbrella spearhead

The immediate shared spearhead is **external systems review of the SARA control plane**:

1. ACTIVE 1/3 finishes PR #279 and freezes a reproducible review target.
2. ACTIVE 3/3 performs one concise criticism-first outreach only after the gate is green.
3. Any technical finding returns to ACTIVE 1/3 for disposition and rerun.
4. Partnership/upstream contribution is discussed only if external review identifies genuine reusable value.

This is the operating model for all Worldshepherd work until intentionally superseded by a reviewed replacement.