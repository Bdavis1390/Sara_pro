# Worldshepherd Repository Freshness Audit — 2026-09-15

**Status:** `EVIDENCE`

**Scope:** public `Bdavis1390/Sara_pro` repository

**Purpose:** preserve useful work while identifying material that is current, historical, superseded, or requires reconciliation before it can safely guide present work.

## Executive result

The repository contains substantial useful work, but its branch/PR history has outgrown an informal lifecycle model. The appropriate corrective action is **classification and reconciliation, not bulk deletion**.

At this audit point:

- branch inventory observed: **237 branches**;
- open pull requests observed: **84**;
- the canonical SARA runtime has been merged to `main` through PR #288 at merge commit `4ded8c2c03343cd6e474cdfe27c74f772b4446ee`;
- runtime-normalization issue #287 is closed;
- top-level operating umbrellas remain #281 Platform & Assurance, #282 Science & Validation, and #283 Growth & Externalization;
- PR #279 remains useful but is `RECONCILE_REQUIRED` because its review-readiness work predates the newly canonical runtime/public information architecture;
- at least six open PRs were created before 2026-09-01 and therefore require explicit lifecycle review rather than age-based closure.

Counts are a dated repository snapshot, not permanent invariants.

## Canonical runtime freshness

PR #288 established the current repository-level runtime contract:

- canonical implementation: `deployments/sara_verified_local_v1/`;
- repository entry point: `runtime/README.md`;
- root wrapper: `scripts/sara.sh`;
- machine-readable runtime identity: `runtime/manifest.json`;
- canonical-runtime ADR: `docs/adr/0001-canonical-sara-runtime.md`;
- dedicated entry-point workflow: `.github/workflows/sara-runtime-entrypoint.yml`.

The final exact head passed the relevant gate set before merge, including Required Test and Build, CodeQL, SARA Commit Closure Evidence, NIST 800-171 precursor, Operational Resilience, TLS architecture, replacement-environment restore, rollback, Canonical Runtime Entrypoint, and SARA Verified Local v1.

The Verified Local gate also completed unit/API tests, PRE evidence export, partner-screening export, Compose validation, deployment verification, destructive backup/restore, operational snapshot, release-identity verification, and release-evidence indexing.

### Stale statement found

`docs/WORLDSHEPHERD_CAPABILITY_MAP.md` still described SARA runtime packaging as fragmented after PR #288 merged. That is a material documentation staleness defect and is corrected in the freshness-governance change set.

## Branch-retention findings

### GLOB 99073 family

Names alone are unsafe deletion signals.

The following branch aliases were compared and found to point to the same historical commit:

- `agent/glob-99073-evidence-ingestion-duplicate`
- `agent/glob-99073-evidence-ingestion-please-ignore`
- `agent/glob-99073-evidence-ingestion-temp4`
- `agent/glob-99073-evidence-ingestion-tempcheck`

Those aliases contain substantial evidence-ingestion history. The primary branch `agent/glob-99073-evidence-ingestion` is **51 commits newer** than that shared alias point and contains additional unique work.

Relative to the then-current `main`, the primary GLOB branch was observed with **129 unique commits** while also being materially behind the modern repository. Its content includes append-only discovery/evidence ledgers, negative controls, source corrections, NIST ASD tooling, transition-graph analysis, raw-hit coverage analysis, registries, and tests.

**Classification:** primary branch = `RECONCILE_REQUIRED`; identical aliases = candidate `SAFE_DELETE_AFTER_VERIFY` only after the retained primary/successor work is preserved and a final comparison is repeated.

### Research intelligence PR #3

PR #3 (`Add governed Worldshepherd research intelligence pipeline`) is old but not empty. It was observed with **12 unique commits**, 9 changed files, and 1,571 additions on a branch that has substantially diverged from modern `main`.

**Classification:** `RECONCILE_REQUIRED`, not stale-by-age deletion. Forward-port the useful source-governance/collector work if it still fits current SARA architecture and current source terms.

### GLOB PR #4

PR #4 remains the historical public review surface for the primary GLOB evidence-ingestion work. Its scientific framing explicitly retains historical/current source separation, negative controls, correction records, and blocks physical-significance promotion pending stronger statistical testing.

**Classification:** `RECONCILE_REQUIRED` under #282 Science & Validation. Preserve evidence; rebuild onto current architecture before any merge consideration.

### External-review PR #279

PR #279 contains useful security and external-review preparation, including a PRIME key-fingerprint reuse finding, clean-room reproducibility work, review kill criteria, licensing gate, hostile-review notes, and a reviewer-readiness gate.

It predates the post-professionalization/canonical-runtime source of truth.

**Classification:** `RECONCILE_REQUIRED` under #281. Forward-port useful deltas; do not overwrite current README/runtime architecture. Reviewer outreach remains on HOLD until the reconciled exact head is green.

### Administrative branch created during this audit

`tmp-check-existing-never-use` was created as an administrative probe and carries no intended product work.

**Classification:** `SAFE_DELETE_AFTER_VERIFY`. The current connector surface does not expose branch deletion, so it remains identified here rather than being falsely reported as removed.

## Pull-request aging

Open PR count alone is not a quality metric. The risk is ambiguity about whether an old PR is:

- still active;
- dependent/stacked;
- superseded;
- carrying unique evidence;
- safe to close; or
- safe to delete after preserving its successor.

The repository therefore adopts explicit lifecycle states in `FRESHNESS_POLICY.md` instead of using arbitrary age as a destructive cutoff.

A 14-day inactive/materially-behind threshold is a **classification trigger**, not an auto-close rule.

## CI/dependency freshness finding

Current workflow execution emitted deprecation warnings for action runtimes associated with older `actions/checkout` / `actions/setup-python` majors. Upstream maintained releases have advanced beyond versions still referenced in at least some repository workflows.

**Classification:** `ACTIVE` under #281.

Migration rule:

1. inventory action references;
2. upgrade maintained upstream actions in reviewable batches;
3. preserve existing inputs and least-privilege permissions;
4. run the full existing repository gates;
5. never weaken a failing check merely to complete a version migration.

This freshness change itself uses current maintained major versions for the new workflow.

## Document freshness model

The repository now distinguishes:

- `CURRENT_CANONICAL`
- `ACTIVE`
- `DATED_EVIDENCE`
- `RECONCILE_REQUIRED`
- `SUPERSEDED`
- `ARCHIVE`
- `SAFE_DELETE_AFTER_VERIFY`

Dated evidence does not expire merely due to age. It is superseded by a new evidence record when configuration, data, calibration, interpretation, or validation state changes.

## Immediate next reconciliation queue

1. Merge freshness governance after exact-head CI.
2. Reconcile PR #279 onto current `main` without regressing the canonical runtime/public architecture.
3. Inventory and migrate deprecated GitHub Action major versions through CI-proven batches.
4. Reconcile the primary GLOB 99073 branch/PR #4 under #282; only then consider removal of identical alias branches.
5. Reconcile PR #3 research-intelligence work against current SARA/PRE architecture and current source/licensing constraints.
6. Review the remaining pre-2026-09-01 open PRs and explicitly assign `ACTIVE`, `RECONCILE_REQUIRED`, `SUPERSEDED`, or `ARCHIVE` treatment.
7. Continue branch-family deduplication only when commit/tree comparison proves preservation of unique work.

## Non-claim

This audit classifies repository state. It does not validate the scientific truth of research artifacts, certify security/compliance, or establish external/partner acceptance. Those remain governed by their own evidence gates.
