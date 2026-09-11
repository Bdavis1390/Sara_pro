from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from worldshepherd_sara.overwatch_attestation_contract import (
    OVERWATCH_ATTESTATION_CONTRACT_SCHEMA,
    OverwatchAttestationContract,
)
from worldshepherd_sara.overwatch_tripwire import (
    OverwatchObservation,
    OverwatchSignal,
)


NOW = datetime(2026, 9, 11, 22, 50, tzinfo=timezone.utc)


def _observation() -> OverwatchObservation:
    return OverwatchObservation(
        observation_id="OBS-CONTRACT-1",
        action_id="ACTION-CONTRACT-1",
        monitor_id="OVERWATCH-CONTRACT-1",
        model_id="MODEL-1",
        model_version="v1",
        observed_at=NOW,
        signals=(OverwatchSignal.RESOURCE_CEILING_BREACH,),
    )


def _contract(**overrides) -> OverwatchAttestationContract:
    values = {
        "attestation_id": "ATTEST-CONTRACT-1",
        "observation": _observation(),
        "issued_at": NOW,
        "expires_at": NOW + timedelta(seconds=20),
        "nonce": "contract-nonce-0001",
    }
    values.update(overrides)
    return OverwatchAttestationContract(**values)


def test_contract_is_explicitly_unverified_and_non_authorizing():
    contract = _contract()

    assert contract.schema == OVERWATCH_ATTESTATION_CONTRACT_SCHEMA
    assert contract.verification_status == "UNVERIFIED"
    assert contract.authorization_effect == "NONE"
    assert contract.execution_effect_applied is False


def test_contract_rejects_attempts_to_claim_verification_or_effects():
    with pytest.raises(ValidationError):
        _contract(verification_status="VERIFIED")

    with pytest.raises(ValidationError):
        _contract(authorization_effect="ALLOW")

    with pytest.raises(ValidationError):
        _contract(execution_effect_applied=True)


def test_contract_requires_timezone_aware_window():
    naive = datetime(2026, 9, 11, 22, 50)

    with pytest.raises(ValidationError, match="issued_at must be timezone-aware"):
        _contract(issued_at=naive, expires_at=NOW + timedelta(seconds=20))

    with pytest.raises(ValidationError, match="expires_at must be timezone-aware"):
        _contract(issued_at=NOW, expires_at=naive + timedelta(seconds=20))


def test_contract_rejects_nonpositive_and_overlong_windows():
    with pytest.raises(ValidationError, match="expires_at must be after issued_at"):
        _contract(expires_at=NOW)

    with pytest.raises(ValidationError, match="lifetime exceeds 30 seconds"):
        _contract(expires_at=NOW + timedelta(seconds=31))


def test_contract_forbids_extra_fields():
    with pytest.raises(ValidationError):
        _contract(signature="not-part-of-phase-8b-contract")


def test_contract_reuses_strict_observation_validation():
    with pytest.raises(ValidationError, match="duplicates"):
        OverwatchObservation(
            observation_id="OBS-DUP",
            action_id="ACTION-DUP",
            monitor_id="OVERWATCH-CONTRACT-1",
            model_id="MODEL-1",
            model_version="v1",
            observed_at=NOW,
            signals=(
                OverwatchSignal.SANDBOX_ESCAPE,
                OverwatchSignal.SANDBOX_ESCAPE,
            ),
        )


def test_contract_is_frozen_after_creation():
    contract = _contract()

    with pytest.raises(ValidationError):
        contract.verification_status = "VERIFIED"
