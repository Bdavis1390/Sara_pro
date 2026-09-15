from __future__ import annotations

import argparse
import json
from pathlib import Path

from .sentinel_supplier_preflight import (
    SupplierReadinessInput,
    default_unverified_profile,
    evaluate_supplier_preflight,
)


def _load(path: Path | None) -> SupplierReadinessInput:
    if path is None:
        return default_unverified_profile()
    return SupplierReadinessInput.model_validate_json(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate status-only, fail-closed Sentinel supplier/subcontractor onboarding readiness. "
            "This preflight cannot authorize registration, outreach, or external supplier submission."
        )
    )
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--require-registration-ready", action="store_true")
    parser.add_argument(
        "--require-external-authorized",
        action="store_true",
        help=(
            "Negative-control/legacy compatibility flag. Supplier preflight is not an authorization "
            "boundary, so this request always fails closed with exit status 3."
        ),
    )
    args = parser.parse_args()

    report = evaluate_supplier_preflight(_load(args.profile))
    text = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(json.dumps(report, sort_keys=True))

    # Deliberately unconditional and checked first. This CLI reports evidence status only;
    # actual external-action permission requires a separate authenticated SARA workflow.
    if args.require_external_authorized:
        raise SystemExit(3)

    if args.require_registration_ready and not report["supplier_registration_ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
