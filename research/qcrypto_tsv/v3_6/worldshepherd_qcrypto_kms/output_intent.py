"""Exact recipient/change binding for Bitcoin signing approval."""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Sequence

from .address_codec import AddressCodecError, address_to_scriptpubkey
from .bitcoin_tx import TxOutput


class OutputIntentError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExpectedPayment:
    amount_sat: int
    address: str | None = None
    script_pubkey_hex: str | None = None
    label: str = ""

    def resolve_script(self, *, network: str) -> bytes:
        if not isinstance(self.amount_sat, int) or isinstance(self.amount_sat, bool) or self.amount_sat < 0:
            raise OutputIntentError("expected payment amount must be a non-negative integer")
        if (self.address is None) == (self.script_pubkey_hex is None):
            raise OutputIntentError("expected payment must specify exactly one of address or script_pubkey_hex")
        if self.address is not None:
            try:
                return address_to_scriptpubkey(self.address, network=network)
            except AddressCodecError as exc:
                raise OutputIntentError(str(exc)) from exc
        try:
            script = bytes.fromhex(self.script_pubkey_hex or "")
        except ValueError as exc:
            raise OutputIntentError("expected payment script_pubkey_hex is invalid") from exc
        if not script:
            raise OutputIntentError("expected payment script must not be empty")
        return script


@dataclass(frozen=True)
class OutputIntentPolicy:
    expected_payments: tuple[ExpectedPayment, ...]
    allowed_change_addresses: tuple[str, ...] = ()
    allowed_change_script_pubkeys_hex: tuple[str, ...] = ()
    max_change_outputs: int = 1
    allow_unlisted_zero_value_op_return: bool = False


@dataclass(frozen=True)
class OutputIntentReport:
    satisfied: bool
    matched_payment_indexes: tuple[int, ...]
    change_output_indexes: tuple[int, ...]
    unauthorized_output_indexes: tuple[int, ...]
    policy_sha256: str
    findings: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _allowed_change_scripts(policy: OutputIntentPolicy, *, network: str) -> set[bytes]:
    out: set[bytes] = set()
    for address in policy.allowed_change_addresses:
        try:
            out.add(address_to_scriptpubkey(address, network=network))
        except AddressCodecError as exc:
            raise OutputIntentError(f"invalid change address: {exc}") from exc
    for text in policy.allowed_change_script_pubkeys_hex:
        try:
            raw = bytes.fromhex(text)
        except ValueError as exc:
            raise OutputIntentError("invalid change script hex") from exc
        if not raw:
            raise OutputIntentError("change script must not be empty")
        out.add(raw)
    return out


def evaluate_output_intent(outputs: Sequence[TxOutput], *, network: str, policy: OutputIntentPolicy) -> OutputIntentReport:
    if not isinstance(policy.max_change_outputs, int) or isinstance(policy.max_change_outputs, bool) or policy.max_change_outputs < 0:
        raise OutputIntentError("max_change_outputs must be a non-negative integer")
    available = set(range(len(outputs)))
    matched: list[int] = []
    findings: list[str] = []
    resolved_payments = [(p, p.resolve_script(network=network)) for p in policy.expected_payments]
    for payment, script in resolved_payments:
        candidates = [i for i in sorted(available) if outputs[i].script_pubkey == script and outputs[i].value_sat == payment.amount_sat]
        if not candidates:
            raise OutputIntentError(f"required payment is absent or amount differs: {payment.label or hashlib.sha256(script).hexdigest()[:16]}")
        chosen = candidates[0]
        available.remove(chosen)
        matched.append(chosen)
    change_scripts = _allowed_change_scripts(policy, network=network)
    change: list[int] = []
    unauthorized: list[int] = []
    for i in sorted(available):
        out = outputs[i]
        if out.script_pubkey in change_scripts:
            change.append(i)
            continue
        if policy.allow_unlisted_zero_value_op_return and out.value_sat == 0 and out.script_pubkey[:1] == b"\x6a":
            continue
        unauthorized.append(i)
    if len(change) > policy.max_change_outputs:
        unauthorized.extend(change[policy.max_change_outputs:])
        findings.append("transaction contains more change outputs than policy permits")
    if unauthorized:
        findings.append(f"unlisted outputs detected: {sorted(set(unauthorized))}")
    if not unauthorized:
        findings.append("every transaction output is bound to an exact recipient or allowlisted change destination")
    canonical = {
        "network": network.strip().upper(),
        "expected": [
            {"amount_sat": p.amount_sat, "script_sha256": hashlib.sha256(script).hexdigest(), "label": p.label}
            for p, script in resolved_payments
        ],
        "change_script_sha256": sorted(hashlib.sha256(x).hexdigest() for x in change_scripts),
        "max_change_outputs": policy.max_change_outputs,
        "allow_unlisted_zero_value_op_return": policy.allow_unlisted_zero_value_op_return,
    }
    import json
    policy_hash = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return OutputIntentReport(
        satisfied=not unauthorized,
        matched_payment_indexes=tuple(matched),
        change_output_indexes=tuple(change[: policy.max_change_outputs]),
        unauthorized_output_indexes=tuple(sorted(set(unauthorized))),
        policy_sha256=policy_hash,
        findings=tuple(findings),
    )
