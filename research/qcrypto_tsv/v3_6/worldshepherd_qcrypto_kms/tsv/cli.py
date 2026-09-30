from __future__ import annotations

import argparse
import json
from pathlib import Path

from .policy import evaluate_tsv
from .runtime import authorize_bundle
from .source_evidence import source_evidence_from_dict


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser(description="Worldshepherd TSV control-profile evaluator")
    p.add_argument("input", type=Path, help="TSV state JSON")
    p.add_argument("--notice", type=Path, help="Section III Notice JSON; enables combined authorization bundle")
    p.add_argument("--market-evidence", type=Path, help="Structured market-source evidence JSON")
    p.add_argument("--symbol", help="Expected NMS stock symbol for market-source evidence")
    p.add_argument("--require-market-evidence", action="store_true", help="Fail closed unless bounded source evidence passes")
    p.add_argument("--market-evidence-max-age-seconds", type=int, default=30)
    p.add_argument("--out", type=Path)
    args = p.parse_args()

    state = _read_json(args.input)
    if args.notice:
        notice = _read_json(args.notice)
        market_evidence = source_evidence_from_dict(_read_json(args.market_evidence)) if args.market_evidence else None
        result = authorize_bundle(
            state,
            notice,
            symbol=args.symbol,
            market_evidence=market_evidence,
            market_evidence_max_age_seconds=args.market_evidence_max_age_seconds,
            require_market_evidence=args.require_market_evidence,
        ).to_dict()
    else:
        if args.market_evidence or args.require_market_evidence or args.symbol:
            p.error("--notice is required for combined market-evidence authorization")
        result = evaluate_tsv(state).to_dict()

    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if result["decision"] != "DENY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
