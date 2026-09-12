from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .independent_review_export import (
    IndependentReviewExportBundle,
    IndependentReviewExportError,
    verify_independent_review_export_bundle,
)


INDEPENDENT_REVIEW_VERIFICATION_RESULT_SCHEMA = (
    "WS-INDEPENDENT-REVIEW-VERIFICATION-RESULT-V1"
)
MAX_SERIALIZED_REVIEW_BUNDLE_BYTES = 8 * 1024 * 1024
_MAX_DETAIL_CHARS = 1600


class _DuplicateJsonKeyError(ValueError):
    def __init__(self, key: str) -> None:
        super().__init__(f"duplicate JSON object key: {key}")
        self.key = key


class IndependentReviewVerificationResult(BaseModel):
    """Evidence-only PASS/FAIL result for a serialized reviewer bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema: Literal["WS-INDEPENDENT-REVIEW-VERIFICATION-RESULT-V1"] = (
        INDEPENDENT_REVIEW_VERIFICATION_RESULT_SCHEMA
    )
    status: Literal["PASS", "FAIL"]
    code: Literal[
        "VERIFIED",
        "UNSUPPORTED_INPUT_TYPE",
        "INPUT_TOO_LARGE",
        "INVALID_UTF8",
        "INVALID_JSON",
        "DUPLICATE_JSON_KEY",
        "TOP_LEVEL_NOT_OBJECT",
        "SCHEMA_VALIDATION_FAILED",
        "EVIDENCE_VERIFICATION_FAILED",
    ]
    detail: str = Field(min_length=1, max_length=_MAX_DETAIL_CHARS)
    bundle_digest_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    verification_scope: Literal["LOCAL_EVIDENCE_REPRODUCTION_ONLY"] = (
        "LOCAL_EVIDENCE_REPRODUCTION_ONLY"
    )
    monitor_verification_status: Literal["UNVERIFIED"] = "UNVERIFIED"
    approval_status: Literal["NOT_APPROVED_BY_THIS_RESULT"] = (
        "NOT_APPROVED_BY_THIS_RESULT"
    )
    authorization_effect: Literal["NONE"] = "NONE"
    readiness_effect: Literal["NONE"] = "NONE"
    execution_effect_applied: Literal[False] = False


def _result(
    *,
    status: Literal["PASS", "FAIL"],
    code: str,
    detail: str,
    bundle_digest_sha256: str | None = None,
) -> IndependentReviewVerificationResult:
    normalized_detail = detail.strip() or "verification failed without detail"
    if len(normalized_detail) > _MAX_DETAIL_CHARS:
        normalized_detail = normalized_detail[: _MAX_DETAIL_CHARS - 3] + "..."
    return IndependentReviewVerificationResult(
        status=status,
        code=code,
        detail=normalized_detail,
        bundle_digest_sha256=bundle_digest_sha256,
    )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateJsonKeyError(key)
        value[key] = item
    return value


def _validation_detail(exc: ValidationError) -> str:
    errors = exc.errors(include_url=False)
    if not errors:
        return "serialized reviewer bundle failed schema validation"
    rendered: list[str] = []
    for item in errors[:8]:
        location = ".".join(str(part) for part in item.get("loc", ())) or "<root>"
        error_type = str(item.get("type", "validation_error"))
        message = str(item.get("msg", "schema validation failed"))
        rendered.append(f"{location}: {error_type}: {message}")
    if len(errors) > len(rendered):
        rendered.append(f"{len(errors) - len(rendered)} additional validation error(s)")
    return "; ".join(rendered)


def verify_serialized_independent_review_export(
    serialized: str | bytes,
) -> IndependentReviewVerificationResult:
    """Verify a serialized Phase 9D bundle without authority or side effects.

    The function performs only local parsing, strict schema validation, and the
    Phase 9D evidence-reproduction checks. It performs no network I/O, registry
    access, signing, authorization, readiness promotion, or execution.
    """

    if not isinstance(serialized, (str, bytes)):
        return _result(
            status="FAIL",
            code="UNSUPPORTED_INPUT_TYPE",
            detail="serialized reviewer bundle must be str or bytes",
        )

    if isinstance(serialized, bytes):
        raw = serialized
        if len(raw) > MAX_SERIALIZED_REVIEW_BUNDLE_BYTES:
            return _result(
                status="FAIL",
                code="INPUT_TOO_LARGE",
                detail=(
                    "serialized reviewer bundle exceeds "
                    f"{MAX_SERIALIZED_REVIEW_BUNDLE_BYTES} byte limit"
                ),
            )
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            return _result(
                status="FAIL",
                code="INVALID_UTF8",
                detail=f"serialized reviewer bundle is not valid UTF-8: {exc}",
            )
    else:
        try:
            raw = serialized.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            return _result(
                status="FAIL",
                code="INVALID_UTF8",
                detail=f"serialized reviewer bundle cannot encode as UTF-8: {exc}",
            )
        if len(raw) > MAX_SERIALIZED_REVIEW_BUNDLE_BYTES:
            return _result(
                status="FAIL",
                code="INPUT_TOO_LARGE",
                detail=(
                    "serialized reviewer bundle exceeds "
                    f"{MAX_SERIALIZED_REVIEW_BUNDLE_BYTES} byte limit"
                ),
            )
        text = serialized

    try:
        parsed = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except _DuplicateJsonKeyError as exc:
        return _result(
            status="FAIL",
            code="DUPLICATE_JSON_KEY",
            detail=str(exc),
        )
    except json.JSONDecodeError as exc:
        return _result(
            status="FAIL",
            code="INVALID_JSON",
            detail=(
                f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
            ),
        )

    if not isinstance(parsed, dict):
        return _result(
            status="FAIL",
            code="TOP_LEVEL_NOT_OBJECT",
            detail="serialized reviewer bundle must be a top-level JSON object",
        )

    try:
        bundle = IndependentReviewExportBundle.model_validate(parsed)
    except ValidationError as exc:
        return _result(
            status="FAIL",
            code="SCHEMA_VALIDATION_FAILED",
            detail=_validation_detail(exc),
        )

    try:
        verify_independent_review_export_bundle(bundle)
    except IndependentReviewExportError as exc:
        return _result(
            status="FAIL",
            code="EVIDENCE_VERIFICATION_FAILED",
            detail=str(exc),
            bundle_digest_sha256=bundle.bundle_digest_sha256,
        )

    return _result(
        status="PASS",
        code="VERIFIED",
        detail=(
            "serialized reviewer bundle passed strict schema validation and all "
            "local Phase 9D evidence-reproduction checks"
        ),
        bundle_digest_sha256=bundle.bundle_digest_sha256,
    )
