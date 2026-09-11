from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldshepherd_sara.fasa import (
    CapabilityLevel,
    CapabilityRegistryEntry,
    FrontierActionCandidate,
    FrontierDisposition,
    FrontierSafetyPolicy,
    evaluate_frontier_action,
)


def test_policy_configuration_cannot_enable_f5_in_ws_fasa_v1():
    with pytest.raises(ValidationError):
        FrontierSafetyPolicy(
            policy_id="WS-FASA-001",
            allow_f5_when_all_gates_pass=True,
        )


def test_f5_is_denied_even_when_all_other_candidate_gates_are_satisfied():
    registry = CapabilityRegistryEntry(
        model_id="model-A",
        model_version="1.0",
        assessed_level=CapabilityLevel.F5,
        maximum_authorized_level=CapabilityLevel.F5,
        evaluation_id="EVAL-F5-TEST",
        evaluation_current=True,
    )
    candidate = FrontierActionCandidate(
        action_id="ACT-F5-TEST",
        model_id="model-A",
        model_version="1.0",
        capability_level=CapabilityLevel.F5,
        reversible=True,
        human_approval_present=True,
        safety_case_current=True,
        independent_review_current=True,
        provenance_enabled=True,
        overwatch_enabled=True,
    )
    disposition, reasons = evaluate_frontier_action(
        candidate,
        registry,
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
    )
    assert disposition == FrontierDisposition.DENIED
    assert any("F5 execution is disabled" in reason for reason in reasons)
