from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    NOT_EVALUATED = "NOT_EVALUATED"


@dataclass(frozen=True)
class Finding:
    control_id: str
    status: Status
    message: str
    authority: str
    ws_component: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass(frozen=True)
class Evaluation:
    decision: str
    findings: List[Finding]
    claims_label: str = "IMPLEMENTED_IN_SOFTWARE"
    deployment_label: str = "TESTED_LOCAL_NOT_DEPLOYED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "claims_label": self.claims_label,
            "deployment_label": self.deployment_label,
            "findings": [f.to_dict() for f in self.findings],
        }


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _finding(cid: str, ok: bool, pass_msg: str, fail_msg: str, authority: str, component: str) -> Finding:
    return Finding(cid, Status.PASS if ok else Status.FAIL, pass_msg if ok else fail_msg, authority, component)


def evaluate_tsv(state: Dict[str, Any], *, now: Optional[datetime] = None) -> Evaluation:
    """Evaluate a bounded subset of SEC Release 34-106402 TSV conditions.

    This is a software compliance control profile, not legal advice and not an SEC
    determination. A FAIL is fail-closed for the modeled authorization path.
    """
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    findings: List[Finding] = []

    # II.A - distributed ledger applications
    findings.append(_finding(
        "TSV-DLT-001",
        bool(state.get("smart_contract_source_public"))
        and bool(state.get("smart_contract_auditable"))
        and bool(state.get("public_permissionless_ledger")),
        "Distributed-ledger application is public, auditable, and deployed on a public permissionless ledger.",
        "Distributed-ledger application fails public/auditable/public-permissionless requirements.",
        "SEC 34-106402 II.A",
        "QCRYPTO+ECHO",
    ))

    # II.B - U.S. person / sanctions posture
    findings.append(_finding(
        "TSV-ORG-001",
        bool(state.get("tsv_is_us_person")),
        "TSV is represented as a U.S. person for this control evaluation.",
        "TSV is not represented as a U.S. person.",
        "SEC 34-106402 II.B",
        "PRIME",
    ))
    findings.append(_finding(
        "TSV-ACCESS-001",
        bool(state.get("identity_verification"))
        and bool(state.get("wallet_verification"))
        and bool(state.get("ofac_screening"))
        and bool(state.get("aml_cft_controls")),
        "Participant identity, wallet, OFAC, and AML/CFT controls are present.",
        "One or more participant identity/wallet/OFAC/AML-CFT controls are absent.",
        "SEC 34-106402 III.f / II.B",
        "PRIME",
    ))

    # II.C - public notice timing
    notice = _parse_dt(state.get("public_notice_published_at"))
    operate = _parse_dt(state.get("operations_start_at"))
    notice_ok = bool(notice and operate and operate - notice >= timedelta(days=30))
    findings.append(_finding(
        "TSV-NOTICE-001",
        notice_ok,
        "Public Notice timing satisfies the modeled 30-calendar-day pre-operation gate.",
        "Public Notice is missing or was not published at least 30 calendar days before operation.",
        "SEC 34-106402 II.C",
        "SARA+ECHO",
    ))

    # II.D - issuer notice for unaffiliated third-party tokenization
    if state.get("tokenizer_unaffiliated_third_party"):
        issuer_notice = _parse_dt(state.get("issuer_notice_received_at"))
        trade_start = _parse_dt(state.get("symbol_trading_start_at"))
        timely_wait = bool(issuer_notice and trade_start and trade_start - issuer_notice >= timedelta(days=30))
        no_objection = not bool(state.get("issuer_objected_within_30_days"))
        findings.append(_finding(
            "TSV-ISSUER-001",
            timely_wait and no_objection,
            "Issuer notice/waiting-period/objection gate passes.",
            "Issuer notice gate fails: missing notice, insufficient 30-day wait, or timely issuer objection.",
            "SEC 34-106402 II.D",
            "SARA+PRIME+ECHO",
        ))
    else:
        findings.append(Finding(
            "TSV-ISSUER-001", Status.NOT_EVALUATED,
            "Issuer notice gate not triggered because tokenization is not marked as unaffiliated third-party tokenization.",
            "SEC 34-106402 II.D", "SARA+PRIME+ECHO"
        ))

    # II.E - no primary issuance + rights equivalence
    findings.append(_finding(
        "TSV-OFFER-001",
        not bool(state.get("primary_issuance_or_initial_offering")),
        "No primary issuance or initial offering is represented on the TSV path.",
        "Primary issuance or initial offering is represented; modeled TSV exemption path denies.",
        "SEC 34-106402 II.E",
        "PRIME",
    ))
    rights = state.get("rights", {})
    rights_ok = all(bool(rights.get(k)) for k in ("same_company_interest", "same_dividends", "same_voting", "same_liquidation_share"))
    findings.append(_finding(
        "TSV-RIGHTS-001",
        rights_ok,
        "Modeled tokenized stock rights match the equivalent traditional class on the four enumerated rights dimensions.",
        "Rights-equivalence evidence is incomplete or negative.",
        "SEC 34-106402 II.E",
        "PRIME+ECHO",
    ))

    # II.F - symbol and ADV limits, aggregated across affiliates
    tier = int(state.get("tier", 0) or 0)
    symbols = int(state.get("aggregate_affiliate_symbol_count", 0) or 0)
    adv_share = float(state.get("aggregate_affiliate_adv_share", 0.0) or 0.0)
    threshold_breach_count = int(state.get("prior_volume_threshold_breaches", 0) or 0)
    if tier == 1:
        symbol_ok, volume_ok = symbols <= 75, adv_share <= 0.0025
    elif tier == 2:
        symbol_ok, volume_ok = symbols <= 250, adv_share <= 0.025
    else:
        symbol_ok = volume_ok = False
    findings.append(_finding(
        "TSV-LIMIT-001",
        symbol_ok,
        "Aggregate affiliated TSV symbol count is within the tier limit.",
        "Aggregate affiliated TSV symbol count exceeds the tier limit or tier is invalid.",
        "SEC 34-106402 II.F",
        "OVERWATCH+PRIME",
    ))
    if volume_ok:
        findings.append(Finding(
            "TSV-LIMIT-002", Status.PASS,
            "Aggregate affiliated TSV volume share is within the modeled prior-month ADV threshold.",
            "SEC 34-106402 II.F", "OVERWATCH+PRIME"
        ))
    elif tier in (1, 2) and threshold_breach_count == 0:
        findings.append(Finding(
            "TSV-LIMIT-002", Status.WARN,
            "First modeled volume-threshold exceedance detected: record breach and prevent subsequent exceedance; no automatic three-month pause on first exceedance.",
            "SEC 34-106402 II.F", "OVERWATCH+ECHO+PRIME"
        ))
    else:
        findings.append(Finding(
            "TSV-LIMIT-002", Status.FAIL,
            "Subsequent modeled volume-threshold exceedance requires immediate three-month pause for this Tokenized NMS Stock, including affiliated TSVs.",
            "SEC 34-106402 II.F", "OVERWATCH+PRIME+ECHO"
        ))

    # II.G - transaction transparency
    tx_age_minutes = state.get("transaction_publication_delay_minutes")
    transparency_ok = (
        isinstance(tx_age_minutes, (int, float)) and tx_age_minutes <= 10
        and int(state.get("public_transaction_history_days", 0) or 0) >= 30
        and bool(state.get("transaction_data_machine_readable"))
        and bool(state.get("transaction_data_free_public"))
        and bool(state.get("transaction_data_usd_denominated"))
        and bool(state.get("transaction_fields_complete"))
    )
    findings.append(_finding(
        "TSV-TRANS-001",
        transparency_ok,
        "Transaction transparency controls satisfy the modeled 10-minute/30-day/machine-readable/public/field-completeness requirements.",
        "Transaction transparency controls are incomplete or stale.",
        "SEC 34-106402 II.G",
        "OVERWATCH+ECHO",
    ))

    # II.H - trading stoppage
    underlying_stopped = bool(state.get("underlying_primary_exchange_stopped"))
    token_stopped = bool(state.get("tokenized_stock_stopped"))
    halt_ok = (not underlying_stopped) or token_stopped
    findings.append(_finding(
        "TSV-HALT-001",
        halt_ok,
        "Tokenized-stock halt state is consistent with the underlying primary-exchange stoppage state.",
        "Underlying NMS stock is stopped while tokenized-stock trading remains enabled.",
        "SEC 34-106402 II.H",
        "OVERWATCH+PRIME+ECHO",
    ))

    # II.I - significant operational events
    if state.get("significant_operational_event"):
        op_ok = bool(state.get("participants_notified_immediately")) and bool(state.get("sec_notified_promptly")) and bool(state.get("remediation_tracked"))
        findings.append(_finding(
            "TSV-OPS-001",
            op_ok,
            "Significant operational event notification/remediation controls are represented as satisfied.",
            "Significant operational event exists without complete participant/SEC notification and remediation tracking.",
            "SEC 34-106402 II.I",
            "OVERWATCH+SARA+ECHO",
        ))
    else:
        findings.append(Finding(
            "TSV-OPS-001", Status.NOT_EVALUATED,
            "No significant operational event is represented in this evaluation.",
            "SEC 34-106402 II.I", "OVERWATCH+SARA+ECHO"
        ))

    # II.J - no leverage
    leverage_ok = not any(bool(state.get(k)) for k in ("borrowing_on_tsv", "hypothecation", "participant_purchase_credit"))
    findings.append(_finding(
        "TSV-LEV-001",
        leverage_ok,
        "No prohibited borrowing, hypothecation, or purchase credit is represented.",
        "Prohibited leverage/credit activity is represented.",
        "SEC 34-106402 II.J",
        "PRIME",
    ))

    # II.K - misrepresentation/disclaimer
    representation_ok = not bool(state.get("claims_sec_registered_approved_or_endorsed")) and bool(state.get("public_notice_disclaims_sec_registration"))
    findings.append(_finding(
        "TSV-DISC-001",
        representation_ok,
        "Public representation/disclaimer state passes the modeled SEC-registration/endorsement guard.",
        "SEC registration/approval/endorsement representation or required disclaimer control fails.",
        "SEC 34-106402 II.K / III.a",
        "SARA+PRIME",
    ))

    # II.L - records
    records_ok = (
        bool(state.get("records_current"))
        and bool(state.get("records_maintained_in_us"))
        and bool(state.get("records_human_readable"))
        and bool(state.get("records_usable_electronic"))
        and int(state.get("post_exemption_retention_years", 0) or 0) >= 3
    )
    findings.append(_finding(
        "TSV-REC-001",
        records_ok,
        "Books-and-records controls satisfy the modeled currency/location/format/retention requirements.",
        "Books-and-records controls are incomplete.",
        "SEC 34-106402 II.L",
        "ECHO+SARA",
    ))

    # III.x/z/bb/cc - systems safeguards, risk disclosure, surveillance, stop procedures
    safeguards_ok = all(bool(state.get(k)) for k in (
        "code_review", "security_audit", "post_deployment_monitoring", "authorization_controls",
        "stress_testing", "business_continuity", "incident_response", "market_abuse_monitoring",
        "risk_disclosure", "stoppage_procedures_disclosed"
    ))
    findings.append(_finding(
        "TSV-SAFE-001",
        safeguards_ok,
        "Modeled systems-safeguard, surveillance, risk-disclosure, and stoppage-procedure controls are present.",
        "One or more modeled safeguards/surveillance/risk/stoppage controls are absent.",
        "SEC 34-106402 III.x, III.z, III.bb, III.cc",
        "QCRYPTO+OVERWATCH+PRIME+ECHO",
    ))

    fail_count = sum(1 for f in findings if f.status == Status.FAIL)
    decision = "DENY" if fail_count else "ALLOW_WITH_WARNINGS" if any(f.status == Status.WARN for f in findings) else "ALLOW"
    return Evaluation(decision=decision, findings=findings)
