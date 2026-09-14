import os
from pathlib import Path

import psycopg
import pytest

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


def reset_table():
    with connection_factory() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DROP TRIGGER IF EXISTS ws_fail_claim_trigger ON worldshepherd_connector_read_tickets")
            cursor.execute("DROP FUNCTION IF EXISTS ws_fail_claim()")
            cursor.execute("TRUNCATE TABLE worldshepherd_connector_read_tickets")


def broker():
    return ReadExecutionBroker(
        ConnectorControlPlane(MANIFEST),
        ledger=SharedReadTicketLedger(store()),
    )


def issue_ticket():
    planned = broker().plan_read(
        connector_id="web_research",
        action="research.search",
        actor="operator",
        data_class="PUBLIC",
        context={"query": "failure-injection"},
        ttl_seconds=60,
    )
    assert planned.ok and planned.ticket is not None
    return planned.ticket


def setup_module():
    store().initialize()


def test_database_transaction_abort_does_not_consume_ticket():
    reset_table()
    ticket = issue_ticket()

    with connection_factory() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE FUNCTION ws_fail_claim() RETURNS trigger
                LANGUAGE plpgsql AS $$
                BEGIN
                    RAISE EXCEPTION 'worldshepherd injected claim transaction failure';
                END;
                $$
                """
            )
            cursor.execute(
                """
                CREATE TRIGGER ws_fail_claim_trigger
                BEFORE UPDATE ON worldshepherd_connector_read_tickets
                FOR EACH ROW EXECUTE FUNCTION ws_fail_claim()
                """
            )

    try:
        with pytest.raises(psycopg.Error):
            broker().claim_for_execution(ticket)
    finally:
        with connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DROP TRIGGER IF EXISTS ws_fail_claim_trigger ON worldshepherd_connector_read_tickets")
                cursor.execute("DROP FUNCTION IF EXISTS ws_fail_claim()")

    status = store().status(ticket["ticket_id"])
    assert status["known"] is True
    assert status["consumed"] is False

    recovered = broker().claim_for_execution(ticket)
    assert recovered["ok"] is True


def test_forced_backend_termination_fails_closed_then_fresh_connection_claims():
    reset_table()
    ticket = issue_ticket()

    doomed = psycopg.connect(DSN)
    backend_pid = doomed.info.backend_pid
    with connection_factory() as killer:
        with killer.cursor() as cursor:
            cursor.execute("SELECT pg_terminate_backend(%s)", (backend_pid,))
            assert cursor.fetchone()[0] is True

    dead_store = PostgresClaimStore(lambda: doomed)
    dead_ledger = SharedReadTicketLedger(dead_store)
    with pytest.raises(psycopg.Error):
        dead_ledger.claim(ticket)

    status = store().status(ticket["ticket_id"])
    assert status["known"] is True
    assert status["consumed"] is False

    recovered = broker().claim_for_execution(ticket)
    assert recovered["ok"] is True
