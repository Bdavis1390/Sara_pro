from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.prime_configuration_custody import REQUALIFICATION_CHECKS
from worldshepherd_sara.prime_sentinel_authorization import (
    PrimeSentinelAuthorizationAssertion,
    PrimeSentinelVerifier,
    canonical_authorization_message,
)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _configure_sentinel(client):
    private = Ed25519PrivateKey.generate()
    client.app.state.prime_sentinel_verifier = PrimeSentinelVerifier(
        public_keys_b64url={"PS-K1": _b64url(private.public_key().public_bytes_raw())}
    )
    return private


def _signed_authorization(private: Ed25519PrivateKey, *, authorization_id: str = "AUTH-SUPERSEDE-001") -> dict[str, object]:
    now = datetime.now(timezone.utc)
    assertion = PrimeSentinelAuthorizationAssertion(
        key_id="PS-K1",
        authorization_id=authorization_id,
        prime_id="PRIME-001",
        target_environment="SPACE",
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
        nonce=f"nonce-{authorization_id}-0123456789abcdef",
        signature_b64url=_b64url(b"0" * 64),
    )
    signature = private.sign(canonical_authorization_message(assertion))
    return assertion.model_copy(
        update={"signature_b64url": _b64url(signature)}
    ).model_dump(mode="json")


def _create_quarantined_requalified_passport(client, admin: str):
    created = client.post(
        "/admin/prime/PRIME-001/passport",
        headers=auth(admin),
        json={"hardware_revision": "HW-A", "software_revision": "SW-A"},
    )
    assert created.status_code == 201
    mission = client.post(
        "/admin/prime/PRIME-001/mission-complete",
        headers=auth(admin),
        json={"environment": "SUBTERRA"},
    )
    assert mission.status_code == 200
    evidence = client.patch(
        "/admin/prime/PRIME-001/requalification",
        headers=auth(admin),
        json={"completed_checks": list(REQUALIFICATION_CHECKS)},
    )
    assert evidence.status_code == 200


def _qualified_space_pack() -> dict[str, object]:
    return {
        "pack": {
            "pack_id": "SPACE-PACK-001",
            "target_environment": "SPACE",
            "authenticated": True,
            "compatible_with_prime": True,
            "target_environment_qualification_valid": True,
        }
    }


def test_requalification_evidence_change_supersedes_pending_authorization_atomically(client, tokens):
    _, admin = tokens
    private = _configure_sentinel(client)
    _create_quarantined_requalified_passport(client, admin)

    authorized = client.post(
        "/admin/prime/PRIME-001/requalification/authorize",
        headers=auth(admin),
        json=_signed_authorization(private),
    )
    assert authorized.status_code == 200
    assert authorized.json()["passport"]["custody"]["requalification_release_authorization_id"] == "AUTH-SUPERSEDE-001"

    changed = client.patch(
        "/admin/prime/PRIME-001/requalification",
        headers=auth(admin),
        json={
            "completed_checks": list(REQUALIFICATION_CHECKS),
            "evidence_refs": ["ECHO:REQUAL:CHANGED:001"],
        },
    )
    assert changed.status_code == 200
    body = changed.json()
    assert body["passport"]["custody"]["requalification_release_authorization_id"] is None
    assert body["provenance"]["details"]["superseded_authorization_id"] == "AUTH-SUPERSEDE-001"

    registry = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    record = registry["PRIME_SENTINEL_AUTHORIZATIONS"]["AUTH-SUPERSEDE-001"]
    assert record["status"] == "SUPERSEDED"
    assert record["superseded_reason"] == "REQUALIFICATION_EVIDENCE_CHANGED"
    assert record["superseded_transition_id"] == body["provenance"]["transition_id"]

    blocked = client.post(
        "/admin/prime/PRIME-001/activate-pack",
        headers=auth(admin),
        json=_qualified_space_pack(),
    )
    assert blocked.status_code == 409
    assert blocked.json()["disposition"] == "REQUALIFICATION_REQUIRED"


def test_new_mission_supersedes_pending_authorization_and_preserves_quarantine(client, tokens):
    _, admin = tokens
    private = _configure_sentinel(client)
    _create_quarantined_requalified_passport(client, admin)

    authorized = client.post(
        "/admin/prime/PRIME-001/requalification/authorize",
        headers=auth(admin),
        json=_signed_authorization(private, authorization_id="AUTH-MISSION-001"),
    )
    assert authorized.status_code == 200

    mission = client.post(
        "/admin/prime/PRIME-001/mission-complete",
        headers=auth(admin),
        json={"environment": "HADAL", "evidence_refs": ["ECHO:MISSION:HADAL:NEW"]},
    )
    assert mission.status_code == 200
    body = mission.json()
    custody = body["passport"]["custody"]
    assert custody["state"] == "QUARANTINED_FOR_REQUALIFICATION"
    assert custody["requalification_release_authorization_id"] is None
    assert body["provenance"]["details"]["superseded_authorization_id"] == "AUTH-MISSION-001"

    registry = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    record = registry["PRIME_SENTINEL_AUTHORIZATIONS"]["AUTH-MISSION-001"]
    assert record["status"] == "SUPERSEDED"
    assert record["superseded_reason"] == "MISSION_COMPLETED"
    assert record["superseded_transition_id"] == body["provenance"]["transition_id"]


def test_removed_signing_key_blocks_activation_of_previously_verified_authorization(client, tokens):
    _, admin = tokens
    private = _configure_sentinel(client)
    _create_quarantined_requalified_passport(client, admin)

    authorized = client.post(
        "/admin/prime/PRIME-001/requalification/authorize",
        headers=auth(admin),
        json=_signed_authorization(private, authorization_id="AUTH-ROTATE-001"),
    )
    assert authorized.status_code == 200

    replacement_private = Ed25519PrivateKey.generate()
    client.app.state.prime_sentinel_verifier = PrimeSentinelVerifier(
        public_keys_b64url={
            "PS-K2": _b64url(replacement_private.public_key().public_bytes_raw())
        }
    )

    blocked = client.post(
        "/admin/prime/PRIME-001/activate-pack",
        headers=auth(admin),
        json=_qualified_space_pack(),
    )
    assert blocked.status_code == 409
    assert blocked.json()["disposition"] == "REQUALIFICATION_REQUIRED"
    assert any("no longer configured" in reason for reason in blocked.json()["reasons"])

    passport = client.get(
        "/admin/prime/PRIME-001/passport", headers=auth(admin)
    ).json()["passport"]
    assert passport["custody"]["state"] == "QUARANTINED_FOR_REQUALIFICATION"
    assert passport["installed_pack"] is None
