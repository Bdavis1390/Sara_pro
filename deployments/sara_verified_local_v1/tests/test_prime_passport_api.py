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


def _signed_authorization(private: Ed25519PrivateKey, **overrides) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    values = {
        "key_id": "PS-K1",
        "authorization_id": "AUTH-REQUAL-001",
        "prime_id": "PRIME-001",
        "target_environment": "SPACE",
        "issued_at": now,
        "expires_at": now + timedelta(minutes=5),
        "nonce": "nonce-0123456789abcdef",
        "signature_b64url": _b64url(b"0" * 64),
    }
    values.update(overrides)
    assertion = PrimeSentinelAuthorizationAssertion(**values)
    signature = private.sign(canonical_authorization_message(assertion))
    return assertion.model_copy(
        update={"signature_b64url": _b64url(signature)}
    ).model_dump(mode="json")


def _qualified_space_pack() -> dict[str, object]:
    return {
        "pack": {
            "pack_id": "SPACE-PACK-001",
            "target_environment": "SPACE",
            "authenticated": True,
            "compatible_with_prime": True,
            "target_environment_qualification_valid": True,
        },
        "evidence_refs": ["ECHO:PACK:SPACE:001"],
    }


def _create_passport(client, admin: str):
    return client.post(
        "/admin/prime/PRIME-001/passport",
        headers=auth(admin),
        json={
            "hardware_revision": "HW-A",
            "software_revision": "SW-A",
            "evidence_refs": ["ECHO:BUILD:001"],
        },
    )


def test_prime_passport_endpoints_are_admin_only(client, tokens):
    relay, _ = tokens
    response = client.get(
        "/admin/prime/PRIME-001/passport",
        headers=auth(relay),
    )
    assert response.status_code == 403


def test_signed_sentinel_quarantine_requalification_activation_lifecycle(client, tokens):
    _, admin = tokens
    private = _configure_sentinel(client)

    created = _create_passport(client, admin)
    assert created.status_code == 201
    assert created.json()["passport"]["custody"]["state"] == "READY"

    mission = client.post(
        "/admin/prime/PRIME-001/mission-complete",
        headers=auth(admin),
        json={"environment": "HADAL", "evidence_refs": ["ECHO:MISSION:HADAL:001"]},
    )
    assert mission.status_code == 200
    assert mission.json()["passport"]["custody"]["state"] == "QUARANTINED_FOR_REQUALIFICATION"

    evidence = client.patch(
        "/admin/prime/PRIME-001/requalification",
        headers=auth(admin),
        json={
            "completed_checks": list(REQUALIFICATION_CHECKS),
            "evidence_refs": ["ECHO:REQUAL:001"],
        },
    )
    assert evidence.status_code == 200

    bypass = client.patch(
        "/admin/prime/PRIME-001/requalification",
        headers=auth(admin),
        json={
            "completed_checks": list(REQUALIFICATION_CHECKS),
            "release_authorization_id": "UNVERIFIED-BYPASS",
        },
    )
    assert bypass.status_code == 422

    blocked = client.post(
        "/admin/prime/PRIME-001/activate-pack",
        headers=auth(admin),
        json=_qualified_space_pack(),
    )
    assert blocked.status_code == 409
    assert blocked.json()["disposition"] == "REQUALIFICATION_REQUIRED"

    assertion = _signed_authorization(private)
    authorized = client.post(
        "/admin/prime/PRIME-001/requalification/authorize",
        headers=auth(admin),
        json=assertion,
    )
    assert authorized.status_code == 200
    custody = authorized.json()["passport"]["custody"]
    assert custody["requalification_release_authorization_id"] == "AUTH-REQUAL-001"
    assert custody["requalification_release_target_environment"] == "SPACE"
    assert custody["requalification_release_key_id"] == "PS-K1"

    replay = client.post(
        "/admin/prime/PRIME-001/requalification/authorize",
        headers=auth(admin),
        json=assertion,
    )
    assert replay.status_code == 403

    activated = client.post(
        "/admin/prime/PRIME-001/activate-pack",
        headers=auth(admin),
        json=_qualified_space_pack(),
    )
    assert activated.status_code == 200
    body = activated.json()
    assert body["disposition"] == "ACTIVATION_ALLOWED"
    assert body["passport"]["custody"]["state"] == "READY"
    assert body["passport"]["custody"]["requalification_release_authorization_id"] is None
    assert body["passport"]["installed_pack"]["pack_id"] == "SPACE-PACK-001"

    registry = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    auth_record = registry["PRIME_SENTINEL_AUTHORIZATIONS"]["AUTH-REQUAL-001"]
    assert auth_record["status"] == "CONSUMED"
    assert auth_record["consumed_transition_id"] == body["provenance"]["transition_id"]

    audit = client.get("/v1/audit?limit=100", headers=auth(admin)).json()["records"]
    assert any(
        item.get("event") == "prime_sentinel_authorization_rejected"
        for item in audit
    )
    assert any(
        item.get("event") == "prime_custody_provenance"
        and item["payload"].get("action") == "REQUALIFICATION_AUTHORIZATION_VERIFIED"
        for item in audit
    )


