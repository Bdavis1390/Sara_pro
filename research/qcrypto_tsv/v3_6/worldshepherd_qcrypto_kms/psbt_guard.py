"""Strict PSBT v0/v2 structural parsing and pre-sign quantum policy audit.

The guard is deliberately narrower than a wallet: it does not sign, finalize, or
broadcast. Its job is to reject malformed/mutable signing packages and bind policy
checks to the exact transaction/output data carried by a BIP-174/BIP-370 PSBT.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Iterable

from .bitcoin_quantum_policy import CryptoPolicyState, ProposedOutput, evaluate_new_output
from .signature_policy import (
    SignaturePolicyError,
    enforce_sighash_policy,
    parse_schnorr_signature,
    parse_strict_der_ecdsa_signature,
)
from .bitcoin_tx import (
    BitcoinTransaction,
    BitcoinTxError,
    MAX_MONEY,
    TxInput,
    TxOutput,
    classify_script_pubkey,
    encode_compact_size,
    parse_transaction,
    read_compact_size,
)


class PsbtGuardError(RuntimeError):
    pass


PSBT_MAGIC = b"psbt\xff"
MAX_PSBT_BYTES = 16 * 1024 * 1024
MAX_MAP_ENTRIES = 10_000
MAX_FIELD_BYTES = 4 * 1024 * 1024

# BIP 174 global types
PSBT_GLOBAL_UNSIGNED_TX = 0x00
PSBT_GLOBAL_XPUB = 0x01
PSBT_GLOBAL_VERSION = 0xFB
# BIP 370 global types
PSBT_GLOBAL_TX_VERSION = 0x02
PSBT_GLOBAL_FALLBACK_LOCKTIME = 0x03
PSBT_GLOBAL_INPUT_COUNT = 0x04
PSBT_GLOBAL_OUTPUT_COUNT = 0x05
PSBT_GLOBAL_TX_MODIFIABLE = 0x06
# Per-input types
PSBT_IN_NON_WITNESS_UTXO = 0x00
PSBT_IN_WITNESS_UTXO = 0x01
PSBT_IN_PARTIAL_SIG = 0x02
PSBT_IN_SIGHASH_TYPE = 0x03
PSBT_IN_REDEEM_SCRIPT = 0x04
PSBT_IN_WITNESS_SCRIPT = 0x05
PSBT_IN_BIP32_DERIVATION = 0x06
PSBT_IN_FINAL_SCRIPTSIG = 0x07
PSBT_IN_FINAL_SCRIPTWITNESS = 0x08
PSBT_IN_RIPEMD160 = 0x0A
PSBT_IN_SHA256 = 0x0B
PSBT_IN_HASH160 = 0x0C
PSBT_IN_HASH256 = 0x0D
PSBT_IN_PREVIOUS_TXID = 0x0E
PSBT_IN_OUTPUT_INDEX = 0x0F
PSBT_IN_SEQUENCE = 0x10
PSBT_IN_REQUIRED_TIME_LOCKTIME = 0x11
PSBT_IN_REQUIRED_HEIGHT_LOCKTIME = 0x12
PSBT_IN_TAP_KEY_SIG = 0x13
PSBT_IN_TAP_SCRIPT_SIG = 0x14
PSBT_IN_TAP_LEAF_SCRIPT = 0x15
PSBT_IN_TAP_BIP32_DERIVATION = 0x16
PSBT_IN_TAP_INTERNAL_KEY = 0x17
PSBT_IN_TAP_MERKLE_ROOT = 0x18
PSBT_IN_MUSIG2_PARTICIPANT_PUBKEYS = 0x1A
PSBT_IN_MUSIG2_PUB_NONCE = 0x1B
PSBT_IN_MUSIG2_PARTIAL_SIG = 0x1C
# Per-output types
PSBT_OUT_BIP32_DERIVATION = 0x02
PSBT_OUT_AMOUNT = 0x03
PSBT_OUT_SCRIPT = 0x04
PSBT_OUT_TAP_INTERNAL_KEY = 0x05
PSBT_OUT_TAP_TREE = 0x06
PSBT_OUT_TAP_BIP32_DERIVATION = 0x07
PSBT_OUT_MUSIG2_PARTICIPANT_PUBKEYS = 0x08
PSBT_PROPRIETARY = 0xFC

KNOWN_GLOBAL_TYPES = {
    PSBT_GLOBAL_UNSIGNED_TX, PSBT_GLOBAL_XPUB, PSBT_GLOBAL_TX_VERSION,
    PSBT_GLOBAL_FALLBACK_LOCKTIME, PSBT_GLOBAL_INPUT_COUNT, PSBT_GLOBAL_OUTPUT_COUNT,
    PSBT_GLOBAL_TX_MODIFIABLE, PSBT_GLOBAL_VERSION, PSBT_PROPRIETARY,
}
KNOWN_INPUT_TYPES = {
    PSBT_IN_NON_WITNESS_UTXO, PSBT_IN_WITNESS_UTXO, PSBT_IN_PARTIAL_SIG,
    PSBT_IN_SIGHASH_TYPE, PSBT_IN_REDEEM_SCRIPT, PSBT_IN_WITNESS_SCRIPT,
    PSBT_IN_BIP32_DERIVATION, PSBT_IN_FINAL_SCRIPTSIG, PSBT_IN_FINAL_SCRIPTWITNESS,
    PSBT_IN_RIPEMD160, PSBT_IN_SHA256, PSBT_IN_HASH160, PSBT_IN_HASH256,
    PSBT_IN_PREVIOUS_TXID, PSBT_IN_OUTPUT_INDEX, PSBT_IN_SEQUENCE,
    PSBT_IN_REQUIRED_TIME_LOCKTIME, PSBT_IN_REQUIRED_HEIGHT_LOCKTIME,
    PSBT_IN_TAP_KEY_SIG, PSBT_IN_TAP_SCRIPT_SIG, PSBT_IN_TAP_LEAF_SCRIPT,
    PSBT_IN_TAP_BIP32_DERIVATION, PSBT_IN_TAP_INTERNAL_KEY, PSBT_IN_TAP_MERKLE_ROOT,
    PSBT_IN_MUSIG2_PARTICIPANT_PUBKEYS, PSBT_IN_MUSIG2_PUB_NONCE,
    PSBT_IN_MUSIG2_PARTIAL_SIG, PSBT_PROPRIETARY,
}
KNOWN_OUTPUT_TYPES = {
    PSBT_OUT_BIP32_DERIVATION, PSBT_OUT_AMOUNT, PSBT_OUT_SCRIPT,
    PSBT_OUT_TAP_INTERNAL_KEY, PSBT_OUT_TAP_TREE, PSBT_OUT_TAP_BIP32_DERIVATION,
    PSBT_OUT_MUSIG2_PARTICIPANT_PUBKEYS, PSBT_PROPRIETARY,
}


@dataclass(frozen=True)
class PsbtEntry:
    key_type: int
    key_data: bytes
    value: bytes
    raw_key: bytes

    def safe_summary(self) -> dict:
        return {
            "key_type": self.key_type,
            "key_data_len": len(self.key_data),
            "value_len": len(self.value),
            "raw_key_sha256": hashlib.sha256(self.raw_key).hexdigest(),
        }


@dataclass(frozen=True)
class ParsedPsbt:
    version: int
    global_map: tuple[PsbtEntry, ...]
    input_maps: tuple[tuple[PsbtEntry, ...], ...]
    output_maps: tuple[tuple[PsbtEntry, ...], ...]
    unsigned_tx: BitcoinTransaction | None
    reconstructed_v2_tx: BitcoinTransaction | None

    @property
    def transaction(self) -> BitcoinTransaction:
        tx = self.unsigned_tx or self.reconstructed_v2_tx
        if tx is None:  # pragma: no cover
            raise PsbtGuardError("PSBT has no reconstructable transaction")
        return tx


def _read_map(data: bytes, offset: int) -> tuple[tuple[PsbtEntry, ...], int]:
    entries: list[PsbtEntry] = []
    seen: set[bytes] = set()
    while True:
        if len(entries) > MAX_MAP_ENTRIES:
            raise PsbtGuardError("PSBT map exceeds safety entry limit")
        try:
            key_len, offset = read_compact_size(data, offset)
        except BitcoinTxError as exc:
            raise PsbtGuardError(str(exc)) from exc
        if key_len == 0:
            return tuple(entries), offset
        if key_len > MAX_FIELD_BYTES or offset + key_len > len(data):
            raise PsbtGuardError("truncated or oversized PSBT key")
        raw_key = data[offset:offset + key_len]
        offset += key_len
        if raw_key in seen:
            raise PsbtGuardError("duplicate PSBT key in map")
        seen.add(raw_key)
        try:
            key_type, key_data_offset = read_compact_size(raw_key, 0)
        except BitcoinTxError as exc:
            raise PsbtGuardError(f"invalid PSBT key type: {exc}") from exc
        key_data = raw_key[key_data_offset:]
        try:
            value_len, offset = read_compact_size(data, offset)
        except BitcoinTxError as exc:
            raise PsbtGuardError(str(exc)) from exc
        if value_len > MAX_FIELD_BYTES or offset + value_len > len(data):
            raise PsbtGuardError("truncated or oversized PSBT value")
        value = data[offset:offset + value_len]
        offset += value_len
        entries.append(PsbtEntry(key_type=key_type, key_data=key_data, value=value, raw_key=raw_key))


def _entries_of(entries: tuple[PsbtEntry, ...], key_type: int) -> list[PsbtEntry]:
    return [e for e in entries if e.key_type == key_type]


def _singleton(entries: tuple[PsbtEntry, ...], key_type: int, *, required: bool = False, no_keydata: bool = True) -> PsbtEntry | None:
    values = _entries_of(entries, key_type)
    if not values:
        if required:
            raise PsbtGuardError(f"missing required PSBT field 0x{key_type:02x}")
        return None
    if len(values) != 1:
        raise PsbtGuardError(f"field 0x{key_type:02x} must occur once")
    if no_keydata and values[0].key_data:
        raise PsbtGuardError(f"field 0x{key_type:02x} must not contain key data")
    return values[0]


def _compact_value(entry: PsbtEntry, name: str) -> int:
    try:
        value, end = read_compact_size(entry.value, 0)
    except BitcoinTxError as exc:
        raise PsbtGuardError(f"invalid {name}: {exc}") from exc
    if end != len(entry.value):
        raise PsbtGuardError(f"invalid {name}: trailing bytes")
    return value


def _u32(entry: PsbtEntry, name: str, *, signed: bool = False) -> int:
    if len(entry.value) != 4:
        raise PsbtGuardError(f"{name} must be exactly 4 bytes")
    return int.from_bytes(entry.value, "little", signed=signed)


def _valid_pubkey_bytes(raw: bytes) -> bool:
    return _is_valid_secp256k1_pubkey(raw)


def _validate_derivation_value(value: bytes, *, name: str) -> int:
    if len(value) < 4 or (len(value) - 4) % 4:
        raise PsbtGuardError(f"{name} must be master fingerprint plus 32-bit path elements")
    return (len(value) - 4) // 4


def _validate_tap_derivation(entry: PsbtEntry, *, name: str) -> None:
    if len(entry.key_data) != 32 or not _is_valid_xonly_pubkey(entry.key_data):
        raise PsbtGuardError(f"{name} key data must be a valid 32-byte x-only public key")
    try:
        count, offset = read_compact_size(entry.value, 0)
    except BitcoinTxError as exc:
        raise PsbtGuardError(f"invalid {name} leaf-hash count: {exc}") from exc
    hashes_end = offset + 32 * count
    if hashes_end > len(entry.value):
        raise PsbtGuardError(f"{name} leaf-hash list is truncated")
    _validate_derivation_value(entry.value[hashes_end:], name=name)



_SECP256K1_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F


def _is_valid_secp256k1_pubkey(raw: bytes) -> bool:
    """Cheap curve-membership check for serialized secp256k1 public keys."""
    if len(raw) == 33 and raw[0] in (2, 3):
        x = int.from_bytes(raw[1:], "big")
        if x >= _SECP256K1_P:
            return False
        rhs = (pow(x, 3, _SECP256K1_P) + 7) % _SECP256K1_P
        return rhs != 0 and pow(rhs, (_SECP256K1_P - 1) // 2, _SECP256K1_P) == 1
    if len(raw) == 65 and raw[0] == 4:
        x = int.from_bytes(raw[1:33], "big")
        y = int.from_bytes(raw[33:], "big")
        return x < _SECP256K1_P and y < _SECP256K1_P and (y * y - x * x * x - 7) % _SECP256K1_P == 0
    return False


def _is_valid_xonly_pubkey(raw: bytes) -> bool:
    if len(raw) != 32:
        return False
    x = int.from_bytes(raw, "big")
    if x >= _SECP256K1_P:
        return False
    rhs = (pow(x, 3, _SECP256K1_P) + 7) % _SECP256K1_P
    return rhs != 0 and pow(rhs, (_SECP256K1_P - 1) // 2, _SECP256K1_P) == 1


def _validate_hash_preimages(m: tuple[PsbtEntry, ...], *, input_index: int) -> None:
    specs = (
        (PSBT_IN_RIPEMD160, 20, lambda b: hashlib.new("ripemd160", b).digest(), "RIPEMD160"),
        (PSBT_IN_SHA256, 32, lambda b: hashlib.sha256(b).digest(), "SHA256"),
        (PSBT_IN_HASH160, 20, lambda b: hashlib.new("ripemd160", hashlib.sha256(b).digest()).digest(), "HASH160"),
        (PSBT_IN_HASH256, 32, lambda b: hashlib.sha256(hashlib.sha256(b).digest()).digest(), "HASH256"),
    )
    for key_type, key_len, digest, name in specs:
        for entry in _entries_of(m, key_type):
            if len(entry.key_data) != key_len:
                raise PsbtGuardError(f"input[{input_index}] {name} preimage key has wrong hash length")
            if digest(entry.value) != entry.key_data:
                raise PsbtGuardError(f"input[{input_index}] {name} preimage does not match its key hash")


def _declared_sighash(m: tuple[PsbtEntry, ...], *, input_index: int) -> int | None:
    sighash = _singleton(m, PSBT_IN_SIGHASH_TYPE)
    if sighash is None:
        return None
    if len(sighash.value) != 4:
        raise PsbtGuardError(f"input[{input_index}] sighash type must be exactly 4 bytes")
    value = int.from_bytes(sighash.value, "little")
    if value > 0xFF:
        raise PsbtGuardError(f"input[{input_index}] sighash type has unsupported high bits")
    return value


def _validate_partial_signatures(m: tuple[PsbtEntry, ...], *, input_index: int) -> None:
    declared = _declared_sighash(m, input_index=input_index)
    for entry in _entries_of(m, PSBT_IN_PARTIAL_SIG):
        if not _is_valid_secp256k1_pubkey(entry.key_data):
            raise PsbtGuardError(f"input[{input_index}] partial signature key is not a valid secp256k1 public key")
        try:
            parsed = parse_strict_der_ecdsa_signature(entry.value, require_low_s=True)
            enforce_sighash_policy(parsed.sighash_type, taproot=False)
        except SignaturePolicyError as exc:
            raise PsbtGuardError(f"input[{input_index}] invalid ECDSA partial signature: {exc}") from exc
        if declared is not None and parsed.sighash_type != declared:
            raise PsbtGuardError(f"input[{input_index}] partial signature sighash disagrees with PSBT_IN_SIGHASH_TYPE")


def _validate_taproot_fields(m: tuple[PsbtEntry, ...], *, input_index: int) -> None:
    declared = _declared_sighash(m, input_index=input_index)
    key_sig = _singleton(m, PSBT_IN_TAP_KEY_SIG)
    if key_sig is not None:
        try:
            parsed = parse_schnorr_signature(key_sig.value)
            enforce_sighash_policy(parsed.sighash_type, taproot=True)
        except SignaturePolicyError as exc:
            raise PsbtGuardError(f"input[{input_index}] invalid Taproot key-path signature: {exc}") from exc
        if declared is not None and parsed.sighash_type != declared:
            raise PsbtGuardError(f"input[{input_index}] Taproot key signature sighash disagrees with PSBT_IN_SIGHASH_TYPE")
    for entry in _entries_of(m, PSBT_IN_TAP_SCRIPT_SIG):
        if len(entry.key_data) != 64:
            raise PsbtGuardError(f"input[{input_index}] Taproot script signature key data must be xonly pubkey + leaf hash")
        if not _is_valid_xonly_pubkey(entry.key_data[:32]):
            raise PsbtGuardError(f"input[{input_index}] Taproot script signature has invalid x-only public key")
        try:
            parsed = parse_schnorr_signature(entry.value)
            enforce_sighash_policy(parsed.sighash_type, taproot=True)
        except SignaturePolicyError as exc:
            raise PsbtGuardError(f"input[{input_index}] invalid Taproot script-path signature: {exc}") from exc
        if declared is not None and parsed.sighash_type != declared:
            raise PsbtGuardError(f"input[{input_index}] Taproot script signature sighash disagrees with PSBT_IN_SIGHASH_TYPE")
    for entry in _entries_of(m, PSBT_IN_TAP_LEAF_SCRIPT):
        # BIP-341 control block: 33 + 32m bytes, m in [0,128].
        if len(entry.key_data) < 33 or (len(entry.key_data) - 33) % 32 != 0:
            raise PsbtGuardError(f"input[{input_index}] Taproot leaf control block has invalid length")
        if (len(entry.key_data) - 33) // 32 > 128:
            raise PsbtGuardError(f"input[{input_index}] Taproot leaf control block exceeds depth 128")
        if not _is_valid_xonly_pubkey(entry.key_data[1:33]):
            raise PsbtGuardError(f"input[{input_index}] Taproot leaf control block has invalid internal key")
        if len(entry.value) < 1:
            raise PsbtGuardError(f"input[{input_index}] Taproot leaf script value must include leaf version")
    root = _singleton(m, PSBT_IN_TAP_MERKLE_ROOT)
    if root is not None and len(root.value) != 32:
        raise PsbtGuardError(f"input[{input_index}] Taproot Merkle root must be 32 bytes")


def _parse_final_scriptwitness(value: bytes, *, input_index: int) -> tuple[bytes, ...]:
    try:
        count, offset = read_compact_size(value, 0)
    except BitcoinTxError as exc:
        raise PsbtGuardError(f"input[{input_index}] invalid final scriptWitness: {exc}") from exc
    if count > 10_000:
        raise PsbtGuardError(f"input[{input_index}] final scriptWitness has too many elements")
    items: list[bytes] = []
    for _ in range(count):
        try:
            size, offset = read_compact_size(value, offset)
        except BitcoinTxError as exc:
            raise PsbtGuardError(f"input[{input_index}] invalid final scriptWitness element: {exc}") from exc
        if size > MAX_FIELD_BYTES or offset + size > len(value):
            raise PsbtGuardError(f"input[{input_index}] final scriptWitness element is truncated/oversized")
        items.append(value[offset:offset + size])
        offset += size
    if offset != len(value):
        raise PsbtGuardError(f"input[{input_index}] final scriptWitness has trailing bytes")
    return tuple(items)


def _validate_finalization_exclusivity(m: tuple[PsbtEntry, ...], *, input_index: int) -> None:
    final_sig = _singleton(m, PSBT_IN_FINAL_SCRIPTSIG)
    final_wit = _singleton(m, PSBT_IN_FINAL_SCRIPTWITNESS)
    if final_wit is not None:
        _parse_final_scriptwitness(final_wit.value, input_index=input_index)
    if final_sig is None and final_wit is None:
        return
    forbidden = {
        PSBT_IN_PARTIAL_SIG, PSBT_IN_SIGHASH_TYPE, PSBT_IN_REDEEM_SCRIPT, PSBT_IN_WITNESS_SCRIPT,
        PSBT_IN_BIP32_DERIVATION, PSBT_IN_RIPEMD160, PSBT_IN_SHA256, PSBT_IN_HASH160,
        PSBT_IN_HASH256, PSBT_IN_TAP_KEY_SIG, PSBT_IN_TAP_SCRIPT_SIG, PSBT_IN_TAP_LEAF_SCRIPT,
        PSBT_IN_TAP_BIP32_DERIVATION, PSBT_IN_TAP_INTERNAL_KEY, PSBT_IN_TAP_MERKLE_ROOT,
        PSBT_IN_MUSIG2_PARTICIPANT_PUBKEYS, PSBT_IN_MUSIG2_PUB_NONCE, PSBT_IN_MUSIG2_PARTIAL_SIG,
    }
    leftovers = sorted({e.key_type for e in m if e.key_type in forbidden})
    if leftovers:
        raise PsbtGuardError(f"input[{input_index}] finalized PSBT input retains signing metadata: {leftovers}")


def _validate_musig2_participants(entry: PsbtEntry, *, name: str) -> None:
    if len(entry.key_data) != 33 or not _is_valid_secp256k1_pubkey(entry.key_data):
        raise PsbtGuardError(f"{name} aggregate public key must be a valid compressed secp256k1 key")
    if not entry.value or len(entry.value) % 33:
        raise PsbtGuardError(f"{name} participant list must contain one or more 33-byte compressed keys")
    for off in range(0, len(entry.value), 33):
        if not _is_valid_secp256k1_pubkey(entry.value[off:off + 33]):
            raise PsbtGuardError(f"{name} contains an invalid participant public key")


def _validate_musig2_input_fields(m: tuple[PsbtEntry, ...], *, input_index: int) -> None:
    for e in _entries_of(m, PSBT_IN_MUSIG2_PARTICIPANT_PUBKEYS):
        _validate_musig2_participants(e, name=f"input[{input_index}] MuSig2 participants")
    for key_type, value_len, label in (
        (PSBT_IN_MUSIG2_PUB_NONCE, 66, "public nonce"),
        (PSBT_IN_MUSIG2_PARTIAL_SIG, 32, "partial signature"),
    ):
        for e in _entries_of(m, key_type):
            if len(e.key_data) not in (66, 98):
                raise PsbtGuardError(f"input[{input_index}] MuSig2 {label} key data must be 66 or 98 bytes")
            part, agg = e.key_data[:33], e.key_data[33:66]
            if not _is_valid_secp256k1_pubkey(part) or not _is_valid_secp256k1_pubkey(agg):
                raise PsbtGuardError(f"input[{input_index}] MuSig2 {label} contains invalid public key material")
            if len(e.value) != value_len:
                raise PsbtGuardError(f"input[{input_index}] MuSig2 {label} value must be {value_len} bytes")


def _validate_tap_tree(value: bytes, *, output_index: int) -> None:
    if not value:
        raise PsbtGuardError(f"output[{output_index}] Taproot tree cannot be empty")
    offset = 0
    while offset < len(value):
        if offset + 2 > len(value):
            raise PsbtGuardError(f"output[{output_index}] Taproot tree tuple is truncated")
        depth = value[offset]
        offset += 2  # leaf version byte is structurally present; semantics remain Bitcoin Core's job.
        if depth > 128:
            raise PsbtGuardError(f"output[{output_index}] Taproot tree depth exceeds 128")
        try:
            script_len, offset = read_compact_size(value, offset)
        except BitcoinTxError as exc:
            raise PsbtGuardError(f"output[{output_index}] invalid Taproot tree script length: {exc}") from exc
        if offset + script_len > len(value):
            raise PsbtGuardError(f"output[{output_index}] Taproot tree script is truncated")
        offset += script_len

def _validate_common_metadata(globals_: tuple[PsbtEntry, ...], inputs: tuple[tuple[PsbtEntry, ...], ...], outputs: tuple[tuple[PsbtEntry, ...], ...]) -> None:
    for entry in _entries_of(globals_, PSBT_GLOBAL_XPUB):
        if len(entry.key_data) != 78:
            raise PsbtGuardError("PSBT_GLOBAL_XPUB key data must be 78-byte BIP32 serialization")
        if entry.key_data[45] not in (2, 3):
            raise PsbtGuardError("PSBT_GLOBAL_XPUB must contain a compressed public key")
        path_count = _validate_derivation_value(entry.value, name="PSBT_GLOBAL_XPUB derivation")
        if entry.key_data[4] != path_count:
            raise PsbtGuardError("PSBT_GLOBAL_XPUB depth does not match derivation path length")
    for index, m in enumerate(inputs):
        for entry in _entries_of(m, PSBT_IN_BIP32_DERIVATION):
            if not _valid_pubkey_bytes(entry.key_data):
                raise PsbtGuardError(f"input[{index}] BIP32 derivation key is not a valid serialized public key")
            _validate_derivation_value(entry.value, name=f"input[{index}] BIP32 derivation")
        for entry in _entries_of(m, PSBT_IN_TAP_BIP32_DERIVATION):
            _validate_tap_derivation(entry, name=f"input[{index}] Taproot BIP32 derivation")
        _ = _declared_sighash(m, input_index=index)
        _validate_hash_preimages(m, input_index=index)
        _validate_partial_signatures(m, input_index=index)
        _validate_taproot_fields(m, input_index=index)
        _validate_musig2_input_fields(m, input_index=index)
        _validate_finalization_exclusivity(m, input_index=index)
        tap_internal = _singleton(m, PSBT_IN_TAP_INTERNAL_KEY)
        if tap_internal is not None and (len(tap_internal.value) != 32 or not _is_valid_xonly_pubkey(tap_internal.value)):
            raise PsbtGuardError(f"input[{index}] Taproot internal key must be a valid 32-byte x-only public key")
    for index, m in enumerate(outputs):
        for entry in _entries_of(m, PSBT_OUT_BIP32_DERIVATION):
            if not _valid_pubkey_bytes(entry.key_data):
                raise PsbtGuardError(f"output[{index}] BIP32 derivation key is not a valid serialized public key")
            _validate_derivation_value(entry.value, name=f"output[{index}] BIP32 derivation")
        for entry in _entries_of(m, PSBT_OUT_TAP_BIP32_DERIVATION):
            _validate_tap_derivation(entry, name=f"output[{index}] Taproot BIP32 derivation")
        tap_internal = _singleton(m, PSBT_OUT_TAP_INTERNAL_KEY)
        if tap_internal is not None and (len(tap_internal.value) != 32 or not _is_valid_xonly_pubkey(tap_internal.value)):
            raise PsbtGuardError(f"output[{index}] Taproot internal key must be a valid 32-byte x-only public key")
        tree = _singleton(m, PSBT_OUT_TAP_TREE)
        if tree is not None:
            _validate_tap_tree(tree.value, output_index=index)
        for e in _entries_of(m, PSBT_OUT_MUSIG2_PARTICIPANT_PUBKEYS):
            _validate_musig2_participants(e, name=f"output[{index}] MuSig2 participants")


def _parse_version(globals_: tuple[PsbtEntry, ...]) -> int:
    version_entry = _singleton(globals_, PSBT_GLOBAL_VERSION)
    if version_entry is None:
        return 0
    version = _u32(version_entry, "PSBT global version")
    if version not in (0, 2):
        raise PsbtGuardError("only PSBT versions 0 and 2 are accepted")
    return version


def _determine_v2_locktime(globals_: tuple[PsbtEntry, ...], inputs: tuple[tuple[PsbtEntry, ...], ...]) -> int:
    fallback_entry = _singleton(globals_, PSBT_GLOBAL_FALLBACK_LOCKTIME)
    fallback = _u32(fallback_entry, "PSBTv2 fallback locktime") if fallback_entry else 0
    time_values: list[int] = []
    height_values: list[int] = []
    time_supported_by_all = True
    height_supported_by_all = True
    any_requirement = False
    for index, m in enumerate(inputs):
        t = _singleton(m, PSBT_IN_REQUIRED_TIME_LOCKTIME)
        h = _singleton(m, PSBT_IN_REQUIRED_HEIGHT_LOCKTIME)
        if t is not None:
            any_requirement = True
            tv = _u32(t, f"input[{index}] required time locktime")
            if tv < 500_000_000:
                raise PsbtGuardError(f"input[{index}] required time locktime must be >= 500000000")
            time_values.append(tv)
        else:
            # An input with no locktime requirements can support either type; an
            # input that specifies only height cannot support a time locktime.
            if h is not None:
                time_supported_by_all = False
        if h is not None:
            any_requirement = True
            hv = _u32(h, f"input[{index}] required height locktime")
            if hv <= 0 or hv >= 500_000_000:
                raise PsbtGuardError(f"input[{index}] required height locktime must be 1..499999999")
            height_values.append(hv)
        else:
            if t is not None:
                height_supported_by_all = False
    if not any_requirement:
        return fallback
    # BIP-370 chooses height when both forms are possible.
    if height_supported_by_all and height_values:
        return max(height_values)
    if time_supported_by_all and time_values:
        return max(time_values)
    raise PsbtGuardError("PSBTv2 inputs have incompatible required locktime types")


def _reconstruct_v2(globals_: tuple[PsbtEntry, ...], inputs: tuple[tuple[PsbtEntry, ...], ...], outputs: tuple[tuple[PsbtEntry, ...], ...]) -> BitcoinTransaction:
    tx_version = _u32(_singleton(globals_, PSBT_GLOBAL_TX_VERSION, required=True), "PSBTv2 transaction version", signed=True)  # type: ignore[arg-type]
    locktime = _determine_v2_locktime(globals_, inputs)

    txins: list[TxInput] = []
    for index, m in enumerate(inputs):
        prev = _singleton(m, PSBT_IN_PREVIOUS_TXID, required=True)
        out_index = _singleton(m, PSBT_IN_OUTPUT_INDEX, required=True)
        assert prev is not None and out_index is not None
        if len(prev.value) != 32:
            raise PsbtGuardError(f"input[{index}] previous txid must be 32 bytes")
        vout = _u32(out_index, f"input[{index}] output index")
        seq_entry = _singleton(m, PSBT_IN_SEQUENCE)
        sequence = _u32(seq_entry, f"input[{index}] sequence") if seq_entry else 0xFFFFFFFF
        txins.append(TxInput(prev_txid=prev.value[::-1].hex(), vout=vout, script_sig=b"", sequence=sequence))

    txouts: list[TxOutput] = []
    for index, m in enumerate(outputs):
        amount = _singleton(m, PSBT_OUT_AMOUNT, required=True)
        script = _singleton(m, PSBT_OUT_SCRIPT, required=True)
        assert amount is not None and script is not None
        if len(amount.value) != 8:
            raise PsbtGuardError(f"output[{index}] amount must be 8 bytes")
        value = int.from_bytes(amount.value, "little", signed=True)
        if value < 0:
            raise PsbtGuardError(f"output[{index}] amount cannot be negative")
        txouts.append(TxOutput(value_sat=value, script_pubkey=script.value))
    tx = BitcoinTransaction(version=tx_version, inputs=tuple(txins), outputs=tuple(txouts), locktime=locktime, segwit=False)
    # Serializer applies MAX_MONEY and aggregate checks when the transaction is later hashed.
    _ = tx.txid
    return tx


def parse_psbt(raw: bytes | str) -> ParsedPsbt:
    if isinstance(raw, str):
        text = raw.strip()
        try:
            raw = bytes.fromhex(text)
        except ValueError as exc:
            raise PsbtGuardError("PSBT text must be hexadecimal") from exc
    if not isinstance(raw, (bytes, bytearray)):
        raise PsbtGuardError("PSBT must be bytes or hexadecimal text")
    data = bytes(raw)
    if len(data) > MAX_PSBT_BYTES:
        raise PsbtGuardError("PSBT exceeds parser safety size")
    if not data.startswith(PSBT_MAGIC):
        raise PsbtGuardError("invalid PSBT magic")
    offset = len(PSBT_MAGIC)
    globals_, offset = _read_map(data, offset)
    version = _parse_version(globals_)

    unsigned_tx: BitcoinTransaction | None = None
    reconstructed: BitcoinTransaction | None = None
    if version == 0:
        for forbidden in (PSBT_GLOBAL_TX_VERSION, PSBT_GLOBAL_FALLBACK_LOCKTIME, PSBT_GLOBAL_INPUT_COUNT, PSBT_GLOBAL_OUTPUT_COUNT, PSBT_GLOBAL_TX_MODIFIABLE):
            if _entries_of(globals_, forbidden):
                raise PsbtGuardError(f"PSBTv0 contains PSBTv2-only global field 0x{forbidden:02x}")
        tx_entry = _singleton(globals_, PSBT_GLOBAL_UNSIGNED_TX, required=True)
        assert tx_entry is not None
        try:
            unsigned_tx = parse_transaction(tx_entry.value)
        except BitcoinTxError as exc:
            raise PsbtGuardError(f"invalid PSBTv0 unsigned transaction: {exc}") from exc
        if unsigned_tx.segwit:
            raise PsbtGuardError("PSBTv0 unsigned transaction must use legacy serialization without witness marker")
        if any(i.script_sig or i.witness for i in unsigned_tx.inputs):
            raise PsbtGuardError("PSBTv0 unsigned transaction must have empty scriptSig and witness")
        input_count = len(unsigned_tx.inputs)
        output_count = len(unsigned_tx.outputs)
    else:
        if _entries_of(globals_, PSBT_GLOBAL_UNSIGNED_TX):
            raise PsbtGuardError("PSBTv2 must exclude PSBT_GLOBAL_UNSIGNED_TX")
        version_entry = _singleton(globals_, PSBT_GLOBAL_VERSION, required=True)
        assert version_entry is not None and _u32(version_entry, "PSBT global version") == 2
        input_count = _compact_value(_singleton(globals_, PSBT_GLOBAL_INPUT_COUNT, required=True), "PSBTv2 input count")  # type: ignore[arg-type]
        output_count = _compact_value(_singleton(globals_, PSBT_GLOBAL_OUTPUT_COUNT, required=True), "PSBTv2 output count")  # type: ignore[arg-type]
        if input_count == 0 or output_count == 0:
            raise PsbtGuardError("PSBTv2 must contain at least one input and one output for signing")
        mod = _singleton(globals_, PSBT_GLOBAL_TX_MODIFIABLE)
        if mod is not None and len(mod.value) != 1:
            raise PsbtGuardError("PSBTv2 transaction modifiable flags must be one byte")

    if input_count > 100_000 or output_count > 100_000:
        raise PsbtGuardError("PSBT input/output count exceeds safety bound")
    input_maps: list[tuple[PsbtEntry, ...]] = []
    for _ in range(input_count):
        m, offset = _read_map(data, offset)
        input_maps.append(m)
    output_maps: list[tuple[PsbtEntry, ...]] = []
    for _ in range(output_count):
        m, offset = _read_map(data, offset)
        output_maps.append(m)
    if offset != len(data):
        raise PsbtGuardError("trailing bytes after declared PSBT maps")

    _validate_common_metadata(globals_, tuple(input_maps), tuple(output_maps))

    if version == 2:
        reconstructed = _reconstruct_v2(globals_, tuple(input_maps), tuple(output_maps))
    return ParsedPsbt(
        version=version,
        global_map=globals_,
        input_maps=tuple(input_maps),
        output_maps=tuple(output_maps),
        unsigned_tx=unsigned_tx,
        reconstructed_v2_tx=reconstructed,
    )


def _parse_witness_utxo(value: bytes, *, input_index: int) -> TxOutput:
    if len(value) < 9:
        raise PsbtGuardError(f"input[{input_index}] witness UTXO is truncated")
    amount = int.from_bytes(value[:8], "little", signed=False)
    if amount > MAX_MONEY:
        raise PsbtGuardError(f"input[{input_index}] witness UTXO amount exceeds MAX_MONEY")
    try:
        script_len, offset = read_compact_size(value, 8)
    except BitcoinTxError as exc:
        raise PsbtGuardError(f"input[{input_index}] invalid witness UTXO: {exc}") from exc
    if offset + script_len != len(value):
        raise PsbtGuardError(f"input[{input_index}] witness UTXO has invalid script length/trailing bytes")
    return TxOutput(value_sat=amount, script_pubkey=value[offset:])


def _hash160(data: bytes) -> bytes:
    return hashlib.new("ripemd160", hashlib.sha256(data).digest()).digest()


def _validate_input_script_commitments(*, input_index: int, prevout: TxOutput, m: tuple[PsbtEntry, ...]) -> None:
    st = classify_script_pubkey(prevout.script_pubkey)
    redeem = _singleton(m, PSBT_IN_REDEEM_SCRIPT)
    witness_script = _singleton(m, PSBT_IN_WITNESS_SCRIPT)

    effective = prevout.script_pubkey
    if st == "P2SH":
        if redeem is None:
            raise PsbtGuardError(f"input[{input_index}] P2SH prevout requires redeemScript before signing")
        if len(prevout.script_pubkey) != 23 or _hash160(redeem.value) != prevout.script_pubkey[2:22]:
            raise PsbtGuardError(f"input[{input_index}] redeemScript does not match P2SH commitment")
        effective = redeem.value
        nested_type = classify_script_pubkey(effective)
        if nested_type not in {"P2WPKH", "P2WSH"}:
            # Non-SegWit P2SH remains signable when a full non-witness UTXO is
            # present; commitment verification above is the required check.
            if _singleton(m, PSBT_IN_NON_WITNESS_UTXO) is None:
                raise PsbtGuardError(f"input[{input_index}] witness-only P2SH is not a recognized SegWit redeemScript")
    elif redeem is not None:
        raise PsbtGuardError(f"input[{input_index}] redeemScript supplied for non-P2SH prevout")

    effective_type = classify_script_pubkey(effective)
    if effective_type == "P2WSH":
        if witness_script is None:
            raise PsbtGuardError(f"input[{input_index}] P2WSH requires witnessScript before signing")
        if hashlib.sha256(witness_script.value).digest() != effective[2:34]:
            raise PsbtGuardError(f"input[{input_index}] witnessScript does not match P2WSH commitment")
    elif witness_script is not None:
        raise PsbtGuardError(f"input[{input_index}] witnessScript supplied for non-P2WSH spend path")


def _validate_input_utxo_provenance(psbt: ParsedPsbt) -> tuple[tuple[TxOutput, ...], tuple[str, ...]]:
    """Resolve every input's claimed previous output and cross-check duplicate sources."""
    tx = psbt.transaction
    resolved: list[TxOutput] = []
    findings: list[str] = []
    seen_prevouts: set[tuple[str, int]] = set()
    for index, (txin, m) in enumerate(zip(tx.inputs, psbt.input_maps)):
        prevout_id = (txin.prev_txid.lower(), txin.vout)
        if prevout_id in seen_prevouts:
            raise PsbtGuardError(f"input[{index}] duplicates a previous outpoint in the same PSBT")
        seen_prevouts.add(prevout_id)
        nonw = _singleton(m, PSBT_IN_NON_WITNESS_UTXO)
        wit = _singleton(m, PSBT_IN_WITNESS_UTXO)
        if nonw is None and wit is None:
            raise PsbtGuardError(f"input[{index}] has no UTXO provenance; signing is refused")

        from_nonw: TxOutput | None = None
        if nonw is not None:
            try:
                prev_tx = parse_transaction(nonw.value)
            except BitcoinTxError as exc:
                raise PsbtGuardError(f"input[{index}] invalid non-witness UTXO transaction: {exc}") from exc
            if prev_tx.txid.lower() != txin.prev_txid.lower():
                raise PsbtGuardError(f"input[{index}] non-witness UTXO txid does not match prevout")
            if txin.vout >= len(prev_tx.outputs):
                raise PsbtGuardError(f"input[{index}] prevout index is outside non-witness UTXO outputs")
            from_nonw = prev_tx.outputs[txin.vout]

        from_wit: TxOutput | None = None
        if wit is not None:
            from_wit = _parse_witness_utxo(wit.value, input_index=index)
            st = classify_script_pubkey(from_wit.script_pubkey)
            if nonw is None and st in {"P2PKH", "P2PK", "P2MS", "UNKNOWN", "OP_RETURN"}:
                raise PsbtGuardError(f"input[{index}] witness-only UTXO is not a recognized native/wrapped SegWit/Taproot form")

        if from_nonw is not None and from_wit is not None:
            if from_nonw.value_sat != from_wit.value_sat or from_nonw.script_pubkey != from_wit.script_pubkey:
                raise PsbtGuardError(f"input[{index}] witness and non-witness UTXO data disagree")
            findings.append(f"input[{index}] witness/non-witness UTXO sources agree")
        chosen = from_wit or from_nonw
        assert chosen is not None
        _validate_input_script_commitments(input_index=index, prevout=chosen, m=m)
        resolved.append(chosen)
    return tuple(resolved), tuple(findings)


def _proprietary_prefix(entry: PsbtEntry) -> bytes:
    if entry.key_type != PSBT_PROPRIETARY:
        raise PsbtGuardError("entry is not proprietary")
    try:
        length, off = read_compact_size(entry.key_data, 0)
    except BitcoinTxError as exc:
        raise PsbtGuardError(f"invalid proprietary PSBT key prefix: {exc}") from exc
    if length == 0 or off + length > len(entry.key_data):
        raise PsbtGuardError("invalid proprietary PSBT key identifier")
    prefix = entry.key_data[off:off + length]
    off += length
    # A proprietary subtype CompactSize must follow the identifier.
    try:
        _subtype, _ = read_compact_size(entry.key_data, off)
    except BitcoinTxError as exc:
        raise PsbtGuardError(f"invalid proprietary PSBT subtype: {exc}") from exc
    return prefix


def _field_policy_counts(psbt: ParsedPsbt, allowed_proprietary_prefixes: tuple[bytes, ...]) -> tuple[int, int, tuple[str, ...]]:
    unknown = 0
    proprietary = 0
    findings: list[str] = []
    groups = [("global", psbt.global_map, KNOWN_GLOBAL_TYPES)]
    groups += [(f"input[{i}]", m, KNOWN_INPUT_TYPES) for i, m in enumerate(psbt.input_maps)]
    groups += [(f"output[{i}]", m, KNOWN_OUTPUT_TYPES) for i, m in enumerate(psbt.output_maps)]
    for label, entries, known in groups:
        for e in entries:
            if e.key_type not in known:
                unknown += 1
                findings.append(f"{label} contains unreviewed PSBT field type 0x{e.key_type:x}")
            if e.key_type == PSBT_PROPRIETARY:
                proprietary += 1
                prefix = _proprietary_prefix(e)
                if prefix not in allowed_proprietary_prefixes:
                    findings.append(f"{label} contains unapproved proprietary PSBT namespace sha256={hashlib.sha256(prefix).hexdigest()}")
    return unknown, proprietary, tuple(findings)


