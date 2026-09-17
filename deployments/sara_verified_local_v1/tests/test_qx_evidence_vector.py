from worldshepherd_sara.qx_evidence import EvidenceVector


def test_evidence_axes_are_independent():
    v = EvidenceVector(physical_performance="NONE", assurance_tevv="INTERNAL_REPRODUCIBLE_TEST", replication_external="NONE")
    assert v.assurance_tevv != "NONE"
    assert v.physical_performance == "NONE"
    assert v.replication_external == "NONE"
