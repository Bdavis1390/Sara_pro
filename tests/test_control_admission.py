import json
from pathlib import Path

import pytest

from worldshepherd_sara.control_admission import ArchiveControlAdmissionGate


EVIDENCE = Path("evidence/fair_mast/shot_30420_amc_data_probe_20260912.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_real_fair_mast_probe_is_denied_control_admission():
    decision = ArchiveControlAdmissionGate().evaluate(load_evidence())
    assert decision.admitted is False
    assert decision.reason == "archive_not_control_evidence_eligible"
    assert "uncertainty_metadata_unavailable" in decision.blockers
    assert "upstream_quality_not_control_qualified" in decision.blockers


def test_require_fails_closed_with_machine_readable_blockers():
    with pytest.raises(ValueError, match="archive_not_control_evidence_eligible") as exc:
        ArchiveControlAdmissionGate().require(load_evidence())
    assert "real_plasma_state_estimation_not_validated" in str(exc.value)


def test_admission_cannot_be_forced_by_supplying_only_uncertainty_and_quality_flags():
    evidence = load_evidence()
    evidence["readiness"]["uncertainty_metadata_available"] = True
    evidence["readiness"]["upstream_quality"] = "Checked"
    evidence["readiness"]["control_evidence_eligible"] = True
    decision = ArchiveControlAdmissionGate().evaluate(evidence)
    assert decision.admitted is False
    assert "real_plasma_state_estimation_not_validated" in decision.blockers
    assert "real_machine_control_not_validated" in decision.blockers


def test_fully_explicit_validated_fixture_can_be_admitted():
    evidence = load_evidence()
    evidence["readiness"]["uncertainty_metadata_available"] = True
    evidence["readiness"]["upstream_quality"] = "Checked"
    evidence["readiness"]["control_evidence_eligible"] = True
    evidence["claims_boundary"]["real_plasma_state_estimation_validated"] = True
    evidence["claims_boundary"]["real_machine_control_validated"] = True
    decision = ArchiveControlAdmissionGate().evaluate(evidence)
    assert decision.admitted is True
    assert decision.blockers == ()
