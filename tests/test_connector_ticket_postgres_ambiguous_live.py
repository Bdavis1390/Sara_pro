import os
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


def store():
    return PostgresClaimStore(connection_factory)


def normal_broker():
    return ReadExecutionBroker(
        ConnectorControlPlane(MANIFEST),
        ledger=SharedReadTicketLedger(store()),
    )


def reset_table():
    with connection_factory() as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE worldshepherd_connector_read_tickets")


def issue_ticket():
    planned = normal_broker().plan_read(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        data_class="PUBLIC",
        context={"query": "ambiguous-commit"},
        ttl_seconds=60,
    )
    assert planned.ok and planned.ticket is not None
    return planned.ticket


class CommitOutcomeLostConnection:
    def __init__(self, inner, *, commit_reaches_database):
        self._inner = inner
        self._commit_reaches_database = bool(commit_reaches_database)

    def cursor(self):
        return self._inner.cursor()

    def commit(self):
        if self._commit_reaches_database:
            self._inner.commit()
        raise psycopg.OperationalError("simulated lost COMMIT acknowledgement")

    def rollback(self):
        return self._inner.rollback()

    def close(self):
        return self._inner.close()


def ambiguous_broker(*, commit_reaches_database):
    def factory():
        return CommitOutcomeLostConnection(
            psycopg.connect(DSN),
            commit_reaches_database=commit_reaches_database,
        )

    ambiguous_store = PostgresClaimStore(factory)
    return ReadExecutionBroker(
        ConnectorControlPlane(MANIFEST),
        ledger=SharedReadTicketLedger(ambiguous_store),
    )


def setup_module():
    store().initialize()


def test_commit_succeeded_but_ack_lost_remains_non_executable_after_reconciliation():
    reset_table()
    ticket = issue_ticket()
    worker = ambiguous_broker(commit_reaches_database=True)

    claim = worker.claim_for_execution(ticket)
    assert claim["ok"] is False
    assert claim["state"] == "unknown"
    assert claim["may_execute_connector"] is False
    assert claim["may_retry_claim"] is False

    reconciled = worker.reconcile_claim_for_execution(ticket)
    assert reconciled["ok"] is False
    assert reconciled["state"] == "consumed_ownership_unknown"
    assert reconciled["may_execute_connector"] is False
    assert reconciled["may_retry_claim"] is False

    replay = normal_broker().claim_for_execution(ticket)
    assert replay["ok"] is False
    assert replay["reason"] == "ticket already consumed"


def test_commit_did_not_happen_ack_lost_requires_explicit_retry_then_claims_once():
    reset_table()
    ticket = issue_ticket()
    worker = ambiguous_broker(commit_reaches_database=False)

    claim = worker.claim_for_execution(ticket)
    assert claim["ok"] is False
    assert claim["state"] == "unknown"
    assert claim["may_execute_connector"] is False
    assert claim["may_retry_claim"] is False

    reconciled = worker.reconcile_claim_for_execution(ticket)
    assert reconciled["ok"] is False
    assert reconciled["state"] == "unconsumed_retryable"
    assert reconciled["may_execute_connector"] is False
    assert reconciled["may_retry_claim"] is True

    explicit_retry = normal_broker().claim_for_execution(ticket)
    assert explicit_retry["ok"] is True
    assert explicit_retry["may_execute_connector"] is True

    replay = normal_broker().claim_for_execution(ticket)
    assert replay["ok"] is False
    assert replay["reason"] == "ticket already consumed"
