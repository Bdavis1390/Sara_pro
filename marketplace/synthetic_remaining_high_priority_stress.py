#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

TARGET_CASES = {
  "WS-MKT-003": {
    "organization":"Airbus / former Spirit AeroSystems sites",
    "cases":[
      ("clean_work_transfer",{},True),
      ("stale_transferred_configuration",{"config_current":False},False),
      ("missing_tool_custody",{"evidence_complete":False},False),
      ("unknown_part_or_process_source",{"source_known":False},False),
      ("unapproved_work_transfer_change",{"approval_valid":False},False),
      ("invalid_release_authority",{"authority_valid":False},False),
      ("contradictory_site_records",{"contradiction_free":False},False),
      ("segregation_of_duties_conflict",{"segregation_ok":False},False),
      ("unverified_restore_after_transfer",{"restore_verified":False},False)
    ]
  },
  "WS-MKT-020": {
    "organization":"Serve Robotics / Diligent / Vayu / Vebu",
    "cases":[
      ("clean_robot_integration",{},True),
      ("robot_software_hardware_mismatch",{"config_current":False},False),
      ("missing_acquired_component_provenance",{"source_known":False},False),
      ("missing_privacy_or_use_case_evidence",{"evidence_complete":False},False),
      ("unapproved_model_or_software_change",{"approval_valid":False},False),
      ("invalid_operational_release_authority",{"authority_valid":False},False),
      ("contradictory_acquisition_records",{"contradiction_free":False},False),
      ("role_access_conflict",{"segregation_ok":False},False),
      ("unverified_clean_environment_restore",{"restore_verified":False},False)
    ]
  },
  "WS-MKT-021": {
    "organization":"Pioneer Power Solutions",
    "cases":[
      ("clean_erp_source_interface",{},True),
      ("stale_interface_mapping",{"config_current":False},False),
      ("unknown_source_system",{"source_known":False},False),
      ("missing_reconciliation_evidence",{"evidence_complete":False},False),
      ("unapproved_erp_change",{"approval_valid":False},False),
      ("invalid_privileged_authority",{"authority_valid":False},False),
      ("contradictory_source_records",{"contradiction_free":False},False),
      ("segregation_of_duties_conflict",{"segregation_ok":False},False),
      ("unverified_restore",{"restore_verified":False},False)
    ]
  },
  "WS-MKT-027": {
    "organization":"VSE Corporation / PAG / NorthStar / Aero 3",
    "cases":[
      ("clean_mro_work_package",{},True),
      ("stale_repair_configuration",{"config_current":False},False),
      ("unknown_part_or_repair_source",{"source_known":False},False),
      ("incomplete_work_package_evidence",{"evidence_complete":False},False),
      ("unapproved_repair_or_process_change",{"approval_valid":False},False),
      ("invalid_return_to_service_authority",{"authority_valid":False},False),
      ("contradictory_cross_site_records",{"contradiction_free":False},False),
      ("inspection_release_role_conflict",{"segregation_ok":False},False),
      ("unverified_recovery_of_evidence_store",{"restore_verified":False},False)
    ]
  },
  "WS-MKT-016": {
    "organization":"BOXABL Inc.",
    "cases":[
      ("clean_module_manufacturing_record",{},True),
      ("stale_module_configuration",{"config_current":False},False),
      ("unknown_material_or_component_source",{"source_known":False},False),
      ("missing_inspection_or_inventory_evidence",{"evidence_complete":False},False),
      ("unapproved_manufacturing_change",{"approval_valid":False},False),
      ("invalid_release_authority",{"authority_valid":False},False),
      ("contradictory_inventory_records",{"contradiction_free":False},False),
      ("role_access_conflict",{"segregation_ok":False},False),
      ("unverified_restore",{"restore_verified":False},False)
    ]
  }
}

BASE={
  "config_current":True,
  "source_known":True,
  "evidence_complete":True,
  "approval_valid":True,
  "authority_valid":True,
  "contradiction_free":True,
  "segregation_ok":True,
  "restore_verified":True
}

def evaluate(r):
    return all([
      r["config_current"],r["source_known"],r["evidence_complete"],r["approval_valid"],
      r["authority_valid"],r["contradiction_free"],r["segregation_ok"],r["restore_verified"]
    ])

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output',required=True); a=ap.parse_args()
    fixtures=[]; results=[]; by_target={}
    for tid,spec in TARGET_CASES.items():
        passed=0
        for name,mods,expected in spec['cases']:
            rec=dict(BASE); rec.update(mods); rec.update({'target_id':tid,'organization':spec['organization'],'case':name})
            fixtures.append(rec)
            actual=evaluate(rec)
            ok=(actual==expected)
            passed+=int(ok)
            results.append({'target_id':tid,'case':name,'expected':'accept' if expected else 'reject','actual':'accept' if actual else 'reject','pass':ok})
        by_target[tid]={'fixture_count':len(spec['cases']),'pass_count':passed}
    total=len(fixtures); passed=sum(1 for x in results if x['pass'])
    report={
      'schema':'WS-MARKETPLACE-REMAINING-HIGH-PRIORITY-SYNTHETIC-STRESS-V1',
      'result':'PASS' if passed==total else 'FAIL',
      'target_count':len(TARGET_CASES),
      'fixture_count':total,
      'pass_count':passed,
      'by_target':by_target,
      'fixtures_sha256':digest(fixtures),
      'results_sha256':digest(results),
      'external_gate_updates':{tid:'none' for tid in TARGET_CASES},
      'contact_gate_effect':'NONE',
      'claims_boundary':'Synthetic fixtures test encoded fail-closed evidence-control behavior for five remaining high-priority target patterns only. They do not measure target systems, product quality, safety, compliance, remediation effect, customer interest or probability of success.'
    }
    Path(a.output).parent.mkdir(parents=True,exist_ok=True); Path(a.output).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2)); raise SystemExit(0 if report['result']=='PASS' else 1)
if __name__=='__main__': main()
