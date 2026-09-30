#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from worldshepherd_qcrypto_kms.source_integrity import build_source_manifest, verify_source_manifest
from worldshepherd_qcrypto_kms.tsv.evidence import canonical_json, sha256_hex
from worldshepherd_qcrypto_kms.tsv.external_adversarial import validate_external_adversarial_bundle
from worldshepherd_qcrypto_kms.tsv.issuer_delivery import IssuerDeliveryReceipt
from worldshepherd_qcrypto_kms.tsv.market_data_adapter import MarketDataMessage
from worldshepherd_qcrypto_kms.tsv.operational_runtime import authorize_operational_tsv
from worldshepherd_qcrypto_kms.tsv.runtime import authorize_bundle
from worldshepherd_qcrypto_kms.tsv_qcrypto_binding import bind_tsv_authorization

PARENT_QCRYPTO_V32="e0c7c968f6d8f31278d677c881d3dea4173452ffd4b8ba07850d70970fc654bc"
PARENT_INTEGRATED_V34="806db617532dc8840dca3f39504efa4cd78f5b4312005d730e5a73e4b54fffd8"
PQ_RECEIPT="79a124693b6c959ea9e1cf43d8fcd2e4bdf5309b562a502cec793f286fd090d3"
EXTERNAL_V34_BUNDLE="b3773256881b1690587378d651d4d637bdc3c9d581ba204905e4675852d16625"
EXTERNAL_V35_ADVERSARIAL="551ca894c536219189a554517cf9126e8d168ab19cb96fc5320ee03a2bb79c95"
CONTROL_CORE="4b4e1c85b80b8ad5b9326cbacec0a8754dcc80ec98cf2b2e7bc917cd921d8341"
EVAL=datetime(2026,9,19,1,5,0,tzinfo=timezone.utc)


def ph(s:str)->str:
    return hashlib.sha256(s.encode()).hexdigest()


