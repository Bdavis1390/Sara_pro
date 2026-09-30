"""Bitcoin Core RPC/CLI interoperability cross-checks.

This module never starts a node, signs, finalizes, broadcasts, or touches mainnet.
It queries an operator-controlled REGTEST/SIGNET/TESTNET instance and records
version-gated PSBT/descriptor capabilities before comparing Core's interpretation
with Worldshepherd's prepared signing package.
"""
from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Sequence


class BitcoinCoreInteropError(RuntimeError):
    pass


_ALLOWED_NETWORKS = {"REGTEST": "-regtest", "SIGNET": "-signet", "TESTNET": "-testnet", "TESTNET4": "-testnet4"}

# Bitcoin Core version integer floors documented by the Core BIP support table.
_CAPABILITY_FLOORS = {
    "descriptors": 170000,
    "taproot_psbt_bip371": 240000,
    "musig2_psbt_bip373": 300000,
    "psbt_v2_bip370": 320000,
}


def core_capabilities(version: int) -> dict[str, bool]:
    if not isinstance(version, int) or version < 0:
        raise BitcoinCoreInteropError("invalid Bitcoin Core version integer")
    return {name: version >= floor for name, floor in _CAPABILITY_FLOORS.items()}


@dataclass(frozen=True)
class CoreInteropReport:
    network: str
    bitcoin_core_version: int
    bitcoin_core_subversion: str
    capabilities: dict[str, bool]
    required_capabilities: tuple[str, ...]
    capability_mismatches: tuple[str, ...]
    decoded_txid: str
    local_txid: str
    txid_match: bool
    descriptor_checks: tuple[dict, ...]
    analyzepsbt: dict
    pass_interop: bool

    def to_dict(self) -> dict:
        return {
            "schema": "WS-BITCOIN-CORE-INTEROP-V2",
            "network": self.network,
            "bitcoin_core_version": self.bitcoin_core_version,
            "bitcoin_core_subversion": self.bitcoin_core_subversion,
            "capabilities": self.capabilities,
            "required_capabilities": list(self.required_capabilities),
            "capability_mismatches": list(self.capability_mismatches),
            "decoded_txid": self.decoded_txid,
            "local_txid": self.local_txid,
            "txid_match": self.txid_match,
            "descriptor_checks": list(self.descriptor_checks),
            "analyzepsbt": self.analyzepsbt,
            "pass_interop": self.pass_interop,
            "signing_performed": False,
            "finalization_performed": False,
            "broadcast_performed": False,
        }


class BitcoinCoreCLI:
    def __init__(self, *, network: str, executable: str = "bitcoin-cli", extra_args: Sequence[str] = (), runner: Callable | None = None):
        n = network.strip().upper()
        if n not in _ALLOWED_NETWORKS:
            raise BitcoinCoreInteropError("Bitcoin Core interoperability is restricted to REGTEST/SIGNET/TESTNET/TESTNET4")
        self.network = n
        self.executable = executable
        self.extra_args = tuple(extra_args)
        self._runner = runner or subprocess.run

    def available(self) -> bool:
        return bool(shutil.which(self.executable))

    def rpc(self, method: str, *params: object) -> object:
        if not method or not method.replace("_", "").isalnum():
            raise BitcoinCoreInteropError("invalid RPC method name")
        args = [self.executable, _ALLOWED_NETWORKS[self.network], *self.extra_args, method]
        for p in params:
            if isinstance(p, (dict, list, bool, int, float)):
                args.append(json.dumps(p, separators=(",", ":")))
            elif p is None:
                args.append("null")
            else:
                args.append(str(p))
        try:
            cp = self._runner(args, check=False, capture_output=True, text=True, timeout=30)
        except FileNotFoundError as exc:
            raise BitcoinCoreInteropError("bitcoin-cli is not installed") from exc
        except subprocess.TimeoutExpired as exc:
            raise BitcoinCoreInteropError("bitcoin-cli RPC timed out") from exc
        if cp.returncode != 0:
            err = (cp.stderr or cp.stdout or "bitcoin-cli failed").strip()
            raise BitcoinCoreInteropError(err[:1000])
        out = cp.stdout.strip()
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return out


