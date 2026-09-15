from __future__ import annotations

import argparse
import json
from pathlib import Path

from .identity_security_g1 import (
    IdentitySecurityG1Report,
    run_identity_security_g1_benchmark,
    verify_identity_security_g1_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run or verify the Worldshepherd identity-security G1 software gate"
    )
    parser.add_argument("--output", type=Path, help="write a deterministic G1 JSON report")
    parser.add_argument("--verify", type=Path, help="verify an existing G1 JSON report")
    args = parser.parse_args()

    if args.verify is not None:
        report = IdentitySecurityG1Report.model_validate_json(args.verify.read_text())
        if not verify_identity_security_g1_report(report):
            raise SystemExit("identity-security G1 report verification failed")
        if not report.acceptance.acceptance_pass:
            raise SystemExit("identity-security G1 report did not pass acceptance")
        print(report.report_digest)
        return

    report = run_identity_security_g1_benchmark()
    if not report.acceptance.acceptance_pass:
        raise SystemExit("identity-security G1 benchmark failed acceptance")
    text = json.dumps(report.model_dump(mode="json"), sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        args.output.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
