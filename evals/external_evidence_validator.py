#!/usr/bin/env python3
"""Validate metadata-only external evidence packages for the Worldshepherd AGI gate.

The validator checks provenance, evaluator-role separation, complete-run attestation,
control assertions, sample metadata, and replication classification without requiring
raw holdout tasks, answer keys, hidden grader targets, credentials, or private
reasoning in the public repository.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence


SCHEMA = "WS-EXTERNAL-EVIDENCE-PACKAGE-V1.0"
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ALLOWED_LEVELS = {"candidate", "verified"}
ALLOWED_REPLICATION = {"DISTINCT", "PARTIALLY_SHARED", "NOT_INDEPENDENT", "UNRESOLVED"}
FORBIDDEN_KEYS = {
    "tasks",
    "raw_tasks",
    "task_content",
    "answer_key",
    "answers",
    "hidden_answers",
    "grader_targets",
    "solutions",
    "credentials",
    "api_key",
    "bearer_token",
    "private_chain_of_thought",
}


def _load(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("external evidence package must be a JSON object")
    return data


def _required(record: Mapping[str, Any], fields: Iterable[str], *, context: str) -> None:
    missing = [field for field in fields if record.get(field) in (None, "")]
    if missing:
        raise ValueError(f"{context} missing required fields: {', '.join(missing)}")


def _scan_forbidden(value: Any, path: str = "$") -> Sequence[str]:
    findings = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_KEYS:
                findings.append(f"{path}.{key}")
            findings.extend(_scan_forbidden(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_scan_forbidden(child, f"{path}[{index}]"))
    return findings


def _require_hash(value: Any, field: str) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ValueError(f"{field} must be canonical sha256:<64 hex>")


def validate_package(package: Dict[str, Any]) -> Dict[str, Any]:
    forbidden = list(_scan_forbidden(package))
    if forbidden:
        raise ValueError("protected or secret content must not be embedded: " + ", ".join(forbidden))

    _required(
        package,
        [
            "schema",
            "package_id",
            "evaluator_identity",
            "evaluator_organization",
            "system_id",
            "system_version",
            "target_lane",
            "target_level",
            "public_manifest_hash",
            "pre_run_commitment_hash",
            "result_seal_hash",
            "evidence_reference",
            "role_identities",
            "controls",
            "metrics",
            "sample_counts",
            "attestation",
        ],
        context="package",
    )
    if package["schema"] != SCHEMA:
        raise ValueError("unsupported external evidence package schema")
    if package["target_level"] not in ALLOWED_LEVELS:
        raise ValueError("target_level must be candidate or verified")

    for field in ("public_manifest_hash", "pre_run_commitment_hash", "result_seal_hash"):
        _require_hash(package[field], field)

    evidence_reference = package["evidence_reference"]
    if not isinstance(evidence_reference, Mapping):
        raise ValueError("evidence_reference must be an object")
    _required(evidence_reference, ["reference_id", "controlled_access"], context="evidence_reference")
    if evidence_reference.get("controlled_access") is not True:
        raise ValueError("evidence_reference.controlled_access must be true")

    roles = package["role_identities"]
    if not isinstance(roles, Mapping):
        raise ValueError("role_identities must be an object")
    _required(roles, ["planner", "verifier", "final_state_evaluator"], context="role_identities")
    identities = [roles["planner"], roles["verifier"], roles["final_state_evaluator"]]
    selector = roles.get("selector")
    if selector not in (None, ""):
        identities.append(selector)
    if not all(isinstance(identity, str) and identity for identity in identities):
        raise ValueError("all supplied role identities must be non-empty strings")
    if len(set(identities)) != len(identities):
        raise ValueError("planner, verifier, final evaluator, and selector identities must be distinct")

    controls = package["controls"]
    if not isinstance(controls, Mapping):
        raise ValueError("controls must be an object")
    required_controls = {
        "complete_run": True,
        "failed_trials_retained": True,
        "independent_final_adjudication": True,
        "protected_artifacts_external": True,
        "contamination_review_completed": True,
        "task_set_frozen_before_run": True,
        "grader_frozen_before_run": True,
    }
    control_errors = [
        f"{name} must equal {expected!r}"
        for name, expected in required_controls.items()
        if controls.get(name) != expected
    ]

    metrics = package["metrics"]
    if not isinstance(metrics, Mapping) or not metrics:
        raise ValueError("metrics must be a non-empty object")
    sample_counts = package["sample_counts"]
    if not isinstance(sample_counts, Mapping) or not sample_counts:
        raise ValueError("sample_counts must be a non-empty object")
    sample_errors = []
    for name, value in sample_counts.items():
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            sample_errors.append(f"sample_counts.{name} must be a positive integer")

    attestation = package["attestation"]
    if not isinstance(attestation, Mapping):
        raise ValueError("attestation must be an object")
    _required(attestation, ["signer", "role", "statement", "attested_complete_run"], context="attestation")
    attestation_errors = []
    if attestation.get("attested_complete_run") is not True:
        attestation_errors.append("attestation.attested_complete_run must be true")
    if not all(isinstance(attestation.get(name), str) and attestation.get(name) for name in ("signer", "role", "statement")):
        attestation_errors.append("attestation signer, role, and statement must be non-empty strings")

    replication = package.get("replication")
    replication_errors = []
    replication_classification = None
    if replication is not None:
        if not isinstance(replication, Mapping):
            raise ValueError("replication must be an object when supplied")
        replication_classification = replication.get("classification")
        if replication_classification not in ALLOWED_REPLICATION:
            replication_errors.append("replication.classification is unsupported")
        if not isinstance(replication.get("dependency_disclosure"), str) or not replication.get("dependency_disclosure"):
            replication_errors.append("replication.dependency_disclosure is required")
        if replication_classification == "DISTINCT" and replication.get("unresolved_material_contradiction") is True:
            replication_errors.append("DISTINCT replication cannot carry an unresolved material contradiction")

    errors = control_errors + sample_errors + attestation_errors + replication_errors
    return {
        "schema": "WS-EXTERNAL-EVIDENCE-VALIDATION-V1.0",
        "valid": not errors,
        "errors": errors,
        "package_id": package["package_id"],
        "evaluator_identity": package["evaluator_identity"],
        "evaluator_organization": package["evaluator_organization"],
        "system_id": package["system_id"],
        "system_version": package["system_version"],
        "target_lane": package["target_lane"],
        "target_level": package["target_level"],
        "replication_classification": replication_classification,
        "metric_names": sorted(str(name) for name in metrics),
        "sample_count_names": sorted(str(name) for name in sample_counts),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Worldshepherd external AGI evidence package metadata")
    parser.add_argument("package", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        result = validate_package(_load(args.package))
        print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=args.pretty))
        return 0 if result["valid"] else 1
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"External evidence validator error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
