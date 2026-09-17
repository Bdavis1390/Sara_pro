"""Measured online-state assessment for the QCRYPTO public-testnet nodes.

The guard consumes read-only node observations. It does not perform wallet,
validator, transaction, broadcast, or private-key operations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ChainOnlineEvidence:
    bitcoin_reported_chain: str
    bitcoin_blocks: int
    bitcoin_headers: int
    bitcoin_verification_progress: float

    ethereum_chain_id: int
    ethereum_execution_block_number: int
    ethereum_consensus_head_slot: int
    ethereum_consensus_sync_distance: int
    ethereum_consensus_is_syncing: bool

    external_signer_boundary_defined: bool = True
    wallet_private_key_present: bool = False
    validator_private_key_present: bool = False
    live_bitcoin_broadcast_enabled: bool = False
    ethereum_validator_activation_enabled: bool = False


@dataclass(frozen=True)
class ChainOnlineAssessment:
    state: str
    bitcoin_state: str
    ethereum_state: str
    synchronized: bool
    node_online_evidence_valid: bool
    transaction_execution_permitted: bool
    validator_activation_permitted: bool
    private_key_operations_permitted: bool
    mainnet_permitted: bool
    end_to_end_post_quantum_security_established: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_chain_online(evidence: ChainOnlineEvidence) -> ChainOnlineAssessment:
    blockers: list[str] = []
    warnings: list[str] = []

    bitcoin_identity_ok = evidence.bitcoin_reported_chain == "signet"
    if not bitcoin_identity_ok:
        blockers.append("Bitcoin node did not report chain=signet.")
    if evidence.bitcoin_blocks < 0 or evidence.bitcoin_headers < 0:
        blockers.append("Bitcoin block/header heights must be non-negative.")
    if not 0.0 <= evidence.bitcoin_verification_progress <= 1.0:
        blockers.append("Bitcoin verification progress must be within [0,1].")

    ethereum_identity_ok = evidence.ethereum_chain_id == 560048
    if not ethereum_identity_ok:
        blockers.append("Ethereum execution node did not report Hoodi chain_id=560048.")
    if evidence.ethereum_execution_block_number < 0:
        blockers.append("Ethereum execution block number must be non-negative.")
    if evidence.ethereum_consensus_head_slot < 0 or evidence.ethereum_consensus_sync_distance < 0:
        blockers.append("Ethereum consensus slot/sync distance must be non-negative.")

    if evidence.wallet_private_key_present or evidence.validator_private_key_present:
        blockers.append("Observer deployment must not contain wallet or validator private keys.")
    if not evidence.external_signer_boundary_defined:
        blockers.append("External signer boundary is not defined.")
    if evidence.live_bitcoin_broadcast_enabled:
        blockers.append("Bitcoin broadcast must remain disabled at NODE_ONLINE evidence stage.")
    if evidence.ethereum_validator_activation_enabled:
        blockers.append("Ethereum validator activation must remain disabled at NODE_ONLINE evidence stage.")

    bitcoin_synced = (
        bitcoin_identity_ok
        and evidence.bitcoin_headers >= 0
        and evidence.bitcoin_blocks == evidence.bitcoin_headers
        and evidence.bitcoin_verification_progress >= 0.999
    )
    bitcoin_state = (
        "BITCOIN_SIGNET_ONLINE_SYNCED"
        if bitcoin_synced
        else "BITCOIN_SIGNET_ONLINE_SYNCING"
        if bitcoin_identity_ok and not blockers
        else "BITCOIN_SIGNET_ONLINE_EVIDENCE_INVALID"
    )

    ethereum_synced = (
        ethereum_identity_ok
        and not evidence.ethereum_consensus_is_syncing
        and evidence.ethereum_consensus_sync_distance == 0
    )
    ethereum_state = (
        "ETHEREUM_HOODI_ONLINE_SYNCED"
        if ethereum_synced
        else "ETHEREUM_HOODI_ONLINE_SYNCING"
        if ethereum_identity_ok and not blockers
        else "ETHEREUM_HOODI_ONLINE_EVIDENCE_INVALID"
    )

    evidence_valid = not blockers
    synchronized = evidence_valid and bitcoin_synced and ethereum_synced

    if synchronized:
        state = "PUBLIC_TESTNET_NODES_ONLINE_AND_SYNCED"
    elif evidence_valid:
        state = "PUBLIC_TESTNET_NODES_ONLINE_SYNCING"
        warnings.append("Chain identity is valid but one or both public-testnet nodes are still synchronizing.")
    else:
        state = "NODE_ONLINE_EVIDENCE_REJECTED"

    return ChainOnlineAssessment(
        state=state,
        bitcoin_state=bitcoin_state,
        ethereum_state=ethereum_state,
        synchronized=synchronized,
        node_online_evidence_valid=evidence_valid,
        transaction_execution_permitted=False,
        validator_activation_permitted=False,
        private_key_operations_permitted=False,
        mainnet_permitted=False,
        end_to_end_post_quantum_security_established=False,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )
