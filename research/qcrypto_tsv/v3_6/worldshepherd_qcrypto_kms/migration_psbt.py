"""Construct deterministic non-mainnet wallet-migration PSBTs.

This closes the gap between a migration manifest and an actually signable Bitcoin
artifact.  The builder intentionally creates PSBTv0 only, never signs/finalizes,
never broadcasts, and never accepts MAINNET.  It is designed for sweeping selected
SegWit UTXOs from long-exposure or legacy custody locations into an explicitly
approved hash-hidden destination (P2WPKH/P2WSH) on REGTEST/SIGNET/TESTNET4.

Moving to a hash-hidden classical output reduces *long-exposure* public-key risk; it
does not make Bitcoin post-quantum secure and does not eliminate short-exposure risk
when the destination is eventually spent.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Sequence

from .address_codec import address_to_scriptpubkey
from .bitcoin_tx import BitcoinTransaction, TxInput, TxOutput, classify_script_pubkey, encode_compact_size
from .migration_engine import MigrationBatchBinding, MigrationEngineError


class MigrationPsbtError(RuntimeError):
    pass


_ALLOWED_NETWORKS = {"SIGNET", "REGTEST", "TESTNET4"}
_ALLOWED_SOURCE_TYPES = {"P2WPKH", "P2WSH", "P2TR"}
_HASH_HIDDEN_DESTINATION_TYPES = {"P2WPKH", "P2WSH"}
_MAGIC = b"psbt\xff"


def _kv(key_type: int, value: bytes, key_data: bytes = b"") -> bytes:
    if not 0 <= key_type <= 255:
        raise MigrationPsbtError("PSBT key type out of range")
    key = bytes([key_type]) + bytes(key_data)
    return encode_compact_size(len(key)) + key + encode_compact_size(len(value)) + value


def _psbt_map(*entries: bytes) -> bytes:
    return b"".join(entries) + b"\x00"


def _witness_utxo(value_sat: int, script_pubkey: bytes) -> bytes:
    return int(value_sat).to_bytes(8, "little") + encode_compact_size(len(script_pubkey)) + script_pubkey


@dataclass(frozen=True)
class MigrationSpendInput:
    txid: str
    vout: int
    value_sat: int
    script_pubkey_hex: str
    sequence: int = 0xFFFFFFFE

    def normalized(self) -> dict:
        txid = self.txid.lower()
        if len(txid) != 64 or any(c not in "0123456789abcdef" for c in txid):
            raise MigrationPsbtError("migration input txid must be 32-byte hex")
        if not isinstance(self.vout, int) or isinstance(self.vout, bool) or self.vout < 0 or self.vout > 0xFFFFFFFF:
            raise MigrationPsbtError("migration input vout is invalid")
        if not isinstance(self.value_sat, int) or isinstance(self.value_sat, bool) or self.value_sat <= 0:
            raise MigrationPsbtError("migration input value_sat must be positive")
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool) or not 0 <= self.sequence <= 0xFFFFFFFF:
            raise MigrationPsbtError("migration input sequence is invalid")
        try:
            script = bytes.fromhex(self.script_pubkey_hex)
        except ValueError as exc:
            raise MigrationPsbtError("migration input script_pubkey_hex is invalid") from exc
        if not script:
            raise MigrationPsbtError("migration input script_pubkey must not be empty")
        script_type = classify_script_pubkey(script)
        if script_type not in _ALLOWED_SOURCE_TYPES:
            raise MigrationPsbtError(
                "migration PSBT builder accepts only SegWit source UTXOs because witness_utxo alone is insufficiently safe for legacy inputs"
            )
        return {
            "txid": txid,
            "vout": self.vout,
            "value_sat": self.value_sat,
            "script_pubkey": script,
            "script_type": script_type,
            "sequence": self.sequence,
        }


@dataclass(frozen=True)
class MigrationPsbtBuildResult:
    psbt: bytes
    unsigned_tx: bytes
    txid: str
    input_total_sat: int
    output_value_sat: int
    fee_sat: int
    destination_script_type: str
    destination_script_sha256: str
    source_script_types: tuple[str, ...]
    binding_sha256: str
    manifest_sha256: str
    short_exposure_risk_remains: bool = True
    bitcoin_consensus_pq_security_established: bool = False

    def report(self) -> dict:
        out = asdict(self)
        out.pop("psbt")
        out.pop("unsigned_tx")
        out["schema"] = "WS-QCRYPTO-MIGRATION-PSBT-BUILD-V1"
        out["psbt_sha256"] = hashlib.sha256(self.psbt).hexdigest()
        out["unsigned_tx_sha256"] = hashlib.sha256(self.unsigned_tx).hexdigest()
        return out


def build_sweep_migration_psbt(
    inputs: Sequence[MigrationSpendInput],
    *,
    network: str,
    fee_sat: int,
    binding: MigrationBatchBinding,
    destination_address: str | None = None,
    destination_script_pubkey_hex: str | None = None,
    tx_version: int = 2,
    locktime: int = 0,
) -> MigrationPsbtBuildResult:
    """Build a deterministic PSBTv0 sweep bound to a reserved migration batch.

    Exactly one hash-hidden destination output is created.  Change is intentionally
    avoided: the destination receives ``sum(inputs)-fee``.  That makes destination
    substitution and hidden extra outputs easier to detect in the later signing gate.
    """
    net = network.strip().upper()
    if net not in _ALLOWED_NETWORKS:
        raise MigrationPsbtError("migration PSBT construction is restricted to explicit non-mainnet networks")
    if net != binding.network.strip().upper():
        raise MigrationPsbtError("migration binding network does not match builder network")
    if not inputs:
        raise MigrationPsbtError("migration sweep requires at least one input")
    if not isinstance(fee_sat, int) or isinstance(fee_sat, bool) or fee_sat < 0:
        raise MigrationPsbtError("fee_sat must be a non-negative integer")
    if fee_sat > binding.max_fee_sat:
        raise MigrationPsbtError("migration fee exceeds reserved batch maximum")
    if (destination_address is None) == (destination_script_pubkey_hex is None):
        raise MigrationPsbtError("specify exactly one migration destination address or script")
    if destination_address is not None:
        try:
            destination_script = address_to_scriptpubkey(destination_address, network=net)
        except Exception as exc:
            raise MigrationPsbtError(str(exc)) from exc
    else:
        try:
            destination_script = bytes.fromhex(destination_script_pubkey_hex or "")
        except ValueError as exc:
            raise MigrationPsbtError("destination_script_pubkey_hex is invalid") from exc
        if not destination_script:
            raise MigrationPsbtError("destination script must not be empty")
    destination_type = classify_script_pubkey(destination_script)
    if destination_type not in _HASH_HIDDEN_DESTINATION_TYPES:
        raise MigrationPsbtError(
            "migration destination must be P2WPKH or P2WSH so public-key material remains hash-hidden while unspent"
        )
    allowed_dest = {x.strip().upper() for x in binding.allowed_destination_script_types}
    if destination_type.upper() not in allowed_dest:
        raise MigrationPsbtError("destination script type is not allowed by the reserved migration binding")

    rows = [i.normalized() for i in inputs]
    outpoints = tuple(sorted(f"{r['txid']}:{r['vout']}" for r in rows))
    expected = tuple(sorted(binding.canonical_dict()["outpoints"]))
    if outpoints != expected:
        raise MigrationPsbtError("supplied migration inputs do not exactly match the reserved batch outpoints")
    if len(set(outpoints)) != len(outpoints):
        raise MigrationPsbtError("duplicate migration input outpoint")
    total = sum(int(r["value_sat"]) for r in rows)
    output_value = total - fee_sat
    if output_value <= 0:
        raise MigrationPsbtError("migration fee consumes the entire input value")

    tx = BitcoinTransaction(
        version=tx_version,
        inputs=tuple(
            TxInput(prev_txid=r["txid"], vout=int(r["vout"]), script_sig=b"", sequence=int(r["sequence"]))
            for r in rows
        ),
        outputs=(TxOutput(value_sat=output_value, script_pubkey=destination_script),),
        locktime=locktime,
        segwit=False,
    )
    unsigned = tx.serialize()
    psbt = bytearray(_MAGIC)
    psbt += _psbt_map(_kv(0x00, unsigned))
    for r in rows:
        psbt += _psbt_map(_kv(0x01, _witness_utxo(int(r["value_sat"]), bytes(r["script_pubkey"]))))
    psbt += _psbt_map()  # one output map
    raw = bytes(psbt)

    return MigrationPsbtBuildResult(
        psbt=raw,
        unsigned_tx=unsigned,
        txid=tx.txid,
        input_total_sat=total,
        output_value_sat=output_value,
        fee_sat=fee_sat,
        destination_script_type=destination_type,
        destination_script_sha256=hashlib.sha256(destination_script).hexdigest(),
        source_script_types=tuple(str(r["script_type"]) for r in rows),
        binding_sha256=binding.binding_sha256,
        manifest_sha256=binding.manifest_sha256.lower(),
    )