def _required_capabilities(prepared: object, descriptors: Sequence[str]) -> tuple[str, ...]:
    req: list[str] = []
    audit = getattr(prepared, "audit", None)
    if getattr(audit, "version", 0) == 2:
        req.append("psbt_v2_bip370")
    meta = getattr(audit, "metadata_exposure", {}) or {}
    if meta.get("input_tap_bip32_derivation_count") or meta.get("output_tap_bip32_derivation_count") or meta.get("taproot_key_signature_count") or meta.get("taproot_script_signature_count"):
        req.append("taproot_psbt_bip371")
    if meta.get("musig2_participant_field_count") or meta.get("musig2_nonce_count") or meta.get("musig2_partial_signature_count"):
        req.append("musig2_psbt_bip373")
    if descriptors:
        req.append("descriptors")
    return tuple(dict.fromkeys(req))


def cross_check_prepared_with_core(prepared: object, raw_psbt: bytes, *, cli: BitcoinCoreCLI, descriptors: Sequence[str] = ()) -> CoreInteropReport:
    if getattr(prepared, "network", None) != cli.network:
        raise BitcoinCoreInteropError("prepared signing network does not match Bitcoin Core network")
    psbt_b64 = base64.b64encode(bytes(raw_psbt)).decode("ascii")
    net = cli.rpc("getnetworkinfo")
    if not isinstance(net, dict) or not isinstance(net.get("version"), int):
        raise BitcoinCoreInteropError("unexpected getnetworkinfo response")
    version = net["version"]
    caps = core_capabilities(version)
    required = _required_capabilities(prepared, descriptors)
    mismatches = tuple(name for name in required if not caps.get(name, False))
    if mismatches:
        raise BitcoinCoreInteropError(
            f"Bitcoin Core {version} lacks version-gated capabilities required by this package: {', '.join(mismatches)}"
        )

    decoded = cli.rpc("decodepsbt", psbt_b64)
    if not isinstance(decoded, dict) or not isinstance(decoded.get("tx"), dict):
        raise BitcoinCoreInteropError("unexpected decodepsbt response")
    txid = decoded["tx"].get("txid")
    if not isinstance(txid, str):
        raise BitcoinCoreInteropError("Bitcoin Core decodepsbt response omitted txid")
    analysis = cli.rpc("analyzepsbt", psbt_b64)
    if not isinstance(analysis, dict):
        raise BitcoinCoreInteropError("unexpected analyzepsbt response")
    checks: list[dict] = []
    all_desc_ok = True
    for descriptor in descriptors:
        info = cli.rpc("getdescriptorinfo", descriptor)
        if not isinstance(info, dict) or not isinstance(info.get("descriptor"), str):
            raise BitcoinCoreInteropError("unexpected getdescriptorinfo response")
        has_private = bool(info.get("hasprivatekeys", False))
        checksum = info["descriptor"].rsplit("#", 1)[-1] if "#" in info["descriptor"] else None
        ok = not has_private and isinstance(checksum, str) and len(checksum) == 8
        all_desc_ok &= ok
        checks.append({
            "input_sha256": hashlib.sha256(descriptor.encode()).hexdigest(),
            "core_descriptor": info["descriptor"],
            "core_checksum": checksum,
            "has_private_keys": has_private,
            "isrange": bool(info.get("isrange", False)),
            "issolvable": bool(info.get("issolvable", False)),
            "pass": ok,
        })
    local_txid = getattr(prepared, "txid", "")
    match = txid.lower() == str(local_txid).lower()
    return CoreInteropReport(
        network=cli.network,
        bitcoin_core_version=version,
        bitcoin_core_subversion=str(net.get("subversion", "")),
        capabilities=caps,
        required_capabilities=required,
        capability_mismatches=mismatches,
        decoded_txid=txid,
        local_txid=str(local_txid),
        txid_match=match,
        descriptor_checks=tuple(checks),
        analyzepsbt=analysis,
        pass_interop=bool(match and all_desc_ok and not mismatches),
    )
