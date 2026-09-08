from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_RESULT_VALUES = {
    "ACTUAL_HOST_PVK_SHADOW_ACCEPTANCE": "PASS",
    "relay_admin_boundary": "PASS",
    "pvk_record_append": "PASS",
    "pvk_claims_linter": "PASS",
    "pvk_restart_persistence": "PASS",
    "pvk_audit_presence": "PASS",
    "scientific_validation_claim": "NOT_ESTABLISHED_BY_THIS_TEST",
}

REQUIRED_FILES = {
    "baseline.txt",
    "authorization.txt",
    "physics-status.initial.json",
    "record-append.json",
    "lint-response.json",
    "physics-records.after-restart.json",
    "audit.after-restart.PRIVATE.json",
    "compose.ps.txt",
    "SHA256SUMS",
    "RESULT.txt",
}

REQUIRED_AUDIT_EVENTS = {
    "physics_record_appended",
    "physics_claim_linted",
    "service_started",
}

REQUIRED_BASELINE_FIELDS = {
    "hostname",
    "kernel",
    "git_branch",
    "git_head",
    "docker_version",
    "compose_version",
    "shadow_project",
    "shadow_base_url",
}


@dataclass(frozen=True)
class HostEvidenceAssessment:
    accepted: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    branch: str | None
    commit: str | None
    evidence_manifest_digest: str | None
    record_id: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "branch": self.branch,
            "commit": self.commit,
            "evidence_manifest_digest": self.evidence_manifest_digest,
            "record_id": self.record_id,
            "scientific_validation_claim": "NOT_ESTABLISHED_BY_HOST_ACCEPTANCE",
        }


