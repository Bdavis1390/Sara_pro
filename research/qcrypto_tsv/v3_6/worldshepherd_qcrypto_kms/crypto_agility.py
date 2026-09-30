"""Cryptographic-agility and downgrade-resistance policy for QCRYPTO.

This module does not implement post-quantum primitives itself.  It enforces which
standards/parameter sets a signing workflow may rely on, their expected wire sizes,
algorithm-family diversity, and lifecycle state.  Cryptographic operations are
performed by independently configured providers and verified by provider-specific
verifiers.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable, Mapping, Sequence


class CryptoAgilityError(RuntimeError):
    pass


class AlgorithmFamily(str, Enum):
    CLASSICAL_ECC = "CLASSICAL_ECC"
    LATTICE = "LATTICE"
    HASH_BASED = "HASH_BASED"


class AlgorithmState(str, Enum):
    APPROVED = "APPROVED"
    DEPRECATED = "DEPRECATED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class AlgorithmSpec:
    algorithm_id: str
    family: AlgorithmFamily
    standard: str
    security_category: int
    signature_bytes: int
    public_key_bytes: int | None
    state: AlgorithmState = AlgorithmState.APPROVED
    detached_authorization_only: bool = True

    def to_dict(self) -> dict:
        out = asdict(self)
        out["family"] = self.family.value
        out["state"] = self.state.value
        return out


# Final NIST FIPS 204/205 parameter sizes.  These entries are policy metadata; the
# module never pretends that a primitive is available merely because it is listed.
_STANDARD_ALGORITHMS: dict[str, AlgorithmSpec] = {
    "ML-DSA-44": AlgorithmSpec("ML-DSA-44", AlgorithmFamily.LATTICE, "FIPS 204", 2, 2420, 1312),
    "ML-DSA-65": AlgorithmSpec("ML-DSA-65", AlgorithmFamily.LATTICE, "FIPS 204", 3, 3309, 1952),
    "ML-DSA-87": AlgorithmSpec("ML-DSA-87", AlgorithmFamily.LATTICE, "FIPS 204", 5, 4627, 2592),
    "SLH-DSA-SHA2-128s": AlgorithmSpec("SLH-DSA-SHA2-128s", AlgorithmFamily.HASH_BASED, "FIPS 205", 1, 7856, 32),
    "SLH-DSA-SHAKE-128s": AlgorithmSpec("SLH-DSA-SHAKE-128s", AlgorithmFamily.HASH_BASED, "FIPS 205", 1, 7856, 32),
    "SLH-DSA-SHA2-128f": AlgorithmSpec("SLH-DSA-SHA2-128f", AlgorithmFamily.HASH_BASED, "FIPS 205", 1, 17088, 32),
    "SLH-DSA-SHAKE-128f": AlgorithmSpec("SLH-DSA-SHAKE-128f", AlgorithmFamily.HASH_BASED, "FIPS 205", 1, 17088, 32),
    "SLH-DSA-SHA2-192s": AlgorithmSpec("SLH-DSA-SHA2-192s", AlgorithmFamily.HASH_BASED, "FIPS 205", 3, 16224, 48),
    "SLH-DSA-SHAKE-192s": AlgorithmSpec("SLH-DSA-SHAKE-192s", AlgorithmFamily.HASH_BASED, "FIPS 205", 3, 16224, 48),
    "SLH-DSA-SHA2-256s": AlgorithmSpec("SLH-DSA-SHA2-256s", AlgorithmFamily.HASH_BASED, "FIPS 205", 5, 29792, 64),
    "SLH-DSA-SHAKE-256s": AlgorithmSpec("SLH-DSA-SHAKE-256s", AlgorithmFamily.HASH_BASED, "FIPS 205", 5, 29792, 64),
    # Governance signatures only; not post-quantum and never a substitute for PQ.
    "ED25519": AlgorithmSpec("ED25519", AlgorithmFamily.CLASSICAL_ECC, "FIPS 186-5/RFC 8032", 1, 64, 32, detached_authorization_only=True),
    # Bitcoin consensus signatures remain classical until a future activated PQ path.
    "SECP256K1-ECDSA": AlgorithmSpec("SECP256K1-ECDSA", AlgorithmFamily.CLASSICAL_ECC, "Bitcoin consensus", 1, 73, 33, detached_authorization_only=False),
    "SECP256K1-SCHNORR": AlgorithmSpec("SECP256K1-SCHNORR", AlgorithmFamily.CLASSICAL_ECC, "BIP 340", 1, 64, 32, detached_authorization_only=False),
}


def normalize_algorithm_id(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CryptoAgilityError("algorithm identifier is required")
    text = value.strip().replace("_", "-")
    aliases = {
        "ML-DSA-44": "ML-DSA-44",
        "ML-DSA-65": "ML-DSA-65",
        "ML-DSA-87": "ML-DSA-87",
        "ML-DSA-SHAKE-256/44": "ML-DSA-44",
        "ML-DSA-SHAKE-256/65": "ML-DSA-65",
        "ML-DSA-SHAKE-256/87": "ML-DSA-87",
        "ED25519": "ED25519",
        "SECP256K1-ECDSA": "SECP256K1-ECDSA",
        "SECP256K1-SCHNORR": "SECP256K1-SCHNORR",
    }
    upper = text.upper()
    if upper in aliases:
        return aliases[upper]
    # Preserve the mixed-case suffix used by the FIPS 205 names in the registry.
    for known in _STANDARD_ALGORITHMS:
        if known.upper() == upper:
            return known
    raise CryptoAgilityError(f"algorithm {value!r} is not in the QCRYPTO standards registry")


def algorithm_spec(algorithm_id: str) -> AlgorithmSpec:
    return _STANDARD_ALGORITHMS[normalize_algorithm_id(algorithm_id)]


@dataclass(frozen=True)
class CryptoAgilityPolicy:
    minimum_security_category: int = 1
    minimum_pq_attestations: int = 1
    required_pq_families: tuple[AlgorithmFamily, ...] = (AlgorithmFamily.LATTICE,)
    required_algorithms: tuple[str, ...] = ()
    blocked_algorithms: tuple[str, ...] = ()
    allow_deprecated: bool = False
    max_detached_signature_bytes: int = 65536
    minimum_provider_fault_domains: int = 1

    def canonical_dict(self) -> dict:
        if not 1 <= self.minimum_security_category <= 5:
            raise CryptoAgilityError("minimum_security_category must be 1..5")
        if self.minimum_pq_attestations < 0:
            raise CryptoAgilityError("minimum_pq_attestations must be non-negative")
        if self.max_detached_signature_bytes <= 0:
            raise CryptoAgilityError("max_detached_signature_bytes must be positive")
        if self.minimum_provider_fault_domains < 0:
            raise CryptoAgilityError("minimum_provider_fault_domains must be non-negative")
        return {
            "minimum_security_category": self.minimum_security_category,
            "minimum_pq_attestations": self.minimum_pq_attestations,
            "required_pq_families": sorted(f.value for f in self.required_pq_families),
            "required_algorithms": sorted(normalize_algorithm_id(a) for a in self.required_algorithms),
            "blocked_algorithms": sorted(normalize_algorithm_id(a) for a in self.blocked_algorithms),
            "allow_deprecated": bool(self.allow_deprecated),
            "max_detached_signature_bytes": self.max_detached_signature_bytes,
            "minimum_provider_fault_domains": self.minimum_provider_fault_domains,
        }

    @property
    def policy_sha256(self) -> str:
        body = json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(b"WS-QCRYPTO-CRYPTO-AGILITY-POLICY-V1\x00" + body).hexdigest()


@dataclass(frozen=True)
class CryptoAgilityReport:
    selected_algorithms: tuple[str, ...]
    pq_algorithms: tuple[str, ...]
    pq_families: tuple[str, ...]
    detached_signature_bytes: int
    missing_families: tuple[str, ...]
    missing_algorithms: tuple[str, ...]
    blocked_selected: tuple[str, ...]
    below_security_floor: tuple[str, ...]
    satisfied: bool
    policy_sha256: str

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_algorithm_set(
    selected_algorithms: Sequence[str],
    policy: CryptoAgilityPolicy,
    *,
    lifecycle_overrides: Mapping[str, AlgorithmState] | None = None,
) -> CryptoAgilityReport:
    canonical = tuple(normalize_algorithm_id(a) for a in selected_algorithms)
    overrides = {normalize_algorithm_id(k): v for k, v in (lifecycle_overrides or {}).items()}
    blocked_policy = set(policy.canonical_dict()["blocked_algorithms"])
    pq_specs: list[AlgorithmSpec] = []
    blocked: list[str] = []
    below: list[str] = []
    detached_bytes = 0
    for alg in canonical:
        spec = algorithm_spec(alg)
        state = overrides.get(alg, spec.state)
        if alg in blocked_policy or state == AlgorithmState.BLOCKED or (state == AlgorithmState.DEPRECATED and not policy.allow_deprecated):
            blocked.append(alg)
        if spec.family != AlgorithmFamily.CLASSICAL_ECC:
            pq_specs.append(spec)
            detached_bytes += spec.signature_bytes
            if spec.security_category < policy.minimum_security_category:
                below.append(alg)
    required_families = {f.value for f in policy.required_pq_families}
    present_families = {s.family.value for s in pq_specs}
    missing_families = sorted(required_families - present_families)
    required_algs = {normalize_algorithm_id(a) for a in policy.required_algorithms}
    missing_algs = sorted(required_algs - set(canonical))
    satisfied = (
        len(pq_specs) >= policy.minimum_pq_attestations
        and not missing_families
        and not missing_algs
        and not blocked
        and not below
        and detached_bytes <= policy.max_detached_signature_bytes
    )
    return CryptoAgilityReport(
        selected_algorithms=canonical,
        pq_algorithms=tuple(s.algorithm_id for s in pq_specs),
        pq_families=tuple(sorted(present_families)),
        detached_signature_bytes=detached_bytes,
        missing_families=tuple(missing_families),
        missing_algorithms=tuple(missing_algs),
        blocked_selected=tuple(sorted(blocked)),
        below_security_floor=tuple(sorted(below)),
        satisfied=satisfied,
        policy_sha256=policy.policy_sha256,
    )


def build_crypto_bill_of_materials(
    *,
    bitcoin_signature_algorithms: Iterable[str],
    pq_authorization_algorithms: Iterable[str] = (),
    governance_algorithms: Iterable[str] = ("ED25519",),
) -> dict:
    """Return a deterministic cryptographic bill of materials (CBOM).

    The CBOM is an inventory and policy-binding object.  It is not a certification
    and does not infer that any listed provider is FIPS validated.
    """
    ordered = []
    for usage, values in (
        ("BITCOIN_CONSENSUS", bitcoin_signature_algorithms),
        ("PQ_RELEASE_AUTHORIZATION", pq_authorization_algorithms),
        ("GOVERNANCE", governance_algorithms),
    ):
        for value in values:
            spec = algorithm_spec(value)
            ordered.append({"usage": usage, **spec.to_dict()})
    ordered.sort(key=lambda x: (x["usage"], x["algorithm_id"]))
    digest = hashlib.sha256(json.dumps(ordered, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "schema": "WS-QCRYPTO-CBOM-V1",
        "components": ordered,
        "cbom_sha256": digest,
        "certification_claim": "NONE",
    }
