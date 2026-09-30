from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class TransactionRecord:
    token_symbol: str
    paired_asset_symbol: str
    price_usd: str
    size: str
    transaction_time_utc: datetime
    published_at: datetime
    contributed_asset: str
    withdrawn_asset: str
    smart_contract_address: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["transaction_time_utc"] = _utc(self.transaction_time_utc).isoformat().replace("+00:00", "Z")
        data["published_at"] = _utc(self.published_at).isoformat().replace("+00:00", "Z")
        return data


@dataclass(frozen=True)
class TransparencyFeedState:
    free_public: bool
    machine_readable: bool
    usd_denominated: bool
    same_time_same_terms: bool
    history_start_at: datetime
    continuous_history_asserted: bool
    pricing_method_consistent_impartial_reasonable: bool
    daily_asset_pair_share_volume_present: bool
    end_of_day_pool_size_present: bool


def validate_transaction(record: TransactionRecord, *, max_publish_delay_minutes: int = 10) -> dict:
    errors: list[str] = []
    if not record.token_symbol.strip() or not record.paired_asset_symbol.strip():
        errors.append("SYMBOL_PAIR_MISSING")
    try:
        price = Decimal(record.price_usd)
        size = Decimal(record.size)
        if price <= 0:
            errors.append("PRICE_NOT_POSITIVE")
        if size <= 0:
            errors.append("SIZE_NOT_POSITIVE")
    except InvalidOperation:
        errors.append("PRICE_OR_SIZE_NOT_DECIMAL")
    tx_time = _utc(record.transaction_time_utc)
    published = _utc(record.published_at)
    if published < tx_time:
        errors.append("PUBLICATION_PRECEDES_TRANSACTION")
    elif published - tx_time > timedelta(minutes=max_publish_delay_minutes):
        errors.append("PUBLICATION_DELAY_EXCEEDS_10_MINUTES")
    if not record.contributed_asset.strip() or not record.withdrawn_asset.strip():
        errors.append("TRANSACTION_DIRECTION_INCOMPLETE")
    if record.contributed_asset.strip().upper() == record.withdrawn_asset.strip().upper():
        errors.append("TRANSACTION_DIRECTION_ASSETS_IDENTICAL")
    if not record.smart_contract_address.strip():
        errors.append("SMART_CONTRACT_ADDRESS_MISSING")
    return {
        "decision": "DENY" if errors else "ALLOW",
        "errors": errors,
        "authority": "SEC 34-106402 II.G",
        "record": record.to_dict(),
    }


def validate_feed(feed: TransparencyFeedState, *, now: datetime, required_history_days: int = 30) -> dict:
    now = _utc(now)
    errors: list[str] = []
    if not feed.free_public:
        errors.append("NOT_FREELY_PUBLIC")
    if not feed.machine_readable:
        errors.append("NOT_MACHINE_READABLE")
    if not feed.usd_denominated:
        errors.append("NOT_USD_DENOMINATED")
    if not feed.same_time_same_terms:
        errors.append("NOT_AVAILABLE_SAME_TIME_SAME_TERMS")
    if not feed.continuous_history_asserted:
        errors.append("CONTINUOUS_30_DAY_HISTORY_NOT_ASSERTED")
    if _utc(feed.history_start_at) > now - timedelta(days=required_history_days):
        errors.append("HISTORY_WINDOW_SHORTER_THAN_30_DAYS")
    if not feed.pricing_method_consistent_impartial_reasonable:
        errors.append("USD_PRICING_METHOD_CONTROL_MISSING")
    if not feed.daily_asset_pair_share_volume_present:
        errors.append("DAILY_ASSET_PAIR_SHARE_VOLUME_MISSING")
    if not feed.end_of_day_pool_size_present:
        errors.append("END_OF_DAY_POOL_SIZE_MISSING")
    return {"decision": "DENY" if errors else "ALLOW", "errors": errors, "authority": "SEC 34-106402 II.G"}


def validate_batch(records: Iterable[TransactionRecord], *, max_publish_delay_minutes: int = 10) -> dict:
    results = [validate_transaction(record, max_publish_delay_minutes=max_publish_delay_minutes) for record in records]
    return {
        "decision": "DENY" if any(r["decision"] == "DENY" for r in results) else "ALLOW",
        "count": len(results),
        "results": results,
        "authority": "SEC 34-106402 II.G",
    }
