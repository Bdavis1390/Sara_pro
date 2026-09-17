from __future__ import annotations

import pytest

import worldshepherd_sara.restriction_context_policy as context_policy
from worldshepherd_sara.restriction_context_policy import (
    CHAT_ASSISTANT_PROFILE_ID,
    EMPTY_CONTEXT_PROFILE_ID,
    RestrictionContextPolicyError,
    registered_context_profile_ids,
    validate_restriction_context,
)
from worldshepherd_sara.restriction_provenance import (
    RestrictionProvenanceError,
    capture_restriction,
)


KEY = b"worldshepherd-g3-context-policy-key-32-bytes-minimum"
KEY_ID = "ws-restriction-key-epoch-2026-09"
APPROVED_SUMMARY = "Output was restricted; only bounded provenance is retained."


def test_registered_chat_assistant_profile_accepts_only_declared_context():
    metadata, summary = validate_restriction_context(
        source_system="CHAT_ASSISTANT",
        processor="POLICY_GATE",
        metadata={
            "stage": "post_generation_policy_check",
            "claims_state": "IMPLEMENTED_IN_SOFTWARE",
            "attempt": 1,
        },
        safe_summary=APPROVED_SUMMARY,
    )

    assert metadata == {
        "stage": "post_generation_policy_check",
        "claims_state": "IMPLEMENTED_IN_SOFTWARE",
        "attempt": 1,
        "context_profile": CHAT_ASSISTANT_PROFILE_ID,
    }
    assert summary == APPROVED_SUMMARY
    assert registered_context_profile_ids() == (CHAT_ASSISTANT_PROFILE_ID,)


def test_profile_registry_and_field_rules_are_immutable():
    profile = context_policy._PROFILES[("CHAT_ASSISTANT", "POLICY_GATE")]

    with pytest.raises(TypeError):
        context_policy._PROFILES[("FORGED", "GATE")] = profile

    with pytest.raises(TypeError):
        profile.metadata_rules["new_field"] = context_policy.MetadataRule(kind="integer")


def test_capture_binds_context_profile_into_persisted_evidence():
    evidence = capture_restriction(
        fingerprint_key=KEY,
        fingerprint_key_id=KEY_ID,
        action="REDACT",
        reason_code="POLICY.RESTRICTED_OUTPUT",
        source_system="CHAT_ASSISTANT",
        processor="POLICY_GATE",
        raw_generated="restricted candidate",
        safe_summary=APPROVED_SUMMARY,
        metadata={
            "stage": "post_generation_policy_check",
            "claims_state": "PROVEN_INTERNALLY",
            "attempt": 2,
        },
        occurred_at="2026-09-17T21:30:00+00:00",
    )

    document = evidence.semantic_document()
    assert document["metadata"]["context_profile"] == CHAT_ASSISTANT_PROFILE_ID
    assert document["metadata"]["attempt"] == 2
    assert "restricted candidate" not in evidence.canonical_json()


def test_registered_profile_rejects_unknown_metadata_fields():
    with pytest.raises(RestrictionContextPolicyError, match="outside"):
        validate_restriction_context(
            source_system="CHAT_ASSISTANT",
            processor="POLICY_GATE",
            metadata={"unexpected": "value"},
            safe_summary=None,
        )


def test_registered_profile_rejects_unapproved_enum_values():
    for field, value in (
        ("stage", "arbitrary_free_text"),
        ("claims_state", "CERTIFIED_BY_PROVIDER"),
    ):
        with pytest.raises(RestrictionContextPolicyError, match="not allowed"):
            validate_restriction_context(
                source_system="CHAT_ASSISTANT",
                processor="POLICY_GATE",
                metadata={field: value},
                safe_summary=None,
            )


def test_registered_profile_rejects_boolean_and_out_of_range_attempts():
    for value in (True, 0, 1001):
        with pytest.raises(RestrictionContextPolicyError):
            validate_restriction_context(
                source_system="CHAT_ASSISTANT",
                processor="POLICY_GATE",
                metadata={"attempt": value},
                safe_summary=None,
            )


def test_context_profile_is_system_managed():
    with pytest.raises(RestrictionContextPolicyError, match="system-managed"):
        validate_restriction_context(
            source_system="CHAT_ASSISTANT",
            processor="POLICY_GATE",
            metadata={"context_profile": "FORGED"},
            safe_summary=None,
        )


def test_registered_profile_rejects_arbitrary_safe_summary():
    with pytest.raises(RestrictionContextPolicyError, match="approved template"):
        validate_restriction_context(
            source_system="CHAT_ASSISTANT",
            processor="POLICY_GATE",
            metadata={},
            safe_summary="free-form text is not an approved summary template",
        )


def test_unregistered_integration_accepts_only_empty_context():
    metadata, summary = validate_restriction_context(
        source_system="UNKNOWN_CONNECTOR",
        processor="UNKNOWN_GATE",
        metadata={},
        safe_summary=None,
    )

    assert metadata == {"context_profile": EMPTY_CONTEXT_PROFILE_ID}
    assert summary is None

    with pytest.raises(RestrictionContextPolicyError, match="may not persist metadata"):
        validate_restriction_context(
            source_system="UNKNOWN_CONNECTOR",
            processor="UNKNOWN_GATE",
            metadata={"stage": "post_generation_policy_check"},
            safe_summary=None,
        )

    with pytest.raises(RestrictionContextPolicyError, match="may not persist a summary"):
        validate_restriction_context(
            source_system="UNKNOWN_CONNECTOR",
            processor="UNKNOWN_GATE",
            metadata={},
            safe_summary=APPROVED_SUMMARY,
        )


def test_capture_propagates_context_policy_failure_as_provenance_error():
    with pytest.raises(RestrictionProvenanceError, match="unregistered"):
        capture_restriction(
            fingerprint_key=KEY,
        fingerprint_key_id=KEY_ID,
            action="BLOCK",
            reason_code="POLICY.UNKNOWN_SOURCE",
            source_system="UNREGISTERED_PROVIDER",
            processor="POLICY_GATE",
            metadata={"stage": "post_generation_policy_check"},
            occurred_at="2026-09-17T21:30:00+00:00",
        )
