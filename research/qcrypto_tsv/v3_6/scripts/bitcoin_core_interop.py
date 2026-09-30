#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from worldshepherd_qcrypto_kms.bitcoin_core_interop import BitcoinCoreCLI, BitcoinCoreInteropError, cross_check_prepared_with_core
from worldshepherd_qcrypto_kms.bitcoin_quantum_policy import CryptoPolicyState
from worldshepherd_qcrypto_kms.signing_gate import prepare_psbt_signing


def load_psbt(path: Path) -> bytes:
    data = path.read_bytes()
    if data.startswith(b"psbt\xff"):
        return data
    text = data.decode().strip()
    try:
        raw = bytes.fromhex(text)
        if raw.startswith(b"psbt\xff"):
            return raw
    except ValueError:
        pass
    raw = base64.b64decode(text, validate=True)
    if not raw.startswith(b"psbt\xff"):
        raise ValueError("file is not binary, hex, or base64 PSBT")
    return raw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--psbt-file", required=True)
    ap.add_argument("--network", choices=["REGTEST","SIGNET","TESTNET","TESTNET4"], required=True)
    ap.add_argument("--max-fee-sat", type=int, required=True)
    ap.add_argument("--policy-state", choices=[x.value for x in CryptoPolicyState], default="ECDSA_ALLOWED")
    ap.add_argument("--policy-epoch", required=True)
    ap.add_argument("--authorization-nonce", required=True)
    ap.add_argument("--expires-at", required=True)
    ap.add_argument("--max-fee-bps", type=int, default=1000)
    ap.add_argument("--max-fee-rate-upper-bound", type=float, default=1000.0)
    ap.add_argument("--descriptor", action="append", default=[])
    ap.add_argument("--bitcoin-cli", default="bitcoin-cli")
    ap.add_argument("--rpc-arg", action="append", default=[])
    args = ap.parse_args()
    raw = load_psbt(Path(args.psbt_file))
    prepared = prepare_psbt_signing(
        raw, network=args.network, policy_state=CryptoPolicyState(args.policy_state),
        policy_epoch=args.policy_epoch, max_fee_sat=args.max_fee_sat,
        max_fee_bps_of_input=args.max_fee_bps,
        max_fee_rate_upper_bound_sat_vb=args.max_fee_rate_upper_bound,
        authorization_nonce=args.authorization_nonce, expires_at=args.expires_at,
        descriptors=args.descriptor,
    )
    cli = BitcoinCoreCLI(network=args.network, executable=args.bitcoin_cli, extra_args=args.rpc_arg)
    try:
        report = cross_check_prepared_with_core(prepared, raw, cli=cli, descriptors=args.descriptor)
    except BitcoinCoreInteropError as exc:
        print(json.dumps({"schema":"WS-BITCOIN-CORE-INTEROP-V2","pass_interop":False,"blocked":True,"reason":str(exc),"broadcast_performed":False}, indent=2))
        return 2
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.pass_interop else 1

if __name__ == "__main__":
    raise SystemExit(main())
