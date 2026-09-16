from copy import deepcopy
from datetime import timedelta

import pytest

from qcrypto_external_signer import (
    CustodyConflict,
    CustodyIndeterminate,
    CustodyLedger,
    CustodyPolicy,
    ExternalCustodyService,
    FailingAfterInvocationSigner,
)
from tests.test_custody import fixture


def service(tmp_path, signer, human_public):
    return ExternalCustodyService(
        ledger=CustodyLedger(tmp_path / "durable-ledger.json"),
        signer=signer,
        policy=CustodyPolicy.testnet_reference(),
        trusted_human_keys={"HUMAN-MLDSA65-TEST": human_public},
    )


def test_exact_signed_receipt_is_retrievable_after_approval_and_intent_expiry(tmp_path):
    request, signer, human_public, now = fixture()
    first = service(tmp_path, signer, human_public).execute_release(
        request, now=now + timedelta(seconds=1)
    )
    restarted = service(tmp_path, signer, human_public)
    after_expiry = restarted.execute_release(
        deepcopy(request), now=now + timedelta(hours=1)
    )
    assert after_expiry == first
    assert signer.invocation_count == 1


def test_changed_envelope_after_expiry_conflicts_without_new_signer_invocation(tmp_path):
    request, signer, human_public, now = fixture()
    svc = service(tmp_path, signer, human_public)
    svc.execute_release(request, now=now + timedelta(seconds=1))
    changed = deepcopy(request)
    changed["unsigned_payload_b64url"] = changed["unsigned_payload_b64url"] + "A"
    with pytest.raises(CustodyConflict, match="changed exact envelope"):
        service(tmp_path, signer, human_public).execute_release(
            changed, now=now + timedelta(hours=1)
        )
    assert signer.invocation_count == 1


def test_indeterminate_request_remains_blocked_after_original_approval_expiry(tmp_path):
    signer = FailingAfterInvocationSigner()
    request, signer, human_public, now = fixture(signer=signer)
    svc = service(tmp_path, signer, human_public)
    with pytest.raises(CustodyIndeterminate):
        svc.execute_release(request, now=now + timedelta(seconds=1))
    with pytest.raises(CustodyIndeterminate, match="human reconciliation"):
        service(tmp_path, signer, human_public).execute_release(
            deepcopy(request), now=now + timedelta(hours=1)
        )
    assert signer.invocation_count == 1
