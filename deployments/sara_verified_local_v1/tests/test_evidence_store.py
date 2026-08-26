from __future__ import annotations

import json

import pytest

from worldshepherd_sara.evidence_store import EvidenceIntegrityError, EvidenceStore
from worldshepherd_sara.qualification import canonical_digest


def _bundle() -> dict:
    value = {
        "requirement": {"id": "PRE-RD-TEST"},
        "evidence": [{"test_id": "T1", "result": "PASS"}],
        "claims_boundary": ["synthetic only"],
    }
    value["bundle_digest"] = canonical_digest(value)
    return value


def test_evidence_store_round_trips_hash_addressed_bundle(tmp_path):
    store = EvidenceStore(tmp_path / "evidence")
    bundle = _bundle()
    digest = store.put_bundle(bundle)
    assert digest == bundle["bundle_digest"]
    assert store.get_bundle(digest) == bundle
    assert store.verify_all() == {digest: True}


def test_evidence_store_rejects_bad_declared_digest(tmp_path):
    store = EvidenceStore(tmp_path / "evidence")
    bundle = _bundle()
    bundle["bundle_digest"] = "sha256:" + "0" * 64
    with pytest.raises(EvidenceIntegrityError):
        store.put_bundle(bundle)


def test_evidence_store_detects_post_write_tampering(tmp_path):
    store = EvidenceStore(tmp_path / "evidence")
    bundle = _bundle()
    digest = store.put_bundle(bundle)
    path = store.root / f"{digest.split(':', 1)[1]}.json"
    tampered = json.loads(path.read_text())
    tampered["evidence"][0]["result"] = "FAIL"
    path.write_text(json.dumps(tampered))
    with pytest.raises(EvidenceIntegrityError):
        store.get_bundle(digest)
    assert store.verify_all() == {digest: False}
