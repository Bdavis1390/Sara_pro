import pytest

from baros.evidence_graph import EvidenceDependencyGraph, EvidenceNode


def graph_with_measurement(*, measurement_valid=True, measurement_quarantined=False):
    nodes = (
        EvidenceNode("raw-dose", "raw_evidence", valid=measurement_valid, quarantined=measurement_quarantined),
        EvidenceNode("analysis-dose", "analysis"),
        EvidenceNode("locked-config", "configuration"),
        EvidenceNode("claim-g6", "claim"),
        EvidenceNode("claim-g7", "claim"),
    )
    deps = {
        "analysis-dose": ("raw-dose", "locked-config"),
        "claim-g6": ("analysis-dose",),
        "claim-g7": ("claim-g6",),
    }
    return EvidenceDependencyGraph(nodes, deps)


def test_valid_dependency_chain_allows_claim():
    graph = graph_with_measurement()
    assert graph.assess_claim("claim-g6").eligible is True
    assert graph.assess_claim("claim-g7").eligible is True


def test_invalid_raw_measurement_invalidates_downstream_claims():
    graph = graph_with_measurement(measurement_valid=False)
    assessment = graph.assess_claim("claim-g7")
    assert assessment.eligible is False
    assert "raw-dose" in assessment.invalid_dependencies
    assert graph.blast_radius(("raw-dose",)) == ("claim-g6", "claim-g7")


def test_quarantined_measurement_blocks_claim():
    graph = graph_with_measurement(measurement_valid=False, measurement_quarantined=True)
    assessment = graph.assess_claim("claim-g6")
    assert assessment.eligible is False
    assert "raw-dose" in assessment.quarantined_dependencies


def test_changed_configuration_has_transitive_blast_radius():
    graph = graph_with_measurement()
    assert graph.blast_radius(("locked-config",)) == ("claim-g6", "claim-g7")


def test_cycles_are_rejected():
    nodes = (
        EvidenceNode("a", "analysis"),
        EvidenceNode("b", "claim"),
    )
    with pytest.raises(ValueError, match="cycle"):
        EvidenceDependencyGraph(nodes, {"a": ("b",), "b": ("a",)})


def test_unknown_dependency_is_rejected():
    with pytest.raises(ValueError, match="unknown dependencies"):
        EvidenceDependencyGraph(
            (EvidenceNode("claim", "claim"),),
            {"claim": ("missing",)},
        )


def test_quarantined_node_cannot_be_marked_valid():
    with pytest.raises(ValueError, match="quarantined evidence"):
        EvidenceDependencyGraph(
            (EvidenceNode("bad", "raw_evidence", valid=True, quarantined=True),),
            {},
        )
