# ADR-0002 — Worldshepherd Portfolio and Repository Topology

- **Status:** Accepted
- **Date:** 2026-09-15
- **Decision owner:** Worldshepherd
- **Scope:** public GitHub information architecture

## Context

Worldshepherd spans governed software, evidence/provenance, requirements intelligence, mission/autonomy integration, communications/APNT, edge AI, digital twins, RF/metasurfaces, materials/manufacturing, propulsion/energy/space, advanced physics and opportunity/capture work.

Historically, many of these lanes developed inside `Sara_pro` through a large branch and artifact history. Splitting every named concept into a separate repository now would create the appearance of product maturity without necessarily improving reproducibility, evidence custody or maintainability.

At the same time, leaving the repository as an undifferentiated accumulation makes professional evaluation unnecessarily difficult.

## Decision

`Sara_pro` remains the **current Worldshepherd umbrella/incubator repository** until a component passes explicit repository-promotion gates.

The root portfolio map is:

```text
PORTFOLIO.md
```

The canonical runnable SARA decision remains governed by ADR-0001 and is not weakened by this umbrella topology.

## Portfolio classes

Public artifacts are organized conceptually into:

1. `CANONICAL / RUNNABLE` — supported entry point plus CI/evidence contract;
2. `SOFTWARE / INTEGRATION` — code/schema/workflow exists, maturity artifact-specific;
3. `RESEARCH / SIMULATION` — model/design/study requiring explicit evidence promotion;
4. `CAPTURE / SCREENING / HISTORY` — dated requirement, opportunity, partner or provenance artifacts.

A component may span classes only when the boundaries are explicit—for example, software tooling can be implemented while the physical system it studies remains hypothetical.

## Repository-promotion gate

A component should become a standalone repository only when the split is more rigorous than leaving it in the umbrella. At minimum, require:

- a defined product/research boundary;
- authoritative source directory or migration set;
- reproducible install/run/test path when executable;
- dedicated CI relevant to its claims;
- security and secret-handling boundary;
- claim-state and evidence policy references;
- ownership/maintainer responsibility;
- version/release identity;
- provenance bridge from `Sara_pro` history;
- links back from the umbrella repository;
- migration plan for issues/PRs/docs/evidence references;
- no false implication that repository creation itself upgraded TRL, validation or certification.

## Candidate repository families

Candidates are architectural targets, not current product claims:

- `worldshepherd-sara`
- `worldshepherd-pre`
- `worldshepherd-provenance`
- `worldshepherd-labs`
- `worldshepherd-hardware`
- `worldshepherd-docs`

## Branch policy

Branches are subordinate to `main` for public truth. Branch lifecycle is governed by:

```text
docs/BRANCH_GOVERNANCE.md
```

Historical branch cleanup is permitted only after ancestry/supersession, open-PR, unique-evidence, external-reference and retention checks. Research/evidence branches receive a presumption of retention until those checks are complete.

## Consequences

### Positive

- visitors get one authoritative portfolio map;
- Worldshepherd breadth remains visible without manufacturing a forest of thin repositories;
- components earn standalone status through reproducibility/evidence rather than naming;
- historical branch cleanup can proceed without sacrificing provenance;
- SARA remains immediately runnable while other lanes retain honest maturity states.

### Costs

- `Sara_pro` remains large during the transition;
- portfolio/docs governance becomes a maintained responsibility;
- future splits require deliberate history/evidence migration work;
- branch cleanup cannot be a one-click cosmetic operation.

## Reversal / supersession

This ADR may be superseded by an organization-level repository architecture once multiple Worldshepherd components independently satisfy the promotion gate. Any superseding decision must preserve stable redirects/navigation and evidence provenance from this repository.
