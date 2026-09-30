"""Worldshepherd QCRYPTO Bitcoin hardening candidate v3.1.

Isolated recovery-scaffold implementation. It is locally tested but is not a
Bitcoin consensus implementation, not mainnet-enabled, and not represented as a
canonical Sara_pro merge while repository continuity is unavailable.
"""
from .address_codec import AddressBinding, AddressCodecError, address_to_scriptpubkey, bind_address, scriptpubkey_to_address
from .approval_quorum import ApprovalQuorumError, ApprovalStatement, SignedApproval, sign_approval, verify_approval_quorum
from .authorization_ledger import AuthorizationLedgerError, append_authorization_receipt, verify_authorization_ledger
from .output_intent import ExpectedPayment, OutputIntentError, OutputIntentPolicy, OutputIntentReport, evaluate_output_intent
from .signature_policy import (
    ParsedEcdsaSignature, ParsedSchnorrSignature, SignaturePolicyError,
    enforce_sighash_policy, parse_schnorr_signature, parse_strict_der_ecdsa_signature,
)
from .aws_kms_provider import (
    AwsKmsDescriptor,
    AwsKmsMlDsa65Provider,
    AwsKmsProviderError,
    AwsKmsProviderConflict,
    ProviderAmbiguousOutcome,
    ProviderResult,
    ProviderState,
    provider_operation_id,
)
from .bitcoin_quantum_policy import (
    BitcoinQuantumPolicyError,
    CryptoPolicyState,
    ExposureClass,
    OutputPolicyDecision,
    ProposedOutput,
    UtxoAssessment,
    UtxoRecord,
    assess_utxo,
    build_migration_manifest,
    evaluate_new_output,
)
from .bitcoin_tx import (
    BitcoinTransaction, BitcoinTxError, SerializedOutputDecision,
    SerializedTransactionPolicyReport, TxInput, TxOutput, classify_script_pubkey,
    encode_compact_size, evaluate_serialized_transaction, parse_transaction,
    read_compact_size, sha256d,
)
from .external_parser_quorum import ExternalParserQuorumBinding, ExternalParserQuorumError, validate_external_parser_quorum_report
from .descriptor_guard import (
    DescriptorAudit, DescriptorGuardError, audit_descriptor, descriptor_checksum,
    descriptor_checksum_valid, descriptor_with_checksum,
)
from .psbt_guard import ParsedPsbt, PsbtAuditReport, PsbtGuardError, audit_psbt, parse_psbt
from .bitcoin_core_interop import (
    BitcoinCoreCLI, BitcoinCoreInteropError, CoreInteropReport, core_capabilities, cross_check_prepared_with_core,
)
from .client_factory import build_production_kms_client, production_botocore_config_kwargs
from .operation_journal import (
    FileOperationJournal,
    JournalRecord,
    OperationJournalConflict,
    OperationJournalError,
)
from .p2mr_draft import (
    BIP360_VERSION,
    P2MrDraftError,
    P2MrLeaf,
    build_balanced_merkle_root,
    encode_segwit_v2_bech32m,
    experimental_p2mr_address,
    p2mr_control_block,
    p2mr_script_pubkey,
    tapbranch_hash,
    tapleaf_hash,
    verify_p2mr_merkle_path,
)
from .release_policy import (
    RELEASE_ATTESTATION_CONTEXT,
    BitcoinReleaseIntent,
    PqReleaseAttestation,
    ReleasePolicyError,
    authorize_release,
    build_pq_release_attestation_from_provider_result,
)
from .signing_gate import (
    PreparedSigningGate, SigningGateError, authorize_prepared_signing,
    authorize_prepared_with_kms_provider, prepare_psbt_signing,
)
from .secp256k1_testnet_primitive import (
    AwsKmsSecp256k1TestnetDigestSigner,
    ClassicalDigestSignature,
    ClassicalSignerError,
    classical_operation_id,
)


from .crypto_agility import (
    AlgorithmFamily, AlgorithmSpec, AlgorithmState, CryptoAgilityError, CryptoAgilityPolicy,
    CryptoAgilityReport, algorithm_spec, build_crypto_bill_of_materials, evaluate_algorithm_set, normalize_algorithm_id,
)
from .key_lifecycle import KeyLifecycleError, KeyRecord, KeyRegistry, KeyState
from .runtime_attestation import RuntimeAttestationError, RuntimeAttestationStatement, SignedRuntimeAttestation, sign_runtime_attestation, verify_runtime_attestation
from .resource_budget import ResourceBudgetError, ResourceBudgetPolicy, ResourceBudgetReport, evaluate_resource_budget
from .pq_quorum import (
    AwsKmsMlDsa65Adapter, CallablePqProviderAdapter, LatencyBudget, PqProviderAttestation,
    PqQuorumError, ProviderTiming, execute_and_verify_pq_quorum, verify_pq_quorum,
)
from .openssl_pq_provider import OpenSslPqAuthorizationProvider, OpenSslPqProviderError, generate_openssl_pq_private_key
from .migration_engine import MigrationBatchBinding, MigrationEngineError, MigrationStateStore, build_migration_batches
from .migration_psbt import MigrationPsbtBuildResult, MigrationPsbtError, MigrationSpendInput, build_sweep_migration_psbt
from .chain_context import ChainContextError, ChainContextPolicy, validate_chain_context_report, verify_psbt_chain_context_with_core
from .emergency_state import EmergencyStateError, EmergencyStateLedger
from .governance_plane import (
    EmergencyMode, GovernancePlaneError, PrimeDecision, PrimePolicyProfile, SaraWorkflowJournal,
    SaraWorkflowState, evaluate_prime_decision, render_overwatch_openmetrics,
)
from .control_plane import ControlPlaneError, GovernedPreparation, GovernedSigningPolicy, authorize_governed_signing, prepare_governed_signing
from .policy_epoch import PolicyEpochError, QuantumPolicyLedger
from .source_integrity import SourceIntegrityError, SourceIntegrityPolicy, build_source_manifest, verify_source_manifest

__all__ = [
    "AwsKmsDescriptor", "AwsKmsMlDsa65Provider", "AwsKmsProviderError",
    "AwsKmsProviderConflict", "ProviderAmbiguousOutcome", "ProviderResult",
    "ProviderState", "provider_operation_id", "build_production_kms_client",
    "production_botocore_config_kwargs", "FileOperationJournal", "JournalRecord",
    "OperationJournalConflict", "OperationJournalError", "BitcoinQuantumPolicyError",
    "CryptoPolicyState", "ExposureClass", "OutputPolicyDecision", "ProposedOutput",
    "UtxoAssessment", "UtxoRecord", "assess_utxo", "build_migration_manifest",
    "evaluate_new_output", "BIP360_VERSION", "P2MrDraftError", "P2MrLeaf",
    "build_balanced_merkle_root", "encode_segwit_v2_bech32m",
    "experimental_p2mr_address", "p2mr_control_block", "p2mr_script_pubkey",
    "tapbranch_hash", "tapleaf_hash", "verify_p2mr_merkle_path",
    "BitcoinReleaseIntent", "PqReleaseAttestation", "ReleasePolicyError",
    "authorize_release", "AwsKmsSecp256k1TestnetDigestSigner",
    "ClassicalDigestSignature", "ClassicalSignerError", "classical_operation_id",
    "BitcoinTransaction", "BitcoinTxError", "SerializedOutputDecision",
    "SerializedTransactionPolicyReport", "TxInput", "TxOutput",
    "classify_script_pubkey", "encode_compact_size", "evaluate_serialized_transaction",
    "parse_transaction", "read_compact_size", "sha256d", "DescriptorAudit",
    "DescriptorGuardError", "audit_descriptor", "descriptor_checksum",
    "descriptor_checksum_valid", "descriptor_with_checksum", "BitcoinCoreCLI",
    "BitcoinCoreInteropError", "CoreInteropReport", "cross_check_prepared_with_core",
    "ParsedPsbt", "PsbtAuditReport",
    "PsbtGuardError", "audit_psbt", "parse_psbt", "RELEASE_ATTESTATION_CONTEXT",
    "build_pq_release_attestation_from_provider_result", "PreparedSigningGate",
    "SigningGateError", "authorize_prepared_signing",
    "authorize_prepared_with_kms_provider", "prepare_psbt_signing",
    "AddressBinding", "AddressCodecError", "address_to_scriptpubkey", "bind_address",
    "scriptpubkey_to_address", "ApprovalQuorumError", "ApprovalStatement",
    "SignedApproval", "sign_approval", "verify_approval_quorum",
    "AuthorizationLedgerError", "append_authorization_receipt", "verify_authorization_ledger",
    "ExpectedPayment", "OutputIntentError", "OutputIntentPolicy", "OutputIntentReport",
    "evaluate_output_intent", "ParsedEcdsaSignature", "ParsedSchnorrSignature",
    "SignaturePolicyError", "enforce_sighash_policy", "parse_schnorr_signature",
    "ExternalParserQuorumBinding", "ExternalParserQuorumError", "validate_external_parser_quorum_report",
    "parse_strict_der_ecdsa_signature", "core_capabilities",

    "AlgorithmFamily", "AlgorithmSpec", "AlgorithmState", "CryptoAgilityError", "CryptoAgilityPolicy",
    "CryptoAgilityReport", "algorithm_spec", "build_crypto_bill_of_materials", "evaluate_algorithm_set", "normalize_algorithm_id",
    "KeyLifecycleError", "KeyRecord", "KeyRegistry", "KeyState",
    "RuntimeAttestationError", "RuntimeAttestationStatement", "SignedRuntimeAttestation", "sign_runtime_attestation", "verify_runtime_attestation",
    "ResourceBudgetError", "ResourceBudgetPolicy", "ResourceBudgetReport", "evaluate_resource_budget",
    "AwsKmsMlDsa65Adapter", "CallablePqProviderAdapter", "LatencyBudget", "PqProviderAttestation", "PqQuorumError", "ProviderTiming",
    "execute_and_verify_pq_quorum", "verify_pq_quorum",
    "OpenSslPqAuthorizationProvider", "OpenSslPqProviderError", "generate_openssl_pq_private_key",
    "MigrationBatchBinding", "MigrationEngineError", "MigrationStateStore", "build_migration_batches",
    "MigrationPsbtBuildResult", "MigrationPsbtError", "MigrationSpendInput", "build_sweep_migration_psbt",
    "ChainContextError", "ChainContextPolicy", "validate_chain_context_report", "verify_psbt_chain_context_with_core",
    "EmergencyStateError", "EmergencyStateLedger", "EmergencyMode", "GovernancePlaneError", "PrimeDecision", "PrimePolicyProfile",
    "SaraWorkflowJournal", "SaraWorkflowState", "evaluate_prime_decision", "render_overwatch_openmetrics",
    "ControlPlaneError", "GovernedPreparation", "GovernedSigningPolicy", "authorize_governed_signing", "prepare_governed_signing",
    "PolicyEpochError", "QuantumPolicyLedger", "SourceIntegrityError", "SourceIntegrityPolicy", "build_source_manifest", "verify_source_manifest",
]
