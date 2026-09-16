"""Deterministic, fail-closed pre-signing context for defensive PQ migration.

A signing preimage must exist before a signature exists.  This module therefore
models pre-sign authority intent separately from the post-sign AuthorityEnvelope
used by hybrid_authority_migration.  It does not generate keys, create or verify
signatures, authorize execution, or move value.

The context binds network, authority role, algorithm intent, migration policy,
version/epoch floors, replay state, payload/evidence digests, and recovery
commitment into fixed binary framing and a SHA-256 context digest.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
import struct
import unicodedata

from security.qcrypto.canonical_authority_envelope import CanonicalAuthorityEnvelope
from security.qcrypto.hybrid_authority_migration import (
    AuthorityLayer,
    AuthorityPolicy,
    MigrationRequirement,
)
from security.qcrypto.pqc_algorithm_policy import (
    CryptoRole,
    REGISTRY,
    StandardizationState,
    validate_registry,
)


CONTEXT_SCHEMA = "WS-QCRYPTO-CANONICAL-SIGNING-CONTEXT-V1"
DOMAIN_TAG = b"WS-QCRYPTO-AUTH-BINDING-V1\x00"
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$")
U32_MAX = (1 << 32) - 1
U64_MAX = (1 << 64) - 1


@dataclass(frozen=True)
class AuthoritySigningIntent:
    network_id: str
    domain_separator: str
    payload_digest: str
    authority_id: str
    authority_layer: AuthorityLayer
    declared_requirement: MigrationRequirement
    envelope_version: int
    key_epoch: int
    classical_algorithm_id: str | None
    pq_algorithm_id: str | None
    classical_required_for_acceptance: bool
    pq_required_for_acceptance: bool
    recovery_evidence_present: bool = False
    execution_authority: bool = False
    live_value_authorized: bool = False


@dataclass(frozen=True)
class CanonicalSigningContextRequest:
    intent: AuthoritySigningIntent
    authority_policy: AuthorityPolicy
    adapter: CanonicalAuthorityEnvelope
    policy_version: int
    replay_domain: str
    replay_sequence: int
    evidence_digest: str
    recovery_commitment_digest: str | None = None


@dataclass(frozen=True)
class CanonicalSigningContextDecision:
    verdict: str
    ready: bool
    blockers: tuple[str, ...]
    context_schema: str
    context_digest: str | None
    canonical_preimage_hex: str | None
    canonical_fields: dict[str, str]
    pre_sign_intent_only: bool = True
    signature_presence_assumed: bool = False
    execution_authority: bool = False
    live_value_authorized: bool = False
    transaction_signed: bool = False
    claim_boundary: str = (
        "Deterministic pre-sign message-binding result only; no signature is assumed to "
        "exist at this stage. This does not authorize a transaction, move value, "
        "establish protocol conformance, or establish end-to-end post-quantum security."
    )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["blockers"] = list(self.blockers)
        return data


def _normalize_identifier(name: str, value: str) -> tuple[str | None, str | None]:
    normalized = unicodedata.normalize("NFC", value)
    if normalized != value:
        return None, f"{name} must already be NFC-normalized."
    if not _SAFE_ID.fullmatch(value):
        return None, f"{name} contains unsupported characters or length."
    return value, None


def _validate_digest(name: str, value: str | None, *, required: bool) -> str | None:
    if value is None:
        return f"{name} is required." if required else None
    if len(value) != 64:
        return f"{name} must be a 64-character hexadecimal SHA-256 digest."
    try:
        int(value, 16)
    except ValueError:
        return f"{name} must be hexadecimal SHA-256 text."
    if value.lower() != value:
        return f"{name} must use lowercase hexadecimal canonical form."
    return None


def _validate_uint(name: str, value: int, *, minimum: int, maximum: int) -> str | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return f"{name} must be an integer."
    if value < minimum or value > maximum:
        return f"{name} must be in the inclusive range {minimum}..{maximum}."
    return None


def _role_for_layer(layer: AuthorityLayer) -> CryptoRole:
    if layer is AuthorityLayer.CONSENSUS_VALIDATOR:
        return CryptoRole.CONSENSUS_AUTH
    return CryptoRole.DIGITAL_SIGNATURE


def _validate_signing_intent(
    intent: AuthoritySigningIntent,
    policy: AuthorityPolicy,
) -> tuple[list[str], MigrationRequirement]:
    """Validate pre-sign policy/algorithm intent without pretending signatures exist."""

    validate_registry()
    blockers: list[str] = []

    if intent.execution_authority:
        blockers.append("Signing intent cannot self-assert execution authority.")
    if intent.live_value_authorized:
        blockers.append("Signing intent cannot self-assert live-value authorization.")
    if not intent.network_id or intent.network_id != policy.network_id:
        blockers.append("Network id does not match the governed policy scope.")
    if not intent.domain_separator or intent.domain_separator != policy.domain_separator:
        blockers.append("Domain separator does not match the governed policy scope.")
    if not intent.authority_id:
        blockers.append("Authority id is required.")
    if intent.envelope_version < policy.minimum_envelope_version:
        blockers.append("Envelope version rollback rejected.")
    if intent.key_epoch < policy.minimum_key_epoch:
        blockers.append("Key epoch rollback rejected.")
    if intent.declared_requirement < policy.minimum_requirement:
        blockers.append("Migration-policy downgrade rejected.")

    role = _role_for_layer(intent.authority_layer)
    classical = REGISTRY.get(intent.classical_algorithm_id) if intent.classical_algorithm_id else None
    pq = REGISTRY.get(intent.pq_algorithm_id) if intent.pq_algorithm_id else None

    if intent.classical_algorithm_id:
        if classical is None:
            blockers.append("Classical algorithm is not present in the controlled registry.")
        elif classical.pq_resistant:
            blockers.append("Algorithm confusion: PQ algorithm was placed in the classical slot.")
        elif role not in classical.roles:
            blockers.append(f"Classical algorithm is not registered for role {role.value}.")
    elif intent.classical_required_for_acceptance:
        blockers.append("Classical acceptance is required but no classical algorithm is configured.")

    if intent.pq_algorithm_id:
        if pq is None:
            blockers.append("PQ algorithm is not present in the controlled registry.")
        elif not pq.pq_resistant:
            blockers.append("Algorithm confusion: classical algorithm was placed in the PQ slot.")
        elif role not in pq.roles:
            blockers.append(f"PQ algorithm is not registered for role {role.value}.")
        elif pq.standardization_state is not StandardizationState.FINAL_FIPS:
            blockers.append("PQ algorithm does not have finalized-FIPS status in the controlled registry.")
    elif intent.pq_required_for_acceptance:
        blockers.append("PQ acceptance is required but no PQ algorithm is configured.")

    effective = MigrationRequirement(
        max(int(intent.declared_requirement), int(policy.minimum_requirement))
    )
    if effective is MigrationRequirement.CLASSICAL_ALLOWED:
        if not (intent.classical_algorithm_id or intent.pq_algorithm_id):
            blockers.append("At least one governed signing algorithm must be configured.")
    elif effective is MigrationRequirement.HYBRID_REQUIRED:
        if not intent.classical_algorithm_id or not intent.pq_algorithm_id:
            blockers.append("Hybrid signing intent requires classical and PQ algorithm slots.")
        if not intent.classical_required_for_acceptance or not intent.pq_required_for_acceptance:
            blockers.append("Hybrid signing intent requires both signature classes for acceptance.")
    elif effective is MigrationRequirement.PQ_REQUIRED:
        if not intent.pq_algorithm_id or not intent.pq_required_for_acceptance:
            blockers.append("PQ-required signing intent requires a PQ algorithm for acceptance.")
        if intent.classical_required_for_acceptance:
            blockers.append("PQ-required signing intent rejects continued classical acceptance dependency.")

    high_concentration = intent.authority_layer in {
        AuthorityLayer.BRIDGE_CUSTODY,
        AuthorityLayer.GOVERNANCE_ADMIN,
    }
    if (policy.require_recovery_evidence or high_concentration) and not intent.recovery_evidence_present:
        blockers.append("Recovery evidence is required for this authority surface.")

    return blockers, effective


def _frame_text(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return struct.pack(">I", len(encoded)) + encoded


def _canonical_preimage(fields: tuple[tuple[str, str], ...]) -> bytes:
    framed = bytearray(DOMAIN_TAG)
    framed.extend(struct.pack(">H", len(fields)))
    for name, value in fields:
        framed.extend(_frame_text(name))
        framed.extend(_frame_text(value))
    return bytes(framed)


def build_canonical_signing_context(
    request: CanonicalSigningContextRequest,
) -> CanonicalSigningContextDecision:
    """Build a deterministic pre-sign context after intent/policy controls pass."""

    blockers, effective_requirement = _validate_signing_intent(
        request.intent,
        request.authority_policy,
    )
    intent = request.intent
    adapter = request.adapter

    if not adapter.stable_authority_id:
        blockers.append("Canonical adapter requires a stable authority identifier.")
    if not adapter.authenticator_versioned or not adapter.authenticator_replaceable:
        blockers.append("Canonical adapter requires versioned, replaceable authentication.")
    if not adapter.policy_versioned:
        blockers.append("Canonical adapter requires versioned policy.")
    if not adapter.chain_binding_present:
        blockers.append("Canonical adapter requires chain binding.")
    if not adapter.replay_domain_present:
        blockers.append("Canonical adapter requires replay-domain binding.")
    if not adapter.evidence_binding_present:
        blockers.append("Canonical adapter requires evidence binding.")
    if not adapter.recovery_commitment_present:
        blockers.append("Canonical adapter requires a recovery commitment.")
    if not adapter.explicit_human_approval_required:
        blockers.append("Canonical adapter must preserve explicit human approval.")

    for name, value, minimum, maximum in (
        ("envelope_version", intent.envelope_version, 1, U32_MAX),
        ("policy_minimum_envelope_version", request.authority_policy.minimum_envelope_version, 1, U32_MAX),
        ("policy_version", request.policy_version, 1, U32_MAX),
        ("key_epoch", intent.key_epoch, 0, U64_MAX),
        ("policy_minimum_key_epoch", request.authority_policy.minimum_key_epoch, 0, U64_MAX),
        ("replay_sequence", request.replay_sequence, 0, U64_MAX),
    ):
        error = _validate_uint(name, value, minimum=minimum, maximum=maximum)
        if error:
            blockers.append(error)

    identifiers = {
        "network_id": intent.network_id,
        "authority_domain_separator": intent.domain_separator,
        "chain": adapter.chain,
        "adapter_class": adapter.adapter_class,
        "authority_id": intent.authority_id,
        "authority_layer": intent.authority_layer.value,
        "replay_domain": request.replay_domain,
    }
    normalized: dict[str, str] = {}
    for name, value in identifiers.items():
        item, error = _normalize_identifier(name, value)
        if error:
            blockers.append(error)
        elif item is not None:
            normalized[name] = item

    for name, value, required in (
        ("payload_digest", intent.payload_digest, True),
        ("evidence_digest", request.evidence_digest, True),
        ("recovery_commitment_digest", request.recovery_commitment_digest, True),
    ):
        error = _validate_digest(name, value, required=required)
        if error:
            blockers.append(error)

    classical = intent.classical_algorithm_id or "NONE"
    pq = intent.pq_algorithm_id or "NONE"
    for name, value in (("classical_algorithm_id", classical), ("pq_algorithm_id", pq)):
        _, error = _normalize_identifier(name, value)
        if error:
            blockers.append(error)

    if blockers:
        return CanonicalSigningContextDecision(
            verdict="CANONICAL_SIGNING_CONTEXT_BLOCKED",
            ready=False,
            blockers=tuple(blockers),
            context_schema=CONTEXT_SCHEMA,
            context_digest=None,
            canonical_preimage_hex=None,
            canonical_fields={},
        )

    fields: tuple[tuple[str, str], ...] = (
        ("schema", CONTEXT_SCHEMA),
        ("network_id", normalized["network_id"]),
        ("authority_domain_separator", normalized["authority_domain_separator"]),
        ("chain", normalized["chain"]),
        ("adapter_class", normalized["adapter_class"]),
        ("authority_id", normalized["authority_id"]),
        ("authority_layer", normalized["authority_layer"]),
        ("declared_migration_requirement", intent.declared_requirement.name),
        ("policy_minimum_requirement", request.authority_policy.minimum_requirement.name),
        ("effective_migration_requirement", effective_requirement.name),
        ("envelope_version", str(intent.envelope_version)),
        ("policy_minimum_envelope_version", str(request.authority_policy.minimum_envelope_version)),
        ("key_epoch", str(intent.key_epoch)),
        ("policy_minimum_key_epoch", str(request.authority_policy.minimum_key_epoch)),
        ("policy_version", str(request.policy_version)),
        ("policy_requires_recovery_evidence", "1" if request.authority_policy.require_recovery_evidence else "0"),
        ("classical_algorithm_id", classical),
        ("pq_algorithm_id", pq),
        ("classical_required_for_acceptance", "1" if intent.classical_required_for_acceptance else "0"),
        ("pq_required_for_acceptance", "1" if intent.pq_required_for_acceptance else "0"),
        ("replay_domain", normalized["replay_domain"]),
        ("replay_sequence", str(request.replay_sequence)),
        ("payload_digest", intent.payload_digest),
        ("evidence_digest", request.evidence_digest),
        ("recovery_commitment_digest", request.recovery_commitment_digest or ""),
    )
    preimage = _canonical_preimage(fields)
    digest = hashlib.sha256(preimage).hexdigest()

    return CanonicalSigningContextDecision(
        verdict="CANONICAL_SIGNING_CONTEXT_READY",
        ready=True,
        blockers=(),
        context_schema=CONTEXT_SCHEMA,
        context_digest=digest,
        canonical_preimage_hex=preimage.hex(),
        canonical_fields=dict(fields),
    )
