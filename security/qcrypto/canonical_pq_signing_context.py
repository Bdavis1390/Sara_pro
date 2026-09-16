"""Deterministic, fail-closed signing context for defensive PQ migration.

This module does not sign, generate keys, authorize execution, or move value.  It
binds the governance-relevant fields of a cryptocurrency authority action into a
fixed binary framing and SHA-256 context digest.  The digest is suitable for
controlled interoperability tests and later signer integration only after
separate execution approval.

Security goals of the context include preventing silent substitution across
networks, authority roles, algorithm slots, policy versions and floors, key
epochs, replay domains, evidence records, and recovery commitments.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
import struct
import unicodedata

from security.qcrypto.canonical_authority_envelope import CanonicalAuthorityEnvelope
from security.qcrypto.hybrid_authority_migration import (
    AuthorityEnvelope,
    AuthorityPolicy,
    MigrationRequirement,
    assess_authority_envelope,
)


CONTEXT_SCHEMA = "WS-QCRYPTO-CANONICAL-SIGNING-CONTEXT-V1"
DOMAIN_TAG = b"WS-QCRYPTO-AUTH-BINDING-V1\x00"
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$")
U32_MAX = (1 << 32) - 1
U64_MAX = (1 << 64) - 1


@dataclass(frozen=True)
class CanonicalSigningContextRequest:
    authority: AuthorityEnvelope
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
    execution_authority: bool = False
    live_value_authorized: bool = False
    transaction_signed: bool = False
    claim_boundary: str = (
        "Deterministic message-binding result only; this does not create or verify a "
        "signature, authorize a transaction, move value, establish protocol conformance, "
        "or establish end-to-end post-quantum security."
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
    """Build a deterministic context digest after all migration controls pass."""

    blockers: list[str] = []

    authority_decision = assess_authority_envelope(
        request.authority,
        request.authority_policy,
    )
    if not authority_decision.accepted:
        blockers.append(
            "Authority migration envelope is not accepted by the governed migration policy."
        )
        blockers.extend(authority_decision.blockers)

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
        ("envelope_version", request.authority.envelope_version, 1, U32_MAX),
        (
            "policy_minimum_envelope_version",
            request.authority_policy.minimum_envelope_version,
            1,
            U32_MAX,
        ),
        ("policy_version", request.policy_version, 1, U32_MAX),
        ("key_epoch", request.authority.key_epoch, 0, U64_MAX),
        ("policy_minimum_key_epoch", request.authority_policy.minimum_key_epoch, 0, U64_MAX),
        ("replay_sequence", request.replay_sequence, 0, U64_MAX),
    ):
        error = _validate_uint(name, value, minimum=minimum, maximum=maximum)
        if error:
            blockers.append(error)

    identifiers = {
        "network_id": request.authority.network_id,
        "authority_domain_separator": request.authority.domain_separator,
        "chain": adapter.chain,
        "adapter_class": adapter.adapter_class,
        "authority_id": request.authority.authority_id,
        "authority_layer": request.authority.authority_layer.value,
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
        ("payload_digest", request.authority.payload_digest, True),
        ("evidence_digest", request.evidence_digest, True),
        ("recovery_commitment_digest", request.recovery_commitment_digest, True),
    ):
        error = _validate_digest(name, value, required=required)
        if error:
            blockers.append(error)

    classical = request.authority.classical_algorithm_id or "NONE"
    pq = request.authority.pq_algorithm_id or "NONE"
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

    effective_requirement = MigrationRequirement(
        max(
            int(request.authority.declared_requirement),
            int(request.authority_policy.minimum_requirement),
        )
    )

    fields: tuple[tuple[str, str], ...] = (
        ("schema", CONTEXT_SCHEMA),
        ("network_id", normalized["network_id"]),
        ("authority_domain_separator", normalized["authority_domain_separator"]),
        ("chain", normalized["chain"]),
        ("adapter_class", normalized["adapter_class"]),
        ("authority_id", normalized["authority_id"]),
        ("authority_layer", normalized["authority_layer"]),
        ("declared_migration_requirement", request.authority.declared_requirement.name),
        ("policy_minimum_requirement", request.authority_policy.minimum_requirement.name),
        ("effective_migration_requirement", effective_requirement.name),
        ("envelope_version", str(request.authority.envelope_version)),
        ("policy_minimum_envelope_version", str(request.authority_policy.minimum_envelope_version)),
        ("key_epoch", str(request.authority.key_epoch)),
        ("policy_minimum_key_epoch", str(request.authority_policy.minimum_key_epoch)),
        ("policy_version", str(request.policy_version)),
        ("policy_requires_recovery_evidence", "1" if request.authority_policy.require_recovery_evidence else "0"),
        ("classical_algorithm_id", classical),
        ("pq_algorithm_id", pq),
        ("classical_required_for_acceptance", "1" if request.authority.classical_required_for_acceptance else "0"),
        ("pq_required_for_acceptance", "1" if request.authority.pq_required_for_acceptance else "0"),
        ("replay_domain", normalized["replay_domain"]),
        ("replay_sequence", str(request.replay_sequence)),
        ("payload_digest", request.authority.payload_digest),
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
