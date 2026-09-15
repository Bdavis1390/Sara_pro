# Licensing decision gate

## Current status

This repository is publicly inspectable, but this review packet does **not** assert that the entire Worldshepherd repository is open source under a specific license.

That distinction matters. Public visibility is not the same thing as granting permission to copy, modify, redistribute, or sublicense the work.

Until an explicit license is selected and applied to a defined scope, external review should be treated as **inspection and discussion**, not an invitation to reuse the repository's code.

## Why this is a release blocker for an open-source partnership

A technically serious open-source collaborator should not have to guess:

- what they may copy;
- what they may modify;
- whether contributions can be redistributed;
- whether patent rights are granted;
- whether different directories have different licensing terms;
- whether broader research artifacts are intended to share the same license as the software.

Therefore the project should not describe Worldshepherd itself as an open-source project until this decision is complete.

## Decision options to evaluate

### Option A — Apache License 2.0 for a carved-out software core

Potential advantages:

- permissive integration;
- explicit patent-license language;
- suitable for reusable infrastructure and cross-ecosystem adoption;
- allows a separately governed commercial/research layer to remain outside the open-source scope.

Potential cost:

- downstream proprietary use is permitted, which may be inconsistent with project strategy.

### Option B — GPL-family license for a carved-out software core

Potential advantages:

- strong reciprocal open-source expectations;
- familiar to Linux/kernel communities.

Potential cost:

- copyleft obligations can complicate integration with some partners and architectures;
- the exact GPL version and compatibility consequences require deliberate review.

### Option C — dual licensing

Potential advantages:

- an open-source path plus a separate commercial license can coexist.

Potential cost:

- contributor agreements, copyright ownership, inbound licensing, and administrative discipline become more important.

### Option D — remain source-visible but not open source

Potential advantages:

- preserves maximum control while still allowing technical inspection.

Potential cost:

- substantially weaker fit for an open-source infrastructure partnership and for upstream reuse.

## Recommended scope decision

Do **not** license the entire repository by accident.

First decide whether the candidate reusable core should be limited to a narrow surface such as:

```text
deployments/sara_verified_local_v1/worldshepherd_sara/
deployments/sara_verified_local_v1/tests/
selected operational/security documentation
```

Broader physics, opportunity, partner, qualification, and business artifacts should be reviewed separately for IP, data-rights, export-control, and contractual implications before inheriting any software license.

## Required before external open-source partnership language

- [ ] Define the exact directory/repository scope to be licensed.
- [ ] Confirm ownership/right-to-license for every included file.
- [ ] Select license and exact version.
- [ ] Add root or scoped license notices.
- [ ] Define inbound contribution terms.
- [ ] Check dependency-license compatibility.
- [ ] Separate third-party artifacts and data where necessary.
- [ ] Obtain legal review appropriate to the intended commercial/defense/research uses.

## Current claim

**REQUIRES LEGAL REVIEW / DECISION.**

Technical review can proceed before this gate closes. Code reuse, formal open-source contribution, or an open-source partnership should not be represented as ready until it does.
