#!/usr/bin/env python3
"""Build a deterministic non-mainnet migration PSBT from an approved reservation JSON.

Input JSON format:
{
  "network":"SIGNET", "fee_sat":1000,
  "binding": {fields accepted by MigrationBatchBinding},
  "inputs":[{"txid":"...","vout":0,"value_sat":100000,"script_pubkey_hex":"..."}],
  "destination_address":"..."  // or destination_script_pubkey_hex
}

No signing, finalization, or broadcast occurs.
"""
from __future__ import annotations
import argparse, base64, json
from pathlib import Path
from worldshepherd_qcrypto_kms.migration_engine import MigrationBatchBinding
from worldshepherd_qcrypto_kms.migration_psbt import MigrationSpendInput, build_sweep_migration_psbt

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--request',required=True); ap.add_argument('--output',required=True); ap.add_argument('--report',required=True)
    a=ap.parse_args(); req=json.loads(Path(a.request).read_text())
    binding=MigrationBatchBinding(**req['binding'])
    inputs=tuple(MigrationSpendInput(**row) for row in req['inputs'])
    result=build_sweep_migration_psbt(inputs,network=req['network'],fee_sat=int(req['fee_sat']),binding=binding,destination_address=req.get('destination_address'),destination_script_pubkey_hex=req.get('destination_script_pubkey_hex'))
    Path(a.output).write_bytes(result.psbt)
    report=result.report(); report['psbt_base64_sha256_note']='PSBT bytes written separately; report contains psbt_sha256'
    Path(a.report).write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print('psbt_sha256:',report['psbt_sha256']); print('txid:',report['txid']); print('broadcast_performed: false')
    return 0
if __name__=='__main__': raise SystemExit(main())
