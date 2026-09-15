#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from scanner import analyze


def main() -> int:
    base = Path(__file__).resolve().parent
    clean = analyze(base / "fixtures/clean.png")
    embedded = analyze(base / "fixtures/embedded.png")

    expected = {"clean": False, "embedded": True}
    observed = {"clean": clean["finding"], "embedded": embedded["finding"]}
    tp = int(observed["embedded"] is True)
    tn = int(observed["clean"] is False)
    fp = int(observed["clean"] is True)
    fn = int(observed["embedded"] is False)

    report = {
        "schema": "WS-STEG-BENCHMARK-V1",
        "fixture_scope": "synthetic deterministic PNG fixtures",
        "expected": expected,
        "observed": observed,
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "false_positive_rate": fp / (fp + tn) if fp + tn else None,
        "false_negative_rate": fn / (fn + tp) if fn + tp else None,
        "result": "PASS" if (tp, tn, fp, fn) == (1, 1, 0, 0) else "FAIL",
        "boundary": "This benchmark validates only the included synthetic fixtures; it does not establish general steganography detection accuracy.",
    }
    (base / "benchmark-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
