from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .evidence import EvidenceChain, canonical_json, sha256_hex
from .notice import validate_notice
from .policy import evaluate_tsv
from .source_evidence import SourceEvidence, validate_source_evidence


@dataclass(frozen=True)
class AuthorizationBundle:
    decision: str
    policy: Dict[str, Any]
    notice: Dict[str, Any]
    market_evidence: Optional[Dict[str, Any]]
    decision_sha256: str
    evidence_head: str
    claims_label: str = "IMPLEMENTED_IN_SOFTWARE"
    deployment_label: str = "TESTED_LOCAL_NOT_DEPLOYED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "policy": self.policy,
            "notice": self.notice,
            "market_evidence": self.market_evidence,
            "decision_sha256": self.decision_sha256,
            "evidence_head": self.evidence_head,
            "claims_label": self.claims_label,
            "deployment_label": self.deployment_label,
        }


def authorize_bundle(
    state: Dict[str, Any],
    notice: Dict[str, Any],
    *,
    now: Optional[datetime] = None,
    symbol: Optional[str] = None,
    market_evidence: Optional[SourceEvidence] = None,
    market_evidence_max_age_seconds: int = 30,
    require_market_evidence: bool = False,
    chain: Optional[EvidenceChain] = None,
) -> AuthorizationBundle:
    """Combine policy, public-Notice, optional source evidence and ECHO-like receipts.

    This function authorizes only the modeled software path; it cannot establish
    legal/regulatory compliance or authorize a real securities transaction.
    """
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    policy_result = evaluate_tsv(state, now=now).to_dict()
    notice_result = validate_notice(notice).to_dict()

    evidence_result: Optional[Dict[str, Any]] = None
    evidence_allowed = True
    if require_market_evidence:
        if not symbol:
            evidence_result = {"decision": "DENY", "reason": "symbol is required when market evidence is required"}
            evidence_allowed = False
        else:
            checked = validate_source_evidence(
                market_evidence,
                expected_symbol=symbol,
                now=now,
                max_age_seconds=market_evidence_max_age_seconds,
                allowed_source_kinds={"SIP", "PRIMARY_LISTING_EXCHANGE", "LULD_PLAN"},
            )
            evidence_result = checked.to_dict()
            evidence_allowed = checked.decision == "ALLOW"

    allowed = policy_result["decision"] != "DENY" and notice_result["decision"] != "DENY" and evidence_allowed
    warning = policy_result["decision"] == "ALLOW_WITH_WARNINGS"
    decision = "DENY" if not allowed else "ALLOW_WITH_WARNINGS" if warning else "ALLOW"

    decision_material = {
        "decision": decision,
        "state_sha256": sha256_hex(canonical_json(state)),
        "notice_sha256": sha256_hex(canonical_json(notice)),
        "policy": policy_result,
        "notice": notice_result,
        "market_evidence": evidence_result,
        "evaluated_at": now.isoformat().replace("+00:00", "Z"),
    }
    decision_sha = sha256_hex(canonical_json(decision_material))

    chain = chain or EvidenceChain()
    chain.append("TSV_AUTHORIZATION_DECISION", {**decision_material, "decision_sha256": decision_sha}, occurred_at=now)

    return AuthorizationBundle(
        decision=decision,
        policy=policy_result,
        notice=notice_result,
        market_evidence=evidence_result,
        decision_sha256=decision_sha,
        evidence_head=chain.head(),
    )
