# Worldshepherd Branch Governance

**Status:** `CANONICAL` repository-governance guidance  
**Scope:** branches in `Bdavis1390/Sara_pro`

The repository has accumulated a large engineering/research branch history. That history may contain merged work, abandoned experiments, superseded implementations, unmerged evidence or externally referenced commit identities. Cleanup must therefore be **evidence-safe**, not cosmetic.

## Governing rule

> A branch name is not proof that the branch is disposable.

Names containing `temp`, `duplicate`, `please-ignore`, an old date, an old version or a completed topic are **review signals only**. Deletion requires ancestry, PR, provenance and retention checks.

## Lifecycle states

| State | Meaning | Normal action |
|---|---|---|
| `ACTIVE` | current engineering/research work with an owner and intended next gate | continue through PR/evidence process |
| `REVIEW` | work is ready for technical/claims/CI review | open/reconcile PR; do not delete |
| `MERGED` | intended changes are incorporated into authoritative `main` | eligible for cleanup after evidence checks |
| `SUPERSEDED` | replaced by a named newer branch/commit/design | retain until replacement/provenance link is recorded |
| `EVIDENCE-HOLD` | branch contains uniquely referenced test, qualification, forensic or historical evidence | retain even if code is obsolete |
| `ARCHIVE-CANDIDATE` | no active PR, no unique evidence, and merge/supersession is demonstrated | may be deleted after checklist review |

These states are governance concepts. Until automated branch metadata exists, record the state in the relevant issue/PR or branch-audit ledger.

## New branch naming

Use one of these forms for new work:

```text
feature/<component>-<capability>
fix/<component>-<problem>
docs/<topic>
research/<lane>-<experiment-or-model>
capture/<program-or-opportunity>-<gate>
release/<component>-v<major>.<minor>
governance/<topic>
```

Prefer stable semantic names over timestamps unless the date is genuinely part of the artifact identity. Avoid persistent branches named `temp`, `test`, `duplicate`, `please-ignore`, `final-final`, or similar ambiguous labels.

## Branch creation requirements

A durable branch should have:

1. a bounded objective;
2. a component/lane owner;
3. intended evidence or acceptance criteria;
4. a claims boundary when the work can affect public technical assertions;
5. a defined destination: merge, evidence hold, explicit supersession or abandonment with rationale.

## Archive/deletion gate

A branch may become `ARCHIVE-CANDIDATE` only when **all** applicable checks pass:

- no open PR depends on it;
- its required changes are already on `main`, or a named superseding branch/commit is authoritative;
- no issue, release, evidence manifest, publication, partner package or external reference relies on the branch ref itself;
- no unique test output, qualification record, source snapshot or provenance artifact would become materially harder to retrieve;
- no security/incident investigation requires retention;
- no public-release, legal, IP, contractual or export-review hold requires retention;
- the replacement/provenance path is recorded before deletion.

When uncertain, retain the branch and classify it `EVIDENCE-HOLD` until reviewed.

## Technical ancestry checks

For a local clone, useful checks include:

```bash
# Does main contain the branch tip?
git merge-base --is-ancestor <branch> main

# What commits exist only on the branch?
git log --oneline main..<branch>

# What changed relative to the merge base?
git diff main...<branch>
```

An ancestor check passing is strong evidence that code history is incorporated, but it is **not sufficient by itself** if external systems reference the branch name or if retention obligations exist.

## Supersession record

Before removing a superseded branch, record at minimum:

```yaml
branch:
state: SUPERSEDED | ARCHIVE-CANDIDATE
reviewed_utc:
reviewer:
replacement_branch_or_commit:
merged_to_main: true | false
open_pr: null
unique_commits_reviewed: true | false
evidence_refs: []
external_refs_checked: true | false
retention_holds: []
deletion_decision: RETAIN | APPROVE
rationale:
```

## Branches vs capability claims

Branches are implementation/research history. They do not independently establish:

- current product status;
- physical performance;
- field readiness;
- partner validation;
- government acceptance;
- standards conformity or certification;
- security authorization.

Only authoritative code/configuration plus reproducible evidence can support those claims.

## Pull-request discipline

For durable work:

1. branch from current `main` unless a documented dependency requires otherwise;
2. keep the scope bounded;
3. link the governing issue/requirement when one exists;
4. declare claims affected by the change;
5. require relevant CI/evidence gates;
6. merge only after failures are reconciled rather than bypassed;
7. allow branch cleanup only after the archive/deletion gate above.

## Historical cleanup campaign

The existing branch set predates this policy and should be reviewed in batches rather than mass-deleted. Recommended order:

1. obvious duplicate/temp-name families;
2. old merged CI/fix branches;
3. version-series branches with later canonical successors;
4. opportunity/capture branches with passed deadlines or superseding packages;
5. research branches, which receive the strongest evidence-retention presumption.

Every batch should produce a review ledger before any destructive action.
