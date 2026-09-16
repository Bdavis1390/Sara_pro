from datetime import timedelta

import pytest

from qcrypto_external_signer import (
    CustodyError,
    CustodyLedger,
    CustodyPolicy,
    ExternalCustodyService,
)
from test_custody import fixture


def strict_service(tmp_path, signer, human_public):
    return ExternalCustodyService(
        ledger=CustodyLedger(tmp_path / "strict-ledger.json"),
        signer=signer,
        policy=CustodyPolicy.testnet_reference(),
        trusted_human_keys={"HUMAN-MLDSA65-TEST": human_public},
    )


def test_public_service_accepts_exact_synthetic_request(tmp_path):
    request, signer, human_public, now = fixture()
    receipt = strict_service(tmp_path, signer, human_public).execute_release(
        request, now=now + timedelta(seconds=1)
    )
    assert receipt["state"] == "SIGNED_CUSTODY_RELEASE_ATTESTATION"


def test_public_service_rejects_unknown_top_level_fields(tmp_path):
    request, signer, human_public, now = fixture()
    request["unexpected"] = "value"
    with pytest.raises(CustodyError, match="surface mismatch"):
        strict_service(tmp_path, signer, human_public).execute_release(
            request, now=now + timedelta(seconds=1)
        )


def test_public_service_rejects_nested_private_key_shaped_fields(tmp_path):
    request, signer, human_public, now = fixture()
    request["preflight"]["private_key_pem"] = "forbidden"
    with pytest.raises(CustodyError, match="secret/private-key-shaped"):
        strict_service(tmp_path, signer, human_public).execute_release(
            request, now=now + timedelta(seconds=1)
        )
