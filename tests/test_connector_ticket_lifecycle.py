import hashlib
import json
from pathlib import Path

from worldshepherd_sara.connector_control import ConnectorControlPlane
from worldshepherd_sara.connector_execution import ReadExecutionBroker
from worldshepherd_sara.connector_receipt import seal_read_receipt, verify_read_receipt
from worldshepherd_sara.connector_ticket_lifecycle import (
    MAX_TTL_SECONDS,
    MIN_TTL_SECONDS,
    READ_TICKET_SCHEMA_V2,
    ReadTicketLedger,
    context_sha256,
    verify_v2_ticket_shape,
)


MANIFEST = Path("data/worldshepherd_connectors.v2.json")
POLICY = Path("data/worldshepherd_read_ticket_policy.v1.json")


def make_broker(*, now=1000.0):
    ledger = ReadTicketLedger(clock=lambda: now)
    control = ConnectorControlPlane(MANIFEST)
    return ReadExecutionBroker(control, ledger=ledger), ledger


def test_ticket_policy_matches_code_contract():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["ticket_schema"] == READ_TICKET_SCHEMA_V2
    assert policy["single_use"] is True
    assert policy["min_ttl_seconds"] == MIN_TTL_SECONDS
    assert policy["max_ttl_seconds"] == MAX_TTL_SECONDS
    assert policy["raw_context_in_ticket"] is False
    assert policy["durable_replay_protection"] is False
    assert policy["distributed_replay_protection"] is False


def test_ticket_contains_context_hash_not_raw_context():
    broker, _ = make_broker()
    context = {"query": "private-looking-context-value", "scope": "ci"}
    result = broker.plan_read(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        data_class="PUBLIC",
        context=context,
        ttl_seconds=30,
    )
    assert result.ok is True
    ticket = result.ticket
    assert ticket is not None
    assert ticket["schema"] == READ_TICKET_SCHEMA_V2
    assert ticket["context_sha256"] == context_sha256(context)
    assert "context" not in ticket
    assert "private-looking-context-value" not in json.dumps(ticket, sort_keys=True)
    assert ticket["expires_at"] - ticket["issued_at"] == 30
    assert verify_v2_ticket_shape(ticket) is True


def test_ticket_is_claimable_once_only():
    broker, ledger = make_broker()
    result = broker.plan_read(
        connector_id="github",
        action="repo.read",
        actor="admin",
        data_class="PUBLIC",
        ttl_seconds=30,
    )
    ticket = result.ticket
    assert result.ok and ticket is not None

    first = broker.claim_for_execution(ticket, now=1001.0)
    second = broker.claim_for_execution(ticket, now=1002.0)
    assert first["ok"] is True
    assert second["ok"] is False
    assert second["reason"] == "ticket already consumed"
    assert ledger.status(ticket["ticket_id"])["consumed"] is True


def test_expired_ticket_fails_closed():
    broker, _ = make_broker()
    result = broker.plan_read(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        data_class="PUBLIC",
        ttl_seconds=5,
    )
    ticket = result.ticket
    assert result.ok and ticket is not None
    claim = broker.claim_for_execution(ticket, now=1006.0)
    assert claim["ok"] is False
    assert claim["reason"] == "ticket expired"


def test_out_of_range_ttl_is_rejected():
    broker, _ = make_broker()
    low = broker.plan_read(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        ttl_seconds=MIN_TTL_SECONDS - 1,
    )
    high = broker.plan_read(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        ttl_seconds=MAX_TTL_SECONDS + 1,
    )
    assert low.ok is False
    assert high.ok is False
    assert "ttl_seconds" in low.reason
    assert "ttl_seconds" in high.reason


def test_tampered_ticket_fails_claim():
    broker, _ = make_broker()
    result = broker.plan_read(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        ttl_seconds=30,
    )
    ticket = dict(result.ticket or {})
    ticket["action"] = "source.verify"
    claim = broker.claim_for_execution(ticket, now=1001.0)
    assert claim["ok"] is False
    assert claim["reason"] == "invalid read ticket"


def test_v2_ticket_can_anchor_echo_receipt_after_claim():
    broker, _ = make_broker()
    result = broker.plan_read(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        ttl_seconds=30,
    )
    ticket = result.ticket
    assert result.ok and ticket is not None
    claim = broker.claim_for_execution(ticket, now=1001.0)
    assert claim["ok"] is True

    raw = b"normalized synthetic connector result"
    digest = hashlib.sha256(raw).hexdigest()
    receipt = seal_read_receipt(
        ticket=ticket,
        status="success",
        result_sha256=digest,
        completed_at=1002.0,
    )
    assert verify_read_receipt(receipt, ticket=ticket, result_bytes=raw) is True
    assert receipt["ticket_id_sha256"] is not None
    assert ticket["ticket_id"] not in json.dumps(receipt, sort_keys=True)
