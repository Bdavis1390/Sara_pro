from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
from typing import Iterable, Optional, Mapping

from .operational_events import SignificantOperationalEvent, evaluate_operational_event
from .regulatory_clock import DeadlineEvaluation, exemption_window_status, operations_start_status
from .runtime import AuthorizationBundle, authorize_bundle
from .source_evidence import SourceEvidence
from .transaction_transparency import TransactionRecord, TransparencyFeedState, validate_batch, validate_feed
from .volume_limits import AffiliateVolumeObservation, aggregate_affiliate_volume
from .market_data_adapter import MarketDataMessage, validate_market_batch
from .issuer_delivery import IssuerDeliveryReceipt, validate_issuer_delivery
from .provider_resilience import (
    ProviderHealth, ProviderRoute, CalendarEvidence, select_provider, validate_calendar_evidence,
)


def _canon(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class OperationalAuthorization:
    decision: str
    failures: tuple[str, ...]
    base_authorization: dict
    exemption_window: dict
    deadlines: tuple[dict, ...]
    transparency_feed: Optional[dict]
    transaction_batch: Optional[dict]
    aggregate_volume: Optional[dict]
    operational_event: Optional[dict]
    market_data_batch: Optional[dict]
    issuer_delivery: Optional[dict]
    provider_failover: Optional[dict]
    calendar_evidence: Optional[dict]
    runtime_sha256: str
    claims_label: str = "IMPLEMENTED_IN_SOFTWARE_NOT_SEC_APPROVAL"

    def to_dict(self) -> dict:
        return asdict(self)


def authorize_operational_tsv(
    state: dict,
    notice: dict,
    *,
    now: datetime,
    symbol: Optional[str] = None,
    market_evidence: Optional[SourceEvidence] = None,
    market_evidence_max_age_seconds: int = 30,
    require_market_evidence: bool = False,
    deadlines: Iterable[DeadlineEvaluation] = (),
    transparency_feed: Optional[TransparencyFeedState] = None,
    require_transparency_feed: bool = False,
    transactions: Iterable[TransactionRecord] = (),
    volume_observations: Iterable[AffiliateVolumeObservation] = (),
    operational_event: Optional[SignificantOperationalEvent] = None,
    market_messages: Iterable[MarketDataMessage] = (),
    market_source_registry: Optional[Mapping[str, set[str] | frozenset[str]]] = None,
    require_market_adapter: bool = False,
    issuer_delivery_receipt: Optional[IssuerDeliveryReceipt] = None,
    issuer_notice_sha256: Optional[str] = None,
    require_issuer_delivery: bool = False,
    provider_route: Optional[ProviderRoute] = None,
    provider_health: Iterable[ProviderHealth] = (),
    provider_registry: Optional[Mapping[str, set[str] | frozenset[str]]] = None,
    require_provider_resilience: bool = False,
    calendar_evidence: Optional[CalendarEvidence] = None,
    calendar_provider_registry: Optional[set[str] | frozenset[str]] = None,
    require_calendar_evidence: bool = False,
) -> OperationalAuthorization:
    base: AuthorizationBundle = authorize_bundle(
        state,
        notice,
        now=now,
        symbol=symbol,
        market_evidence=market_evidence,
        market_evidence_max_age_seconds=market_evidence_max_age_seconds,
        require_market_evidence=require_market_evidence,
    )
    exemption = exemption_window_status(now)
    operation_start = None
    if state.get("operations_start_at"):
        try:
            operation_start = operations_start_status(datetime.fromisoformat(str(state["operations_start_at"]).replace("Z", "+00:00")))
        except (ValueError, TypeError):
            operation_start = {"decision": "DENY", "authority": "SEC 34-106402 V / VII", "note": "operations_start_at is malformed"}
    deadline_rows = tuple(d.to_dict() for d in deadlines)

    feed_result: Optional[dict] = None
    if transparency_feed is not None:
        feed_result = validate_feed(transparency_feed, now=now)
    elif require_transparency_feed:
        feed_result = {"decision": "DENY", "errors": ["TRANSPARENCY_FEED_REQUIRED_BUT_ABSENT"], "authority": "SEC 34-106402 II.G"}

    tx_rows = list(transactions)
    tx_result = validate_batch(tx_rows) if tx_rows else None

    volume_rows = list(volume_observations)
    volume_result = aggregate_affiliate_volume(volume_rows).to_dict() if volume_rows else None

    event_result = evaluate_operational_event(operational_event, now=now) if operational_event is not None else None

    market_rows = list(market_messages)
    market_batch_result: Optional[dict] = None
    if market_rows or require_market_adapter:
        if not symbol:
            market_batch_result = {"decision": "DENY", "errors": ["SYMBOL_REQUIRED_FOR_MARKET_ADAPTER"]}
        elif market_source_registry is None:
            market_batch_result = {"decision": "DENY", "errors": ["MARKET_SOURCE_REGISTRY_REQUIRED"]}
        else:
            market_batch_result = validate_market_batch(
                market_rows, expected_symbol=symbol, now=now, source_registry=market_source_registry
            ).to_dict()

    issuer_result: Optional[dict] = None
    if issuer_delivery_receipt is not None or require_issuer_delivery:
        trading_raw = state.get("symbol_trading_start_at")
        try:
            trading_at = datetime.fromisoformat(str(trading_raw).replace("Z", "+00:00")) if trading_raw else None
        except (ValueError, TypeError):
            trading_at = None
        if not symbol or not issuer_notice_sha256 or trading_at is None:
            issuer_result = {"decision": "DENY", "errors": ["ISSUER_DELIVERY_CONTEXT_INCOMPLETE"]}
        else:
            issuer_result = validate_issuer_delivery(
                issuer_delivery_receipt, expected_symbol=symbol, expected_notice_sha256=issuer_notice_sha256,
                trading_start_at=trading_at, now=now
            ).to_dict()

    provider_result: Optional[dict] = None
    health_rows = list(provider_health)
    if provider_route is not None or health_rows or require_provider_resilience:
        if provider_route is None or provider_registry is None:
            provider_result = {"decision": "DENY", "errors": ["PROVIDER_RESILIENCE_CONTEXT_INCOMPLETE"]}
        else:
            provider_result = select_provider(
                provider_route, health_rows, now=now, provider_registry=provider_registry
            ).to_dict()

    calendar_result: Optional[dict] = None
    if calendar_evidence is not None or require_calendar_evidence:
        if calendar_evidence is None or calendar_provider_registry is None:
            calendar_result = {"decision": "DENY", "errors": ["CALENDAR_EVIDENCE_CONTEXT_INCOMPLETE"]}
        else:
            calendar_result = validate_calendar_evidence(
                calendar_evidence, expected_session_date=now.date(), now=now,
                provider_registry=calendar_provider_registry
            ).to_dict()

    failures = []
    if base.decision == "DENY": failures.append("BASE_AUTHORIZATION")
    if exemption["decision"] == "DENY": failures.append("EXEMPTION_WINDOW")
    if operation_start is not None and operation_start["decision"] == "DENY": failures.append("OPERATIONS_START_OUTSIDE_EXEMPTION_WINDOW")
    if any(d["status"] == "FAIL" for d in deadline_rows): failures.append("DEADLINE")
    if feed_result is not None and feed_result["decision"] == "DENY": failures.append("TRANSPARENCY_FEED")
    if tx_result is not None and tx_result["decision"] == "DENY": failures.append("TRANSACTION_BATCH")
    if event_result is not None and event_result["decision"] == "DENY": failures.append("OPERATIONAL_EVENT")
    if market_batch_result is not None and market_batch_result["decision"] == "DENY": failures.append("MARKET_DATA_ADAPTER")
    if issuer_result is not None and issuer_result["decision"] == "DENY": failures.append("ISSUER_DELIVERY")
    if provider_result is not None and provider_result["decision"] == "DENY": failures.append("PROVIDER_RESILIENCE")
    if calendar_result is not None and calendar_result["decision"] == "DENY": failures.append("CALENDAR_EVIDENCE")

    warnings = base.decision == "ALLOW_WITH_WARNINGS" or any(d["status"] in {"PENDING", "BLOCKED"} for d in deadline_rows)
    decision = "DENY" if failures else "ALLOW_WITH_WARNINGS" if warnings else "ALLOW"

    material = {
        "schema": "WS-TSV-OPERATIONAL-AUTHORIZATION-V1",
        "decision": decision,
        "failures": failures,
        "base_decision_sha256": base.decision_sha256,
        "base_evidence_head": base.evidence_head,
        "exemption_window": exemption,
        "operations_start_window": operation_start,
        "deadlines": deadline_rows,
        "transparency_feed": feed_result,
        "transaction_batch": tx_result,
        "aggregate_volume": volume_result,
        "operational_event": event_result,
        "market_data_batch": market_batch_result,
        "issuer_delivery": issuer_result,
        "provider_failover": provider_result,
        "calendar_evidence": calendar_result,
    }
    digest = hashlib.sha256(b"WS-TSV-OPERATIONAL-AUTHORIZATION-V1\x00" + _canon(material)).hexdigest()
    return OperationalAuthorization(
        decision=decision,
        failures=tuple(failures),
        base_authorization=base.to_dict(),
        exemption_window=exemption,
        deadlines=deadline_rows,
        transparency_feed=feed_result,
        transaction_batch=tx_result,
        aggregate_volume=volume_result,
        operational_event=event_result,
        market_data_batch=market_batch_result,
        issuer_delivery=issuer_result,
        provider_failover=provider_result,
        calendar_evidence=calendar_result,
        runtime_sha256=digest,
    )
