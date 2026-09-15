from __future__ import annotations

from worldshepherd_sara.assurance_evidence_bundle import (
    build_assurance_evidence_bundle,
    verify_assurance_evidence_bundle,
    verify_assurance_evidence_chain,
)


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def _bundle(*, bundle_id: str = "RUN-001", predecessor: str | None = None):
    return build_assurance_evidence_bundle(
        bundle_id=bundle_id,
        created_utc="2026-09-12T20:40:00+00:00",
        source_ref="synthetic://assurance-run",
        readiness="DEGRADED",
        degraded_metrics=["temperature_c", "temperature_c"],
        baseline_digest=DIGEST_A,
        active_configuration_digest=DIGEST_B,
        authorization_state="DENIED",
        reviewer="REVIEWER-1",
        replay_events=[{"sequence": 1, "state": "observed"}],
        audit_records=[{"event": "assurance.check", "outcome": "recorded"}],
        predecessor_manifest_digest=predecessor,
    )


def test_bundle_is_deterministic_and_verifies():
    first = _bundle()
    second = _bundle()

    assert first.manifest_digest == second.manifest_digest
    assert first.degraded_metrics == ["temperature_c"]
    assert verify_assurance_evidence_bundle(first)


def test_bundle_tampering_is_detected():
    bundle = _bundle()
    tampered = bundle.model_copy(update={"authorization_state": "APPROVED"})

    assert not verify_assurance_evidence_bundle(tampered)


def test_chain_binds_each_bundle_to_its_predecessor():
    first = _bundle(bundle_id="RUN-001")
    second = _bundle(bundle_id="RUN-002", predecessor=first.manifest_digest)

    assert verify_assurance_evidence_chain([first, second])

    broken = second.model_copy(update={"predecessor_manifest_digest": None})
    assert not verify_assurance_evidence_chain([first, broken])
