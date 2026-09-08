from __future__ import annotations

D_A = "sha256:" + "a" * 64
D_B = "sha256:" + "b" * 64
D_C = "sha256:" + "c" * 64


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def package_payload() -> dict[str, object]:
    return {
        "package_id": "LABPKG-API-001",
        "campaign_id": "SV-META-001-P1",
        "project_id": "ADAPTIVE_METASURFACE",
        "artifact_id": "META-COUPON-001",
        "laboratory_organization": "Example RF Lab",
        "facility": "Anechoic/VNA Facility",
        "engagement_reference": "ENG-001",
        "received_at_utc": "2026-09-06T23:50:00Z",
        "acquisition_start_utc": "2026-09-06T22:00:00Z",
        "acquisition_end_utc": "2026-09-06T23:00:00Z",
        "time_reference": "UTC",
        "independence": "external_independence_pending",
        "independence_basis": "External measurement organization; independence review pending.",
        "samples": [
            {
                "sample_id": "META-SAMPLE-001",
                "specimen_type": "active metasurface coupon",
                "configuration_digest": D_A,
                "custody_events": [
                    {
                        "event_id": "C-1",
                        "timestamp_utc": "2026-09-06T21:30:00Z",
                        "actor_or_org": "Example RF Lab",
                        "action": "sample received for test",
                    }
                ],
            }
        ],
        "instruments": [
            {
                "instrument_id": "VNA-001",
                "instrument_type": "vector network analyzer",
                "calibration_record_ids": ["CAL-VNA-001"],
                "calibration_due_or_valid_at_test": True,
            }
        ],
        "methods": [
            {
                "method_id": "S-PARAM-001",
                "title": "Complex S-parameter measurement",
                "standard_or_procedure_ref": "LAB-SOP-RF-001",
            }
        ],
        "files": [
            {
                "file_id": "RAW-S2P-001",
                "role": "raw_data",
                "sha256": D_B,
                "media_type": "text/plain",
                "original_name": "coupon.s2p",
            },
            {
                "file_id": "CAL-PDF-001",
                "role": "calibration",
                "sha256": D_C,
                "media_type": "application/pdf",
                "original_name": "vna-calibration.pdf",
            },
        ],
        "results": [
            {
                "result_id": "META-R-001",
                "sample_id": "META-SAMPLE-001",
                "observable": "command-state phase difference",
                "value": 45.0,
                "unit": "degree",
                "uncertainty": "fixture value",
                "method_id": "S-PARAM-001",
                "source_file_ids": ["RAW-S2P-001"],
            }
        ],
    }


def test_lab_package_validate_requires_admin(client, tokens):
    relay, _ = tokens
    response = client.post(
        "/admin/physics/lab-packages/validate",
        headers=auth(relay),
        json=package_payload(),
    )
    assert response.status_code == 403


def test_lab_package_validate_returns_digest_and_never_promotes(client, tokens):
    _, admin = tokens
    response = client.post(
        "/admin/physics/lab-packages/validate",
        headers=auth(admin),
        json=package_payload(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["evidence_complete"] is True
    assert body["maturity_promoted"] is False
    assert body["package_digest"].startswith("sha256:")

    audit = client.get("/v1/audit?limit=100", headers=auth(admin))
    assert any(
        item.get("event") == "physics_lab_package_validated"
        and item.get("payload", {}).get("package_id") == "LABPKG-API-001"
        for item in audit.json()["records"]
    )
