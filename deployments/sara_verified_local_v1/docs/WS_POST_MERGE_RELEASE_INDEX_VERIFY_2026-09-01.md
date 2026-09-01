# WS Post-Merge Release Index Verification — 2026-09-01

## Purpose

This record documents the post-merge release-index verification patch for the Worldshepherd/SARA Verified Local v1 evidence path.

The prior release-index path generated a machine-readable `release-index.json` in PR runs and non-PR runs, but non-PR runs used a broad merge-state label:

```text
POST_MERGE_OR_MANUAL_RUN
```

That was useful, but not precise enough to distinguish a merged `main` push from a manual or non-main run.

This patch adds explicit release-state separation so the post-merge `main` run can be verified independently.

## Added release states

```text
PR_CANDIDATE_UNMERGED
MAIN_BRANCH_PUSH
MANUAL_OR_NON_MAIN_RUN
```

## Derivation rule

```text
if GITHUB_EVENT_NAME == pull_request:
    merge_state = PR_CANDIDATE_UNMERGED
elif GITHUB_EVENT_NAME == push and GITHUB_REF == refs/heads/main:
    merge_state = MAIN_BRANCH_PUSH
else:
    merge_state = MANUAL_OR_NON_MAIN_RUN
```

## Validation rule

The release-index builder rejects mismatches between the supplied merge-state label and the event/ref context.

Examples:

```text
pull_request + refs/pull/<n>/merge => PR_CANDIDATE_UNMERGED
push + refs/heads/main            => MAIN_BRANCH_PUSH
workflow_dispatch                 => MANUAL_OR_NON_MAIN_RUN
push + non-main branch            => MANUAL_OR_NON_MAIN_RUN
```

## CI effect

The SARA Verified Local v1 Gate now validates the generated `release-index.json` after the hard evidence gates:

1. PRE full-bloom generation.
2. Partner-screening batch export.
3. Partner-screening manifest verification.
4. Deployment verification.
5. Destructive backup/restore.
6. Operational snapshot.
7. Observable release identity.
8. Release-index build.
9. Release-index event/ref/merge-state assertion.
10. Release-index artifact upload.

## Post-merge verification target

After this PR merges, the push-triggered run on `main` must produce a `sara-release-evidence-index` artifact whose `release-index.json` contains:

```json
{
  "workflow": {
    "event_name": "push",
    "ref": "refs/heads/main",
    "pull_request_number": null,
    "merge_state": "MAIN_BRANCH_PUSH"
  }
}
```

That confirms the merged commit itself, not only the PR-candidate merge ref, generated a release-index artifact.

## Claims boundary

This patch verifies CI evidence custody and event/ref labeling only.

It does not claim:

- BAE interest;
- partner validation;
- supplier approval;
- certification;
- CMMC, NIST SP 800-171, or DFARS conformity;
- classified access;
- DOE validation;
- field performance;
- hardware performance;
- external reproduction;
- export-control clearance;
- operational authority.

## Current maturity label

```text
INTERNAL SOFTWARE EVIDENCE / PR-CANDIDATE AND POST-MERGE CI INDEXING / REQUIRES EXTERNAL VALIDATION
```
