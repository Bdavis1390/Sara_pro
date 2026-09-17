from pathlib import Path

from worldshepherd_sara.connector_claim_recovery import (
    ClaimReconciliation,
    UnknownClaimOutcome,
    reconcile_claim_status,
)
from worldshepherd_sara.connector_control import ConnectorControlPlane
from worldshepherd_sara.connector_execution import ReadExecutionBroker


MANIFEST = Path("data/worldshepherd_connectors.v2.json")


def test_reconciliation_never_authorizes_consumed_unknown_ownership():
    result = reconcile_claim_status(
        ticket_id="ticket-1",
        ticket_sha256="a" * 64,
        status={
            "known": True,
            "ticket_sha256": "a" * 64,
            "expired": False,
            "consumed": True,
        },
    )
    assert result.state == "consumed_ownership_unknown"
    assert result.may_execute_connector is False
    assert result.may_retry_claim is False


def test_reconciliation_allows_only_explicit_retry_when_fresh_status_is_unconsumed():
    result = reconcile_claim_status(
        ticket_id="ticket-2",
        ticket_sha256="b" * 64,
        status={
            "known": True,
            "ticket_sha256": "b" * 64,
            "expired": False,
            "consumed": False,
        },
    )
    assert result.state == "unconsumed_retryable"
    assert result.may_execute_connector is False
    assert result.may_retry_claim is True


def test_reconciliation_blocks_expired_digest_mismatch_and_missing_records():
    expired = reconcile_claim_status(
        ticket_id="ticket-3",
        ticket_sha256="c" * 64,
        status={
            "known": True,
            "ticket_sha256": "c" * 64,
            "expired": True,
            "consumed": False,
        },
    )
    mismatch = reconcile_claim_status(
        ticket_id="ticket-4",
        ticket_sha256="d" * 64,
        status={
            "known": True,
            "ticket_sha256": "e" * 64,
            "expired": False,
            "consumed": False,
        },
    )
    missing = reconcile_claim_status(
        ticket_id="ticket-5",
        ticket_sha256="f" * 64,
        status={"known": False},
    )
    for result in (expired, mismatch, missing):
        assert result.may_execute_connector is False
        assert result.may_retry_claim is False


class _UnknownLedger:
    def claim(self, ticket, *, now=None):
        raise UnknownClaimOutcome(str(ticket.get("ticket_id", "")))

    def reconcile_unknown_claim(self, ticket):
        return ClaimReconciliation(
            state="consumed_ownership_unknown",
            ticket_id=str(ticket.get("ticket_id", "")),
            reason="synthetic consumed unknown ownership",
        )


class _RetryableLedger:
    def claim(self, ticket, *, now=None):
        raise UnknownClaimOutcome(str(ticket.get("ticket_id", "")))

    def reconcile_unknown_claim(self, ticket):
        return ClaimReconciliation(
            state="unconsumed_retryable",
            ticket_id=str(ticket.get("ticket_id", "")),
            reason="synthetic fresh unconsumed observation",
            may_retry_claim=True,
        )


def test_broker_converts_unknown_exception_into_non_authorizing_state():
    broker = ReadExecutionBroker(ConnectorControlPlane(MANIFEST), ledger=_UnknownLedger())
    result = broker.claim_for_execution({"ticket_id": "ticket-6"})
    assert result["ok"] is False
    assert result["state"] == "unknown"
    assert result["may_execute_connector"] is False
    assert result["may_retry_claim"] is False


def test_broker_reconciliation_keeps_consumed_unknown_non_executable():
    broker = ReadExecutionBroker(ConnectorControlPlane(MANIFEST), ledger=_UnknownLedger())
    result = broker.reconcile_claim_for_execution({"ticket_id": "ticket-7"})
    assert result["ok"] is False
    assert result["state"] == "consumed_ownership_unknown"
    assert result["may_execute_connector"] is False
    assert result["may_retry_claim"] is False


def test_broker_reconciliation_marks_unconsumed_only_as_retryable():
    broker = ReadExecutionBroker(ConnectorControlPlane(MANIFEST), ledger=_RetryableLedger())
    result = broker.reconcile_claim_for_execution({"ticket_id": "ticket-8"})
    assert result["ok"] is False
    assert result["state"] == "unconsumed_retryable"
    assert result["may_execute_connector"] is False
    assert result["may_retry_claim"] is True
