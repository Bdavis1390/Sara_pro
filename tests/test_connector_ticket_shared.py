from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from worldshepherd_sara.connector_control import ConnectorControlPlane
from worldshepherd_sara.connector_execution import ReadExecutionBroker
from worldshepherd_sara.connector_ticket_shared import (
    SharedReadTicketLedger,
    ThreadSafeSharedClaimStore,
)


MANIFEST = Path("data/worldshepherd_connectors.v2.json")


def make_ticket(*, now=1000.0):
    store = ThreadSafeSharedClaimStore()
    ledger = SharedReadTicketLedger(store, clock=lambda: now)
    broker = ReadExecutionBroker(ConnectorControlPlane(MANIFEST), ledger=ledger)
    result = broker.plan_read(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        data_class="PUBLIC",
        context={"query": "shared-claim-contract"},
        ttl_seconds=30,
    )
    assert result.ok and result.ticket is not None
    return broker, store, result.ticket


def test_shared_store_allows_exactly_one_concurrent_claim():
    broker, _, ticket = make_ticket()

    def claim(_):
        return broker.claim_for_execution(ticket, now=1001.0)["ok"]

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(claim, range(64)))

    assert results.count(True) == 1
    assert results.count(False) == 63


def test_shared_store_rejects_tampered_ticket_before_store_claim():
    broker, store, ticket = make_ticket()
    tampered = dict(ticket)
    tampered["action"] = "source.verify"
    result = broker.claim_for_execution(tampered, now=1001.0)
    assert result["ok"] is False
    assert result["reason"] == "invalid read ticket"
    status = store.status(ticket["ticket_id"])
    assert status["consumed"] is False


def test_shared_store_rejects_expired_ticket():
    broker, _, ticket = make_ticket()
    result = broker.claim_for_execution(ticket, now=1031.0)
    assert result["ok"] is False
    assert result["reason"] == "ticket expired"


def test_shared_store_persists_minimal_claim_state_only():
    _, store, ticket = make_ticket()
    record = store._records[ticket["ticket_id"]]
    assert set(record.__dict__) == {"ticket_sha256", "expires_at", "consumed_at"}
    assert "context_sha256" not in record.__dict__
    assert "policy_envelope_sha256" not in record.__dict__
