from __future__ import annotations

import pytest

from worldshepherd_sara.apnt_interface_contract import (
    AuthoritativeInterfaceContract,
    ContractPntAdapter,
)

SPEC_DIGEST = "sha256:" + "a" * 64


def test_apnt_contract_cannot_enable_without_required_mapping_and_validation():
    with pytest.raises(ValueError):
        AuthoritativeInterfaceContract(
            contract_id="ASPN-TEST",
            interface_name="Authoritative test interface",
            version="1",
            authoritative_spec_ref="spec://authoritative-test",
            authoritative_spec_digest=SPEC_DIGEST,
            field_mapping={"source_id": "id"},
            validated_fields=["source_id"],
            enabled=True,
        )


def test_contract_adapter_normalizes_only_after_explicit_contract_enablement():
    contract = AuthoritativeInterfaceContract(
        contract_id="ASPN-TEST",
        interface_name="Authoritative test interface",
        version="1",
        authoritative_spec_ref="spec://authoritative-test",
        authoritative_spec_digest=SPEC_DIGEST,
        field_mapping={
            "source_id": "id",
            "source_kind": "kind",
            "health": "status",
            "confidence": "confidence_value",
            "observed_utc": "timestamp",
        },
        validated_fields=["source_id", "source_kind", "health", "confidence", "observed_utc"],
        enabled=True,
    )
    normalized = ContractPntAdapter(contract).normalize(
        {"id": "source-1", "kind": "GNSS", "status": "NOMINAL", "confidence_value": 0.9, "timestamp": "2026-08-26T00:00:00Z"}
    )
    assert normalized.source_id == "source-1"
    assert normalized.attributes["contract_id"] == "ASPN-TEST"
    assert normalized.attributes["contract_digest"].startswith("sha256:")


def test_disabled_contract_fails_closed():
    contract = AuthoritativeInterfaceContract(
        contract_id="DISABLED",
        interface_name="Disabled interface",
        version="1",
        authoritative_spec_ref="spec://disabled",
        authoritative_spec_digest=SPEC_DIGEST,
    )
    with pytest.raises(ValueError):
        ContractPntAdapter(contract)
