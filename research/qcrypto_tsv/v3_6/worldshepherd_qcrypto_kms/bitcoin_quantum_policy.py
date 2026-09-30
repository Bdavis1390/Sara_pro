"""Bitcoin quantum-risk inventory and pre-sign policy controls.

This module does not change Bitcoin consensus and does not claim BIP-360 or BIP-361
are active. It gives custody/wallet software enforceable local controls today:
classify long-exposure risk, stop address reuse, block creation of known exposed-key
output types under hardened policy, and generate a migration priority manifest.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable


class BitcoinQuantumPolicyError(RuntimeError):
    pass


class ExposureClass(str, Enum):
    EXPOSED_LONG = "EXPOSED_LONG"
    HIDDEN_UNTIL_SPEND = "HIDDEN_UNTIL_SPEND"
    CONDITIONAL_REUSE_EXPOSURE = "CONDITIONAL_REUSE_EXPOSURE"
    PROPOSED_LONG_EXPOSURE_RESISTANT = "PROPOSED_LONG_EXPOSURE_RESISTANT"
    UNKNOWN = "UNKNOWN"


class CryptoPolicyState(str, Enum):
    ECDSA_ALLOWED = "ECDSA_ALLOWED"
    HYBRID_REQUIRED = "HYBRID_REQUIRED"
    PQ_REQUIRED = "PQ_REQUIRED"
    CLASSICAL_REJECTED = "CLASSICAL_REJECTED"


# Based on BIP-360's current draft classification. These are local policy labels,
# not consensus activation claims.
_ALWAYS_LONG_EXPOSED = {"P2PK", "P2MS", "P2TR"}
_HASH_HIDDEN_UNTIL_SPEND = {"P2PKH", "P2SH", "P2WPKH", "P2WSH"}
_PROPOSED_P2MR = {"P2MR"}


@dataclass(frozen=True)
class UtxoRecord:
    txid: str
    vout: int
    amount_sat: int
    script_type: str
    address_reused: bool = False
    public_key_known_exposed: bool = False
    wallet_label: str = ""
    timelocked: bool = False


@dataclass(frozen=True)
class UtxoAssessment:
    txid: str
    vout: int
    amount_sat: int
    script_type: str
    exposure: ExposureClass
    priority: int
    reasons: tuple[str, ...]
    actions: tuple[str, ...]
    consensus_feature_required: bool

    def to_dict(self) -> dict:
        out = asdict(self)
        out["exposure"] = self.exposure.value
        return out


@dataclass(frozen=True)
class ProposedOutput:
    network: str
    script_type: str
    address_reused: bool = False
    has_pq_recovery_path: bool = False


@dataclass(frozen=True)
class OutputPolicyDecision:
    allowed: bool
    policy_state: CryptoPolicyState
    reasons: tuple[str, ...]
    required_controls: tuple[str, ...]

    def to_dict(self) -> dict:
        out = asdict(self)
        out["policy_state"] = self.policy_state.value
        return out


def _normalized_script_type(value: str) -> str:
    return value.strip().upper().replace("-", "")


def assess_utxo(record: UtxoRecord) -> UtxoAssessment:
    if len(record.txid) != 64 or any(c not in "0123456789abcdefABCDEF" for c in record.txid):
        raise BitcoinQuantumPolicyError("txid must be 32-byte hex")
    if record.vout < 0 or record.amount_sat < 0:
        raise BitcoinQuantumPolicyError("vout and amount_sat must be non-negative")

    script = _normalized_script_type(record.script_type)
    reasons: list[str] = []
    actions: list[str] = []
    consensus_feature_required = False

    if record.public_key_known_exposed:
        exposure = ExposureClass.EXPOSED_LONG
        reasons.append("public key is explicitly recorded as exposed")
    elif script in _ALWAYS_LONG_EXPOSED:
        exposure = ExposureClass.EXPOSED_LONG
        reasons.append(f"{script} exposes elliptic-curve public-key material for long periods")
    elif script in _HASH_HIDDEN_UNTIL_SPEND:
        if record.address_reused:
            exposure = ExposureClass.CONDITIONAL_REUSE_EXPOSURE
            reasons.append("address reuse can leave the controlling public key exposed while value remains")
        else:
            exposure = ExposureClass.HIDDEN_UNTIL_SPEND
            reasons.append("public-key material is normally hidden until spend, leaving short-exposure risk")
    elif script in _PROPOSED_P2MR:
        exposure = ExposureClass.PROPOSED_LONG_EXPOSURE_RESISTANT
        reasons.append("P2MR draft removes the Taproot key-path public-key exposure but is not activated consensus")
        consensus_feature_required = True
    else:
        exposure = ExposureClass.UNKNOWN
        reasons.append("script type is not covered by the local classifier")

    if record.address_reused:
        actions.append("STOP_ADDRESS_REUSE")
    if exposure in {ExposureClass.EXPOSED_LONG, ExposureClass.CONDITIONAL_REUSE_EXPOSURE}:
        actions.extend(("PRIORITIZE_MIGRATION", "PRESERVE_OWNER_RECOVERY_EVIDENCE"))
    if exposure == ExposureClass.HIDDEN_UNTIL_SPEND:
        actions.extend(("AVOID_REUSE", "PREPARE_SHORT_EXPOSURE_MITIGATION"))
    if exposure == ExposureClass.PROPOSED_LONG_EXPOSURE_RESISTANT:
        actions.append("TEST_ONLY_UNTIL_CONSENSUS_ACTIVATION")
    if record.timelocked:
        actions.append("FLAG_TIMELOCK_MIGRATION_CONSTRAINT")

    # Higher number = earlier migration priority. Exposed value dominates; timelocks
    # add urgency because the owner may not be able to migrate freely later.
    base = {
        ExposureClass.EXPOSED_LONG: 100,
        ExposureClass.CONDITIONAL_REUSE_EXPOSURE: 90,
        ExposureClass.HIDDEN_UNTIL_SPEND: 60,
        ExposureClass.PROPOSED_LONG_EXPOSURE_RESISTANT: 20,
        ExposureClass.UNKNOWN: 70,
    }[exposure]
    if record.timelocked:
        base += 10
    if record.amount_sat >= 100_000_000:
        base += 5
    priority = min(base, 115)

    return UtxoAssessment(
        txid=record.txid.lower(),
        vout=record.vout,
        amount_sat=record.amount_sat,
        script_type=script,
        exposure=exposure,
        priority=priority,
        reasons=tuple(reasons),
        actions=tuple(dict.fromkeys(actions)),
        consensus_feature_required=consensus_feature_required,
    )


def build_migration_manifest(records: Iterable[UtxoRecord]) -> dict:
    assessments = [assess_utxo(r) for r in records]
    assessments.sort(key=lambda a: (-a.priority, -a.amount_sat, a.txid, a.vout))
    exposed_sat = sum(a.amount_sat for a in assessments if a.exposure in {ExposureClass.EXPOSED_LONG, ExposureClass.CONDITIONAL_REUSE_EXPOSURE})
    hidden_sat = sum(a.amount_sat for a in assessments if a.exposure == ExposureClass.HIDDEN_UNTIL_SPEND)
    return {
        "schema": "WS-BITCOIN-QCRYPTO-MIGRATION-MANIFEST-V1",
        "consensus_claim": "NONE_LOCAL_POLICY_ONLY",
        "totals": {
            "utxo_count": len(assessments),
            "long_or_reuse_exposed_sat": exposed_sat,
            "hidden_until_spend_sat": hidden_sat,
        },
        "utxos": [a.to_dict() for a in assessments],
    }


def evaluate_new_output(output: ProposedOutput, policy_state: CryptoPolicyState) -> OutputPolicyDecision:
    network = output.network.strip().upper()
    script = _normalized_script_type(output.script_type)
    reasons: list[str] = []
    controls: list[str] = []

    if network in {"MAINNET", "BITCOIN_MAINNET", "BTC_MAINNET"}:
        return OutputPolicyDecision(
            allowed=False,
            policy_state=policy_state,
            reasons=("this candidate has no Bitcoin mainnet authority",),
            required_controls=("USE_OFFLINE_OR_PUBLIC_TESTNET_ONLY",),
        )

    if network not in {"SIGNET", "TESTNET4", "REGTEST"}:
        return OutputPolicyDecision(
            allowed=False,
            policy_state=policy_state,
            reasons=("network is not explicitly allowed by the candidate",),
            required_controls=("FAIL_CLOSED_UNKNOWN_NETWORK",),
        )

    if output.address_reused:
        reasons.append("address reuse is forbidden by local quantum-hardening policy")
        controls.append("NEW_DESTINATION_REQUIRED")

    if script in _ALWAYS_LONG_EXPOSED:
        reasons.append(f"{script} is long-exposure vulnerable under the current BIP-360 threat model")
        controls.append("AVOID_LONG_EXPOSURE_OUTPUT")

    if script in _PROPOSED_P2MR:
        reasons.append("P2MR is draft/not activated and may only be exercised in isolated experimental code")
        controls.append("CONSENSUS_FEATURE_NOT_ACTIVE")

    if policy_state == CryptoPolicyState.ECDSA_ALLOWED:
        # Baseline state: still reject reuse, unknown scripts and inactive draft output
        # types, but do not pretend existing Bitcoin consensus has become PQ-safe.
        allowed = not output.address_reused and script not in _PROPOSED_P2MR
    elif policy_state == CryptoPolicyState.HYBRID_REQUIRED:
        controls.append("PQ_RELEASE_ATTESTATION_REQUIRED")
        if not output.has_pq_recovery_path:
            reasons.append("HYBRID_REQUIRED state requires a PQ-bound recovery/authorization path")
        if script in _ALWAYS_LONG_EXPOSED:
            reasons.append("HYBRID_REQUIRED blocks creation of new long-exposure outputs")
        allowed = (
            not output.address_reused
            and script in _HASH_HIDDEN_UNTIL_SPEND
            and output.has_pq_recovery_path
        )
    elif policy_state == CryptoPolicyState.PQ_REQUIRED:
        # There is no currently activated Bitcoin post-quantum output/signature path.
        # Fail closed rather than relabeling a classical output as PQ-secure.
        controls.extend(("PQ_CONSENSUS_PATH_REQUIRED", "NO_CURRENT_ACTIVATED_BITCOIN_PQ_OUTPUT"))
        allowed = False
        reasons.append("PQ_REQUIRED cannot be satisfied by currently activated Bitcoin signature/output types")
    elif policy_state == CryptoPolicyState.CLASSICAL_REJECTED:
        controls.extend(("CLASSICAL_ONLY_RELEASE_REJECTED", "RESCUE_OR_PQ_PATH_REQUIRED"))
        allowed = False
        reasons.append("classical-only Bitcoin release is disabled in CLASSICAL_REJECTED state")
    else:  # pragma: no cover
        raise BitcoinQuantumPolicyError("unknown crypto policy state")

    if script not in _ALWAYS_LONG_EXPOSED | _HASH_HIDDEN_UNTIL_SPEND | _PROPOSED_P2MR:
        allowed = False
        reasons.append("unknown script type fails closed")
        controls.append("CLASSIFY_SCRIPT_BEFORE_USE")

    if not reasons and allowed:
        reasons.append("output passes current local pre-sign policy")
    return OutputPolicyDecision(
        allowed=allowed,
        policy_state=policy_state,
        reasons=tuple(dict.fromkeys(reasons)),
        required_controls=tuple(dict.fromkeys(controls)),
    )
