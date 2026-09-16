"""Claims-controlled per-chain canonical test vectors for PQ migration.

The vectors bridge public chain-readiness evidence into the generic Worldshepherd
canonical authority context without pretending to implement a chain's native
transaction format.  Native cryptographic capability and Worldshepherd reference
PQC are deliberately separate fields.

No vector creates a native transaction, wallet signature, consensus message,
execution authority, or live-value authorization.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from hashlib import sha256
import json

from security.qcrypto.canonical_authority_envelope import CanonicalAuthorityEnvelope
from security.qcrypto.canonical_pq_signing_context import (
    CanonicalSigningContextDecision,
    CanonicalSigningContextRequest,
    build_canonical_signing_context,
)
from security.qcrypto.chain_pq_readiness_profiles import (
    PROFILES,
    ProfileLayer,
    assess_chain_profile,
)
from security.qcrypto.hybrid_authority_migration import (
    AuthorityEnvelope,
    AuthorityLayer,
    AuthorityPolicy,
    MigrationRequirement,
)


class VectorClass(StrEnum):
    DESIGN_ONLY = "DESIGN_ONLY"
    ROADMAP_INTEROP = "ROADMAP_INTEROP"
    LIVE_ACCOUNT_REFERENCE = "LIVE_ACCOUNT_REFERENCE"


@dataclass(frozen=True)
class ChainVectorSpec:
    chain_id: str
    vector_id: str
    vector_class: VectorClass
    adapter_class: str
    native_authority_capability: str
    native_pq_algorithm: str | None
    ws_reference_pq_algorithm: str
    ws_reference_class: str
    replay_domain: str
    live_native_pq_account_support: bool
    native_transaction_format_implemented: bool = False
    native_signature_generated: bool = False
    live_value_authorized: bool = False
    execution_authority: bool = False


@dataclass(frozen=True)
class ChainCanonicalVectorDecision:
    chain_id: str
    vector_id: str
    vector_class: str
    profile_verdict: str
    profile_evidence_as_of: str
    account_readiness: str
    consensus_readiness: str
    native_authority_capability: str
    native_pq_algorithm: str | None
    ws_reference_pq_algorithm: str
    ws_reference_class: str
    native_and_reference_algorithm_same: bool
    canonical_context_ready: bool
    canonical_context_digest: str | None
    canonical_preimage_hex: str | None
    canonical_fields: dict[str, str]
    source_urls: tuple[str, ...]
    blockers: tuple[str, ...]
    native_transaction_format_implemented: bool = False
    native_signature_generated: bool = False
    live_value_authorized: bool = False
    execution_authority: bool = False
    production_protocol_integration: bool = False
    whole_chain_pq_security_established: bool = False
    claim_boundary: str = (
        "Worldshepherd migration test-vector result only. Native chain evidence and "
        "Worldshepherd reference PQC are separate; this does not establish a native "
        "transaction implementation, production activation, whole-chain PQ security, "
        "or authority to move value."
    )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["source_urls"] = list(self.source_urls)
        data["blockers"] = list(self.blockers)
        return data


SPECS: dict[str, ChainVectorSpec] = {
    "BITCOIN": ChainVectorSpec(
        chain_id="BITCOIN",
        vector_id="BTC-DRAFT-PQ-AUTH-REFERENCE-V1",
        vector_class=VectorClass.DESIGN_ONLY,
        adapter_class="DRAFT_PQ_OUTPUT_MIGRATION_REFERENCE",
        native_authority_capability="BIP-360/BIP-361 DRAFT MIGRATION CONCEPTS",
        native_pq_algorithm=None,
        ws_reference_pq_algorithm="ML-DSA",
        ws_reference_class="WORLDSHEPHERD_REFERENCE_NOT_BIP_SIGNATURE_SELECTION",
        replay_domain="bitcoin-pq-migration-reference",
        live_native_pq_account_support=False,
    ),
    "ETHEREUM": ChainVectorSpec(
        chain_id="ETHEREUM",
        vector_id="ETH-PQ-AA-ROADMAP-REFERENCE-V1",
        vector_class=VectorClass.ROADMAP_INTEROP,
        adapter_class="PQ_ACCOUNT_ABSTRACTION_ROADMAP_REFERENCE",
        native_authority_capability="PQ INTEROP DEVNET / SIGNATURE-AGILITY ROADMAP",
        native_pq_algorithm=None,
        ws_reference_pq_algorithm="ML-DSA",
        ws_reference_class="WORLDSHEPHERD_REFERENCE_NOT_MAINNET_ACCOUNT_PRIMITIVE",
        replay_domain="ethereum-pq-account-reference",
        live_native_pq_account_support=False,
    ),
    "ALGORAND": ChainVectorSpec(
        chain_id="ALGORAND",
        vector_id="ALGO-FALCON-ACCOUNT-REFERENCE-V1",
        vector_class=VectorClass.LIVE_ACCOUNT_REFERENCE,
        adapter_class="NATIVE_REKEY_PQ_ACCOUNT_REFERENCE",
        native_authority_capability="LIVE FALCON-1024 ACCOUNT AUTHORIZATION",
        native_pq_algorithm="FALCON-1024",
        ws_reference_pq_algorithm="ML-DSA",
        ws_reference_class="STANDARDIZED_REFERENCE_DISTINCT_FROM_NATIVE_FALCON",
        replay_domain="algorand-pq-account-reference",
        live_native_pq_account_support=True,
    ),
}


def _observation(profile, layer: ProfileLayer):
    return next(item for item in profile.observations if item.layer is layer)


def _stable_digest(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def build_chain_canonical_vector(chain_id: str) -> ChainCanonicalVectorDecision:
    """Build one non-native canonical migration vector for a tracked chain."""

    try:
        profile = PROFILES[chain_id]
        spec = SPECS[chain_id]
    except KeyError as exc:
        raise ValueError(f"unsupported chain vector: {chain_id}") from exc

    profile_decision = assess_chain_profile(profile)
    account = _observation(profile, ProfileLayer.ACCOUNTS)
    consensus = _observation(profile, ProfileLayer.CONSENSUS)
    sources = tuple(
        sorted(
            {
                url
                for observation in profile.observations
                for url in observation.source_urls
            }
        )
    )

    payload_digest = _stable_digest(
        {
            "vector_id": spec.vector_id,
            "chain_id": spec.chain_id,
            "vector_class": spec.vector_class.value,
            "profile_evidence_as_of": profile.evidence_as_of,
            "profile_verdict": profile_decision.verdict,
            "account_readiness": account.readiness.name,
            "consensus_readiness": consensus.readiness.name,
            "native_authority_capability": spec.native_authority_capability,
            "native_pq_algorithm": spec.native_pq_algorithm,
            "ws_reference_pq_algorithm": spec.ws_reference_pq_algorithm,
        }
    )
    evidence_digest = _stable_digest(
        {
            "chain_id": chain_id,
            "evidence_as_of": profile.evidence_as_of,
            "sources": sources,
            "observations": [asdict(item) for item in profile.observations],
        }
    )
    recovery_digest = _stable_digest(
        {
            "chain_id": chain_id,
            "scope": "TEST_VECTOR_RECOVERY_COMMITMENT_ONLY",
            "live_value_authorized": False,
        }
    )

    network_id = f"ws-reference-{chain_id.lower()}"
    domain_separator = "WS-QCRYPTO-CHAIN-VECTOR-V1"
    authority = AuthorityEnvelope(
        network_id=network_id,
        domain_separator=domain_separator,
        payload_digest=payload_digest,
        authority_id=f"{chain_id.lower()}-reference-authority",
        authority_layer=AuthorityLayer.ACCOUNT,
        declared_requirement=MigrationRequirement.HYBRID_REQUIRED,
        envelope_version=1,
        key_epoch=0,
        classical_algorithm_id="ECDSA",
        pq_algorithm_id=spec.ws_reference_pq_algorithm,
        classical_signature_present=True,
        pq_signature_present=True,
        classical_required_for_acceptance=True,
        pq_required_for_acceptance=True,
        recovery_evidence_present=True,
    )
    policy = AuthorityPolicy(
        network_id=network_id,
        domain_separator=domain_separator,
        minimum_requirement=MigrationRequirement.HYBRID_REQUIRED,
        minimum_envelope_version=1,
        minimum_key_epoch=0,
        require_recovery_evidence=True,
    )
    adapter = CanonicalAuthorityEnvelope(
        chain=chain_id,
        adapter_class=spec.adapter_class,
        stable_authority_id=True,
        authenticator_versioned=True,
        authenticator_replaceable=True,
        policy_versioned=True,
        recovery_commitment_present=True,
        chain_binding_present=True,
        replay_domain_present=True,
        evidence_binding_present=True,
        explicit_human_approval_required=True,
        live_chain_support=False,
        independent_review_complete=False,
        consensus_layer_pq=False,
    )
    context: CanonicalSigningContextDecision = build_canonical_signing_context(
        CanonicalSigningContextRequest(
            authority=authority,
            authority_policy=policy,
            adapter=adapter,
            policy_version=1,
            replay_domain=spec.replay_domain,
            replay_sequence=0,
            evidence_digest=evidence_digest,
            recovery_commitment_digest=recovery_digest,
        )
    )

    blockers: list[str] = []
    if not context.ready:
        blockers.extend(context.blockers)
    if profile_decision.known_blocking_layers:
        blockers.append(
            "Source-backed profile retains classical blocking layers: "
            + ", ".join(profile_decision.known_blocking_layers)
        )
    if profile_decision.unknown_layers:
        blockers.append(
            "Source-backed profile retains unknown layers: "
            + ", ".join(profile_decision.unknown_layers)
        )
    if spec.native_pq_algorithm != spec.ws_reference_pq_algorithm:
        blockers.append(
            "Native PQ algorithm and Worldshepherd reference algorithm are distinct; "
            "reference signature interoperability is not native-chain signature proof."
        )

    return ChainCanonicalVectorDecision(
        chain_id=chain_id,
        vector_id=spec.vector_id,
        vector_class=spec.vector_class.value,
        profile_verdict=profile_decision.verdict,
        profile_evidence_as_of=profile.evidence_as_of,
        account_readiness=account.readiness.name,
        consensus_readiness=consensus.readiness.name,
        native_authority_capability=spec.native_authority_capability,
        native_pq_algorithm=spec.native_pq_algorithm,
        ws_reference_pq_algorithm=spec.ws_reference_pq_algorithm,
        ws_reference_class=spec.ws_reference_class,
        native_and_reference_algorithm_same=(
            spec.native_pq_algorithm == spec.ws_reference_pq_algorithm
        ),
        canonical_context_ready=context.ready,
        canonical_context_digest=context.context_digest,
        canonical_preimage_hex=context.canonical_preimage_hex,
        canonical_fields=context.canonical_fields,
        source_urls=sources,
        blockers=tuple(blockers),
    )


def build_all_chain_canonical_vectors() -> tuple[ChainCanonicalVectorDecision, ...]:
    return tuple(build_chain_canonical_vector(chain_id) for chain_id in SPECS)
