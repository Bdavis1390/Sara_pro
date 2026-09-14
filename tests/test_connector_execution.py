from pathlib import Path

from worldshepherd_sara.connector_control import ConnectorControlPlane
from worldshepherd_sara.connector_execution import ReadExecutionBroker


MANIFEST = Path("data/worldshepherd_connectors.v2.json")


def broker() -> ReadExecutionBroker:
    return ReadExecutionBroker(ConnectorControlPlane(MANIFEST))


def test_public_web_read_gets_sealed_ticket():
    result = broker().plan_read(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        data_class="PUBLIC",
        context={"query": "test"},
    )
    assert result.ok is True
    assert result.mode == "host_connector_handoff"
    assert result.ticket is not None
    assert result.ticket["write_enabled"] is False
    assert result.ticket["credential_handling"] == "outside_sara_broker"
    assert len(result.ticket["sha256"]) == 64


def test_github_write_is_blocked_before_handoff():
    result = broker().plan_read(
        connector_id="github",
        action="file.update",
        actor="admin",
        data_class="INTERNAL",
    )
    assert result.ok is False
    assert result.mode == "blocked"
    assert "write actions" in result.reason


def test_admin_only_read_rejects_operator():
    result = broker().plan_read(
        connector_id="github",
        action="repo.read",
        actor="operator",
        data_class="PUBLIC",
    )
    assert result.ok is False
    assert "role" in result.reason


def test_data_class_policy_still_applies():
    result = broker().plan_read(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        data_class="INTERNAL",
    )
    assert result.ok is False
    assert "exceeds connector maximum" in result.reason


def test_unknown_connector_is_blocked():
    result = broker().plan_read(
        connector_id="unknown_service",
        action="read",
        actor="operator",
        data_class="PUBLIC",
    )
    assert result.ok is False
    assert "unknown connector" in result.reason
