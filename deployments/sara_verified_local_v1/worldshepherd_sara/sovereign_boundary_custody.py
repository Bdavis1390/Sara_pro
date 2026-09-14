from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .qualification import canonical_digest
from .release_index_cli import (
    ALLOWED_MERGE_STATES,
    RELEASE_INDEX_SCHEMA,
)


EXECUTION_CUSTODY_SCHEMA = "WS-SBK-EXECUTION-CUSTODY-V0.1"
RELEASE_ATTESTATION_RECEIPT_SCHEMA = "WS-SARA-RELEASE-ATTESTATION-RECEIPT-V1"
_SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"
_COMMIT_PATTERN = r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$"


class ExecutionCustodyError(ValueError):
    pass


class ExecutionCustody(BaseModel):
    """Evidence identity for the software/configuration allowed to execute an effect.

    This object is intentionally evidence-oriented. It binds a governed effect
    to a SARA release-evidence index, the indexed source commit, and an exact
    configuration digest. Optional GitHub/Sigstore receipt fields preserve the
    existing release-attestation custody chain when a merged-main attestation is
    available, but their presence alone is not treated as independent signature
    verification by SBK.
    """

    model_config = ConfigDict(extra="forbid")

    schema: Literal[EXECUTION_CUSTODY_SCHEMA] = EXECUTION_CUSTODY_SCHEMA
    release_index_digest: str = Field(pattern=_SHA256_PATTERN)
    release_index_file_sha256: str = Field(pattern=_SHA256_PATTERN)
    release_commit_sha: str = Field(pattern=_COMMIT_PATTERN)
    release_merge_state: str = Field(min_length=1, max_length=64)
    release_evidence_ref: str = Field(min_length=1, max_length=1024)
    configuration_digest: str = Field(pattern=_SHA256_PATTERN)
    attestation_receipt_file_sha256: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    attestation_id: str | None = Field(default=None, min_length=1, max_length=512)
    attestation_ref: str | None = Field(default=None, min_length=1, max_length=2048)


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _load_json_bytes(value: bytes, *, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExecutionCustodyError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, dict):
        raise ExecutionCustodyError(f"{label} must contain a JSON object")
    return parsed


def _validate_release_index(index: dict[str, Any]) -> None:
    if index.get("schema") != RELEASE_INDEX_SCHEMA:
        raise ExecutionCustodyError("unexpected SARA release evidence index schema")
    supplied_digest = index.get("release_index_digest")
    if not isinstance(supplied_digest, str):
        raise ExecutionCustodyError("release evidence index is missing release_index_digest")
    without_digest = dict(index)
    without_digest.pop("release_index_digest", None)
    expected_digest = canonical_digest(without_digest)
    if supplied_digest != expected_digest:
        raise ExecutionCustodyError("release evidence index digest does not verify")

    commit_sha = index.get("commit_sha")
    if not isinstance(commit_sha, str) or not (
        len(commit_sha) in {40, 64}
        and all(ch in "0123456789abcdef" for ch in commit_sha)
    ):
        raise ExecutionCustodyError("release evidence index commit_sha is invalid")

    workflow = index.get("workflow")
    if not isinstance(workflow, dict):
        raise ExecutionCustodyError("release evidence index workflow metadata is missing")
    if workflow.get("merge_state") not in ALLOWED_MERGE_STATES:
        raise ExecutionCustodyError("release evidence index merge_state is invalid")


def _validate_attestation_receipt(
    receipt: dict[str, Any],
    *,
    release_index_file_sha256: str,
    release_commit_sha: str,
) -> None:
    if receipt.get("schema") != RELEASE_ATTESTATION_RECEIPT_SCHEMA:
        raise ExecutionCustodyError("unexpected SARA release attestation receipt schema")
    if receipt.get("triggering_commit_sha") != release_commit_sha:
        raise ExecutionCustodyError(
            "release attestation receipt commit does not match release index"
        )
    if receipt.get("release_index_file_sha256") != release_index_file_sha256:
        raise ExecutionCustodyError(
            "release attestation receipt does not bind the supplied release-index file"
        )
    if not receipt.get("attestation_id"):
        raise ExecutionCustodyError("release attestation receipt is missing attestation_id")
    if not receipt.get("attestation_url"):
        raise ExecutionCustodyError("release attestation receipt is missing attestation_url")


