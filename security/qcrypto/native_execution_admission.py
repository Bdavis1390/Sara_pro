"""Evidence admission guard for chain-native transaction execution.

This module does not sign or broadcast transactions. It determines whether externally
produced evidence is sufficient to record progressively stronger execution states.
The purpose is to keep native signing, broadcast, mainnet authority, and real-value
movement as separate claims with separate evidence requirements.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


_TEST_NETWORKS = {("BITCOIN", "SIGNET"), ("ETHEREUM", "HOODI")}
_MAIN_NETWORKS = {("BITCOIN", "MAINNET"), ("ETHEREUM", "MAINNET")}


@dataclass(frozen=True)
class NativeExecutionEvidence:
    chain: str
    network: str
    network_identity_verified: bool = False
    exact_unsigned_digest_bound_to_approval: bool = False
    external_signer_attestation_verified: bool = False
    chain_native_signature_verified: bool = False
    signed_transaction_digest_verified: bool = False
    broadcast_receipt_verified: bool = False
    canonical_transaction_id_recorded: bool = False
    distinct_mainnet_authorization_recorded: bool = False
    real_value_execution_receipt_verified: bool = False
    qcrypto_execution_authority: bool = False
    qcrypto_private_key_operations_permitted: bool = False
    qcrypto_broadcast_permitted: bool = False


@dataclass(frozen=True)
class NativeExecutionAssessment:
    state: str
    native_signature_claim: bool
    broadcast_claim: bool
    mainnet_authority_claim: bool
    real_value_movement_claim: bool
    qcrypto_authority_remains_false: bool
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def assess_native_execution(e: NativeExecutionEvidence) -> NativeExecutionAssessment:
    identity = (e.chain.upper(), e.network.upper())
    if identity not in _TEST_NETWORKS | _MAIN_NETWORKS:
        raise ValueError("unsupported or ambiguous chain/network identity")
    if e.qcrypto_execution_authority or e.qcrypto_private_key_operations_permitted or e.qcrypto_broadcast_permitted:
        raise ValueError("QCRYPTO governance may not self-grant execution, private-key, or broadcast authority")

    signature = all(
        (
            e.network_identity_verified,
            e.exact_unsigned_digest_bound_to_approval,
            e.external_signer_attestation_verified,
            e.chain_native_signature_verified,
            e.signed_transaction_digest_verified,
        )
    )
    if e.broadcast_receipt_verified and not signature:
        raise ValueError("broadcast evidence cannot be admitted without verified native signature evidence")
    broadcast = signature and e.broadcast_receipt_verified and e.canonical_transaction_id_recorded

    is_mainnet = identity in _MAIN_NETWORKS
    if e.distinct_mainnet_authorization_recorded and not is_mainnet:
        raise ValueError("mainnet authorization evidence is invalid for a test network")
    mainnet = is_mainnet and broadcast and e.distinct_mainnet_authorization_recorded

    if e.real_value_execution_receipt_verified and not mainnet:
        raise ValueError("real-value evidence requires verified mainnet authorization and broadcast evidence")
    real_value = mainnet and e.real_value_execution_receipt_verified

    if real_value:
        state = "REAL_VALUE_EXECUTION_EVIDENCE_RECORDED"
        reason = "native signature, broadcast, mainnet authorization, and value-execution evidence are all present"
    elif mainnet:
        state = "MAINNET_BROADCAST_AUTHORITY_EVIDENCE_RECORDED"
        reason = "mainnet authorization and broadcast evidence are present; real-value execution is not recorded"
    elif broadcast:
        state = "TESTNET_BROADCAST_EVIDENCE_RECORDED" if not is_mainnet else "MAINNET_BROADCAST_WITHOUT_AUTHORITY"
        reason = "broadcast receipt and transaction identifier are present"
    elif signature:
        state = "NATIVE_SIGNATURE_EVIDENCE_RECORDED"
        reason = "native signature is bound to approved digest and network identity; no broadcast is established"
    else:
        state = "NATIVE_EXECUTION_NOT_ESTABLISHED"
        reason = "required chain-native signature evidence is incomplete"

    return NativeExecutionAssessment(
        state=state,
        native_signature_claim=signature,
        broadcast_claim=broadcast,
        mainnet_authority_claim=mainnet,
        real_value_movement_claim=real_value,
        qcrypto_authority_remains_false=True,
        reason=reason,
    )
