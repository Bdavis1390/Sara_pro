import hashlib
import json
import sqlite3
from pathlib import Path

from worldshepherd_sara.connector_control import ConnectorControlPlane
from worldshepherd_sara.connector_execution import ReadExecutionBroker
from worldshepherd_sara.connector_receipt import seal_read_receipt, verify_read_receipt
from worldshepherd_sara.connector_ticket_sqlite import SqliteReadTicketLedger


MANIFEST = Path("data/worldshepherd_connectors.v2.json")


def make_broker(db_path, *, now=1000.0):
    ledger = SqliteReadTicketLedger(db_path, clock=lambda: now)
    control = ConnectorControlPlane(MANIFEST)
    return ReadExecutionBroker(control, ledger=ledger), ledger


def test_sqlite_claim_survives_process_style_reopen(tmp_path):
    db_path = tmp_path / "tickets.db"
    broker1, _ = make_broker(db_path)
    result = broker1.plan_read(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        data_class="PUBLIC",
        ttl_seconds=30,
        context={"query": "durable-test"},
    )
    ticket = result.ticket
    assert result.ok and ticket is not None

    ledger2 = SqliteReadTicketLedger(db_path, clock=lambda: 1001.0)
    first = ledger2.claim(ticket)
    assert first.ok is True

    ledger3 = SqliteReadTicketLedger(db_path, clock=lambda: 1002.0)
    second = ledger3.claim(ticket)
    assert second.ok is False
    assert second.reason == "ticket already consumed"
    assert ledger3.status(ticket["ticket_id"])["consumed"] is True


def test_sqlite_expiry_survives_reopen(tmp_path):
    db_path = tmp_path / "tickets.db"
    broker, _ = make_broker(db_path)
    result = broker.plan_read(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        data_class="PUBLIC",
        ttl_seconds=5,
    )
    ticket = result.ticket
    assert result.ok and ticket is not None

    reopened = SqliteReadTicketLedger(db_path, clock=lambda: 1006.0)
    claim = reopened.claim(ticket)
    assert claim.ok is False
    assert claim.reason == "ticket expired"


def test_sqlite_schema_stores_only_bounded_claim_metadata(tmp_path):
    db_path = tmp_path / "tickets.db"
    broker, _ = make_broker(db_path)
    secret_marker = "raw-context-must-not-enter-ledger"
    result = broker.plan_read(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        data_class="PUBLIC",
        ttl_seconds=30,
        context={"query": secret_marker},
    )
    ticket = result.ticket
    assert result.ok and ticket is not None

    with sqlite3.connect(db_path) as connection:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(connector_read_tickets)")]
        rows = connection.execute("SELECT * FROM connector_read_tickets").fetchall()

    assert columns == ["ticket_id", "ticket_sha256", "expires_at", "consumed_at"]
    serialized = json.dumps(rows, sort_keys=True)
    assert secret_marker not in serialized
    assert ticket["context_sha256"] not in serialized
    assert ticket["policy_envelope_sha256"] not in serialized


def test_sqlite_duplicate_registration_fails_closed(tmp_path):
    db_path = tmp_path / "tickets.db"
    broker, ledger = make_broker(db_path)
    result = broker.plan_read(
        connector_id="github",
        action="repo.read",
        actor="admin",
        data_class="PUBLIC",
        ttl_seconds=30,
    )
    ticket = result.ticket
    assert result.ok and ticket is not None

    try:
        ledger.register(ticket)
    except ValueError as exc:
        assert str(exc) == "duplicate ticket_id"
    else:
        raise AssertionError("duplicate registration should fail closed")


def test_sqlite_claim_can_anchor_echo_receipt(tmp_path):
    db_path = tmp_path / "tickets.db"
    broker, _ = make_broker(db_path)
    result = broker.plan_read(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        data_class="PUBLIC",
        ttl_seconds=30,
    )
    ticket = result.ticket
    assert result.ok and ticket is not None

    reopened = SqliteReadTicketLedger(db_path, clock=lambda: 1001.0)
    assert reopened.claim(ticket).ok is True

    raw = b"durably claimed synthetic result"
    receipt = seal_read_receipt(
        ticket=ticket,
        status="success",
        result_sha256=hashlib.sha256(raw).hexdigest(),
        completed_at=1002.0,
    )
    assert verify_read_receipt(receipt, ticket=ticket, result_bytes=raw) is True
