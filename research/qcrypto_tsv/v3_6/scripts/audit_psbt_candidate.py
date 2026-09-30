#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worldshepherd_qcrypto_kms.bitcoin_quantum_policy import CryptoPolicyState
from worldshepherd_qcrypto_kms.signing_gate import SigningGateError, prepare_psbt_signing


def load_psbt(path: pathlib.Path) -> bytes:
    raw = path.read_bytes()
    if raw.startswith(b"psbt\xff"):
        return raw
    try:
        text = raw.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise SystemExit("PSBT file is neither binary PSBT nor ASCII hex/base64") from exc
    try:
        decoded = bytes.fromhex(text)
        if decoded.startswith(b"psbt\xff"):
            return decoded
    except ValueError:
        pass
    try:
        decoded = base64.b64decode(text, validate=True)
    except Exception as exc:
        raise SystemExit("PSBT ASCII content is neither valid hex nor strict base64") from exc
    if not decoded.startswith(b"psbt\xff"):
        raise SystemExit("decoded content does not have PSBT magic")
    return decoded


def main() -> int:
    ap = argparse.ArgumentParser(description="Strict Worldshepherd Bitcoin PSBT pre-sign audit")
    ap.add_argument("--psbt-file", required=True)
    ap.add_argument("--network", required=True, choices=["SIGNET", "TESTNET4", "REGTEST"])
    ap.add_argument("--policy-state", required=True, choices=[x.value for x in CryptoPolicyState])
    ap.add_argument("--policy-epoch", required=True)
    ap.add_argument("--max-fee-sat", required=True, type=int)
    ap.add_argument("--max-fee-bps", type=int, default=1000)
    ap.add_argument("--max-fee-rate-upper-bound", type=float, default=1000.0)
    ap.add_argument("--authorization-nonce", required=True)
    ap.add_argument("--expires-at", required=True, help="offset-aware ISO-8601 release-intent expiry")
    ap.add_argument("--pq-recovery-output", action="append", type=int, default=[])
    ap.add_argument("--descriptor", action="append", default=[])
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    raw = load_psbt(pathlib.Path(args.psbt_file))
    try:
        prepared = prepare_psbt_signing(
            raw,
            network=args.network,
            policy_state=CryptoPolicyState(args.policy_state),
            policy_epoch=args.policy_epoch,
            max_fee_sat=args.max_fee_sat,
            max_fee_bps_of_input=args.max_fee_bps,
            max_fee_rate_upper_bound_sat_vb=args.max_fee_rate_upper_bound,
            authorization_nonce=args.authorization_nonce,
            expires_at=args.expires_at,
            pq_recovery_output_indexes=args.pq_recovery_output,
            descriptors=args.descriptor,
        )
    except SigningGateError as exc:
        print(json.dumps({"allowed": False, "error": str(exc)}, indent=2))
        return 2
    payload = prepared.to_dict()
    text = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    if args.output:
        pathlib.Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
