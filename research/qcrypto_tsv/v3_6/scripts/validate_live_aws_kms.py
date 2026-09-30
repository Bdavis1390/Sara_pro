#!/usr/bin/env python3
"""Live AWS KMS integration validator for a synthetic non-transaction message.

This script never constructs a BTC/ETH transaction, never broadcasts, and never
accepts an asset amount, destination, wallet seed, or private key. A real KMS Sign
operation requires the explicit --authorize-synthetic-sign token. Production mode
also requires an operator-selected persistent journal directory so an ambiguous
Sign cannot be accidentally retried after process restart.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, pathlib
from datetime import datetime, timezone

from worldshepherd_qcrypto_kms import (
    AwsKmsMlDsa65Provider,
    FileOperationJournal,
    build_production_kms_client,
    provider_operation_id,
)

AUTH="YES_SYNTHETIC_NONTRANSACTION_SIGN"
MESSAGE=b"Worldshepherd-QCRYPTO-live-AWS-KMS-integration-evidence-v1"
CONTEXT=b"WS-QCRYPTO-AWS-KMS-LIVE-INTEGRATION-V1"

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--region', required=True)
    ap.add_argument('--key-id', required=True)
    ap.add_argument('--journal-dir', required=True, help='Persistent local directory for one-shot KMS operation state')
    ap.add_argument('--output', required=True)
    ap.add_argument('--authorize-synthetic-sign', default='')
    args=ap.parse_args()

    journal=FileOperationJournal(args.journal_dir)
    client=build_production_kms_client(args.region)
    provider=AwsKmsMlDsa65Provider(
        kms_client=client,key_id=args.key_id,region=args.region,
        fips_endpoint_requested=True,production_profile=True,
        operation_journal=journal,
    )
    evidence={
      'schema':'WS-QCRYPTO-LIVE-AWS-KMS-INTEGRATION-EVIDENCE-V1',
      'generated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
      'descriptor':provider.descriptor.to_dict(),
      'journal_dir_sha256':hashlib.sha256(str(pathlib.Path(args.journal_dir).resolve()).encode()).hexdigest(),
      'synthetic_nontransaction_message_sha256':hashlib.sha256(MESSAGE).hexdigest(),
      'transaction_serialized':False,'transaction_broadcast':False,'mainnet_authority':False,'real_value_moved':False,
      'private_key_exported':False,'federal_compliance_established':False,'end_to_end_pq_crypto_established':False,
      'synthetic_sign_performed':False,
    }
    if args.authorize_synthetic_sign:
        if args.authorize_synthetic_sign != AUTH:
            raise SystemExit('invalid synthetic-sign authorization token')
        op=provider_operation_id(key_arn=provider.key_handle,message=MESSAGE,context=CONTEXT)
        result=provider.begin_sign(op,MESSAGE,CONTEXT)
        raw=base64.urlsafe_b64decode(result.signature_b64url + '='*(-len(result.signature_b64url)%4))
        if not provider.verify_with_kms(message=MESSAGE,context=CONTEXT,signature=raw):
            raise SystemExit('AWS KMS Verify did not confirm synthetic signature')
        evidence.update({
          'synthetic_sign_performed':True,
          'provider_operation_id':op,
          'aws_request_id':result.aws_request_id,
          'signature_sha256':hashlib.sha256(raw).hexdigest(),
          'kms_verify_pass':True,
        })
    pathlib.Path(args.output).write_text(json.dumps(evidence,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('live_aws_kms_descriptor: PASS')
    print('synthetic_sign_performed:', evidence['synthetic_sign_performed'])
    return 0
if __name__=='__main__': raise SystemExit(main())
