"""Claims-controlled phasing for post-quantum live-value canaries.

Phase A permits only a narrowly bounded native-PQ account canary. Phase B is
reserved for institution-grade authorization after a multi-approver policy layer
is actually available and validated. This module never signs or moves assets.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class InstitutionalCanaryEvidence:
    native_pq_account_live: bool = False
    wallet_tooling_live: bool = False
    bounded_single_account_controls_validated: bool = False
    native_multi_crypto_policy_live: bool = False
    weighted_or_multi_approver_policy_live: bool = False
    hybrid_classical_pq_policy_supported: bool = False
    policy_interop_validated: bool = False
    independent_review_complete: bool = False
    recovery_drill_passed: bool = False
    explicit_human_approval_required: bool = True
    consensus_layer_pq: bool = False


@dataclass(frozen=True)
class InstitutionalCanaryAssessment:
    phase: str
    deployment_class: str
    action: str
    blockers: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_institutional_canary(evidence: InstitutionalCanaryEvidence) -> InstitutionalCanaryAssessment:
    blockers: list[str] = []

    phase_a = all(
        (
            evidence.native_pq_account_live,
            evidence.wallet_tooling_live,
            evidence.bounded_single_account_controls_validated,
            evidence.explicit_human_approval_required,
        )
    )

    phase_b = all(
        (
            phase_a,
            evidence.native_multi_crypto_policy_live,
            evidence.weighted_or_multi_approver_policy_live,
            evidence.hybrid_classical_pq_policy_supported,
            evidence.policy_interop_validated,
            evidence.independent_review_complete,
            evidence.recovery_drill_passed,
        )
    )

    if phase_b:
        phase = "PHASE_B_INSTITUTIONAL_CANARY_READY"
        deployment_class = "MULTI_APPROVER_PQ_AUTHORIZATION"
        action = "REQUIRE_SEPARATE_EXPLICIT_AUTHORIZATION_BEFORE_ANY_BOUNDED_LIVE_EXECUTION"
    elif phase_a:
        phase = "PHASE_A_BOUNDED_NATIVE_PQ_CANARY"
        deployment_class = "SINGLE_ACCOUNT_PQ_AUTHORIZATION_ONLY"
        action = "KEEP_VALUE_MINIMAL_AND_DO_NOT_LABEL_AS_INSTITUTION_GRADE_MULTISIG"
    else:
        phase = "PRE_CANARY_INTEGRATION"
        deployment_class = "NOT_READY"
        action = "COMPLETE_NATIVE_ACCOUNT_TOOLING_AND_BOUNDED_CONTROL_VALIDATION"

    if not evidence.native_multi_crypto_policy_live:
        blockers.append("Institution-grade promotion waits for a live multi-crypto policy layer rather than a roadmap promise.")
    if not evidence.policy_interop_validated:
        blockers.append("Multi-approver policy interoperability must be exercised before Phase B.")
    if not evidence.independent_review_complete:
        blockers.append("Independent review is required before Phase B.")
    if not evidence.recovery_drill_passed:
        blockers.append("Recovery must be rehearsed before Phase B.")
    if not evidence.consensus_layer_pq:
        blockers.append("Account-policy protection does not imply post-quantum consensus security.")

    return InstitutionalCanaryAssessment(
        phase=phase,
        deployment_class=deployment_class,
        action=action,
        blockers=tuple(blockers),
    )
