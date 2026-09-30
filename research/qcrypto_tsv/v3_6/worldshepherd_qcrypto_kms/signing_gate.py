"""High-assurance local signing gate for Bitcoin PSBTs.

The gate joins strict PSBT parsing, UTXO/fee validation, output quantum policy,
descriptor validation, recipient/change binding, replay-bounded release intents,
optional independent operator quorum, and optional ML-DSA authorization. It does
not finalize or broadcast Bitcoin transactions.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence

from .approval_quorum import ApprovalQuorumError, SignedApproval, verify_approval_quorum
from .authorization_ledger import AuthorizationLedgerError, append_authorization_receipt
from .bitcoin_quantum_policy import CryptoPolicyState
from .descriptor_guard import DescriptorAudit, audit_descriptor
from .external_parser_quorum import ExternalParserQuorumError, validate_external_parser_quorum_report
from .external_pq_evidence import ExternalPqEvidenceError, validate_external_pq_evidence_report
from .crypto_agility import CryptoAgilityPolicy, build_crypto_bill_of_materials, evaluate_algorithm_set
from .migration_engine import MigrationBatchBinding, MigrationEngineError
from .resource_budget import ResourceBudgetPolicy, ResourceBudgetReport, ResourceBudgetError, evaluate_resource_budget
from .output_intent import OutputIntentError, OutputIntentPolicy, OutputIntentReport, evaluate_output_intent
from .psbt_guard import PsbtAuditReport, PsbtGuardError, audit_psbt, parse_psbt
from .release_policy import (
    RELEASE_ATTESTATION_CONTEXT,
    BitcoinReleaseIntent,
    PqReleaseAttestation,
    ReleasePolicyError,
    authorize_release,
    build_pq_release_attestation_from_provider_result,
)


class SigningGateError(RuntimeError):
    pass


def _canonical_hash(domain: bytes, payload: object) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def _psbt_bytes(raw: bytes | str) -> bytes:
    if isinstance(raw, bytes):
        return raw
    if isinstance(raw, bytearray):
        return bytes(raw)
    if isinstance(raw, str):
        try:
            return bytes.fromhex(raw.strip())
        except ValueError as exc:
            raise SigningGateError("PSBT text must be hexadecimal") from exc
    raise SigningGateError("PSBT must be bytes or hexadecimal text")


@dataclass(frozen=True)
class PreparedSigningGate:
    psbt_sha256: str
    txid: str
    network: str
    policy_state: CryptoPolicyState
    audit: PsbtAuditReport
    descriptor_audits: tuple[DescriptorAudit, ...]
    output_intent_report: OutputIntentReport | None
    signing_policy_sha256: str
    intent: BitcoinReleaseIntent
    resource_budget_report: ResourceBudgetReport | None = None
    crypto_bill_of_materials: dict | None = None
    crypto_agility_policy_sha256: str | None = None
    migration_binding_sha256: str | None = None
    migration_report: dict | None = None
    chain_context_sha256: str | None = None
    external_parser_quorum_binding: dict | None = None
    external_pq_evidence_binding: dict | None = None

    def to_dict(self) -> dict:
        return {
            "schema": "WS-BITCOIN-PREPARED-SIGNING-GATE-V2",
            "psbt_sha256": self.psbt_sha256,
            "txid": self.txid,
            "network": self.network,
            "policy_state": self.policy_state.value,
            "audit": self.audit.to_dict(),
            "descriptor_audits": [d.to_dict() for d in self.descriptor_audits],
            "output_intent_report": self.output_intent_report.to_dict() if self.output_intent_report else None,
            "signing_policy_sha256": self.signing_policy_sha256,
            "resource_budget_report": self.resource_budget_report.to_dict() if self.resource_budget_report else None,
            "crypto_bill_of_materials": self.crypto_bill_of_materials,
            "crypto_agility_policy_sha256": self.crypto_agility_policy_sha256,
            "migration_binding_sha256": self.migration_binding_sha256,
            "migration_report": self.migration_report,
            "chain_context_sha256": self.chain_context_sha256,
            "external_parser_quorum_binding": self.external_parser_quorum_binding,
            "external_pq_evidence_binding": self.external_pq_evidence_binding,
            "intent": json.loads(self.intent.canonical_bytes()),
            "intent_sha256": self.intent.intent_sha256,
            "ready_for_local_authorization": True,
            "transaction_broadcast_authorized": False,
            "mainnet_authority": False,
        }


def prepare_psbt_signing(
    raw_psbt: bytes | str,
    *,
    network: str,
    policy_state: CryptoPolicyState,
    policy_epoch: str,
    max_fee_sat: int,
    authorization_nonce: str,
    expires_at: str,
    max_fee_bps_of_input: int = 1000,
    max_fee_rate_upper_bound_sat_vb: float = 1000.0,
    pq_recovery_output_indexes: Iterable[int] = (),
    descriptors: Sequence[str] = (),
    allow_descriptor_xpubs: bool = False,
    require_descriptor_checksums: bool = True,
    output_intent_policy: OutputIntentPolicy | None = None,
    require_output_intent: bool = False,
    reject_address_reuse: bool = True,
    reject_rbf: bool = True,
    reject_dust: bool = True,
    allow_op_return: bool = False,
    max_op_return_script_bytes: int = 83,
    allowed_proprietary_prefixes: Iterable[bytes] = (),
    resource_budget_policy: ResourceBudgetPolicy | None = None,
    detached_pq_algorithms: Sequence[str] = (),
    crypto_agility_policy: CryptoAgilityPolicy | None = None,
    migration_binding: MigrationBatchBinding | None = None,
    unknown_input_weight_overrides: Mapping[int, int] | None = None,
    chain_context_sha256: str | None = None,
    external_parser_quorum_report: Mapping[str, object] | None = None,
    require_external_parser_quorum: bool = False,
    minimum_external_parser_libraries: int = 2,
    external_pq_evidence_report: Mapping[str, object] | None = None,
    require_external_pq_evidence: bool = False,
    minimum_external_pq_execution_targets: int = 1,
    require_external_pq_family_diversity: bool = False,
) -> PreparedSigningGate:
    """Prepare a fail-closed signing package from exact PSBT bytes.

    v2 binds the exact transaction to the policy profile, an explicit nonce and an
    expiry time. Absolute fee, input-value fee ratio, and a rigorous unsigned-vsize
    feerate upper bound are all enforced before authorization.
    """
    if not isinstance(max_fee_sat, int) or isinstance(max_fee_sat, bool) or max_fee_sat < 0:
        raise SigningGateError("max_fee_sat must be an explicit non-negative integer")
    if not isinstance(max_fee_bps_of_input, int) or isinstance(max_fee_bps_of_input, bool) or not 0 <= max_fee_bps_of_input <= 10_000:
        raise SigningGateError("max_fee_bps_of_input must be an integer from 0 through 10000")
    if not isinstance(max_fee_rate_upper_bound_sat_vb, (int, float)) or isinstance(max_fee_rate_upper_bound_sat_vb, bool) or max_fee_rate_upper_bound_sat_vb < 0:
        raise SigningGateError("max_fee_rate_upper_bound_sat_vb must be non-negative")
    if require_output_intent and output_intent_policy is None:
        raise SigningGateError("output intent policy is mandatory for this signing request")

    proprietary_prefixes = tuple(bytes(x) for x in allowed_proprietary_prefixes)
    try:
        audit = audit_psbt(
            raw_psbt,
            network=network,
            policy_state=policy_state,
            pq_recovery_output_indexes=pq_recovery_output_indexes,
            reject_global_xpub=True,
            reject_unknown_fields=True,
            reject_proprietary_fields=True,
            allowed_proprietary_prefixes=proprietary_prefixes,
            max_fee_sat=max_fee_sat,
            max_fee_bps_of_input=max_fee_bps_of_input,
            max_fee_rate_upper_bound_sat_vb=max_fee_rate_upper_bound_sat_vb,
            reject_address_reuse=reject_address_reuse,
            reject_rbf=reject_rbf,
            reject_dust=reject_dust,
            allow_op_return=allow_op_return,
            max_op_return_script_bytes=max_op_return_script_bytes,
        )
        psbt = parse_psbt(raw_psbt)
    except PsbtGuardError as exc:
        raise SigningGateError(str(exc)) from exc
    if not audit.allowed:
        raise SigningGateError("PSBT failed strict local signing audit")

    raw = _psbt_bytes(raw_psbt)
    external_parser_binding = None
    if require_external_parser_quorum and external_parser_quorum_report is None:
        raise SigningGateError("an independent external parser quorum receipt is required")
    if external_parser_quorum_report is not None:
        try:
            external_parser_binding = validate_external_parser_quorum_report(
                external_parser_quorum_report,
                expected_psbt_sha256=hashlib.sha256(raw).hexdigest(),
                expected_txid=audit.txid,
                expected_fee_sat=audit.fee_sat,
                minimum_libraries=minimum_external_parser_libraries,
            )
        except ExternalParserQuorumError as exc:
            raise SigningGateError(str(exc)) from exc

    external_pq_binding = None
    if require_external_pq_evidence and external_pq_evidence_report is None:
        raise SigningGateError("candidate-bound external PQ execution evidence is required")
    if external_pq_evidence_report is not None:
        if not detached_pq_algorithms:
            raise SigningGateError("external PQ evidence cannot be used without configured detached PQ algorithms")
        try:
            external_pq_binding = validate_external_pq_evidence_report(
                external_pq_evidence_report,
                expected_psbt_sha256=hashlib.sha256(raw).hexdigest(),
                expected_txid=audit.txid,
                expected_fee_sat=audit.fee_sat,
                expected_parser_receipt_sha256=external_parser_binding.receipt_sha256 if external_parser_binding else None,
                policy_epoch=policy_epoch,
                required_algorithms=detached_pq_algorithms,
                minimum_execution_targets=minimum_external_pq_execution_targets,
                require_family_diversity=require_external_pq_family_diversity,
            )
        except ExternalPqEvidenceError as exc:
            raise SigningGateError(str(exc)) from exc

    desc_audits = tuple(
        audit_descriptor(
            d,
            allow_public_extended_keys=allow_descriptor_xpubs,
            require_checksum=require_descriptor_checksums,
        )
        for d in descriptors
    )
    blocked_descriptors = [d for d in desc_audits if not d.allowed_for_external_signing_boundary]
    if blocked_descriptors:
        raise SigningGateError("one or more descriptors failed signing-boundary policy")

    tx = psbt.transaction
    output_intent_report: OutputIntentReport | None = None
    if output_intent_policy is not None:
        try:
            output_intent_report = evaluate_output_intent(tx.outputs, network=network, policy=output_intent_policy)
        except OutputIntentError as exc:
            raise SigningGateError(str(exc)) from exc
        if not output_intent_report.satisfied:
            raise SigningGateError("transaction outputs do not match the authorized recipient/change policy")

    resource_report: ResourceBudgetReport | None = None
    if resource_budget_policy is not None:
        try:
            resource_report = evaluate_resource_budget(
                raw, psbt, audit, policy=resource_budget_policy,
                detached_pq_algorithms=detached_pq_algorithms,
                unknown_input_weight_overrides=unknown_input_weight_overrides,
            )
        except ResourceBudgetError as exc:
            raise SigningGateError(str(exc)) from exc
        if not resource_report.satisfied:
            raise SigningGateError(f"resource budget rejected signing candidate: {', '.join(resource_report.limits_exceeded)}")

    migration_report = None
    migration_binding_sha256 = None
    if migration_binding is not None:
        try:
            if migration_binding.network.strip().upper() != network.strip().upper():
                raise MigrationEngineError("migration binding network does not match signing network")
            migration_report = migration_binding.validate_prepared_transaction(tx, audit)
            migration_binding_sha256 = migration_binding.binding_sha256
        except MigrationEngineError as exc:
            raise SigningGateError(str(exc)) from exc

    if chain_context_sha256 is not None:
        text = chain_context_sha256.lower()
        if len(text) != 64 or any(c not in "0123456789abcdef" for c in text):
            raise SigningGateError("chain_context_sha256 must be 32-byte hex")
        chain_context_sha256 = text

    input_script_types = tuple(str(x) for x in audit.metadata_exposure.get("input_script_types", ()))
    bitcoin_algorithms = []
    if any(x == "P2TR" for x in input_script_types):
        bitcoin_algorithms.append("SECP256K1-SCHNORR")
    if any(x != "P2TR" for x in input_script_types):
        bitcoin_algorithms.append("SECP256K1-ECDSA")
    cbom = build_crypto_bill_of_materials(
        bitcoin_signature_algorithms=bitcoin_algorithms or ("SECP256K1-ECDSA",),
        pq_authorization_algorithms=detached_pq_algorithms,
    )
    agility_policy_sha256 = None
    if crypto_agility_policy is not None:
        agility = evaluate_algorithm_set(tuple(detached_pq_algorithms), crypto_agility_policy)
        if policy_state == CryptoPolicyState.HYBRID_REQUIRED and not agility.satisfied:
            raise SigningGateError("configured PQ algorithm set cannot satisfy crypto-agility policy")
        agility_policy_sha256 = crypto_agility_policy.policy_sha256

    input_payload = [
        {"index": i, "prev_txid": txin.prev_txid.lower(), "vout": txin.vout, "sequence": txin.sequence}
        for i, txin in enumerate(tx.inputs)
    ]
    output_payload = [
        {"index": i, "value_sat": out.value_sat, "script_pubkey_hex": out.script_pubkey.hex()}
        for i, out in enumerate(tx.outputs)
    ]
    policy_payload = {
        "schema": "WS-BITCOIN-SIGNING-POLICY-V2",
        "network": network.strip().upper(),
        "policy_state": policy_state.value,
        "policy_epoch": policy_epoch,
        "max_fee_sat": max_fee_sat,
        "max_fee_bps_of_input": max_fee_bps_of_input,
        "max_fee_rate_upper_bound_sat_vb": float(max_fee_rate_upper_bound_sat_vb),
        "reject_global_xpub": True,
        "reject_unknown_fields": True,
        "reject_proprietary_fields": True,
        "allowed_proprietary_prefix_sha256": sorted(hashlib.sha256(x).hexdigest() for x in proprietary_prefixes),
        "reject_address_reuse": reject_address_reuse,
        "reject_rbf": reject_rbf,
        "reject_dust": reject_dust,
        "allow_op_return": allow_op_return,
        "max_op_return_script_bytes": max_op_return_script_bytes,
        "require_descriptor_checksums": require_descriptor_checksums,
        "allow_descriptor_xpubs": allow_descriptor_xpubs,
        "descriptor_sha256": [d.descriptor_sha256 for d in desc_audits],
        "output_intent_policy_sha256": output_intent_report.policy_sha256 if output_intent_report else None,
        "resource_budget_policy_sha256": resource_report.policy_sha256 if resource_report else None,
        "resource_projection": None if resource_report is None else {
            "projected_signed_weight_wu": resource_report.projected_signed_weight_wu,
            "projected_signed_vsize": resource_report.projected_signed_vsize,
            "projected_detached_pq_signature_bytes": resource_report.projected_detached_pq_signature_bytes,
        },
        "cbom_sha256": cbom["cbom_sha256"],
        "crypto_agility_policy_sha256": agility_policy_sha256,
        "migration_binding_sha256": migration_binding_sha256,
        "chain_context_sha256": chain_context_sha256,
        "external_parser_quorum_receipt_sha256": external_parser_binding.receipt_sha256 if external_parser_binding else None,
        "minimum_external_parser_libraries": minimum_external_parser_libraries if external_parser_binding else None,
        "external_pq_evidence_receipt_sha256": external_pq_binding.receipt_sha256 if external_pq_binding else None,
        "external_pq_candidate_challenge_sha256": external_pq_binding.candidate_challenge_sha256 if external_pq_binding else None,
        "minimum_external_pq_execution_targets": minimum_external_pq_execution_targets if external_pq_binding else None,
        "require_external_pq_family_diversity": bool(require_external_pq_family_diversity) if external_pq_binding else None,
    }
    signing_policy_sha256 = _canonical_hash(b"WS-BITCOIN-SIGNING-POLICY-V2", policy_payload)
    raw_unsigned = tx.serialize(include_witness=False)
    intent = BitcoinReleaseIntent(
        network=network.strip().upper(),
        unsigned_tx_sha256=hashlib.sha256(raw_unsigned).hexdigest(),
        input_set_sha256=_canonical_hash(b"WS-BITCOIN-INPUT-SET-V1", input_payload),
        output_set_sha256=_canonical_hash(b"WS-BITCOIN-OUTPUT-SET-V1", output_payload),
        fee_sat=audit.fee_sat,
        policy_epoch=policy_epoch,
        signing_policy_sha256=signing_policy_sha256,
        authorization_nonce=authorization_nonce,
        expires_at=expires_at,
    )
    try:
        _ = intent.intent_sha256
    except ReleasePolicyError as exc:
        raise SigningGateError(str(exc)) from exc
    return PreparedSigningGate(
        psbt_sha256=hashlib.sha256(raw).hexdigest(),
        txid=tx.txid,
        network=network.strip().upper(),
        policy_state=policy_state,
        audit=audit,
        descriptor_audits=desc_audits,
        output_intent_report=output_intent_report,
        signing_policy_sha256=signing_policy_sha256,
        intent=intent,
        resource_budget_report=resource_report,
        crypto_bill_of_materials=cbom,
        crypto_agility_policy_sha256=agility_policy_sha256,
        migration_binding_sha256=migration_binding_sha256,
        migration_report=migration_report,
        chain_context_sha256=chain_context_sha256,
        external_parser_quorum_binding=external_parser_binding.to_dict() if external_parser_binding else None,
        external_pq_evidence_binding=external_pq_binding.to_dict() if external_pq_binding else None,
    )


def authorize_prepared_signing(
    prepared: PreparedSigningGate,
    *,
    pq_attestation: PqReleaseAttestation | None = None,
    pq_signature_verifier: Callable[[bytes, bytes, bytes], bool] | None = None,
    pq_quorum_report: dict | None = None,
    approvals: Sequence[SignedApproval] = (),
    trusted_approvers: Mapping[str, bytes] | None = None,
    required_approval_count: int = 0,
    required_approval_roles: Sequence[str] = (),
    authorization_ledger_path: str | None = None,
    now: dt.datetime | None = None,
) -> dict:
    """Authorize a prepared package, optionally requiring an operator quorum."""
    try:
        auth = authorize_release(
            intent=prepared.intent,
            policy_state=prepared.policy_state,
            pq_attestation=pq_attestation,
            pq_signature_verifier=pq_signature_verifier,
            pq_quorum_report=pq_quorum_report,
            now=now,
        )
    except ReleasePolicyError as exc:
        raise SigningGateError(str(exc)) from exc

    if required_approval_count and trusted_approvers is None:
        raise SigningGateError("trusted approver registry is required when an approval quorum is configured")
    try:
        quorum = verify_approval_quorum(
            intent_sha256=prepared.intent.intent_sha256,
            approvals=approvals,
            trusted_approvers=trusted_approvers or {},
            required_count=required_approval_count,
            required_roles=required_approval_roles,
            now=now,
        )
    except ApprovalQuorumError as exc:
        raise SigningGateError(str(exc)) from exc
    if not quorum["satisfied"]:
        raise SigningGateError("operator approval quorum is not satisfied")

    result = {
        "schema": "WS-BITCOIN-SIGNING-GATE-AUTHORIZATION-V2",
        "psbt_sha256": prepared.psbt_sha256,
        "txid": prepared.txid,
        "intent_sha256": prepared.intent.intent_sha256,
        "signing_policy_sha256": prepared.signing_policy_sha256,
        "policy_state": prepared.policy_state.value,
        "authorization": auth,
        "operator_quorum": quorum,
        "authorized_for_local_signing_workflow": auth["authorized_for_local_signing_workflow"] and quorum["satisfied"],
        "transaction_broadcast_authorized": False,
        "mainnet_authority": False,
    }
    if authorization_ledger_path is not None:
        try:
            rec = append_authorization_receipt(authorization_ledger_path, result)
        except AuthorizationLedgerError as exc:
            raise SigningGateError(str(exc)) from exc
        result["authorization_ledger_record_hash"] = rec["record_hash"]
        result["authorization_ledger_sequence"] = rec["sequence"]
    return result


def authorize_prepared_with_kms_provider(
    prepared: PreparedSigningGate,
    provider: object,
    *,
    approvals: Sequence[SignedApproval] = (),
    trusted_approvers: Mapping[str, bytes] | None = None,
    required_approval_count: int = 0,
    required_approval_roles: Sequence[str] = (),
    authorization_ledger_path: str | None = None,
    now: dt.datetime | None = None,
) -> dict:
    """Perform one governed ML-DSA authorization using the configured KMS provider."""
    if prepared.policy_state != CryptoPolicyState.HYBRID_REQUIRED:
        raise SigningGateError("KMS PQ authorization helper is only used for HYBRID_REQUIRED in this candidate")
    try:
        from .aws_kms_provider import provider_operation_id

        descriptor = provider.descriptor
        message = prepared.intent.canonical_bytes()
        op_id = provider_operation_id(
            key_arn=descriptor.key_arn,
            message=message,
            context=RELEASE_ATTESTATION_CONTEXT,
        )
        result = provider.begin_sign(op_id, message, RELEASE_ATTESTATION_CONTEXT)
        attestation = build_pq_release_attestation_from_provider_result(
            intent=prepared.intent,
            descriptor=descriptor,
            result=result,
        )
        return authorize_prepared_signing(
            prepared,
            pq_attestation=attestation,
            pq_signature_verifier=lambda m, c, s: provider.verify_with_kms(message=m, context=c, signature=s),
            approvals=approvals,
            trusted_approvers=trusted_approvers,
            required_approval_count=required_approval_count,
            required_approval_roles=required_approval_roles,
            authorization_ledger_path=authorization_ledger_path,
            now=now,
        )
    except SigningGateError:
        raise
    except Exception as exc:
        raise SigningGateError("KMS-backed prepared signing authorization failed") from exc
