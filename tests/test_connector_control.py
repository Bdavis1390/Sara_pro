import json
from pathlib import Path

import pytest

from worldshepherd_sara.connector_control import ConnectorControlPlane


MANIFEST = Path("data/worldshepherd_connectors.v2.json")


def test_manifest_validates():
    control = ConnectorControlPlane(MANIFEST)
    result = control.validate_manifest()
    assert result["ok"] is True
    assert result["connectors"] >= 10
    assert result["tools"] >= 8


def test_unknown_action_is_denied():
    control = ConnectorControlPlane(MANIFEST)
    decision = control.authorize(
        connector_id="github",
        action="repo.destroy",
        actor="admin",
        data_class="INTERNAL",
    )
    assert decision.allowed is False
    assert "allow-listed" in decision.reason


def test_external_write_requires_human_approval():
    control = ConnectorControlPlane(MANIFEST)
    decision = control.authorize(
        connector_id="github",
        action="file.update",
        actor="admin",
        data_class="INTERNAL",
    )
    assert decision.allowed is False
    assert decision.requires_human_approval is True


def test_approved_external_write_gets_echo_envelope():
    control = ConnectorControlPlane(MANIFEST)
    decision = control.authorize(
        connector_id="github",
        action="file.update",
        actor="admin",
        data_class="INTERNAL",
        human_approved=True,
        approval_id="test-approval-001",
        context={"path": "README.md"},
    )
    assert decision.allowed is True
    assert decision.envelope is not None
    assert len(decision.envelope["sha256"]) == 64


def test_operator_cannot_use_admin_only_connector():
    control = ConnectorControlPlane(MANIFEST)
    decision = control.authorize(
        connector_id="github",
        action="repo.read",
        actor="operator",
        data_class="PUBLIC",
    )
    assert decision.allowed is False
    assert "role" in decision.reason


def test_data_class_ceiling_is_enforced():
    control = ConnectorControlPlane(MANIFEST)
    decision = control.authorize(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        data_class="INTERNAL",
    )
    assert decision.allowed is False
    assert "exceeds connector maximum" in decision.reason


def test_policy_views_cannot_mutate_live_authorization_state():
    control = ConnectorControlPlane(MANIFEST)

    manifest_view = control.manifest
    github_view = next(c for c in manifest_view["connectors"] if c["id"] == "github")
    github_view["external_write_actions"].remove("file.update")

    connector_view = control.connector("github")
    connector_view["allowed_actions"].remove("file.update")

    decision = control.authorize(
        connector_id="github",
        action="file.update",
        actor="admin",
        data_class="INTERNAL",
    )
    assert decision.allowed is False
    assert decision.requires_human_approval is True
    assert decision.reason == "human approval required"


def test_failed_reload_preserves_last_known_good_policy(tmp_path):
    manifest_path = tmp_path / "connectors.json"
    original = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_path.write_text(json.dumps(original), encoding="utf-8")

    control = ConnectorControlPlane(manifest_path)
    baseline = control.authorize(
        connector_id="github",
        action="repo.read",
        actor="admin",
        data_class="PUBLIC",
    )
    assert baseline.allowed is True

    invalid = dict(original)
    invalid["schema"] = "invalid.schema"
    manifest_path.write_text(json.dumps(invalid), encoding="utf-8")

    with pytest.raises(ValueError):
        control.reload()

    assert control.validate_manifest()["ok"] is True
    after_failed_reload = control.authorize(
        connector_id="github",
        action="repo.read",
        actor="admin",
        data_class="PUBLIC",
    )
    assert after_failed_reload.allowed is True
