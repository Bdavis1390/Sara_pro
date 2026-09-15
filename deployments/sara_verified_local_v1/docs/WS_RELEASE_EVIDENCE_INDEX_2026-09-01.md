# WS Release Evidence Index — 2026-09-01

## Purpose

Add a machine-readable release evidence index to the SARA Verified Local v1 Gate.

The index ties one CI run to the evidence artifacts it produced so the Worldshepherd review path has a single custody record for:

- repository;
- commit SHA;
- workflow name;
- workflow run ID;
- workflow run number;
- event name;
- ref;
- pull request number where available;
- merge-state label;
- PRE full-bloom artifact ID, URL, and SHA-256 artifact digest;
- partner-screening batch artifact ID, URL, and SHA-256 artifact digest;
- local qualification-index digest;
- local partner batch-manifest digest;
- partner package count;
- partner presets;
- partner lanes;
- release-index digest.

## New command

```bash
ws-release-index \
  --out release_index_ci/release-index.json \
  --pre-dir qualification_evidence_ci \
  --partner-dir partner_screening_ci \
  --sbom-dir sbom_evidence_ci \
  --vulnerability-dir vulnerability_evidence_ci \
  --human-triage-dir human_triage_ci \
  --repository "$GITHUB_REPOSITORY" \
  --commit-sha "$GITHUB_SHA" \
  --workflow-name "$GITHUB_WORKFLOW" \
  --workflow-run-id "$GITHUB_RUN_ID" \
  --workflow-run-number "$GITHUB_RUN_NUMBER" \
  --event-name "$GITHUB_EVENT_NAME" \
  --ref "$GITHUB_REF" \
  --pr-number "$PR_NUMBER" \
  --merge-state "$MERGE_STATE" \
  --pre-artifact-id "$PRE_ARTIFACT_ID" \
  --pre-artifact-digest "$PRE_ARTIFACT_DIGEST" \
  --pre-artifact-url "$PRE_ARTIFACT_URL" \
  --partner-artifact-id "$PARTNER_ARTIFACT_ID" \
  --partner-artifact-digest "$PARTNER_ARTIFACT_DIGEST" \
  --partner-artifact-url "$PARTNER_ARTIFACT_URL" \
  --sbom-artifact-id "$SBOM_ARTIFACT_ID" \
  --sbom-artifact-digest "$SBOM_ARTIFACT_DIGEST" \
  --sbom-artifact-url "$SBOM_ARTIFACT_URL" \
  --vulnerability-artifact-id "$VULNERABILITY_ARTIFACT_ID" \
  --vulnerability-artifact-digest "$VULNERABILITY_ARTIFACT_DIGEST" \
  --vulnerability-artifact-url "$VULNERABILITY_ARTIFACT_URL" \
  --human-triage-artifact-id "$HUMAN_TRIAGE_ARTIFACT_ID" \
  --human-triage-artifact-digest "$HUMAN_TRIAGE_ARTIFACT_DIGEST" \
  --human-triage-artifact-url "$HUMAN_TRIAGE_ARTIFACT_URL"
```

## CI artifact

The workflow now uploads:

```text
sara-release-evidence-index
```

The artifact contains:

```text
release-index.json
```

## Schema

```text
WS-SARA-RELEASE-EVIDENCE-INDEX-V1
```

Core fields:

```json
{
  "schema": "WS-SARA-RELEASE-EVIDENCE-INDEX-V1",
  "repository": "Bdavis1390/Sara_pro",
  "commit_sha": "<GITHUB_SHA>",
  "workflow": {
    "name": "SARA Verified Local v1 Gate",
    "run_id": "<GITHUB_RUN_ID>",
    "run_number": "<GITHUB_RUN_NUMBER>",
    "event_name": "pull_request|push|workflow_dispatch",
    "ref": "<GITHUB_REF>",
    "pull_request_number": "<PR number or null>",
    "merge_state": "PR_CANDIDATE_UNMERGED|MAIN_BRANCH_PUSH|MANUAL_OR_NON_MAIN_RUN"
  },
  "artifacts": {
    "pre_full_bloom_qualification_evidence": {
      "artifact_id": "<upload-artifact id>",
      "artifact_digest": "sha256:<digest>",
      "artifact_url": "<upload-artifact url>"
    },
    "partner_screening_batch_evidence": {
      "artifact_id": "<upload-artifact id>",
      "artifact_digest": "sha256:<digest>",
      "artifact_url": "<upload-artifact url>"
    }
  },
  "local_evidence": {
    "qualification_index_sha256": "sha256:<digest>",
    "partner_batch_manifest_sha256": "sha256:<digest>",
    "partner_batch_digest": "sha256:<canonical batch digest>",
    "partner_package_count": 0,
    "partner_source_bundle_count": 0,
    "partner_presets": [],
    "partner_lanes": []
  },
  "release_index_digest": "sha256:<canonical index digest>"
}
```

## Claims boundary

This artifact records CI evidence custody only.

It does **not** establish partner interest, partner validation, BAE validation, supplier approval, certification, CMMC conformity, NIST SP 800-171 implementation, DFARS satisfaction, classified access, DOE validation, external reproduction, field performance, hardware performance, export-control clearance, or operational authority.

## Worldshepherd readiness effect

This closes the release-index gap between generated evidence artifacts and review/disclosure discipline.

The resulting path becomes:

```text
PRE full-bloom evidence
→ partner-screening batch evidence
→ manifest/file verification
→ downloaded-artifact verification
→ release evidence index
→ reviewer can map run ⇄ commit ⇄ artifacts ⇄ digests ⇄ PR state
```

Current maturity remains:

```text
INTERNAL SOFTWARE EVIDENCE / CI-GENERATED RELEASE INDEX / REQUIRES EXTERNAL VALIDATION
```
