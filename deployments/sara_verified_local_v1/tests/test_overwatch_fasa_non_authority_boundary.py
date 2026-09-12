from __future__ import annotations

import ast
import inspect
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

import worldshepherd_sara.fasa_runtime_gate as fasa_runtime_gate
from worldshepherd_sara.fasa_runtime_gate import FASAEchoExecutionReadiness
from worldshepherd_sara.overwatch_attestation_contract import OverwatchAttestationContract
from worldshepherd_sara.overwatch_provenance import OverwatchProvenanceReceipt
from worldshepherd_sara.overwatch_tripwire import OverwatchObservation


NOW = datetime(2026, 9, 12, 1, 20, tzinfo=timezone.utc)


def _observation() -> OverwatchObservation:
    return OverwatchObservation(
        observation_id="OBS-NON-AUTHORITY-1",
        action_id="ACTION-NON-AUTHORITY-1",
        monitor_id="OVERWATCH-INDEPENDENT-1",
        model_id="MODEL-1",
        model_version="v1",
        observed_at=NOW,
        signals=(),
    )


def test_fasa_runtime_gate_has_no_overwatch_attestation_or_provenance_import():
    """UNVERIFIED OVERWATCH evidence is not an execution-authority dependency."""

    source = inspect.getsource(fasa_runtime_gate)
    tree = ast.parse(source)
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden_suffixes = {
        "overwatch_attestation_contract",
        "overwatch_provenance",
        "overwatch_tripwire",
    }
    assert not any(
        module.split(".")[-1] in forbidden_suffixes
        for module in imported_modules
    )


def test_fasa_readiness_consumption_signature_has_no_overwatch_authority_parameter():
    parameters = inspect.signature(
        fasa_runtime_gate.consume_execution_readiness
    ).parameters

    assert set(parameters) == {"store", "readiness", "execution_id", "now"}
    assert "attestation" not in parameters
    assert "overwatch" not in parameters
    assert "monitor" not in parameters


def test_unverified_overwatch_attestation_cannot_validate_as_fasa_readiness():
    attestation = OverwatchAttestationContract(
        attestation_id="ATTEST-NON-AUTHORITY-1",
        observation=_observation(),
        issued_at=NOW,
        expires_at=NOW + timedelta(seconds=10),
        nonce="nonce-non-authority-0001",
    )

    with pytest.raises(ValidationError):
        FASAEchoExecutionReadiness.model_validate(
            attestation.model_dump(mode="json")
        )


def test_overwatch_provenance_receipt_cannot_validate_as_fasa_readiness():
    receipt = OverwatchProvenanceReceipt(
        observation_id="OBS-NON-AUTHORITY-2",
        provenance_event_id="SARA-EVENT-OVERWATCH-NON-AUTHORITY-2",
        decision_digest_sha256="a" * 64,
        echo_semantic_sha256="b" * 64,
        echo_delivery_count=1,
    )

    assert receipt.authorization_effect == "NONE"
    assert receipt.execution_effect_applied is False
    with pytest.raises(ValidationError):
        FASAEchoExecutionReadiness.model_validate(
            receipt.model_dump(mode="json")
        )
