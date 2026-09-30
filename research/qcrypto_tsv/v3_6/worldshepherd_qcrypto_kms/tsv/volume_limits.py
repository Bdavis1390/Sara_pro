from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping


TIER_LIMITS = {
    1: {"max_symbols": 75, "max_share": Decimal("0.0025")},
    2: {"max_symbols": 250, "max_share": Decimal("0.025")},
}


@dataclass(frozen=True)
class AffiliateVolumeObservation:
    venue_id: str
    symbol: str
    tier: int
    tokenized_average_daily_share_volume: Decimal
    sip_prior_month_average_daily_share_volume: Decimal

    @classmethod
    def create(cls, *, venue_id: str, symbol: str, tier: int, tokenized_average_daily_share_volume: object, sip_prior_month_average_daily_share_volume: object) -> "AffiliateVolumeObservation":
        try:
            num = Decimal(str(tokenized_average_daily_share_volume))
            den = Decimal(str(sip_prior_month_average_daily_share_volume))
        except InvalidOperation as exc:
            raise ValueError("volume values must be decimal-compatible") from exc
        return cls(venue_id.strip(), symbol.upper().strip(), int(tier), num, den)


@dataclass(frozen=True)
class AggregateVolumeResult:
    symbol: str
    tier: int
    affiliate_count: int
    numerator_tokenized_adv: str
    denominator_sip_adv: str
    aggregate_share: str
    threshold_share: str
    exceeded: bool
    decision: str
    authority: str = "SEC 34-106402 II.F"

    def to_dict(self) -> dict:
        return asdict(self)


def aggregate_affiliate_volume(observations: Iterable[AffiliateVolumeObservation]) -> AggregateVolumeResult:
    rows = list(observations)
    if not rows:
        raise ValueError("at least one affiliate volume observation is required")
    symbol = rows[0].symbol
    tier = rows[0].tier
    if tier not in TIER_LIMITS:
        raise ValueError("tier must be 1 or 2")
    if not symbol:
        raise ValueError("symbol is required")
    venue_ids = set()
    denominators = set()
    numerator = Decimal("0")
    for row in rows:
        if row.symbol != symbol or row.tier != tier:
            raise ValueError("all affiliate observations must refer to the same symbol and tier")
        if not row.venue_id or row.venue_id in venue_ids:
            raise ValueError("affiliate venue_id values must be nonempty and unique")
        venue_ids.add(row.venue_id)
        if row.tokenized_average_daily_share_volume < 0:
            raise ValueError("tokenized average daily share volume cannot be negative")
        if row.sip_prior_month_average_daily_share_volume <= 0:
            raise ValueError("SIP prior-month average daily share volume must be positive")
        denominators.add(row.sip_prior_month_average_daily_share_volume)
        numerator += row.tokenized_average_daily_share_volume
    if len(denominators) != 1:
        raise ValueError("affiliate observations must use one consistent SIP denominator for the same symbol/month")
    denominator = next(iter(denominators))
    share = numerator / denominator
    threshold = TIER_LIMITS[tier]["max_share"]
    exceeded = share > threshold
    return AggregateVolumeResult(
        symbol=symbol,
        tier=tier,
        affiliate_count=len(venue_ids),
        numerator_tokenized_adv=str(numerator),
        denominator_sip_adv=str(denominator),
        aggregate_share=str(share),
        threshold_share=str(threshold),
        exceeded=exceeded,
        decision="EXCEEDED" if exceeded else "WITHIN_LIMIT",
    )


@dataclass(frozen=True)
class AffiliateSymbolInventory:
    venue_id: str
    tier1_symbols: frozenset[str]
    tier2_symbols: frozenset[str]

    @classmethod
    def create(cls, venue_id: str, *, tier1_symbols: Iterable[str] = (), tier2_symbols: Iterable[str] = ()) -> "AffiliateSymbolInventory":
        return cls(
            venue_id.strip(),
            frozenset(s.upper().strip() for s in tier1_symbols if s.strip()),
            frozenset(s.upper().strip() for s in tier2_symbols if s.strip()),
        )


def aggregate_affiliate_symbol_counts(inventories: Iterable[AffiliateSymbolInventory]) -> dict:
    rows = list(inventories)
    if not rows:
        raise ValueError("at least one affiliate inventory is required")
    seen_venues = set()
    tier1 = set()
    tier2 = set()
    for row in rows:
        if not row.venue_id or row.venue_id in seen_venues:
            raise ValueError("affiliate venue_id values must be nonempty and unique")
        seen_venues.add(row.venue_id)
        overlap = row.tier1_symbols & row.tier2_symbols
        if overlap:
            raise ValueError(f"symbols cannot be both Tier 1 and Tier 2 in one inventory: {sorted(overlap)!r}")
        tier1.update(row.tier1_symbols)
        tier2.update(row.tier2_symbols)
    cross = tier1 & tier2
    if cross:
        raise ValueError(f"affiliate inventories disagree on LULD tier for symbols: {sorted(cross)!r}")
    return {
        "tier1_unique_symbols": len(tier1),
        "tier2_unique_symbols": len(tier2),
        "tier1_limit": TIER_LIMITS[1]["max_symbols"],
        "tier2_limit": TIER_LIMITS[2]["max_symbols"],
        "tier1_decision": "ALLOW" if len(tier1) <= TIER_LIMITS[1]["max_symbols"] else "DENY",
        "tier2_decision": "ALLOW" if len(tier2) <= TIER_LIMITS[2]["max_symbols"] else "DENY",
        "authority": "SEC 34-106402 II.F",
    }
