from __future__ import annotations

import base64
import copy
import hashlib
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.prime_sentinel_authorization import PrimeSentinelVerifier
from worldshepherd_sara.restriction_observability import (
    ASSURANCE_DIMENSIONS,
    project_restriction_audit_record,
    restriction_assurance_dimensions,
    restriction_observability,
)
from worldshepherd_sara.restriction_provenance import (
    RESTRICTION_AUTHORITY,
    RESTRICTION_EVENT,
    RESTRICTION_SCHEMA_V2,
    capture_restriction,
)
from worldshepherd_sara.restriction_signature import (
    SIGNED_RESTRICTION_SCHEMA,
    bind_verified_restriction_signature,
    canonical_restriction_signature_message,
)


KEY = b"worldshepherd-g7-quality-hmac-key-32-bytes-minimum"
KEY_ID = "ws-restriction-key-epoch-quality"
SIGNING_KEY_ID = "PS-QUALITY-K1"
APPROVED_SUMMARY = "Output was restricted; only bounded provenance is retained."
TOTAL_ASSURANCE_DIMENSIONS = 10
BASELINE_UNRESOLVED_DIMENSIONS = frozenset(
    {
        "authority_identity",
        "authority_binding",
        "fingerprint_key_epoch",
        "signature_verification",
        "signing_key_identity",
        "signing_key_fingerprint",
    }
)
BASELINE_MANUAL_INFERENCE_UNITS = len(BASELINE_UNRESOLVED_DIMENSIONS)
MAX_UNRESOLVED_RATIO = 0.10


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _evidence():
    return capture_restriction(
        fingerprint_key=KEY,
        fingerprint_key_id=KEY_ID,
        action="BLOCK",
        reason_code="POLICY.QUALITY_GATE",
        source_system="CHAT_ASSISTANT",
        processor="POLICY_GATE",
        process_version="v3",
        policy_ref="CONTENT_POLICY",
        correlation_id="quality-001",
        raw_input="quality gate input must not persist",
        raw_generated="quality gate output must not persist",
        safe_summary=APPROVED_SUMMARY,
        metadata={
            "stage": "post_generation_policy_check",
            "claims_state": "IMPLEMENTED_IN_SOFTWARE",
            "attempt": 1,
        },
        occurred_at="2026-09-17T23:20:00+00:00",
    )


def _verifier_and_signed_record():
    private = Ed25519PrivateKey.generate()
    verifier = PrimeSentinelVerifier(
        public_keys_b64url={
            SIGNING_KEY_ID: _b64url(private.public_key().public_bytes_raw())
        }
    )
    evidence = _evidence()
    signature = _b64url(
        private.sign(
            canonical_restriction_signature_message(
                evidence,
                signing_key_id=SIGNING_KEY_ID,
            )
        )
    )
    signed = bind_verified_restriction_signature(
        evidence,
        signing_key_id=SIGNING_KEY_ID,
        signature_b64url=signature,
        verifier=verifier,
    )
    payload = signed.semantic_document()
    payload["_outbox_event_id"] = signed.outbox_event_id
    payload["_delivery_semantics"] = "AT_LEAST_ONCE"
    record = AuditRecord(
        timestamp="2026-09-17T23:20:01+00:00",
        event=RESTRICTION_EVENT,
        actor=RESTRICTION_AUTHORITY,
        payload=payload,
    ).model_dump(mode="json")
    return evidence, verifier, record


def _canonical_id(payload: dict) -> str:
    identity = {
        key: value
        for key, value in payload.items()
        if key not in {"restriction_id", "_outbox_event_id", "_delivery_semantics"}
    }
    encoded = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:32]


def _legacy_v2_record():
    evidence = _evidence()
    payload = copy.deepcopy(evidence.semantic_document())
    payload["schema"] = RESTRICTION_SCHEMA_V2
    payload.pop("fingerprint_key_id")
    payload["restriction_id"] = _canonical_id(payload)
    payload["_outbox_event_id"] = (
        f"SARA-EVENT-RESTRICTION-{payload['restriction_id']}"
    )
    payload["_delivery_semantics"] = "AT_LEAST_ONCE"
    return AuditRecord(
        timestamp="2026-09-17T23:20:01+00:00",
        event=RESTRICTION_EVENT,
        actor=RESTRICTION_AUTHORITY,
        payload=payload,
    ).model_dump(mode="json")


def test_v4_machine_resolves_all_ten_assurance_dimensions():
    _evidence_obj, verifier, record = _verifier_and_signed_record()
    projected = project_restriction_audit_record(record, verifier=verifier)
    facts = restriction_assurance_dimensions(projected)

    assert projected["provenance_schema"] == SIGNED_RESTRICTION_SCHEMA
    assert len(ASSURANCE_DIMENSIONS) == TOTAL_ASSURANCE_DIMENSIONS == 10
    assert BASELINE_MANUAL_INFERENCE_UNITS == 6
    assert BASELINE_UNRESOLVED_DIMENSIONS.issubset(set(ASSURANCE_DIMENSIONS))
    assert set(facts) == set(ASSURANCE_DIMENSIONS)
    assert all(facts.values())
    assert not [
        name for name in BASELINE_UNRESOLVED_DIMENSIONS if not facts[name]
    ]

    unresolved = sum(int(not value) for value in facts.values())
    assert unresolved / BASELINE_MANUAL_INFERENCE_UNITS <= MAX_UNRESOLVED_RATIO
    assert unresolved == 0


def test_observability_reports_zero_unresolved_dimensions_for_signed_v4():
    _evidence_obj, verifier, record = _verifier_and_signed_record()

    report = restriction_observability(
        [record],
        recent_limit=1,
        verifier=verifier,
    )

    assert report["ok"] is True
    assert report["assurance_quality"] == {
        "required_dimensions_per_record": 10,
        "fully_resolved_v4_records": 1,
        "unresolved_dimensions": 0,
    }


def test_legacy_v2_remains_readable_but_cannot_claim_fully_resolved_v4_quality():
    record = _legacy_v2_record()
    projected = project_restriction_audit_record(record)
    facts = restriction_assurance_dimensions(projected)

    assert projected["provenance_schema"] == RESTRICTION_SCHEMA_V2
    assert facts["restriction_identity"] is True
    assert facts["event_identity"] is True
    assert facts["delivery_semantics"] is True
    assert facts["authority_identity"] is True
    assert facts["authority_binding"] is True
    assert facts["fingerprint_key_epoch"] is False
    assert facts["signature_verification"] is False
    assert facts["signing_key_identity"] is False
    assert facts["signing_key_fingerprint"] is False
    assert facts["raw_content_persistence"] is True

    report = restriction_observability([record], recent_limit=1)
    assert report["valid_restriction_events"] == 1
    assert report["assurance_quality"]["fully_resolved_v4_records"] == 0
    assert report["assurance_quality"]["unresolved_dimensions"] == 4
