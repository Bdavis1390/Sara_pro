from __future__ import annotations

import json

import pytest

from worldshepherd_sara.assurance_evidence_bundle import build_assurance_evidence_bundle
from worldshepherd_sara.assurance_evidence_portable import (
    build_portable_assurance_package,
    load_portable_assurance_package,
    serialize_portable_assurance_package,
    verify_portable_assurance_package,
)


SHA_A = "a" * 64
SHA_B = "b" * 64


def _bundle(bundle_id: str, predecessor: str | None = None):
    return build_assurance_evidence_bundle(
        bundle_id=bundle_id,
        created_utc="2026-09-12T21:00:00+00:00",
        source_ref="synthetic://assurance-test",
        readiness="READY",
        degraded_metrics=[],
        baseline_digest=SHA_A,
        active_configuration_digest=SHA_B,
        authorization_state="APPROVED",
        reviewer="reviewer-1",
        replay_events=[{"sequence": 1, "state": "READY"}],
        audit_records=[{"event": "configuration_reviewed", "actor": "reviewer-1"}],
        predecessor_manifest_digest=predecessor,
    )


def test_portable_package_round_trips_deterministically():
    first = _bundle("bundle-1")
    second = _bundle("bundle-2", predecessor=first.manifest_digest)
    package = build_portable_assurance_package(
        package_id="portable-1",
        created_utc="2026-09-12T21:05:00+00:00",
        bundles=[first, second],
    )

    serialized_a = serialize_portable_assurance_package(package)
    serialized_b = serialize_portable_assurance_package(package)

    assert serialized_a == serialized_b
    loaded = load_portable_assurance_package(serialized_a)
    assert loaded == package
    assert verify_portable_assurance_package(loaded)


def test_portable_package_rejects_bundle_tampering_on_import():
    first = _bundle("bundle-1")
    package = build_portable_assurance_package(
        package_id="portable-1",
        created_utc="2026-09-12T21:05:00+00:00",
        bundles=[first],
    )
    payload = json.loads(serialize_portable_assurance_package(package))
    payload["bundles"][0]["authorization_state"] = "DENIED"

    with pytest.raises(ValueError, match="failed verification"):
        load_portable_assurance_package(json.dumps(payload))


def test_portable_package_rejects_broken_predecessor_chain():
    first = _bundle("bundle-1")
    second = _bundle("bundle-2", predecessor="c" * 64)

    with pytest.raises(ValueError, match="invalid assurance evidence chain"):
        build_portable_assurance_package(
            package_id="portable-1",
            created_utc="2026-09-12T21:05:00+00:00",
            bundles=[first, second],
        )