def build_execution_custody(
    *,
    release_index_bytes: bytes,
    runtime_configuration: dict[str, Any],
    release_evidence_ref: str,
    attestation_receipt_bytes: bytes | None = None,
) -> ExecutionCustody:
    """Build exact software/configuration custody from existing SARA release evidence.

    The release-index canonical digest is reverified. The exact release-index
    file bytes are independently SHA-256 hashed because the existing GitHub
    attestation receipt binds the file hash rather than the canonical JSON
    digest. Runtime configuration is canonicalized using the repository's
    existing ``canonical_digest`` helper.

    If an attestation receipt is supplied, this function verifies its schema and
    binding to the same commit and exact release-index file. It does not verify
    the external Sigstore bundle or GitHub OIDC signature; that remains release
    attestation infrastructure evidence, not a claim made by this local parser.
    """

    if not isinstance(runtime_configuration, dict):
        raise ExecutionCustodyError("runtime_configuration must be a JSON object")
    if not release_evidence_ref:
        raise ExecutionCustodyError("release_evidence_ref must be non-empty")

    index = _load_json_bytes(release_index_bytes, label="release evidence index")
    _validate_release_index(index)
    release_index_file_sha256 = _sha256_bytes(release_index_bytes)
    workflow = index["workflow"]

    attestation_receipt_file_sha256 = None
    attestation_id = None
    attestation_ref = None
    if attestation_receipt_bytes is not None:
        receipt = _load_json_bytes(
            attestation_receipt_bytes, label="release attestation receipt"
        )
        _validate_attestation_receipt(
            receipt,
            release_index_file_sha256=release_index_file_sha256,
            release_commit_sha=index["commit_sha"],
        )
        attestation_receipt_file_sha256 = _sha256_bytes(attestation_receipt_bytes)
        attestation_id = str(receipt["attestation_id"])
        attestation_ref = str(receipt["attestation_url"])

    return ExecutionCustody(
        release_index_digest=index["release_index_digest"],
        release_index_file_sha256=release_index_file_sha256,
        release_commit_sha=index["commit_sha"],
        release_merge_state=str(workflow["merge_state"]),
        release_evidence_ref=release_evidence_ref,
        configuration_digest=canonical_digest(runtime_configuration),
        attestation_receipt_file_sha256=attestation_receipt_file_sha256,
        attestation_id=attestation_id,
        attestation_ref=attestation_ref,
    )


def build_execution_custody_from_files(
    *,
    release_index_path: str | Path,
    runtime_configuration: dict[str, Any],
    release_evidence_ref: str | None = None,
    attestation_receipt_path: str | Path | None = None,
) -> ExecutionCustody:
    release_path = Path(release_index_path)
    if not release_path.is_file():
        raise ExecutionCustodyError("release evidence index file does not exist")
    receipt_bytes = None
    if attestation_receipt_path is not None:
        receipt_path = Path(attestation_receipt_path)
        if not receipt_path.is_file():
            raise ExecutionCustodyError("release attestation receipt file does not exist")
        receipt_bytes = receipt_path.read_bytes()
    return build_execution_custody(
        release_index_bytes=release_path.read_bytes(),
        runtime_configuration=runtime_configuration,
        release_evidence_ref=release_evidence_ref or str(release_path),
        attestation_receipt_bytes=receipt_bytes,
    )


def execution_custody_matches(
    expected: ExecutionCustody,
    observed: ExecutionCustody,
) -> bool:
    """Constant-shape semantic equality used by authority/PEP binding checks."""

    return expected.model_dump(mode="json") == observed.model_dump(mode="json")
