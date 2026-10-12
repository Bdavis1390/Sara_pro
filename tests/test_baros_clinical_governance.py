from datetime import datetime, timedelta, timezone
import hashlib

import pytest

from baros.clinical_governance import (
    EvidenceEnvelope,
    GateTransitionRequest,
    IntendedUseManifest,
    SQLiteGateLedger,
    assess_evidence_for_gate,
    authorize_request,
)


def h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def manifest() -> IntendedUseManifest:
    return IntendedUseManifest(
        validation_id="BAROS-VAL-001",
        indication="locked research indication",
        disease_stage_or_risk_group="locked cohort",
        modality="external-beam photon",
        delivery_technique="IMRT/VMAT research comparison",
        machine_class="partner-defined linac class",
        tps_name="partner TPS",
        tps_version="locked-version",
        fractionation="locked protocol",
        comparator_workflow="institution standard-of-care planning workflow",
        planning_protocol="BAROS external validation protocol v1",
        operator_roles=("qualified medical physicist", "radiation oncologist"),
        primary_endpoints=("physical dosimetric agreement",),
    )


def envelope(*, kinds=("component_verification",), contradictions=(), deviations=(), external=False, human=False):
    m = manifest()
    return EvidenceEnvelope(
        validation_id=m.validation_id,
        commit_sha="abc123",
        intended_use_sha256=m.digest(),
        protocol_sha256=h("protocol"),
        configuration_sha256=h("config"),
        evidence_kinds=tuple(kinds),
        raw_artifact_sha256=(h("raw"),),
        analysis_artifact_sha256=(h("analysis"),),
        environment_sha256=h("environment"),
        source_custody="controlled research evidence store",
        uncertainty_statement="measurement/model uncertainty is declared and bounded by protocol",
        deviations=tuple(deviations),
        unresolved_contradictions=tuple(contradictions),
        independent_reviewer_role="qualified medical physicist" if external else None,
        externally_controlled=external,
        human_authorized=human,
        patient_care_allowed=False,
    )


def iso(hours: int = 0) -> str:
    return (datetime(2026, 9, 18, 1, 0, tzinfo=timezone.utc) + timedelta(hours=hours)).isoformat()


def request_for(env: EvidenceEnvelope, *, nonce="n-1", epoch=0, from_gate="G0", to_gate="G1"):
    return GateTransitionRequest(
        validation_id=env.validation_id,
        from_gate=from_gate,
        to_gate=to_gate,
        expected_epoch=epoch,
        commit_sha=env.commit_sha,
        intended_use_sha256=env.intended_use_sha256,
        evidence_sha256=env.digest(),
        target_environment="BAROS research validation",
        nonce=nonce,
        expires_at=iso(2),
    )


def auth_for(req: GateTransitionRequest, *, auth_id="auth-1"):
    return authorize_request(
        req,
        approver_id="human-reviewer",
        approver_role="CRE1AWS / authorized human reviewer",
        authorization_id=auth_id,
        issued_at=iso(0),
        expires_at=iso(2),
    )


def test_intended_use_digest_is_stable_and_field_sensitive():
    first = manifest()
    second = manifest()
    assert first.digest() == second.digest()
    changed = IntendedUseManifest(**{**first.__dict__, "tps_version": "different-version"})
    assert changed.digest() != first.digest()


def test_external_gate_requires_partner_control_and_independent_reviewer():
    env = envelope(kinds=("external_tps_recalculation",), external=False)
    assessment = assess_evidence_for_gate(env, "G5")
    assert assessment.promotable is False
    assert "external gate requires partner-controlled evidence" in assessment.blockers


def test_contradiction_and_deviation_quarantine_evidence():
    env = envelope(
        contradictions=("dose grid origin conflict",),
        deviations=("unapproved protocol change",),
    )
    assessment = assess_evidence_for_gate(env, "G1")
    assert assessment.promotable is False
    assert any("contradictions" in item for item in assessment.blockers)
    assert any("deviations" in item for item in assessment.blockers)


def test_g6_requires_measured_dose_and_deliverability():
    env = envelope(kinds=("measured_dose",), external=True)
    assessment = assess_evidence_for_gate(env, "G6")
    assert assessment.promotable is False
    assert assessment.missing_evidence_kinds == ("deliverability",)


def test_adjacent_transition_only():
    env = envelope()
    with pytest.raises(ValueError, match="exactly one gate"):
        request_for(env, from_gate="G0", to_gate="G2").validate()


def test_exact_effect_authorization_rejects_changed_request(tmp_path):
    env = envelope()
    req = request_for(env)
    auth = auth_for(req)
    changed = GateTransitionRequest(**{**req.__dict__, "target_environment": "different-environment"})
    ledger = SQLiteGateLedger(tmp_path / "ledger.sqlite3")
    with pytest.raises(ValueError, match="exact request|exact activation effect"):
        ledger.apply(request=changed, authorization=auth, envelope=env, now=iso(1))


def test_expired_request_fails_closed(tmp_path):
    env = envelope()
    req = request_for(env)
    auth = auth_for(req)
    ledger = SQLiteGateLedger(tmp_path / "ledger.sqlite3")
    with pytest.raises(ValueError, match="expired"):
        ledger.apply(request=req, authorization=auth, envelope=env, now=iso(3))


def test_valid_transition_is_durable_and_replay_is_rejected(tmp_path):
    env = envelope()
    req = request_for(env)
    auth = auth_for(req)
    path = tmp_path / "ledger.sqlite3"
    ledger = SQLiteGateLedger(path)

    assert ledger.apply(request=req, authorization=auth, envelope=env, now=iso(1)) == ("G1", 1)
    assert ledger.state(env.validation_id)[:2] == ("G1", 1)

    reopened = SQLiteGateLedger(path)
    with pytest.raises(ValueError):
        reopened.apply(request=req, authorization=auth, envelope=env, now=iso(1))


def test_stale_epoch_cannot_advance_state(tmp_path):
    env1 = envelope()
    req1 = request_for(env1)
    auth1 = auth_for(req1)
    ledger = SQLiteGateLedger(tmp_path / "ledger.sqlite3")
    ledger.apply(request=req1, authorization=auth1, envelope=env1, now=iso(1))

    env2 = EvidenceEnvelope(
        **{
            **env1.__dict__,
            "evidence_kinds": ("end_to_end_pipeline",),
            "analysis_artifact_sha256": (h("analysis-2"),),
        }
    )
    stale = request_for(env2, nonce="n-2", epoch=0, from_gate="G1", to_gate="G2")
    stale_auth = auth_for(stale, auth_id="auth-2")
    with pytest.raises(ValueError, match="stale epoch"):
        ledger.apply(request=stale, authorization=stale_auth, envelope=env2, now=iso(1))


def test_g7_requires_explicit_human_authorization():
    env = envelope(kinds=("held_out_retrospective",), external=True, human=False)
    assessment = assess_evidence_for_gate(env, "G7")
    assert assessment.promotable is False
    assert "clinical/external progression requires explicit human authorization" in assessment.blockers


def test_research_envelope_cannot_authorize_patient_care():
    env = EvidenceEnvelope(**{**envelope().__dict__, "patient_care_allowed": True})
    with pytest.raises(ValueError, match="cannot authorize patient care"):
        env.validate()
