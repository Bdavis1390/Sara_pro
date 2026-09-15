# WS Army Decision Program v0.1

**Status:** DRAFT / SIMULATED_ONLY / INTERNAL SOFTWARE DEMONSTRATOR / BLOCK MERGE

**Date:** 2026-09-12

**Opportunity alignment:** ARM26BX06-NV012 (SBIR) / ARM26TX06-NV003 (STTR)

**Authoritative opportunity source reviewed:** https://armysbir.army.mil/

## Purpose

This bounded implementation tests whether existing Worldshepherd governance and provenance patterns can support a schema-driven, reproducible decision program without claiming Army acceptance, DAOSoft replacement, production readiness, external validation, or a completed agentic-AI product.

The implementation focuses on the portions of the topic that can be falsifiably demonstrated with synthetic data:

- objectives, options, constraints, assumptions, risks, and bias checks represented as first-class structured objects;
- deterministic evaluation of declared alternatives against declared evidence;
- explicit constraint failures rather than silent option removal;
- explicit unvalidated and contradicted assumptions;
- explicit bias-check warnings/failures;
- a bounded `what flips the decision` sensitivity surface;
- a provenance-bearing Decision Package hash;
- longitudinal refresh that preserves the prior package hash instead of overwriting history;
- a governed agentic-plan seam in which every generated workflow step remains `PROPOSED` and requires identified-human authority;
- no automatic human signoff.

## Implementation

### Core module

`worldshepherd_sara/decision_program.py`

The module implements:

- `DecisionSpec`
- `Objective`
- `Option`
- `Constraint`
- `Assumption`
- `Risk`
- `BiasCheck`
- `EvidenceDatum`
- `DecisionEpoch`
- `OptionEvaluation`
- `FlipCondition`
- `DecisionPackage`
- `DecisionHistory`
- deterministic evaluation and canonical SHA-256 package hashing
- longitudinal package chaining through `parent_package_hash`
- bounded PRIME `ActionProposal` workflow steps

### Demo A — point trade study

The first synthetic epoch evaluates three notional ground-vehicle subsystem architectures against declared mass, unit-cost, and reliability objectives plus declared hard constraints, assumptions, option-specific risks, and bias checks.

The expected result is a single recommendation that is still only `READY_FOR_HUMAN_REVIEW`. The software does not sign or execute an acquisition decision.

### Demo B — longitudinal decision program

The second synthetic epoch changes cost and reliability evidence. The system recomputes from the declared evidence rather than inheriting the prior recommendation, preserves the prior package hash, and emits a new package/version.

This demonstrates the intended decision-program property:

`decision v1 -> changed evidence -> explicit delta -> deterministic reevaluation -> decision v2`

The older result remains auditable rather than being silently replaced.

## Decision-flip logic

The first implementation computes the aggregate score margin between the recommended option and runner-up and expresses, per declared objective, the normalized shift sufficient to erase that margin if other quantities remain unchanged.

This is a bounded sensitivity indicator, not a general causal model or proof of real-world decision robustness.

## Governance boundary

The generated workflow plan uses the repository's existing PRIME `ActionProposal` contract. Every step remains `PROPOSED` and requires `identified-human-authority`.

The demonstrator intentionally does not:

- auto-approve an analysis plan;
- auto-sign a Decision Package;
- execute procurement or contracting actions;
- contact an Army technical point of contact;
- modify external systems;
- contain weapons-targeting or lethality logic.

## Evidence and failure behavior

The implementation fails closed on:

- duplicate option/metric evidence;
- evidence for unknown options;
- evidence for undeclared metrics;
- missing required metric evidence;
- invalid option references from risk objects;
- all-options-infeasible conditions;
- contradicted assumptions;
- failed bias checks.

Warnings preserve unvalidated assumptions and bias-check warnings instead of hiding them.

## Focused verification gate

`.github/workflows/ws-army-decision-program-v0-1.yml`

The dedicated workflow:

1. checks out the exact PR head;
2. records the tested SHA and claims boundary;
3. installs the pinned repository CI dependencies;
4. compiles the new module;
5. runs only the bounded decision-program regression suite.

Tests cover deterministic replay, no automatic signoff, recommendation refresh, package-history linkage, decision-flip output, assumption contradiction, bias-check failure, missing/unknown evidence, hard-constraint failure, and duplicate evidence rejection.

## Claims boundary

Current allowed claim after implementation but before successful exact-head CI review:

**IMPLEMENTED IN SOFTWARE — DRAFT / VALIDATION PENDING**

After successful exact-head focused CI, the maximum allowed claim is:

**PROVEN INTERNALLY FOR THE SYNTHETIC V0.1 DEMONSTRATOR SCOPE**

The following remain **NOT CURRENTLY CLAIMED**:

- Army validation, adoption, acceptance, or endorsement;
- SBIR/STTR eligibility or award readiness;
- production agentic-AI capability;
- autonomous acquisition authority;
- SysML 2.0 interoperability;
- digital-thread/digital-twin integration;
- DAOSoft replacement or compatibility;
- ground-vehicle engineering validity of synthetic demo values;
- external customer validation;
- commercial traction;
- CMMC/NIST compliance or certification.

## Next gates

1. Exact-head CI must pass.
2. Independent exact-head review must confirm deterministic scoring, hash stability, and fail-closed schema behavior.
3. Add a topic-specific ground-vehicle domain schema using authoritative non-sensitive engineering data or qualified partner input.
4. Add explicit evidence-to-claim provenance nodes compatible with the existing ECHO evidence graph.
5. Add a governed human-review/decision record without enabling automatic signature.
6. Demonstrate SysML/digital-engineering interchange only after a concrete tool/schema boundary is available.
7. Validate the two demo workflows with an external engineering/acquisition user before making a customer-value claim.
8. Verify legal entity, SBIR/STTR, SAM/UEI and other contracting eligibility before any formal submission claim.

No merge or external submission is authorized by this implementation alone.
