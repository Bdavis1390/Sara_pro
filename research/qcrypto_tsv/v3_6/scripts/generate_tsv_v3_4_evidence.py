#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from worldshepherd_qcrypto_kms.source_integrity import build_source_manifest, verify_source_manifest
from worldshepherd_qcrypto_kms.tsv.external_execution import validate_external_tsv_execution_bundle
from worldshepherd_qcrypto_kms.tsv.operational_runtime import authorize_operational_tsv
from worldshepherd_qcrypto_kms.tsv.transaction_transparency import TransparencyFeedState
from worldshepherd_qcrypto_kms.tsv.runtime import authorize_bundle
from worldshepherd_qcrypto_kms.tsv_qcrypto_binding import bind_tsv_authorization

Q_PARENT = "e0c7c968f6d8f31278d677c881d3dea4173452ffd4b8ba07850d70970fc654bc"
TSV_PARENT = "7c1ee785f82c5180a7920d8d34889698b3367680788aa4d80b80ed51a1babefe"
V3_3_RELEASE = "fab44ddd5a1d46516f8d2b9fc759f4f23db7d811ab8a7d7a9b79da2d0400a25f"
V3_3_SOURCE = "36af6e42fb78ab6e97a56678b87afc02ff71d4ea79d3d11a778eb03a31c9becc"
PQ_RECEIPT = "79a124693b6c959ea9e1cf43d8fcd2e4bdf5309b562a502cec793f286fd090d3"
EXTERNAL_TSV_BUNDLE = "b3773256881b1690587378d651d4d637bdc3c9d581ba204905e4675852d16625"
EVAL = datetime(2026, 9, 18, 22, 46, tzinfo=timezone.utc)


def main() -> int:
    cp = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"], cwd=ROOT, text=True, capture_output=True)
    log = (cp.stdout or "") + (cp.stderr or "")
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "LOCAL_TEST_V3_4.log").write_text(log, encoding="utf-8")
    count = log.count(" ... ok")

    package_root = ROOT / "worldshepherd_qcrypto_kms"
    manifest = build_source_manifest(package_root)
    integrity = verify_source_manifest(package_root, manifest)
    (ROOT / "SOURCE_INTEGRITY_MANIFEST_V3_4.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (evidence / "SOURCE_INTEGRITY_REPORT_V3_4.json").write_text(json.dumps(integrity, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    external_bundle = json.loads((evidence / "TSV_EXTERNAL_EXECUTION_BUNDLE_V3_4.json").read_text(encoding="utf-8"))
    external_validation = validate_external_tsv_execution_bundle(
        external_bundle,
        expected_parent_release_sha256=V3_3_RELEASE,
        expected_parent_source_manifest_sha256=V3_3_SOURCE,
    )
    (evidence / "TSV_EXTERNAL_EXECUTION_VALIDATION_V3_4.json").write_text(json.dumps(external_validation.to_dict(), sort_keys=True, indent=2) + "\n", encoding="utf-8")

    state = json.loads((evidence / "tsv" / "examples_pass_v3_3.json").read_text(encoding="utf-8"))
    notice = json.loads((evidence / "tsv" / "examples_notice.json").read_text(encoding="utf-8"))
    feed = TransparencyFeedState(True, True, True, True, EVAL - timedelta(days=31), True, True, True, True)
    operational = authorize_operational_tsv(state, notice, now=EVAL, transparency_feed=feed, require_transparency_feed=True)
    (evidence / "TSV_OPERATIONAL_AUTHORIZATION_V3_4.json").write_text(json.dumps(operational.to_dict(), sort_keys=True, indent=2) + "\n", encoding="utf-8")

    base = authorize_bundle(state, notice, now=EVAL)
    binding = bind_tsv_authorization(
        base,
        package_root=package_root,
        source_manifest=manifest,
        parent_qcrypto_zip_sha256=Q_PARENT,
        parent_tsv_zip_sha256=TSV_PARENT,
        external_pq_receipt_sha256=PQ_RECEIPT,
        external_tsv_execution_bundle_sha256=EXTERNAL_TSV_BUNDLE,
    )
    (evidence / "TSV_QCRYPTO_BINDING_V3_4.json").write_text(json.dumps(binding.to_dict(), sort_keys=True, indent=2) + "\n", encoding="utf-8")

    summary = {
        "schema": "WS-QCRYPTO-TSV-V3_4-EVIDENCE-SUMMARY",
        "candidate_version": "v3.4",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "fixed_evaluation_time": EVAL.isoformat().replace("+00:00", "Z"),
        "test_returncode": cp.returncode,
        "test_count": count,
        "test_pass": cp.returncode == 0,
        "source_integrity_satisfied": integrity["satisfied"],
        "source_manifest_sha256": manifest["manifest_sha256"],
        "qcrypto_parent_sha256": Q_PARENT,
        "tsv_parent_sha256": TSV_PARENT,
        "v3_3_parent_release_sha256": V3_3_RELEASE,
        "external_tsv_execution_validation": external_validation.decision,
        "external_tsv_execution_bundle_sha256": external_validation.bundle_sha256,
        "external_tsv_pass_receipt_sha256": external_validation.pass_receipt_sha256,
        "external_tsv_negative_case_count": external_validation.negative_case_count,
        "operational_decision": operational.decision,
        "operational_runtime_sha256": operational.runtime_sha256,
        "tsv_qcrypto_binding_sha256": binding.binding_sha256,
        "claims": {
            "external_software_execution_performed": True,
            "sec_approval": False,
            "legal_opinion": False,
            "registered_exchange_or_ats": False,
            "live_tsv_deployment": False,
            "licensed_sip_feed_connected": False,
            "primary_exchange_halt_feed_connected": False,
            "luld_feed_connected": False,
            "issuer_notice_receipt_source_connected": False,
            "real_value_trading_authorized": False,
            "mainnet_or_broadcast_authorized": False,
            "independent_validation": False
        }
    }
    (evidence / "EVIDENCE_SUMMARY_V3_4.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    ok = cp.returncode == 0 and integrity["satisfied"] and operational.decision != "DENY" and external_validation.decision == "ALLOW"
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
