"""Claims-controlled gate for a bounded live-value post-quantum canary.

This module only classifies deployment readiness. It never creates keys, signs,
submits, broadcasts, or moves assets. Any live-value execution remains a separate,
explicitly authorized action outside this module.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LiveValueCanaryEvidence:
    candidate_chain: str
    native_pq_authorization_live: bool = False
    single_native_asset_scope: bool = False
    bridge_free_scope: bool = False
    fresh_dedicated_canary_account: bool = False
    wallet_and_tooling_interop_validated: bool = False
    chain_adapter_testnet_validated: bool = False
    recovery_path_precommitted: bool = False
    recovery_drill_passed: bool = False
    independent_review_complete: bool = False
    critical_findings_closed: bool = False
    immutable_evidence_logging: bool = False
    monitoring_and_pause_ready: bool = False
    bounded_value_policy_defined: bool = False
    deployment_expiry_defined: bool = False
    explicit_human_approval_present: bool = False
    live_execution_receipt_present: bool = False
    consensus_layer_pq: bool = False


@dataclass(frozen=True)
class LiveValueCanaryAssessment:
    readiness_state: str
    scope_state: str
    execution_state: str
    action: str
    blockers: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_live_value_canary(evidence: LiveValueCanaryEvidence) -> LiveValueCanaryAssessment:
    blockers: list[str] = []

    scope_ready = all(
        (
            evidence.native_pq_authorization_live,
            evidence.single_native_asset_scope,
            evidence.bridge_free_scope,
            evidence.fresh_dedicated_canary_account,
        )
    )
    scope_state = "MINIMIZED_NATIVE_PQ_SCOPE" if scope_ready else "SCOPE_NOT_MINIMIZED"
    if not scope_ready:
        blockers.append("Use a fresh dedicated account on a chain with native PQ authorization, one native asset, and no bridge dependency.")

    integration_ready = all(
        (
            evidence.wallet_and_tooling_interop_validated,
            evidence.chain_adapter_testnet_validated,
            evidence.recovery_path_precommitted,
            evidence.recovery_drill_passed,
            evidence.immutable_evidence_logging,
            evidence.monitoring_and_pause_ready,
        )
    )
    if not integration_ready:
        blockers.append("Tooling, non-production chain adapter, recovery drill, evidence logging, and pause/monitoring controls are not all validated.")

    assurance_ready = all(
        (
            evidence.independent_review_complete,
            evidence.critical_findings_closed,
            evidence.bounded_value_policy_defined,
            evidence.deployment_expiry_defined,
        )
    )
    if not assurance_ready:
        blockers.append("Independent review, closed critical findings, explicit value cap, and deployment expiry are required before live value.")

    if scope_ready and integration_ready and assurance_ready:
        if evidence.explicit_human_approval_present:
            readiness = "LVC_AUTHORIZED_FOR_BOUNDED_EXECUTION"
            action = "EXECUTION_MAY_PROCEED_ONLY_THROUGH_AN_EXPLICITLY_AUTHORIZED_WALLET_OR_CUSTODY_PATH_WITH_THE_CONFIGURED_CAP"
        else:
            readiness = "LVC_READY_PENDING_EXPLICIT_HUMAN_APPROVAL"
            action = "HOLD_AT_ZERO_LIVE_VALUE_AND_OBTAIN_EXPLICIT_APPROVAL"
    elif scope_ready and integration_ready:
        readiness = "LVC_ASSURANCE_REVIEW_REQUIRED"
        action = "COMPLETE_INDEPENDENT_REVIEW_AND_CLOSE_FINDINGS"
    elif scope_ready:
        readiness = "LVC_INTEGRATION_VALIDATION_REQUIRED"
        action = "COMPLETE_TOOLING_TESTNET_RECOVERY_AND_MONITORING_VALIDATION"
    else:
        readiness = "LVC_SCOPE_DESIGN_REQUIRED"
        action = "SELECT_AND_MINIMIZE_THE_CANARY_SCOPE"

    if evidence.live_execution_receipt_present and evidence.explicit_human_approval_present and readiness == "LVC_AUTHORIZED_FOR_BOUNDED_EXECUTION":
        execution_state = "EXTERNAL_LIVE_CANARY_EXECUTION_RECORDED"
    elif evidence.live_execution_receipt_present:
        execution_state = "INVALID_EXECUTION_EVIDENCE_REQUIRES_REVIEW"
        blockers.append("An execution receipt must not be accepted without the complete authorization chain.")
    else:
        execution_state = "NO_LIVE_VALUE_EXECUTED_BY_THIS_CONTROL"

    if not evidence.consensus_layer_pq:
        blockers.append("Native account authorization does not imply post-quantum consensus or validator security.")

    return LiveValueCanaryAssessment(
        readiness_state=readiness,
        scope_state=scope_state,
        execution_state=execution_state,
        action=action,
        blockers=tuple(blockers),
    )
