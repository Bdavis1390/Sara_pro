"""Adapters into the WS-CAE cryptographic-continuity manifest."""

from __future__ import annotations

from .continuity_manifest import ContinuityManifest, EvidenceRef
from .patch import ChainPatch


def from_chain_patch(patch: ChainPatch, *, version: str, as_of: str) -> ContinuityManifest:
    p = patch.profile
    if p.stable_authority_id and p.authenticator_replaceable:
        authority = "STABLE_AUTHORITY_REPLACEABLE_AUTHENTICATOR"
    elif p.authenticator_replaceable:
        authority = "REPLACEABLE_AUTHENTICATOR"
    else:
        authority = "DIRECT_OR_STATIC_AUTHORITY"

    agility = "DOCUMENTED" if p.authenticator_replaceable else "NOT_ESTABLISHED"
    recovery = "DOCUMENTED" if p.recovery_state_documented else "NOT_DOCUMENTED"
    evidence = tuple(EvidenceRef(item.label, item.url, item.claim) for item in patch.evidence)

    return ContinuityManifest(
        subject_id=f"urn:ws-cae:chain:{patch.chain.strip().lower()}",
        subject_type="CHAIN",
        version=version,
        as_of=as_of,
        authority_model=authority,
        implementation_maturity=p.implementation_maturity,
        protocol_commitment_state=p.protocol_commitment_state,
        pq_authorization_state=p.pq_authorization_state,
        consensus_pq_state=p.consensus_pq_state,
        crypto_agility_state=agility,
        recovery_state=recovery,
        dependencies=tuple(),
        evidence=evidence,
    )
