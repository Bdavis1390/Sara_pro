from __future__ import annotations

import asyncio
import json
import stat
from pathlib import Path

import pytest

from worldshepherd_sara.app import RequestSizeLimitMiddleware
from worldshepherd_sara.storage import DurableStore
from worldshepherd_sara.limits import (
    MAX_MAPPING_KEYS,
    MAX_NESTING_DEPTH,
    MAX_REQUEST_BYTES,
    MAX_SEQUENCE_ITEMS,
    MAX_STRING_LENGTH,
)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_health_liveness_readiness_and_ui(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True
    assert client.get("/livez").json() == {"ok": True, "status": "alive"}
    ready = client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    ui = client.get("/ui")
    assert ui.status_code == 200
    assert "Worldshepherd SARA" in ui.text


def test_readiness_reports_storage_failure_but_liveness_survives(client, monkeypatch):
    monkeypatch.setattr(
        client.app.state.store,
        "check_storage",
        lambda: (False, "simulated persistent-storage failure"),
    )
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert client.get("/livez").status_code == 200


@pytest.mark.parametrize(
    ("headers", "detail"),
    [
        ({}, "Missing Authorization header"),
        ({"Authorization": "Basic abc"}, "Authorization must use Bearer token"),
        ({"Authorization": "Bearer"}, "Authorization must use Bearer token"),
        (auth("incorrect-token-value-000000"), "Invalid bearer token"),
    ],
)
def test_missing_malformed_and_invalid_credentials(client, headers, detail):
    response = client.get("/v1/audit", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == detail


def test_invalid_credentials_rejected_by_relay_endpoint(client):
    response = client.post(
        "/v1/relay",
        headers=auth("incorrect-token-value-000000"),
        json={"target": "local", "action": "check", "payload": {}},
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", "/v1/audit", None),
        ("get", "/admin/registry", None),
        ("patch", "/admin/registry", {"values": {}}),
        ("get", "/admin/selftest", None),
    ],
)
def test_every_admin_endpoint_rejects_relay_credentials(
    client, tokens, method, path, body
):
    relay, _ = tokens
    response = client.request(method, path, headers=auth(relay), json=body)
    assert response.status_code == 403


def test_relay_and_admin_credentials_can_record_local_relay(client, tokens):
    for token in tokens:
        response = client.post(
            "/v1/relay",
            headers=auth(token),
            json={
                "target": "SSPADAWANZZ",
                "action": "status_check",
                "payload": {"scope": "local"},
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "recorded_local_only"


def test_admin_registry_audit_and_selftest(client, tokens):
    _, admin = tokens
    patch = client.patch(
        "/admin/registry",
        headers=auth(admin),
        json={"values": {"SARA_CORE": {"role": "core", "status": "online"}}},
    )
    assert patch.status_code == 200
    assert client.get("/admin/registry", headers=auth(admin)).status_code == 200

    selftest = client.get("/admin/selftest", headers=auth(admin))
    assert selftest.status_code == 200
    assert selftest.json()["ok"] is True
    assert set(selftest.json()["checks"]) == {
        "persistent_storage",
        "registry_read",
        "audit_append",
    }

    audit = client.get("/v1/audit?limit=50", headers=auth(admin))
    assert audit.status_code == 200
    assert any(item["event"] == "registry_patched" for item in audit.json()["records"])


def test_admin_selftest_structures_secure_registry_open_failure(
    client, tokens, monkeypatch
):
    _, admin = tokens

    def fail_secure_registry_open():
        raise RuntimeError("simulated secure registry-open failure")

    monkeypatch.setattr(client.app.state.store, "get_registry", fail_secure_registry_open)
    monkeypatch.setattr(
        client.app.state.store,
        "check_storage",
        lambda: (True, "simulated persistent-storage success"),
    )

    response = client.get("/admin/selftest", headers=auth(admin))

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["checks"]["registry_read"] == {
        "ok": False,
        "detail": (
            "registry read failed: simulated secure registry-open failure"
        ),
    }
    assert body["checks"]["persistent_storage"]["ok"] is True
    assert body["checks"]["audit_append"]["ok"] is True


def test_malformed_json_does_not_mutate_state(client, tokens):
    relay, admin = tokens
    store = client.app.state.store
    audit_before = store.audit_path.read_bytes()
    registry_before = store.registry_path.read_bytes()
    response = client.post(
        "/v1/relay",
        headers={**auth(relay), "Content-Type": "application/json"},
        content=b'{"target":',
    )
    assert response.status_code == 422
    assert store.audit_path.read_bytes() == audit_before
    assert store.registry_path.read_bytes() == registry_before

    response = client.patch(
        "/admin/registry",
        headers={**auth(admin), "Content-Type": "application/json"},
        content=b'{"values":',
    )
    assert response.status_code == 422
    assert store.audit_path.read_bytes() == audit_before
    assert store.registry_path.read_bytes() == registry_before


def test_oversized_request_does_not_mutate_state(client, tokens):
    relay, _ = tokens
    store = client.app.state.store
    audit_before = store.audit_path.read_bytes()
    response = client.post(
        "/v1/relay",
        headers={**auth(relay), "Content-Type": "application/json"},
        content=b"x" * (MAX_REQUEST_BYTES + 1),
    )
    assert response.status_code == 413
    assert store.audit_path.read_bytes() == audit_before


def test_request_limit_counts_streamed_body_without_content_length():
    sent: list[dict[str, object]] = []
    incoming = iter(
        [
            {"type": "http.request", "body": b"abc", "more_body": True},
            {"type": "http.request", "body": b"def", "more_body": False},
        ]
    )

    async def receive():
        return next(incoming)

    async def send(message):
        sent.append(message)

    async def downstream(scope, receive, send):
        while True:
            message = await receive()
            if not message.get("more_body", False):
                break
        await send(
            {"type": "http.response.start", "status": 200, "headers": []}
        )
        await send({"type": "http.response.body", "body": b"unexpected"})

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "scheme": "http",
        "method": "POST",
        "server": ("testserver", 80),
        "client": ("testclient", 123),
        "root_path": "",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [],
    }

    middleware = RequestSizeLimitMiddleware(downstream, max_bytes=4)
    asyncio.run(middleware(scope, receive, send))

    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 413

    body = b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    )
    assert json.loads(body) == {"detail": "Request body exceeds 4 bytes"}


@pytest.mark.parametrize(
    "payload",
    [
        {"nested": [[[[[[[[["too deep"]]]]]]]]]},
        {"many_keys": {f"k{i}": i for i in range(MAX_MAPPING_KEYS + 1)}},
        {"many_items": list(range(MAX_SEQUENCE_ITEMS + 1))},
        {"long": "x" * (MAX_STRING_LENGTH + 1)},
        {"serialized": ["x" * 400 for _ in range(MAX_SEQUENCE_ITEMS)]},
    ],
)
def test_relay_resource_limits_do_not_mutate_state(client, tokens, payload):
    relay, _ = tokens
    store = client.app.state.store
    before = store.audit_path.read_bytes()
    response = client.post(
        "/v1/relay",
        headers=auth(relay),
        json={"target": "local", "action": "check", "payload": payload},
    )
    assert response.status_code == 422
    assert store.audit_path.read_bytes() == before


def test_registry_limits_do_not_mutate_registry_or_audit(client, tokens):
    _, admin = tokens
    store = client.app.state.store
    registry_before = store.registry_path.read_bytes()
    audit_before = store.audit_path.read_bytes()
    nested: object = "leaf"
    for _ in range(MAX_NESTING_DEPTH + 1):
        nested = {"child": nested}
    response = client.patch(
        "/admin/registry",
        headers=auth(admin),
        json={"values": {"nested": nested}},
    )
    assert response.status_code == 422
    assert store.registry_path.read_bytes() == registry_before
    assert store.audit_path.read_bytes() == audit_before


def test_runtime_file_modes(client):
    store = client.app.state.store
    assert stat.S_IMODE(store.root.stat().st_mode) == 0o700
    assert stat.S_IMODE(store.registry_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(store.audit_path.stat().st_mode) == 0o600


def test_registry_symlink_swap_is_rejected(tmp_path):
    store = DurableStore(tmp_path / "data")
    outside = tmp_path / "outside-registry.json"
    outside.write_text('{"outside": true}\n', encoding="utf-8")

    store.registry_path.unlink()
    store.registry_path.symlink_to(outside)

    with pytest.raises(RuntimeError, match="registry file"):
        store.get_registry()

    assert outside.read_text(encoding="utf-8") == '{"outside": true}\n'


def test_audit_symlink_swap_is_rejected(tmp_path):
    store = DurableStore(tmp_path / "data")
    outside = tmp_path / "outside-audit.jsonl"
    outside.write_text('{"event": "outside"}\n', encoding="utf-8")

    store.audit_path.symlink_to(outside)

    with pytest.raises(RuntimeError, match="audit file"):
        store.read_audit(1)

    assert outside.read_text(encoding="utf-8") == '{"event": "outside"}\n'


def test_registry_replace_fsyncs_parent_directory(tmp_path, monkeypatch):
    store = DurableStore(tmp_path / "data")
    synchronized: list[Path] = []

    monkeypatch.setattr(
        store,
        "_fsync_directory",
        lambda path: synchronized.append(path),
    )

    store.patch_registry({"SARA_CORE": {"status": "online"}})

    assert synchronized == [store.root]


def test_corrupted_audit_lines_are_safely_labeled(client, tokens):
    _, admin = tokens
    store = client.app.state.store
    with store.audit_path.open("ab") as handle:
        handle.write(b"not-json\n")
    response = client.get("/v1/audit?limit=1", headers=auth(admin))
    assert response.status_code == 200
    assert response.json()["records"] == [
        {"event": "audit_corruption_detected", "reason": "invalid_line"}
    ]


def test_audit_tail_does_not_use_whole_file_read(client, tokens, monkeypatch):
    _, admin = tokens
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda *args, **kwargs: pytest.fail("whole-file read is forbidden"),
    )
    response = client.get("/v1/audit?limit=1", headers=auth(admin))
    assert response.status_code == 200
    assert len(response.json()["records"]) == 1
