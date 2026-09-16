#!/usr/bin/env python3
"""Cross-check Hoodi finalized state across independent checkpoint providers.

This is a bootstrap trust-reduction measure. It does not replace local protocol
verification after the beacon node starts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from security.qcrypto.hoodi_checkpoint_quorum import (
    HOODI_CHECKPOINT_PROVIDERS,
    assess_hoodi_checkpoint_quorum,
)


def fetch_finalized_root(base_url: str, timeout: int = 20) -> str:
    url = base_url.rstrip("/") + "/eth/v1/beacon/states/finalized/root"
    request = Request(url, headers={"User-Agent": "Worldshepherd-QCRYPTO-Hoodi-Quorum/1"})
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    root = ((payload.get("data") or {}).get("root"))
    if not isinstance(root, str):
        raise RuntimeError(f"Provider returned no finalized root: {base_url}")
    return root


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configured-url", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    observations: dict[str, str] = {}
    errors: dict[str, str] = {}
    for name, url in HOODI_CHECKPOINT_PROVIDERS.items():
        try:
            observations[name] = fetch_finalized_root(url)
        except Exception as exc:
            errors[name] = f"{type(exc).__name__}: {exc}"

    assessment = assess_hoodi_checkpoint_quorum(args.configured_url, observations)
    receipt = assessment.to_dict()
    receipt["schema"] = "WS-QCRYPTO-HOODI-CHECKPOINT-QUORUM-V1"
    receipt["provider_errors"] = errors
    receipt["network"] = "HOODI"
    receipt["chain_id"] = 560048
    receipt["claims"] = {
        "consensus_verification_replaced": False,
        "validator_activation_authorized": False,
        "private_key_operations_permitted": False,
        "mainnet_permitted": False,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    if not assessment.accepted:
        raise RuntimeError("Hoodi checkpoint-provider quorum was not established")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
