from __future__ import annotations

from worldshepherd_sara.cbm_twin import (
    ExpectedEnvelope,
    TelemetrySample,
    evaluate_series,
    health_graph,
)


def test_cbm_twin_flags_only_envelope_deviation_and_preserves_source_lineage():
    envelopes = {
        "temperature_c": ExpectedEnvelope(metric="temperature_c", minimum=20.0, maximum=80.0, units="C")
    }
    samples = [
        TelemetrySample(sample_id="S1", asset_id="pump-1", metric="temperature_c", value=60.0, t_seconds=0, source_ref="sensor://temp-1"),
        TelemetrySample(sample_id="S2", asset_id="pump-1", metric="temperature_c", value=90.0, t_seconds=10, source_ref="sensor://temp-1"),
    ]
    findings = evaluate_series(samples, envelopes)
    assert [finding.status for finding in findings] == ["NOMINAL", "HIGH"]
    assert findings[1].deviation == 10.0
    graph = health_graph(graph_id="CBM-SYNTH-1", samples=samples, findings=findings)
    assert {edge.relation for edge in graph.edges} == {"supports_health_finding"}
    assert any(node.source_ref == "sensor://temp-1" for node in graph.nodes)