def test_tampered_signed_assertion_is_rejected_and_passport_remains_quarantined(client, tokens):
    _, admin = tokens
    private = _configure_sentinel(client)
    assert _create_passport(client, admin).status_code == 201
    assert client.post(
        "/admin/prime/PRIME-001/mission-complete",
        headers=auth(admin),
        json={"environment": "SUBTERRA"},
    ).status_code == 200
    assert client.patch(
        "/admin/prime/PRIME-001/requalification",
        headers=auth(admin),
        json={"completed_checks": list(REQUALIFICATION_CHECKS)},
    ).status_code == 200

    assertion = _signed_authorization(private)
    assertion["target_environment"] = "AERO"
    rejected = client.post(
        "/admin/prime/PRIME-001/requalification/authorize",
        headers=auth(admin),
        json=assertion,
    )
    assert rejected.status_code == 403
    passport = client.get(
        "/admin/prime/PRIME-001/passport", headers=auth(admin)
    ).json()["passport"]
    assert passport["custody"]["state"] == "QUARANTINED_FOR_REQUALIFICATION"
    assert passport["custody"]["requalification_release_authorization_id"] is None


def test_authorization_route_fails_closed_when_no_public_keys_are_configured(client, tokens):
    _, admin = tokens
    private = Ed25519PrivateKey.generate()
    assert _create_passport(client, admin).status_code == 201
    response = client.post(
        "/admin/prime/PRIME-001/requalification/authorize",
        headers=auth(admin),
        json=_signed_authorization(private),
    )
    assert response.status_code == 503


def test_protected_registry_namespaces_cannot_be_patched_through_generic_admin_api(client, tokens):
    _, admin = tokens
    for key in ("PRIME_DIGITAL_PASSPORTS", "PRIME_SENTINEL_AUTHORIZATIONS"):
        response = client.patch(
            "/admin/registry",
            headers=auth(admin),
            json={"values": {key: {}}},
        )
        assert response.status_code == 403


def test_denied_pack_activation_is_audited_but_does_not_mutate_ready_passport(client, tokens):
    _, admin = tokens
    assert _create_passport(client, admin).status_code == 201
    before = client.get(
        "/admin/prime/PRIME-001/passport", headers=auth(admin)
    ).json()["passport"]

    denied_body = _qualified_space_pack()
    denied_body["pack"]["target_environment_qualification_valid"] = False
    denied = client.post(
        "/admin/prime/PRIME-001/activate-pack",
        headers=auth(admin),
        json=denied_body,
    )
    assert denied.status_code == 403
    assert denied.json()["disposition"] == "DENIED"

    after = client.get(
        "/admin/prime/PRIME-001/passport", headers=auth(admin)
    ).json()["passport"]
    assert after == before



def test_ready_legacy_authorization_id_does_not_block_pack_activation(client, tokens):
    _, admin = tokens
    assert _create_passport(client, admin).status_code == 201
    store = client.app.state.store
    registry = store.get_registry()
    passports = dict(registry["PRIME_DIGITAL_PASSPORTS"])
    legacy = dict(passports["PRIME-001"])
    custody = dict(legacy["custody"])
    custody["requalification_release_authorization_id"] = "LEGACY-AUTHORIZATION"
    legacy["custody"] = custody
    passports["PRIME-001"] = legacy
    store.patch_registry({"PRIME_DIGITAL_PASSPORTS": passports})

    activated = client.post(
        "/admin/prime/PRIME-001/activate-pack",
        headers=auth(admin),
        json=_qualified_space_pack(),
    )
    assert activated.status_code == 200
    assert activated.json()["disposition"] == "ACTIVATION_ALLOWED"


def test_authorization_route_reports_corrupt_passport_as_server_failure(client, tokens):
    _, admin = tokens
    private = _configure_sentinel(client)
    assert _create_passport(client, admin).status_code == 201
    store = client.app.state.store
    registry = store.get_registry()
    passports = dict(registry["PRIME_DIGITAL_PASSPORTS"])
    malformed = dict(passports["PRIME-001"])
    malformed["prime_id"] = "PRIME-MISMATCH"
    passports["PRIME-001"] = malformed
    store.patch_registry({"PRIME_DIGITAL_PASSPORTS": passports})

    response = client.post(
        "/admin/prime/PRIME-001/requalification/authorize",
        headers=auth(admin),
        json=_signed_authorization(private),
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "PRIME passport registry validation failed"


def test_authorization_route_reports_corrupt_sentinel_registry_as_server_failure(client, tokens):
    _, admin = tokens
    private = _configure_sentinel(client)
    assert _create_passport(client, admin).status_code == 201
    store = client.app.state.store
    store.patch_registry({"PRIME_SENTINEL_AUTHORIZATIONS": []})
    response = client.post(
        "/admin/prime/PRIME-001/requalification/authorize",
        headers=auth(admin),
        json=_signed_authorization(private),
    )
    assert response.status_code == 500


def test_ready_legacy_id_clears_on_successful_activation(client, tokens):
    _, admin = tokens
    assert _create_passport(client, admin).status_code == 201
    store = client.app.state.store
    registry = store.get_registry()
    passports = dict(registry["PRIME_DIGITAL_PASSPORTS"])
    legacy = dict(passports["PRIME-001"])
    legacy["custody"] = {
        **legacy["custody"],
        "requalification_release_authorization_id": "LEGACY-AUTHORIZATION",
    }
    passports["PRIME-001"] = legacy
    store.patch_registry({"PRIME_DIGITAL_PASSPORTS": passports})
    activated = client.post(
        "/admin/prime/PRIME-001/activate-pack",
        headers=auth(admin),
        json=_qualified_space_pack(),
    )
    assert activated.status_code == 200
    assert activated.json()["passport"]["custody"]["requalification_release_authorization_id"] is None
    stored = client.get("/admin/prime/PRIME-001/passport", headers=auth(admin)).json()
    assert stored["passport"]["custody"]["requalification_release_authorization_id"] is None
