from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any, Iterable


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class DuplicateEventError(ValueError):
    pass


@dataclass(frozen=True)
class NewsEvent:
    event_id: str
    asset: str
    value_delta: float
    timestamp: int


@dataclass(frozen=True)
class Agent:
    agent_id: str
    asset: str
    base_value: float
    bid_multiplier: float = 1.0

    def true_value(self, news: Iterable[NewsEvent]) -> float:
        delta = sum(e.value_delta for e in news if e.asset == self.asset)
        return max(0.0, self.base_value + delta)

    def bid(self, news: Iterable[NewsEvent]) -> float:
        return round(self.true_value(news) * self.bid_multiplier, 8)


@dataclass(frozen=True)
class LedgerEvent:
    seq: int
    event_id: str
    kind: str
    payload: dict[str, Any]
    prev_hash: str
    event_hash: str


class EventLedger:
    def __init__(self) -> None:
        self._events: list[LedgerEvent] = []
        self._ids: set[str] = set()

    @property
    def events(self) -> tuple[LedgerEvent, ...]:
        return tuple(self._events)

    def append(self, event_id: str, kind: str, payload: dict[str, Any]) -> LedgerEvent:
        if event_id in self._ids:
            raise DuplicateEventError(event_id)

        prev_hash = self._events[-1].event_hash if self._events else "GENESIS"
        material = {
            "seq": len(self._events),
            "event_id": event_id,
            "kind": kind,
            "payload": payload,
            "prev_hash": prev_hash,
        }
        event_hash = sha256(_canonical(material).encode()).hexdigest()
        event = LedgerEvent(event_hash=event_hash, **material)
        self._events.append(event)
        self._ids.add(event_id)
        return event

    def verify(self) -> bool:
        prev_hash = "GENESIS"
        seen: set[str] = set()

        for seq, event in enumerate(self._events):
            if event.seq != seq or event.event_id in seen or event.prev_hash != prev_hash:
                return False

            material = {
                "seq": event.seq,
                "event_id": event.event_id,
                "kind": event.kind,
                "payload": event.payload,
                "prev_hash": event.prev_hash,
            }
            if sha256(_canonical(material).encode()).hexdigest() != event.event_hash:
                return False

            seen.add(event.event_id)
            prev_hash = event.event_hash

        return True

    def digest(self) -> str:
        if not self._events:
            return sha256(b"").hexdigest()
        return self._events[-1].event_hash


@dataclass(frozen=True)
class MarketResult:
    winner_id: str | None
    clearing_price: float | None
    allocative_efficiency: float
    bids: dict[str, float]
    true_values: dict[str, float]
    ledger_digest: str


@dataclass(frozen=True)
class ShadingClassification:
    agent_id: str
    bid_to_value_ratio: float
    label: str


def classify_bid_shading(
    result: MarketResult,
    low: float = 0.8,
    high: float = 1.2,
) -> list[ShadingClassification]:
    classifications: list[ShadingClassification] = []

    for agent_id, bid in sorted(result.bids.items()):
        value = result.true_values[agent_id]
        ratio = (
            1.0
            if value == 0 and bid == 0
            else (float("inf") if value == 0 else bid / value)
        )

        if ratio < low:
            label = "underbid"
        elif ratio > high:
            label = "overbid"
        else:
            label = "near_value"

        classifications.append(
            ShadingClassification(agent_id, round(ratio, 8), label)
        )

    return classifications


def run_sealed_bid_market(
    *,
    asset: str,
    agents: Iterable[Agent],
    news: Iterable[NewsEvent],
    reserve_price: float = 0.0,
) -> tuple[MarketResult, EventLedger]:
    agents = tuple(sorted(agents, key=lambda a: a.agent_id))
    news = tuple(sorted(news, key=lambda e: (e.timestamp, e.event_id)))
    ledger = EventLedger()

    ledger.append(
        "market-config",
        "market_config",
        {
            "mechanism": "sealed_bid_second_price",
            "asset": asset,
            "reserve_price": reserve_price,
        },
    )

    for event in news:
        ledger.append(event.event_id, "news", asdict(event))

    true_values: dict[str, float] = {}
    bids: dict[str, float] = {}

    for agent in agents:
        if agent.asset != asset:
            continue

        value = round(agent.true_value(news), 8)
        bid = agent.bid(news)
        true_values[agent.agent_id] = value
        bids[agent.agent_id] = bid

        ledger.append(
            f"bid:{agent.agent_id}",
            "bid",
            {
                "agent_id": agent.agent_id,
                "asset": asset,
                "bid": bid,
                "true_value": value,
            },
        )

    ranked = sorted(bids.items(), key=lambda item: (-item[1], item[0]))

    winner_id: str | None = None
    clearing_price: float | None = None

    if ranked and ranked[0][1] >= reserve_price:
        winner_id = ranked[0][0]
        second = ranked[1][1] if len(ranked) > 1 else reserve_price
        clearing_price = round(max(reserve_price, second), 8)

    max_value = max(true_values.values(), default=0.0)
    if winner_id is None:
        efficiency = 1.0 if max_value == 0.0 else 0.0
    else:
        efficiency = true_values[winner_id] / max_value if max_value else 1.0

    ledger.append(
        "market-result",
        "result",
        {
            "winner_id": winner_id,
            "clearing_price": clearing_price,
            "allocative_efficiency": round(efficiency, 8),
        },
    )

    return (
        MarketResult(
            winner_id=winner_id,
            clearing_price=clearing_price,
            allocative_efficiency=round(efficiency, 8),
            bids=bids,
            true_values=true_values,
            ledger_digest=ledger.digest(),
        ),
        ledger,
    )
