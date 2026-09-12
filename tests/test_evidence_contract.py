import copy
import json
from pathlib import Path

import pytest

from worldshepherd_sara.evidence_contract import (
    EvidenceValidationError,
    validate_claim_record,
    validate_experiment_record,
)

ROOT = Path(__file__).resolve().parents[1]


def load_payload(name: str):
    return json.loads((ROOT / "payloads" / name).read_text(encoding="utf-8"))


def test_valid_experiment_fixture():
    payload = load_payload("experiment_record.valid.json")
    assert validate_experiment_record(payload)["experiment_id"] == "WS-EXP-20260817-001"


def test_valid_claim_fixture():
    payload = load_payload("claim_record.valid.json")
    assert validate_claim_record(payload)["claim_id"] == "WS-CLM-001"


def test_anomalous_residual_cannot_claim_independent_reproduction_without_replication():
    payload = copy.deepcopy(load_payload("claim_record.valid.json"))
    payload["claim_class"] = "ANOMALOUS_RESIDUAL"
    payload["confidence_status"] = "INDEPENDENTLY_REPRODUCED"
    payload["replication_ids"] = []

    with pytest.raises(EvidenceValidationError, match="requires replication_ids"):
        validate_claim_record(payload)


def test_unknown_evidence_class_rejected():
    payload = copy.deepcopy(load_payload("experiment_record.valid.json"))
    payload["evidence_class"] = ["MEASURED", "MAGIC"]

    with pytest.raises(EvidenceValidationError, match="unsupported values"):
        validate_experiment_record(payload)


def test_unknown_glob_operator_rejected():
    payload = copy.deepcopy(load_payload("experiment_record.valid.json"))
    payload["glob"]["operator"] = "PZ"

    with pytest.raises(EvidenceValidationError, match="glob.operator"):
        validate_experiment_record(payload)
