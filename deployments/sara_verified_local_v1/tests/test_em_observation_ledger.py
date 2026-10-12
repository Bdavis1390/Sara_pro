import json

import pytest

from worldshepherd_sara.em_intelligence import EMObservation
from worldshepherd_sara.em_observation_ledger import EMObservationLedger


def _observation(observation_id: str, shift: float = 0.0) -> EMObservation:
    return EMObservation(
        observation_id=observation_id,
        observed_utc="2026-09-30T17:00:00Z",
        device_id="UC06-SIM",
        commanded_state="LOW_C",
        frequency_GHz=[9.2, 9.21],
        te_real=[0.9 + shift, 0.8 + shift],
        te_imag=[0.1, 0.2],
        tm_real=[0.01, 0.02],
        tm_imag=[0.03, 0.04],
        latent_coordinates=[0.1, 0.2, 0.3],
        provenance_hashes={"source": "sha256:" + "a" * 64},
    )


def test_ledger_appends_and_verifies_hash_chain(tmp_path):
    ledger = EMObservationLedger(tmp_path / "em-observations.jsonl")

    first = ledger.append(_observation("OBS-1"))
    second = ledger.append(_observation("OBS-2", shift=0.01))
    records = ledger.read_all()

    assert first.sequence == 1
    assert second.sequence == 2
    assert second.previous_record_digest == first.record_digest
    assert [record.observation.observation_id for record in records] == ["OBS-1", "OBS-2"]


def test_ledger_rejects_duplicate_observation_id(tmp_path):
    ledger = EMObservationLedger(tmp_path / "em-observations.jsonl")
    ledger.append(_observation("OBS-1"))

    with pytest.raises(ValueError, match="duplicate EM observation_id"):
        ledger.append(_observation("OBS-1", shift=0.02))


def test_ledger_rejects_inconsistent_channel_lengths(tmp_path):
    ledger = EMObservationLedger(tmp_path / "em-observations.jsonl")
    bad = _observation("OBS-BAD").model_copy(update={"te_real": [0.9]})

    with pytest.raises(ValueError, match="does not match frequency_GHz"):
        ledger.append(bad)


def test_ledger_detects_tampering(tmp_path):
    path = tmp_path / "em-observations.jsonl"
    ledger = EMObservationLedger(path)
    ledger.append(_observation("OBS-1"))

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["observation"]["device_id"] = "TAMPERED"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="observation digest mismatch"):
        ledger.read_all()
