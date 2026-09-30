from __future__ import annotations
from typing import Optional, Dict, Any
import hashlib
import json
from worldshepherd_time_authority_v0_2 import TimeDecision


class EchoTimeCustody:
    """ECHO receipt custody with explicit time-anchor provenance and uncertainty.

    SHA-256 provides deterministic content binding only. It is not a digital
    signature, RFC 3161 timestamp, trusted timestamp authority, or proof of UTC.
    """

    def __init__(self, *, require_external_anchor_for_absolute: bool = False):
        self._last_counter: Optional[int] = None
        self._last_digest: Optional[str] = None
        self.require_external_anchor_for_absolute = require_external_anchor_for_absolute

    @staticmethod
    def _canonical(obj: Dict[str, Any]) -> bytes:
        return json.dumps(
            obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")

    def issue(
        self,
        *,
        event_id: str,
        event_counter: int,
        payload_digest: str,
        time_decision: TimeDecision,
    ) -> Dict[str, Any]:
        if not event_id:
            raise ValueError("event_id required")
        if event_counter < 0:
            raise ValueError("event_counter must be nonnegative")
        if self._last_counter is not None and event_counter <= self._last_counter:
            raise ValueError("event_counter must increase monotonically")
        if len(payload_digest) != 64 or any(
            c not in "0123456789abcdef" for c in payload_digest.lower()
        ):
            raise ValueError("payload_digest must be a 64-hex SHA-256 digest")

        trusted_state = (
            time_decision.state == "TRUSTED"
            and time_decision.consensus_time is not None
        )
        anchor_requirement_met = (
            not self.require_external_anchor_for_absolute
            or time_decision.anchor_source == "EXTERNAL_INTERVAL_CALIBRATION"
        )
        trusted_absolute = trusted_state and anchor_requirement_met

        custody_reasons = list(time_decision.reasons)
        if trusted_state and not anchor_requirement_met:
            custody_reasons.append("ECHO_EXTERNAL_ANCHOR_REQUIRED")

        receipt = {
            "schema": "WS-ECHO-TIME-RECEIPT-0.2",
            "event_id": event_id,
            "event_counter": event_counter,
            "ordering_mode": (
                "ABSOLUTE_PLUS_MONOTONIC" if trusted_absolute else "MONOTONIC_ONLY"
            ),
            "payload_digest": payload_digest.lower(),
            "parent_receipt_digest": self._last_digest,
            "time": {
                "authority_state": time_decision.state,
                "absolute_time_authorized": trusted_absolute,
                "authoritative_time": (
                    time_decision.consensus_time if trusted_absolute else None
                ),
                "observed_consensus_time": time_decision.consensus_time,
                "agreeing_sources": list(time_decision.agreeing_sources),
                "source_count": time_decision.source_count,
                "dispersion_s": time_decision.dispersion_s,
                "holdover_error_s": time_decision.holdover_error_s,
                "holdover_bound_s": time_decision.holdover_bound_s,
                "anchor_source": time_decision.anchor_source,
                "anchor_uncertainty_s": time_decision.anchor_uncertainty_s,
                "external_anchor_required_by_echo": self.require_external_anchor_for_absolute,
                "anchor_requirement_met": anchor_requirement_met,
                "reasons": custody_reasons,
            },
        }
        digest = hashlib.sha256(self._canonical(receipt)).hexdigest()
        receipt["receipt_digest"] = digest
        self._last_counter = event_counter
        self._last_digest = digest
        return receipt

    @staticmethod
    def verify_digest(receipt: Dict[str, Any]) -> bool:
        candidate = dict(receipt)
        supplied = candidate.pop("receipt_digest", None)
        if not isinstance(supplied, str):
            return False
        return hashlib.sha256(EchoTimeCustody._canonical(candidate)).hexdigest() == supplied
