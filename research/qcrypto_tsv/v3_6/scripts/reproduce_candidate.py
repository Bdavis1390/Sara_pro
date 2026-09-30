#!/usr/bin/env python3
"""Generate an attributable-independent-review receipt template from local reproduction."""
from __future__ import annotations
import argparse, hashlib, json, pathlib, platform, shutil, subprocess, sys
from datetime import datetime, timezone
ROOT=pathlib.Path(__file__).resolve().parents[1]

def file_hashes():
    out={}
    excluded = {
        'INDEPENDENT_REPRODUCTION_RECEIPT.json',
        'INTERNAL_REPRODUCTION_RECEIPT.json',
        'SHA256SUMS.txt',
        'REPRODUCE.stdout',
        'GENERATE_EVIDENCE.stdout',
    }
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.name not in excluded:
            out[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output',required=True); ap.add_argument('--reviewer',required=True); ap.add_argument('--organization',default='')
    a=ap.parse_args()
    cp=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],cwd=ROOT,text=True,capture_output=True)
    log=(cp.stdout or '')+(cp.stderr or '')
    receipt={
      'schema':'WS-QCRYPTO-INDEPENDENT-REPRODUCTION-RECEIPT-V3',
      'candidate_version':'v3.0',
      'reviewer':a.reviewer,'organization':a.organization,
      'generated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
      'python':sys.version,'platform':platform.platform(),
      'test_returncode':cp.returncode,'test_pass':cp.returncode==0,'test_count':log.count(' ... ok'),'test_log_sha256':hashlib.sha256(log.encode()).hexdigest(),
      'bitcoin_cli_available':bool(shutil.which('bitcoin-cli')),
      'openssl_available':bool(shutil.which('openssl')),
      'actual_pq_reproduction_requires_unskipped_openssl_tests':True,
      'live_bitcoin_core_interop_claim':False,
      'source_file_sha256':file_hashes(),
      'reviewer_attestation':'UNSIGNED_REVIEWER_STATEMENT_REQUIRED',
      'independent_validation_claim_ready':False,
      'claims_boundary':'Running this script alone does not constitute independent validation. The outside reviewer must authenticate the receipt and provide findings/deviations.'
    }
    pathlib.Path(a.output).write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('reproduction_tests:', 'PASS' if cp.returncode==0 else 'FAIL')
    print('receipt:', a.output)
    return cp.returncode
if __name__=='__main__': raise SystemExit(main())