def _dust_threshold_sat(script_type: str) -> int | None:
    # Conservative local relay-policy guard using widely deployed dust thresholds
    # at the conventional 3000 sat/kvB dust relay fee. This is policy, not consensus.
    return {
        "P2PKH": 546,
        "P2SH": 540,
        "P2WPKH": 294,
        "P2WSH": 330,
        "P2TR": 330,
        "P2MR": 330,
        "P2PK": 546,
        "P2MS": 546,
    }.get(script_type)


def _minimum_unsigned_vsize(tx: BitcoinTransaction) -> int:
    # The eventual signed transaction cannot have a lower vsize than its stripped
    # unsigned serialization. Using this as the denominator yields an upper bound
    # on the eventual feerate, suitable for fail-closed fee-burn policy.
    return len(tx.serialize(include_witness=False))


@dataclass(frozen=True)
class PsbtAuditReport:
    version: int
    txid: str
    network: str
    policy_state: CryptoPolicyState
    allowed: bool
    findings: tuple[str, ...]
    output_decisions: tuple[dict, ...]
    metadata_exposure: dict
    input_value_sat: int
    output_value_sat: int
    fee_sat: int
    fee_bps_of_input: int
    minimum_unsigned_vsize: int
    fee_rate_upper_bound_sat_vb: float
    address_reuse_output_indexes: tuple[int, ...]
    rbf_signaling_input_indexes: tuple[int, ...]
    dust_output_indexes: tuple[int, ...]
    op_return_output_indexes: tuple[int, ...]

    def to_dict(self) -> dict:
        out = asdict(self)
        out["policy_state"] = self.policy_state.value
        return out


