from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = ROOT / "manifests" / "qo_backend_b000.json"


def validate_qo_contract(path: Path = DEFAULT_MANIFEST) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    native = manifest["paper_native"]
    open_lane = manifest["open_crosscheck"]
    compat = manifest["compatibility_gate"]
    gate = manifest["qo_gate"]

    wheel_pinned = (
        open_lane["status"] == "WHEEL_PINNED_NOT_INSTALLED"
        and len(open_lane["artifact_sha256"]) == 64
    )
    fail_closed = (
        compat["adapter_required"] is True
        and compat["direct_elk_to_pyskeaf_allowed"] is False
        and gate["current_decision"] == "BLOCK_QO_EXTRACTION"
    )
    native_fail_closed = (
        native["status"] == "OFFICIAL_SOURCE_NOT_YET_PINNED"
        and native["retrieval_attempt"]["tls_verification_bypassed"] is False
    )

    return {
        "program": manifest["program"],
        "benchmark": manifest["benchmark"],
        "wheel_pinned": wheel_pinned,
        "paper_native_fail_closed": native_fail_closed,
        "format_adapter_required": compat["adapter_required"],
        "direct_elk_to_pyskeaf_allowed": compat["direct_elk_to_pyskeaf_allowed"],
        "adapter_status": compat["adapter_status"],
        "decision": gate["current_decision"],
        "contract_pass": wheel_pinned and fail_closed and native_fail_closed,
        "claim_boundary": manifest["claim_boundary"],
    }


def main() -> None:
    print(json.dumps(validate_qo_contract(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
