from worldshepherd_sara.quantum_external_campaign import (
    build_external_campaigns,
    campaigns_as_dict,
    evaluate_campaign,
)
from worldshepherd_sara.quantum_external_evidence import ExternalEvidenceRecord, ExternalEvidenceType
from worldshepherd_sara.quantum_mission_readiness import CURRENT_QUANTUM_MISSION_INPUTS, MissionEvidenceStage


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64


def _sara_qpu_record(gate_id: str, *, run_id: str = "job-1") -> ExternalEvidenceRecord:
    return ExternalEvidenceRecord(
        project_id="SARA-QRF",
        evidence_type=ExternalEvidenceType.QPU_EXECUTION,
        source_id=f"ibm-runtime-{run_id}",
        raw_artifact_digest=SHA_A,
        collected_utc="2026-08-17T15:45:00Z",
        provider_or_lab="named-qpu-provider",
        configuration_digest=SHA_B,
        result_digest=SHA_C,
        job_or_run_id=run_id,
        backend_or_device="named-qpu-backend",
        latency_seconds=12.5,
        cost_usd=1.25,
        environment="remote_cloud_qpu",
        metadata={
            "campaign_gate_id": gate_id,
            "test_protocol_digest": SHA_A,
            "program_digest": SHA_B,
            "transpiled_program_digest": SHA_C,
            "backend_properties_digest": SHA_A,
            "queue_seconds": "8.0",
            "failure_mode": "none observed",
        },
    )


def test_all_current_projects_have_contiguous_campaigns_to_operational_demo():
    campaigns = build_external_campaigns()
    current = {row.project_id: row for row in CURRENT_QUANTUM_MISSION_INPUTS}

    assert len(campaigns) == len(current) == 7
    assert {row.project_id for row in campaigns} == set(current)

    for campaign in campaigns:
        assert campaign.current_stage == current[campaign.project_id].evidence_stage
        assert campaign.target_stage == MissionEvidenceStage.OPERATIONAL_DEMONSTRATION
        assert campaign.target_score == 97
        assert campaign.gates
        assert campaign.gates[0].from_stage == campaign.current_stage
        assert campaign.gates[-1].to_stage == MissionEvidenceStage.OPERATIONAL_DEMONSTRATION
        for left, right in zip(campaign.gates, campaign.gates[1:]):
            assert left.to_stage == right.from_stage
            assert right.ordinal == left.ordinal + 1


def test_apnt_promotion_preserves_stable_gate_ids_and_starts_at_ext02():
    apnt = next(row for row in build_external_campaigns() if row.project_id == "WS-APNT")

    assert apnt.current_stage == MissionEvidenceStage.SYNTHETIC_SURROGATE
    assert apnt.gates[0].gate_id == "WS-APNT-EXT-02"
    assert apnt.gates[0].from_stage == MissionEvidenceStage.SYNTHETIC_SURROGATE
    assert apnt.gates[0].to_stage == MissionEvidenceStage.CALIBRATED_MODEL


def test_later_stage_evidence_cannot_skip_first_unsatisfied_gate():
    sara = next(row for row in build_external_campaigns() if row.project_id == "SARA-QRF")
    later_record = _sara_qpu_record("SARA-QRF-EXT-02")

    result = evaluate_campaign(sara, [later_record])

    assert result.complete is False
    assert result.achieved_stage == MissionEvidenceStage.INTEGRATED_SIMULATION.value
    assert result.next_gate_id == "SARA-QRF-EXT-01"
    assert result.gate_evaluations[0].satisfied is False


def test_valid_first_qpu_package_advances_exactly_one_stage():
    sara = next(row for row in build_external_campaigns() if row.project_id == "SARA-QRF")
    first_record = _sara_qpu_record("SARA-QRF-EXT-01")

    result = evaluate_campaign(sara, [first_record])

    assert result.complete is False
    assert result.achieved_stage == MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE.value
    assert result.next_gate_id == "SARA-QRF-EXT-02"
    assert result.gate_evaluations[0].satisfied is True
    assert result.gate_evaluations[1].satisfied is False


def test_glob_mapping_preconditions_are_not_silently_assumed():
    glob = next(row for row in build_external_campaigns() if row.project_id == "WS-GLOB")

    blocked = evaluate_campaign(glob, [])
    assert blocked.achieved_stage == MissionEvidenceStage.CONCEPT.value
    assert blocked.next_gate_id == "WS-GLOB-EXT-01"

    first_gate_complete = evaluate_campaign(
        glob,
        [],
        completed_preconditions={
            "WS-GLOB-QMAPPING-PASSED",
            "WS-GLOB-NULL-MODEL-FROZEN",
            "WS-GLOB-CLASSICAL-COMPLEXITY-FROZEN",
        },
    )
    assert first_gate_complete.achieved_stage == MissionEvidenceStage.SYNTHETIC_SURROGATE.value
    assert first_gate_complete.next_gate_id == "WS-GLOB-EXT-02"


def test_campaign_artifact_contains_no_evidence_claims():
    payload = campaigns_as_dict()

    assert payload["mission_readiness_target"] == 97
    assert payload["stage_skipping_prohibited"] is True
    assert payload["stable_gate_ids_preserved_after_promotion"] is True
    assert payload["gate_binding_field"] == "metadata.campaign_gate_id"
    assert len(payload["campaigns"]) == 7
    assert "contains no fabricated external evidence" in payload["claim_control"]
