import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

import psycopg

from worldshepherd_sara.connector_control import ConnectorControlPlane
from worldshepherd_sara.connector_execution import ReadExecutionBroker
from worldshepherd_sara.connector_ticket_postgres import PostgresClaimStore
from worldshepherd_sara.connector_ticket_shared import SharedReadTicketLedger


MANIFEST = Path("data/worldshepherd_connectors.v2.json")
POLICY = Path("data/worldshepherd_read_ticket_policy.v1.json")
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


def process_claim(ticket):
    store = PostgresClaimStore(connection_factory)
    ledger = SharedReadTicketLedger(store)
    claim = ledger.claim(ticket, now=1001.0)
    return claim.ok, claim.reason


def issue_ticket(*, action="research.search", ttl_seconds=30, issuer_now=1000.0):
    issuer = make_broker(now=issuer_now)
    planned = issuer.plan_read(
        connector_id="web_research",
        action=action,
        actor="operator",
        data_class="PUBLIC",
        context={"query": "live-postgres-contention"},
        ttl_seconds=ttl_seconds,
    )
    assert planned.ok and planned.ticket is not None
    return planned.ticket


def test_real_postgres_allows_exactly_one_of_64_independent_claimants():
    store = PostgresClaimStore(connection_factory)
    store.initialize()
    reset_table()
    ticket = issue_ticket()

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


def test_real_postgres_allows_exactly_one_across_separate_worker_processes():
    reset_table()
    ticket = issue_ticket()

    with ProcessPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(process_claim, [ticket] * 24))

    winners = [result for result in results if result[0]]
    losers = [result for result in results if not result[0]]
    assert len(winners) == 1
    assert len(losers) == 23
    assert all(reason == "ticket already consumed" for _, reason in losers)


def test_database_time_ignores_large_issuer_and_claimant_clock_offsets():
    reset_table()
    issuer_now = 10_000_000.0
    claimant_now = -10_000_000.0
    ticket = issue_ticket(ttl_seconds=30, issuer_now=issuer_now)

    store = PostgresClaimStore(connection_factory)
    registered = store.status(ticket["ticket_id"])
    assert registered["known"] is True
    assert abs(float(registered["expires_at"]) - float(ticket["expires_at"])) > 1_000_000

    claimant = make_broker(now=claimant_now)
    claim = claimant.claim_for_execution(ticket, now=claimant_now)
    assert claim["ok"] is True
    assert claim["consumed_at"] != claimant_now
    assert claim["consumed_at"] != issuer_now


def test_real_postgres_rejects_expired_ticket_by_database_time_despite_client_skew():
    reset_table()
    ticket = issue_ticket(
        action="source.verify",
        ttl_seconds=5,
        issuer_now=10_000_000.0,
    )

    time.sleep(5.25)
    later_worker = make_broker(now=-10_000_000.0)
    claim = later_worker.claim_for_execution(ticket, now=-10_000_000.0)
    assert claim["ok"] is False
    assert claim["reason"] == "ticket expired"


def test_policy_records_database_time_and_clock_skew_evidence_without_distributed_upgrade():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["postgres_live_validation"] is True
    assert policy["postgres_live_validation_environment"] == "ephemeral_postgresql_18_6_github_actions"
    assert policy["postgres_client_validation"] == "psycopg_3_3_5"
    assert policy["multi_connection_live_validation"] is True
    assert policy["multi_process_live_validation"] is True
    assert policy["multi_worker_live_validation"] is True
    assert policy["multi_worker_validation_scope"] == "single_host_separate_python_processes"
    assert policy["reconnect_replay_validation"] is True
    assert policy["fresh_connection_expiry_validation"] is True
    assert policy["clock_authority"] == "postgres_clock_timestamp"
    assert policy["database_time_expiry_validation"] is True
    assert policy["database_time_consumption_validation"] is True
    assert policy["clock_skew_live_validation"] is True
    assert policy["clock_skew_validation_scope"] == "single_host_injected_issuer_and_claimant_absolute_offsets"
    assert policy["clock_skew_offset_test_seconds"] == 10_000_000
    assert policy["failure_injection_validation"] is False
    assert policy["multi_host_live_validation"] is False
    assert policy["distributed_replay_protection"] is False
    assert policy["multi_host_consensus"] is False
