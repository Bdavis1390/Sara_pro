from __future__ import annotations

import argparse
import json
from pathlib import Path

from .offline_attestation import receipt_sha256, verify_offline_attestation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a Worldshepherd release artifact offline using a GitHub attestation bundle and trusted root."
    )
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--trusted-root", required=True)
    parser.add_argument("--repository", default="Bdavis1390/Sara_pro")
    parser.add_argument("--gh-executable", default="gh")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    receipt = verify_offline_attestation(
        artifact=args.artifact,
        bundle=args.bundle,
        trusted_root=args.trusted_root,
        repository=args.repository,
        gh_executable=args.gh_executable,
    )
    result = {
        "receipt": receipt,
        "receipt_sha256": receipt_sha256(receipt),
    }
    rendered = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
