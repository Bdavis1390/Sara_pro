"""Defensive classifier for Bitcoin mainnet post-quantum proof-of-concept maturity.

Tracks whether a construction has progressed from paper/test implementation to
consensus-compatible mainnet execution. It does not sign transactions, access
wallets, construct spends, recover keys, or interact with live networks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MainnetPQCProofEvidence:
    name: str
    source: str
    mainnet_confirmed: bool = False
    consensus_change_required: bool = True
    standard_relay: bool = False
    direct_miner_path_required: bool = False
    protects_previously_exposed_pubkeys: bool = False
    production_wallet_support: bool = False
    network_wide_migration_path: bool = False
    independent_security_review_complete: bool = False


@dataclass(frozen=True)
class MainnetPQCReadiness:
    maturity_state: str
    deployment_scope: str
    migration_value: str
    urgency: str
    blocking_gaps: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_mainnet_pqc_proof(evidence: MainnetPQCProofEvidence) -> MainnetPQCReadiness:
    """Classify what a mainnet PQ proof-of-concept actually establishes."""

    gaps: list[str] = []

    if evidence.mainnet_confirmed and not evidence.consensus_change_required:
        maturity = "CONSENSUS_COMPATIBLE_MAINNET_PROOF"
    elif evidence.mainnet_confirmed:
        maturity = "MAINNET_PROOF_WITH_PROTOCOL_CHANGE"
    else:
        maturity = "PRE_MAINNET_RESEARCH"

    if evidence.standard_relay:
        scope = "STANDARD_RELAY_CAPABLE"
    elif evidence.direct_miner_path_required:
        scope = "NONSTANDARD_DIRECT_MINER_PATH"
        gaps.append("Construction does not currently propagate through ordinary mempool relay.")
    else:
        scope = "RELAY_STATUS_UNVERIFIED"

    if not evidence.protects_previously_exposed_pubkeys:
        gaps.append("Does not rescue coins whose public keys were already exposed before migration.")
    if not evidence.production_wallet_support:
        gaps.append("No production wallet support is demonstrated.")
    if not evidence.network_wide_migration_path:
        gaps.append("Does not provide a network-wide migration or legacy-sunset mechanism.")
    if not evidence.independent_security_review_complete:
        gaps.append("Independent security review is incomplete or not established by this evidence record.")

    if maturity == "CONSENSUS_COMPATIBLE_MAINNET_PROOF":
        migration_value = "DEMONSTRATED_OPT_IN_PREPOSITIONING_PATH"
        urgency = "INTEGRATE_INTO_MIGRATION_PLANNING_AND_REVIEW"
    else:
        migration_value = "RESEARCH_ONLY"
        urgency = "CONTINUE_VALIDATION"

    return MainnetPQCReadiness(
        maturity_state=maturity,
        deployment_scope=scope,
        migration_value=migration_value,
        urgency=urgency,
        blocking_gaps=tuple(gaps),
    )
