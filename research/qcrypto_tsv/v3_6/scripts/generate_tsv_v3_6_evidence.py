#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import date, datetime, time, timedelta, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from worldshepherd_qcrypto_kms.source_integrity import build_source_manifest, verify_source_manifest
from worldshepherd_qcrypto_kms.tsv.durable_market_state import DurableCursorStore, apply_message_durably
from worldshepherd_qcrypto_kms.tsv.evidence import canonical_json, sha256_hex
from worldshepherd_qcrypto_kms.tsv.external_resilience import validate_external_resilience_bundle
from worldshepherd_qcrypto_kms.tsv.issuer_delivery import IssuerDeliveryReceipt
from worldshepherd_qcrypto_kms.tsv.market_data_adapter import MarketDataMessage
from worldshepherd_qcrypto_kms.tsv.operational_runtime import authorize_operational_tsv
from worldshepherd_qcrypto_kms.tsv.provider_resilience import ProviderHealth, ProviderRoute, CalendarEvidence
from worldshepherd_qcrypto_kms.tsv.runtime import authorize_bundle
from worldshepherd_qcrypto_kms.tsv_qcrypto_binding import bind_tsv_authorization

PARENT_QCRYPTO_V32='e0c7c968f6d8f31278d677c881d3dea4173452ffd4b8ba07850d70970fc654bc'
PARENT_INTEGRATED_V35='9b41b15e58898fe9f8fa836b258b13e93e860d20ea2c19e76693bfb3e3948653'
PQ_RECEIPT='79a124693b6c959ea9e1cf43d8fcd2e4bdf5309b562a502cec793f286fd090d3'
EXTERNAL_V34='b3773256881b1690587378d651d4d637bdc3c9d581ba204905e4675852d16625'
EXTERNAL_V35='551ca894c536219189a554517cf9126e8d168ab19cb96fc5320ee03a2bb79c95'
CONTROL_V35='4b4e1c85b80b8ad5b9326cbacec0a8754dcc80ec98cf2b2e7bc917cd921d8341'
EXTERNAL_V36='ebc3b80d92ec8afca9be7c4265811358d41fbfeddd7f016ef5ef04a1fe2732a5'
CORE_V36='b6920cfa2fb8609991b623ceabe61b8b1c0d432cb293a13082fba8eab1977dfa'
EVAL=datetime(2026,9,19,2,35,0,tzinfo=timezone.utc)

def ph(s:str)->str: return hashlib.sha256(s.encode()).hexdigest()

