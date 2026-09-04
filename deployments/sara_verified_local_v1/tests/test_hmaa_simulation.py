from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.hmaa import AssuranceDisposition, verify_chain
from worldshepherd_sara.hmaa_simulation import load_sil_steps, run_sil_scenario


FIXTURE = Path(__file__).parent.parent / "fixtures" / "hmaa_link_loss_scenario.json"


def test_link_loss_scenario_produces_verifiable_evidence_and_expected_dispositions():
    steps = load_sil_steps(json.loads(FIXTURE.read_text(encoding="utf-8")))
    result = run_sil_scenario(mission_id="SIM-LINK-LOSS-001", steps=steps)

    ok, errors = verify_chain(result.evidence_bundle.events)
    assert ok is True
    assert errors == []
    assert result.evidence_bundle.final_chain_hash
    assert len(result.steps) == 7
    assert result.disposition_counts[AssuranceDisposition.ALLOW.value] == 4
    assert result.disposition_counts[AssuranceDisposition.WARN.value] == 1
    assert result.disposition_counts[AssuranceDisposition.REVIEW.value] == 1
    assert result.disposition_counts[AssuranceDisposition.INDETERMINATE.value] == 1


def test_link_loss_scenario_records_reconnect_after_degraded_heartbeat():
    steps = load_sil_steps(json.loads(FIXTURE.read_text(encoding="utf-8")))
    result = run_sil_scenario(mission_id="SIM-LINK-LOSS-002", steps=steps)

    assert result.steps[3].event.event_type == "HEARTBEAT"
    assert result.steps[3].assessment.disposition == AssuranceDisposition.WARN
    assert result.steps[4].event.event_type == "STREAM_RECONNECT"
    assert result.steps[4].event.payload["attempt"] == 1


def test_scenario_rejects_empty_step_set():
    try:
        run_sil_scenario(mission_id="SIM-EMPTY", steps=[])
    except ValueError as exc:
        assert "at least one step" in str(exc)
    else:
        raise AssertionError("empty SIL scenario must be rejected")
