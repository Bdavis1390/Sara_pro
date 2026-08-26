from __future__ import annotations

import pytest

from worldshepherd_sara.readiness import CapabilityReadinessRecord, ReadinessRung


def test_readiness_record_requires_explicit_evidence_for_every_supported_rung():
    record = CapabilityReadinessRecord(
        capability_id="CAP-APNT-SYNTH",
        capability_name="Synthetic APNT bounded awareness",
        highest_supported_rung=ReadinessRung.INTERNAL_SOFTWARE,
        evidence_refs={
            ReadinessRung.SCHEMA: ["qualification.py"],
            ReadinessRung.FIXTURE: ["WS-APNT-SYNTH-001"],
            ReadinessRung.INTERNAL_SOFTWARE: ["apnt_qualification_bundle"],
        },
        blocked_next_rung=ReadinessRung.SIMULATION,
        missing_evidence=["representative validated simulation"],
    )
    assert record.can_claim(ReadinessRung.INTERNAL_SOFTWARE) is True
    assert record.can_claim(ReadinessRung.PHYSICAL_LAB) is False
    assert record.next_rung() == ReadinessRung.SIMULATION


def test_readiness_record_rejects_skipped_or_implicit_rungs():
    with pytest.raises(ValueError):
        CapabilityReadinessRecord(
            capability_id="CAP-BAD",
            capability_name="Bad readiness claim",
            highest_supported_rung=ReadinessRung.PHYSICAL_LAB,
            evidence_refs={ReadinessRung.PHYSICAL_LAB: ["one-test"]},
        )
