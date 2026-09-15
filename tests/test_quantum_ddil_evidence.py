from pathlib import Path

from worldshepherd_sara.quantum_ddil_evidence import (
    acknowledge_delayed_sync,
    create_ddil_custody,
    custody_identity_digest,
    validate_ddil_custody,
)


CONFIG_DIGEST = "sha256:" + "a" * 64


def test_ddil_local_identity_survives_matching_delayed_provider_ack(tmp_path: Path):
    artifact = tmp_path / "run.json"
    artifact.write_text('{"result":"local"}\n', encoding="utf-8")
    record = create_ddil_custody(
        artifact,
        project_id="SARA-QRF",
        node_id="field-node-01",
        local_sequence=1,
        local_configuration_digest=CONFIG_DIGEST,
        campaign_gate_id="SARA-QRF-EXT-03",
        collected_utc="2026-08-17T17:20:00Z",
    )
    identity = custody_identity_digest(record)
    acknowledged = acknowledge_delayed_sync(
        record,
        provider_or_service="provider-a",
        provider_ack_id="ack-001",
        provider_artifact_digest=record.local_artifact_digest,
        synchronized_utc="2026-08-17T18:20:00Z",
    )
    decision = validate_ddil_custody(
        acknowledged,
        artifact_path=artifact,
        expected_identity_digest=identity,
    )
    assert acknowledged.sync_state == "acknowledged"
    assert decision.accepted is True
    assert decision.identity_preserved is True
    assert custody_identity_digest(acknowledged) == identity


def test_ddil_provider_digest_mismatch_becomes_conflict_without_rewriting_local_identity(tmp_path: Path):
    artifact = tmp_path / "run.json"
    artifact.write_text('{"result":"local"}\n', encoding="utf-8")
    record = create_ddil_custody(
        artifact,
        project_id="SARA-QRF",
        node_id="field-node-01",
        local_sequence=2,
        local_configuration_digest=CONFIG_DIGEST,
        campaign_gate_id="SARA-QRF-EXT-03",
        collected_utc="2026-08-17T17:21:00Z",
    )
    identity = custody_identity_digest(record)
    conflict = acknowledge_delayed_sync(
        record,
        provider_or_service="provider-a",
        provider_ack_id="ack-002",
        provider_artifact_digest="sha256:" + "b" * 64,
        synchronized_utc="2026-08-17T18:21:00Z",
    )
    decision = validate_ddil_custody(conflict, artifact_path=artifact, expected_identity_digest=identity)
    assert conflict.sync_state == "conflict"
    assert conflict.local_artifact_digest == record.local_artifact_digest
    assert custody_identity_digest(conflict) == identity
    assert decision.accepted is True
    assert decision.identity_preserved is True
    assert conflict.conflict_reason is not None


def test_ddil_detects_local_artifact_tampering(tmp_path: Path):
    artifact = tmp_path / "run.json"
    artifact.write_text('{"result":"original"}\n', encoding="utf-8")
    record = create_ddil_custody(
        artifact,
        project_id="SARA-QRF",
        node_id="field-node-01",
        local_sequence=3,
        local_configuration_digest=CONFIG_DIGEST,
        campaign_gate_id="SARA-QRF-EXT-03",
        collected_utc="2026-08-17T17:22:00Z",
    )
    artifact.write_text('{"result":"tampered"}\n', encoding="utf-8")
    decision = validate_ddil_custody(record, artifact_path=artifact)
    assert decision.accepted is False
    assert any("no longer matches" in reason for reason in decision.reasons)
