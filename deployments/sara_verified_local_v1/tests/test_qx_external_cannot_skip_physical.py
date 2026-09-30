from worldshepherd_sara.qx_evidence import EvidenceVector, QualificationEnvelope, digest


def test_external_reference_cannot_skip_physical_gate():
    env = QualificationEnvelope(
        qualification_id="test", qualification_version="EVIDENCE-01",
        experiment_id="test", run_id="test", claim_state_before="SOFTWARE",
        requested_claim_state_after="EXTERNAL_BLIND_TEST", software_commit="test",
        operator_id="test", authorization_record="test",
        test_manifest_digest=digest({"test": True}), raw_evidence=[{"test": True}],
        dimensions={"test": True}, run_complete=True,
        external_replication_reference="external:report",
        evidence_vector=EvidenceVector(assurance_tevv="INTERNAL_REPRODUCIBLE_TEST", replication_external="EXTERNAL_BLIND_TEST"),
    )
    assert env.finalize_internal()["qualified"] is True
    assert env.promote_external() is False
    assert env.claims["external_validation"] is False
