"""Fail-closed deployment readiness for Bitcoin Signet and Ethereum Hoodi.

This module validates a host-ready public-testnet deployment package. It never
creates/imports wallet or validator private keys, signs or broadcasts Bitcoin
transactions, activates Ethereum validators, mutates mainnet state, or grants
production authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


BITCOIN_ALLOWED_NETWORK = "SIGNET"
ETHEREUM_ALLOWED_NETWORK = "HOODI"
ETHEREUM_HOODI_CHAIN_ID = 560048


@dataclass(frozen=True)
class ChainDeploymentEvidence:
    bitcoin_network: str = BITCOIN_ALLOWED_NETWORK
    ethereum_network: str = ETHEREUM_ALLOWED_NETWORK
    ethereum_chain_id: int = ETHEREUM_HOODI_CHAIN_ID

    bitcoin_image_digest_pinned: bool = False
    ethereum_execution_image_digest_pinned: bool = False
    ethereum_consensus_image_digest_pinned: bool = False

    bitcoin_persistent_storage: bool = False
    ethereum_execution_persistent_storage: bool = False
    ethereum_consensus_persistent_storage: bool = False

    bitcoin_healthcheck_defined: bool = False
    ethereum_execution_healthcheck_defined: bool = False
    ethereum_consensus_healthcheck_defined: bool = False

    bitcoin_rpc_private_only: bool = False
    ethereum_engine_api_private_only: bool = False
    ethereum_beacon_admin_private_only: bool = False

    external_signer_boundary_defined: bool = False
    wallet_private_key_mounted: bool = False
    validator_private_key_mounted: bool = False
    qcrypto_secret_key_retention: bool = False

    bitcoin_mainnet_enabled: bool = False
    ethereum_mainnet_enabled: bool = False
    live_bitcoin_broadcast_enabled: bool = False
    ethereum_validator_activation_enabled: bool = False

    rollback_plan_defined: bool = False
    monitoring_plan_defined: bool = False
    evidence_receipt_enabled: bool = False


@dataclass(frozen=True)
class ChainDeploymentAssessment:
    state: str
    bitcoin_state: str
    ethereum_state: str
    custody_state: str
    deployment_action: str
    host_deployment_ready: bool
    public_testnet_only: bool
    private_key_operations_permitted: bool
    live_value_authorized: bool
    mainnet_permitted: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_chain_deployment(evidence: ChainDeploymentEvidence) -> ChainDeploymentAssessment:
    blockers: list[str] = []
    warnings: list[str] = []

    bitcoin_network_ok = evidence.bitcoin_network == BITCOIN_ALLOWED_NETWORK
    ethereum_network_ok = (
        evidence.ethereum_network == ETHEREUM_ALLOWED_NETWORK
        and evidence.ethereum_chain_id == ETHEREUM_HOODI_CHAIN_ID
    )

    if not bitcoin_network_ok:
        blockers.append("Bitcoin deployment must be pinned to SIGNET.")
    if not ethereum_network_ok:
        blockers.append("Ethereum deployment must be pinned to HOODI chain_id=560048.")

    if evidence.bitcoin_mainnet_enabled or evidence.ethereum_mainnet_enabled:
        blockers.append("Mainnet enablement is forbidden in the public-testnet deployment package.")
    if evidence.live_bitcoin_broadcast_enabled:
        blockers.append("Live Bitcoin broadcast remains outside QCRYPTO deployment authority.")
    if evidence.ethereum_validator_activation_enabled:
        blockers.append("Ethereum validator activation remains an external human-operated action.")

    if evidence.wallet_private_key_mounted or evidence.validator_private_key_mounted:
        blockers.append("Wallet or validator private-key mounts are forbidden; use an external signer boundary.")
    if evidence.qcrypto_secret_key_retention:
        blockers.append("QCRYPTO must not retain signing secret material.")

    custody_ready = (
        evidence.external_signer_boundary_defined
        and not evidence.wallet_private_key_mounted
        and not evidence.validator_private_key_mounted
        and not evidence.qcrypto_secret_key_retention
    )
    custody_state = "EXTERNAL_SIGNER_BOUNDARY_READY" if custody_ready else "CUSTODY_BOUNDARY_INCOMPLETE"

    bitcoin_infra_ready = all(
        (
            bitcoin_network_ok,
            evidence.bitcoin_image_digest_pinned,
            evidence.bitcoin_persistent_storage,
            evidence.bitcoin_healthcheck_defined,
            evidence.bitcoin_rpc_private_only,
            custody_ready,
        )
    )
    bitcoin_state = "BITCOIN_SIGNET_NODE_HOST_READY" if bitcoin_infra_ready else "BITCOIN_SIGNET_DEPLOYMENT_INCOMPLETE"

    ethereum_infra_ready = all(
        (
            ethereum_network_ok,
            evidence.ethereum_execution_image_digest_pinned,
            evidence.ethereum_consensus_image_digest_pinned,
            evidence.ethereum_execution_persistent_storage,
            evidence.ethereum_consensus_persistent_storage,
            evidence.ethereum_execution_healthcheck_defined,
            evidence.ethereum_consensus_healthcheck_defined,
            evidence.ethereum_engine_api_private_only,
            evidence.ethereum_beacon_admin_private_only,
            custody_ready,
        )
    )
    ethereum_state = "ETHEREUM_HOODI_NODE_HOST_READY" if ethereum_infra_ready else "ETHEREUM_HOODI_DEPLOYMENT_INCOMPLETE"

    operations_ready = all(
        (
            evidence.rollback_plan_defined,
            evidence.monitoring_plan_defined,
            evidence.evidence_receipt_enabled,
        )
    )
    if not evidence.rollback_plan_defined:
        blockers.append("Rollback plan is not defined.")
    if not evidence.monitoring_plan_defined:
        blockers.append("Monitoring plan is not defined.")
    if not evidence.evidence_receipt_enabled:
        blockers.append("Deployment evidence receipt is not enabled.")

    ready = bitcoin_infra_ready and ethereum_infra_ready and operations_ready and not blockers

    if ready:
        state = "PUBLIC_TESTNET_CHAIN_DEPLOYMENT_HOST_READY"
        action = "PROVISION_HOST_AND_START_BITCOIN_SIGNET_AND_ETHEREUM_HOODI_NODES"
        warnings.append("Host readiness is not evidence that either node is currently online or synchronized.")
        warnings.append("Hoodi validator activation requires a separately controlled validator key/deposit workflow.")
    else:
        state = "CHAIN_DEPLOYMENT_BLOCKED"
        action = "COMPLETE_PUBLIC_TESTNET_HOST_CUSTODY_AND_OPERATIONS_GATES"

    return ChainDeploymentAssessment(
        state=state,
        bitcoin_state=bitcoin_state,
        ethereum_state=ethereum_state,
        custody_state=custody_state,
        deployment_action=action,
        host_deployment_ready=ready,
        public_testnet_only=True,
        private_key_operations_permitted=False,
        live_value_authorized=False,
        mainnet_permitted=False,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )
