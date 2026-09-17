"""Production-assurance claims guard for Worldshepherd QCRYPTO.

The guard intentionally prevents evidence from one assurance axis from promoting
unrelated claims. In particular, use of a provider backed by a validated HSM does
not make Worldshepherd itself FIPS validated, and software readiness never grants
native-chain signing, broadcast, mainnet, or real-value authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProductionEvidence:
    provider_adapter_contract_passed: bool = False
    live_hsm_kms_probe_passed: bool = False
    provider_fips_module_documented: bool = False
    provider_cmvp_certificate_active: bool = False
    worldshepherd_cmvp_certificate_verified: bool = False
    bitcoin_native_signature_verified: bool = False
    ethereum_native_signature_verified: bool = False
    transaction_broadcast_receipt_verified: bool = False
    mainnet_authorization_recorded: bool = False
    real_value_execution_receipt_verified: bool = False
    federal_assessment_attributable: bool = False
    federal_scope_and_version_bound: bool = False
    independent_reproduction_recorded: bool = False
    pq_transaction_authority_covered: bool = False
    pq_consensus_covered: bool = False
    pq_data_availability_covered: bool = False
    pq_bridge_custody_covered: bool = False
    pq_network_transport_covered: bool = False
    production_deployment_evidence: bool = False


@dataclass(frozen=True)
class ProductionAssessment:
    hsm_kms_state: str
    fips_state: str
    bitcoin_native_signing_claim: bool
    ethereum_native_signing_claim: bool
    broadcast_claim: bool
    mainnet_authority_claim: bool
    real_value_movement_claim: bool
    federal_compliance_claim: bool
    independent_validation_claim: bool
    end_to_end_pq_cryptocurrency_security_claim: bool

    def to_dict(self) -> dict:
        return asdict(self)


def assess_production(e: ProductionEvidence) -> ProductionAssessment:
    if e.live_hsm_kms_probe_passed:
        hsm_state = "LIVE_HSM_KMS_INTEGRATION_OBSERVED"
    elif e.provider_adapter_contract_passed:
        hsm_state = "PROVIDER_ADAPTER_IMPLEMENTED_NOT_LIVE_INTEGRATED"
    else:
        hsm_state = "NO_PRODUCTION_HSM_KMS_EVIDENCE"

    if e.worldshepherd_cmvp_certificate_verified:
        fips_state = "WORLDSHEPHERD_CMVP_VALIDATION_EVIDENCE_PRESENT"
    elif (
        e.live_hsm_kms_probe_passed
        and e.provider_fips_module_documented
        and e.provider_cmvp_certificate_active
    ):
        fips_state = "VALIDATED_PROVIDER_MODULE_USED_NOT_WORLD_SHEPHERD_VALIDATED"
    elif e.provider_fips_module_documented:
        fips_state = "PROVIDER_FIPS_DOCUMENTATION_ONLY"
    else:
        fips_state = "FIPS_VALIDATION_NOT_ESTABLISHED"

    federal = e.federal_assessment_attributable and e.federal_scope_and_version_bound
    independent = e.independent_reproduction_recorded
    end_to_end_pq = all(
        (
            e.pq_transaction_authority_covered,
            e.pq_consensus_covered,
            e.pq_data_availability_covered,
            e.pq_bridge_custody_covered,
            e.pq_network_transport_covered,
            e.production_deployment_evidence,
            independent,
        )
    )

    return ProductionAssessment(
        hsm_kms_state=hsm_state,
        fips_state=fips_state,
        bitcoin_native_signing_claim=e.bitcoin_native_signature_verified,
        ethereum_native_signing_claim=e.ethereum_native_signature_verified,
        broadcast_claim=e.transaction_broadcast_receipt_verified,
        mainnet_authority_claim=(
            e.mainnet_authorization_recorded and e.transaction_broadcast_receipt_verified
        ),
        real_value_movement_claim=(
            e.real_value_execution_receipt_verified
            and e.mainnet_authorization_recorded
            and e.transaction_broadcast_receipt_verified
        ),
        federal_compliance_claim=federal,
        independent_validation_claim=independent,
        end_to_end_pq_cryptocurrency_security_claim=end_to_end_pq,
    )