def main()->int:
    evidence=ROOT/'evidence'; evidence.mkdir(exist_ok=True)
    cp=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],cwd=ROOT,text=True,capture_output=True)
    log=(cp.stdout or '')+(cp.stderr or '')
    (evidence/'LOCAL_TEST_V3_5.log').write_text(log,encoding='utf-8')
    test_count=log.count(' ... ok')

    pkg=ROOT/'worldshepherd_qcrypto_kms'
    manifest=build_source_manifest(pkg)
    integrity=verify_source_manifest(pkg,manifest)
    (ROOT/'SOURCE_INTEGRITY_MANIFEST_V3_5.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    (evidence/'SOURCE_INTEGRITY_REPORT_V3_5.json').write_text(json.dumps(integrity,sort_keys=True,indent=2)+'\n')

    external=json.loads((evidence/'TSV_EXTERNAL_ADVERSARIAL_BUNDLE_V3_5.json').read_text())
    extval=validate_external_adversarial_bundle(external,expected_parent_v3_4_sha256=PARENT_INTEGRATED_V34,expected_control_core_sha256=CONTROL_CORE)
    (evidence/'TSV_EXTERNAL_ADVERSARIAL_VALIDATION_V3_5.json').write_text(json.dumps(extval.to_dict(),sort_keys=True,indent=2)+'\n')

    state=json.loads((evidence/'tsv'/'examples_pass_v3_3.json').read_text())
    notice=json.loads((evidence/'tsv'/'examples_notice.json').read_text())
    notice_sha=sha256_hex(canonical_json(notice))
    market=[
      MarketDataMessage('PRIMARY_LISTING_EXCHANGE','sim-primary','ABC',100,'TRADING',EVAL-timedelta(seconds=2),EVAL-timedelta(seconds=1),ph('primary-100'),True,'v35-session'),
      MarketDataMessage('SIP','sim-sip','ABC',200,'TRADING',EVAL-timedelta(seconds=2),EVAL-timedelta(seconds=1),ph('sip-200'),True,'v35-session'),
    ]
    registry={'PRIMARY_LISTING_EXCHANGE':{'sim-primary'},'SIP':{'sim-sip'},'LULD_PLAN':{'sim-luld'}}
    delivered=datetime(2026,9,18,0,0,tzinfo=timezone.utc)
    issuer=IssuerDeliveryReceipt(
      symbol='ABC',issuer_id='issuer-synthetic-1',notice_sha256=notice_sha,delivery_channel='REGISTERED_EMAIL',
      delivery_provider_id='synthetic-provider',delivered_at=delivered,provider_recorded_at=delivered+timedelta(minutes=1),
      provider_receipt_id='synthetic-receipt-v35',provider_payload_sha256=ph('issuer-provider-payload-v35'),verified=True,
    )
    operational=authorize_operational_tsv(
      state,notice,now=EVAL,symbol='ABC',market_messages=market,market_source_registry=registry,require_market_adapter=True,
      issuer_delivery_receipt=issuer,issuer_notice_sha256=notice_sha,require_issuer_delivery=True,
    )
    (evidence/'TSV_OPERATIONAL_AUTHORIZATION_V3_5.json').write_text(json.dumps(operational.to_dict(),sort_keys=True,indent=2)+'\n')

    base=authorize_bundle(state,notice,now=EVAL)
    binding=bind_tsv_authorization(
      base,package_root=pkg,source_manifest=manifest,
      parent_qcrypto_zip_sha256=PARENT_QCRYPTO_V32,parent_tsv_zip_sha256=PARENT_INTEGRATED_V34,
      external_pq_receipt_sha256=PQ_RECEIPT,external_tsv_execution_bundle_sha256=EXTERNAL_V34_BUNDLE,
      external_tsv_adversarial_bundle_sha256=EXTERNAL_V35_ADVERSARIAL,tsv_control_core_sha256=CONTROL_CORE,
    )
    (evidence/'TSV_QCRYPTO_BINDING_V3_5.json').write_text(json.dumps(binding.to_dict(),sort_keys=True,indent=2)+'\n')

    summary={
      'schema':'WS-QCRYPTO-TSV-V3_5-EVIDENCE-SUMMARY','candidate_version':'v3.5',
      'generated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'fixed_evaluation_time':EVAL.isoformat().replace('+00:00','Z'),
      'test_returncode':cp.returncode,'test_count':test_count,'test_pass':cp.returncode==0,
      'source_integrity_satisfied':integrity['satisfied'],'source_manifest_sha256':manifest['manifest_sha256'],
      'parent_integrated_v3_4_sha256':PARENT_INTEGRATED_V34,'parent_qcrypto_v3_2_sha256':PARENT_QCRYPTO_V32,
      'control_core_sha256':CONTROL_CORE,'external_adversarial_validation':extval.decision,
      'external_adversarial_bundle_sha256':extval.bundle_sha256,'external_adversarial_pass_receipt_sha256':extval.pass_receipt_sha256,
      'external_adversarial_negative_case_count':extval.negative_case_count,'operational_decision':operational.decision,
      'operational_runtime_sha256':operational.runtime_sha256,'market_batch_sha256':operational.market_data_batch['batch_sha256'],
      'issuer_delivery_receipt_sha256':operational.issuer_delivery['receipt_sha256'],'tsv_qcrypto_binding_sha256':binding.binding_sha256,
      'claims':{
        'external_synthetic_adversarial_execution_performed':True,'licensed_sip_feed_connected':False,
        'live_primary_exchange_feed_connected':False,'live_luld_feed_connected':False,'qualified_issuer_delivery_attestation':False,
        'digital_signature_or_trusted_timestamp_for_delivery':False,'sec_approval':False,'legal_opinion':False,
        'registered_exchange_or_ats':False,'live_tsv_deployment':False,'real_value_trading_authorized':False,
        'mainnet_or_broadcast_authorized':False,'independent_validation':False,
      }
    }
    (evidence/'EVIDENCE_SUMMARY_V3_5.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    ok=cp.returncode==0 and integrity['satisfied'] and extval.decision=='ALLOW' and operational.decision=='ALLOW'
    return 0 if ok else 1

if __name__=='__main__': raise SystemExit(main())
