from __future__ import annotations

from worldshepherd_sara.prime_configuration_custody import REQUALIFICATION_CHECKS


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


def test_prime_passport_full_quarantine_requalification_activation_lifecycle(client, tokens):
    _, admin = tokens

    created = _create_passport(client, admin)
    assert created.status_code == 201
    assert created.json()["passport"]["custody"]["state"] == "READY"
    assert created.json()["provenance"]["provenance_channel"] == "SARA_AUDIT_FOR_ECHO_INGEST"

    duplicate = _create_passport(client, admin)
    assert duplicate.status_code == 409

    mission = client.post(
        "/admin/prime/PRIME-001/mission-complete",
        headers=auth(admin),
        json={
            "environment": "HADAL",
            "evidence_refs": ["ECHO:MISSION:HADAL:001"],
        },
    )
    assert mission.status_code == 200
    assert mission.json()["passport"]["custody"]["state"] == "QUARANTINED_FOR_REQUALIFICATION"

    evidence_only = client.patch(
        "/admin/prime/PRIME-001/requalification",
        headers=auth(admin),
        json={
            "completed_checks": list(REQUALIFICATION_CHECKS),
            "evidence_refs": ["ECHO:REQUAL:001"],
        },
    )
    assert evidence_only.status_code == 200

    blocked = client.post(
        "/admin/prime/PRIME-001/activate-pack",
        headers=auth(admin),
        json=_qualified_space_pack(),
    )
    assert blocked.status_code == 409
    assert blocked.json()["disposition"] == "REQUALIFICATION_REQUIRED"
    assert blocked.json()["passport"]["installed_pack"] is None

    authorized = client.patch(
        "/admin/prime/PRIME-001/requalification",
        headers=auth(admin),
        json={
            "completed_checks": list(REQUALIFICATION_CHECKS),
            "evidence_refs": ["ECHO:REQUAL:002"],
            "release_authorization_id": "AUTH-REQUAL-001",
        },
    )
    assert authorized.status_code == 200

    activated = client.post(
        "/admin/prime/PRIME-001/activate-pack",
        headers=auth(admin),
        json=_qualified_space_pack(),
    )
    assert activated.status_code == 200
    body = activated.json()
    assert body["disposition"] == "ACTIVATION_ALLOWED"
    assert body["passport"]["custody"]["state"] == "READY"
    assert body["passport"]["installed_pack"]["pack_id"] == "SPACE-PACK-001"

    fetched = client.get(
        "/admin/prime/PRIME-001/passport",
        headers=auth(admin),
    )
    assert fetched.status_code == 200
    assert fetched.json()["passport"]["installed_pack"]["pack_id"] == "SPACE-PACK-001"

    registry = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert registry["PRIME_DIGITAL_PASSPORTS"]["PRIME-001"]["custody"]["state"] == "READY"

    audit = client.get("/v1/audit?limit=100", headers=auth(admin))
    assert audit.status_code == 200
    provenance = [
        item for item in audit.json()["records"]
        if item.get("event") == "prime_custody_provenance"
    ]
    assert len(provenance) >= 5
    assert all(
        item["payload"]["schema"] == "WS-ECHO-PRIME-CUSTODY-V1"
        for item in provenance
    )


def test_denied_pack_activation_is_audited_but_does_not_mutate_passport(client, tokens):
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

    audit = client.get("/v1/audit?limit=50", headers=auth(admin)).json()["records"]
    events = [item for item in audit if item.get("event") == "prime_custody_provenance"]
    assert any(
        item["payload"]["details"].get("disposition") == "DENIED"
        for item in events
    )
