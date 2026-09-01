#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import time
import urllib.error
import urllib.request

REQUIRED = {
    "SARA Verified Local v1 Gate": "sara-release-evidence-index",
    "SARA Rollback Drill": "sara-rollback-drill-evidence",
    "SARA Replacement Environment Restore": "sara-replacement-environment-restore-evidence",
    "SARA TLS Private Backend Architecture": "sara-tls-private-backend-architecture-evidence",
    "SARA Operational Resilience Drill": "sara-operational-resilience-evidence",
}


def api(path: str) -> dict:
    base = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    req = urllib.request.Request(
        base + path,
        headers={
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "worldshepherd-sara-closure-manifest",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def select_successful_run(runs: list[dict], workflow_name: str, sha: str) -> dict | None:
    matches = [
        run for run in runs
        if run.get("name") == workflow_name
        and run.get("head_sha") == sha
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
    ]
    if not matches:
        return None
    return max(matches, key=lambda r: (r.get("run_attempt", 0), r.get("id", 0)))


def main() -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    sha = os.environ["TARGET_SHA"]
    out_dir = pathlib.Path(os.environ.get("CLOSURE_MANIFEST_DIR", "closure_manifest"))
    out_dir.mkdir(parents=True, exist_ok=True)

    selected: dict[str, tuple[dict, dict]] = {}
    deadline = time.monotonic() + int(os.environ.get("CLOSURE_WAIT_SECONDS", "420"))
    last_missing: list[str] = []

    while time.monotonic() < deadline:
        run_payload = api(f"/repos/{repo}/actions/runs?head_sha={sha}&per_page=100")
        runs = run_payload.get("workflow_runs", [])
        selected.clear()
        missing: list[str] = []
        for workflow_name, artifact_name in REQUIRED.items():
            run = select_successful_run(runs, workflow_name, sha)
            if run is None:
                missing.append(f"workflow:{workflow_name}")
                continue
            artifacts = api(f"/repos/{repo}/actions/runs/{run['id']}/artifacts?per_page=100").get("artifacts", [])
            candidates = [a for a in artifacts if a.get("name") == artifact_name and not a.get("expired")]
            if not candidates:
                missing.append(f"artifact:{artifact_name}")
                continue
            artifact = max(candidates, key=lambda a: a.get("id", 0))
            digest = artifact.get("digest") or ""
            if not digest.startswith("sha256:"):
                missing.append(f"artifact_digest:{artifact_name}")
                continue
            selected[workflow_name] = (run, artifact)
        if not missing:
            break
        last_missing = missing
        print("CLOSURE_MANIFEST_WAIT:", ", ".join(missing), flush=True)
        time.sleep(3)
    else:
        raise SystemExit("CLOSURE_MANIFEST_TIMEOUT: " + ", ".join(last_missing))

    entries = []
    for workflow_name, artifact_name in REQUIRED.items():
        run, artifact = selected[workflow_name]
        entries.append({
            "workflow_name": workflow_name,
            "workflow_run_id": run["id"],
            "workflow_run_attempt": run.get("run_attempt"),
            "workflow_event": run.get("event"),
            "workflow_head_branch": run.get("head_branch"),
            "workflow_head_sha": run.get("head_sha"),
            "workflow_conclusion": run.get("conclusion"),
            "workflow_html_url": run.get("html_url"),
            "artifact_name": artifact_name,
            "artifact_id": artifact["id"],
            "artifact_digest": artifact["digest"],
            "artifact_size_in_bytes": artifact.get("size_in_bytes"),
            "artifact_created_at": artifact.get("created_at"),
            "artifact_expires_at": artifact.get("expires_at"),
            "artifact_expired": artifact.get("expired"),
        })

    checks = {
        "all_required_workflows_successful": len(entries) == len(REQUIRED) and all(e["workflow_conclusion"] == "success" for e in entries),
        "all_evidence_bound_to_target_commit": all(e["workflow_head_sha"] == sha for e in entries),
        "all_required_artifacts_present": {e["artifact_name"] for e in entries} == set(REQUIRED.values()),
        "all_artifacts_have_sha256_digests": all(str(e["artifact_digest"]).startswith("sha256:") for e in entries),
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
    (out_dir / "commit-closure-evidence-manifest.sha256").write_text(f"{digest}  {manifest_path.name}\n", encoding="utf-8")
    if manifest["result"] != "PASS":
        raise SystemExit("CLOSURE_MANIFEST_FAIL: " + json.dumps(checks, sort_keys=True))
    print("CLOSURE_MANIFEST_PASS", sha, "sha256:" + digest)


if __name__ == "__main__":
    main()
