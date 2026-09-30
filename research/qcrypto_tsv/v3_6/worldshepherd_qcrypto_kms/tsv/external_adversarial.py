"""Validate the externally executed v3.5 adversarial TSV evidence bundle.

The bundle proves only that a hosted synthetic reproducer executed the listed
software controls and negative cases.  It does not prove access to licensed
market data, legal sufficiency of issuer delivery, or SEC compliance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping

HEX64=re.compile(r"^[0-9a-f]{64}$")
DOMAIN=b"WS-QCRYPTO-TSV-V3_5-EXTERNAL-ADVERSARIAL-BUNDLE-V1\x00"
EXPECTED_PASS={
    "PARENT_V34_BINDING","CONTROL_CORE_BINDING","MARKET_STREAM_PRESENT",
    "MARKET_STREAM_SEQUENCE_AND_FRESHNESS","MARKET_STATUS_CLEAR","ISSUER_DELIVERY_AND_WAIT",
}
EXPECTED_FAIL={
    "MARKET_STALE":"MARKET_FRESHNESS_CLOCK",
    "MARKET_SEQUENCE_GAP":"MARKET_SEQUENCE_GAP",
    "MARKET_REPLAY":"MARKET_SEQUENCE_REPLAY_OR_REORDER",
    "MARKET_EQUIVOCATION":"MARKET_SEQUENCE_EQUIVOCATION",
    "MARKET_CONFLICT":"MARKET_STATUS_CONFLICT",
    "MARKET_UNREGISTERED_SOURCE":"MARKET_SOURCE_IDENTITY",
    "RESUME_QUORUM_INCOMPLETE":"RESUME_QUORUM",
    "ISSUER_NOTICE_DIGEST_MISMATCH":"ISSUER_NOTICE_DIGEST",
    "ISSUER_WAIT_SHORT":"ISSUER_30_DAY_WAIT",
    "ISSUER_OBJECTION":"ISSUER_OBJECTION_HOLD",
    "WRONG_PARENT":"PARENT_V34_BINDING",
}


def _canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def _sha(v:object)->bool:
    return isinstance(v,str) and HEX64.fullmatch(v) is not None

@dataclass(frozen=True)
class ExternalAdversarialValidation:
    decision:str
    errors:tuple[str,...]
    bundle_sha256:str|None
    pass_receipt_sha256:str|None
    negative_case_count:int
    execution_target:str|None
    claims_label:str="EXTERNAL_SYNTHETIC_ADVERSARIAL_VALIDATION_ONLY"
    def to_dict(self)->dict: return asdict(self)


def validate_external_adversarial_bundle(bundle:Mapping[str,Any],*,expected_parent_v3_4_sha256:str,expected_control_core_sha256:str)->ExternalAdversarialValidation:
    errors:list[str]=[]
    if bundle.get("schema")!="WS-QCRYPTO-TSV-V3_5-EXTERNAL-ADVERSARIAL-BUNDLE-V1": errors.append("BAD_SCHEMA")
    claimed=bundle.get("bundle_sha256")
    material=dict(bundle); material.pop("bundle_sha256",None)
    computed=hashlib.sha256(DOMAIN+_canon(material)).hexdigest()
    if not _sha(claimed) or claimed!=computed: errors.append("BUNDLE_HASH_MISMATCH")
    parent=bundle.get("parent_binding") or {}
    if parent.get("v3_4_release_sha256")!=expected_parent_v3_4_sha256: errors.append("PARENT_V34_MISMATCH")
    if parent.get("v3_5_control_core_sha256")!=expected_control_core_sha256: errors.append("CONTROL_CORE_MISMATCH")
    target=bundle.get("execution_target") or {}
    if target.get("provider")!="Supabase Edge Functions": errors.append("UNEXPECTED_PROVIDER")
    if target.get("verify_jwt") is not True: errors.append("JWT_NOT_REQUIRED")
    if int(target.get("function_version") or 0)<1: errors.append("FUNCTION_VERSION_INVALID")
    for key in ("deployed_bundle_sha256","source_index_sha256"):
        if not _sha(target.get(key)): errors.append(f"{key.upper()}_INVALID")
    passed=bundle.get("pass_case") or {}
    if passed.get("http_status")!=200 or passed.get("decision")!="ALLOW": errors.append("PASS_CASE_NOT_ALLOW_200")
    if not _sha(passed.get("receipt_sha256")): errors.append("PASS_RECEIPT_INVALID")
    missing=EXPECTED_PASS-set(passed.get("passed_checks") or [])
    if missing: errors.append("PASS_CHECKS_MISSING:"+",".join(sorted(missing)))
    rows=bundle.get("fail_cases")
    if not isinstance(rows,list): rows=[]; errors.append("FAIL_CASES_NOT_LIST")
    by_name={}
    for row in rows:
        if not isinstance(row,Mapping): errors.append("FAIL_CASE_ROW_INVALID"); continue
        name=str(row.get("name") or "")
        if not name or name in by_name: errors.append("FAIL_CASE_NAME_INVALID_OR_DUPLICATE"); continue
        by_name[name]=row
        if row.get("http_status")!=200 or row.get("decision")!="DENY": errors.append(f"FAIL_CASE_NOT_DENY_200:{name}")
        if not _sha(row.get("receipt_sha256")): errors.append(f"FAIL_RECEIPT_INVALID:{name}")
    for name,check in EXPECTED_FAIL.items():
        row=by_name.get(name)
        if row is None: errors.append(f"MISSING_FAIL_CASE:{name}")
        elif row.get("expected_failed_check")!=check: errors.append(f"WRONG_FAILED_CHECK:{name}")
    if bundle.get("claims_label")!="EXTERNAL_SYNTHETIC_ADVERSARIAL_SOFTWARE_EVIDENCE_ONLY_NOT_LIVE_MARKET_DATA_OR_LEGAL_COMPLIANCE": errors.append("CLAIMS_LABEL_CHANGED")
    negatives=bundle.get("negative_claims") or {}
    for key in (
        "licensed_sip_feed_used","live_primary_exchange_feed_used","live_luld_feed_used",
        "qualified_delivery_provider_attestation","digital_signature_or_trusted_timestamp",
        "sec_approval_established","legal_compliance_established","live_tsv_deployment",
        "real_value_moved","independent_third_party_certification",
    ):
        if negatives.get(key) is not False: errors.append(f"NEGATIVE_CLAIM_NOT_FALSE:{key}")
    exec_target=None
    if target.get("project_ref") and target.get("function_slug"):
        exec_target=f"Supabase:{target['project_ref']}:{target['function_slug']}:v{target.get('function_version')}"
    return ExternalAdversarialValidation(
        "ALLOW" if not errors else "DENY",tuple(errors),claimed if _sha(claimed) else None,
        passed.get("receipt_sha256") if _sha(passed.get("receipt_sha256")) else None,len(rows),exec_target
    )
