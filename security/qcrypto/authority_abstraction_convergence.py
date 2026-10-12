"""Cross-chain readiness model for stable identity with replaceable authentication.

The model captures a converging migration primitive: keep the account/authority
identifier stable while changing the authentication scheme underneath it. This
is a defensive architecture classifier only; it does not create accounts, rekey,
sign, submit, or move assets.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AuthorityAbstractionEvidence:
    chain: str
    stable_authority_identifier: bool = False
    authenticator_replaceable_without_asset_move: bool = False
    pq_authentication_live: bool = False
    programmable_or_scheme_agile_validation: bool = False
    migration_path_live: bool = False
    roadmap_only: bool = False
    recovery_compatible: bool = False
    consensus_layer_pq: bool = False


@dataclass(frozen=True)
class AuthorityAbstractionAssessment:
    chain: str
    maturity: str
    migration_primitive: str
    recommended_worldshepherd_adapter: str
    residual_risks: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_authority_abstraction(evidence: AuthorityAbstractionEvidence) -> AuthorityAbstractionAssessment:
    residual: list[str] = []

    stable_replaceable = evidence.stable_authority_identifier and evidence.authenticator_replaceable_without_asset_move

    if stable_replaceable and evidence.pq_authentication_live and evidence.migration_path_live:
        maturity = "LIVE_PQ_AUTHORITY_ABSTRACTION"
        primitive = "STABLE_IDENTITY_REPLACEABLE_PQ_AUTHENTICATOR"
    elif stable_replaceable and evidence.programmable_or_scheme_agile_validation and evidence.roadmap_only:
        maturity = "LIVE_AGILITY_SUBSTRATE_PQ_PATH_PENDING"
        primitive = "STABLE_IDENTITY_REPLACEABLE_AUTHENTICATOR_SUBSTRATE"
    elif evidence.programmable_or_scheme_agile_validation and evidence.roadmap_only:
        maturity = "DRAFT_NATIVE_AUTHORITY_ABSTRACTION"
        primitive = "PROGRAMMABLE_VALIDATION_AND_KEY_ROTATION"
    else:
        maturity = "NO_VERIFIED_AUTHORITY_ABSTRACTION_PATH"
        primitive = "LEGACY_AUTHORITY_COUPLING"

    if not evidence.recovery_compatible:
        residual.append("Recovery compatibility is incomplete or not established by this evidence record.")
    if not evidence.consensus_layer_pq:
        residual.append("Account authorization agility does not imply post-quantum consensus or validator security.")
    if evidence.roadmap_only:
        residual.append("Roadmap capability must not be promoted to deployed capability before activation and validation.")

    return AuthorityAbstractionAssessment(
        chain=evidence.chain,
        maturity=maturity,
        migration_primitive=primitive,
        recommended_worldshepherd_adapter="CANONICAL_AUTHORITY_ENVELOPE",
        residual_risks=tuple(residual),
    )


def assess_cross_chain_convergence(assessments: list[AuthorityAbstractionAssessment]) -> str:
    matured = {item.maturity for item in assessments}
    if "LIVE_PQ_AUTHORITY_ABSTRACTION" in matured and len(assessments) >= 3:
        agile_count = sum(
            item.maturity in {
                "LIVE_PQ_AUTHORITY_ABSTRACTION",
                "LIVE_AGILITY_SUBSTRATE_PQ_PATH_PENDING",
                "DRAFT_NATIVE_AUTHORITY_ABSTRACTION",
            }
            for item in assessments
        )
        if agile_count >= 3:
            return "CROSS_CHAIN_AUTHORITY_ABSTRACTION_CONVERGENCE"
    return "CHAIN_SPECIFIC_MIGRATION_ONLY"
