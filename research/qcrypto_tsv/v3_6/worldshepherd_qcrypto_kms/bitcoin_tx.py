"""Strict Bitcoin transaction parsing and script classification for local policy enforcement.

This module intentionally does not broadcast transactions or implement consensus validation.
It parses serialized transactions so Worldshepherd policy decisions are bound to the actual
bytes presented for signing instead of caller-supplied labels.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, replace
from typing import Iterable, Sequence

from .bitcoin_quantum_policy import CryptoPolicyState, ProposedOutput, evaluate_new_output


class BitcoinTxError(RuntimeError):
    pass


MAX_MONEY = 21_000_000 * 100_000_000
MAX_VECTOR_ITEMS = 100_000
MAX_SCRIPT_BYTES = 1_000_000


def sha256d(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def read_compact_size(data: bytes, offset: int = 0) -> tuple[int, int]:
    """Read a minimally-encoded Bitcoin CompactSize integer."""
    if offset < 0 or offset >= len(data):
        raise BitcoinTxError("truncated CompactSize")
    first = data[offset]
    offset += 1
    if first < 253:
        return first, offset
    widths = {253: 2, 254: 4, 255: 8}
    width = widths[first]
    if offset + width > len(data):
        raise BitcoinTxError("truncated CompactSize payload")
    value = int.from_bytes(data[offset:offset + width], "little")
    if first == 253 and value < 253:
        raise BitcoinTxError("non-minimal CompactSize")
    if first == 254 and value <= 0xFFFF:
        raise BitcoinTxError("non-minimal CompactSize")
    if first == 255 and value <= 0xFFFFFFFF:
        raise BitcoinTxError("non-minimal CompactSize")
    return value, offset + width


def encode_compact_size(value: int) -> bytes:
    if value < 0:
        raise BitcoinTxError("CompactSize cannot encode negative values")
    if value < 253:
        return bytes([value])
    if value <= 0xFFFF:
        return b"\xfd" + value.to_bytes(2, "little")
    if value <= 0xFFFFFFFF:
        return b"\xfe" + value.to_bytes(4, "little")
    if value <= 0xFFFFFFFFFFFFFFFF:
        return b"\xff" + value.to_bytes(8, "little")
    raise BitcoinTxError("CompactSize value too large")


def _read_slice(data: bytes, offset: int, length: int, what: str) -> tuple[bytes, int]:
    if length < 0 or offset < 0 or offset + length > len(data):
        raise BitcoinTxError(f"truncated {what}")
    return data[offset:offset + length], offset + length


@dataclass(frozen=True)
class TxInput:
    prev_txid: str
    vout: int
    script_sig: bytes
    sequence: int
    witness: tuple[bytes, ...] = ()

    def to_dict(self) -> dict:
        out = asdict(self)
        out["script_sig"] = self.script_sig.hex()
        out["witness"] = [w.hex() for w in self.witness]
        return out


@dataclass(frozen=True)
class TxOutput:
    value_sat: int
    script_pubkey: bytes

    @property
    def script_type(self) -> str:
        return classify_script_pubkey(self.script_pubkey)

    def to_dict(self) -> dict:
        return {
            "value_sat": self.value_sat,
            "script_pubkey": self.script_pubkey.hex(),
            "script_type": self.script_type,
        }


@dataclass(frozen=True)
class BitcoinTransaction:
    version: int
    inputs: tuple[TxInput, ...]
    outputs: tuple[TxOutput, ...]
    locktime: int
    segwit: bool

    def serialize(self, *, include_witness: bool = True) -> bytes:
        out = bytearray()
        out += int(self.version).to_bytes(4, "little", signed=True)
        use_witness = include_witness and self.segwit
        if use_witness:
            out += b"\x00\x01"
        out += encode_compact_size(len(self.inputs))
        for txin in self.inputs:
            try:
                prev = bytes.fromhex(txin.prev_txid)
            except ValueError as exc:  # pragma: no cover - construction guard
                raise BitcoinTxError("invalid prev_txid hex") from exc
            if len(prev) != 32:
                raise BitcoinTxError("prev_txid must be 32 bytes")
            out += prev[::-1]
            out += int(txin.vout).to_bytes(4, "little")
            out += encode_compact_size(len(txin.script_sig)) + txin.script_sig
            out += int(txin.sequence).to_bytes(4, "little")
        out += encode_compact_size(len(self.outputs))
        for txout in self.outputs:
            if not 0 <= txout.value_sat <= MAX_MONEY:
                raise BitcoinTxError("output value outside Bitcoin monetary range")
            out += int(txout.value_sat).to_bytes(8, "little", signed=False)
            out += encode_compact_size(len(txout.script_pubkey)) + txout.script_pubkey
        if use_witness:
            for txin in self.inputs:
                out += encode_compact_size(len(txin.witness))
                for item in txin.witness:
                    out += encode_compact_size(len(item)) + item
        out += int(self.locktime).to_bytes(4, "little")
        return bytes(out)

    @property
    def txid(self) -> str:
        return sha256d(self.serialize(include_witness=False))[::-1].hex()

    @property
    def wtxid(self) -> str:
        return sha256d(self.serialize(include_witness=True))[::-1].hex()

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "segwit": self.segwit,
            "locktime": self.locktime,
            "txid": self.txid,
            "wtxid": self.wtxid,
            "inputs": [i.to_dict() for i in self.inputs],
            "outputs": [o.to_dict() for o in self.outputs],
        }


def parse_transaction(raw: bytes | str) -> BitcoinTransaction:
    if isinstance(raw, str):
        try:
            raw = bytes.fromhex(raw.strip())
        except ValueError as exc:
            raise BitcoinTxError("transaction must be valid hex") from exc
    if not isinstance(raw, (bytes, bytearray)):
        raise BitcoinTxError("transaction must be bytes or hex text")
    data = bytes(raw)
    if len(data) < 10:
        raise BitcoinTxError("transaction is too short")
    offset = 0
    version_raw, offset = _read_slice(data, offset, 4, "version")
    version = int.from_bytes(version_raw, "little", signed=True)

    segwit = False
    if offset + 2 <= len(data) and data[offset] == 0 and data[offset + 1] != 0:
        if data[offset + 1] != 1:
            raise BitcoinTxError("unsupported transaction witness flag")
        segwit = True
        offset += 2

    vin_count, offset = read_compact_size(data, offset)
    if vin_count > MAX_VECTOR_ITEMS:
        raise BitcoinTxError("input count exceeds parser safety bound")
    if vin_count == 0:
        raise BitcoinTxError("transaction has zero inputs")
    inputs: list[TxInput] = []
    for _ in range(vin_count):
        prev_raw, offset = _read_slice(data, offset, 32, "previous txid")
        vout_raw, offset = _read_slice(data, offset, 4, "previous output index")
        script_len, offset = read_compact_size(data, offset)
        if script_len > MAX_SCRIPT_BYTES:
            raise BitcoinTxError("scriptSig exceeds parser safety bound")
        script_sig, offset = _read_slice(data, offset, script_len, "scriptSig")
        seq_raw, offset = _read_slice(data, offset, 4, "sequence")
        inputs.append(TxInput(
            prev_txid=prev_raw[::-1].hex(),
            vout=int.from_bytes(vout_raw, "little"),
            script_sig=script_sig,
            sequence=int.from_bytes(seq_raw, "little"),
        ))

    vout_count, offset = read_compact_size(data, offset)
    if vout_count > MAX_VECTOR_ITEMS:
        raise BitcoinTxError("output count exceeds parser safety bound")
    if vout_count == 0:
        raise BitcoinTxError("transaction has zero outputs")
    outputs: list[TxOutput] = []
    total = 0
    for _ in range(vout_count):
        value_raw, offset = _read_slice(data, offset, 8, "output value")
        value = int.from_bytes(value_raw, "little", signed=False)
        if value > MAX_MONEY:
            raise BitcoinTxError("output value exceeds MAX_MONEY")
        total += value
        if total > MAX_MONEY:
            raise BitcoinTxError("total output value exceeds MAX_MONEY")
        script_len, offset = read_compact_size(data, offset)
        if script_len > MAX_SCRIPT_BYTES:
            raise BitcoinTxError("scriptPubKey exceeds parser safety bound")
        script, offset = _read_slice(data, offset, script_len, "scriptPubKey")
        outputs.append(TxOutput(value_sat=value, script_pubkey=script))

    if segwit:
        witnessed: list[TxInput] = []
        for txin in inputs:
            item_count, offset = read_compact_size(data, offset)
            if item_count > MAX_VECTOR_ITEMS:
                raise BitcoinTxError("witness item count exceeds parser safety bound")
            items: list[bytes] = []
            for _ in range(item_count):
                item_len, offset = read_compact_size(data, offset)
                if item_len > MAX_SCRIPT_BYTES:
                    raise BitcoinTxError("witness element exceeds parser safety bound")
                item, offset = _read_slice(data, offset, item_len, "witness element")
                items.append(item)
            witnessed.append(replace(txin, witness=tuple(items)))
        inputs = witnessed

    lock_raw, offset = _read_slice(data, offset, 4, "locktime")
    if offset != len(data):
        raise BitcoinTxError("trailing bytes after transaction")
    return BitcoinTransaction(
        version=version,
        inputs=tuple(inputs),
        outputs=tuple(outputs),
        locktime=int.from_bytes(lock_raw, "little"),
        segwit=segwit,
    )


def classify_script_pubkey(script: bytes) -> str:
    """Classify common scriptPubKeys without executing Script."""
    if not isinstance(script, (bytes, bytearray)):
        raise BitcoinTxError("scriptPubKey must be bytes")
    s = bytes(script)
    if len(s) == 25 and s[:3] == b"\x76\xa9\x14" and s[-2:] == b"\x88\xac":
        return "P2PKH"
    if len(s) == 23 and s[:2] == b"\xa9\x14" and s[-1:] == b"\x87":
        return "P2SH"
    if len(s) == 22 and s[:2] == b"\x00\x14":
        return "P2WPKH"
    if len(s) == 34 and s[:2] == b"\x00\x20":
        return "P2WSH"
    if len(s) == 34 and s[:2] == b"\x51\x20":
        return "P2TR"
    if len(s) == 34 and s[:2] == b"\x52\x20":
        return "P2MR"
    if len(s) == 35 and s[0] == 33 and s[-1] == 0xAC and s[1] in (2, 3):
        return "P2PK"
    if len(s) == 67 and s[0] == 65 and s[-1] == 0xAC and s[1] == 4:
        return "P2PK"
    if s[:1] == b"\x6a":
        return "OP_RETURN"
    # Conservative direct multisig signal; full Script semantics are intentionally
    # not reimplemented here. This is enough to keep bare multisig fail-closed.
    if len(s) >= 3 and s[-1] == 0xAE and 0x51 <= s[0] <= 0x60:
        return "P2MS"
    return "UNKNOWN"


@dataclass(frozen=True)
class SerializedOutputDecision:
    index: int
    value_sat: int
    script_pubkey_hex: str
    script_type: str
    allowed: bool
    reasons: tuple[str, ...]
    required_controls: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SerializedTransactionPolicyReport:
    txid: str
    wtxid: str
    network: str
    policy_state: CryptoPolicyState
    allowed: bool
    output_decisions: tuple[SerializedOutputDecision, ...]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        out = asdict(self)
        out["policy_state"] = self.policy_state.value
        out["output_decisions"] = [x.to_dict() for x in self.output_decisions]
        return out


def evaluate_serialized_transaction(
    raw: bytes | str,
    *,
    network: str,
    policy_state: CryptoPolicyState,
    pq_recovery_output_indexes: Iterable[int] = (),
    allow_zero_value_op_return: bool = False,
) -> SerializedTransactionPolicyReport:
    """Apply output quantum policy to the actual serialized transaction bytes.

    Mainnet remains blocked by ``evaluate_new_output``. OP_RETURN is denied by
    default because this candidate is for custody migration, not arbitrary data
    publication; callers can opt into zero-value OP_RETURN explicitly.
    """
    tx = parse_transaction(raw)
    pq_indexes = set(pq_recovery_output_indexes)
    if any(i < 0 or i >= len(tx.outputs) for i in pq_indexes):
        raise BitcoinTxError("PQ recovery output index is outside transaction outputs")

    decisions: list[SerializedOutputDecision] = []
    reasons: list[str] = []
    for index, txout in enumerate(tx.outputs):
        script_type = txout.script_type
        if script_type == "OP_RETURN":
            ok = bool(allow_zero_value_op_return and txout.value_sat == 0 and network.strip().upper() not in {"MAINNET", "BITCOIN_MAINNET", "BTC_MAINNET"})
            local_reasons = (
                "zero-value OP_RETURN explicitly allowed by local non-mainnet policy" if ok
                else "OP_RETURN denied by default custody-migration policy"
            ,)
            controls = ("EXPLICIT_DATA_CARRIER_OPT_IN",)
        else:
            d = evaluate_new_output(
                ProposedOutput(
                    network=network,
                    script_type=script_type,
                    address_reused=False,
                    has_pq_recovery_path=index in pq_indexes,
                ),
                policy_state,
            )
            ok = d.allowed
            local_reasons = d.reasons
            controls = d.required_controls
        if not ok:
            reasons.append(f"output[{index}] rejected: {'; '.join(local_reasons)}")
        decisions.append(SerializedOutputDecision(
            index=index,
            value_sat=txout.value_sat,
            script_pubkey_hex=txout.script_pubkey.hex(),
            script_type=script_type,
            allowed=ok,
            reasons=tuple(local_reasons),
            required_controls=tuple(controls),
        ))

    if any(txin.script_sig for txin in tx.inputs):
        reasons.append("transaction is not unsigned: at least one scriptSig is populated")
    if any(txin.witness for txin in tx.inputs):
        reasons.append("transaction is not unsigned: at least one witness stack is populated")

    allowed = all(d.allowed for d in decisions) and not any(txin.script_sig or txin.witness for txin in tx.inputs)
    if allowed:
        reasons.append("actual transaction bytes pass local pre-sign output policy")
    return SerializedTransactionPolicyReport(
        txid=tx.txid,
        wtxid=tx.wtxid,
        network=network.strip().upper(),
        policy_state=policy_state,
        allowed=allowed,
        output_decisions=tuple(decisions),
        reasons=tuple(reasons),
    )
