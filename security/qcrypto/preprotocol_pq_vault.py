"""Defensive classifier for pre-protocol post-quantum asset protection.

The goal is to identify whether a chain has a deployable path for moving value
under post-quantum-gated control before the base protocol completes full PQ
migration. This module does not sign transactions, access wallets, recover keys,
or interact with live networks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ChainVaultEvidence:
    chain: str
    source: str
    native_pq_account_live: bool = False
    mainnet_pq_vault_or_proof_live: bool = False
    programmable_account_substrate_live: bool = False
    audited_reference_implementation: bool = False
    pq_authorization_live: bool = False
    standard_relay_or_wallet_flow: bool = False
    exposed_key_rescue: bool = False
    consensus_layer_pq: bool = False
    independent_security_review_complete: bool = False


@dataclass(frozen=True)
class ChainVaultReadiness:
    chain: str
    protection_state: str
    deployment_state: str
    residual_risk: str
    recommended_action: str
    blocking_gaps: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_chain_vault(evidence: ChainVaultEvidence) -> ChainVaultReadiness:
    gaps: list[str] = []

    if evidence.native_pq_account_live and evidence.pq_authorization_live:
        protection = "NATIVE_PQ_ACCOUNT_PATH"
        deployment = "MAINNET_PQ_AUTHORIZATION_AVAILABLE"
    elif evidence.mainnet_pq_vault_or_proof_live and evidence.pq_authorization_live:
        protection = "PRE_PROTOCOL_PQ_VAULT_PATH"
        deployment = "MAINNET_APPLICATION_LAYER_PQ_PATH"
    elif evidence.programmable_account_substrate_live and evidence.audited_reference_implementation:
        protection = "AUDITED_CRYPTO_AGILE_ACCOUNT_SUBSTRATE"
        deployment = "PQ_AUTHORIZATION_INTEGRATION_PENDING"
    else:
        protection = "RESEARCH_OR_EARLY_INTEGRATION"
        deployment = "NO_VERIFIED_MAINNET_PQ_ASSET_PATH"

    if not evidence.standard_relay_or_wallet_flow:
        gaps.append("Standard wallet/relay UX is incomplete or not established by this evidence record.")
    if not evidence.exposed_key_rescue:
        gaps.append("Previously exposed classical public keys are not universally rescued by this path.")
    if not evidence.consensus_layer_pq:
        gaps.append("Base-layer consensus/authentication remains outside the scope of this asset-protection path.")
    if not evidence.independent_security_review_complete:
        gaps.append("Independent security review of the complete deployed path is incomplete or not established.")

    if protection == "NATIVE_PQ_ACCOUNT_PATH":
        action = "MIGRATE_HIGH_VALUE_ACCOUNTS_AND_VALIDATE_RESIDUAL_CONSENSUS_RISK"
    elif protection == "PRE_PROTOCOL_PQ_VAULT_PATH":
        action = "PILOT_HIGH_VALUE_VAULTS_AND_REQUIRE_INDEPENDENT_REVIEW"
    elif protection == "AUDITED_CRYPTO_AGILE_ACCOUNT_SUBSTRATE":
        action = "INTEGRATE_AND_BENCHMARK_PQ_VALIDATOR_BEFORE_HIGH_VALUE_USE"
    else:
        action = "CONTINUE_IMPLEMENTATION_AND_TESTNET_VALIDATION"

    residual = "FULL_PROTOCOL_NOT_PQ" if not evidence.consensus_layer_pq else "ACCOUNT_OR_VAULT_SCOPE_RESIDUALS"

    return ChainVaultReadiness(
        chain=evidence.chain,
        protection_state=protection,
        deployment_state=deployment,
        residual_risk=residual,
        recommended_action=action,
        blocking_gaps=tuple(gaps),
    )


def assess_portfolio(readiness: list[ChainVaultReadiness]) -> str:
    """Return the highest defensible portfolio-level solution state."""
    states = {item.protection_state for item in readiness}
    if "NATIVE_PQ_ACCOUNT_PATH" in states and "PRE_PROTOCOL_PQ_VAULT_PATH" in states:
        return "INCREMENTAL_MULTI_CHAIN_PQ_ASSET_PROTECTION_AVAILABLE"
    if "PRE_PROTOCOL_PQ_VAULT_PATH" in states:
        return "PARTIAL_MULTI_CHAIN_PQ_VAULT_PATHS_AVAILABLE"
    return "MIGRATION_SUBSTRATES_ONLY"
