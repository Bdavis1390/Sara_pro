from __future__ import annotations

import json
from pathlib import Path

BASELINE_PATH = Path(__file__).resolve().parents[1] / "standards_conformance_baseline.json"
REQUIRED_STANDARD_IDS = {
    "NIST_CSF_2_0",
    "NIST_SSDF_800_218",
    "NIST_800_171_R3",
    "NIST_800_171A_R3",
    "NIST_800_172_R3",
    "DOD_CMMC_32_CFR_170",
    "NIST_800_161_R1_UPD1",
    "SLSA_1_2",
    "OPENSSF_SCORECARD",
    "OWASP_ASVS_5",
    "CYCLONEDX_1_6_PLUS",
    "SPDX_3",
    "OPENVEX",
    "NIST_AI_RMF_1_0",
}
PROHIBITED_CURRENT_STATUS_TERMS = {
    "CERTIFIED",
    "CONFORMANT",
    "VALIDATED",
    "ACCREDITED",
    "APPROVED",
    "AUTHORIZED",
}


def _load() -> dict:
    assert BASELINE_PATH.is_file(), f"missing baseline file: {BASELINE_PATH}"
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def test_standards_baseline_schema_and_claims_boundary() -> None:
    baseline = _load()

    assert baseline["schema"] == "WS-INDUSTRY-STANDARDS-CONFORMANCE-BASELINE-V1"
    assert "does not establish certification" in baseline["claims_boundary"]
    assert "CMMC conformity" in baseline["claims_boundary"]
    assert "BAE validation" in baseline["claims_boundary"]
    assert "field performance" in baseline["claims_boundary"]


def test_required_authoritative_standards_are_tracked() -> None:
    baseline = _load()
    standards = baseline["standard_sources"]
    observed = {record["id"] for record in standards}

    assert REQUIRED_STANDARD_IDS.issubset(observed)
    for record in standards:
        assert record["authoritative_url"].startswith("https://")
        assert record["baseline_target"]
        assert record["exceed_target"]
        assert record["current_status"]


def test_no_target_standard_is_self_certified_by_baseline() -> None:
    baseline = _load()

    for record in baseline["standard_sources"]:
        status = record["current_status"].upper()
        for term in PROHIBITED_CURRENT_STATUS_TERMS:
            non_claim_status = status.replace(f"NOT_{term}", "").replace(f"{term}_NOT_CLAIMED", "")
            assert term not in non_claim_status, (record["id"], record["current_status"], term)
        assert "NOT_CLAIMED" in status or "REQUIRED" in status or "TARGET" in status or "PARTIAL" in status


def test_meet_or_exceed_requires_evidence_and_assessment() -> None:
    baseline = _load()
    stance = baseline["stance"]
    gates = set(baseline["evidence_gates"])

    assert "not marked MET or EXCEEDED" in stance["meet_or_exceed_rule"]
    assert "never upgrades capability maturity" in stance["prediction_rule"]
    assert "not validation" in stance["partner_rule"]
    assert "No CUI/CDI handling is claimed" in stance["cui_rule"]
    assert "implementation_evidence_attached" in gates
    assert "ci_artifact_or_review_artifact_attached" in gates
    assert "external_or_formal_assessment_attached_when_required" in gates


def test_minimum_redlines_block_common_overclaims() -> None:
    baseline = _load()
    redlines = "\n".join(baseline["minimum_redlines"])

    assert "No certification or conformity claim" in redlines
    assert "No CUI/CDI handling claim" in redlines
    assert "No BAE, DOE, partner, supplier, or government validation claim" in redlines
    assert "No hardware, field, laboratory, or operational-performance claim" in redlines


def test_readiness_model_preserves_assessment_boundary() -> None:
    baseline = _load()
    levels = {entry["level"]: entry["meaning"] for entry in baseline["readiness_levels"]}

    assert levels["L2_INTERNAL_EVIDENCE"] == "Internal implementation evidence or CI artifact exists."
    assert "external reviewer" in levels["L4_INDEPENDENT_REVIEW_READY"]
    assert "third-party" in levels["L5_FORMALLY_ASSESSED"]
    assert "L1_CONTROL_INTENT" in baseline["current_global_readiness"]
    assert "L4_INDEPENDENT_REVIEW_READY" in baseline["target_global_readiness"]
