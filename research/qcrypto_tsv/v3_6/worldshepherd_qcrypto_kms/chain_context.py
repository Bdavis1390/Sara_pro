"""Bind a signing decision to live non-mainnet Bitcoin chain state.

The local PSBT can prove what UTXO it *claims* to spend, but not that the UTXO is
still unspent or sufficiently confirmed.  This module asks an operator-controlled
Bitcoin Core instance for chain tip and gettxout state, verifies the exact amount and
locking script committed by the PSBT, and emits a deterministic chain-context hash
that can be included in the signing policy.

It is read-only: no wallet, signing, finalization, or broadcast RPCs are used.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from .bitcoin_core_interop import BitcoinCoreCLI, BitcoinCoreInteropError
from .bitcoin_quantum_policy import CryptoPolicyState
from .psbt_guard import audit_psbt


class ChainContextError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChainContextPolicy:
    minimum_confirmations: int = 1
    max_tip_age_seconds: int = 7200
    require_not_initial_block_download: bool = True

    def canonical_dict(self) -> dict:
        if not isinstance(self.minimum_confirmations, int) or isinstance(self.minimum_confirmations, bool) or self.minimum_confirmations < 0:
            raise ChainContextError("minimum_confirmations must be a non-negative integer")
        if not isinstance(self.max_tip_age_seconds, int) or isinstance(self.max_tip_age_seconds, bool) or self.max_tip_age_seconds <= 0:
            raise ChainContextError("max_tip_age_seconds must be positive")
        return asdict(self)

    @property
    def policy_sha256(self) -> str:
        raw=json.dumps(self.canonical_dict(),sort_keys=True,separators=(",", ":")).encode()
        return hashlib.sha256(b"WS-QCRYPTO-CHAIN-CONTEXT-POLICY-V1\x00"+raw).hexdigest()


def _btc_to_sat(value: Any) -> int:
    try:
        sat = Decimal(str(value)) * Decimal(100_000_000)
    except (InvalidOperation, ValueError) as exc:
        raise ChainContextError("Bitcoin Core returned an invalid UTXO amount") from exc
    if sat != sat.to_integral_value():
        raise ChainContextError("Bitcoin Core UTXO amount is not satoshi-exact")
    return int(sat)


def _report_hash(report_without_hash: dict) -> str:
    body=json.dumps(report_without_hash,sort_keys=True,separators=(",", ":")).encode()
    return hashlib.sha256(b"WS-QCRYPTO-CHAIN-CONTEXT-V1\x00"+body).hexdigest()


def verify_psbt_chain_context_with_core(
    raw_psbt: bytes | str,
    *,
    network: str,
    cli: BitcoinCoreCLI,
    policy: ChainContextPolicy = ChainContextPolicy(),
    now: dt.datetime | None = None,
) -> dict:
    net=network.strip().upper()
    if net not in {"REGTEST","SIGNET","TESTNET4"} or cli.network != net:
        raise ChainContextError("chain-context verification requires the same explicit non-mainnet network as Bitcoin Core")
    cfg=policy.canonical_dict()
    # ECDSA_ALLOWED avoids imposing quantum-output policy here.  This pass is only
    # resolving exact input UTXO provenance; the real signing gate applies policy.
    try:
        audit=audit_psbt(raw_psbt,network=net,policy_state=CryptoPolicyState.ECDSA_ALLOWED,reject_global_xpub=False,reject_unknown_fields=False,reject_proprietary_fields=False,reject_address_reuse=False,reject_rbf=False,reject_dust=False)
    except Exception as exc:
        raise ChainContextError(f"PSBT cannot be chain-context checked: {exc}") from exc
    meta=audit.metadata_exposure
    outpoints=list(meta.get("input_outpoints", []))
    values=list(meta.get("input_values_sat", []))
    script_hashes=list(meta.get("input_script_pubkey_sha256", []))
    if not (len(outpoints)==len(values)==len(script_hashes)>0):
        raise ChainContextError("PSBT audit omitted input provenance required for chain-context verification")
    try:
        chain=cli.rpc("getblockchaininfo")
    except BitcoinCoreInteropError as exc:
        raise ChainContextError(str(exc)) from exc
    if not isinstance(chain,dict):
        raise ChainContextError("unexpected getblockchaininfo response")
    reported_chain=str(chain.get("chain", "")).upper()
    acceptable={"REGTEST":{"REGTEST"},"SIGNET":{"SIGNET"},"TESTNET4":{"TESTNET4"}}[net]
    if reported_chain not in acceptable:
        raise ChainContextError("Bitcoin Core chain does not match requested signing network")
    if cfg["require_not_initial_block_download"] and bool(chain.get("initialblockdownload", True)):
        raise ChainContextError("Bitcoin Core is still in initial block download")
    current=(now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    try:
        median_time=int(chain["mediantime"])
        best_hash=str(chain["bestblockhash"]).lower()
        height=int(chain["blocks"])
    except Exception as exc:
        raise ChainContextError("Bitcoin Core chain-tip response lacks required fields") from exc
    if len(best_hash)!=64 or any(c not in "0123456789abcdef" for c in best_hash):
        raise ChainContextError("Bitcoin Core bestblockhash is invalid")
    tip_age=max(0,int(current.timestamp())-median_time)
    if tip_age>cfg["max_tip_age_seconds"]:
        raise ChainContextError("Bitcoin Core chain tip is too stale for signing authorization")

    rows=[]
    for index,(outpoint,expected_value,expected_script_hash) in enumerate(zip(outpoints,values,script_hashes)):
        txid,vout_text=outpoint.split(":",1)
        vout=int(vout_text)
        try:
            row=cli.rpc("gettxout",txid,vout,True)
        except BitcoinCoreInteropError as exc:
            raise ChainContextError(str(exc)) from exc
        if row is None:
            raise ChainContextError(f"input[{index}] is spent, missing, or not in the selected Bitcoin Core UTXO view")
        if not isinstance(row,dict):
            raise ChainContextError("unexpected gettxout response")
        confirmations=int(row.get("confirmations",-1))
        if confirmations<cfg["minimum_confirmations"]:
            raise ChainContextError(f"input[{index}] has insufficient confirmations")
        value_sat=_btc_to_sat(row.get("value"))
        if value_sat!=int(expected_value):
            raise ChainContextError(f"input[{index}] value differs between PSBT and Bitcoin Core")
        spk=row.get("scriptPubKey") or {}
        if not isinstance(spk,dict) or not isinstance(spk.get("hex"),str):
            raise ChainContextError("gettxout omitted scriptPubKey.hex")
        try:
            script=bytes.fromhex(spk["hex"])
        except ValueError as exc:
            raise ChainContextError("gettxout returned invalid scriptPubKey hex") from exc
        if hashlib.sha256(script).hexdigest()!=str(expected_script_hash).lower():
            raise ChainContextError(f"input[{index}] locking script differs between PSBT and Bitcoin Core")
        rows.append({"index":index,"outpoint":outpoint,"confirmations":confirmations,"value_sat":value_sat,"script_pubkey_sha256":hashlib.sha256(script).hexdigest()})
    report={
        "schema":"WS-QCRYPTO-CHAIN-CONTEXT-V1",
        "network":net,
        "txid":audit.txid,
        "bestblockhash":best_hash,
        "height":height,
        "mediantime":median_time,
        "tip_age_seconds":tip_age,
        "initial_block_download":bool(chain.get("initialblockdownload",False)),
        "inputs":rows,
        "policy_sha256":policy.policy_sha256,
        "satisfied":True,
        "read_only_rpc_methods":["getblockchaininfo","gettxout"],
    }
    report["chain_context_sha256"]=_report_hash(report)
    return report


def validate_chain_context_report(report: dict, *, network: str, txid: str) -> str:
    if not isinstance(report,dict) or report.get("satisfied") is not True:
        raise ChainContextError("chain-context report is absent or unsatisfied")
    if str(report.get("network","")).upper()!=network.strip().upper() or str(report.get("txid","")).lower()!=txid.lower():
        raise ChainContextError("chain-context report is bound to a different network or transaction")
    supplied=str(report.get("chain_context_sha256","")).lower()
    body=dict(report); body.pop("chain_context_sha256",None)
    expected=_report_hash(body)
    if supplied!=expected:
        raise ChainContextError("chain-context report hash is invalid")
    return expected
