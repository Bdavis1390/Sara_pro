from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Callable

from opentelemetry.trace import format_span_id, format_trace_id, get_current_span
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


TRACE_RECEIPT_SCHEMA = "WS-TRACE-CORRELATION-V1"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def extract_w3c_trace_context(
    *,
    traceparent: str,
    tracestate: str | None = None,
    evidence_sha256: str | None = None,
    now: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    if not isinstance(traceparent, str) or not traceparent.strip():
        raise ValueError("traceparent is required")
    if evidence_sha256 is not None and not SHA256_PATTERN.fullmatch(evidence_sha256):
        raise ValueError("evidence_sha256 must be 64 lowercase hexadecimal characters")

    carrier: dict[str, str] = {"traceparent": traceparent.strip()}
    if tracestate is not None:
        if not isinstance(tracestate, str):
            raise ValueError("tracestate must be a string when supplied")
        carrier["tracestate"] = tracestate.strip()

    context = TraceContextTextMapPropagator().extract(carrier=carrier)
    span_context = get_current_span(context).get_span_context()
    if not span_context.is_valid:
        raise ValueError("invalid W3C trace context")

    timestamp = (now or (lambda: datetime.now(timezone.utc)))()
    if timestamp.tzinfo is None:
        raise ValueError("receipt timestamp must be timezone-aware")

    normalized_tracestate = span_context.trace_state.to_header()
    source = {
        "traceparent": carrier["traceparent"],
        "tracestate": carrier.get("tracestate"),
    }
    receipt = {
        "schema": TRACE_RECEIPT_SCHEMA,
        "recorded_utc": timestamp.astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        ),
        "trace_id": format_trace_id(span_context.trace_id),
        "parent_span_id": format_span_id(span_context.span_id),
        "trace_flags": int(span_context.trace_flags),
        "is_remote": bool(span_context.is_remote),
        "tracestate": normalized_tracestate or None,
        "source_headers_sha256": hashlib.sha256(
            _canonical_json_bytes(source)
        ).hexdigest(),
        "evidence_sha256": evidence_sha256,
        "claims_boundary": (
            "This receipt binds a valid W3C Trace Context to an optional evidence digest for "
            "correlation. Trace context is not identity, authorization, integrity proof, human "
            "approval, or evidence that the upstream caller is trustworthy. PRIME/SARA authority "
            "and ECHO evidence-integrity gates remain independently applicable."
        ),
    }
    return receipt


def receipt_sha256(receipt: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(receipt)).hexdigest()
