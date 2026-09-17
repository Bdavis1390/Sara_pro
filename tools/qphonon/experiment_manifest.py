#!/usr/bin/env python3
"""Immutable pre-run manifest helpers for WS-QPHONON.

The manifest binds the exact configuration, parameter snapshot, acceptance
criteria, model version, and claims state before an experiment can advance.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any
import uuid

from security_controls import sha256_json

MANIFEST_SCHEMA = "WS-QPHONON-EXPERIMENT-MANIFEST-V0.2"
ALLOWED_CLAIMS_STATES = {
    "PROVEN_INTERNALLY",
    "IMPLEMENTED_IN_SOFTWARE",
    "SUPPORTED_BY_LITERATURE",
    "SIMULATED_ONLY",
    "HYPOTHESIS",
    "SPECULATIVE_EXTENSION",
    "REQUIRES_LAB_VALIDATION",
    "REQUIRES_PARTNER_VALIDATION",
    "REQUIRES_LEGAL_REVIEW",
    "NOT_CURRENTLY_CLAIMED",
}


@dataclass(frozen=True)
class ExperimentManifest:
    schema: str
    experiment_id: str
    created_at_utc: str
    model_version: str
    claims_state: str
    config_digest: str
    parameter_snapshot_digest: str
    acceptance_criteria_digest: str
    manifest_digest: str
    frozen: bool


def _canonical_uuid4(value: str) -> bool:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        return False
    return parsed.version == 4 and str(parsed) == value


def _valid_utc_z(value: str) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0


def freeze_manifest(
    *,
    experiment_id: str,
    created_at_utc: str,
    model_version: str,
    claims_state: str,
    config: dict[str, Any],
    parameter_snapshot: dict[str, Any],
    acceptance_criteria: dict[str, Any],
) -> ExperimentManifest:
    if not _canonical_uuid4(experiment_id):
        raise ValueError("experiment_id must be a canonical UUIDv4")
    if not _valid_utc_z(created_at_utc):
        raise ValueError("created_at_utc must be a parseable UTC timestamp ending in Z")
    if not isinstance(model_version, str) or not model_version.strip():
        raise ValueError("model_version is required")
    if claims_state not in ALLOWED_CLAIMS_STATES:
        raise ValueError("claims_state is not recognized")

    config_digest = sha256_json(config)
    parameter_digest = sha256_json(parameter_snapshot)
    acceptance_digest = sha256_json(acceptance_criteria)

    material = {
        "schema": MANIFEST_SCHEMA,
        "experiment_id": experiment_id,
        "created_at_utc": created_at_utc,
        "model_version": model_version,
        "claims_state": claims_state,
        "config_digest": config_digest,
        "parameter_snapshot_digest": parameter_digest,
        "acceptance_criteria_digest": acceptance_digest,
        "frozen": True,
    }
    return ExperimentManifest(
        **material,
        manifest_digest=sha256_json(material),
    )


def verify_manifest(
    manifest: ExperimentManifest,
    *,
    config: dict[str, Any],
    parameter_snapshot: dict[str, Any],
    acceptance_criteria: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if manifest.schema != MANIFEST_SCHEMA:
        errors.append("MANIFEST_SCHEMA_MISMATCH")
    if manifest.frozen is not True:
        errors.append("MANIFEST_NOT_FROZEN")
    if manifest.claims_state not in ALLOWED_CLAIMS_STATES:
        errors.append("CLAIMS_STATE_INVALID")
    if not _valid_utc_z(manifest.created_at_utc):
        errors.append("MANIFEST_TIME_INVALID")
    if manifest.config_digest != sha256_json(config):
        errors.append("CONFIG_DIGEST_MISMATCH")
    if manifest.parameter_snapshot_digest != sha256_json(parameter_snapshot):
        errors.append("PARAMETER_SNAPSHOT_DIGEST_MISMATCH")
    if manifest.acceptance_criteria_digest != sha256_json(acceptance_criteria):
        errors.append("ACCEPTANCE_CRITERIA_DIGEST_MISMATCH")

    material = asdict(manifest)
    material.pop("manifest_digest", None)
    if manifest.manifest_digest != sha256_json(material):
        errors.append("MANIFEST_DIGEST_MISMATCH")
    return errors
