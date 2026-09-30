from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


NOTICE_SECTIONS = {
    "a": "disclaimer",
    "b": "use_of_exemption",
    "c": "venue_overview",
    "d": "non_exempt_activities",
    "e": "tsv_participants",
    "f": "permissioned_access_eligibility",
    "g": "assets_traded",
    "h": "tokenization_of_securities",
    "i": "rights_equivalence_verification",
    "j": "issuer_objections",
    "k": "tokenization_by_tsv_or_affiliates",
    "l": "trading_by_tsv_or_affiliates",
    "m": "participant_treatment_differences",
    "n": "distributed_ledger_technology",
    "o": "entry_of_trading_interest",
    "p": "amm_liquidity_pool_trading_procedures",
    "q": "offchain_trading_procedures",
    "r": "hours_of_operations",
    "s": "market_data_and_oracles",
    "t": "display_and_transaction_dissemination",
    "u": "fees_rebates_discounts_compensation",
    "v": "complaints_execution_errors_disputes",
    "w": "participant_information_and_mev",
    "x": "systems_safeguards",
    "y": "clearing_and_settlement",
    "z": "material_risks_and_mitigations",
    "aa": "service_providers",
    "bb": "trading_oversight",
    "cc": "trading_stoppage_and_resumption",
    "dd": "exclusive_or_predominant_venue_risk",
}


@dataclass(frozen=True)
class NoticeFinding:
    section: str
    key: str
    status: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NoticeEvaluation:
    decision: str
    findings: List[NoticeFinding]

    def to_dict(self) -> Dict[str, Any]:
        return {"decision": self.decision, "findings": [f.to_dict() for f in self.findings]}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


def validate_notice(notice: Dict[str, Any]) -> NoticeEvaluation:
    findings: List[NoticeFinding] = []
    for section, key in NOTICE_SECTIONS.items():
        ok = _present(notice.get(key))
        findings.append(NoticeFinding(
            section=section,
            key=key,
            status="PASS" if ok else "FAIL",
            message=(
                f"Section III.{section} ({key}) is present."
                if ok else f"Section III.{section} ({key}) is missing or empty."
            ),
        ))

    disclaimer = notice.get("disclaimer")
    if isinstance(disclaimer, dict):
        required = {
            "not_registered_with_sec": True,
            "sec_has_not_passed_on_merits_or_accuracy": True,
            "not_subject_to_fair_access_requirements": True,
            "denials_not_subject_to_sec_review": True,
            "not_subject_to_regulation_nms": True,
        }
        for key, expected in required.items():
            ok = disclaimer.get(key) is expected
            findings.append(NoticeFinding(
                section="a",
                key=f"disclaimer.{key}",
                status="PASS" if ok else "FAIL",
                message=(f"Required disclaimer assertion {key} is present."
                         if ok else f"Required disclaimer assertion {key} is absent or false."),
            ))
    else:
        findings.append(NoticeFinding(
            section="a", key="disclaimer.structured_assertions", status="FAIL",
            message="Disclaimer must be a structured object so mandatory assertions can be verified."
        ))

    decision = "DENY" if any(f.status == "FAIL" for f in findings) else "ALLOW"
    return NoticeEvaluation(decision=decision, findings=findings)
