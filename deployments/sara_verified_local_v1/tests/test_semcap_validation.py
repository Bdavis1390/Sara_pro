import pytest
from worldshepherd_sara.semcap import SemcapMeasurements


def make(**changes):
    d = dict(baseline_bits=100, semantic_bits=10, baseline_mission_utility=1.0,
        semantic_mission_utility=.9, latency_ms=1, power_w=1,
        missed_critical_events=0, false_semantic_selections=0,
        reconstruction_fidelity=1.0, provenance_completeness=1.0)
    d.update(changes)
    return SemcapMeasurements(**d)


@pytest.mark.parametrize("changes", [
    {"semantic_bits": -1}, {"latency_ms": -1}, {"power_w": -1},
    {"missed_critical_events": -1}, {"false_semantic_selections": -1},
    {"reconstruction_fidelity": 1.1}, {"provenance_completeness": -0.1},
])
def test_invalid_measurements_rejected(changes):
    with pytest.raises(ValueError):
        make(**changes).validate()
