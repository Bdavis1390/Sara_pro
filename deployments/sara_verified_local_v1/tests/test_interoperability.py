from __future__ import annotations

import pytest

from worldshepherd_sara.interoperability import (
    ConformanceCheck,
    ConformanceState,
    InterfaceConformanceRecord,
    InterfaceContract,
)


def test_internal_conformance_pass_requires_all_checks_and_stays_non_certification_claim():
    contract = InterfaceContract(
        contract_id="IFACE-1",
        interface_name="Synthetic C2 Adapter",
        version="1",
        required_message_types=["track_update"],
        required_fields={"track_update":["track_id","timestamp","position"]},
    )
    record = InterfaceConformanceRecord(
        record_id="CONF-1",
        contract_digest=contract.digest(),
        implementation_id="adapter-1",
        implementation_digest="sha256:adapter",
        state=ConformanceState.INTERNAL_PASS,
        checks=[ConformanceCheck(check_id="C1", description="required fields present", passed=True, evidence_refs=["fixture://track-update"])],
    )
    assert "no platform acceptance" in record.claims_boundary().lower()


def test_external_certification_state_requires_authority_and_certificate():
    with pytest.raises(ValueError):
        InterfaceConformanceRecord(
            record_id="BAD",
            contract_digest="sha256:contract",
            implementation_id="adapter",
            implementation_digest="sha256:adapter",
            state=ConformanceState.EXTERNALLY_CERTIFIED,
        )