def audit_psbt(
    raw: bytes | str,
    *,
    network: str,
    policy_state: CryptoPolicyState,
    pq_recovery_output_indexes: Iterable[int] = (),
    reject_global_xpub: bool = True,
    reject_unknown_fields: bool = True,
    reject_proprietary_fields: bool = True,
    allowed_proprietary_prefixes: Iterable[bytes] = (),
    max_fee_sat: int | None = None,
    max_fee_bps_of_input: int | None = None,
    max_fee_rate_upper_bound_sat_vb: float | None = None,
    reject_address_reuse: bool = False,
    reject_rbf: bool = False,
    reject_dust: bool = False,
    allow_op_return: bool = False,
    max_op_return_script_bytes: int = 83,
    allow_sighash_none: bool = False,
    allow_sighash_single: bool = False,
    allow_sighash_anyonecanpay: bool = False,
) -> PsbtAuditReport:
    psbt = parse_psbt(raw)
    tx = psbt.transaction
    resolved_inputs, provenance_findings = _validate_input_utxo_provenance(psbt)
    pq_indexes = set(pq_recovery_output_indexes)
    if any(i < 0 or i >= len(tx.outputs) for i in pq_indexes):
        raise PsbtGuardError("PQ recovery output index is outside PSBT outputs")

    findings: list[str] = list(provenance_findings)
    allowed_prefixes = tuple(bytes(x) for x in allowed_proprietary_prefixes)
    unknown_fields, proprietary_fields, field_findings = _field_policy_counts(psbt, allowed_prefixes)
    findings.extend(field_findings)
    unapproved_proprietary = 0
    for entries in (psbt.global_map, *psbt.input_maps, *psbt.output_maps):
        for e in entries:
            if e.key_type == PSBT_PROPRIETARY and _proprietary_prefix(e) not in allowed_prefixes:
                unapproved_proprietary += 1

    input_value_sat = sum(o.value_sat for o in resolved_inputs)
    output_value_sat = sum(o.value_sat for o in tx.outputs)
    fee_sat = input_value_sat - output_value_sat
    if fee_sat < 0:
        raise PsbtGuardError("PSBT outputs exceed resolved input value")
    fee_bps = (fee_sat * 10_000 // input_value_sat) if input_value_sat else 0
    minimum_vsize = _minimum_unsigned_vsize(tx)
    fee_rate_upper = fee_sat / minimum_vsize if minimum_vsize else float("inf")

    if max_fee_sat is not None:
        if not isinstance(max_fee_sat, int) or isinstance(max_fee_sat, bool) or max_fee_sat < 0:
            raise PsbtGuardError("max_fee_sat must be a non-negative integer")
        if fee_sat > max_fee_sat:
            findings.append(f"fee {fee_sat} sat exceeds configured cap {max_fee_sat} sat")
    else:
        findings.append("no absolute fee cap configured; fee is measured but not capped")
    if max_fee_bps_of_input is not None:
        if not isinstance(max_fee_bps_of_input, int) or isinstance(max_fee_bps_of_input, bool) or not 0 <= max_fee_bps_of_input <= 10_000:
            raise PsbtGuardError("max_fee_bps_of_input must be an integer from 0 through 10000")
        if fee_bps > max_fee_bps_of_input:
            findings.append(f"fee consumes {fee_bps} bps of input value, above cap {max_fee_bps_of_input}")
    if max_fee_rate_upper_bound_sat_vb is not None:
        if not isinstance(max_fee_rate_upper_bound_sat_vb, (int, float)) or isinstance(max_fee_rate_upper_bound_sat_vb, bool) or max_fee_rate_upper_bound_sat_vb < 0:
            raise PsbtGuardError("max_fee_rate_upper_bound_sat_vb must be non-negative")
        if fee_rate_upper > float(max_fee_rate_upper_bound_sat_vb):
            findings.append(
                f"fee-rate upper bound {fee_rate_upper:.3f} sat/vB exceeds cap {float(max_fee_rate_upper_bound_sat_vb):.3f}"
            )

    # Enforce strict sighash semantics even before any signature is present.
    for index, (m, prevout) in enumerate(zip(psbt.input_maps, resolved_inputs)):
        declared = _declared_sighash(m, input_index=index)
        if declared is None:
            continue
        taproot = classify_script_pubkey(prevout.script_pubkey) == "P2TR"
        try:
            enforce_sighash_policy(
                declared, taproot=taproot, allow_none=allow_sighash_none,
                allow_single=allow_sighash_single, allow_anyonecanpay=allow_sighash_anyonecanpay,
            )
        except SignaturePolicyError as exc:
            raise PsbtGuardError(f"input[{index}] sighash policy rejected PSBT: {exc}") from exc

    input_scripts = {o.script_pubkey for o in resolved_inputs}
    address_reuse_indexes = tuple(i for i, o in enumerate(tx.outputs) if o.script_pubkey in input_scripts)
    if address_reuse_indexes:
        findings.append(f"outputs reuse an input locking script/address: {list(address_reuse_indexes)}")

    rbf_indexes = tuple(i for i, txin in enumerate(tx.inputs) if txin.sequence < 0xFFFFFFFE)
    if rbf_indexes:
        findings.append(f"inputs signal opt-in replaceability by sequence: {list(rbf_indexes)}")

    dust_indexes: list[int] = []
    op_return_indexes: list[int] = []
    output_decisions: list[dict] = []
    for idx, out in enumerate(tx.outputs):
        script_type = classify_script_pubkey(out.script_pubkey)
        extra_reasons: list[str] = []
        extra_controls: list[str] = []
        if script_type == "OP_RETURN":
            op_return_indexes.append(idx)
            ok = bool(
                allow_op_return and out.value_sat == 0 and len(out.script_pubkey) <= max_op_return_script_bytes
                and network.strip().upper() not in {"MAINNET", "BITCOIN_MAINNET", "BTC_MAINNET"}
            )
            if out.value_sat != 0:
                extra_reasons.append("OP_RETURN output burns non-zero value")
            if len(out.script_pubkey) > max_op_return_script_bytes:
                extra_reasons.append("OP_RETURN script exceeds configured data-carrier bound")
            if not allow_op_return:
                extra_reasons.append("OP_RETURN is disabled at the signing boundary")
            if ok:
                extra_reasons.append("zero-value bounded OP_RETURN explicitly allowed on non-mainnet")
            extra_controls.append("EXPLICIT_DATA_CARRIER_POLICY")
            d_allowed = ok
            d_reasons = tuple(extra_reasons)
            d_controls = tuple(extra_controls)
        else:
            reused = idx in address_reuse_indexes and reject_address_reuse
            d = evaluate_new_output(
                ProposedOutput(
                    network=network, script_type=script_type, address_reused=reused,
                    has_pq_recovery_path=idx in pq_indexes,
                ),
                policy_state,
            )
            d_allowed = d.allowed
            d_reasons = d.reasons
            d_controls = d.required_controls

        threshold = _dust_threshold_sat(script_type)
        if threshold is not None and out.value_sat < threshold:
            dust_indexes.append(idx)
            extra_reasons.append(f"output is below local dust threshold {threshold} sat")
            extra_controls.append("DUST_OUTPUT_REJECT")
            if reject_dust:
                d_allowed = False
        if extra_reasons and script_type != "OP_RETURN":
            d_reasons = tuple(dict.fromkeys((*d_reasons, *extra_reasons)))
            d_controls = tuple(dict.fromkeys((*d_controls, *extra_controls)))

        output_decisions.append({
            "index": idx,
            "value_sat": out.value_sat,
            "script_type": script_type,
            "script_pubkey_sha256": hashlib.sha256(out.script_pubkey).hexdigest(),
            "address_reuse_detected": idx in address_reuse_indexes,
            "dust_threshold_sat": threshold,
            "allowed": d_allowed,
            "reasons": list(d_reasons),
            "required_controls": list(d_controls),
        })
        if not d_allowed:
            findings.append(f"output[{idx}] fails signing policy: {'; '.join(d_reasons)}")

    global_xpubs = _entries_of(psbt.global_map, PSBT_GLOBAL_XPUB)
    input_bip32 = sum(len(_entries_of(m, PSBT_IN_BIP32_DERIVATION)) for m in psbt.input_maps)
    output_bip32 = sum(len(_entries_of(m, PSBT_OUT_BIP32_DERIVATION)) for m in psbt.output_maps)
    input_tap_bip32 = sum(len(_entries_of(m, PSBT_IN_TAP_BIP32_DERIVATION)) for m in psbt.input_maps)
    output_tap_bip32 = sum(len(_entries_of(m, PSBT_OUT_TAP_BIP32_DERIVATION)) for m in psbt.output_maps)
    tap_key_sigs = sum(len(_entries_of(m, PSBT_IN_TAP_KEY_SIG)) for m in psbt.input_maps)
    tap_script_sigs = sum(len(_entries_of(m, PSBT_IN_TAP_SCRIPT_SIG)) for m in psbt.input_maps)
    partial_sigs = sum(len(_entries_of(m, PSBT_IN_PARTIAL_SIG)) for m in psbt.input_maps)
    musig_participants = sum(len(_entries_of(m, PSBT_IN_MUSIG2_PARTICIPANT_PUBKEYS)) for m in psbt.input_maps) + sum(len(_entries_of(m, PSBT_OUT_MUSIG2_PARTICIPANT_PUBKEYS)) for m in psbt.output_maps)
    musig_nonces = sum(len(_entries_of(m, PSBT_IN_MUSIG2_PUB_NONCE)) for m in psbt.input_maps)
    musig_partial = sum(len(_entries_of(m, PSBT_IN_MUSIG2_PARTIAL_SIG)) for m in psbt.input_maps)
    finalized = sum(bool(_entries_of(m, PSBT_IN_FINAL_SCRIPTSIG) or _entries_of(m, PSBT_IN_FINAL_SCRIPTWITNESS)) for m in psbt.input_maps)

    if global_xpubs:
        findings.append("PSBT carries global extended public key material; derivation/privacy scope is broadened")
    if reject_global_xpub and global_xpubs:
        findings.append("local signing-boundary policy rejects PSBT_GLOBAL_XPUB by default")

    mutable_after_signature = False
    if psbt.version == 2:
        mod = _singleton(psbt.global_map, PSBT_GLOBAL_TX_MODIFIABLE)
        mod_flags = mod.value[0] if mod else 0
        if (partial_sigs or tap_key_sigs or tap_script_sigs or musig_partial or finalized) and (mod_flags & 0x03):
            mutable_after_signature = True
            findings.append("PSBTv2 contains signatures/finalization data while inputs or outputs remain modifiable")

    taproot_outputs = [i for i, o in enumerate(tx.outputs) if classify_script_pubkey(o.script_pubkey) == "P2TR"]
    if taproot_outputs:
        findings.append(f"P2TR outputs expose x-only public keys for long periods under the current quantum-risk model: {taproot_outputs}")

    metadata = {
        "input_script_types": [classify_script_pubkey(o.script_pubkey) for o in resolved_inputs],
        "input_outpoints": [f"{txin.prev_txid}:{txin.vout}" for txin in tx.inputs],
        "input_values_sat": [o.value_sat for o in resolved_inputs],
        "input_script_pubkey_sha256": [hashlib.sha256(o.script_pubkey).hexdigest() for o in resolved_inputs],
        "global_xpub_count": len(global_xpubs),
        "global_xpub_key_fingerprints_sha256": [hashlib.sha256(e.key_data).hexdigest() for e in global_xpubs],
        "input_bip32_derivation_count": input_bip32,
        "output_bip32_derivation_count": output_bip32,
        "input_tap_bip32_derivation_count": input_tap_bip32,
        "output_tap_bip32_derivation_count": output_tap_bip32,
        "partial_signature_count": partial_sigs,
        "taproot_key_signature_count": tap_key_sigs,
        "taproot_script_signature_count": tap_script_sigs,
        "musig2_participant_field_count": musig_participants,
        "musig2_nonce_count": musig_nonces,
        "musig2_partial_signature_count": musig_partial,
        "finalized_input_count": finalized,
        "mutable_after_signature": mutable_after_signature,
        "unknown_field_count": unknown_fields,
        "proprietary_field_count": proprietary_fields,
        "unapproved_proprietary_field_count": unapproved_proprietary,
    }

    allowed = all(d["allowed"] for d in output_decisions)
    if reject_global_xpub and global_xpubs:
        allowed = False
    if reject_unknown_fields and unknown_fields:
        allowed = False
    if reject_proprietary_fields and unapproved_proprietary:
        allowed = False
    if mutable_after_signature:
        allowed = False
    if reject_address_reuse and address_reuse_indexes:
        allowed = False
    if reject_rbf and rbf_indexes:
        allowed = False
    if reject_dust and dust_indexes:
        allowed = False
    if max_fee_sat is not None and fee_sat > max_fee_sat:
        allowed = False
    if max_fee_bps_of_input is not None and fee_bps > max_fee_bps_of_input:
        allowed = False
    if max_fee_rate_upper_bound_sat_vb is not None and fee_rate_upper > float(max_fee_rate_upper_bound_sat_vb):
        allowed = False
    if allowed:
        findings.append("PSBT passes strict local pre-sign structure, signature, metadata, fee, mutability, and output-policy checks")
    return PsbtAuditReport(
        version=psbt.version, txid=tx.txid, network=network.strip().upper(), policy_state=policy_state,
        allowed=allowed, findings=tuple(findings), output_decisions=tuple(output_decisions),
        metadata_exposure=metadata, input_value_sat=input_value_sat, output_value_sat=output_value_sat,
        fee_sat=fee_sat, fee_bps_of_input=fee_bps, minimum_unsigned_vsize=minimum_vsize,
        fee_rate_upper_bound_sat_vb=fee_rate_upper, address_reuse_output_indexes=address_reuse_indexes,
        rbf_signaling_input_indexes=rbf_indexes, dust_output_indexes=tuple(dust_indexes),
        op_return_output_indexes=tuple(op_return_indexes),
    )
