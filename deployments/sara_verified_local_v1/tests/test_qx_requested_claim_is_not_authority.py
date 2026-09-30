from worldshepherd_sara.qx_evidence import EvidenceVector, QualificationEnvelope, digest


def test_requested_physical_claim_does_not_self_authorize():
    env = QualificationEnvelope(
        qualification_id="test", qualification_version="EVIDENCE-01",
        experiment_id="test", run_id="test",
        claim_state_before="IMPLEMENTED_IN_SOFTWARE",
        requested_claim_state_after="PHYSICAL_COUPON_HARDWARE",
        software_commit="test", operator_id="test", authorization_record="test",
        test_manifest_digest=digest({"test": True}), raw_evidence=[{"software": "pass"}],
        dimensions={"software": True}, run_complete=True,
        evidence_vector=EvidenceVector(assurance_tevv="INTERNAL_REPRODUCIBLE_TEST"),
    )
    assert env.finalize_internal()["qualified"] is True
    assert env.claims["physical_validation"] is False
    assert env.promote_physical() is False