def _parse_key_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.lstrip().startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_sha256_manifest(root: Path) -> tuple[list[str], str | None]:
    blockers: list[str] = []
    manifest = root / "SHA256SUMS"
    if not manifest.is_file():
        return ["MISSING_SHA256SUMS"], None

    manifest_bytes = manifest.read_bytes()
    manifest_digest = "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
    seen: set[str] = set()
    for line_number, raw in enumerate(manifest_bytes.decode("utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        parts = raw.split(maxsplit=1)
        if len(parts) != 2:
            blockers.append(f"MALFORMED_SHA256_LINE:{line_number}")
            continue
        expected, filename = parts
        filename = filename.lstrip("* ").removeprefix("./")
        rel = Path(filename)
        if rel.is_absolute() or ".." in rel.parts or len(rel.parts) != 1:
            blockers.append(f"UNSAFE_SHA256_PATH:{filename}")
            continue
        if filename == "SHA256SUMS":
            blockers.append("SHA256SUMS_SELF_REFERENCE")
            continue
        if filename in seen:
            blockers.append(f"DUPLICATE_SHA256_ENTRY:{filename}")
            continue
        seen.add(filename)
        target = root / filename
        if not target.is_file():
            blockers.append(f"HASHED_FILE_MISSING:{filename}")
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual.lower() != expected.lower():
            blockers.append(f"SHA256_MISMATCH:{filename}")

    for filename in REQUIRED_FILES - {"SHA256SUMS"}:
        if filename not in seen:
            blockers.append(f"REQUIRED_FILE_NOT_HASHED:{filename}")
    return blockers, manifest_digest


def assess_actual_host_evidence(
    evidence_dir: str | Path,
    *,
    expected_branch: str | None = None,
    expected_commit: str | None = None,
) -> HostEvidenceAssessment:
    root = Path(evidence_dir).resolve()
    blockers: list[str] = []
    warnings: list[str] = []

    if not root.is_dir():
        return HostEvidenceAssessment(
            accepted=False,
            blockers=("EVIDENCE_DIRECTORY_MISSING",),
            warnings=(),
            branch=None,
            commit=None,
            evidence_manifest_digest=None,
            record_id=None,
        )

    missing = sorted(name for name in REQUIRED_FILES if not (root / name).is_file())
    blockers.extend(f"MISSING_FILE:{name}" for name in missing)

    hash_blockers, manifest_digest = _verify_sha256_manifest(root)
    blockers.extend(hash_blockers)

    branch: str | None = None
    commit: str | None = None
    record_id: str | None = None
    shadow_port: int | None = None

    try:
        result = _parse_key_values(root / "RESULT.txt")
        for key, expected in REQUIRED_RESULT_VALUES.items():
            if result.get(key) != expected:
                blockers.append(f"RESULT_GATE_FAILED:{key}")
        branch = result.get("branch")
        commit = result.get("commit")
        try:
            shadow_port = int(result.get("shadow_port", ""))
        except ValueError:
            blockers.append("SHADOW_PORT_INVALID")
        else:
            if shadow_port < 1024 or shadow_port > 65535:
                blockers.append("SHADOW_PORT_INVALID")
    except (OSError, UnicodeError):
        blockers.append("RESULT_UNREADABLE")
        result = {}

    try:
        baseline = _parse_key_values(root / "baseline.txt")
        if baseline.get("schema") != "WS-ACTUAL-HOST-PVK-ACCEPTANCE-V1":
            blockers.append("BASELINE_SCHEMA_MISMATCH")
        for field in sorted(REQUIRED_BASELINE_FIELDS):
            if not baseline.get(field):
                blockers.append(f"BASELINE_FIELD_MISSING:{field}")
        if branch and baseline.get("git_branch") != branch:
            blockers.append("BRANCH_EVIDENCE_MISMATCH")
        if commit and baseline.get("git_head") != commit:
            blockers.append("COMMIT_EVIDENCE_MISMATCH")
        if shadow_port is not None:
            expected_url = f"http://127.0.0.1:{shadow_port}"
            if baseline.get("shadow_base_url") != expected_url:
                blockers.append("SHADOW_BASE_URL_NOT_LOOPBACK")
    except (OSError, UnicodeError):
        blockers.append("BASELINE_UNREADABLE")
        baseline = {}

    if expected_branch is not None and branch != expected_branch:
        blockers.append("UNEXPECTED_BRANCH")
    if expected_commit is not None and commit != expected_commit:
        blockers.append("UNEXPECTED_COMMIT")

    try:
        compose_ps = (root / "compose.ps.txt").read_text(encoding="utf-8")
        if shadow_port is not None:
            expected_mapping = f"127.0.0.1:{shadow_port}->9530/tcp"
            if expected_mapping not in compose_ps:
                blockers.append("SHADOW_LOOPBACK_BINDING_NOT_PROVEN")
            wildcard_markers = (
                f"0.0.0.0:{shadow_port}",
                f":::{shadow_port}",
                f"[::]:{shadow_port}",
            )
            if any(marker in compose_ps for marker in wildcard_markers):
                blockers.append("SHADOW_WILDCARD_BINDING_DETECTED")
    except (OSError, UnicodeError):
        blockers.append("COMPOSE_PS_UNREADABLE")

    try:
        authorization = _parse_key_values(root / "authorization.txt")
        if authorization.get("relay_pvk_status_http") != "403":
            blockers.append("RELAY_ADMIN_BOUNDARY_NOT_403")
    except (OSError, UnicodeError):
        blockers.append("AUTHORIZATION_EVIDENCE_UNREADABLE")

    try:
        appended = _load_json(root / "record-append.json")
        if appended.get("accepted") is not True:
            blockers.append("PVK_RECORD_NOT_ACCEPTED")
        record = appended.get("record") or {}
        record_id = record.get("record_id")
        if not record_id or not str(record_id).startswith("PHYS-HOST-"):
            blockers.append("HOST_RECORD_ID_INVALID")
        if record.get("validation_state") != "concept":
            blockers.append("HOST_PROBE_WRONG_MATURITY")
        if record.get("claim_label") != "IMPLEMENTED IN SOFTWARE":
            blockers.append("HOST_PROBE_WRONG_CLAIM_LABEL")
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        blockers.append("RECORD_APPEND_EVIDENCE_UNREADABLE")

    try:
        lint = _load_json(root / "lint-response.json")
        if lint.get("blocked") is not True:
            blockers.append("CLAIMS_LINTER_DID_NOT_BLOCK")
        findings = lint.get("findings", [])
        if not any(
            item.get("rule_id") == "PROP-01" and item.get("severity") == "BLOCK"
            for item in findings
            if isinstance(item, dict)
        ):
            blockers.append("PROP_01_BLOCK_MISSING")
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        blockers.append("LINT_EVIDENCE_UNREADABLE")

    try:
        after_restart = _load_json(root / "physics-records.after-restart.json")
        persisted_ids = {
            item.get("record_id")
            for item in after_restart.get("records", [])
            if isinstance(item, dict)
        }
        if record_id is None or record_id not in persisted_ids:
            blockers.append("HOST_RECORD_NOT_PERSISTED")
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        blockers.append("PERSISTENCE_EVIDENCE_UNREADABLE")

    try:
        audit = _load_json(root / "audit.after-restart.PRIVATE.json")
        events = {
            item.get("event")
            for item in audit.get("records", [])
            if isinstance(item, dict)
        }
        missing_events = sorted(REQUIRED_AUDIT_EVENTS - events)
        blockers.extend(f"AUDIT_EVENT_MISSING:{event}" for event in missing_events)
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        blockers.append("AUDIT_EVIDENCE_UNREADABLE")

    try:
        status = _load_json(root / "physics-status.initial.json")
        if status.get("ok") is not True:
            blockers.append("PVK_STATUS_NOT_OK")
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        blockers.append("PVK_STATUS_EVIDENCE_UNREADABLE")

    if not (root / "compose.rendered.PRIVATE.yaml").is_file():
        warnings.append("PRIVATE_RENDERED_COMPOSE_NOT_PRESENT")
    if not (root / "build.log").is_file():
        warnings.append("BUILD_LOG_NOT_PRESENT")

    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))
    return HostEvidenceAssessment(
        accepted=not blockers,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        branch=branch,
        commit=commit,
        evidence_manifest_digest=manifest_digest,
        record_id=record_id,
    )
