from worldshepherd_sara.qx_evidence import EvidenceVector, QualificationEnvelope, digest, dry_run_envelope


def _complete_internal():
    return QualificationEnvelope(
        qualification_id="WS-SEMCAP-01",
        qualification_version="EVIDENCE-01",
        experiment_id="exp-1",
        run_id="run-1",
        claim_state_before="IMPLEMENTED_IN_SOFTWARE",
        requested_claim_state_after="INTERNAL_REPRODUCIBLE_TEST",
        software_commit="abc123",
        operator_id="operator",
        authorization_record="approved-test",
        test_manifest_digest=digest({"test": 1}),
        raw_evidence=[{"measurement": 1}],
        dimensions={"Q_P": True, "Q_R": True, "Q_S": True},
        run_complete=True,
        evidence_vector=EvidenceVector(assurance_tevv="INTERNAL_REPRODUCIBLE_TEST"),
    )


def test_dry_run_cannot_promote():
    env = dry_run_envelope()
    result = env.finalize_internal()
    assert result["qualified"] is False
    assert env.promote_physical() is False
    assert env.promote_external() is False


def test_internal_qualification_does_not_imply_physical():
    env = _complete_internal()
    assert env.finalize_internal()["qualified"] is True
    assert env.claims["physical_validation"] is False
    assert env.claims["external_validation"] is False
    assert env.claims["standards_conformance"] is False
    assert env.claims["program_qualification"] is False


def test_failed_dimension_blocks_internal_qualification():
    env = _complete_internal()
    env.dimensions["Q_S"] = False
    assert env.finalize_internal()["qualified"] is False


def test_physical_promotion_requires_real_interlocks():
    env = _complete_internal()
    assert env.finalize_internal()["qualified"] is True
    env.hardware_ids = ["device-a"]
    env.calibration_ids = ["cal-a"]
    env.physical_io_observed = True
    env.human_safety_controls_verified = True
    env.evidence_vector.physical_performance = "BOUNDED_LOCAL_PHYSICAL_EVIDENCE"
    assert env.promote_physical() is True
    assert env.claims["external_validation"] is False


def test_external_promotion_requires_reference_and_replication_axis():
    env = _complete_internal()
    env.finalize_internal()
    env.hardware_ids = ["device-a"]
    env.calibration_ids = ["cal-a"]
    env.physical_io_observed = True
    env.human_safety_controls_verified = True
    env.evidence_vector.physical_performance = "BOUNDED_LOCAL_PHYSICAL_EVIDENCE"
    env.promote_physical()
    assert env.promote_external() is False
    env.external_replication_reference = "external:test-report-001"
    env.evidence_vector.replication_external = "EXTERNAL_BLIND_TEST"
    assert env.promote_external() is True
