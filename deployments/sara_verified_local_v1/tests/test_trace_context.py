from datetime import datetime, timezone

import pytest

from worldshepherd_sara.trace_context import extract_w3c_trace_context


def test_valid_w3c_trace_context_is_correlated() -> None:
    receipt = extract_w3c_trace_context(
        traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        tracestate="vendorname=opaquevalue",
        evidence_sha256="a" * 64,
        now=lambda: datetime(2026, 9, 17, 21, 30, tzinfo=timezone.utc),
    )
    assert receipt["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert receipt["parent_span_id"] == "00f067aa0ba902b7"
    assert receipt["trace_flags"] == 1
    assert receipt["is_remote"] is True
    assert receipt["tracestate"] == "vendorname=opaquevalue"
    assert receipt["evidence_sha256"] == "a" * 64
    assert len(receipt["source_headers_sha256"]) == 64


def test_zero_trace_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid W3C trace context"):
        extract_w3c_trace_context(
            traceparent="00-00000000000000000000000000000000-00f067aa0ba902b7-01"
        )


def test_zero_span_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid W3C trace context"):
        extract_w3c_trace_context(
            traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736-0000000000000000-01"
        )


def test_malformed_traceparent_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid W3C trace context"):
        extract_w3c_trace_context(traceparent="not-a-traceparent")


def test_invalid_evidence_digest_is_rejected() -> None:
    with pytest.raises(ValueError, match="evidence_sha256"):
        extract_w3c_trace_context(
            traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
            evidence_sha256="ABC123",
        )


def test_trace_context_does_not_create_authorization_claim() -> None:
    receipt = extract_w3c_trace_context(
        traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00"
    )
    boundary = receipt["claims_boundary"].lower()
    assert "not identity" in boundary
    assert "authorization" in boundary
    assert "human approval" in boundary