def main()->int:
    evidence=ROOT/'evidence'; evidence.mkdir(exist_ok=True)
    cp=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],cwd=ROOT,text=True,capture_output=True)
    log=(cp.stdout or '')+(cp.stderr or '')
    (evidence/'LOCAL_TEST_V3_6.log').write_text(log,encoding='utf-8')
    test_count=log.count(' ... ok')

    pkg=ROOT/'worldshepherd_qcrypto_kms'
    manifest=build_source_manifest(pkg)
    integrity=verify_source_manifest(pkg,manifest)
    (ROOT/'SOURCE_INTEGRITY_MANIFEST_V3_6.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    (evidence/'SOURCE_INTEGRITY_REPORT_V3_6.json').write_text(json.dumps(integrity,sort_keys=True,indent=2)+'\n')

    ext=json.loads((evidence/'TSV_EXTERNAL_RESILIENCE_BUNDLE_V3_6.json').read_text())
    extval=validate_external_resilience_bundle(ext,expected_parent_v3_5_sha256=PARENT_INTEGRATED_V35,expected_resilience_core_sha256=CORE_V36)
    (evidence/'TSV_EXTERNAL_RESILIENCE_VALIDATION_V3_6.json').write_text(json.dumps(extval.to_dict(),sort_keys=True,indent=2)+'\n')

    # Local restart-survivable cursor demonstration.
    reg={'PRIMARY_LISTING_EXCHANGE':{'sim-primary'}}
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/'cursor.json'
        m1=MarketDataMessage('PRIMARY_LISTING_EXCHANGE','sim-primary','ABC',10,'TRADING',EVAL-timedelta(seconds=3),EVAL-timedelta(seconds=2),ph('v36-local-10'),True,'restart-local')
        m2=MarketDataMessage('PRIMARY_LISTING_EXCHANGE','sim-primary','ABC',11,'TRADING',EVAL-timedelta(seconds=2),EVAL-timedelta(seconds=1),ph('v36-local-11'),True,'restart-local')
        a=apply_message_durably(DurableCursorStore(path),m1,expected_symbol='ABC',now=EVAL,source_registry=reg)
        b=apply_message_durably(DurableCursorStore(path),m2,expected_symbol='ABC',now=EVAL,source_registry=reg)
        replay=apply_message_durably(DurableCursorStore(path),m1,expected_symbol='ABC',now=EVAL,source_registry=reg)
        durable={'first':a.to_dict(),'after_restart':b.to_dict(),'replay_after_restart':replay.to_dict(),'final_state':DurableCursorStore(path).load().to_dict()}
    (evidence/'TSV_LOCAL_DURABLE_CURSOR_V3_6.json').write_text(json.dumps(durable,sort_keys=True,indent=2)+'\n')

    state=json.loads((evidence/'tsv'/'examples_pass_v3_3.json').read_text())
    notice=json.loads((evidence/'tsv'/'examples_notice.json').read_text())
    notice_sha=sha256_hex(canonical_json(notice))
    market=[
      MarketDataMessage('PRIMARY_LISTING_EXCHANGE','sim-primary','ABC',300,'TRADING',EVAL-timedelta(seconds=2),EVAL-timedelta(seconds=1),ph('primary-300'),True,'v36-session'),
      MarketDataMessage('SIP','sim-sip','ABC',400,'TRADING',EVAL-timedelta(seconds=2),EVAL-timedelta(seconds=1),ph('sip-400'),True,'v36-session'),
    ]
    market_reg={'PRIMARY_LISTING_EXCHANGE':{'sim-primary'},'SIP':{'sim-sip'},'LULD_PLAN':{'sim-luld'}}
    delivered=datetime(2026,9,18,0,0,tzinfo=timezone.utc)
    issuer=IssuerDeliveryReceipt('ABC','issuer-synthetic-1',notice_sha,'REGISTERED_EMAIL','synthetic-provider',delivered,delivered+timedelta(minutes=1),'synthetic-receipt-v36',ph('issuer-v36'),True)
    provider_route=ProviderRoute('SIP','sip-a',('sip-b',))
    provider_health=[
      ProviderHealth('SIP','sip-a',False,EVAL-timedelta(seconds=2),'partition-main',True),
      ProviderHealth('SIP','sip-b',True,EVAL-timedelta(seconds=1),'partition-main',True),
    ]
    provider_reg={'SIP':{'sip-a','sip-b'}}
    calendar=CalendarEvidence('calendar-a','synthetic-market-calendar',date(2026,9,19),True,time(13,30),time(20,0),EVAL-timedelta(days=1),ph('calendar-v36'),True)
    operational=authorize_operational_tsv(
      state,notice,now=EVAL,symbol='ABC',market_messages=market,market_source_registry=market_reg,require_market_adapter=True,
      issuer_delivery_receipt=issuer,issuer_notice_sha256=notice_sha,require_issuer_delivery=True,
      provider_route=provider_route,provider_health=provider_health,provider_registry=provider_reg,require_provider_resilience=True,
      calendar_evidence=calendar,calendar_provider_registry={'calendar-a'},require_calendar_evidence=True,
    )
    (evidence/'TSV_OPERATIONAL_AUTHORIZATION_V3_6.json').write_text(json.dumps(operational.to_dict(),sort_keys=True,indent=2)+'\n')

    base=authorize_bundle(state,notice,now=EVAL)
    binding=bind_tsv_authorization(
      base,package_root=pkg,source_manifest=manifest,parent_qcrypto_zip_sha256=PARENT_QCRYPTO_V32,parent_tsv_zip_sha256=PARENT_INTEGRATED_V35,
      external_pq_receipt_sha256=PQ_RECEIPT,external_tsv_execution_bundle_sha256=EXTERNAL_V34,
      external_tsv_adversarial_bundle_sha256=EXTERNAL_V35,tsv_control_core_sha256=CONTROL_V35,
      external_tsv_resilience_bundle_sha256=EXTERNAL_V36,tsv_resilience_core_sha256=CORE_V36,
    )
    (evidence/'TSV_QCRYPTO_BINDING_V3_6.json').write_text(json.dumps(binding.to_dict(),sort_keys=True,indent=2)+'\n')

    floot=json.loads((evidence/'FLOOT_SECOND_PROVIDER_VALIDATION_V3_6.json').read_text())
    floot_ok=(
      floot.get('provider')=='Floot' and floot.get('source_bundle_sha256')==EXTERNAL_V36 and
      floot.get('positive',{}).get('decision')=='ALLOW' and floot.get('positive',{}).get('http_status')==200 and
      floot.get('positive',{}).get('verification_receipt_sha256')=='2a044c101f2e795b2637fe71089e0d75407aa909973fb1a50592545cc8417d6e' and
      all(row.get('decision')=='DENY' for row in floot.get('negative_cases',[])) and
      floot.get('claims',{}).get('independently_administered') is False and
      floot.get('claims',{}).get('third_party_certification') is False
    )
    final_binding={
      'schema':'WS-QCRYPTO-TSV-V3_6-FINAL-EVIDENCE-BINDING-V1',
      'qcrypto_tsv_binding_sha256':binding.binding_sha256,
      'source_manifest_sha256':binding.qcrypto_source_manifest_sha256,
      'supabase_resilience_bundle_sha256':EXTERNAL_V36,
      'supabase_durable_state_sha256':extval.durable_state_sha256,
      'floot_validation_record_sha256':floot['record_sha256'],
      'floot_verification_receipt_sha256':floot['positive']['verification_receipt_sha256'],
      'provider_domains':['Supabase','Floot'],
      'independently_administered':False,
      'third_party_certification':False,
      'claims_label':'MULTI_PROVIDER_SOFTWARE_EVIDENCE_BINDING_ONLY_NOT_REGULATORY_OR_THIRD_PARTY_CERTIFICATION',
    }
    final_binding['final_evidence_binding_sha256']=hashlib.sha256(
      b'WS-QCRYPTO-TSV-V3_6-FINAL-EVIDENCE-BINDING-V1\0'+
      json.dumps(final_binding,sort_keys=True,separators=(',',':')).encode()
    ).hexdigest()
    (evidence/'FINAL_EVIDENCE_BINDING_V3_6.json').write_text(json.dumps(final_binding,sort_keys=True,indent=2)+'\n')

    summary={
      'schema':'WS-QCRYPTO-TSV-V3_6-EVIDENCE-SUMMARY','candidate_version':'v3.6','generated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
      'fixed_evaluation_time':EVAL.isoformat().replace('+00:00','Z'),'test_returncode':cp.returncode,'test_count':test_count,'test_pass':cp.returncode==0,
      'source_integrity_satisfied':integrity['satisfied'],'source_manifest_sha256':manifest['manifest_sha256'],
      'parent_integrated_v3_5_sha256':PARENT_INTEGRATED_V35,'parent_qcrypto_v3_2_sha256':PARENT_QCRYPTO_V32,
      'resilience_core_sha256':CORE_V36,'external_resilience_validation':extval.decision,'external_resilience_bundle_sha256':extval.bundle_sha256,
      'external_durable_state_sha256':extval.durable_state_sha256,'external_resilience_case_count':extval.case_count,
      'local_durable_restart_first':a.decision,'local_durable_restart_second':b.decision,'local_durable_replay':replay.decision,
      'operational_decision':operational.decision,'operational_runtime_sha256':operational.runtime_sha256,
      'provider_failover_selected':operational.provider_failover['selected_provider_id'] if operational.provider_failover else None,
      'calendar_decision':operational.calendar_evidence['decision'] if operational.calendar_evidence else None,
      'tsv_qcrypto_binding_sha256':binding.binding_sha256,
      'floot_second_provider_validation': 'ALLOW' if floot_ok else 'DENY',
      'floot_validation_record_sha256':floot['record_sha256'],
      'floot_verification_receipt_sha256':floot['positive']['verification_receipt_sha256'],
      'final_evidence_binding_sha256':final_binding['final_evidence_binding_sha256'],
      'external_provider_domains':['Supabase','Floot'],
      'claims':{
        'external_durable_postgres_state_executed':True,'external_restart_sequence_continuity_executed':True,
        'external_synthetic_provider_failover_executed':True,'external_synthetic_partition_failure_executed':True,
        'external_synthetic_calendar_evidence_executed':True,'licensed_market_data_connected':False,
        'authoritative_market_calendar_connected':False,'qualified_delivery_provider_connected':False,
        'second_external_provider_software_validation_executed':True,'independently_administered_validation':False,
        'independent_third_party_certification':False,'sec_approval':False,'legal_opinion':False,
        'registered_exchange_or_ats':False,'live_tsv_deployment':False,'real_value_trading_authorized':False,
      }
    }
    (evidence/'EVIDENCE_SUMMARY_V3_6.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    ok=cp.returncode==0 and integrity['satisfied'] and extval.decision=='ALLOW' and floot_ok and operational.decision=='ALLOW' and a.decision=='ALLOW' and b.decision=='ALLOW' and replay.decision=='DENY'
    return 0 if ok else 1

if __name__=='__main__': raise SystemExit(main())
