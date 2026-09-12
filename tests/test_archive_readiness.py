import json
from pathlib import Path

from worldshepherd_sara.archive_readiness import evaluate_archive_evidence


EVIDENCE = Path("evidence/fair_mast/shot_30420_amc_data_probe_20260912.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_real_fair_mast_probe_is_analysis_eligible_but_control_ineligible():
    decision = evaluate_archive_evidence(load_evidence())
    assert decision.analysis_eligible is True
    assert decision.control_evidence_eligible is False
    assert "uncertainty_metadata_unavailable" in decision.reasons
    assert "upstream_quality_not_control_qualified" in decision.reasons
    assert "real_plasma_state_estimation_not_validated" in decision.reasons
    assert "real_machine_control_not_validated" in decision.reasons
    assert "source_record_declares_control_ineligible" in decision.reasons


def test_missing_integrity_blocks_even_analysis_eligibility():
    evidence = load_evidence()
    evidence["readiness"]["chunk_integrity_hashed"] = False
    decision = evaluate_archive_evidence(evidence)
    assert decision.analysis_eligible is False
    assert decision.control_evidence_eligible is False
    assert "chunk_integrity_not_hashed" in decision.reasons


def test_missing_readiness_section_fails_closed():
    decision = evaluate_archive_evidence({"schema": "test"})
    assert decision.analysis_eligible is False
    assert decision.control_evidence_eligible is False
    assert decision.reasons == ("readiness_section_missing",)


def test_control_eligibility_cannot_be_created_by_only_flipping_declared_flag():
    evidence = load_evidence()
    evidence["readiness"]["control_evidence_eligible"] = True
    decision = evaluate_archive_evidence(evidence)
    assert decision.control_evidence_eligible is False
    assert "uncertainty_metadata_unavailable" in decision.reasons
    assert "upstream_quality_not_control_qualified" in decision.reasons
