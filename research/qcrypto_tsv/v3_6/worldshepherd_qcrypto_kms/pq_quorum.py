"""Provider-diverse post-quantum release authorization.

This module promotes PQ experimentation into an enforceable application-layer
quorum.  It supports independent algorithm families (for example ML-DSA plus
SLH-DSA) without pretending either is a Bitcoin consensus signature.
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from typing import Callable, Mapping, Protocol, Sequence

from .crypto_agility import (
    AlgorithmFamily,
    CryptoAgilityPolicy,
    algorithm_spec,
    evaluate_algorithm_set,
    normalize_algorithm_id,
)
from .key_lifecycle import KeyLifecycleError, KeyRegistry
from .release_policy import BitcoinReleaseIntent, RELEASE_ATTESTATION_CONTEXT


class PqQuorumError(RuntimeError):
    pass


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    try:
        raw = text.encode("ascii")
        return base64.b64decode(raw + b"=" * (-len(raw) % 4), altchars=b"-_", validate=True)
    except Exception as exc:
        raise PqQuorumError("invalid base64url PQ signature") from exc


def _hex32(name: str, value: str) -> str:
    value = value.lower()
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise PqQuorumError(f"{name} must be 32-byte hex")
    return value


@dataclass(frozen=True)
class PqProviderAttestation:
    intent_sha256: str
    provider_id: str
    algorithm_id: str
    key_fingerprint_sha256: str
    signature_b64url: str
    operation_id: str
    fault_domain_id: str = ""

    def to_dict(self) -> dict:
        out = asdict(self)
        out["algorithm_id"] = normalize_algorithm_id(self.algorithm_id)
        return out


@dataclass(frozen=True)
class LatencyBudget:
    max_sign_ms_per_provider: float = 20_000.0
    max_verify_ms_per_provider: float = 20_000.0
    max_total_ms: float = 60_000.0

    def validate(self) -> None:
        for name, value in asdict(self).items():
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                raise PqQuorumError(f"{name} must be positive")


@dataclass(frozen=True)
class ProviderTiming:
    provider_id: str
    algorithm_id: str
    sign_ms: float
    verify_ms: float
    within_budget: bool

    def to_dict(self) -> dict:
        return asdict(self)


class PqAuthorizationProvider(Protocol):
    @property
    def provider_id(self) -> str: ...
    @property
    def algorithm_id(self) -> str: ...
    @property
    def key_fingerprint_sha256(self) -> str: ...
    @property
    def fault_domain_id(self) -> str: ...
    def sign_release_intent(self, *, intent: BitcoinReleaseIntent, context: bytes) -> PqProviderAttestation: ...
    def verify_release_intent(self, *, intent: BitcoinReleaseIntent, context: bytes, signature: bytes) -> bool: ...


class CallablePqProviderAdapter:
    """Strict adapter for an externally supplied ML-DSA/SLH-DSA provider.

    The callbacks must perform the real cryptographic operation.  QCRYPTO does not
    substitute a mock signature when a primitive is unavailable.
    """

    def __init__(
        self,
        *,
        provider_id: str,
        algorithm_id: str,
        key_fingerprint_sha256: str,
        signer: Callable[[bytes, bytes], tuple[bytes, str]],
        verifier: Callable[[bytes, bytes, bytes], bool],
        fault_domain_id: str | None = None,
    ) -> None:
        if not provider_id or len(provider_id) > 128:
            raise PqQuorumError("provider_id is required")
        self._provider_id = provider_id
        self._algorithm_id = normalize_algorithm_id(algorithm_id)
        self._key_fingerprint = _hex32("key_fingerprint_sha256", key_fingerprint_sha256)
        self._signer = signer
        self._verifier = verifier
        self._fault_domain_id = (fault_domain_id or provider_id).strip()
        if not self._fault_domain_id or len(self._fault_domain_id) > 128:
            raise PqQuorumError("fault_domain_id is invalid")

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def algorithm_id(self) -> str:
        return self._algorithm_id

    @property
    def key_fingerprint_sha256(self) -> str:
        return self._key_fingerprint

    @property
    def fault_domain_id(self) -> str:
        return self._fault_domain_id

    def sign_release_intent(self, *, intent: BitcoinReleaseIntent, context: bytes) -> PqProviderAttestation:
        signature, operation_id = self._signer(intent.canonical_bytes(), context)
        if not isinstance(signature, (bytes, bytearray)) or not signature:
            raise PqQuorumError("external PQ provider returned no signature")
        if not isinstance(operation_id, str) or not operation_id:
            raise PqQuorumError("external PQ provider returned no operation ID")
        return PqProviderAttestation(
            intent_sha256=intent.intent_sha256, provider_id=self.provider_id, algorithm_id=self.algorithm_id,
            key_fingerprint_sha256=self.key_fingerprint_sha256, signature_b64url=_b64u(bytes(signature)), operation_id=operation_id,
            fault_domain_id=self.fault_domain_id,
        )

    def verify_release_intent(self, *, intent: BitcoinReleaseIntent, context: bytes, signature: bytes) -> bool:
        return bool(self._verifier(intent.canonical_bytes(), context, signature))


class AwsKmsMlDsa65Adapter:
    """Adapter for the existing one-shot AWS KMS ML-DSA-65 provider."""

    def __init__(self, provider: object, *, provider_id: str = "AWS_KMS_ML_DSA_65") -> None:
        self._provider = provider
        self._provider_id = provider_id

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def algorithm_id(self) -> str:
        return "ML-DSA-65"

    @property
    def key_fingerprint_sha256(self) -> str:
        return str(self._provider.descriptor.public_key_der_sha256)

    @property
    def fault_domain_id(self) -> str:
        arn = str(self._provider.descriptor.key_arn).split(":")
        if len(arn) >= 5:
            return f"AWS_KMS:{arn[3]}:{arn[4]}"
        return "AWS_KMS:UNKNOWN"

    def sign_release_intent(self, *, intent: BitcoinReleaseIntent, context: bytes) -> PqProviderAttestation:
        from .aws_kms_provider import ProviderState, provider_operation_id
        message = intent.canonical_bytes()
        key_arn = self._provider.descriptor.key_arn
        operation_id = provider_operation_id(key_arn=key_arn, message=message, context=context)
        result = self._provider.begin_sign(operation_id, message, context)
        if result.state != ProviderState.SIGNED or not result.signature_b64url:
            raise PqQuorumError("AWS KMS provider did not return a signed result")
        if result.message_sha256 != hashlib.sha256(message).hexdigest() or result.context_sha256 != hashlib.sha256(context).hexdigest():
            raise PqQuorumError("AWS KMS result is not bound to the requested release intent/context")
        return PqProviderAttestation(
            intent_sha256=intent.intent_sha256,
            provider_id=self.provider_id,
            algorithm_id=self.algorithm_id,
            key_fingerprint_sha256=self.key_fingerprint_sha256,
            signature_b64url=result.signature_b64url,
            operation_id=result.operation_id,
            fault_domain_id=self.fault_domain_id,
        )

    def verify_release_intent(self, *, intent: BitcoinReleaseIntent, context: bytes, signature: bytes) -> bool:
        return bool(self._provider.verify_with_kms(message=intent.canonical_bytes(), context=context, signature=signature))


def verify_pq_quorum(
    *,
    intent: BitcoinReleaseIntent,
    attestations: Sequence[PqProviderAttestation],
    verifiers: Mapping[tuple[str, str], Callable[[bytes, bytes, bytes], bool]],
    policy: CryptoAgilityPolicy,
    key_registry: KeyRegistry | None = None,
    runtime_attestation_reports: Mapping[str, Mapping] | None = None,
    require_runtime_attestation: bool = False,
) -> dict:
    if not attestations and policy.minimum_pq_attestations:
        raise PqQuorumError("PQ provider quorum is empty")
    provider_ids: set[str] = set()
    key_fps: set[str] = set()
    op_ids: set[str] = set()
    algorithms: list[str] = []
    fault_domains: set[str] = set()
    verified_rows: list[dict] = []
    runtime_reports = runtime_attestation_reports or {}
    message = intent.canonical_bytes()
    for att in attestations:
        if _hex32("intent_sha256", att.intent_sha256) != intent.intent_sha256:
            raise PqQuorumError("PQ provider attestation is bound to a different release intent")
        if not att.provider_id or len(att.provider_id) > 128:
            raise PqQuorumError("invalid provider_id")
        fp = _hex32("key_fingerprint_sha256", att.key_fingerprint_sha256)
        alg = normalize_algorithm_id(att.algorithm_id)
        fault_domain = (att.fault_domain_id or att.provider_id).strip()
        if not fault_domain or len(fault_domain) > 128:
            raise PqQuorumError("invalid provider fault_domain_id")
        if att.provider_id in provider_ids:
            raise PqQuorumError("one provider cannot satisfy the PQ quorum twice")
        if fp in key_fps:
            raise PqQuorumError("one PQ key cannot satisfy the quorum twice")
        if not att.operation_id or att.operation_id in op_ids:
            raise PqQuorumError("missing or replayed provider operation ID")
        verifier = verifiers.get((att.provider_id, fp))
        if verifier is None:
            raise PqQuorumError("no trusted verifier is registered for provider/key")
        signature = _unb64(att.signature_b64url)
        expected_signature_bytes = algorithm_spec(alg).signature_bytes
        if len(signature) != expected_signature_bytes:
            raise PqQuorumError(f"{alg} signature length {len(signature)} does not match standard size {expected_signature_bytes}")
        try:
            ok = bool(verifier(message, RELEASE_ATTESTATION_CONTEXT, signature))
        except Exception as exc:
            raise PqQuorumError("PQ verifier raised an exception") from exc
        if not ok:
            raise PqQuorumError("PQ provider signature verification failed")
        key_report = None
        if key_registry is not None:
            try:
                key_report = key_registry.authorize_key(provider_id=att.provider_id, fingerprint_sha256=fp, algorithm_id=alg)
            except KeyLifecycleError as exc:
                raise PqQuorumError(str(exc)) from exc
        runtime_report = runtime_reports.get(att.provider_id)
        if require_runtime_attestation:
            if not runtime_report or runtime_report.get("verified") is not True:
                raise PqQuorumError("verified runtime/TEE attestation is required for every PQ provider")
            if runtime_report.get("key_fingerprint_sha256", "").lower() != fp:
                raise PqQuorumError("runtime attestation key does not match PQ provider key")
        provider_ids.add(att.provider_id)
        key_fps.add(fp)
        op_ids.add(att.operation_id)
        algorithms.append(alg)
        fault_domains.add(fault_domain)
        verified_rows.append({
            "provider_id": att.provider_id,
            "fault_domain_id": fault_domain,
            "algorithm_id": alg,
            "family": ("LATTICE" if alg.startswith("ML-DSA") else "HASH_BASED" if alg.startswith("SLH-DSA") else "UNKNOWN"),
            "key_fingerprint_sha256": fp,
            "operation_id": att.operation_id,
            "signature_sha256": hashlib.sha256(signature).hexdigest(),
            "signature_bytes": len(signature),
            "key_lifecycle": key_report,
            "runtime_attestation": dict(runtime_report) if runtime_report else None,
            "verified": True,
        })
    agility = evaluate_algorithm_set(algorithms, policy)
    if len(fault_domains) < policy.minimum_provider_fault_domains:
        raise PqQuorumError(
            f"PQ quorum spans {len(fault_domains)} provider fault domain(s); policy requires {policy.minimum_provider_fault_domains}"
        )
    if not agility.satisfied:
        raise PqQuorumError("PQ algorithm quorum violates cryptographic-agility policy")
    report_body = {
        "schema": "WS-QCRYPTO-PQ-PROVIDER-QUORUM-V1",
        "intent_sha256": intent.intent_sha256,
        "providers": verified_rows,
        "algorithm_agility": agility.to_dict(),
        "verified_count": len(verified_rows),
        "fault_domains": sorted(fault_domains),
        "fault_domain_count": len(fault_domains),
        "satisfied": True,
    }
    report_body["quorum_sha256"] = hashlib.sha256(json.dumps(report_body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return report_body


def execute_and_verify_pq_quorum(
    *,
    intent: BitcoinReleaseIntent,
    providers: Sequence[PqAuthorizationProvider],
    policy: CryptoAgilityPolicy,
    latency_budget: LatencyBudget = LatencyBudget(),
    key_registry: KeyRegistry | None = None,
    runtime_attestation_reports: Mapping[str, Mapping] | None = None,
    require_runtime_attestation: bool = False,
) -> tuple[tuple[PqProviderAttestation, ...], dict, tuple[ProviderTiming, ...]]:
    """Execute a bounded M-of-N provider authorization and enforce latency.

    Every configured provider is attempted at most once and never retried by this
    function.  Provider-specific durable anti-retry semantics still apply.  If an
    attempted provider fails or returns an ambiguous outcome, QCRYPTO may continue
    with a *different* provider only when the remaining independently verified
    providers can still satisfy the configured algorithm-family/count policy.
    """
    latency_budget.validate()
    if len({p.provider_id for p in providers}) != len(providers):
        raise PqQuorumError("provider_id must be unique before signing")
    preflight = evaluate_algorithm_set([p.algorithm_id for p in providers], policy)
    if not preflight.satisfied:
        raise PqQuorumError("configured provider set cannot satisfy crypto-agility policy")
    start_all = time.monotonic_ns()
    attestations: list[PqProviderAttestation] = []
    verifiers: dict[tuple[str, str], Callable[[bytes, bytes, bytes], bool]] = {}
    timings: list[ProviderTiming] = []
    failures: list[dict] = []
    for provider in providers:
        sign_ms = 0.0
        verify_ms = 0.0
        try:
            t0 = time.monotonic_ns()
            att = provider.sign_release_intent(intent=intent, context=RELEASE_ATTESTATION_CONTEXT)
            sign_ms = (time.monotonic_ns() - t0) / 1_000_000
            if sign_ms > latency_budget.max_sign_ms_per_provider:
                raise PqQuorumError(f"provider {provider.provider_id} exceeded signing latency budget")
            signature = _unb64(att.signature_b64url)
            expected_size = algorithm_spec(provider.algorithm_id).signature_bytes
            if len(signature) != expected_size:
                raise PqQuorumError(
                    f"provider {provider.provider_id} returned {len(signature)} signature bytes; expected {expected_size}"
                )
            t1 = time.monotonic_ns()
            verify_ok = bool(provider.verify_release_intent(intent=intent, context=RELEASE_ATTESTATION_CONTEXT, signature=signature))
            verify_ms = (time.monotonic_ns() - t1) / 1_000_000
            if verify_ms > latency_budget.max_verify_ms_per_provider:
                raise PqQuorumError(f"provider {provider.provider_id} exceeded verification latency budget")
            if not verify_ok:
                raise PqQuorumError(f"provider {provider.provider_id} failed immediate signature verification")
            timings.append(ProviderTiming(provider.provider_id, normalize_algorithm_id(provider.algorithm_id), sign_ms, verify_ms, True))
            attestations.append(att)
            verifiers[(provider.provider_id, provider.key_fingerprint_sha256.lower())] = (
                lambda m, c, sig, p=provider: p.verify_release_intent(intent=intent, context=c, signature=sig) and m == intent.canonical_bytes()
            )
            partial = evaluate_algorithm_set([a.algorithm_id for a in attestations], policy)
            if partial.satisfied:
                break
        except Exception as exc:
            timings.append(ProviderTiming(provider.provider_id, normalize_algorithm_id(provider.algorithm_id), sign_ms, verify_ms, False))
            failures.append({
                "provider_id": provider.provider_id,
                "algorithm_id": normalize_algorithm_id(provider.algorithm_id),
                "failure_type": type(exc).__name__,
                "message_sha256": hashlib.sha256(str(exc).encode()).hexdigest(),
            })
            # Continue only with a different provider; this function never retries p.
            continue
    total_ms = (time.monotonic_ns() - start_all) / 1_000_000
    if total_ms > latency_budget.max_total_ms:
        raise PqQuorumError("aggregate PQ authorization exceeded total latency budget")
    if not evaluate_algorithm_set([a.algorithm_id for a in attestations], policy).satisfied:
        raise PqQuorumError(
            f"PQ provider threshold/family policy was not satisfied after {len(providers)} bounded provider attempts"
        )
    report = verify_pq_quorum(
        intent=intent,
        attestations=attestations,
        verifiers=verifiers,
        policy=policy,
        key_registry=key_registry,
        runtime_attestation_reports=runtime_attestation_reports,
        require_runtime_attestation=require_runtime_attestation,
    )
    report["latency"] = {
        "total_ms": total_ms,
        "budget": asdict(latency_budget),
        "providers": [t.to_dict() for t in timings],
        "satisfied": True,
    }
    report["provider_failures"] = failures
    report["configured_provider_count"] = len(providers)
    report["attempted_provider_count"] = len(timings)
    report["threshold_failover_used"] = bool(failures)
    return tuple(attestations), report, tuple(timings)
