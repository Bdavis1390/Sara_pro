from worldshepherd_sara.qx_evidence import EvidenceVector, QualificationEnvelope, digest


def test_failed_run_still_has_evidence_digest_and_does_not_promote():
    env = QualificationEnvelope(
        qualification_id="WS-SEMCAP-01", qualification_version="EVIDENCE-01",
        experiment_id="negative-test", run_id="negative-test",
        claim_state_before="IMPLEMENTED_IN_SOFTWARE",
        requested_claim_state_after="INTERNAL_REPRODUCIBLE_TEST",
        software_commit="test", operator_id="test", authorization_record="test",
        test_manifest_digest=digest({"negative": True}),
        raw_evidence=[{"observed": "mandatory dimension failed"}],
        dimensions={"Q_C": True, "Q_X": False}, run_complete=True,
        evidence_vector=EvidenceVector(assurance_tevv="INTERNAL_REPRODUCIBLE_TEST"),
    )
    result = env.finalize_internal()
    assert result["qualified"] is False
    assert result["evidence_digest"].startswith("sha256:")
    assert env.claims["physical_validation"] is False
