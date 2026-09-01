#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import re

REQUIRED = {
    "SARA Verified Local v1 Gate": "sara-release-evidence-index",
    "SARA Rollback Drill": "sara-rollback-drill-evidence",
    "SARA Replacement Environment Restore": "sara-replacement-environment-restore-evidence",
    "SARA TLS Private Backend Architecture": "sara-tls-private-backend-architecture-evidence",
    "SARA Operational Resilience Drill": "sara-operational-resilience-evidence",
}

REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def positive_int(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise SystemExit(f"CLOSURE_MANIFEST_INVALID_{label}")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"CLOSURE_MANIFEST_INVALID_{label}") from exc
    if number <= 0:
        raise SystemExit(f"CLOSURE_MANIFEST_INVALID_{label}")
    return number


def main() -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    sha = os.environ["TARGET_SHA"].lower()
    if not REPO_RE.fullmatch(repo):
        raise SystemExit("CLOSURE_MANIFEST_INVALID_REPOSITORY")
    if not SHA_RE.fullmatch(sha):
        raise SystemExit("CLOSURE_MANIFEST_INVALID_SHA")

    snapshot_path = pathlib.Path(os.environ["CLOSURE_SNAPSHOT_FILE"])
    out_dir = pathlib.Path(os.environ.get("CLOSURE_MANIFEST_DIR", "closure_manifest"))
    out_dir.mkdir(parents=True, exist_ok=True)

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if snapshot.get("schema") != "WS-SARA-CLOSURE-SNAPSHOT-V1":
        raise SystemExit("CLOSURE_MANIFEST_INVALID_SNAPSHOT_SCHEMA")
    if snapshot.get("repository") != repo or snapshot.get("target_commit_sha") != sha:
        raise SystemExit("CLOSURE_MANIFEST_SNAPSHOT_IDENTITY_MISMATCH")
    supplied = snapshot.get("entries")
    if not isinstance(supplied, list):
        raise SystemExit("CLOSURE_MANIFEST_INVALID_SNAPSHOT_ENTRIES")

    by_workflow: dict[str, dict] = {}
    for item in supplied:
        if not isinstance(item, dict):
            raise SystemExit("CLOSURE_MANIFEST_INVALID_SNAPSHOT_ENTRY")
        name = item.get("workflow_name")
        if name not in REQUIRED or name in by_workflow:
            raise SystemExit("CLOSURE_MANIFEST_UNEXPECTED_OR_DUPLICATE_WORKFLOW")
        by_workflow[name] = item

    entries = []
    for workflow_name, artifact_name in REQUIRED.items():
        item = by_workflow.get(workflow_name)
        if item is None:
            raise SystemExit(f"CLOSURE_MANIFEST_MISSING_WORKFLOW:{workflow_name}")
        run = item.get("run")
        artifact = item.get("artifact")
        if not isinstance(run, dict) or not isinstance(artifact, dict):
            raise SystemExit(f"CLOSURE_MANIFEST_INVALID_ENTRY:{workflow_name}")
        run_id = positive_int(run.get("id"), "RUN_ID")
        artifact_id = positive_int(artifact.get("id"), "ARTIFACT_ID")
        digest = artifact.get("digest")
        if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
            raise SystemExit(f"CLOSURE_MANIFEST_INVALID_DIGEST:{artifact_name}")
        if artifact.get("name") != artifact_name:
            raise SystemExit(f"CLOSURE_MANIFEST_ARTIFACT_NAME_MISMATCH:{workflow_name}")
        entries.append({
            "workflow_name": workflow_name,
            "workflow_run_id": run_id,
            "workflow_run_attempt": run.get("run_attempt"),
            "workflow_event": run.get("event"),
            "workflow_head_branch": run.get("head_branch"),
            "workflow_head_sha": run.get("head_sha"),
            "workflow_conclusion": run.get("conclusion"),
            "workflow_html_url": run.get("html_url"),
            "artifact_name": artifact_name,
            "artifact_id": artifact_id,
            "artifact_digest": digest,
            "artifact_size_in_bytes": artifact.get("size_in_bytes"),
            "artifact_created_at": artifact.get("created_at"),
            "artifact_expires_at": artifact.get("expires_at"),
            "artifact_expired": artifact.get("expired"),
        })

    checks = {
        "all_required_workflows_successful": len(entries) == len(REQUIRED) and all(e["workflow_conclusion"] == "success" for e in entries),
        "all_evidence_bound_to_target_commit": all(e["workflow_head_sha"] == sha for e in entries),
        "all_required_artifacts_present": {e["artifact_name"] for e in entries} == set(REQUIRED.values()),
        "all_artifacts_have_sha256_digests": all(DIGEST_RE.fullmatch(e["artifact_digest"]) for e in entries),
        "all_artifacts_unexpired_at_manifest_time": all(e["artifact_expired"] is False for e in entries),
    }
    manifest = {
        "schema": "WS-SARA-COMMIT-CLOSURE-EVIDENCE-MANIFEST-V1",
        "result": "PASS" if all(checks.values()) else "FAIL",
        "evidence_status": "GITHUB_HOSTED_COMMIT_BOUND_EVIDENCE_INVENTORY",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repository": repo,
        "target_commit_sha": sha,
        "required_evidence_classes": list(REQUIRED.values()),
        "entries": entries,
        "checks": checks,
        "claims_boundary": (
            "This manifest binds named GitHub-hosted CI evidence artifacts and their provider-reported SHA-256 digests to one exact commit, "
            "after successful execution of the required SARA, rollback, replacement-restore, TLS, and operational-resilience workflows. "
            "It does not establish independent/off-provider custody, immutable legal-record retention, customer or government acceptance, "
            "external audit, certification, ATO, or third-party reproduction."
        ),
    }
    manifest_path = out_dir / "commit-closure-evidence-manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    (out_dir / "commit-closure-evidence-manifest.sha256").write_text(
        f"{digest}  {manifest_path.name}\n", encoding="utf-8"
    )
    if manifest["result"] != "PASS":
        raise SystemExit("CLOSURE_MANIFEST_FAIL:" + json.dumps(checks, sort_keys=True))
    print("CLOSURE_MANIFEST_PASS", sha, "sha256:" + digest)


if __name__ == "__main__":
    main()
