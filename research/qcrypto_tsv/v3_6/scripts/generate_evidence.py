#!/usr/bin/env python3
"""Regenerate non-secret v3.2 local evidence.

This script does not authorize Bitcoin broadcast, touch mainnet, create production
keys, or turn a local test result into an independent-validation claim.
"""
from __future__ import annotations
import hashlib, json, pathlib, shutil, subprocess, sys
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from worldshepherd_qcrypto_kms.source_integrity import build_source_manifest, verify_source_manifest


def main()->int:
    evidence=ROOT/'evidence'; evidence.mkdir(exist_ok=True)
    cp=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],cwd=ROOT,text=True,capture_output=True)
    log=(cp.stdout or '')+(cp.stderr or '')
    (evidence/'LOCAL_TEST_V3_2.log').write_text(log,encoding='utf-8')
    count=log.count(' ... ok')
    manifest=build_source_manifest(ROOT/'worldshepherd_qcrypto_kms')
    integrity=verify_source_manifest(ROOT/'worldshepherd_qcrypto_kms',manifest)
    (ROOT/'SOURCE_INTEGRITY_MANIFEST_V3_2.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    (evidence/'SOURCE_INTEGRITY_REPORT_V3_2.json').write_text(json.dumps(integrity,sort_keys=True,indent=2)+'\n')
    openssl=shutil.which('openssl')
    sig_list=''
    if openssl:
        probe=subprocess.run([openssl,'list','-signature-algorithms'],capture_output=True,text=True,check=False)
        sig_list=probe.stdout or ''
    report={
      'schema':'WS-QCRYPTO-V3_2-LOCAL-EVIDENCE-SUMMARY',
      'candidate_version':'v3.2',
      'generated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
      'test_returncode':cp.returncode,'test_count':count,'test_pass':cp.returncode==0,
      'source_integrity_satisfied':integrity['satisfied'],'source_manifest_sha256':manifest['manifest_sha256'],
      'openssl_available':bool(openssl),'openssl_ml_dsa_65_advertised':'ML-DSA-65' in sig_list,'openssl_slh_dsa_sha2_128s_advertised':'SLH-DSA-SHA2-128s' in sig_list,
      'bitcoin_cli_available':bool(shutil.which('bitcoin-cli')),
      'live_bitcoin_core_interop_claim':False,'live_aws_kms_claim':False,
      'mainnet_authority':False,'transaction_broadcast_authorized':False,'bitcoin_consensus_pq_security_established':False,
      'independent_validation_claim':False,
    }
    out=evidence/'LOCAL_EVIDENCE_SUMMARY_V3_2.json'; out.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if cp.returncode==0 and integrity['satisfied'] else 1
if __name__=='__main__': raise SystemExit(main())
