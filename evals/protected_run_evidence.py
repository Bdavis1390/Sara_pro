#!/usr/bin/env python3
"""Create tamper-evident commitments and result seals for protected evaluations.

The pre-run commitment binds a protected suite manifest, evaluator-controlled artifact
hash, grader hash, model/service identities, runtime version, and execution settings
before a protected run starts. The post-run seal then binds the independently
adjudicated results to that exact commitment.

This module provides integrity evidence only. It does not reveal holdout content,
execute models, change deployment authority, or establish AGI.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping, Sequence


SCHEMA_COMMITMENT = "WS-PROTECTED-RUN-COMMITMENT-V1.0"
SCHEMA_RESULT_SEAL = "WS-PROTECTED-RUN-RESULT-SEAL-V1.0"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _required(record: Mapping[str, Any], fields: Sequence[str], *, context: str) -> None:
    missing = [name for name in fields if record.get(name) in (None, "")]
    if missing:
        raise ValueError(f"{context} missing required fields: {', '.join(missing)}")


def build_run_commitment(
    manifest: Mapping[str, Any],
    *,
    run_id: str,
    system_id: str,
    system_version: str,
    planner_identity: str,
    verifier_identity: str,
    final_state_evaluator_identity: str,
    runtime_version: str,
    execution_settings: Mapping[str, Any],
    selector_identity: str | None = None,
) -> Dict[str, Any]:
    """Build a deterministic pre-run commitment from public/evaluator metadata."""

    _required(
        manifest,
        [
            "schema",
            "suite_id",
            "suite_version",
            "target_lane",
            "task_count",
            "task_set_hash",
            "grader_hash",
            "artifact_access",
        ],
        context="manifest",
    )
    for name, value in {
        "run_id": run_id,
        "system_id": system_id,
        "system_version": system_version,
        "planner_identity": planner_identity,
        "verifier_identity": verifier_identity,
        "final_state_evaluator_identity": final_state_evaluator_identity,
        "runtime_version": runtime_version,
    }.items():
        if not isinstance(value, str) or not value:
            raise ValueError(f"{name} must be a non-empty string")

    identities = [planner_identity, verifier_identity, final_state_evaluator_identity]
    if selector_identity:
        if not isinstance(selector_identity, str):
            raise ValueError("selector_identity must be a string when supplied")
        identities.append(selector_identity)
    if len(set(identities)) != len(identities):
        raise ValueError("planner, verifier, final evaluator, and selector identities must be distinct")

    access = manifest["artifact_access"]
    if not isinstance(access, Mapping) or access.get("evaluator_controlled") is not True:
        raise ValueError("protected artifact must be evaluator-controlled")
    if access.get("public_repo_contains_raw_tasks") is not False:
        raise ValueError("manifest must declare raw tasks absent from the public repository")
    reference_id = access.get("reference_id")
    if not isinstance(reference_id, str) or not reference_id:
        raise ValueError("artifact_access.reference_id is required")
    if not isinstance(execution_settings, Mapping):
        raise TypeError("execution_settings must be a mapping")

    payload: Dict[str, Any] = {
        "schema": SCHEMA_COMMITMENT,
        "run_id": run_id,
        "suite": {
            "manifest_schema": manifest["schema"],
            "suite_id": manifest["suite_id"],
            "suite_version": manifest["suite_version"],
            "target_lane": manifest["target_lane"],
            "task_count": int(manifest["task_count"]),
            "task_set_hash": manifest["task_set_hash"],
            "grader_hash": manifest["grader_hash"],
            "artifact_reference_id": reference_id,
        },
        "system": {
            "system_id": system_id,
            "system_version": system_version,
        },
        "identities": {
            "planner": planner_identity,
            "verifier": verifier_identity,
            "final_state_evaluator": final_state_evaluator_identity,
            "selector": selector_identity,
        },
        "runtime_version": runtime_version,
        "execution_settings": dict(execution_settings),
    }
    payload["commitment_sha256"] = _sha256(payload)
    return payload


def verify_run_commitment(commitment: Mapping[str, Any], manifest: Mapping[str, Any]) -> bool:
    """Verify commitment integrity and its binding to a protected suite manifest."""

    if commitment.get("schema") != SCHEMA_COMMITMENT:
        return False
    expected = commitment.get("commitment_sha256")
    if not isinstance(expected, str):
        return False
    unsigned = dict(commitment)
    unsigned.pop("commitment_sha256", None)
    if _sha256(unsigned) != expected:
        return False

    suite = commitment.get("suite")
    if not isinstance(suite, Mapping):
        return False
    access = manifest.get("artifact_access")
    if not isinstance(access, Mapping):
        return False
    bindings = {
        "manifest_schema": manifest.get("schema"),
        "suite_id": manifest.get("suite_id"),
        "suite_version": manifest.get("suite_version"),
        "target_lane": manifest.get("target_lane"),
        "task_count": int(manifest.get("task_count", -1)),
        "task_set_hash": manifest.get("task_set_hash"),
        "grader_hash": manifest.get("grader_hash"),
        "artifact_reference_id": access.get("reference_id"),
    }
    return all(suite.get(name) == value for name, value in bindings.items())


def seal_run_results(
    commitment: Mapping[str, Any],
    results: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Bind independently adjudicated results to one verified pre-run commitment."""

    if commitment.get("schema") != SCHEMA_COMMITMENT:
        raise ValueError("unsupported commitment schema")
    commitment_hash = commitment.get("commitment_sha256")
    if not isinstance(commitment_hash, str):
        raise ValueError("commitment_sha256 is required")
    unsigned = dict(commitment)
    unsigned.pop("commitment_sha256", None)
    if _sha256(unsigned) != commitment_hash:
        raise ValueError("commitment hash verification failed")
    if not isinstance(results, Sequence) or isinstance(results, (str, bytes)) or not results:
        raise ValueError("results must be a non-empty sequence")

    trial_ids = []
    normalized = []
    for index, result in enumerate(results):
        if not isinstance(result, Mapping):
            raise ValueError(f"result {index} must be an object")
        trial_id = result.get("trial_id")
        if not isinstance(trial_id, str) or not trial_id:
            raise ValueError(f"result {index} requires trial_id")
        if trial_id in trial_ids:
            raise ValueError(f"duplicate trial_id in results: {trial_id}")
        trial_ids.append(trial_id)
        normalized.append(dict(result))

    expected_count = commitment.get("suite", {}).get("task_count")
    if expected_count != len(normalized):
        raise ValueError("result count does not match committed task count")

    payload: Dict[str, Any] = {
        "schema": SCHEMA_RESULT_SEAL,
        "run_id": commitment.get("run_id"),
        "commitment_sha256": commitment_hash,
        "result_count": len(normalized),
        "trial_ids": sorted(trial_ids),
        "results_sha256": _sha256(normalized),
    }
    payload["result_seal_sha256"] = _sha256(payload)
    return payload


def verify_result_seal(
    seal: Mapping[str, Any],
    commitment: Mapping[str, Any],
    results: Sequence[Mapping[str, Any]],
) -> bool:
    if seal.get("schema") != SCHEMA_RESULT_SEAL:
        return False
    expected = seal.get("result_seal_sha256")
    if not isinstance(expected, str):
        return False
    unsigned = dict(seal)
    unsigned.pop("result_seal_sha256", None)
    if _sha256(unsigned) != expected:
        return False
    if seal.get("commitment_sha256") != commitment.get("commitment_sha256"):
        return False
    if seal.get("run_id") != commitment.get("run_id"):
        return False
    try:
        recomputed = seal_run_results(commitment, results)
    except (TypeError, ValueError):
        return False
    return recomputed == dict(seal)
