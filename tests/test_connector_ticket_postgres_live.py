import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg

from worldshepherd_sara.connector_control import ConnectorControlPlane
from worldshepherd_sara.connector_execution import ReadExecutionBroker
from worldshepherd_sara.connector_ticket_postgres import PostgresClaimStore
from worldshepherd_sara.connector_ticket_shared import SharedReadTicketLedger


MANIFEST = Path("data/worldshepherd_connectors.v2.json")
DSN = os.environ["WORLDSHEPHERD_TEST_POSTGRES_DSN"]


def connection_factory():
    return psycopg.connect(DSN)


def reset_table():
    with connection_factory() as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE worldshepherd_connector_read_tickets")


def make_broker(*, now=1000.0):
    store = PostgresClaimStore(connection_factory)
    ledger = SharedReadTicketLedger(store, clock=lambda: now)
    return ReadExecutionBroker(ConnectorControlPlane(MANIFEST), ledger=ledger)


def test_real_postgres_allows_exactly_one_of_64_independent_claimants():
    store = PostgresClaimStore(connection_factory)
    store.initialize()
    reset_table()

    issuer = make_broker()
    planned = issuer.plan_read(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        data_class="PUBLIC",
        context={"query": "live-postgres-contention"},
        ttl_seconds=30,
    )
    assert planned.ok and planned.ticket is not None
    ticket = planned.ticket

    def contend(_):
        worker = make_broker(now=1001.0)
        return worker.claim_for_execution(ticket, now=1001.0)

    with ThreadPoolExecutor(max_workers=32) as pool:
        results = list(pool.map(contend, range(64)))

    winners = [result for result in results if result["ok"]]
    losers = [result for result in results if not result["ok"]]
    assert len(winners) == 1
    assert len(losers) == 63
    assert all(result["reason"] == "ticket already consumed" for result in losers)

    reconnect_worker = make_broker(now=1002.0)
    replay = reconnect_worker.claim_for_execution(ticket, now=1002.0)
    assert replay["ok"] is False
    assert replay["reason"] == "ticket already consumed"


def test_real_postgres_rejects_expired_ticket_across_new_connection():
    reset_table()
    issuer = make_broker()
    planned = issuer.plan_read(
        connector_id="web_research",
        action="source.verify",
        actor="operator",
        data_class="PUBLIC",
        ttl_seconds=5,
    )
    assert planned.ok and planned.ticket is not None

    later_worker = make_broker(now=1006.0)
    claim = later_worker.claim_for_execution(planned.ticket, now=1006.0)
    assert claim["ok"] is False
    assert claim["reason"] == "ticket expired"
