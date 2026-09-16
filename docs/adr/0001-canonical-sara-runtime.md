# ADR-0001 — Canonical SARA Runtime Location

- **Status:** Accepted
- **Date:** 2026-09-15
- **Decision owner:** Worldshepherd
- **Claim state:** `IMPLEMENTED IN SOFTWARE`
- **Supersedes:** implicit/ambiguous runtime-location conventions

## Context

`Sara_pro` accumulated research, integration, deployment and historical runtime artifacts over time. The repository therefore had two simultaneous problems:

1. a professional user could not determine the supported runnable SARA path from the repository root; and
2. an older `worldshepherd-sspadawanzz-admin` branch still contained historical runtime work, creating a risk that stale code could be mistaken for the current implementation.

Current `main` already contains a materially hardened and protected runtime package at:

```text
deployments/sara_verified_local_v1/
```

The current package includes an installable Python project, localhost-oriented configuration, independently configured relay/admin credentials, API/UI implementation, unit/API tests, deployment verification, recovery/resilience tooling, evidence generation, and a dedicated GitHub Actions gate.

A current-main differential audit (`deployments/sara_verified_local_v1/docs/WS_QE_2026_ADM_001.md`) reconciles historical SSPADAWANZZ administrative requirements with the hardened implementation and explicitly narrows current relay semantics to local evidence recording rather than external message delivery.

## Decision

`deployments/sara_verified_local_v1/` is the **canonical runnable SARA / SSPADAWANZZ local package** for this repository.

The repository will expose that implementation through stable root-level entry points rather than copying the source tree:

```text
runtime/README.md
scripts/sara.sh
```

The root README must identify the canonical package and its protected verification path.

The source package, tests, constraints, deployment artifacts and evidence tooling remain co-located under `deployments/sara_verified_local_v1/` to avoid divergent copies.

## Operator contract

From the repository root, the supported local-development path is:

```bash
bash scripts/sara.sh setup
bash scripts/sara.sh run
```

Additional supported wrapper actions are:

```bash
bash scripts/sara.sh check
bash scripts/sara.sh test
bash scripts/sara.sh smoke
bash scripts/sara.sh path
```

The wrapper must fail closed when required canonical files, runtime environment or local credentials are missing.

## Verification contract

Changes to the implementation remain governed by:

```text
.github/workflows/sara-verified-local-v1.yml
```

Changes to repository-level runtime locators/wrappers are governed by a lightweight canonical-entrypoint workflow.

A change that breaks either contract must not be represented as a valid canonical runtime update.

## Security and claims boundary

The canonical local runtime does not imply:

- external message delivery or third-party activation;
- arbitrary command execution;
- autonomous scanning/broadcasting/self-expansion;
- immutable or independently attested audit storage;
- CMMC certification;
- NIST 800-171 conformity or authorization;
- DFARS compliance;
- CUI or classified-system authorization;
- partner/government validation;
- field, flight or physical-system validation.

`/v1/relay` is treated as governed local relay **recording/audit** unless a separately versioned, tested and authorized external-delivery adapter is introduced later.

## Consequences

### Positive

- A new engineer can find and run SARA from the repository root.
- Current hardened code is preferred over stale historical branch artifacts.
- Source, tests, constraints and evidence stay configuration-aligned.
- Future documentation can reference one canonical runtime identity.
- A future standalone `worldshepherd-sara` repository can be evaluated as an explicit migration rather than an informal copy.

### Costs

- The canonical source remains nested under `deployments/` until a controlled repository split or layout migration is justified.
- Root wrapper/documentation changes must stay synchronized with the deployment package.
- The repository still contains historical and experimental artifacts that require maturity labeling.

## Future migration rule

A dedicated `worldshepherd-sara` repository may supersede this decision only if the migration preserves, at minimum:

1. source history or an auditable provenance bridge;
2. exact test and CI identity;
3. release/evidence links;
4. claims-boundary documentation;
5. security configuration and secret-handling rules;
6. a compatibility or transition notice in `Sara_pro`.

Until then, the path declared in this ADR is authoritative.