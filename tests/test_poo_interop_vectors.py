import json
from pathlib import Path

from security.poo.coc_guard import COCEvidence, coc_digest
from security.poo.ownership_guard import OwnershipEvidence, ownership_digest
from security.poo.recovery_guard import RecoveryEvidence, recovery_digest
from security.poo.transfer_guard import TransferEvidence, transfer_digest


VECTOR_PATH = Path("security/poo/interop/poo_v3_vectors.json")


def _without_schema(payload):
    value = dict(payload)
    value.pop("schema", None)
    return value


def _actual_digest(vector):
    payload = _without_schema(vector["payload"])
    kind = vector["kind"]
    if kind == "coc":
        return coc_digest(COCEvidence(**payload))
    if kind == "poo":
        return ownership_digest(OwnershipEvidence(**payload))
    if kind == "transfer":
        return transfer_digest(TransferEvidence(**payload))
    if kind == "recovery":
        return recovery_digest(RecoveryEvidence(**payload))
    raise AssertionError(f"unsupported vector kind: {kind}")


def test_shared_vectors_match_python_protocol_implementation():
    document = json.loads(VECTOR_PATH.read_text())
    assert document["schema"] == "WS-POO-INTEROP-VECTORS-V1"
    assert document["claim_boundary"] == (
        "INTERNAL_SECOND_LANGUAGE_REPRODUCTION_NOT_INDEPENDENT_EXTERNAL_VALIDATION"
    )
    assert len(document["vectors"]) >= 7
    for vector in document["vectors"]:
        assert _actual_digest(vector) == vector["expected_sha256"], vector["name"]


def test_vector_chain_binds_coc_into_poo_transfer_and_recovery():
    document = json.loads(VECTOR_PATH.read_text())
    by_name = {item["name"]: item for item in document["vectors"]}

    assert by_name["genesis-poo"]["payload"]["coc_reference"] == by_name["genesis-coc"]["expected_sha256"]
    assert by_name["transfer-coc"]["payload"]["previous_coc_digest"] == by_name["genesis-coc"]["expected_sha256"]
    assert by_name["transfer-intent"]["payload"]["prior_poo_digest"] == by_name["genesis-poo"]["expected_sha256"]
    assert by_name["transfer-intent"]["payload"]["recipient_coc_reference"] == by_name["transfer-coc"]["expected_sha256"]
    assert by_name["transferred-poo"]["payload"]["previous_poo_digest"] == by_name["genesis-poo"]["expected_sha256"]
    assert by_name["transferred-poo"]["payload"]["coc_reference"] == by_name["transfer-coc"]["expected_sha256"]
    assert by_name["recovery-coc"]["payload"]["previous_coc_digest"] == by_name["transfer-coc"]["expected_sha256"]
    assert by_name["recovery-intent"]["payload"]["prior_poo_digest"] == by_name["transferred-poo"]["expected_sha256"]
    assert by_name["recovery-intent"]["payload"]["recovery_coc_reference"] == by_name["recovery-coc"]["expected_sha256"]
