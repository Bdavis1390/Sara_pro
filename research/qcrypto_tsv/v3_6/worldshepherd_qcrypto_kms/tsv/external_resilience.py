"""Validation for v3.6 external resilience evidence."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib, json, re
from typing import Any, Mapping

HEX64=re.compile(r"^[0-9a-f]{64}$")
DOMAIN=b"WS-QCRYPTO-TSV-V3_6-EXTERNAL-RESILIENCE-BUNDLE-V1\x00"
REQUIRED_CASES={
    "PERSIST_FIRST":"ALLOW",
    "PERSIST_AFTER_RESTART":"ALLOW",
    "PERSIST_REPLAY_AFTER_RESTART":"DENY",
    "PRIMARY_PARTITION_FALLBACK":"ALLOW",
    "DUAL_PARTITION_CONFLICT":"DENY",
    "NO_HEALTHY_PROVIDER":"DENY",
    "CALENDAR_VALID":"ALLOW",
    "CALENDAR_STALE":"DENY",
    "CALENDAR_WRONG_PROVIDER":"DENY",
    "WRONG_PARENT":"DENY",
}


def _canon(v:Any)->bytes: return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def _sha(v:Any)->bool: return isinstance(v,str) and HEX64.fullmatch(v) is not None

@dataclass(frozen=True)
class ExternalResilienceValidation:
    decision:str
    errors:tuple[str,...]
    bundle_sha256:str|None
    case_count:int
    durable_state_sha256:str|None
    execution_target:str|None
    claims_label:str="EXTERNAL_RESILIENCE_VALIDATION_ONLY"
    def to_dict(self)->dict: return asdict(self)


def validate_external_resilience_bundle(bundle:Mapping[str,Any],*,expected_parent_v3_5_sha256:str,expected_resilience_core_sha256:str)->ExternalResilienceValidation:
    errors:list[str]=[]
    if bundle.get("schema")!="WS-QCRYPTO-TSV-V3_6-EXTERNAL-RESILIENCE-BUNDLE-V1": errors.append("SCHEMA_MISMATCH")
    claimed=bundle.get("bundle_sha256")
    material=dict(bundle); material.pop("bundle_sha256",None)
    computed=hashlib.sha256(DOMAIN+_canon(material)).hexdigest()
    if claimed!=computed: errors.append("BUNDLE_HASH_MISMATCH")
    parent=bundle.get("parent_binding") or {}
    if parent.get("v3_5_release_sha256")!=expected_parent_v3_5_sha256: errors.append("PARENT_V35_MISMATCH")
    if parent.get("v3_6_resilience_core_sha256")!=expected_resilience_core_sha256: errors.append("RESILIENCE_CORE_MISMATCH")
    target=bundle.get("execution_target") or {}
    if target.get("provider")!="Supabase Edge Functions": errors.append("UNEXPECTED_PROVIDER")
    if target.get("verify_jwt") is not True: errors.append("JWT_NOT_REQUIRED")
    if target.get("durable_store")!="Supabase Postgres": errors.append("DURABLE_STORE_NOT_SUPABASE_POSTGRES")
    rows=bundle.get("cases") if isinstance(bundle.get("cases"),list) else []
    by={}
    for row in rows:
        if not isinstance(row,Mapping): errors.append("CASE_ROW_INVALID"); continue
        name=str(row.get("name") or "")
        if name in by or not name: errors.append("CASE_NAME_INVALID_OR_DUPLICATE"); continue
        by[name]=row
        if not _sha(row.get("receipt_sha256")): errors.append(f"CASE_RECEIPT_INVALID:{name}")
    for name,decision in REQUIRED_CASES.items():
        row=by.get(name)
        if row is None: errors.append(f"CASE_MISSING:{name}")
        elif row.get("decision")!=decision: errors.append(f"CASE_DECISION_MISMATCH:{name}")
    if bundle.get("claims_label")!="EXTERNAL_SYNTHETIC_RESILIENCE_EVIDENCE_ONLY_NOT_LIVE_MARKET_DATA_OR_INDEPENDENT_CERTIFICATION": errors.append("CLAIMS_LABEL_CHANGED")
    neg=bundle.get("negative_claims") or {}
    for key in (
        "licensed_market_data_used","authoritative_market_calendar_used","qualified_delivery_provider_used",
        "independent_provider_execution_completed","independent_third_party_certification","live_tsv_deployment",
        "sec_approval_established","legal_compliance_established","real_value_moved",
    ):
        if neg.get(key) is not False: errors.append(f"NEGATIVE_CLAIM_NOT_FALSE:{key}")
    dstate=bundle.get("durable_state_sha256")
    if not _sha(dstate): errors.append("DURABLE_STATE_SHA256_INVALID")
    target_label=None
    if target.get("project_ref") and target.get("function_slug"):
        target_label=f"Supabase:{target['project_ref']}:{target['function_slug']}:v{target.get('function_version')}"
    return ExternalResilienceValidation("ALLOW" if not errors else "DENY",tuple(errors),claimed if _sha(claimed) else None,len(rows),dstate if _sha(dstate) else None,target_label)
